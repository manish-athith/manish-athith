#!/usr/bin/env python3
"""
fetch_contributions.py — pull the real GitHub contribution calendar
with no token and no GraphQL API. GitHub serves the calendar as public
HTML fragment at https://github.com/users/<username>/contributions —
the same markup the profile page itself uses.

Writes data/contributions.json with the raw 53x7 day grid plus derived
stats (current streak, longest streak, best day, monthly totals) that
the info card / heatmap footer can reference.

Usage: python3 fetch_contributions.py [username]
Env:   GITHUB_USERNAME can be used instead of the CLI arg.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; profile-readme-bot/1.0)"


def fetch_html(username):
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_days(html):
    soup = BeautifulSoup(html, "html.parser")

    # tooltip text carries the exact count: "No contributions on July 20th."
    # or "3 contributions on July 21st."
    tooltip_count = {}
    for tip in soup.find_all("tool-tip"):
        for_id = tip.get("for")
        if not for_id:
            continue
        text = tip.get_text(strip=True)
        m = re.match(r"([\d,]+)\s+contributions?", text)
        if m:
            tooltip_count[for_id] = int(m.group(1).replace(",", ""))
        elif text.lower().startswith("no contributions"):
            tooltip_count[for_id] = 0

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        date = td.get("data-date")
        if not date:
            continue
        level = int(td.get("data-level", 0))
        count = tooltip_count.get(td.get("id"), None)
        if count is None:
            # fall back to level as a rough proxy if tooltip missing
            count = level
        days.append({"date": date, "level": level, "count": count})

    days.sort(key=lambda d: d["date"])

    # total, from the page header e.g. "94 contributions in the last year"
    total = None
    h2 = soup.find("h2", id="js-contribution-activity-description")
    if h2:
        m = re.search(r"([\d,]+)\s+contributions", h2.get_text())
        if m:
            total = int(m.group(1).replace(",", ""))
    if total is None:
        total = sum(d["count"] for d in days)

    return days, total


def compute_stats(days, total):
    monthly = defaultdict(int)
    best_day = {"date": None, "count": -1}
    for d in days:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] += d["count"]
        if d["count"] > best_day["count"]:
            best_day = {"date": d["date"], "count": d["count"]}

    # current streak: consecutive days with count > 0 ending at the
    # most recent day that has data
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    run = 0
    for d in days:
        if d["count"] > 0:
            run += 1
            longest_streak = max(longest_streak, run)
        else:
            run = 0

    return {
        "total_last_year": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "monthly_totals": dict(sorted(monthly.items())),
    }


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USERNAME", "manish-athith")
    html = fetch_html(username)
    days, total = parse_days(html)
    stats = compute_stats(days, total)

    out = {
        "username": username,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "days": days,
        "stats": stats,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/contributions.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"wrote data/contributions.json — {len(days)} days, "
          f"{stats['total_last_year']} contributions in the last year, "
          f"current streak {stats['current_streak']}, longest {stats['longest_streak']}")


if __name__ == "__main__":
    main()
