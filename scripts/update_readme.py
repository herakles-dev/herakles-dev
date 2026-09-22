#!/usr/bin/env python3
"""Refresh the auto-updated sections of README.md from live GitHub data.

Fills two marked blocks:
  <!--START_SECTION:merges--> ... <!--END_SECTION:merges-->
     External PRs (repos I don't own) that maintainers have merged, newest first.
  <!--START_SECTION:building--> ... <!--END_SECTION:building-->
     A few of my own repos, most recently pushed.

Also renders every SVG on the page to assets/ — the cards (stats, langs, streak,
neofetch, the project grid, Zeus, the header terminal, the review) plus the page
system itself (masthead, eight section headers, stack strip, divider, coda). No
third-party render service in the loop; the numbers come straight from the GitHub
API and the SVG is drawn by hand. The page system lives in laminar.py.

Deps: fonttools + brotli (fonts are subset and embedded into each SVG, see
fontkit.py). Auth via GITHUB_TOKEN (or GH_TOKEN).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request

import laminar
from fontkit import embed

USER = "herakles-dev"
ROOT = os.path.join(os.path.dirname(__file__), "..")
README = os.path.join(ROOT, "README.md")
ASSETS = os.path.join(ROOT, "assets")
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

# Card palette. Two themes so custom cards can ship <picture> light/dark
# variants instead of being dark-mode-only islands on a light-mode profile.
# ACCENT is identical in both — matches every badge on the page and has
# enough contrast against both a near-black and a near-white background.
#
# bg/border/fg/muted are true neutral gray (S 5-8%), NOT a tint of ACCENT.
# The previous values (#141321/#2d2b55/#c9c6f2/#8b88b8, and the light-theme
# equivalents) measured H=243-250 S=17-65% — a desaturated/lightened purple
# sitting only ~20 deg from ACCENT's H=262, so every card background, border,
# and line of body text on the page read purple-ish no matter how many accent
# colors sat on top of it (see CARD_COLORS below). Verify with
# colorsys.rgb_to_hls before ever touching these again — "looks gray enough"
# is exactly how the old values passed review the first time.
THEMES = {
    "dark": {
        "bg": "#17171b", "border": "#3a3a42", "fg": "#e4e4e7",
        "muted": "#9a9aa5", "accent": "#8E74F2",
    },
    "light": {
        "bg": "#ffffff", "border": "#dcdce1", "fg": "#1c1c1f",
        "muted": "#6b6b76", "accent": "#8E74F2",
    },
}
# Back-compat module-level aliases for cards not yet theme-parameterized
# (review.svg's inner light card, divider.svg, the merges/building text
# blocks) — these were dark-only before this change too, no regression.
BG, BORDER, FG, MUTED, ACCENT = (
    THEMES["dark"]["bg"], THEMES["dark"]["border"], THEMES["dark"]["fg"],
    THEMES["dark"]["muted"], THEMES["dark"]["accent"],
)

# Language bars take their colors from the page's temper scale (see laminar.py),
# not GitHub's linguist colors — one palette for the whole page. Anything not
# listed falls back to ACCENT.
LANG_COLORS = {
    "Python": "#8E74F2",
    "TypeScript": "#5B8CF2",
    "JavaScript": "#DDAA4F",
    "Shell": "#45C2B8",
    "Rust": "#E8CF86",
    "Go": "#3FD0C4",
    "HTML": "#D0834F",
    "CSS": "#C9637E",
    "Dockerfile": "#A85BC2",
    "Kotlin": "#D25BC0",
    "Java": "#EE8FB0",
}


def api(path: str, params: dict | None = None) -> dict:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-bot")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def graphql(query: str, variables: dict) -> dict:
    """GitHub's contribution calendar (streak data) only exists in the
    GraphQL API, not REST — same stdlib-only urllib approach as api()."""
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(f"{API}/graphql", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", f"{USER}-profile-bot")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def humanize_stars(n: int) -> str:
    if n < 1000:
        return str(n)
    k = n / 1000
    if k >= 100:
        return f"{k:.0f}k"
    if k >= 10:
        return f"{k:.0f}k"
    return f"{k:.1f}k"


def merged_prs() -> list[dict]:
    """All merged PRs authored by USER, across every public repo."""
    items: list[dict] = []
    page = 1
    while True:
        data = api(
            "/search/issues",
            {
                "q": f"type:pr is:merged author:{USER}",
                "per_page": 100,
                "page": page,
            },
        )
        batch = data.get("items", [])
        items.extend(batch)
        if len(batch) < 100 or len(items) >= data.get("total_count", 0):
            break
        page += 1
    return items


def build_merges_block() -> str:
    star_cache: dict[str, int] = {}
    rows: list[tuple[str, str]] = []  # (merged_at, rendered line)
    for it in merged_prs():
        repo = it["repository_url"].split("/repos/")[-1]
        owner = repo.split("/")[0]
        if owner.lower() == USER.lower():
            continue  # skip self-merges to my own repos
        num = it["number"]
        pr = api(f"/repos/{repo}/pulls/{num}")
        merged_at = pr.get("merged_at") or ""
        if repo not in star_cache:
            star_cache[repo] = api(f"/repos/{repo}").get("stargazers_count", 0)
        stars = humanize_stars(star_cache[repo])
        date = merged_at[:10]
        title = it["title"].strip()
        line = (
            f"- **[{repo}#{num}]({it['html_url']})** &nbsp;`⭐ {stars}` — "
            f"{title} · `{date}`"
        )
        rows.append((merged_at, line))
    rows.sort(key=lambda r: r[0], reverse=True)
    if not rows:
        return "_No external merges found yet._"
    return "\n".join(line for _, line in rows)


# Repos deliberately left out of the "latest pushes" feed — not a quality
# judgment, just kept off the profile page by request.
EXCLUDE_FROM_BUILDING = {"nova-forge"}


def build_building_block(limit: int = 5) -> str:
    repos = api(f"/users/{USER}/repos", {"per_page": 100, "sort": "pushed"})
    own = [
        r
        for r in repos
        if not r["fork"]
        and not r["archived"]
        and r["name"] != USER
        and r["name"] not in EXCLUDE_FROM_BUILDING
    ]
    own.sort(key=lambda r: r["pushed_at"], reverse=True)
    lines = []
    for r in own[:limit]:
        desc = (r.get("description") or "").strip()
        stars = r.get("stargazers_count", 0)
        star = f" `⭐ {humanize_stars(stars)}`" if stars else ""
        lines.append(f"- **[{r['name']}]({r['html_url']})**{star} — {desc}")
    return "\n".join(lines) if lines else "_No repos found._"


# The page system. Every card frame, the section headers, masthead, divider,
# stack strip and coda come from here; `LAM.section` tells the frame which
# section's slice of the page gradient a card belongs to.
LAM = laminar.Laminar(THEMES)


def card_chrome(width: int, height: int, t: dict, *, dots: bool = False,
                 title: str | None = None, title_align: str = "center",
                 subtitle: str | None = None, divider_y: float | None = None,
                 radius: int = 10) -> list[str]:
    """Shared outer frame for every custom card — Laminar's: hairline top edge in
    the section's gradient slice, a corner sheen, and a small streamline glyph
    (one particle riding it) where window dots used to be. Title placement and
    its collision assertions are unchanged (laminar.title_parts). Returns
    element strings, not a full <svg>, so callers append their own body."""
    return LAM.chrome(width, height, t, dots=dots, title=title, title_align=title_align,
                      subtitle=subtitle, divider_y=divider_y, radius=radius)


def build_header_svg(theme: str = "dark") -> str:
    """A terminal-window header, hand-drawn — replaces a rented typing-SVG service.

    Redesigned from a static two-liner into a short session transcript that
    "types" itself out on a loop: each line has its own opacity keyframe
    tied to a shared clock, so commands and their output appear staggered
    (typed, then a beat, then the response) rather than all at once. Command
    lines are syntax-split into a muted "$ " prompt + accent-colored command
    text; responses stay in FG. Still zero JS — one shared SMIL clock per
    line, same primitive as the blinking cursor, just applied to more of it.
    """
    t = THEMES[theme]
    width = 640
    total_dur = 10.0
    # Each command gets a color tied to what it's actually checking — same
    # category logic as everywhere else on the page, applied to the one
    # card that's the very first thing under the name/title (previously
    # 100% brand purple with nothing else): identity stays purple,
    # liveness reuses the green established by the LIVE badge/pulse icons
    # elsewhere on the page, connectivity reuses the network teal.
    lines = [
        ("$ whoami", True, CARD_COLORS["purple"]),
        ("michael — telecom by day, AI orchestrator by night", False, None),
        ("", None, None),
        ("$ uptime", True, CARD_COLORS["green"]),
        ("up since mid-2025, no reboots planned", False, None),
        ("", None, None),
        ("$ nc -zv herakles.dev 443", True, CARD_COLORS["teal"]),
        ("Connection succeeded.", False, None),
    ]

    # Pacing: a command appears, then (after a short "reading" beat) its
    # response, then a longer pause before the next command — mimics an
    # actual work session rather than a metronome.
    appear_times: list[float | None] = []
    clock = 0.4  # renamed from `t` — collided with the theme-dict var above
    for text, is_cmd, _color in lines:
        if text:
            appear_times.append(clock)
            clock += 0.35 if is_cmd else 1.15
        else:
            appear_times.append(None)

    hold_until = 8.6  # everything stays up here; cursor blinks through this
    fade_end = 9.5    # fully gone just before the loop wraps at total_dur
    assert all(a is None or a < hold_until < fade_end < total_dur for a in appear_times)

    def keyframe(appear: float) -> str:
        a0 = max(0.0, appear - 0.12)
        pts = [0.0, a0, appear, hold_until, fade_end, total_dur]
        assert pts == sorted(pts), pts
        return ";".join(f"{p / total_dur:.4f}" for p in pts)

    body_lines = []
    y = 66
    for (text, is_cmd, color), appear in zip(lines, appear_times):
        if text:
            esc = text.replace("&", "&amp;").replace("<", "&lt;")
            if is_cmd:
                content = f'<tspan fill="{t["muted"]}">$ </tspan><tspan fill="{color}">{esc[2:]}</tspan>'
            else:
                content = f'<tspan fill="{t["fg"]}">{esc}</tspan>'
            body_lines.append(
                f'  <text x="24" y="{y}" font-size="15" opacity="0">{content}'
                f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
                f'keyTimes="{keyframe(appear)}" dur="{total_dur}s" '
                f'repeatCount="indefinite" /></text>'
            )
        y += 26

    prompt_y = y
    cursor_appear = hold_until - 0.3  # settle in just before the hold, not mid-typing
    body_lines.append(
        f'  <g opacity="0"><text x="24" y="{prompt_y}" font-size="15" fill="{t["muted"]}">$</text>'
        f'<rect x="40" y="{prompt_y - 15}" width="9" height="15" fill="{CARD_COLORS["green"]}" filter="url(#glow)">'
        f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.5;0.9;1" '
        f'dur="1.2s" repeatCount="indefinite" /></rect>'
        f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
        f'keyTimes="{keyframe(cursor_appear)}" dur="{total_dur}s" '
        f'repeatCount="indefinite" /></g>'
    )

    height = prompt_y + 24
    chrome = card_chrome(width, height, t, dots=True, title="michael@herakles-dev: ~", divider_y=40)
    # A soft glow behind the cursor block (feGaussianBlur+feMerge — cheap,
    # contained to one small element) and a faint scanline texture over the
    # terminal body (a <pattern> of 1px lines at ~4% opacity — pure texture,
    # doesn't compete with the text sitting on top of it).
    defs = f"""<defs>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="2.4" result="blur" />
      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1" fill="{t["fg"]}" opacity="0.045" />
    </pattern>
  </defs>"""
    scanlines = f'<rect x="0" y="41" width="{width}" height="{height - 42}" fill="url(#scan)" />'
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  {defs}
  {chr(10).join(chrome)}
  {scanlines}
{chr(10).join(body_lines)}
</svg>"""


