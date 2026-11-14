# vibeBMS / bms

Mirrors of BMS event entries, kept so they stay downloadable after the
links people posted during the event go away. Each event is a release;
each work is its original archive, **byte for byte as the author
published it**.

| Event | Release | Works |
|---|---|---|
| THE BMS OF FIGHTERS 22 | [`bof22`](../../releases/tag/bof22) | [bof22/works.json](bof22/works.json) |

## Why this is allowed

The BOF22 rules ([rule.html](https://www.bmsoffighters.net/bof22/rule.html), 「配布の規定」 and 「有志によるパッケージ配布について」):

> なお、作品はイベント開催期間中に限り登録を行った時点で、アーカイブを改変しないことを条件に主催または有志によるbms二次配布およびパッケージ配布に同意する事になります。
>
> 有志によるパッケージの配布行為に関しては制限を行いませんので、各自の判断で配布していただきますようお願い申し上げます。

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

In release `bof22`:

- `042.zip`: the archive of work No.42 (its number on the event venue).
  The original file name is the asset's label.
- `042+1.rar`: an add-on the author published separately (an added
  chart, a BGA archive).
- `index.json`: every work with its files: number, title, artist, team,
  venue page, and for each file its URL, size and original name. Works
  that could not be mirrored list their original links instead.

When a work offers several versions, the mirror takes one: ogg over wav,
the high quality BGA over the low one, the latest full package over
patches for earlier downloads. The choice is in `works.json` (`main`,
`extra`); `overrides.json` holds the hand-made ones.

## How it is made

- `tools/scrape_manbow.py 152 bof22`: reads the venue's URL list and
  work list into `bof22/works.json`.
- `tools/fetch.py URL DIR`: downloads one archive (Google Drive, Dropbox,
  MediaFire, MEGA, OneDrive, web servers) and checks it is one.
- `tools/mirror.py bof22`: uploads what the release lacks.
- The **Mirror an event** workflow runs it in 10 shards and writes
  `index.json`. Run it again to fill in what failed (Google Drive
  download limits clear after a day).
