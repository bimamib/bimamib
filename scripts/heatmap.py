
#!/usr/bin/env python3
"""
GitHub Contribution Heatmap
- A year in blue heading
- Refreshed daily label
- Month labels above the calendar
- Weekday labels on the left
- Less / More contribution legend
- Roboto and Roboto Mono embedded in SVG
- Light and dark mode support
- Animated contribution cells
"""

import base64
import datetime
import functools
import os
import re
import sys
import urllib.request


# ============================================================
# CONFIGURATION
# ============================================================

USER = os.environ.get("GH_PROFILE_USER", "bimamib")

OUT = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "contrib-heatmap.svg"
    )
)


# ============================================================
# FONT CONFIGURATION
# ============================================================

SANS = "'Roboto', sans-serif"
MONO = "'Roboto Mono', monospace"

FONTS = [
    (
        SANS,
        "font-family:'Roboto';font-weight:400",
        "roboto@5.2.8/latin-400-normal"
    ),
    (
        'font-weight="700"',
        "font-family:'Roboto';font-weight:700",
        "roboto@5.2.8/latin-700-normal"
    ),
    (
        MONO,
        "font-family:'Roboto Mono';font-weight:600",
        "roboto-mono@5.2.8/latin-600-normal"
    ),
]


def get(url):
    headers = {
        "User-Agent": "profile-heatmap-bot/1.0"
    }

    request = urllib.request.Request(
        url,
        headers=headers
    )

    return urllib.request.urlopen(
        request,
        timeout=30
    ).read()


@functools.lru_cache(maxsize=None)
def font(file):
    data = get(
        f"https://cdn.jsdelivr.net/fontsource/fonts/{file}.woff2"
    )

    return base64.b64encode(data).decode("ascii")


# ============================================================
# CONTRIBUTION COLORS
# ============================================================

DARK = [
    "#161b22",
    "#102a56",
    "#174ea6",
    "#2563eb",
    "#60a5fa",
]

LIGHT = [
    "#ebedf0",
    "#dbeafe",
    "#93c5fd",
    "#3b82f6",
    "#1d4ed8",
]


# ============================================================
# HEATMAP DIMENSIONS
# ============================================================

CELL = 13
STEP = 16

LEFT_W = 34

# Header and calendar positioning
HEADER_H = 48
MONTH_H = 24

GRID_TOP = HEADER_H + MONTH_H

BOTTOM_H = 36

COL_T = 0.065
ROW_T = 0.036


# ============================================================
# SVG CSS
# ============================================================

CSS = (
    # Main heading
    ".heading{"
    "font-family:Georgia,serif;"
    "font-size:30px;"
    "font-weight:400;"
    "fill:var(--heading)"
    "}"

    ".heading-blue{"
    "fill:#315efb;"
    "font-style:italic"
    "}"

    # Refreshed daily
    ".refreshed{"
    "font-family:'Roboto Mono',monospace;"
    "font-size:13px;"
    "font-weight:600;"
    "letter-spacing:1.2px;"
    "fill:#7d8590"
    "}"

    # Month and weekday labels
    ".lbl{"
    "fill:#7d8590;"
    "font-size:13px;"
    "font-weight:600"
    "}"

    # Total contributions
    ".total{"
    "fill:var(--total);"
    "font-size:13px;"
    "font-weight:700"
    "}"

    # Legend
    ".legend-label{"
    "fill:#7d8590;"
    "font-family:'Roboto Mono',monospace;"
    "font-size:12px;"
    "font-weight:600"
    "}"

    # Contribution cells
    ".c{"
    "transform-box:fill-box;"
    "transform-origin:center;"
    "opacity:0;"
    "animation:pop .55s ease-out both"
    "}"

    ".g{"
    "animation:pop .55s ease-out both,"
    "flash .7s ease-out both"
    "}"

    # Animation
    "@keyframes pop{"
    "0%{opacity:0;transform:scale(.2)}"
    "60%{opacity:1;transform:scale(1.1)}"
    "100%{opacity:1;transform:scale(1)}"
    "}"

    "@keyframes flash{"
    "0%,45%{filter:brightness(2.4)}"
    "100%{filter:brightness(1)}"
    "}"

    # Dark mode
    ":root{"
    "--heading:#1f2328;"
    "--total:#1f2328"
    "}"

    + "".join(
        f".l{i}{{fill:{c}}}"
        for i, c in enumerate(DARK)
    )

    # Light mode
    + "@media (prefers-color-scheme:light){"

    ":root{"
    "--heading:#1f2328;"
    "--total:#1f2328"
    "}"

    + "".join(
        f".l{i}{{fill:{c}}}"
        for i, c in enumerate(LIGHT)
    )

    + "}"

    # Accessibility
    "@media (prefers-reduced-motion:reduce){"
    ".c{opacity:1!important;animation:none!important}"
    "}"
)


# ============================================================
# FETCH CONTRIBUTION DATA
# ============================================================

def fetch_days():

    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions",
        headers={
            "User-Agent": "profile-readme-bot/1.0"
        }
    )

    page = urllib.request.urlopen(
        req,
        timeout=30
    ).read().decode()

    cells = {}

    # Extract calendar cells
    for td in re.findall(
        r"<td[^>]*ContributionCalendar-day[^>]*>",
        page
    ):

        date, cid, lvl = (
            re.search(
                rf'{a}="([^"]*)"',
                td
            )
            for a in (
                "data-date",
                "id",
                "data-level"
            )
        )

        if date and cid:

            cells[cid.group(1)] = {
                "date": date.group(1),
                "level": int(
                    lvl.group(1)
                ) if lvl else 0,
                "count": 0
            }

    # Extract contribution counts
    for cid, text in re.findall(
        r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>',
        page
    ):

        m = re.match(
            r"(\d[\d,]*)",
            text
        )

        if cid in cells and m:

            cells[cid]["count"] = int(
                m.group(1).replace(",", "")
            )

    if not cells:

        sys.exit(
            "no calendar cells found -- github markup may have changed"
        )

    return sorted(
        cells.values(),
        key=lambda d: d["date"]
    )


