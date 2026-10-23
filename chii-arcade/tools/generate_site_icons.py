#!/usr/bin/env python3
"""Rebuild Chii Arcade's browser, iOS and Android website icons.

Run from repository root:
    python3 -m pip install Pillow
    python3 chii-arcade/tools/generate_site_icons.py

The only manually maintained illustration is the *same* WebP file used as
Chii Arcade's Android launcher art. All other sizes are generated from it.
"""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "branding" / "chii-arcade-icon.webp"
BG = (32, 11, 63)


def resized(source: Image.Image, size: int) -> Image.Image:
    return source.resize((size, size), Image.Resampling.LANCZOS)


def png(source: Image.Image, name: str, size: int) -> None:
    target = ROOT / name
    resized(source, size).save(target, format="PNG", optimize=True)
    print(f"{target.relative_to(ROOT)}: {target.stat().st_size:,} bytes")


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    with Image.open(SOURCE) as original:
        original.load()
        source = original.convert("RGBA")

    # Classic browser favicon with 16, 32 and 48 px resolutions.
    # Pillow's ICO writer accepts a 256x256 source and exports each size.
    ico = resized(source, 256)
    ico.save(
        ROOT / "favicon.ico", format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)]
    )
    png(source, "favicon-16x16.png", 16)
    png(source, "favicon-32x32.png", 32)
    png(source, "apple-touch-icon.png", 180)
    png(source, "android-chrome-192x192.png", 192)
    png(source, "android-chrome-512x512.png", 512)

    # Android maskable icon: artwork stays inside the safe central area.
    background = Image.new("RGBA", (512, 512), BG + (255,))
    centered = resized(source, 392)
    background.alpha_composite(centered, (60, 60))
    background.save(ROOT / "android-chrome-maskable-512x512.png", optimize=True)

    # Inline the artwork: SVG favicons cannot reliably load external images.
    data = base64.b64encode(SOURCE.read_bytes()).decode("ascii")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<image x="0" y="0" width="128" height="128" '
        'href="data:image/webp;base64,' + data + '"/>'
        '</svg>\n'
    )
    (ROOT / "favicon.svg").write_text(svg, encoding="utf-8")
    print("favicon.ico, favicon.svg and web app icons generated")


if __name__ == "__main__":
    main()
