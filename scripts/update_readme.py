#!/usr/bin/env python3
"""Refresh the auto-updated sections of README.md from live GitHub data.

Fills two marked blocks:
  <!--START_SECTION:merges--> ... <!--END_SECTION:merges-->
     External PRs (repos I don't own) that maintainers have merged, newest first.
  <!--START_SECTION:building--> ... <!--END_SECTION:building-->
     A few of my own repos, most recently pushed.

Also renders two self-hosted SVG cards to assets/ (stats.svg, langs.svg) — replaces
the old github-readme-stats.vercel.app cards, which go down whenever that shared
free-tier deployment is paused. No third-party render service in the loop; the
numbers come straight from the GitHub API and the SVG is drawn by hand below.

No third-party deps — standard library only. Auth via GITHUB_TOKEN (or GH_TOKEN).
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

USER = "herakles-dev"
ROOT = os.path.join(os.path.dirname(__file__), "..")
README = os.path.join(ROOT, "README.md")
ASSETS = os.path.join(ROOT, "assets")
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

# Card palette — matches the tokyonight streak/typing cards already in the README.
BG = "#141321"
BORDER = "#2d2b55"
FG = "#c9c6f2"
MUTED = "#8b88b8"
ACCENT = "#a78bfa"

# GitHub linguist colors for languages that actually show up on this account.
# Anything not listed here falls back to ACCENT rather than guessing wrong.
LANG_COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178C6",
    "JavaScript": "#f1e05a",
    "Shell": "#89e051",
    "Rust": "#dea584",
    "Go": "#00ADD8",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Dockerfile": "#384d54",
    "Kotlin": "#A97BFF",
    "Java": "#b07219",
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


def build_header_svg() -> str:
    """A terminal-window header, hand-drawn — replaces a rented typing-SVG service.

    Static text (no third-party render dependency, nothing to clip on a narrow
    viewport) plus one SMIL-animated blinking cursor, which is well-supported even
    inside an <img> embed.
    """
    width = 640
    lines = [
        ("$ whoami", MUTED),
        ("michael — telecom by day, AI orchestrator by night", FG),
        ("", None),
        ("$ history | tail -1", MUTED),
        ("The engineering mindset stuck. The credential didn't.", FG),
    ]
    body_lines = []
    y = 66
    for text, color in lines:
        if text:
            esc = text.replace("&", "&amp;").replace("<", "&lt;")
            body_lines.append(f'  <text x="24" y="{y}" font-size="15" fill="{color}">{esc}</text>')
        y += 26
    body_lines.append(f'  <text x="24" y="{y}" font-size="15" fill="{MUTED}">$</text>')
    body_lines.append(
        f'  <rect x="40" y="{y - 15}" width="9" height="15" fill="{ACCENT}">'
        f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.5;0.9;1" '
        f'dur="1.2s" repeatCount="indefinite" /></rect>'
    )
    height = y + 24  # bottom margin below the last (cursor) line
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" \
fill="{BG}" stroke="{BORDER}" />
  <circle cx="24" cy="24" r="5" fill="{BORDER}" />
  <circle cx="42" cy="24" r="5" fill="{BORDER}" />
  <circle cx="60" cy="24" r="5" fill="{BORDER}" />
  <text x="{width / 2}" y="28" font-size="12" fill="{MUTED}" text-anchor="middle">michael@herakles-dev: ~</text>
  <line x1="0" y1="40" x2="{width}" y2="40" stroke="{BORDER}" />
{chr(10).join(body_lines)}
</svg>"""


