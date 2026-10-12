"""Draw the upstream chart at the top of the profile.

Each merged pull request is a line from the day it was opened to the day it
merged, in a lane for its project. Lanes are ordered by the project's stars.
Fixes for bugs that raised no error are marked in amber; the class of every
fix comes from the site's upstream notes, written from the PR descriptions.

It is always dark, on its own background, so it reads the same for viewers
on GitHub's light theme. Nothing in the output depends on today's date: the
axis ends a little after the latest merge, so the file only changes when the
data does. Standard library only.
"""

from datetime import date, datetime, timedelta
from statistics import median

W = 880
PAD = 28  # around the chart, inside its background
X0, X1 = 236, 820  # plot area
TOP = 118  # first lane

# GitHub's dark palette, so on the dark theme the background disappears into
# the page; the amber is the site's accent.
C = dict(bg="#0d1117", ink="#f0f6fc", muted="#9198a1", faint="#656c76", rule="#21262d",
         rail="#262c36", line="#4d5560", quiet="#f0a43a", loud="#9198a1")
QUIET = {"silent", "wrong"}

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def when(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def short(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n < 10_000 else f"{round(n / 1000)}k"


def month_start(d, offset=0):
    y, m = divmod(d.year * 12 + d.month - 1 + offset, 12)
    return date(y, m + 1, 1)


def pack(prs, x, gap):
    """Give each PR a track so lines in one lane never touch."""
    ends = []
    for pr in sorted(prs, key=lambda p: p["start"]):
        a, b = x(pr["start"]), x(pr["end"])
        for i, end in enumerate(ends):
            if a > end + gap:
                ends[i] = b
                pr["track"] = i
                break
        else:
            ends.append(b)
            pr["track"] = len(ends) - 1
    return len(ends)


def render(merged, open_count, stars, classes):
    """merged: search items for merged upstream PRs. stars: repo -> stars.
    classes: "owner/repo#123" -> failure class."""
    c = C

    lanes = {}
    for i in merged:
        repo = i["repository_url"].removeprefix("https://api.github.com/repos/")
        lanes.setdefault(repo, []).append({
            "start": when(i["created_at"]).date(),
            "end": when(i["pull_request"]["merged_at"]).date(),
            "cls": classes.get(f"{repo}#{i['number']}"),
            "days": (when(i["pull_request"]["merged_at"]) - when(i["created_at"])).total_seconds() / 86400,
        })
    order = sorted(lanes, key=lambda r: -stars.get(r, 0))
    prs = [p for r in order for p in lanes[r]]
    quiet = sum(p["cls"] in QUIET for p in prs)
    days = round(median(p["days"] for p in prs))

    first = month_start(min(p["start"] for p in prs))
    last = max(p["end"] for p in prs) + timedelta(days=8)
    span = (last - first).days

    def x(d):
        return X0 + (d - first).days / span * (X1 - X0)

    out = []
    add = out.append

    # Header: the claim on the left, two plain numbers on the right.
    add(f'<text x="0" y="30" font-family="{SANS}" font-size="22" font-weight="600" fill="{c["ink"]}">'
        f'{len(prs)} fixes merged into {len(order)} projects</text>')
    add(f'<text x="0" y="56" font-family="{SANS}" font-size="15" fill="{c["muted"]}">'
        f'<tspan fill="{c["quiet"]}" font-weight="600">{quiet} of them</tspan> fixed bugs that raised no error.</text>')
    for right, big, label in ((W, str(open_count), "in review"),
                              (W - 120, f"{days} day{'s' * (days != 1)}", "median to merge")):
        add(f'<text x="{right}" y="32" text-anchor="end" font-family="{SANS}" font-size="24" font-weight="600" '
            f'fill="{c["ink"]}">{big}</text>')
        add(f'<text x="{right}" y="54" text-anchor="end" font-family="{MONO}" font-size="11" '
            f'fill="{c["faint"]}">{label}</text>')
    add(f'<line x1="0" y1="78" x2="{W}" y2="78" stroke="{c["rule"]}"/>')

    # Lanes, sized to how many lines they need to stack.
    y = TOP
    rows = []
    for repo in order:
        tracks = pack(lanes[repo], x, 9)
        h = max(30, 12 + tracks * 10)
        rows.append((repo, y, h, tracks))
        y += h
    bottom = y

    # Month grid and column heads.
    m = first
    while m <= last:
        gx = x(m)
        add(f'<line x1="{gx:.1f}" y1="{TOP - 8}" x2="{gx:.1f}" y2="{bottom}" stroke="{c["rule"]}"/>')
        if x(m) + 40 < X1:
            add(f'<text x="{gx + 6:.1f}" y="{TOP - 14}" font-family="{MONO}" font-size="11" '
                f'fill="{c["faint"]}">{m.strftime("%b")}</text>')
        m = month_start(m, 1)
    add(f'<text x="0" y="{TOP - 14}" font-family="{MONO}" font-size="11" fill="{c["faint"]}">project</text>')
    add(f'<text x="206" y="{TOP - 14}" text-anchor="end" font-family="{MONO}" font-size="11" '
        f'fill="{c["faint"]}">stars</text>')
    add(f'<text x="{W}" y="{TOP - 14}" text-anchor="end" font-family="{MONO}" font-size="11" '
        f'fill="{c["faint"]}">merged</text>')

    for repo, top, h, tracks in rows:
        mid = top + h / 2
        add(f'<text x="0" y="{mid + 4.5:.1f}" font-family="{MONO}" font-size="13" fill="{c["ink"]}">'
            f'{esc(repo.split("/")[1])}</text>')
        add(f'<text x="206" y="{mid + 4:.1f}" text-anchor="end" font-family="{MONO}" font-size="11.5" '
            f'fill="{c["muted"]}">{short(stars.get(repo, 0))}</text>')
        add(f'<text x="{W}" y="{mid + 4:.1f}" text-anchor="end" font-family="{MONO}" font-size="12" '
            f'fill="{c["muted"]}">{len(lanes[repo])}</text>')
        add(f'<line x1="{X0}" y1="{mid:.1f}" x2="{X1}" y2="{mid:.1f}" stroke="{c["rail"]}" stroke-dasharray="1 4"/>')
        for p in lanes[repo]:
            py = mid + (p["track"] - (tracks - 1) / 2) * 10
            a, b = x(p["start"]), x(p["end"])
            fill = c["quiet"] if p["cls"] in QUIET else c["loud"]
            if b - a > 1:
                add(f'<line x1="{a:.1f}" y1="{py:.1f}" x2="{b:.1f}" y2="{py:.1f}" stroke="{c["line"]}" '
                    f'stroke-width="2" stroke-linecap="round"/>')
                add(f'<circle cx="{a:.1f}" cy="{py:.1f}" r="2" fill="{c["line"]}"/>')
            add(f'<circle cx="{b:.1f}" cy="{py:.1f}" r="4.5" fill="{fill}"/>')

    # Key.
    ky = bottom + 34
    add(f'<line x1="0" y1="{bottom + 12}" x2="{W}" y2="{bottom + 12}" stroke="{c["rule"]}"/>')
    key = [
        (0, f'<circle cx="5" cy="{ky - 4}" r="4.5" fill="{c["quiet"]}"/>', "no error: wrong result or lost data"),
        (262, f'<circle cx="267" cy="{ky - 4}" r="4.5" fill="{c["loud"]}"/>', "crash or performance"),
        (432, f'<line x1="434" y1="{ky - 4}" x2="458" y2="{ky - 4}" stroke="{c["line"]}" stroke-width="2" '
              f'stroke-linecap="round"/><circle cx="434" cy="{ky - 4}" r="2" fill="{c["line"]}"/>', "opened to merged"),
    ]
    for kx, mark, label in key:
        add(mark)
        add(f'<text x="{kx + (34 if kx == 432 else 16)}" y="{ky}" font-family="{MONO}" font-size="11" '
            f'fill="{c["muted"]}">{label}</text>')
    add(f'<text x="{W}" y="{ky}" text-anchor="end" font-family="{MONO}" font-size="11" '
        f'fill="{c["faint"]}">redrawn daily from the GitHub API</text>')

    height = ky + 18
    label = (f"{len(prs)} fixes merged into {len(order)} open-source projects, {quiet} of them for bugs that "
             f"raised no error. Median {days} days from opening a pull request to merge; {open_count} more in review.")
    w, h = W + 2 * PAD, round(height + 2 * PAD - 8)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title>\n'
            f'<rect width="{w}" height="{h}" rx="8" fill="{c["bg"]}"/>\n<g transform="translate({PAD} {PAD})">\n'
            + "\n".join(out) + "\n</g>\n</svg>\n")
