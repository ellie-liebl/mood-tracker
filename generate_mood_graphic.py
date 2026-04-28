#!/usr/bin/env python3
"""
Mood Tracker Graphic Generator
Fetches the last 28 days of mood data from a Notion database and generates
a self-contained HTML color-block visualization — ready to host on GitHub Pages.

Run locally:  python generate_mood_graphic.py
On GitHub:    triggered automatically via .github/workflows/update_mood.yml
"""

import os
import requests
from datetime import datetime, timedelta, date

# ---------------------------------------------------------------------------
# CONFIGURATION
# When running locally, you can set these directly below.
# On GitHub Actions, set them as repository secrets (never paste tokens here).
# ---------------------------------------------------------------------------

NOTION_TOKEN      = os.environ.get("NOTION_TOKEN", "PASTE_YOUR_ntn_TOKEN_HERE")
DATABASE_ID       = os.environ.get("NOTION_DATABASE_ID", "350e4f9c7c2d80d9b3bbf28153cf9163")

# These must match the exact property names in your Notion database.
# Open your database, check the column headers, and update if needed.
DATE_PROPERTY     = "Date"
MOOD_PROPERTY     = "Score (1-10)"
SUMMARY_PROPERTY  = "Summary"

# ---------------------------------------------------------------------------
# COLOR PALETTE  (Rocket — mood 1 = darkest, mood 10 = lightest)
# ---------------------------------------------------------------------------

MOOD_COLORS = [
    "#221331",  # 1
    "#451c47",  # 2
    "#691f55",  # 3
    "#921c5b",  # 4
    "#b91657",  # 5
    "#d92847",  # 6
    "#ed503e",  # 7
    "#f47d57",  # 8
    "#f6a47c",  # 9
    "#f7c9aa",  # 10
]

EMPTY_COLOR = "#a9bdc6"

# ---------------------------------------------------------------------------
# NOTION API
# ---------------------------------------------------------------------------

def fetch_mood_data():
    """Query Notion for the last 28 days of entries."""
    today     = date.today()
    start     = today - timedelta(days=27)

    url     = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization":  f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type":   "application/json",
    }
    payload = {
        "filter": {
            "property": DATE_PROPERTY,
            "date": {"on_or_after": start.isoformat()},
        },
        "sorts": [{"property": DATE_PROPERTY, "direction": "ascending"}],
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    entries = {}
    for page in response.json().get("results", []):
        props = page["properties"]

        # Date
        date_prop = props.get(DATE_PROPERTY, {})
        if date_prop.get("type") == "date" and date_prop.get("date"):
            entry_date = date_prop["date"]["start"][:10]
        else:
            continue

        # Mood score (number)
        mood_prop = props.get(MOOD_PROPERTY, {})
        score = mood_prop.get("number") if mood_prop.get("type") == "number" else None

        # Summary (rich text)
        summary_prop = props.get(SUMMARY_PROPERTY, {})
        if summary_prop.get("type") == "rich_text":
            summary = "".join(t.get("plain_text", "") for t in summary_prop.get("rich_text", []))
        else:
            summary = ""

        entries[entry_date] = {"score": score, "summary": summary}

    return entries


# ---------------------------------------------------------------------------
# GRID BUILDER
# ---------------------------------------------------------------------------

def build_grid(entries):
    """Return a list of 28 day-dicts, oldest first, today last."""
    today = date.today()
    days  = []
    for i in range(27, -1, -1):
        d     = today - timedelta(days=i)
        key   = d.isoformat()
        entry = entries.get(key, {})
        score = entry.get("score")
        color = MOOD_COLORS[max(0, min(9, int(score) - 1))] if score is not None else EMPTY_COLOR
        days.append({
            "date":         key,
            "display_date": d.strftime("%b ") + str(d.day),   # cross-platform, no leading zero
            "score":        score,
            "summary":      entry.get("summary", ""),
            "color":        color,
        })
    return days


# ---------------------------------------------------------------------------
# HTML GENERATOR
# ---------------------------------------------------------------------------

def generate_html(days):
    now     = datetime.utcnow()
    updated = now.strftime("%b ") + str(now.day) + now.strftime(", %Y · %H:%M UTC")

    # --- grid cells ---
    cells = ""
    for day in days:
        score_label = str(int(day["score"])) if day["score"] is not None else ""
        tooltip     = day["display_date"]
        if day["score"] is not None:
            tooltip += f" · {score_label}"
        if day["summary"]:
            tooltip += f" · {day['summary']}"

        cells += f"""
    <div class="cell" style="background:{day['color']}" title="{tooltip}">
      <span class="score">{score_label}</span>
    </div>"""

    # --- legend swatches ---
    legend = ""
    for i, c in enumerate(MOOD_COLORS):
        legend += f'<span class="swatch" style="background:{c}" title="Mood {i+1}"></span>'
    legend += f'<span class="swatch empty" style="background:{EMPTY_COLOR}" title="No entry"></span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mood · last 28 days</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body {{ overflow: hidden; }}

    body {{
      background: #120d1e;
      font-family: Georgia, 'Times New Roman', serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 32px 24px;
    }}

    .wrap {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
      width: 100%;
      max-width: 520px;
    }}

    h1 {{
      font-size: 0.75rem;
      font-weight: normal;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: #f6a47c;
      opacity: 0.75;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 7px;
      width: 100%;
    }}

    .cell {{
      aspect-ratio: 1;
      border-radius: 5px;
      cursor: default;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.12s ease, box-shadow 0.12s ease;
      position: relative;
    }}

    .cell:hover {{
      transform: scale(1.15);
      box-shadow: 0 6px 20px rgba(0,0,0,0.6);
      z-index: 10;
    }}

    .score {{
      font-size: 0.6rem;
      color: rgba(255,255,255,0.45);
      pointer-events: none;
      user-select: none;
    }}

    /* custom tooltip */
    .cell::after {{
      content: attr(title);
      position: absolute;
      bottom: calc(100% + 8px);
      left: 50%;
      transform: translateX(-50%);
      background: #221331;
      border: 1px solid #451c47;
      color: #f7c9aa;
      font-size: 0.72rem;
      padding: 5px 10px;
      border-radius: 5px;
      white-space: nowrap;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.1s ease;
      z-index: 20;
    }}

    .cell:hover::after {{
      opacity: 1;
    }}

    .legend {{
      display: flex;
      align-items: center;
      gap: 5px;
    }}

    .swatch {{
      display: inline-block;
      width: 16px;
      height: 16px;
      border-radius: 3px;
    }}

    .empty {{
      margin-left: 6px;
      border: 1px solid rgba(169,189,198,0.3);
    }}

    .updated {{
      font-size: 0.65rem;
      color: #a9bdc6;
      opacity: 0.4;
      letter-spacing: 0.05em;
    }}
  </style>
</head>
<body>
<div class="wrap">
  <h1>mood &mdash; last 28 days</h1>
  <div class="grid">{cells}
  </div>
  <div class="legend">{legend}</div>
  <div class="updated">updated {updated}</div>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Fetching mood data from Notion…")
    entries = fetch_mood_data()
    print(f"  {len(entries)} entries found in the last 28 days")

    days = build_grid(entries)
    html = generate_html(days)

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("  Saved → docs/index.html")
    print("Done.")


if __name__ == "__main__":
    main()