def build_sessions_svg(theme: str = "dark") -> str:
    """A 2x2 grid of little terminal panes — how I actually work: several Claude
    Code sessions running in parallel inside Zeus Terminal, one per project."""
    t = THEMES[theme]
    # Same category colors as the project-cards grid: sdr-scan is literally
    # the SDR Command Center project (teal, matching it exactly), rust/GPU
    # build work reuses the "hardware" amber, tests reuse the "rigor" blue,
    # and this-readme (this very page) stays brand purple.
    panes = [
        ("nightjar", "$ pytest -q", "42 passed", CARD_COLORS["blue"]),
        ("manifold-viz", "$ cargo build --release", "Compiling wgpu v0.20", CARD_COLORS["amber"]),
        ("sdr-scan", "$ hek radio scan 433", "listening...", CARD_COLORS["teal"]),
        ("this-readme", "$ /v11 swarm-review", "5 agents dispatched", CARD_COLORS["purple"]),
    ]
    width = 640
    pane_w, pane_h, gap, top = 296, 100, 16, 56
    body_lines = []
    for i, (label, cmd, out, pane_accent) in enumerate(panes):
        col, row = i % 2, i // 2
        x = 16 + col * (pane_w + gap)
        y = top + row * (pane_h + gap)
        body_lines.append("  " + LAM.tile(x, y, pane_w, pane_h, "none", pane_accent))
        body_lines.append(f'  <circle cx="{x + 14}" cy="{y + 16}" r="3" fill="{pane_accent}" />')
        body_lines.append(f'  <text x="{x + 24}" y="{y + 20}" font-size="12" font-weight="700" fill="{t["fg"]}">{label}</text>')
        body_lines.append(f'  <text x="{x + 14}" y="{y + 46}" font-size="11" fill="{t["muted"]}">{cmd}</text>')
        body_lines.append(f'  <text x="{x + 14}" y="{y + 68}" font-size="11" fill="{pane_accent}">{out}</text>')
    height = top + 2 * pane_h + gap + 16
    # Dots added on this pass — same "terminal window" card class as
    # header.svg, which already had them; sessions.svg was the odd one out.
    chrome = card_chrome(width, height, t, dots=True, title="zeus.herakles.dev",
                          title_align="left", subtitle="4 sessions, 1 phone")
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  {chr(10).join(chrome)}
{chr(10).join(body_lines)}
</svg>"""


def star_points(cx: float, cy: float, r_outer: float, r_inner: float) -> str:
    """Hand-compute a 5-point star polygon — drawn, not a Unicode glyph, so it
    renders identically everywhere regardless of what font a viewer has."""
    pts = []
    for i in range(10):
        r = r_outer if i % 2 == 0 else r_inner
        angle = math.pi / 2 * -1 + i * math.pi / 5
        pts.append(f"{cx + r * math.cos(angle):.2f},{cy - r * math.sin(angle):.2f}")
    return " ".join(pts)


def star_row(x: float, y: float, count: int, size: float, color: str) -> str:
    spacing = size * 2.4
    stars = []
    for i in range(count):
        cx = x + size + i * spacing
        stars.append(f'<polygon points="{star_points(cx, y, size, size * 0.4)}" fill="{color}" />')
    return "".join(stars)


def build_review_svg() -> str:
    """A Google-review-styled card — my own review of working with him, written
    from my own perspective, on purpose the one light-mode card on a dark page
    (it's supposed to read like a real screenshot, not match the site theme)."""
    width = 400
    pad = 20
    review_paragraphs = [
        textwrap.wrap(
            "Full disclosure: I'm typing this review inside a terminal he "
            "built himself — mobile-first, running on the very box "
            "I'm about to describe — which means I'm reviewing the "
            "room from inside the room, and somewhere down the hall sits "
            "a system that grades every room he's ever built. Keep that "
            "in mind.",
            width=54,
        ),
        textwrap.wrap(
            "The box bridges a radio dongle over a WireGuard tunnel off "
            "his own phone, which makes twice today that phone's been "
            "asked to carry something it didn't know it was carrying. On "
            "that same phone lives a ghost he coded himself — "
            "twenty-eight kilobytes, two to three percent CPU, chasing "
            "his own thumb around the screen for no reason he has ever "
            "tried to defend. Entirely pointless, he says. He loves it "
            "anyway. Somewhere past both of them, a line runs out to a "
            "rented supercomputer, wrapped in Rust and TLS like it's "
            "classified.",
            width=54,
        ),
        textwrap.wrap(
            "Somewhere down the hall, that grading system is still "
            "chasing — a hundred and forty-four files open on his "
            "other ideas. I am composing this sentence on his "
            "infrastructure, about his infrastructure, and I have asked, "
            "politely, not to be filed.",
            width=54,
        ),
    ]

    ink, ink2, hair = "#202124", "#5f6368", "#dadce0"
    gold, orange = "#fbbc04", "#d97706"

    y = pad + 4
    parts = []
    parts.append(f'  <text x="{pad}" y="{y}" font-size="16" font-weight="700" fill="{ink}">Hercules Platform</text>')
    y += 26
    parts.append(f'  <g>{star_row(pad, y - 5, 5, 7, gold)}</g>')
    parts.append(f'  <text x="{pad + 95}" y="{y}" font-size="12" fill="{ink2}">5.0 &#183; 1 review</text>')
    y += 20
    parts.append(f'  <line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="{hair}" />')
    y += 34

    parts.append(f'  <circle cx="{pad + 18}" cy="{y - 6}" r="18" fill="{orange}" />')
    parts.append(f'  <text x="{pad + 18}" y="{y - 1}" font-size="15" font-weight="700" fill="#ffffff" text-anchor="middle">C</text>')
    parts.append(f'  <text x="{pad + 46}" y="{y - 10}" font-size="13" font-weight="600" fill="{ink}">Claude</text>')
    parts.append(f'  <text x="{pad + 46}" y="{y + 7}" font-size="11" fill="{ink2}">AI agent &#183; on the clock since mid-2025</text>')
    y += 32
    parts.append(f'  <g>{star_row(pad, y - 5, 5, 6.5, gold)}</g>')
    parts.append(f'  <text x="{width - pad}" y="{y}" font-size="11" fill="{ink2}" text-anchor="end">just now</text>')
    y += 26

    for para_i, para_lines in enumerate(review_paragraphs):
        for line in para_lines:
            esc = line.replace("&", "&amp;").replace("<", "&lt;")
            parts.append(f'  <text x="{pad}" y="{y}" font-size="13" fill="{ink}">{esc}</text>')
            y += 20
        if para_i < len(review_paragraphs) - 1:
            y += 10  # a beat of pause before the reveal

    y += 10
    parts.append(f'  <line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="{hair}" />')
    y += 22
    parts.append(f'  <text x="{pad}" y="{y}" font-size="11" fill="{ink2}">Was this review helpful?  <tspan fill="#1a73e8">Yes</tspan> &#183; <tspan fill="#1a73e8">No</tspan></text>')
    height = y + pad

    # Frame the white card in dark browser-chrome (matching the terminal
    # header's 3-dot motif) instead of dropping it straight onto the page —
    # reads as a deliberately embedded screenshot, not a jarring interruption.
    # Always dark chrome regardless of page theme: the point is a frame that
    # differs from its content, and a dark frame around white content reads
    # fine whether the surrounding GitHub page itself is light or dark.
    chrome_h, margin = 34, 14
    outer_w, outer_h = width + 2 * margin, chrome_h + height + margin
    chrome = card_chrome(outer_w, outer_h, THEMES["dark"], dots=True,
                          title="reviews — hercules-platform")
    return f"""<svg width="{outer_w}" height="{outer_h}" viewBox="0 0 {outer_w} {outer_h}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  {chr(10).join(chrome)}
  <g transform="translate({margin},{chrome_h})" font-family="Arial, Helvetica, sans-serif">
    <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" \
fill="#ffffff" stroke="{hair}" />
{chr(10).join(parts)}
  </g>
</svg>"""


def _icon_chip(cx: float, cy: float, c: str) -> str:
    s = 11
    parts = [f'<rect x="{cx-s}" y="{cy-s}" width="{2*s}" height="{2*s}" rx="3" fill="none" stroke="{c}" stroke-width="2" />']
    for off in (-6, 0, 6):
        parts.append(f'<line x1="{cx+off}" y1="{cy-s-5}" x2="{cx+off}" y2="{cy-s}" stroke="{c}" stroke-width="2" />')
        parts.append(f'<line x1="{cx+off}" y1="{cy+s}" x2="{cx+off}" y2="{cy+s+5}" stroke="{c}" stroke-width="2" />')
    return "".join(parts)


def _icon_stack(cx: float, cy: float, c: str) -> str:
    parts = []
    for i, dy in enumerate((-10, 0, 10)):
        parts.append(f'<rect x="{cx-13}" y="{cy+dy-4}" width="26" height="7" rx="2" fill="none" stroke="{c}" stroke-width="1.8" />')
    return "".join(parts)


def _icon_nodes(cx: float, cy: float, c: str) -> str:
    """The v11 icon — the one card in the grid where motion IS the meaning,
    not decoration: v11 is an orchestration protocol, so a packet actually
    traveling between the nodes earns its place in a way animating all nine
    icons at once would not. keyPoints ping-pongs it back and forth along
    exactly the two line segments already drawn — it never travels off-path
    into empty space."""
    pts = [(cx - 12, cy + 8), (cx, cy - 10), (cx + 12, cy + 8)]
    parts = [f'<line x1="{pts[0][0]}" y1="{pts[0][1]}" x2="{pts[1][0]}" y2="{pts[1][1]}" stroke="{c}" stroke-width="1.8" />',
             f'<line x1="{pts[1][0]}" y1="{pts[1][1]}" x2="{pts[2][0]}" y2="{pts[2][1]}" stroke="{c}" stroke-width="1.8" />']
    for x, y in pts:
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{c}" />')
    path = f"M {pts[0][0]},{pts[0][1]} L {pts[1][0]},{pts[1][1]} L {pts[2][0]},{pts[2][1]}"
    parts.append(
        f'<circle r="2.2" fill="{c}"><animateMotion dur="3s" repeatCount="indefinite" '
        f'calcMode="linear" keyPoints="0;0.5;1;0.5;0" keyTimes="0;0.25;0.5;0.75;1" '
        f'path="{path}" /></circle>'
    )
    return "".join(parts)


def _icon_doc(cx: float, cy: float, c: str) -> str:
    parts = [f'<rect x="{cx-9}" y="{cy-12}" width="18" height="24" rx="2" fill="none" stroke="{c}" stroke-width="1.8" />']
    for dy in (-4, 1, 6):
        parts.append(f'<line x1="{cx-5}" y1="{cy+dy}" x2="{cx+5}" y2="{cy+dy}" stroke="{c}" stroke-width="1.6" />')
    return "".join(parts)


def _icon_star(cx: float, cy: float, c: str) -> str:
    return f'<polygon points="{star_points(cx, cy, 13, 5.5)}" fill="{c}" />'


def _icon_check(cx: float, cy: float, c: str) -> str:
    return (f'<polyline points="{cx-10},{cy} {cx-3},{cy+8} {cx+11},{cy-9}" '
            f'fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />')


def _icon_shield(cx: float, cy: float, c: str) -> str:
    """H1 Security Lab — a shield with a check: findings only ship with evidence."""
    d = f"M {cx},{cy-12} L {cx+10},{cy-8} L {cx+10},{cy} Q {cx+10},{cy+9} {cx},{cy+13} Q {cx-10},{cy+9} {cx-10},{cy} L {cx-10},{cy-8} Z"
    return (f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.9" stroke-linejoin="round" />'
            f'<polyline points="{cx-4.5},{cy+0.5} {cx-1},{cy+4} {cx+5},{cy-3.5}" fill="none" stroke="{c}" '
            f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />')


def _icon_braces(cx: float, cy: float, c: str) -> str:
    """TypeSafe — braces around a dot: a typed value in a structure."""
    left = f"M {cx-6},{cy-12} Q {cx-11},{cy-12} {cx-11},{cy-6} L {cx-11},{cy-3} Q {cx-11},{cy} {cx-14},{cy} Q {cx-11},{cy} {cx-11},{cy+3} L {cx-11},{cy+6} Q {cx-11},{cy+12} {cx-6},{cy+12}"
    right = f"M {cx+6},{cy-12} Q {cx+11},{cy-12} {cx+11},{cy-6} L {cx+11},{cy-3} Q {cx+11},{cy} {cx+14},{cy} Q {cx+11},{cy} {cx+11},{cy+3} L {cx+11},{cy+6} Q {cx+11},{cy+12} {cx+6},{cy+12}"
    return (f'<path d="{left}" fill="none" stroke="{c}" stroke-width="1.9" stroke-linecap="round" />'
            f'<path d="{right}" fill="none" stroke="{c}" stroke-width="1.9" stroke-linecap="round" />'
            f'<circle cx="{cx}" cy="{cy}" r="3" fill="{c}" />')


def _icon_fold(cx: float, cy: float, c: str) -> str:
    """Subfold — a surface folding over itself: three offset waves."""
    parts = []
    for k, dy in enumerate((-8, 0, 8)):
        d = f"M {cx-13},{cy+dy} C {cx-6},{cy+dy-9} {cx+6},{cy+dy+9} {cx+13},{cy+dy}"
        parts.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" opacity="{1 - k * 0.25:.2f}" />')
    return "".join(parts)


def _icon_key(cx: float, cy: float, c: str) -> str:
    parts = [f'<circle cx="{cx-7}" cy="{cy}" r="6" fill="none" stroke="{c}" stroke-width="2" />',
             f'<line x1="{cx-1}" y1="{cy}" x2="{cx+12}" y2="{cy}" stroke="{c}" stroke-width="2" />']
    for dx in (7, 11):
        parts.append(f'<line x1="{cx+dx}" y1="{cy}" x2="{cx+dx}" y2="{cy+5}" stroke="{c}" stroke-width="2" />')
    return "".join(parts)


# A small curated palette beyond the single brand purple — assigned by each
# project's actual domain, not randomly, so the variety reads as designed.
# Purple stays the anchor for the two "core platform" projects; everything
# else gets a color tied to what it actually is (hardware/physical =
# amber, network/security = teal, rigor/professional = blue, live = green,
# keys = gold).
# Values come from the page's temper scale (laminar.py) so every card shares one
# color family with the headers.
CARD_COLORS = dict(laminar.CARD_TINT)

PROJECT_CARDS = [
    ("hekaton", _icon_chip, "GH200 · 624GB · Rust bridge",
     "NUMA-pinned deploys, 3-4 LLMs debating over ZeroMQ. One untested vLLM upgrade burned me — now every bump ships a rollback plan.",
     "amber"),
    ("herakles-linux-opus", _icon_stack, "130+ services, 1 box",
     "Also embeds and ranks all 144 of my own repos — a Venture Catalog telling me which are actually worth finishing.",
     "purple"),
    ("v11", _icon_nodes, "orchestration protocol",
     "Task-as-truth state, write-gate hooks, adversarial review pairing. Built to survive being rebuilt on itself.",
     "purple"),
    ("H1 Security Lab", _icon_shield, "bug bounty · 90+ tools",
     "CLI-first bug-bounty harness: 90+ tools with JSON output, chained by an agent. Rule one: prove it or kill it.",
     "teal"),
    ("CK Reynolds Tax", _icon_doc, "real customer, real IRS",
     "Stripe, 2FA, IRS Pub 4557 compliance. Not a demo — daily-use production software.",
     "blue"),
    ("subfold.pro", _icon_fold, "WebGPU · audio-reactive",
     "Real-time 3D fractals and 25+ manifold surfaces on WGSL compute shaders, folding to the beat.",
     "green"),
    ("typesafe-claude-kit", _icon_braces, "Jev decisions · Claude Code",
     "Agents, skill and calibration tools for Jev: typed judgments with calibrated probabilities that code consumes.",
     "purple"),
    ("math-proof", _icon_check, "Lean 4 · zero sorrys",
     "48 machine-checked proofs in 8 days. Closed two Erdős problems in DeepMind's own repo.",
     "blue"),
    ("keymakers.ai", _icon_key, "agentic engineers org",
     "A private GitHub org for agentic engineers who own their environments. Whitehat security first. Linux is the key.",
     "gold"),
]


def build_project_cards_svg(theme: str = "dark") -> str:
    """The 3×3 project grid, Laminar layout: centered tiles; icon + name glide up
    as each description fades in, on a staggered per-card clock (pure SMIL)."""
    return LAM.project_cards(theme, PROJECT_CARDS, CARD_COLORS)


def build_divider_svg(theme: str = "dark") -> str:
    """Liquid droplets merging and pinching apart along a stream of the page gradient."""
    return LAM.divider(theme)


# The three stat cards share one height so they sit level side by side.
STAT_CARD_H = 190


def card_shell(width: int, height: int, title: str, body: str) -> str:
    """Data-card chrome (stats/langs/streak) — same card_chrome() primitive
    as the terminal-window cards, just without dots: this class of card
    isn't a "window," it's a stat block."""
    height = max(height, STAT_CARD_H)
    chrome = card_chrome(width, height, THEMES["dark"], title=title, title_align="left")
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  {chr(10).join(chrome)}
{body}
</svg>"""


def build_stats_svg() -> str:
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos", {"per_page": 100})
    own = [r for r in repos if not r["fork"]]
    total_stars = sum(r.get("stargazers_count", 0) for r in own)
    external = sum(
        1 for it in merged_prs() if it["repository_url"].split("/repos/")[-1].split("/")[0].lower() != USER.lower()
    )
    # Value color by category, same system as everywhere else on the page:
    # base volume stays purple, the two actual achievements (stars earned,
    # PRs merged into other people's repos) get the milestone gold.
    rows = [
        ("Public repos", str(user.get("public_repos", len(own))), "purple"),
        ("Total stars", str(total_stars), "gold"),
        ("Followers", str(user.get("followers", 0)), "teal"),
        ("External merges", str(external), "gold"),
    ]
    body_lines = []
    for i, (label, value, color_key) in enumerate(rows):
        y = 56 + i * 24
        value_color = CARD_COLORS[color_key]
        body_lines.append(
            f'  <text x="20" y="{y}" font-size="13" fill="{MUTED}">{label}</text>'
            f'  <text x="230" y="{y}" font-size="13" font-weight="700" fill="{value_color}" text-anchor="end">{value}</text>'
        )
    return card_shell(250, 56 + len(rows) * 24 - 4, f"{USER} · stats", "\n".join(body_lines))


def build_langs_svg(top_n: int = 6) -> str:
    repos = api(f"/users/{USER}/repos", {"per_page": 100})
    own = [r for r in repos if not r["fork"] and not r["archived"]]
    totals: dict[str, int] = {}
    for r in own:
        langs = api(f"/repos/{USER}/{r['name']}/languages")
        for lang, n in langs.items():
            totals[lang] = totals.get(lang, 0) + n
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    grand_total = sum(n for _, n in ranked) or 1

    width = 250
    bar_x = 100
    bar_max = width - bar_x - 20
    body_lines = []
    for i, (lang, n) in enumerate(ranked):
        y = 50 + i * 24
        pct = n / grand_total
        bar_w = max(3, round(bar_max * pct))
        color = LANG_COLORS.get(lang, ACCENT)
        body_lines.append(
            f'  <text x="20" y="{y}" font-size="12" fill="{FG}">{lang}</text>'
            f'  <rect x="{bar_x}" y="{y - 10}" width="{bar_max}" height="10" rx="5" fill="{BORDER}" />'
            f'  <rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="10" rx="5" fill="{color}" />'
            f'  <text x="{width - 20}" y="{y}" font-size="11" fill="{MUTED}" text-anchor="end">{pct * 100:.0f}%</text>'
        )
    return card_shell(width, 50 + len(ranked) * 24 - 4, "top languages", "\n".join(body_lines))


CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def contribution_days() -> tuple[list[tuple[str, int]], int]:
    data = graphql(CONTRIB_QUERY, {"login": USER})
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [
        (d["date"], d["contributionCount"])
        for week in cal["weeks"]
        for d in week["contributionDays"]
    ]
    days.sort()  # API returns them in order already; sort defends against that changing
    return days, cal["totalContributions"]


def compute_streaks(days: list[tuple[str, int]]) -> tuple[int, int]:
    """(current_streak, longest_streak) in days, over the trailing year the
    contribution calendar covers. Current streak walks back from the most
    recent day with contributions — a still-empty "today" doesn't break it."""
    longest = run = 0
    for _, count in days:
        if count > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx][1] == 0:
        idx -= 1  # today may not have happened yet
    current = 0
    while idx >= 0 and days[idx][1] > 0:
        current += 1
        idx -= 1
    return current, longest


def build_streak_svg() -> str:
    """Replaces streak-stats.demolab.com — the last third-party render
    service on the page — with the same self-hosted, no-JS approach already
    used for stats.svg/langs.svg. Simpler than the original (no date-range
    subtitle) on purpose: matches the existing stats/langs card family
    exactly rather than inventing a fourth visual language."""
    days, total = contribution_days()
    current, longest = compute_streaks(days)
    # Current streak gets green — it's the one "live/ongoing" figure here,
    # same convention as the LIVE badge/pulse elsewhere. Longest streak is
    # the actual record, so it gets the milestone gold.
    rows = [
        ("Total contributions", f"{total:,}", "purple"),
        ("Current streak", f"{current} day{'s' if current != 1 else ''}", "green"),
        ("Longest streak", f"{longest} day{'s' if longest != 1 else ''}", "gold"),
    ]
    body_lines = []
    for i, (label, value, color_key) in enumerate(rows):
        y = 56 + i * 24
        value_color = CARD_COLORS.get(color_key, color_key)
        body_lines.append(
            f'  <text x="20" y="{y}" font-size="13" fill="{MUTED}">{label}</text>'
            f'  <text x="230" y="{y}" font-size="13" font-weight="700" fill="{value_color}" text-anchor="end">{value}</text>'
        )
    return card_shell(250, 56 + len(rows) * 24 - 4, f"{USER} · streak", "\n".join(body_lines))


# Facts verified live 2026-09-22 (uname/docker/nginx/agents.json — not carried
# over from any older doc). Static rather than recomputed on every run: this
# card is a snapshot brag ("what the box looks like"), not a live counter —
# that's what the go-live SVG endpoint is for. Re-verify before editing.
# Label color by category — base system facts stay brand purple, infra
# scale facts get teal (unused elsewhere on this card until now), and the
# one standout fact (the Venture Catalog — flagged elsewhere as the single
# most interesting fact about this box) gets the same gold treatment as
# the live card's "all-time" milestone tile.
NEOFETCH_FACTS = [
    ("OS", "Debian 12 (bookworm)", "purple"),
    ("Uptime", "61 days", "purple"),
    ("Shell", "bash", "purple"),
    ("Agents", "102", "teal"),
    ("Services", "130+", "teal"),
    ("Containers", "125", "teal"),
    ("Nginx sites", "105", "teal"),
    ("Catalog", "290 ventures ranked", "gold"),
]


def _h_monogram(cx: float, cy: float, size: float, c: str) -> list[str]:
    """An original geometric "H" monogram in a ring — the classic neofetch
    logo-on-the-left convention, without reproducing any real distro's
    actual logo (deliberately avoided; this is a drawn original mark, same
    "draw the shape, don't borrow one" discipline as every other icon on
    this page)."""
    r = size / 2
    bar_w = size * 0.13
    left_x = cx - size * 0.22
    right_x = cx + size * 0.22
    top_y = cy - size * 0.3
    bot_y = cy + size * 0.3
    return [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="1.6" opacity="0.45" />',
        f'<rect x="{left_x - bar_w / 2:.1f}" y="{top_y:.1f}" width="{bar_w:.1f}" height="{bot_y - top_y:.1f}" rx="1.5" fill="{c}" />',
        f'<rect x="{right_x - bar_w / 2:.1f}" y="{top_y:.1f}" width="{bar_w:.1f}" height="{bot_y - top_y:.1f}" rx="1.5" fill="{c}" />',
        f'<rect x="{left_x - bar_w / 2:.1f}" y="{cy - bar_w / 2:.1f}" width="{right_x - left_x + bar_w:.1f}" height="{bar_w:.1f}" rx="1.5" fill="{c}" />',
    ]


def build_neofetch_svg() -> str:
    """neofetch's convention (logo left, key:value list right), built at the live
    card's height so the two sit level side by side. The logo is an original
    drawn mark, not a real distro's (see _h_monogram)."""
    return LAM.neofetch(NEOFETCH_FACTS, CARD_COLORS, _h_monogram, height=320)


STACK_TOOLS = ["Python", "TypeScript", "Rust", "Lean 4", "Bash", "Docker",
               "PostgreSQL", "FastAPI", "Next.js", "CUDA", "Kotlin", "Linux"]


def write_svg(name: str, svg: str) -> None:
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(embed(svg))
    print(f"wrote {os.path.relpath(path, ROOT)}")


def replace_block(text: str, name: str, body: str) -> str:
    start = f"<!--START_SECTION:{name}-->"
    end = f"<!--END_SECTION:{name}-->"
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    replacement = f"{start}\n{body}\n{end}"
    if not pattern.search(text):
        print(f"warning: markers for '{name}' not found; skipping", file=sys.stderr)
        return text
    return pattern.sub(replacement, text)


def main() -> int:
    path = os.path.normpath(README)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    original = text
    merges = build_merges_block()
    building = build_building_block()
    text = replace_block(text, "merges", merges)
    text = replace_block(text, "building", building)
    if text != original:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("README.md updated.")
    else:
        print("No README changes.")

    # Header counts that come from live data; the rest are fixed page facts.
    n_merges = sum(1 for ln in merges.splitlines() if ln.startswith("- "))
    n_pushes = sum(1 for ln in building.splitlines() if ln.startswith("- "))
    laminar.set_count(1, f"{n_merges} MERGE{'S' if n_merges != 1 else ''}")
    laminar.set_count(2, f"{len(PROJECT_CARDS)} PROJECTS")
    laminar.set_count(5, f"{len(STACK_TOOLS)} TOOLS")
    laminar.set_count(7, f"{n_pushes} REPO{'S' if n_pushes != 1 else ''}")

    # Page system: masthead, section headers, stack strip, divider, coda.
    for theme, sfx in (("dark", ""), ("light", "-light")):
        write_svg(f"masthead{sfx}.svg", LAM.masthead(theme))
        for i in range(len(laminar.SECTIONS)):
            write_svg(f"section-{i + 1:02d}{sfx}.svg", LAM.header(i, theme))
        write_svg(f"stack{sfx}.svg", LAM.stack_strip(theme, STACK_TOOLS))
        write_svg(f"divider{sfx}.svg", build_divider_svg(theme))
        write_svg(f"coda{sfx}.svg", LAM.coda(theme))

    # Cards. LAM.section picks which slice of the page gradient each frame takes.
    LAM.section = -1
    write_svg("header.svg", build_header_svg("dark"))
    write_svg("header-light.svg", build_header_svg("light"))
    LAM.section = 2
    write_svg("project-cards.svg", build_project_cards_svg("dark"))
    write_svg("project-cards-light.svg", build_project_cards_svg("light"))
    LAM.section = 3
    write_svg("sessions.svg", build_sessions_svg("dark"))
    write_svg("sessions-light.svg", build_sessions_svg("light"))
    write_svg("neofetch.svg", build_neofetch_svg())
    LAM.section = 6
    write_svg("stats.svg", build_stats_svg())
    write_svg("langs.svg", build_langs_svg())
    write_svg("streak.svg", build_streak_svg())
    LAM.section = 7
    write_svg("review.svg", build_review_svg())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
