#!/usr/bin/env python3
"""Fetches the starter wallpaper pack into ../wallpapers/: real photos
(originally from Unsplash, mirrored by Lorem Picsum — picsum.photos — so no
API key is needed), each given the same dark gradient tint so a user's random
pick always matches TV Home's "dark, calm" look (docs/DESIGN.md) regardless
of the source photo's own colors.

Dev-time only: needs Pillow (`pip install pillow`) and internet access.
Not shipped or run on the TV box — only the JPEGs it produces are (see
session/install.sh). Re-run to regenerate from the same curated IDs below;
see CURATED for how they were chosen (a labeled contact-sheet review).
"""
import io
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parents[1] / "wallpapers"
WIDTH, HEIGHT = 1920, 1080
BG = (0x10, 0x14, 0x18)  # --bg, frontend/src/styles/tokens.css

# Picsum photo id -> (output name, Unsplash photographer credit).
# Picked from https://picsum.photos/v2/list by eye (a contact sheet of ~30
# candidates) for images that read as calm rather than busy, and that still
# have something to look at after a heavy dark tint.
CURATED = {
    "43": ("night-skyline", "Oleg Chursin"),
    "57": ("dusk-street", "Nicholas Swanson"),
    "56": ("bokeh-lights", "Sebastian Muller"),
    "44": ("misty-coast", "Christopher Sardegna"),
    "50": ("harbor-dusk", "Tyler Wanlass"),
    "58": ("lighthouse", "Tony Naccarato"),
    "46": ("desert-dunes", "Jeffrey Kam"),
    "38": ("cloud-sky", "Allyson Souza"),
}


def fetch(picsum_id: str) -> Image.Image:
    url = f"https://picsum.photos/id/{picsum_id}/{WIDTH}/{HEIGHT}"
    req = urllib.request.Request(url, headers={"User-Agent": "tv-home-wallpaper-fetch"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def tint(img: Image.Image) -> Image.Image:
    """A top-to-bottom dark gradient (stronger at the bottom, where the
    greeting/date text sits) plus a uniform tint toward --bg, so every photo
    ends up in the same tonal range no matter how bright it started."""
    gradient = Image.new("L", (1, HEIGHT))
    for y in range(HEIGHT):
        gradient.putpixel((0, y), int(70 + 140 * (y / HEIGHT)))  # 70..210 alpha, top..bottom
    gradient = gradient.resize((WIDTH, HEIGHT))
    dark_layer = Image.new("RGB", (WIDTH, HEIGHT), BG)
    out = Image.composite(dark_layer, img, gradient)

    flat_tint = Image.new("RGB", (WIDTH, HEIGHT), BG)
    out = Image.blend(out, flat_tint, 0.22)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    credits = []
    for picsum_id, (name, author) in CURATED.items():
        img = tint(fetch(picsum_id))
        out_path = OUT_DIR / f"{name}.jpg"
        # quality=95: comfortably clears the 100KB floor wallpaper.py's
        # wallpapers() filter uses to skip thumbnail-sized stray files (one of
        # these came in under it at quality=88 — a night skyline with large
        # flat dark areas compresses unusually well).
        img.save(out_path, "JPEG", quality=95)
        print(f"wrote {out_path} ({out_path.stat().st_size // 1024} KB) — {author} via Unsplash/Picsum")
        credits.append((name, author, picsum_id))

    credits_path = OUT_DIR / "CREDITS.md"
    lines = ["# Wallpaper credits\n", "\nOriginally from Unsplash, fetched via Lorem Picsum (picsum.photos):\n"]
    for name, author, picsum_id in credits:
        lines.append(f"- `{name}.jpg` — {author}, via https://picsum.photos/id/{picsum_id}\n")
    credits_path.write_text("".join(lines))
    print(f"wrote {credits_path}")


if __name__ == "__main__":
    main()
