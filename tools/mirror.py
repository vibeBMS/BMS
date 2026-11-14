#!/usr/bin/env python3
"""Copy an event's archives into its GitHub release, unchanged.

    tools/mirror.py bof22 --shard 3/10 [--hours 5]

For each work in <event>/works.json (disqualified ones skipped) whose
asset is not in release <event> yet: download the main archive (trying
its mirrors in turn) and each add-on, then upload them as

    042.zip      main archive of work No.42
    042+1.rar    its first add-on

with the original file name as the asset's label. Needs `gh` with a token
that can write releases. Prints a Markdown report (also to
$GITHUB_STEP_SUMMARY).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import FetchError, fetch, kind  # noqa: E402

LIMIT = 2 * 1024**3 - 1  # GitHub: each release asset below 2 GiB


def gh(*args, check=True):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


def assets(tag: str) -> set:
    r = gh("release", "view", tag, "--json", "assets", check=False)
    if r.returncode != 0:
        sys.exit(f"release {tag}: {r.stderr.strip()}")
    return {a["name"] for a in json.loads(r.stdout)["assets"]}


def has(existing: set, stem: str) -> bool:
    return any(n.rsplit(".", 1)[0] == stem for n in existing)


def get_one(urls, work_dir: Path):
    """The first of `urls` that downloads, and the errors before it."""
    errors = []
    for u in urls:
        try:
            return fetch(u, work_dir), errors
        except FetchError as e:
            errors.append(f"{u.split('/')[2]}: {e}")
        except Exception as e:  # a host changed its pages, a timeout...
            errors.append(f"{u.split('/')[2]}: {type(e).__name__}: {e}")
    return None, errors


def upload(tag: str, path: Path, stem: str) -> str:
    ext = {"zip": "zip", "rar": "rar", "7z": "7z"}.get(kind(path)) or path.suffix.lstrip(".").lower()
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
    a = ap.parse_args()
    i, n = map(int, a.shard.split("/"))
    deadline = time.time() + a.hours * 3600
    works = json.loads(Path(a.event, "works.json").read_text())
    only = {int(x) for x in a.only.split(",")} if a.only else None
    existing = assets(a.event)
    done, failed, skipped = [], [], []
    for w in works:
        num = w["num"]
        if num % n != i or (only and num not in only):
            continue
        if w.get("kind") == "Disq":
            continue
        jobs = [(f"{num:03}", w["main"])] + [(f"{num:03}+{k}", urls) for k, urls in enumerate(w["extra"], 1)]
        for stem, urls in jobs:
            if has(existing, stem):
                continue
            if time.time() > deadline:
                skipped.append(stem)
                continue
            tmp = Path(tempfile.mkdtemp())
            try:
                path, errors = get_one(urls, tmp)
                if path is None:
                    failed.append((stem, w["title"], "; ".join(errors) or "no link"))
                elif path.stat().st_size > LIMIT:
                    failed.append((stem, w["title"], f"{path.stat().st_size >> 20} MiB is over the 2 GiB asset limit"))
                else:
                    name = upload(a.event, path, stem)
                    done.append((name, w["title"], path.name))
                    print(f"{name}  {path.name}", flush=True)
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
