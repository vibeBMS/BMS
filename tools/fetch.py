#!/usr/bin/env python3
"""Download one BMS archive from the places BMS events link to.

    tools/fetch.py URL DIR      -> prints the saved file's path

Google Drive (files and folders), Dropbox, MediaFire, MEGA (megadl from
megatools), OneDrive (newer share links through their page in a headless
browser: tools/browser_download.js) and plain web servers. What arrives must be an
archive (zip, rar, 7z), a single chart file or a movie (a BGA posted on
its own); a web page is an error.
"""

import base64
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
ARCHIVES = (".zip", ".rar", ".7z")
CHARTS = (".bms", ".bme", ".bml", ".pms", ".bmson")
# a BGA posted on its own (an add-on: higher quality movie for the archive)
VIDEOS = (".mp4", ".avi", ".wmv", ".mpg", ".mpeg", ".webm", ".m4v", ".mkv")


class FetchError(Exception):
    pass


def kind(path: Path) -> str:
    """'zip', 'rar', '7z', 'chart', 'video' or '' (from the first bytes)."""
    head = path.open("rb").read(8)
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return "zip"
    if head.startswith(b"Rar!\x1a\x07"):
        return "rar"
    if head.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7z"
    page = head.lstrip().lower().startswith((b"<!doc", b"<html"))
    if path.suffix.lower() in CHARTS and not page:
        return "chart"
    if path.suffix.lower() in VIDEOS and not page:
        return "video"
    return ""


def name_from(resp: requests.Response, url: str) -> str:
    cd = resp.headers.get("content-disposition", "")
    m = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", cd, re.I)
    if m:
        return urllib.parse.unquote(m.group(1).strip('"'))
    m = re.search(r'filename="?([^";]+)"?', cd, re.I)
    if m:
        name = m.group(1)
        try:  # servers often send UTF-8 bytes as latin-1
            name = name.encode("latin-1").decode("utf-8")
        except UnicodeError:
            pass
        return name
    path = urllib.parse.unquote(urllib.parse.urlparse(resp.url or url).path)
    return path.rstrip("/").rsplit("/", 1)[-1] or "download"


def stream(url: str, dest: Path, session=None) -> Path:
    s = session or requests.Session()
    s.headers.setdefault("User-Agent", UA)
    with s.get(url, stream=True, timeout=60, allow_redirects=True) as r:
        if r.status_code != 200:
            raise FetchError(f"HTTP {r.status_code}")
        if r.headers.get("content-type", "").startswith("text/html"):
            raise FetchError("got a web page, not a file")
        out = dest / safe(name_from(r, url))
        with out.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return out


def safe(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", name).strip() or "download"


def drive_id(url: str):
    m = re.search(r"/file/d/([\w-]+)|[?&]id=([\w-]+)", url)
    return (m.group(1) or m.group(2)) if m else None


def gdrive_file(fid: str, dest: Path) -> Path:
    import gdown

    out = gdown.download(id=fid, output=str(dest) + "/", quiet=True)
    if not out:
        raise FetchError("Google Drive refused (quota, or not shared)")
    return Path(out)


def pick_file(names):
    """The archive to take from a folder: ogg over wav, full over BGA-only."""
    def score(n: str) -> int:
        n = n.lower()
        s = 0
        s += 4 if "ogg" in n else 0
        s -= 4 if re.search(r"wav|flac", n) else 0
        s -= 2 if re.search(r"lq|low|lr2|wmv|mpg|lite|compact", n) else 0
        s -= 8 if re.search(r"bga.?only|only.?bga|bga単体|patch|差分|追加", n) else 0
        return s

    return max(names, key=score) if names else None


def gdrive_folder(url: str, dest: Path) -> Path:
    import gdown

    files = gdown.download_folder(url=url, output=str(dest), quiet=True, skip_download=True) or []
    archives = [f for f in files if f.path.lower().endswith(ARCHIVES)]
    if not archives:
        raise FetchError(f"folder holds no archive ({len(files)} files)")
    best = pick_file([f.path for f in archives])
    f = next(f for f in archives if f.path == best)
    return gdrive_file(f.id, dest)


def mediafire(url: str, dest: Path) -> Path:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    page = s.get(url, timeout=60).text
    m = re.search(r'href="(https?://download\d*\.mediafire\.com/[^"]+)"', page)
    if not m:
        raise FetchError("MediaFire page has no download link")
    return stream(m.group(1), dest, s)


def mega(url: str, dest: Path) -> Path:
    before = set(dest.iterdir())
    r = subprocess.run(["megadl", "--no-progress", "--path", str(dest), url],
                       capture_output=True, text=True, timeout=3 * 3600)
    new = [p for p in dest.iterdir() if p not in before]
    if r.returncode != 0 or not new:
        raise FetchError("MEGA: " + (r.stderr.strip().splitlines() or ["failed"])[-1])
    if new[0].is_dir():
        raise FetchError("MEGA link is a folder")
    return new[0]


def onedrive(url: str, dest: Path) -> Path:
    token = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    try:
        return stream(f"https://api.onedrive.com/v1.0/shares/u!{token}/root/content", dest)
    except FetchError:
        pass
    try:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        r = s.get(url, timeout=60, allow_redirects=True)
        # the page's direct link ("download.aspx" or "?download=1")
        u = r.url
        if "onedrive.live.com" in u and "redir" in u:
            u = u.replace("redir", "download")
        elif "sharepoint.com" in u or "1drv.ms" in u:
            u += ("&" if "?" in u else "?") + "download=1"
        out = stream(u, dest, s)
        if kind(out):
            return out
        out.unlink(missing_ok=True)
    except FetchError:
        pass
    # newer share links only download from their page
    return browser(url, dest)


def browser(url: str, dest: Path) -> Path:
    """The share page's Download button, pressed in a headless browser."""
    script = Path(__file__).with_name("browser_download.js")
    r = subprocess.run(["node", str(script), url, str(dest)], capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise FetchError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "browser download failed")
    return Path(r.stdout.strip().splitlines()[-1])


def dropbox(url: str, dest: Path) -> Path:
    u = re.sub(r"([?&])dl=0", r"\1dl=1", url)
    if "dl=1" not in u:
        u += ("&" if "?" in u else "?") + "dl=1"
    return stream(u, dest)


def fetch(url: str, dest: Path) -> Path:
    host = urllib.parse.urlparse(url).netloc.lower()
    if "drive.google.com" in host or "drive.usercontent.google.com" in host or "docs.google.com" in host:
        if "/folders/" in url:
            out = gdrive_folder(url, dest)
        else:
            fid = drive_id(url)
            if not fid:
                raise FetchError("no Google Drive file id")
            out = gdrive_file(fid, dest)
    elif "dropbox" in host:
        out = dropbox(url, dest)
    elif "mediafire.com" in host:
        out = mediafire(url, dest)
    elif "mega.nz" in host or "mega.co.nz" in host:
        out = mega(url, dest)
    elif "1drv.ms" in host or "onedrive" in host or "sharepoint.com" in host:
        out = onedrive(url, dest)
    elif re.search(r"baidu|lanzou|lanzn|lanzoub", host):
        raise FetchError("this host needs an account or a browser")
    else:
        out = stream(url, dest)
    if not kind(out):
        out.unlink(missing_ok=True)
        raise FetchError("not an archive")
    return out


def main():
    url, dest = sys.argv[1], Path(sys.argv[2])
    dest.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=dest))
    try:
        out = fetch(url, tmp)
        final = dest / out.name
        shutil.move(str(out), final)
        print(final)
    except FetchError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