def build_sessions_svg() -> str:
    """A 2x2 grid of little terminal panes — how I actually work: several Claude
    Code sessions running in parallel inside Zeus Terminal, one per project."""
    panes = [
        ("nightjar", "$ pytest -q", "42 passed"),
        ("manifold-viz", "$ cargo build --release", "Compiling wgpu v0.20"),
        ("sdr-scan", "$ hek radio scan 433", "listening..."),
        ("this-readme", "$ /v11 swarm-review", "5 agents dispatched"),
    ]
    width = 640
    pane_w, pane_h, gap, top = 296, 100, 16, 56
    body_lines = []
    for i, (label, cmd, out) in enumerate(panes):
        col, row = i % 2, i // 2
        x = 16 + col * (pane_w + gap)
        y = top + row * (pane_h + gap)
        body_lines.append(f'  <rect x="{x}" y="{y}" width="{pane_w}" height="{pane_h}" rx="6" fill="none" stroke="{BORDER}" />')
        body_lines.append(f'  <circle cx="{x + 14}" cy="{y + 16}" r="3" fill="{ACCENT}" />')
        body_lines.append(f'  <text x="{x + 24}" y="{y + 20}" font-size="12" font-weight="700" fill="{FG}">{label}</text>')
        body_lines.append(f'  <text x="{x + 14}" y="{y + 46}" font-size="11" fill="{MUTED}">{cmd}</text>')
        body_lines.append(f'  <text x="{x + 14}" y="{y + 68}" font-size="11" fill="{ACCENT}">{out}</text>')
    height = top + 2 * pane_h + gap + 16
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" \
fill="{BG}" stroke="{BORDER}" />
  <text x="20" y="30" font-size="13" font-weight="700" fill="{ACCENT}">zeus.herakles.dev</text>
  <text x="{width - 20}" y="30" font-size="11" fill="{MUTED}" text-anchor="end">4 sessions, 1 phone</text>
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

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="Arial, Helvetica, sans-serif">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" \
fill="#ffffff" stroke="{hair}" />
{chr(10).join(parts)}
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
    pts = [(cx - 12, cy + 8), (cx, cy - 10), (cx + 12, cy + 8)]
    parts = [f'<line x1="{pts[0][0]}" y1="{pts[0][1]}" x2="{pts[1][0]}" y2="{pts[1][1]}" stroke="{c}" stroke-width="1.8" />',
             f'<line x1="{pts[1][0]}" y1="{pts[1][1]}" x2="{pts[2][0]}" y2="{pts[2][1]}" stroke="{c}" stroke-width="1.8" />']
    for x, y in pts:
        parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{c}" />')
    return "".join(parts)


def _icon_rings(cx: float, cy: float, c: str) -> str:
    parts = [f'<circle cx="{cx}" cy="{cy}" r="2" fill="{c}" />']
    for r in (7, 12):
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="1.6" opacity="{1 - r / 16:.2f}" />')
    return "".join(parts)


def _icon_doc(cx: float, cy: float, c: str) -> str:
    parts = [f'<rect x="{cx-9}" y="{cy-12}" width="18" height="24" rx="2" fill="none" stroke="{c}" stroke-width="1.8" />']
    for dy in (-4, 1, 6):
        parts.append(f'<line x1="{cx-5}" y1="{cy+dy}" x2="{cx+5}" y2="{cy+dy}" stroke="{c}" stroke-width="1.6" />')
    return "".join(parts)


def _icon_mesh(cx: float, cy: float, c: str) -> str:
    pts = [(cx - 12, cy - 8), (cx + 10, cy - 10), (cx - 8, cy + 9), (cx + 12, cy + 8), (cx, cy)]
    edges = [(0, 4), (1, 4), (2, 4), (3, 4), (0, 1)]
    parts = []
    for a, b in edges:
        parts.append(f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}" stroke="{c}" stroke-width="1.4" opacity="0.7" />')
    for x, y in pts:
        parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{c}" />')
    return "".join(parts)


def _icon_star(cx: float, cy: float, c: str) -> str:
    return f'<polygon points="{star_points(cx, cy, 13, 5.5)}" fill="{c}" />'


