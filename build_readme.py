"""Rewrite the auto-updated parts of README.md from the GitHub API.

Run by .github/workflows/update.yml every day. Fills the sections between
<!-- name starts --> and <!-- name ends --> markers; everything outside them
is hand-written and left alone. Standard library only.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

USER = "r0h1tb"
README = Path(__file__).parent / "README.md"

# Own projects shown under "Building", in this order. Dates come from the API.
BUILDING = [
    ("r0h1tb/splitlint", "finds the Unicode bugs in RAG text splitters"),
    ("r0h1tb/plumb", "makes AI coding agents prove a task is actually done"),
    ("r0h1tb/r0h1tb.github.io", "my site: a failure lab, retrieval with evals"),
]
# Contributed to heavily, but not upstream in the "other people's code" sense.
MAIN_CONTRIB = "lexasub/raged"


def get(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def search_prs(query):
    q = urllib.parse.quote(f"author:{USER} is:pr {query}")
    items = []
    for page in range(1, 6):
        data = get(f"/search/issues?q={q}&per_page=100&page={page}")
        items += data["items"]
        if len(items) >= data["total_count"] or not data["items"]:
            break
    return items


def repo_of(item):
    return item["repository_url"].removeprefix("https://api.github.com/repos/")


def tidy(title):
    """'fix(html): extract definition lists' -> 'extract definition lists'."""
    title = re.sub(r"^\[[^\]]+\]\s*", "", title)
    title = re.sub(r"^[\w./-]+(\([^)]*\))?!?:\s*", "", title)
    # Titles like "extract <figure> content" would otherwise render as HTML.
    return title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def short_date(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %d").replace(" 0", " ")


def replace(text, name, body):
    pattern = re.compile(rf"(<!-- {name} starts -->).*?(<!-- {name} ends -->)", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"marker '{name}' missing from README.md")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(2)}", text)


def main():
    merged = [
        i for i in search_prs("is:merged")
        if not repo_of(i).startswith(f"{USER}/") and repo_of(i) != MAIN_CONTRIB
    ]
    merged.sort(key=lambda i: i["pull_request"]["merged_at"], reverse=True)
    open_prs = [i for i in search_prs("is:open") if not repo_of(i).startswith(f"{USER}/")]
    open_prs.sort(key=lambda i: i["created_at"], reverse=True)
    contrib = [i for i in search_prs(f"is:merged repo:{MAIN_CONTRIB}")]

    def line(i, when):
        name = repo_of(i).split("/")[1]
        return f"[{name} #{i['number']}]({i['html_url']}) {tidy(i['title'])} <sub>{short_date(when)}</sub>"

    text = README.read_text()
    text = replace(text, "merged", "<br>\n".join(line(i, i["pull_request"]["merged_at"]) for i in merged[:6]))
    text = replace(text, "review", "<br>\n".join(line(i, i["created_at"]) for i in open_prs[:6]))

    building = []
    for full, what in BUILDING:
        pushed = get(f"/repos/{full}")["pushed_at"]
        building.append(f"[{full.split('/')[1]}](https://github.com/{full}) {what} <sub>updated {short_date(pushed)}</sub>")
    building.append(
        f"[raged](https://github.com/{MAIN_CONTRIB}/pulls?q=is%3Apr+author%3A{USER}+is%3Amerged) "
        f"code search for AI agents, {len(contrib)} of my PRs merged"
    )
    text = replace(text, "building", "<br>\n".join(building))

    # No date here: it would change daily and force a commit with nothing new in it.
    projects = len({repo_of(i) for i in merged})
    text = replace(
        text,
        "totals",
        f"<sub>{len(merged)} fixes merged into {projects} projects · {len(open_prs)} in review · "
        f"kept current daily by [a script](build_readme.py), not by hand</sub>",
    )
    README.write_text(text)


if __name__ == "__main__":
    main()