# ============================================================
# RENDER SVG
# ============================================================

def render(days):

    first = datetime.date.fromisoformat(
        days[0]["date"]
    )

    # Sunday = row 0
    cols = [
        [None] * ((first.weekday() + 1) % 7)
    ]

    for d in days:

        if len(cols[-1]) == 7:
            cols.append([])

        cols[-1].append(d)

    # SVG dimensions
    w = LEFT_W + len(cols) * STEP + 6

    h = (
        GRID_TOP
        + 7 * STEP
        + BOTTOM_H
    )

    p = []

    # --------------------------------------------------------
    # HEADER: A YEAR IN BLUE
    # --------------------------------------------------------

    p.append(
        '<text class="heading" '
        'x="12" y="35">'
        'A year '
        '<tspan class="heading-blue">in blue</tspan>'
        '</text>'
    )

    # --------------------------------------------------------
    # HEADER: REFRESHED DAILY
    # --------------------------------------------------------

    p.append(
        f'<text class="refreshed" '
        f'x="{w - 12}" '
        f'y="34" '
        f'text-anchor="end">'
        f'REFRESHED DAILY'
        f'</text>'
    )

    # --------------------------------------------------------
    # MONTH LABELS
    # Positioned above the contribution calendar
    # --------------------------------------------------------

    prev = None

    for ci, col in enumerate(cols):

        date = datetime.date.fromisoformat(
            next(
                c for c in col if c
            )["date"]
        )

        if date.month != prev and (
            prev or date.day <= 7
        ):

            p.append(
                f'<text class="lbl" '
                f'font-family="{MONO}" '
                f'font-weight="600" '
                f'x="{LEFT_W + ci * STEP}" '
                f'y="{HEADER_H + 16}">'
                f'{date:%b}'
                f'</text>'
            )

        prev = date.month

    # --------------------------------------------------------
    # WEEKDAY LABELS
    # Positioned on the left side
    # --------------------------------------------------------

    for ri, name in [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]:

        p.append(
            f'<text class="lbl" '
            f'font-family="{MONO}" '
            f'font-weight="600" '
            f'x="2" '
            f'y="{GRID_TOP + ri * STEP + 11}">'
            f'{name}'
            f'</text>'
        )

    # --------------------------------------------------------
    # CONTRIBUTION CELLS
    # --------------------------------------------------------

    for ci, col in enumerate(cols):

        for ri, d in enumerate(col):

            if d:

                s = "" if d["count"] == 1 else "s"

                cls = (
                    f'c g l{d["level"]}'
                    if d["count"]
                    else "c l0"
                )

                p.append(
                    f'<rect class="{cls}" '
                    f'x="{LEFT_W + ci * STEP}" '
                    f'y="{GRID_TOP + ri * STEP}" '
                    f'width="{CELL}" '
                    f'height="{CELL}" '
                    f'rx="2.5" '
                    f'style="animation-delay:'
                    f'{ci * COL_T + ri * ROW_T:.3f}s">'
                    f'<title>{d["date"]}: '
                    f'{d["count"]} contribution{s}'
                    f'</title>'
                    f'</rect>'
                )

    # --------------------------------------------------------
    # TOTAL CONTRIBUTIONS
    # --------------------------------------------------------

    total = sum(
        d["count"]
        for d in days
    )

    p.append(
        f'<text class="total" '
        f'font-family="{SANS}" '
        f'font-weight="700" '
        f'x="{LEFT_W}" '
        f'y="{h - 7}">'
        f'{total:,} contributions in the last year'
        f'</text>'
    )

    # --------------------------------------------------------
    # LESS / MORE LEGEND
    # --------------------------------------------------------

    legend_y = h - 19
    legend_cell = 13
    legend_step = 17

    legend_width = 163
    legend_x = w - legend_width

    p.append(
        f'<text class="legend-label" '
        f'x="{legend_x}" '
        f'y="{legend_y + 11}">'
        f'Less'
        f'</text>'
    )

    # Five contribution level boxes
    for i in range(5):

        p.append(
            f'<rect class="l{i}" '
            f'x="{legend_x + 40 + i * legend_step}" '
            f'y="{legend_y}" '
            f'width="{legend_cell}" '
            f'height="{legend_cell}" '
            f'rx="2.5"/>'
        )

    p.append(
        f'<text class="legend-label" '
        f'x="{legend_x + 40 + 5 * legend_step + 5}" '
        f'y="{legend_y + 11}">'
        f'More'
        f'</text>'
    )

    # --------------------------------------------------------
    # EMBED FONTS
    # --------------------------------------------------------

    body = "".join(p)

    faces = "".join(
        f"@font-face{{{desc};"
        f"src:url(data:font/woff2;base64,{font(file)}) "
        f"format('woff2')}}"
        for needle, desc, file in FONTS
        if needle in body
    )

    # --------------------------------------------------------
    # FINAL SVG
    # --------------------------------------------------------

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" '
        f'font-family="{SANS}">'
        f'<style>{faces}{CSS}</style>'
        f'{body}'
        f'</svg>'
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    days = fetch_days()

    svg = render(days)

    with open(
        OUT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(svg)

    total = sum(
        d["count"]
        for d in days
    )

    print(
        f"wrote {OUT}: {len(days)} days, "
        f"{total} contributions"
    )
