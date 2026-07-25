#!/usr/bin/env python3
"""
render_heatmap_svg.py — draw data/contributions.json as the classic
53-week x 7-day calendar of rounded, colored boxes using a GitHub-ish
green ramp. Reveals once with a diagonal, line-after-line slide-down
(CSS keyframes that play on load, then freeze — no looping "glow"),
plus a Less->More legend and a stats footer.

Usage: python3 render_heatmap_svg.py [contrib-heatmap.svg]
Env:   STATIC=1 -> emit a frozen (fully revealed) frame
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
#           none ->                                        brightest (neon top end)

CELL = 11
GAP = 3
LEFT_PAD = 34
TOP_PAD = 34
FONT = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
BG = "#0d1117"
TEXT_DIM = "#8b949e"
TEXT = "#c9d1d9"

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DOW_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # Python weekday(): Mon=0


def level_from_count(count, max_count):
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    # 5 non-zero buckets (levels 1..5), scaled against this user's own max
    ratio = count / max_count
    if ratio <= 0.2:
        return 1
    if ratio <= 0.4:
        return 2
    if ratio <= 0.65:
        return 3
    if ratio <= 0.85:
        return 4
    return 5


def build_weeks(days):
    """Group day dicts into columns (weeks), Sunday-first, matching
    GitHub's own calendar layout."""
    by_date = {d["date"]: d for d in days}
    dates = sorted(by_date)
    if not dates:
        return []

    first = datetime.strptime(dates[0], "%Y-%m-%d")
    last = datetime.strptime(dates[-1], "%Y-%m-%d")

    # rewind to the Sunday on/before the first date so week columns align
    start_offset = (first.weekday() + 1) % 7  # Sun=0 ... Sat=6
    from datetime import timedelta
    grid_start = first - timedelta(days=start_offset)

    weeks = []
    cur = grid_start
    week = []
    while cur <= last:
        key = cur.strftime("%Y-%m-%d")
        d = by_date.get(key, {"date": key, "count": 0, "level": 0})
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []
        cur += timedelta(days=1)
    if week:
        while len(week) < 7:
            week.append({"date": None, "count": 0, "level": 0})
        weeks.append(week)
    return weeks


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(data, static=False):
    days = data["days"]
    stats = data["stats"]
    max_count = max((d["count"] for d in days), default=0)

    weeks = build_weeks(days)
    n_weeks = len(weeks)

    width = LEFT_PAD + n_weeks * (CELL + GAP) + 20
    legend_h = 26
    footer_h = 30
    height = TOP_PAD + 7 * (CELL + GAP) + legend_h + footer_h + 20

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    parts.append(f'<rect width="100%" height="100%" rx="12" fill="{BG}"/>')
    parts.append(
        f'<style>'
        f'.mono{{font-family:{FONT};font-size:11px;fill:{TEXT_DIM};}}'
        f'.stat{{font-family:{FONT};font-size:12.5px;fill:{TEXT};}}'
        f'@keyframes slideIn{{'
        f'from{{transform:translateY(-6px);opacity:0;}}'
        f'to{{transform:translateY(0);opacity:1;}}'
        f'}}'
        f'.cell{{animation:slideIn 0.32s ease-out both;}}'
        f'</style>'
    )

    # month labels along the top — one label per week column where the
    # month changes
    last_month = None
    for wi, week in enumerate(weeks):
        first_real = next((d for d in week if d["date"]), None)
        if not first_real:
            continue
        month = int(first_real["date"][5:7])
        if month != last_month:
            x = LEFT_PAD + wi * (CELL + GAP)
            parts.append(f'<text x="{x}" y="{TOP_PAD - 10}" class="mono">{MONTH_NAMES[month-1]}</text>')
            last_month = month

    # day-of-week labels
    for py_weekday, label in DOW_LABELS.items():
        # convert python Mon=0 weekday to our Sun-first row index
        row = (py_weekday + 1) % 7
        y = TOP_PAD + row * (CELL + GAP) + CELL - 2
        parts.append(f'<text x="0" y="{y}" class="mono">{label}</text>')

    # cells, diagonal stagger: delay depends on (week + row)
    for wi, week in enumerate(weeks):
        for ri, d in enumerate(week):
            x = LEFT_PAD + wi * (CELL + GAP)
            y = TOP_PAD + ri * (CELL + GAP)
            level = level_from_count(d["count"], max_count) if d["date"] else 0
            color = PALETTE[level]
            delay = (wi + ri) * 0.012
            title = ""
            if d["date"]:
                title = f'<title>{d["count"]} contribution{"s" if d["count"] != 1 else ""} on {d["date"]}</title>'
            if static:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">{title}</rect>'
                )
            else:
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}" '
                    f'class="cell" style="animation-delay:{delay:.3f}s;transform-box:fill-box;'
                    f'transform-origin:center;">{title}</rect>'
                )

    # legend: Less -> More
    legend_y = TOP_PAD + 7 * (CELL + GAP) + 20
    lx = LEFT_PAD
    parts.append(f'<text x="{lx - 34}" y="{legend_y + CELL - 2}" class="mono">Less</text>')
    for i, color in enumerate(PALETTE):
        parts.append(f'<rect x="{lx + i*(CELL+GAP)}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"/>')
    parts.append(f'<text x="{lx + len(PALETTE)*(CELL+GAP) + 6}" y="{legend_y + CELL - 2}" class="mono">More</text>')

    # stats footer
    footer_y = legend_y + CELL + 22
    footer_text = (
        f'{stats["total_last_year"]:,} contributions in the last year  ·  '
        f'current streak {stats["current_streak"]}d  ·  longest streak {stats["longest_streak"]}d  ·  '
        f'best day {stats["best_day"]["count"]} ({stats["best_day"]["date"]})'
    )
    parts.append(f'<text x="{LEFT_PAD}" y="{footer_y}" class="stat">{esc(footer_text)}</text>')

    parts.append('</svg>')
    return "\n".join(parts)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "contrib-heatmap.svg"
    static = os.environ.get("STATIC") == "1"
    with open("data/contributions.json") as f:
        data = json.load(f)
    svg = build_svg(data, static=static)
    with open(out, "w") as f:
        f.write(svg)
    print(f"wrote {out} (static={static})")


if __name__ == "__main__":
    main()
