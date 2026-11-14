#!/usr/bin/env python3
"""Write <event>/index.json: each work with the release assets that hold it.

    tools/index.py bof22 > index.json

    [{"num": 42, "title": ..., "artist": ..., "team": ..., "page": ...,
      "files": [{"name": "042.zip", "url": ..., "size": ..., "original": ...}]}]

Works without files (not mirrored yet, or only downloadable by hand)
keep their `links` so a player can send people to the original pages.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    event = sys.argv[1]
    works = json.loads(Path(event, "works.json").read_text())
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
            {"name": a["name"], "url": a["url"], "size": a["size"], "original": a.get("label") or a["name"]}
            for _, a in sorted(by_num.get(w["num"], []), key=lambda x: x[0])
        ]
        e = {k: w[k] for k in ("num", "title", "artist", "team", "kind", "page")}
        e["files"] = files
        if not files:
            e["links"] = [l["url"] for l in w["links"]]
        out.append(e)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
