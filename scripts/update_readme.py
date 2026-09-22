#!/usr/bin/env python3
"""Refresh the auto-updated sections of README.md from live GitHub data.

Fills two marked blocks:
  <!--START_SECTION:merges--> ... <!--END_SECTION:merges-->
     External PRs (repos I don't own) that maintainers have merged, newest first.
  <!--START_SECTION:building--> ... <!--END_SECTION:building-->
     A few of my own repos, most recently pushed.

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
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


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
        print("No changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
