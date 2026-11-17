#!/usr/bin/env python3
"""Write <event>/index.json: each work with the release assets that hold it.

    tools/index.py bof22 > index.json

    [{"num": 42, "title": ..., "artist": ..., "team": ..., "page": ...,
      "files": [{"name": "042.zip", "url": ..., "size": ..., "original": ...}]}]

An asset uploaded by hand has no label; the work's `"originals"` (from
overrides.json: {"040.zip": "the original file name"}) names its file.

Works without files (not mirrored yet, or only downloadable by hand)
keep their `links` so a player can download from the authors. Where
`<event>/links.jsonl` (what each link gave: `bmseeker event check`, the
"Check links" workflow) knows them, the links that bring the song itself
come first, then those not checked yet, pages, and failing ones; gone
links (404 / 410) are left out, and add-ons (charts without their sounds,
差分) are listed apart in `"addons"`:

    {..., "links": [the song's, in the order to try], "addons": [...]}
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def order(links, checks):
    """(links to try for the song, in order; add-ons), by what each gave."""
    def rank(u):
        c = checks.get(u)
        if c is None:
            return 1  # not checked yet
        ok = c["state"] in ("archive", "chart")
        if ok and c.get("kind") == "main":
            return 0
        return {"page": 2, "error": 3}.get(c["state"], 9)
    song = [u for u in links if rank(u) < 9]
    song.sort(key=rank)  # stable: the scraped order among equals
    addons = [u for u in links
              if checks.get(u, {}).get("kind") == "addon"
              and checks[u]["state"] in ("archive", "chart")]
    return song, addons


def read_checks(event):
    """URL -> its check: <event>/links.jsonl (records), else the older
    links.json (an object by URL)."""
    lines = Path(event, "links.jsonl")
    if lines.exists():
        recs = [json.loads(l) for l in lines.read_text().splitlines() if l.strip()]
        return {r["url"]: r for r in recs}
    old = Path(event, "links.json")
    return json.loads(old.read_text()) if old.exists() else {}


def main():
    event = sys.argv[1]
    works = json.loads(Path(event, "works.json").read_text())
    checks = read_checks(event)
    charts = any(e["tag"] == event and e.get("charts")
                 for e in json.loads(Path("events.json").read_text()))
    r = subprocess.run(["gh", "release", "view", event, "--json", "assets"],
                       capture_output=True, text=True, check=True)
    by_num = {}
    for a in json.loads(r.stdout)["assets"]:
        m = re.match(r"(\d+)(?:\+(\d+))?\.", a["name"])
        if m:
            by_num.setdefault(int(m.group(1)), []).append((int(m.group(2) or 0), a))
    out = []
    for w in works:
        if w.get("kind") == "Disq":
            continue
        files = [
            {"name": a["name"], "url": a["url"], "size": a["size"],
             "original": a.get("label") or w.get("originals", {}).get(a["name"]) or a["name"]}
            for _, a in sorted(by_num.get(w["num"], []), key=lambda x: x[0])
        ]
        e = {k: w[k] for k in ("num", "title", "artist", "team", "kind", "page")}
        e["files"] = files
        if not files:
            # the chosen archive first, then its add-ons, then the others
            first = w.get("main", []) + [u for g in w.get("extra", []) for u in g]
            links = first + [l["url"] for l in w["links"] if l["url"] not in first]
            # links a source found for it that work (`event check --search`);
            # not for an event of separate charts (they bring the song)
            links += [u for u, c in checks.items()
                      if not charts and c.get("num") == w["num"] and c.get("source")
                      and c["state"] in ("archive", "chart") and u not in links]
            e["links"], addons = order(links, checks)
            if addons:
                e["addons"] = addons
        out.append(e)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
