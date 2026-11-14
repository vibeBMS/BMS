#!/usr/bin/env python3
"""Make <event>/works.json from a manbow BMS event venue.

    tools/scrape_manbow.py 152 bof22

Reads the venue's URL list (every work with its download links) and its
work list (which works are disqualified). For each work it guesses which
link is the main archive (a marked high quality one over a low quality
one, then ogg over wav and a file over a folder) and which links are separate add-on archives
(added charts); mirrors of the same archive are kept as fallbacks.
`<event>/overrides.json` replaces the guess for a work:

    {"25": {"main": ["https://..."], "extra": [["https://..."]], "note": "..."}}

Works the guess was unsure about get `"review": "<why>"`.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://manbow.nothing.sh/event/event.cgi"
UA = "Mozilla/5.0 (vibeBMS archive; +https://github.com/vibeBMS/bms)"


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("cp932", "replace")


def text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


MIRROR = re.compile(r"mirror|ミラー|予備|backup|alt\b|サブ|sub\b", re.I)
EXTRA = re.compile(
    r"追加|差分|add|append|extra|patch|修正|update|fix|bonus|dp譜面|dp chart|別譜面|譜面のみ|charts? only|new \w* ?charts?",
    re.I,
)
# a full package, though its label speaks of a fix or an update
FULL = re.compile(
    r"new ?(ver|link|package|upload|download)|^\W*new\W*$|最新|latest|fixed ?ver|complete|^\W*本体|recommend|推奨|以降はこちら",
    re.I,
)
# a package with its fixes and additions in ("本体(差分適用済)")
APPLIED = re.compile(r"適用済|applied|includ|同梱|込み|全部入り", re.I)
# for those who downloaded an earlier version: a patch
EARLIER = re.compile(r"以前に.{0,24}(dl|ダウンロード)|before .{0,24}download|for package before", re.I)
AGAIN = re.compile(r"再度|もう一度|re-?download", re.I)
# what only adds to a package ("差分のみ", "BGA only")
ADDON_ONLY = re.compile(r"のみ|だけ|only|単体|差分|patch|sabun", re.I)
# HQ / LQ marks outweigh the audio format: an HQ wav beats an LQ ogg
GOOD = [
    # the newer of an old and a new version
    (re.compile(r"new ?(ver|link|package|upload|download)|^\W*new\W*$|最新|latest|fixed|修正版|recommend|推奨|以降はこちら|updated", re.I), 3),
    (re.compile(r"hq|高画質|高品質|high ?quality", re.I), 6),
    (re.compile(r"ogg", re.I), 4),
    (re.compile(r"high|beatoraja|mp4|full|完全", re.I), 2),
]
BAD = [
    (re.compile(r"lq|低画質|低品質|low ?quality", re.I), -6),
    (re.compile(r"wav|flac", re.I), -4),
    (re.compile(r"low|lr2|mpg|wmv|compact|lite|軽量|no ?bga|bga ?(なし|無し)|without", re.I), -2),
    (OLD := re.compile(r"\bold\b|old ?ver|旧|not fixed", re.I), -3),
    # a team's songs in one archive
    (re.compile(r"チーム曲|チーム.{0,8}全部入り|team ?pack|all (team )?songs", re.I), -8),
]
# a separate BGA archive ("BGA only", "HQ BGA", "高画質BGA")
BGA_ONLY = re.compile(r"bga ?(only|単体|のみ)|only ?bga|^\W*(hq ?|sd画質|高画質|仮の)?bga\b", re.I)
# "beatoraja用高画質BGA (HQ BGA for beatoraja)": a high quality BGA alone,
# unless the label speaks of a package ("ogg HQ BGA", "HQBGA版")
HQ_BGA = re.compile(r"(高画質|hq|hd) ?bga", re.I)
PACKAGE = re.compile(r"本体|bms|ogg|wav|package|パッケージ|full|同梱|込|入り|with|版|ver", re.I)


def bga_only(label: str) -> bool:
    return bool(BGA_ONLY.search(label) or HQ_BGA.search(label) and not PACKAGE.search(label))


HQ = GOOD[1][0]
LQ = BAD[0][0]
HOSTS = re.compile(
    r"g-?drive|google ?drive|drive|dropbox|onedrive|one ?drive|mega|mediafire|url ?\d*|link|dl|download|ダウンロード|[\[\]()（）:：・\-]",
    re.I,
)


def is_folder(url: str) -> bool:
    return "/folders/" in url or "/scl/fo/" in url or "/drive/u/" in url


def variant(label: str) -> str:
    """The label without host names and mirror words: mirrors of one
    archive share it."""
    v = MIRROR.sub("", label)
    v = HOSTS.sub(" ", v)
    return re.sub(r"\s+", " ", v).strip().lower()


def links_of(cell: str):
    """[(label, url)] from the address cell: a line's own text, or the
    last heading line above it."""
    out, heading = [], []
    for raw in re.split(r"<br\s*/?>", cell, flags=re.I):
        urls = re.findall(r'href="(https?://[^"]+)"', raw)
        t = text(raw)
        for u in urls:
            t = t.replace(html.unescape(u), "")
        t = t.strip(" :：-")
        if not urls:
            # headings stack ("[ogg]" then "Google Drive:") until a gap
            heading = heading + [t] if t else []
            continue
        for u in urls:
            u = html.unescape(u)
            if all(u != x for _, x in out):
                out.append((" ".join(heading[-2:] + [t]).strip(), u))
        # a host heading ("Google Drive:") names just the link below it
        if heading and not variant(heading[-1]):
            heading.pop()
    return out


def file_part(url: str) -> str:
    """The file name in a URL, if it shows one (`.../song_ogg.zip`)."""
    path = urllib.parse.unquote(urllib.parse.unquote(urllib.parse.urlparse(url).path))
    names = [p for p in path.split("/") if "." in p]
    return names[-1] if names else ""


def bga_versions(links) -> bool:
    """Whether the links are one package with a low and a high quality BGA
    ("(高画質BGA)" and "(低画質BGA)"), not an archive and its BGA."""
    def only(q, other, l):
        return q.search(l) and not other.search(l) and re.search("bga", l, re.I)
    return any(only(LQ, HQ, l) for l, _ in links) and any(only(HQ, LQ, l) for l, _ in links)


def score(label: str, url: str, versions: bool = False) -> int:
    label = label + " " + file_part(url)
    s = sum(w for r, w in GOOD if r.search(label)) + sum(w for r, w in BAD if r.search(label))
    if bga_only(label) and not versions:
        s -= 14
    if MIRROR.search(label):
        s -= 1
    if is_folder(url):
        s -= 3
    if re.search(r"pan\.baidu|lanzou|lanzn|lanzoub", url):
        s -= 5
    return s


def pick(links):
    """(main urls in the order to try, extra archives, why to review)"""
    if not links:
        return [], [], "no link"
    versions = bga_versions(links)

    def addon(l: str) -> bool:
        if bga_only(l) and not versions or EARLIER.search(l) and not AGAIN.search(l):
            return True
        if FULL.search(l) and not ADDON_ONLY.search(l) or OLD.search(l) or APPLIED.search(l):
            return False
        return bool(EXTRA.search(l)) and not re.search(r"ogg|wav", l, re.I)

    extra_links = [(l, u) for l, u in links if addon(l)]
    rest = [(l, u) for l, u in links if (l, u) not in extra_links]
    if not rest:
        # every link adds to a package: the best one that is not a BGA
        # alone is the package, the others stay add-ons
        rest = [(l, u) for l, u in links if not bga_only(l)] or links
        top = max(rest, key=lambda x: score(x[0], x[1], versions))
        rest = [x for x in rest if variant(x[0]) == variant(top[0])]
    extra_links = [x for x in extra_links if x not in rest]
    sc = {u: score(l, u, versions) for l, u in rest}
    best = max(rest, key=lambda x: sc[x[1]])
    key = variant(best[0])
    # a mirror of the main archive is no add-on
    extra_links = [x for x in extra_links if variant(x[0]) != key]
    main = [best[1]] + [u for l, u in rest if u != best[1] and variant(l) == key and not is_folder(u) and sc[u] >= sc[best[1]] - 1]
    extra = []
    for l, u in extra_links:
        k = variant(l)
        group = next((g for g in extra if g[0] == k), None)
        if group:
            group[1].append(u)
        else:
            extra.append((k, [u]))
    why = []
    top = [x for x in rest if sc[x[1]] == sc[best[1]] and variant(x[0]) != key]
    if top:
        why.append("several links score the same")
    if extra:
        why.append("add-on archives guessed")
    if is_folder(best[1]):
        why.append("main link is a folder")
    if len(rest) > 1 and not any(r.search(best[0]) for r, _ in GOOD + BAD) and not top:
        why.append("labels say little")
    return main, [g[1] for g in extra], "; ".join(why)


def main():
    event, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    urls = get(f"{BASE}?action=URLList&event={event}&start=0&end=9999")
    works_page = get(f"{BASE}?action=List_def&event={event}")
    kinds = {int(n): k for n, k in re.findall(r"No\.(\d+) / (\w+)", works_page)}
    overrides_file = out / "overrides.json"
    overrides = json.loads(overrides_file.read_text()) if overrides_file.exists() else {}
    works = []
    for row in re.findall(r"<tr\s*>(.*?)</tr>", urls, re.S):
        tds = re.findall(r"<td>(.*?)</td>", row, re.S)
        if len(tds) < 6:
            continue
        num = int(text(tds[0]))
        size = re.match(r"(\d+)\s*KB", text(tds[4]))
        links = links_of(tds[5])
        main_urls, extra, review = pick(links)
        w = {
            "num": num,
            "title": text(tds[3]),
            "artist": text(tds[1]),
            "team": text(tds[2]),
            "kind": kinds.get(num, ""),
            "size_kb": int(size.group(1)) if size else None,
            "page": f"{BASE}?action=More_def&num={num}&event={event}",
            "links": [{"label": l, "url": u} for l, u in links],
            "main": main_urls,
            "extra": extra,
        }
        if review:
            w["review"] = review
        if str(num) in overrides:
            w.update(overrides[str(num)])
            w.pop("review", None)
        works.append(w)
    works.sort(key=lambda w: w["num"])
    (out / "works.json").write_text(json.dumps(works, ensure_ascii=False, indent=1) + "\n")
    n_review = sum("review" in w for w in works)
    print(f"{len(works)} works, {n_review} to review, {sum(w['kind'] == 'Disq' for w in works)} disqualified")


if __name__ == "__main__":
    main()
