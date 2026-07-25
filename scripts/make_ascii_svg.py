#!/usr/bin/env python3
"""
make_ascii_svg.py — convert a prepped grayscale portrait into a
self-typing, monochrome ASCII-art SVG.

The prepped image is downsampled to a character grid; each pixel's
brightness selects a glyph from a density ramp (sparse -> dense).
Each row is wrapped in a horizontal clip-path wipe that reveals it
left-to-right, staggered top to bottom, using pure SMIL animation
(no JavaScript, no CSS-in-README — GitHub renders this fine because
it's all inside the <img>-embedded SVG).

Usage: python3 make_ascii_svg.py [source-prepped.png] [avi-ascii.svg]
Env:   STATIC=1  -> emit a frozen (fully revealed) frame, no animation
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
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG}" rx="10"/>')
    parts.append(
        f'<style>text{{font-family:\'SFMono-Regular\',Consolas,\'Liberation Mono\',Menlo,monospace;'
        f'font-size:{FONT_SIZE}px;fill:{FILL};white-space:pre;}}</style>'
    )

    row_dur = 0.42
    stagger = 0.055

    for i, row in enumerate(rows):
        y = pad_y + (i + 1) * LINE_H
        row_w = COLS * CHAR_W
        clip_id = f"rowclip{i}"
        start = i * stagger

        if not row.strip():
            continue  # blank row, nothing to draw

        if static:
            # frozen frame: clip rect fully open from the start, no animation
            parts.append(
                f'<clipPath id="{clip_id}"><rect x="{pad_x}" y="{y - LINE_H}" '
                f'width="{row_w:.1f}" height="{LINE_H + 4:.1f}"/></clipPath>'
            )
        else:
            # clip rect starts at width 0 and animates open — <animate> is
            # nested as a child of the rect it targets, so no xlink:href
            # indirection is needed (keeps this robust under GitHub's
            # SVG sanitizer).
            parts.append(
                f'<clipPath id="{clip_id}"><rect x="{pad_x}" y="{y - LINE_H}" '
                f'width="0" height="{LINE_H + 4:.1f}">'
                f'<animate attributeName="width" from="0" to="{row_w:.1f}" '
                f'begin="{start:.3f}s" dur="{row_dur}s" fill="freeze" '
                f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
                f'</rect></clipPath>'
            )

        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.append(f'<text x="{pad_x}" y="{y}">{esc(row)}</text>')
        parts.append('</g>')

        # small block cursor riding the wipe edge (skipped in static mode)
        if not static:
            parts.append(
                f'<rect x="{pad_x}" y="{y - LINE_H + 1}" width="{CHAR_W:.1f}" '
                f'height="{LINE_H - 2:.1f}" fill="{FILL}" opacity="0.55">'
                f'<animate attributeName="x" from="{pad_x}" to="{pad_x + row_w:.1f}" '
                f'begin="{start:.3f}s" dur="{row_dur}s" fill="freeze" '
                f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
                f'<animate attributeName="opacity" from="0.55" to="0" '
                f'begin="{start + row_dur:.3f}s" dur="0.15s" fill="freeze"/>'
                f'</rect>'
            )

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
