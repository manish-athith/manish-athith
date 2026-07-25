#!/usr/bin/env python3
"""
make_info_card.py — hand-author a neofetch-style SVG info card:
a terminal title bar, then colored key/value rows (Now / Prev / Stack /
Highlights).

IMPORTANT finding from testing against the live rendered profile page:
GitHub's SVG sanitizer strips the entire <style> tag on embedded/
previewed SVGs — not just SMIL <animate>, CSS @keyframes inside
<style> get stripped too. Anything whose color/font came only from a
CSS class silently vanished (text rendered fully invisible). The fix:
every font-family/font-size/fill lives as a presentation ATTRIBUTE
directly on each element, never inside <style> — the same pattern
that makes the contribution heatmap's cell colors survive (each
<rect> has its own "fill" attribute, no class needed).

This is the "story numbers can't tell" panel — the contribution
heatmap already covers raw GitHub stats, so keep this to role, stack,
and highlight lines instead of duplicating counts.

Usage: python3 make_info_card.py [info-card.svg]
"""
import sys
import textwrap

WIDTH = 640
FONT = "SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace"

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


def text_el(x, y, s, size, fill, weight=None, anchor=None):
    attrs = f'x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    return f'<text {attrs}>{esc(s)}</text>'


def build_svg():
    row_gap = 10
    line_h = 19
    top_pad = 68

    body = []
    y = [top_pad]

    def label_value_row(label, value):
        lines = wrap(value, VALUE_FONT_PX, VALUE_X)
        row_y = y[0]
        body.append(text_el(LABEL_X, row_y, label, VALUE_FONT_PX, LABEL_COLOR, weight="600"))
        for i, ln in enumerate(lines):
            body.append(text_el(VALUE_X, row_y + i * line_h, ln, VALUE_FONT_PX, VALUE_COLOR))
        y[0] = row_y + (len(lines) - 1) * line_h + line_h + row_gap

    label_value_row("Now", NOW)
    label_value_row("Prev", PREV)
    label_value_row("Stack", STACK)

    y[0] += 8
    body.append(text_el(LABEL_X, y[0], "Highlights", VALUE_FONT_PX, LABEL_COLOR, weight="600"))
    y[0] += 22

    for line in HIGHLIGHTS:
        wrapped = wrap(line, HL_FONT_PX, 40)
        row_y = y[0]
        body.append(text_el(LABEL_X, row_y, "*", 12, DIM))
        for j, ln in enumerate(wrapped):
            body.append(text_el(40, row_y + j * line_h, ln, HL_FONT_PX, VALUE_COLOR))
        y[0] = row_y + (len(wrapped) - 1) * line_h + line_h + 6

    height = y[0] + 20

    header = []
    header.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">'
    )
    header.append(f'<rect width="100%" height="100%" rx="12" fill="{PANEL}" stroke="{BORDER}"/>')
    header.append(
        f'<path d="M0,12 a12,12 0 0 1 12,-12 h{WIDTH-24} a12,12 0 0 1 12,12 v26 h-{WIDTH} z" fill="{TITLE_BAR}"/>'
    )
    for i, c in enumerate([DOT_RED, DOT_YEL, DOT_GRN]):
        header.append(f'<circle cx="{24 + i*18}" cy="19" r="6" fill="{c}"/>')
    header.append(text_el(WIDTH / 2, 24, "manish@github: ~/whoami", 12, DIM, anchor="middle"))

    svg = "\n".join(header) + "\n" + "\n".join(body) + "\n</svg>"
    return svg


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "info-card.svg"
    svg = build_svg()
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
