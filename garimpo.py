# -*- coding: utf-8 -*-
"""
garimpo - searches GitHub for projects related to what you are building and hands you a short list.
("Garimpo" is Portuguese for prospecting: sifting a lot of gravel for a little gold.)

  python garimpo.py            run the searches in themes.txt and write found/YYYY-MM-DD.md
  python garimpo.py --all      also list what already showed up in earlier runs

How it works:
  - each line of themes.txt is one search on GitHub's public API (read-only, no account, nothing installed);
  - seen.json remembers every repository that ever showed up, with its star count on each run;
  - the list of the day only has what is NEW or what GREW a lot since last time;
  - the order comes from a simple score: stars (log scale), stars per day of life, recent activity and growth.

What it does NOT do: download, install or run anything it finds, or tell you whether a project is any good.
Stars can be bought and a README promises whatever it wants. The list is where reading starts, not a recommendation.
"""
import json, math, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(HERE, "seen.json")
MIN_STARS = 60
MAX_STARS = 60000                # above this everybody already knows it: not prospecting
ALIVE_DAYS = 90                  # pushed to within this many days
PER_SEARCH = 20
PER_THEME = 6                    # how many make the list, per theme
GROWTH = 0.10                    # an already seen repository comes back if it grew this much (and at least 100 stars)


def themes(path=None):
    out = []
    with open(path or os.path.join(HERE, "themes.txt"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                theme, query = line.split("|", 1)
                if theme.strip() and query.strip():
                    out.append((theme.strip().upper(), query.strip()))
    return out


def query_for(q, today=None):
    """The full GitHub search string for one line of themes.txt."""
    today = today or date.today()
    if q.lower().startswith("@new"):                              # "@new 7" = created in the last 7 days, any subject
        days = int((q.split() + ["7"])[1])
        return "created:>=%s stars:>=%d archived:false" % ((today - timedelta(days=days)).isoformat(), MIN_STARS)
    since = (today - timedelta(days=ALIVE_DAYS)).isoformat()
    return "%s in:name,description,topics stars:%d..%d pushed:>=%s archived:false" % (q, MIN_STARS, MAX_STARS, since)


def search(q):
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query_for(q), "sort": "stars", "order": "desc", "per_page": PER_SEARCH})
    head = {"User-Agent": "garimpo", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):                            # optional: only raises the searches-per-minute limit
        head["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=head), timeout=25) as r:
                return json.loads(r.read().decode()).get("items", [])
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):                              # unauthenticated limit: 10 searches per minute
                time.sleep(35)
                continue
            raise
    return []


def score(r, grew, now=None):
    now = now or datetime.now()
    idle = (now - datetime.strptime(r["pushed_at"][:10], "%Y-%m-%d")).days
    age = max((now - datetime.strptime(r["created_at"][:10], "%Y-%m-%d")).days, 14)
    pace = r["stargazers_count"] / age                            # stars per day of life: a young project climbing beats an old one standing still
    return round(math.log10(max(r["stargazers_count"], 1)) * 10 + min(pace, 60) * 0.8 + max(0, 30 - idle) * 0.5
                 + min(max(grew, 0), 5000) ** 0.5 * 0.6, 1)


def is_link_list(r):
    label = (r["full_name"] + " " + (r.get("description") or "")).lower()
    return "awesome" in label or "curated list" in label or "a list of" in label


def collect(theme_list, search_fn=search, pause=7, log=print):
    found = {}
    for i, (theme, q) in enumerate(theme_list):
        try:
            items = search_fn(q)
        except Exception as e:
            log("  search failed (%s): %s" % (type(e).__name__, q))
            continue
        log("  %-12s %-50s %d" % (theme[:12], q[:50], len(items)))
        for r in items:
            if is_link_list(r):                                   # a list of links is not a tool
                continue
            found.setdefault(r["full_name"], {"r": r, "themes": set()})["themes"].add(theme)
        if pause and i < len(theme_list) - 1:
            time.sleep(pause)                                     # stays under 10 searches per minute
    return found


def select(found, seen, today, show_all=False):
    """Updates `seen` in place and returns today's rows, best first."""
    rows = []
    for name, a in found.items():
        r, before = a["r"], seen.get(name)
        grew = r["stargazers_count"] - before["stars"][-1][1] if before else 0
        new = before is None
        climbed = bool(before) and grew >= max(100, before["stars"][-1][1] * GROWTH)
        v = seen.setdefault(name, {"first_seen": today, "stars": [], "themes": []})
        if not v["stars"] or v["stars"][-1][0] != today:
            v["stars"] = (v["stars"] + [[today, r["stargazers_count"]]])[-12:]
        v["themes"] = sorted(set(v["themes"]) | a["themes"])
        if show_all or new or climbed:
            rows.append({"name": name, "url": r["html_url"], "desc": (r.get("description") or "").strip()[:220],
                         "stars": r["stargazers_count"], "grew": grew, "new": new, "language": r.get("language") or "?",
                         "license": ((r.get("license") or {}).get("spdx_id") or "no license"), "pushed": r["pushed_at"][:10],
                         "created": r["created_at"][:10], "themes": sorted(a["themes"]), "score": score(r, grew)})
    rows.sort(key=lambda x: -x["score"])
    return rows


def by_theme(rows):
    out, used = {}, set()
    for x in rows:                                                # each repository appears once, under the first theme with room
        for t in x["themes"]:
            if x["name"] not in used and len(out.setdefault(t, [])) < PER_THEME:
                out[t].append(x)
                used.add(x["name"])
    return {t: v for t, v in out.items() if v}


def markdown(groups, n_searches, n_seen, first_run, today):
    L = ["# Garimpo, %s" % today, "",
         "%d searches, %d repositories seen, up to %d per theme (%s)." % (
             n_searches, n_seen, PER_THEME, "first run: everything is new" if first_run else "only what is new or grew"), "",
         "A list to read, not to install. Stars can be bought; what counts is reading the code and seeing if the idea is useful.", ""]
    for theme in sorted(groups):
        L += ["## " + theme, ""]
        for x in groups[theme]:
            L += ["### [%s](%s)" % (x["name"], x["url"]), x["desc"] or "(no description)",
                  "- %s stars%s · %s · %s · pushed %s · created %s%s" % (
                      format(x["stars"], ","), (" (+%d since last time)" % x["grew"]) if x["grew"] > 0 else "",
                      x["language"], x["license"], x["pushed"], x["created"],
                      (" · also in " + ", ".join(t for t in x["themes"] if t != theme)) if len(x["themes"]) > 1 else ""), ""]
    if not groups:
        L += ["Nothing new since the last run.", ""]
    return "\n".join(L)


def run(show_all=False):
    try:
        with open(SEEN, encoding="utf-8") as f:
            seen = json.load(f)
    except (OSError, ValueError):
        seen = {}
    today, first_run = date.today().isoformat(), not seen
    ts = themes()
    found = collect(ts)
    groups = by_theme(select(found, seen, today, show_all))
    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=0)
    os.makedirs(os.path.join(HERE, "found"), exist_ok=True)
    out = os.path.join(HERE, "found", today + ".md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown(groups, len(ts), len(found), first_run, today))
    print("\n%d on the list -> %s" % (sum(len(v) for v in groups.values()), out))
    return out


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
    else:
        run("--all" in sys.argv)
