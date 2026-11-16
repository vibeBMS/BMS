#!/usr/bin/env python3
"""Copy an event's archives into its GitHub release, unchanged.

    tools/mirror.py bof22 --shard 3/10 [--hours 5]

For each work in <event>/works.json (disqualified ones skipped) whose
asset is not in release <event> yet: download the main archive (its
links in turn, then those "Check links" found for it elsewhere and saw
work -- <event>/links.jsonl records with its "num" and a "source" --
then BMS SEARCH's for the song) and each add-on with
`bmseeker link get` (vibeBMS/vibe, on the PATH) -- where a link only gives
a page, in a headless browser (tools/browser_download.js) -- then upload
them as

    042.zip      main archive of work No.42
    042+1.rar    its first add-on

with the original file name as the asset's label. Needs `gh` with a token
that can write releases. Prints a Markdown report (also to
$GITHUB_STEP_SUMMARY).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LIMIT = 2 * 1024**3 - 1  # GitHub: each release asset below 2 GiB


def gh(*args, check=True):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def assets(tag: str) -> set:
    r = gh("release", "view", tag, "--json", "assets", check=False)
    if r.returncode != 0:
        sys.exit(f"release {tag}: {r.stderr.strip()}")
    return {a["name"] for a in json.loads(r.stdout)["assets"]}


def has(existing: set, stem: str) -> bool:
    # by number: a file uploaded by hand may be "40.zip" for "040"
    key = tuple(int(x) for x in stem.split("+"))
    for n in existing:
        m = re.match(r"(\d+)(?:\+(\d+))?\.", n)
        if m and (int(m.group(1)),) + ((int(m.group(2)),) if m.group(2) else ()) == key:
            return True
    return False


def found_links(event: str) -> dict:
    """Work number -> the links "Check links" found for it elsewhere (BMS
    SEARCH, the community archive) that gave the song, with their source."""
    path = Path(event, "links.jsonl")
    out = {}
    for line in path.read_text().splitlines() if path.exists() else []:
        if not line.strip():
            continue
        c = json.loads(line)
        if (c.get("source") and c.get("num") is not None
                and c.get("state") in ("archive", "chart") and c.get("kind", "main") == "main"):
            out.setdefault(c["num"], []).append((c["url"], c["source"]))
    return out


def get_one(urls, work, work_dir: Path, search: bool, third_party: bool):
    """`bmseeker link get`: (the file, its format, the link it came from) or
    None, and the errors of the links that failed."""
    cmd = ["bmseeker", "--json", "link", "get", *urls, "-o", f"{work_dir}/", "--any",
           "--title", work["title"], "--artist", work["artist"]]
    if third_party:
        cmd.append("--third-party")
    if search:
        cmd.append("--search")
    if not urls and not search:
        return None, ["no link"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4 * 3600)
        out = json.loads(r.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, IndexError, json.JSONDecodeError) as e:
        return None, [f"bmseeker: {type(e).__name__} {e}"]
    errors = out.get("errors", [])
    if "file" in out:
        return (Path(out["file"]), out["format"], out["link"]), errors
    got, more = browser(out.get("pages", []), work_dir, any_file=not search)
    return got, errors + more


def kind(path: Path) -> str:
    """'zip', 'rar', '7z', or '' (from the first bytes)."""
    head = path.open("rb").read(8)
    for magic, k in ((b"PK\x03\x04", "zip"), (b"PK\x05\x06", "zip"),
                     (b"Rar!\x1a\x07", "rar"), (b"7z\xbc\xaf\x27\x1c", "7z")):
        if head.startswith(magic):
            return k
    return ""


def browser(pages, work_dir: Path, any_file: bool):
    """The first of `pages` a browser downloads a file from (an archive;
    `any_file`: anything but a page), as `get_one` gives it."""
    if not pages:
        return None, []
    script = Path(__file__).with_name("browser_download.js")
    errors = []
    for u in pages:
        try:
            r = subprocess.run(["node", str(script), u, str(work_dir)],
                               capture_output=True, text=True, timeout=3600)
        except subprocess.TimeoutExpired:
            errors.append(f"{u} (browser): timeout")
            continue
        if r.returncode != 0:
            errors.append(f"{u} (browser): {(r.stderr.strip().splitlines() or ['failed'])[-1]}")
            continue
        path = Path(r.stdout.strip().splitlines()[-1])
        fmt = kind(path)
        page = path.open("rb").read(512).lstrip().startswith(b"<")
        if fmt or (any_file and not page):
            return (path, fmt or "file", u), errors
        path.unlink(missing_ok=True)
        errors.append(f"{u} (browser): not an archive")
    return None, errors


def upload(tag: str, path: Path, fmt: str, stem: str) -> str:
    ext = fmt if fmt in ("zip", "rar", "7z") else path.suffix.lstrip(".").lower()
    name = f"{stem}.{ext}"
    target = path.with_name(name)
    path.rename(target)
    gh("release", "upload", tag, f"{target}#{path.name}", "--clobber")
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("event")
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--hours", type=float, default=5.0)
    ap.add_argument("--only", help="comma separated work numbers")
    ap.add_argument("--replace", action="store_true",
                    help="download --only works again and replace their assets")
    ap.add_argument("--third-party", action="store_true",
                    help="third parties' copies too (dead uploaders' mirrors, the community archive)")
    a = ap.parse_args()
    i, n = map(int, a.shard.split("/"))
    deadline = time.time() + a.hours * 3600
    works = json.loads(Path(a.event, "works.json").read_text())
    only = {int(x) for x in a.only.split(",")} if a.only else None
    existing = assets(a.event)
    found = found_links(a.event)
    done, failed, skipped = [], [], []
    for w in works:
        num = w["num"]
        if num % n != i or (only and num not in only):
            continue
        if w.get("kind") == "Disq":
            continue
        # the song: its own links, then those found for it that worked
        elsewhere = [u for u, _ in found.get(num, []) if u not in w["main"]]
        jobs = [(f"{num:03}", w["main"] + elsewhere)] + [(f"{num:03}+{k}", urls) for k, urls in enumerate(w["extra"], 1)]
        for stem, urls in jobs:
            if has(existing, stem) and not (a.replace and only):
                continue
            if time.time() > deadline:
                skipped.append(stem)
                continue
            tmp = Path(tempfile.mkdtemp())
            try:
                # the song's archive may be found elsewhere; an add-on not
                got, errors = get_one(urls, w, tmp, search="+" not in stem,
                                      third_party=a.third_party)
                if got is None:
                    failed.append((stem, w["title"], "; ".join(errors) or "no link"))
                    continue
                path, fmt, link = got
                if path.stat().st_size > LIMIT:
                    failed.append((stem, w["title"], f"{path.stat().st_size >> 20} MiB is over the 2 GiB asset limit"))
                else:
                    name = upload(a.event, path, fmt, stem)
                    source = dict(found.get(num, [])).get(link)
                    via = ("" if link in w["main"] or "+" in stem
                           else f" ({source}: {link})" if source
                           else f" (BMS SEARCH: {link})")
                    done.append((name, w["title"], path.name + via))
                    print(f"{name}  {path.name}{via}", flush=True)
            except subprocess.CalledProcessError as e:
                failed.append((stem, w["title"], f"upload: {e.stderr.strip()[:200]}"))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    lines = [f"### {a.event} shard {a.shard}", "",
             f"{len(done)} uploaded, {len(failed)} failed, {len(skipped)} left for the next run", ""]
    if failed:
        lines += ["| asset | title | why |", "|---|---|---|"]
        lines += [f"| {s} | {t} | {why} |" for s, t, why in failed]
    report = "\n".join(lines) + "\n"
    print(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(report)
    Path(f"failed-{i}.json").write_text(json.dumps(failed, ensure_ascii=False))


if __name__ == "__main__":
    main()
