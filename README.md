# vibeBMS / bms

Mirrors of BMS event entries, kept so they stay downloadable after the
links people posted during the event go away. Each event is a release;
each work is its original archive, **byte for byte as the author
published it**.

| Event | Release | Mirrored | Works |
|---|---|---|---|
| THE BMS OF FIGHTERS 22 - GO 2 YOUR EVOLUTION - | [`bof22`](../../releases/tag/bof22) | archives | [bof22/works.json](bof22/works.json) |
| THE BMS OF FIGHTERS 21 - GO BACK 2 YOUR ROOTS - | [`bof21`](../../releases/tag/bof21) | archives | [bof21/works.json](bof21/works.json) |
| THE BMS OF FIGHTERS : TT - Sonata for the 20th Ceremony - | [`boftt`](../../releases/tag/boftt) | archives | [boftt/works.json](boftt/works.json) |
| THE BMS OF FIGHTERS : NT - Twinkle Dream Traveler - | [`bofnt`](../../releases/tag/bofnt) | links only | [bofnt/works.json](bofnt/works.json) |
| THE BMS OF FIGHTERS : ET - Summer Dream Traveler - | [`bofet`](../../releases/tag/bofet) | links only | [bofet/works.json](bofet/works.json) |
| THE BMS OF FIGHTERS XVII - VISION THE RETRO FUTURE - | [`bofxvii`](../../releases/tag/bofxvii) | archives | [bofxvii/works.json](bofxvii/works.json) |
| THE BMS OF FIGHTERS XVI - NEO DYSTOPIA - | [`bofxvi`](../../releases/tag/bofxvi) | archives | [bofxvi/works.json](bofxvi/works.json) |
| BOFXV - THE BMS OF FIGHTERS eXtreme Violence - | [`bofxv`](../../releases/tag/bofxv) | links only | [bofxv/works.json](bofxv/works.json) |
| BOFU2017 - LEGENDA EST A MYTH - | [`bofu2017`](../../releases/tag/bofu2017) | links only | [bofu2017/works.json](bofu2017/works.json) |
| BOFU2016 - Legendary Again - | [`bofu2016`](../../releases/tag/bofu2016) | links only | [bofu2016/works.json](bofu2016/works.json) |
| 大血戦 - BOFU2015 - | [`bofu2015`](../../releases/tag/bofu2015) | links only | [bofu2015/works.json](bofu2015/works.json) |
| konzertsaal - THE BMS OF FIGHTERS 2013 - | [`bof2013`](../../releases/tag/bof2013) | links only | [bof2013/works.json](bof2013/works.json) |
| THE BMS OF FIGHTERS 2012 - Ein neuer Heiliger - | [`bof2012`](../../releases/tag/bof2012) | links only | [bof2012/works.json](bof2012/works.json) |
| THE BMS OF FIGHTERS 2011 - Intersection of conflict - | [`bof2011`](../../releases/tag/bof2011) | links only | [bof2011/works.json](bof2011/works.json) |
| THE BMS OF FIGHTERS 2010 - The Evolution of War - | [`bof2010`](../../releases/tag/bof2010) | links only | [bof2010/works.json](bof2010/works.json) |
| THE BMS OF FIGHTERS 2009 - revolutionary battles - | [`bof2009`](../../releases/tag/bof2009) | links only | [bof2009/works.json](bof2009/works.json) |
| THE BMS OF FIGHTERS 2008 - Resurrection - | [`bof2008`](../../releases/tag/bof2008) | links only | [bof2008/works.json](bof2008/works.json) |
| BOF III - THE BMS OF FIGHTERS 2006 - | [`bof2006`](../../releases/tag/bof2006) | links only | [bof2006/works.json](bof2006/works.json) |

`events.json` lists them for players: tag, short name, title, venue
number, whether the archives are mirrored, and the URL of `index.json`.

## Why this is allowed

Registering a work for these events is agreeing to its redistribution,
unaltered, by the organizer or volunteers. The BOF21 rules
([rule_en.html](https://www.bmsoffighters.net/bof21/rule_en.html), the
same in BOF22 and BOF:TT):

> By registering your work during the event period, you agree to secondary
> distribution and package distribution by the organizer or volunteers, as
> long as the archive is not altered.

BOF:XVII ([rule_en.html](https://www.bmsoffighters.net/bofxvii/rule_en.html)):
"By registering your work, you have agreed to the secondary distribution
of BMS and the distribution of packages by the organizer or volunteers,
under the promise that the archive will not be altered." BOF:XVI
([rule.html](https://www.bmsoffighters.net/bofxvi/rule.html)) has the
Japanese sentence of BOF21 and BOF22.

Earlier events limit that agreement to the event period (BOF:NT and
BOF:ET: "…by the event organizer or volunteers during the event period";
BOF2011 to BOF:XV: 「イベント開催期間中に限り、…」), or their rules
could not be found. For those, `index.json` only lists the authors' own
download links: nothing is copied.

So this mirror:

- uploads archives **unmodified** (no repacking, no format conversion);
- leaves out disqualified works;
- takes a work down when its author asks (below).

Charts by other people (差分) are not mirrored: they were never part of
the event.

## Takedown / 削除依頼 / 삭제 요청

If you made one of these works and want it removed, open an
[issue](../../issues/new) with the event and work number. It is removed
without questions.

作品の作者の方で削除を希望される場合は、イベント名と作品番号を書いて
[Issue](../../issues/new) を作成してください。理由を問わず削除します。

## Files

In a mirrored event's release (`bof22`):

- `042.zip`: the archive of work No.42 (its number on the event venue).
  The original file name is the asset's label.
- `042+1.rar`: an add-on the author published separately (an added
  chart, a BGA archive).
- `index.json`: every work with its files: number, title, artist, team,
  venue page, and for each file its URL, size and original name. Works
  that could not be mirrored list their original links instead.

When a work offers several versions, the mirror takes one: the one marked
high quality (HQ, 高画質) over the low quality one, then ogg over wav, and
the latest full package over patches for earlier downloads. The choice is in `works.json` (`main`,
`extra`); `overrides.json` holds the hand-made ones.

## How it is made

- `tools/scrape_manbow.py 152 bof22`: reads the venue's URL list and
  work list into `bof22/works.json` (the venue numbers are in
  `events.json`).
- `tools/fetch.py URL DIR`: downloads one archive (Google Drive, Dropbox,
  MediaFire, MEGA, OneDrive, web servers) and checks it is one.
- `tools/mirror.py bof22`: uploads what the release lacks.
- The **Mirror an event** workflow runs it in 10 shards and writes
  `index.json`. Run it again to fill in what failed (Google Drive
  download limits clear after a day).
- The **Index events** workflow writes `index.json` into the releases of
  the events in `events.json` (creating them), mirrored or not.
