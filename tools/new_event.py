#!/usr/bin/env python3
"""Start the folders of events new in events.json.

    tools/new_event.py bof22 ...

For each event: `<event>/works.json` from its venue (`bmseeker event works
<venue>`, with `<event>/overrides.json` if there is one), unless there is
one already; and `<event>/RELEASE.md`, the release's notes, unless there
is one already. Prints the files it wrote. Needs `bmseeker` on the PATH
for a new works.json.
"""

import json
import subprocess
import sys
from pathlib import Path

VENUE = "https://manbow.nothing.sh/event/event.cgi?action=List_def&event={}"


def notes(e: dict) -> str:
    venue = f"[event venue]({VENUE.format(e['venue'])})" if e.get("venue") else "event venue"
    if e.get("mirror"):
        return (
            f"Entries of {e['title']}, as their authors published them (unmodified archives).\n\n"
            f"- `NNN.zip` / `.rar` / `.7z`: work No.NNN on the {venue}; the original file name is shown as the label.\n"
            "- `NNN+K.*`: an add-on the author published separately.\n"
            "- `index.json`: every work with its files.\n\n"
            "Redistribution follows the event's rules (see the README). Authors: to have a work removed, "
            "open an issue. 削除をご希望の作者の方は Issue でお知らせください。\n"
        )
    return (
        f"Index of the entries of {e['title']}: no archives are mirrored here.\n\n"
        f"`index.json` lists every work on the {venue} with the authors' own download links, "
        "for players such as vibeBMS to open them.\n"
    )


def works(e: dict, folder: Path) -> list:
    if not e.get("venue"):
        sys.exit(f"{e['tag']}: no venue number in events.json to read its works from")
    cmd = ["bmseeker", "event", "works", str(e["venue"])]
    if (folder / "overrides.json").exists():
        cmd += ["--overrides", str(folder / "overrides.json")]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    recs = [json.loads(l) for l in out.splitlines() if l.strip()]
    if not recs:
        sys.exit(f"{e['tag']}: venue {e['venue']} lists no works")
    return recs


def main():
    events = {e["tag"]: e for e in json.loads(Path("events.json").read_text())}
    for tag in sys.argv[1:]:
        e = events.get(tag) or sys.exit(f"{tag}: not in events.json")
        folder = Path(tag)
        folder.mkdir(exist_ok=True)
        if not (folder / "works.json").exists():
            text = json.dumps(works(e, folder), ensure_ascii=False, indent=1) + "\n"
            (folder / "works.json").write_text(text)
            print(folder / "works.json")
        if not (folder / "RELEASE.md").exists():
            (folder / "RELEASE.md").write_text(notes(e))
            print(folder / "RELEASE.md")


if __name__ == "__main__":
    main()
