#!/usr/bin/env python3
"""Tidy release assets uploaded by hand on the web.

    tools/label.py bof22

A file uploaded on the web keeps the name it was given ("40.zip") and has
no label. For a work with `"originals"` (overrides.json:
{"040.zip": "the original file name"}), its unlabelled asset is renamed
to the mirror's name and labelled with the original file name.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def number(name: str):
    m = re.match(r"(\d+)(?:\+(\d+))?\.", name)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def main():
    event = sys.argv[1]
    repo = os.environ["GITHUB_REPOSITORY"]
    works = json.loads(Path(event, "works.json").read_text())
    r = subprocess.run(["gh", "api", f"repos/{repo}/releases/tags/{event}"],
                       capture_output=True, text=True, check=True)
    assets = json.loads(r.stdout)["assets"]
    for w in works:
        for name, original in w.get("originals", {}).items():
            want = number(name)
            for a in assets:
                if a["label"] or number(a["name"]) != want:
                    continue
                subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{repo}/releases/assets/{a['id']}",
                                "-f", f"name={name}", "-f", f"label={original}"],
                               check=True, capture_output=True)
                print(f"{a['name']} -> {name} ({original})")


if __name__ == "__main__":
    main()