def _icon_check(cx: float, cy: float, c: str) -> str:
    return (f'<polyline points="{cx-10},{cy} {cx-3},{cy+8} {cx+11},{cy-9}" '
            f'fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />')


def _icon_grid(cx: float, cy: float, c: str) -> str:
    parts = []
    s = 8
    for dx in (-s - 2, s + 2):
        for dy in (-s - 2, s + 2):
            parts.append(f'<rect x="{cx+dx-s/2}" y="{cy+dy-s/2}" width="{s}" height="{s}" rx="1.5" fill="none" stroke="{c}" stroke-width="1.6" />')
    return "".join(parts)


def _icon_key(cx: float, cy: float, c: str) -> str:
    parts = [f'<circle cx="{cx-7}" cy="{cy}" r="6" fill="none" stroke="{c}" stroke-width="2" />',
             f'<line x1="{cx-1}" y1="{cy}" x2="{cx+12}" y2="{cy}" stroke="{c}" stroke-width="2" />']
    for dx in (7, 11):
        parts.append(f'<line x1="{cx+dx}" y1="{cy}" x2="{cx+dx}" y2="{cy+5}" stroke="{c}" stroke-width="2" />')
    return "".join(parts)


PROJECT_CARDS = [
    ("hekaton", _icon_chip, "GH200 · 624GB · Rust bridge",
     "NUMA-pinned deploys, 3-4 LLMs debating over ZeroMQ. One untested vLLM upgrade burned me — now every bump ships a rollback plan."),
    ("herakles-linux-opus", _icon_stack, "130+ services, 1 box",
     "Also embeds and ranks all 144 of my own repos — a Venture Catalog telling me which are actually worth finishing."),
    ("v11", _icon_nodes, "orchestration protocol",
     "Task-as-truth state, write-gate hooks, adversarial review pairing. Built to survive being rebuilt on itself."),
    ("SDR Command Center", _icon_rings, "RTL-SDR · WireGuard",
     "Live FFT waterfall, remote scans across four ISM bands, tunneled home from a Pixel 6a."),
    ("CK Reynolds Tax", _icon_doc, "real customer, real IRS",
     "Stripe, 2FA, IRS Pub 4557 compliance. Not a demo — daily-use production software."),
    ("Reticulum", _icon_mesh, "off-grid mesh · LoRa",
     "A Raspberry Pi node running 24/7 for an emergency that's never come. Nobody assigned this one."),
    ("Fiber Tree v2", _icon_grid, "PostGIS · 30 tables",
     "Spatial pathfinding and loss-budget calculations for real fiber builds. Ten years of telecom work, encoded."),
    ("math-proof", _icon_check, "Lean 4 · zero sorrys",
     "48 machine-checked proofs in 8 days. Closed two Erdős problems in DeepMind's own repo."),
    ("keymakers.ai", _icon_key, "launching",
     "Key duplication by mail, computer vision doing the matching. keymakers-core + keymakers-club, genuinely early."),
]


