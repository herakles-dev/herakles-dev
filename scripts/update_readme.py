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
import os
import re
import sys
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


def build_building_block(limit: int = 5) -> str:
    repos = api(f"/users/{USER}/repos", {"per_page": 100, "sort": "pushed"})
    own = [
        r
        for r in repos
        if not r["fork"] and not r["archived"] and r["name"] != USER
    ]
    own.sort(key=lambda r: r["pushed_at"], reverse=True)
    lines = []
    for r in own[:limit]:
        desc = (r.get("description") or "").strip()
        stars = r.get("stargazers_count", 0)
        star = f" `⭐ {humanize_stars(stars)}`" if stars else ""
        lines.append(f"- **[{r['name']}]({r['html_url']})**{star} — {desc}")
    return "\n".join(lines) if lines else "_No repos found._"


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

    write_svg("stats.svg", build_stats_svg())
    write_svg("langs.svg", build_langs_svg())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
