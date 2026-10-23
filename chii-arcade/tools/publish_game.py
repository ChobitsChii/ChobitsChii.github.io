#!/usr/bin/env python3
"""Veröffentlicht eine signierte Android-APK in GitHub Releases und aktualisiert Chii Arcade.

Benötigt: Python 3.10+, gh (mit Schreibzugriff angemeldet), Android SDK aapt & apksigner.
Keine privaten Signierschlüssel oder Passwörter werden benötigt.
Die APK wird zuerst öffentlich veröffentlicht und ERST DANACH katalogisiert.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

PAGES_REPO = "ChobitsChii/ChobitsChii.github.io"
PAGES_PATH = "chii-arcade/catalog-v1.json"
PAGES_BRANCH = "main"
PUBLIC_RELEASE_REPO = "ChobitsChii/games"
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FINGERPRINT = re.compile(r"^[a-f0-9]{64}$")
PACKAGE_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z_0-9]*(?:\.[a-zA-Z_][a-zA-Z_0-9]*)+$")


def run(*args: str, stdin: str | None = None) -> str:
    result = subprocess.run(args, input=stdin, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Befehl fehlgeschlagen: {args[0]} {args[1]}: {detail[:600]}")
    return result.stdout


def sdk_binary(tool: str) -> str:
    found = shutil.which(tool)
    if found:
        return found
    roots = [os.environ.get("ANDROID_HOME"), os.environ.get("ANDROID_SDK_ROOT"),
             str(Path.home() / "Android" / "Sdk")]
    for root in roots:
        if not root:
            continue
        options = sorted((Path(root) / "build-tools").glob(f"*/{tool}"), reverse=True)
        if options:
            return str(options[0])
    raise RuntimeError(f"{tool} nicht gefunden – Android SDK Build-Tools installieren oder PATH setzen.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_apk(apk: Path) -> tuple[str, int, str, str]:
    signer_output = run(sdk_binary("apksigner"), "verify", "--print-certs", str(apk))
    match = re.search(r"Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F:]+)", signer_output)
    if not match:
        raise RuntimeError("Kein APK-Signaturfingerabdruck gefunden.")
    fingerprint = match.group(1).replace(":", "").lower()
    if not FINGERPRINT.fullmatch(fingerprint):
        raise RuntimeError("Ungültiger Zertifikatsfingerabdruck.")
    badging = run(sdk_binary("aapt"), "dump", "badging", str(apk))
    match = re.search(
        r"package:\s+name='([^']+)'\s+versionCode='(\d+)'\s+versionName='([^']+)'", badging
    )
    if not match:
        raise RuntimeError("Paket-ID und Version der APK konnten nicht ermittelt werden.")
    return match.group(1), int(match.group(2)), match.group(3), fingerprint


def github_json(endpoint: str) -> dict:
    return json.loads(run("gh", "api", endpoint))


def maybe_release(repo: str, tag: str) -> dict | None:
    # gh release list bietet keine Asset-Digests; hier direkt die API abfragen.
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/releases/tags/{quote(tag, safe='')}"],
        text=True, capture_output=True
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "404" in (result.stderr or ""):
        return None
    raise RuntimeError(f"Release-Abfrage fehlgeschlagen: {result.stderr[:600]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="Spielmetadaten in JSON")
    parser.add_argument("--apk", required=True, type=Path, help="Fertig signierte APK")
    parser.add_argument("--release-repo", default=PUBLIC_RELEASE_REPO,
                        help="Öffentliches Repository für Releases")
    parser.add_argument("--dry-run", action="store_true", help="Prüfen, aber nichts veröffentlichen")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    apk = args.apk.expanduser().resolve()
    if not apk.is_file() or apk.suffix.lower() != ".apk":
        raise RuntimeError("Die angegebene APK fehlt.")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+\.apk", apk.name):
        raise RuntimeError("APK-Dateiname darf nur Buchstaben, Zahlen, Punkt, Unterstrich und Bindestrich enthalten.")
    game_id = config["id"]
    if not ID_PATTERN.fullmatch(game_id):
        raise RuntimeError("Ungültige Spiel-ID.")
    for field in ("title", "category", "teaser", "description", "symbol"):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise RuntimeError(f"Feld fehlt: {field}")
    pkg, code, version, signer = inspect_apk(apk)
    expected = config["android"]["packageName"]
    pinned = config["android"]["signingCertificateSha256"].lower()
    if not PACKAGE_PATTERN.fullmatch(expected) or pkg != expected:
        raise RuntimeError(f"Paketkennung passt nicht zur Konfiguration: {pkg}")
    if not FINGERPRINT.fullmatch(pinned) or signer != pinned:
        raise RuntimeError("APK hat nicht die erwartete dauerhafte Release-Signatur!")
    if not re.fullmatch(r"[a-zA-Z0-9._-]{1,60}", version):
        raise RuntimeError("Versionsname nicht als Release-Tag verwendbar.")
    if not re.fullmatch(r"ChobitsChii/[a-zA-Z0-9._-]+", args.release_repo):
        raise RuntimeError("Release-Repository muss von ChobitsChii stammen.")
    if args.release_repo != PUBLIC_RELEASE_REPO:
        raise RuntimeError("Dieser Android-Client erlaubt derzeit nur das öffentliche Repository ChobitsChii/games.")

    size = apk.stat().st_size
    if not 0 < size <= 150 * 1024 * 1024:
        raise RuntimeError("APK ist zu groß.")
    digest = sha256(apk)
    tag = f"{game_id}-v{version}"
    asset_url = f"https://github.com/{args.release_repo}/releases/download/{tag}/{quote(apk.name)}"
    release_data = {
        "packageName": pkg,
        "versionName": version,
        "versionCode": code,
        "apkUrl": asset_url,
        "sizeBytes": size,
        "sha256": digest,
        "signingCertificateSha256": signer
    }

    print(f"Spiel: {config['title']} | Version {version} (Code {code})")
    print(f"APK: {apk.name} | {size:,} Bytes | SHA-256: {digest}")
    print(f"Öffentliche Adresse: {asset_url}")
    if args.dry_run:
        print("Dry-run abgeschlossen: Es wurden keine GitHub-Daten verändert.")
        return 0

    current = github_json(f"repos/{PAGES_REPO}/contents/{PAGES_PATH}?ref={PAGES_BRANCH}")
    catalog = json.loads(base64.b64decode(current["content"]).decode("utf-8"))
    if catalog.get("schemaVersion") != 1 or not isinstance(catalog.get("games"), list):
        raise RuntimeError("Unerwartetes Store-Katalogformat. Keine Veröffentlichung.")
    old = next((x for x in catalog["games"] if x.get("id") == game_id), None)
    if old and not old.get("preview", True):
        previous = old["androidRelease"]
        if previous["packageName"] != pkg or previous["signingCertificateSha256"] != signer:
            raise RuntimeError("Paket oder Signatur hat sich geändert. Veröffentlichung gestoppt.")
        if int(previous["versionCode"]) > code:
            raise RuntimeError("Niedrigerer Versionscode: Android-Downgrades sind nicht erlaubt.")
        if int(previous["versionCode"]) == code and previous["sha256"] != digest:
            raise RuntimeError("Gleicher Versionscode mit anderer APK. Bitte Versionscode erhöhen.")

    existing = maybe_release(args.release_repo, tag)
    if existing is None:
        print("Erstelle das öffentliche GitHub-Release …")
        run("gh", "release", "create", tag, str(apk),
            "--repo", args.release_repo,
            "--title", f"{config['title']} v{version} (Android)",
            "--notes", f"Signierte Android-Ausgabe für Chii Arcade. Paket: {pkg}, Versionscode: {code}.")
    else:
        assets = [a for a in existing.get("assets", []) if a["name"] == apk.name]
        if assets:
            asset = assets[0]
            if asset.get("digest") != f"sha256:{digest}" or asset.get("size") != size:
                raise RuntimeError("Release enthält bereits eine andere Datei gleichen Namens.")
            print("Identisches öffentliches Release-Asset existiert bereits.")
        else:
            run("gh", "release", "upload", tag, str(apk), "--repo", args.release_repo)
    # Vor Veröffentlichung des Katalogs prüfen, dass der Asset-Eintrag existiert.
    published = maybe_release(args.release_repo, tag)
    assets = [a for a in (published or {}).get("assets", []) if a["name"] == apk.name]
    if not assets or assets[0].get("digest") != f"sha256:{digest}":
        raise RuntimeError("Hochgeladenes Asset nicht verifiziert. Katalog bleibt unverändert.")

    game = {
        "id": game_id, "title": config["title"], "category": config["category"],
        "teaser": config["teaser"], "description": config["description"],
        "symbol": config["symbol"], "preview": False, "androidRelease": release_data
    }
    if old:
        # Media belongs to the game's public catalog entry, not APK release data.
        # Keep its immutable URLs when publishing a new Android version.
        for media_key in ("coverImage", "screenshots"):
            if media_key in old:
                game[media_key] = old[media_key]
        catalog["games"][catalog["games"].index(old)] = game
    else:
        catalog["games"].append(game)
    catalog["catalogMode"] = "mixed"
    catalog["generatedAt"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    data = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    payload = json.dumps({
        "message": f"release(arcade): publish {game_id} v{version}",
        "content": base64.b64encode(data.encode("utf-8")).decode("ascii"),
        "sha": current["sha"],
        "branch": PAGES_BRANCH
    })
    run("gh", "api", "--method", "PUT", f"repos/{PAGES_REPO}/contents/{PAGES_PATH}",
        "--input", "-", stdin=payload)
    print("FERTIG: Chii Arcade Katalog aktualisiert. GitHub Pages benötigt ggf. einen Moment.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"FEHLER: {error}", file=sys.stderr)
        sys.exit(1)