def build_project_cards_svg() -> str:
    """A grid of self-animating project cards — icon + name stay put, the
    lower half crossfades between a one-line tag and the fuller description on
    a staggered per-card loop. Pure SMIL, same non-interactive-but-self-
    animating trick as the header cursor and the marquee: an <img>-loaded SVG
    can't do :hover, but it can run its own clock forever."""
    cols, rows = 3, 3
    card_w, card_h, gap, outer = 192, 170, 16, 16
    width = outer * 2 + cols * card_w + (cols - 1) * gap
    height = outer * 2 + rows * card_h + (rows - 1) * gap

    cards_svg = []
    for i, (name, icon_fn, tag, desc) in enumerate(PROJECT_CARDS):
        col, row = i % cols, i // cols
        cx0 = outer + col * (card_w + gap)
        cy0 = outer + row * (card_h + gap)
        mid_x = cx0 + card_w / 2

        card = [f'<rect x="{cx0}" y="{cy0}" width="{card_w}" height="{card_h}" rx="10" fill="{BG}" stroke="{BORDER}" />']
        card.append(icon_fn(mid_x, cy0 + 26, ACCENT))
        # Names are all <=20 chars by construction — single line, fixed y.
        esc_name = name.replace("&", "&amp;").replace("<", "&lt;")
        card.append(f'<text x="{mid_x}" y="{cy0 + 55}" font-size="12.5" font-weight="700" fill="{FG}" text-anchor="middle">{esc_name}</text>')

        begin = f'{i * 0.9:.1f}s'
        tag_esc = tag.replace("&", "&amp;").replace("<", "&lt;")
        card.append(
            f'<g><text x="{mid_x}" y="{cy0 + 92}" font-size="11" fill="{MUTED}" '
            f'text-anchor="middle">{tag_esc}</text>'
            f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.4;0.5;0.9;1" '
            f'dur="9s" begin="{begin}" repeatCount="indefinite" /></g>'
        )
        # Fixed top-anchored start regardless of line count (verified worst
        # case: 5 lines at width=28 still lands well clear of the bottom
        # edge) — no backward-from-bottom math that silently breaks if a
        # description gets edited longer later.
        desc_lines = textwrap.wrap(desc, width=28)[:5]
        desc_group = ['<g opacity="0">']
        dy = cy0 + 80
        for line in desc_lines:
            esc = line.replace("&", "&amp;").replace("<", "&lt;")
            desc_group.append(f'<text x="{cx0 + 14}" y="{dy}" font-size="10.5" fill="{MUTED}">{esc}</text>')
            dy += 13
        desc_group.append(
            f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.4;0.5;0.9;1" '
            f'dur="9s" begin="{begin}" repeatCount="indefinite" /></g>'
        )
        card.append("".join(desc_group))
        cards_svg.append("\n    ".join(card))

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  {chr(10).join(f'<g>{c}</g>' for c in cards_svg)}
</svg>"""



def build_divider_svg() -> str:
    width, height = 640, 12
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="fade" x1="0" x2="1">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0" />
      <stop offset="50%" stop-color="{ACCENT}" stop-opacity="0.8" />
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0" />
    </linearGradient>
  </defs>
  <circle cx="{width / 2}" cy="{height / 2}" r="3" fill="{ACCENT}" />
  <rect x="0" y="{height / 2 - 0.75}" width="{width}" height="1.5" fill="url(#fade)" />
</svg>"""


def card_shell(width: int, height: int, title: str, body: str) -> str:
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" \
xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono',ui-monospace,monospace">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" \
fill="{BG}" stroke="{BORDER}" />
  <text x="20" y="30" font-size="14" font-weight="700" fill="{ACCENT}">{title}</text>
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
    rows = [
        ("Public repos", str(user.get("public_repos", len(own)))),
        ("Total stars", str(total_stars)),
        ("Followers", str(user.get("followers", 0))),
        ("External merges", str(external)),
    ]
    body_lines = []
    for i, (label, value) in enumerate(rows):
        y = 56 + i * 24
        body_lines.append(
            f'  <text x="20" y="{y}" font-size="13" fill="{MUTED}">{label}</text>'
            f'  <text x="230" y="{y}" font-size="13" font-weight="700" fill="{FG}" text-anchor="end">{value}</text>'
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


def write_svg(name: str, svg: str) -> None:
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
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
    text = replace_block(text, "merges", build_merges_block())
    text = replace_block(text, "building", build_building_block())
    if text != original:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("README.md updated.")
    else:
        print("No README changes.")

    write_svg("header.svg", build_header_svg())
    write_svg("project-cards.svg", build_project_cards_svg())
    write_svg("sessions.svg", build_sessions_svg())
    write_svg("review.svg", build_review_svg())
    write_svg("divider.svg", build_divider_svg())
    write_svg("stats.svg", build_stats_svg())
    write_svg("langs.svg", build_langs_svg())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
