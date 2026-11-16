// A file a share page only gives to a browser: open the page headless and
// take what it downloads. bmseeker presses OneDrive's Download button (the
// script `bmseeker press-js` prints, run on each page); on other pages a
// visible Download button or link is pressed once.
//
//     node tools/browser_download.js URL DIR PRESS_JS_FILE  -> the saved file's path
//
// Needs `playwright` (npm) and its Chromium.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const NAME = /^\s*(download|ダウンロード|다운로드|下载|下載|普通下载)(\s*\(.*\))?\s*$/i;

(async () => {
  const [url, dir, pressJs] = process.argv.slice(2);
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ acceptDownloads: true });
    if (pressJs) await ctx.addInitScript(fs.readFileSync(pressJs, 'utf8'));
    const page = await ctx.newPage();
    const download = page.waitForEvent('download', { timeout: 180000 });
    download.catch(() => {});
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch((e) => {
      // a link straight to the file starts the download instead of a page
      if (!/Download is starting/.test(e.message)) throw e;
    });
    // give bmseeker's script a moment, then try the page's own button
    const pressed = await Promise.race([
      download.then(() => true),
      page.waitForTimeout(8000).then(() => false),
    ]);
    if (!pressed) {
      const button = page.getByRole('button', { name: NAME })
        .or(page.getByRole('link', { name: NAME }))
        .or(page.locator('#downloadButton'))
        .first();
      await button.click({ timeout: 30000 }).catch(() => {});
    }
    const dl = await download;
    const out = path.join(dir, path.basename(dl.suggestedFilename()));
    await dl.saveAs(out);
    console.log(out);
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(`error: ${e.message.split('\n')[0]}`);
  process.exit(1);
});
