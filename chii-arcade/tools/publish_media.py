#!/usr/bin/env python3
"""Publish approved game cover and screenshots to Chii Arcade, without an APK update.

Usage from a game project:
 python3 /path/to/publish_media.py --config chii-arcade.json --dry-run
 python3 /path/to/publish_media.py --config chii-arcade.json

Example private chii-arcade.json fields (paths relative to config file):
 "coverImage": "store-media/cover.webp",
 "screenshots": ["store-media/01-world-map.webp", "store-media/02-puzzle.webp"]

Requires Python 3.10+ and authenticated GitHub CLI 'gh' with write access to
ChobitsChii/ChobitsChii.github.io. Existing game must already be in catalog.
No private signing keys or GitHub secrets are read from game files.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

REPO = "ChobitsChii/ChobitsChii.github.io"
CATALOG_PATH = "chii-arcade/catalog-v1.json"
BRANCH = "main"
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_FILE = 4 * 1024 * 1024
MAX_SCREENSHOTS = 8
MAX_TOTAL = 22 * 1024 * 1024


def gh_api(path: str, payload: dict | None = None) -> dict:
    args = ["gh", "api"]
    if payload is not None:
        args += ["--method", "PUT", path, "--input", "-"]
    else:
        args.append(path)
    process = subprocess.run(
        args,
        input=json.dumps(payload) if payload is not None else None,
        text=True, capture_output=True
    )
    if process.returncode:
        raise RuntimeError(
            f"GitHub API {path} fehlgeschlagen: {(process.stderr or process.stdout)[:500]}"
        )
    return json.loads(process.stdout)


def lookup(path: str) -> dict | None:
    process = subprocess.run(
        ["gh", "api", path], text=True, capture_output=True
    )
    if process.returncode == 0:
        return json.loads(process.stdout)
    if "404" in process.stderr:
        return None
    raise RuntimeError(f"GitHub API-Abfrage fehlgeschlagen: {process.stderr[:500]}")


def image_file(base: Path, relative: object) -> tuple[bytes, str]:
    if not isinstance(relative, str) or not re.fullmatch(
        r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.webp", relative
    ):
        raise ValueError("Bildpfad muss relativ und eine .webp-Datei sein")
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError(f"Bild fehlt oder liegt außerhalb des Projektordners: {relative}")
    data = path.read_bytes()
    if not (0 < len(data) <= MAX_FILE):
        raise ValueError(f"Bildgröße außerhalb der 4-MB-Grenze: {relative}")
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"Datei ist kein WebP-Bild: {relative}")
    return data, hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config_file = args.config.expanduser().resolve()
    cfg = json.loads(config_file.read_text(encoding="utf-8"))
    game_id = cfg["id"]
    if not isinstance(game_id, str) or not ID.fullmatch(game_id):
        raise ValueError("Ungültige Spiel-ID")
    cover_path = cfg.get("coverImage")
    shots = cfg.get("screenshots")
    if not isinstance(cover_path, str) or not isinstance(shots, list) or not 1 <= len(shots) <= MAX_SCREENSHOTS:
        raise ValueError("coverImage und 1–8 screenshots müssen in chii-arcade.json stehen")

    items = [("cover", cover_path)] + [
        (f"screenshot-{i:02d}", path) for i, path in enumerate(shots, 1)
    ]
    images: list[tuple[str, bytes, str]] = []
    total = 0
    urls: dict[str, str] = {}
    for key, relative in items:
        data, digest = image_file(config_file.parent, relative)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError("Gesamte Medienmenge darf 22 MB nicht überschreiten")
        name = f"{key}-{digest[:12]}.webp"
        target = f"chii-arcade/assets/{game_id}/{name}"
        urls[key] = f"https://chobitschii.github.io/{target}"
        images.append((target, data, digest))
        print(f"Bild: {relative} → {target} ({len(data)} Bytes)")

    if args.dry_run:
        print("Dry-run erfolgreich: keine öffentliche Änderung vorgenommen.")
        return 0

    catalog_obj = gh_api(f"repos/{REPO}/contents/{CATALOG_PATH}?ref={BRANCH}")
    catalog = json.loads(base64.b64decode(catalog_obj["content"]))
    if catalog.get("schemaVersion") != 1:
        raise RuntimeError("Unerwartete Katalogversion")
    games = catalog.get("games", [])
    game = next((g for g in games if g.get("id") == game_id), None)
    if game is None or game.get("preview") is not False or not game.get("androidRelease"):
        raise RuntimeError("Nur bereits öffentlich installierbare Spiele dürfen Medien aktualisieren")

    # Write all images first. Hashed filenames are immutable. Orphaned assets on
    # partial errors are harmless; never publish catalog links until all succeed.
    for target, data, digest in images:
        existing = lookup(f"repos/{REPO}/contents/{target}?ref={BRANCH}")
        if existing is not None:
            existing_bytes = base64.b64decode(existing["content"])
            if hashlib.sha256(existing_bytes).hexdigest() != digest:
                raise RuntimeError(f"Bild unter Hashnamen hat andere Daten: {target}")
            continue
        payload = {
            "message": f"media(arcade): {game_id} {target.rsplit('/',1)[-1]}",
            "content": base64.b64encode(data).decode("ascii"),
            "branch": BRANCH,
        }
        gh_api(f"repos/{REPO}/contents/{target}", payload)

    # Refresh sha after media commits (the catalog blob itself is unchanged).
    current = gh_api(f"repos/{REPO}/contents/{CATALOG_PATH}?ref={BRANCH}")
    current_catalog = json.loads(base64.b64decode(current["content"]))
    current_game = next((g for g in current_catalog["games"] if g.get("id") == game_id), None)
    if current_game is None or current_game.get("preview") is not False:
        raise RuntimeError("Spiel wurde während des Uploads aus dem Katalog entfernt")
    current_game["coverImage"] = urls["cover"]
    current_game["screenshots"] = [urls[f"screenshot-{i:02d}"] for i in range(1, len(shots) + 1)]
    current_catalog["generatedAt"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    encoded = json.dumps(current_catalog, ensure_ascii=False, indent=2) + "\n"
    gh_api(f"repos/{REPO}/contents/{CATALOG_PATH}", {
        "message": f"media(arcade): update {game_id} cover and screenshots",
        "content": base64.b64encode(encoded.encode("utf-8")).decode("ascii"),
        "sha": current["sha"],
        "branch": BRANCH
    })
    print(f"Erfolg: {game_id}-Bilder veröffentlicht, Katalog aktualisiert.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        sys.exit(1)
