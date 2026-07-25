#!/usr/bin/env python3
"""
make_ascii_svg.py — convert a prepped grayscale portrait into a
self-typing, monochrome ASCII-art SVG.

The prepped image is downsampled to a character grid; each pixel's
brightness selects a glyph from a density ramp (sparse -> dense).

IMPORTANT finding from testing against the live rendered profile page:
GitHub's SVG sanitizer strips the entire <style> tag (not just SMIL
<animate>/<animateTransform> — CSS @keyframes inside <style> get
stripped too). Any color/font defined only via a CSS class silently
disappears, which is why text rendered invisible even with "working"
CSS animation code. The fix is to put font-family/font-size/fill
directly as presentation ATTRIBUTES on each element (never inside
<style>) — exactly how the contribution heatmap's cell colors survive
(they're set via a "fill" attribute per <rect>, not a CSS class).
So: no <style>, no animation, plain attributes only.

Usage: python3 make_ascii_svg.py [source-prepped.png] [avi-ascii.svg]
"""
import os
import sys
from PIL import Image

RAMP = " .`:-=+*cs#%@"   # bright (sparse) -> dark (dense)
COLS = 100
ROWS = 53
FONT_SIZE = 8.6
CHAR_W = FONT_SIZE * 0.6     # monospace advance width
LINE_H = FONT_SIZE * 1.0
FILL = "#8b96a5"             # single light-gray fill (monochrome, no rainbow)
BG = "#0d1117"               # GitHub-dark canvas so the SVG looks native on profile


def img_to_ascii_rows(path, cols=COLS, rows=ROWS):
    im = Image.open(path).convert("L")
    # Slight blur before downsampling smooths skin/hair micro-texture so
    # the ramp responds to facial shape, not per-pixel noise.
    im = im.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(radius=2))
    im = im.resize((cols, rows), Image.LANCZOS)
    px = im.load()
    ramp_len = len(RAMP)
    out_rows = []
    for y in range(rows):
        line = []
        for x in range(cols):
            v = px[x, y] / 255.0          # 0 = black, 1 = white
            idx = int((1.0 - v) * (ramp_len - 1))
            line.append(RAMP[idx])
        out_rows.append("".join(line))
    return out_rows


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_svg(rows, static=False):
    width = COLS * CHAR_W + 24
    height = ROWS * LINE_H + 24
    pad_x, pad_y = 12, 16

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG}" rx="10"/>')

    font_attrs = (
        f'font-family="SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace" '
        f'font-size="{FONT_SIZE}" fill="{FILL}" xml:space="preserve"'
    )

    for i, row in enumerate(rows):
        y = pad_y + (i + 1) * LINE_H
        if not row.strip():
            continue  # blank row, nothing to draw
        parts.append(f'<text x="{pad_x}" y="{y}" {font_attrs}>{esc(row)}</text>')

    parts.append('</svg>')
    return "\n".join(parts)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    out = sys.argv[2] if len(sys.argv) > 2 else "manish-ascii.svg"
    static = os.environ.get("STATIC") == "1"

    rows = img_to_ascii_rows(src)
    svg = build_svg(rows, static=static)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out}  ({COLS}x{ROWS} chars, static={static})")


if __name__ == "__main__":
    main()
