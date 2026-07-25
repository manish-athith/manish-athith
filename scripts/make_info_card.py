#!/usr/bin/env python3
"""
make_info_card.py — hand-author a neofetch-style SVG info card:
a terminal title bar, then colored key/value rows (Now / Prev / Stack /
Highlights). Each line fades + slides in on a short stagger so the
panel looks like it's printing next to the ASCII portrait.

This is the "story numbers can't tell" panel — the contribution
heatmap already covers raw GitHub stats, so keep this to role, stack,
and highlight lines instead of duplicating counts.

Usage: python3 make_info_card.py [info-card.svg]
Env:   STATIC=1  -> emit a frozen frame (for local Quick Look previews)
"""
import os
import sys
import textwrap

WIDTH = 640
FONT = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

PANEL = "#161b22"
BORDER = "#30363d"
LABEL_COLOR = "#39d353"     # GitHub green — matches the heatmap accent
VALUE_COLOR = "#c9d1d9"
DIM = "#8b949e"
TITLE_BAR = "#21262d"
DOT_RED, DOT_YEL, DOT_GRN = "#ff5f56", "#ffbd2e", "#27c93f"

LABEL_X = 24
VALUE_X = 112
RIGHT_MARGIN = 20
VALUE_FONT_PX = 13
HL_FONT_PX = 12.5
# rough monospace advance-width fraction of font-size (safe overestimate
# so wraps happen a little early rather than clipping at the edge)
ADVANCE = 0.62

# ---- content -----------------------------------------------------
NOW = "AI Product Research Fellow @ iHub-Data, IIIT Hyderabad"
PREV = "Product Lead @ Polygnan · AI/Product Intern @ Jangle, Alpixn, Foruppo"
STACK = "Python · SQL · XGBoost/Scikit-learn · LangChain/LLMs · FastAPI · React · GCP"
HIGHLIGHTS = [
    "Best Mock Pitch Award + Top 7/cohort — LokKala Demo Day",
    "Built SHANK: real-time phishing + threat-intel platform",
    "Shipped a Conversational AI product, +30% engagement",
    "Credit Risk ML pipeline deployed as a live Streamlit app",
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text, font_px, x, right_margin=RIGHT_MARGIN):
    avail_px = WIDTH - right_margin - x
    max_chars = max(10, int(avail_px / (font_px * ADVANCE)))
    return textwrap.wrap(text, width=max_chars) or [""]


def build_svg(static=False):
    row_gap = 10
    line_h = 19
    top_pad = 68

    parts = []
    anims = []
    stagger = 0.16
    step = [0]  # mutable counter for stagger index

    def next_begin():
        b = step[0] * stagger
        step[0] += 1
        return b

    def emit_fade_group(gid, y_shift_from, contents_fn):
        begin = next_begin()
        op = "1" if static else "0"
        tr = "translate(0,0)" if static else f"translate({y_shift_from},0)"
        parts.append(f'<g id="{gid}" opacity="{op}" transform="{tr}">')
        contents_fn()
        parts.append('</g>')
        if not static:
            anims.append(
                f'<animate xlink:href="#{gid}" attributeName="opacity" from="0" to="1" '
                f'begin="{begin:.2f}s" dur="0.35s" fill="freeze"/>'
            )
            anims.append(
                f'<animateTransform xlink:href="#{gid}" attributeName="transform" type="translate" '
                f'from="-8,0" to="0,0" begin="{begin:.2f}s" dur="0.35s" fill="freeze" additive="replace"/>'
            )

    y = [top_pad]

    def label_value_row(label, value, gid):
        lines = wrap(value, VALUE_FONT_PX, VALUE_X)
        row_y = y[0]

        def draw():
            parts.append(f'<text x="{LABEL_X}" y="{row_y}" class="mono label">{esc(label)}</text>')
            for i, ln in enumerate(lines):
                parts.append(
                    f'<text x="{VALUE_X}" y="{row_y + i * line_h}" class="mono value">{esc(ln)}</text>'
                )

        emit_fade_group(gid, -8, draw)
        y[0] = row_y + (len(lines) - 1) * line_h + line_h + row_gap

    label_value_row("Now", NOW, "row-now")
    label_value_row("Prev", PREV, "row-prev")
    label_value_row("Stack", STACK, "row-stack")

    y[0] += 8
    header_y = y[0]
    emit_fade_group("row-hl-header", -8, lambda: parts.append(
        f'<text x="{LABEL_X}" y="{header_y}" class="mono label">Highlights</text>'
    ))
    y[0] += 22

    for i, line in enumerate(HIGHLIGHTS):
        wrapped = wrap(line, HL_FONT_PX, 40)
        row_y = y[0]
        gid = f"row-hl-{i}"

        def draw(wrapped=wrapped, row_y=row_y):
            parts.append(f'<text x="{LABEL_X}" y="{row_y}" class="mono dim">*</text>')
            for j, ln in enumerate(wrapped):
                parts.append(
                    f'<text x="40" y="{row_y + j * line_h}" class="mono hl">{esc(ln)}</text>'
                )

        emit_fade_group(gid, -8, draw)
        y[0] = row_y + (len(wrapped) - 1) * line_h + line_h + 6

    height = y[0] + 20

    header = []
    header.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">'
    )
    header.append(
        f'<style>'
        f'.mono{{font-family:{FONT};}}'
        f'.label{{font-size:{VALUE_FONT_PX}px;fill:{LABEL_COLOR};font-weight:600;}}'
        f'.value{{font-size:{VALUE_FONT_PX}px;fill:{VALUE_COLOR};}}'
        f'.dim{{font-size:12px;fill:{DIM};}}'
        f'.hl{{font-size:{HL_FONT_PX}px;fill:{VALUE_COLOR};}}'
        f'</style>'
    )
    header.append(f'<rect width="100%" height="100%" rx="12" fill="{PANEL}" stroke="{BORDER}"/>')
    header.append(
        f'<path d="M0,12 a12,12 0 0 1 12,-12 h{WIDTH-24} a12,12 0 0 1 12,12 v26 h-{WIDTH} z" fill="{TITLE_BAR}"/>'
    )
    for i, c in enumerate([DOT_RED, DOT_YEL, DOT_GRN]):
        header.append(f'<circle cx="{24 + i*18}" cy="19" r="6" fill="{c}"/>')
    header.append(
        f'<text x="{WIDTH/2}" y="24" text-anchor="middle" class="mono dim">manish@github: ~/whoami</text>'
    )

    svg = "\n".join(header) + "\n" + "\n".join(parts) + "\n" + "\n".join(anims) + "\n</svg>"
    return svg


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "info-card.svg"
    static = os.environ.get("STATIC") == "1"
    svg = build_svg(static=static)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out} (static={static})")


if __name__ == "__main__":
    main()
