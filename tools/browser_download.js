// A file a share page only gives to a browser (OneDrive, a MediaFire page
// built by script...): open the page headless, press its Download button
// or link once, and take what it downloads.
//
//     node tools/browser_download.js URL DIR  -> the saved file's path
//
// Needs `playwright` (npm) and its Chromium.
const path = require('path');
const { chromium } = require('playwright');

const NAME = /^\s*(download|ダウンロード|다운로드|下载|下載|普通下载)(\s*\(.*\))?\s*$/i;

(async () => {
  const [url, dir] = process.argv.slice(2);
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ acceptDownloads: true });
    const page = await ctx.newPage();
    const download = page.waitForEvent('download', { timeout: 180000 });
    download.catch(() => {});
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch((e) => {
      // a link straight to the file starts the download instead of a page
      if (!/Download is starting/.test(e.message)) throw e;
    });
    // pages built by script (OneDrive) show the button after a while
    const button = page.getByRole('button', { name: NAME })
      .or(page.getByRole('menuitem', { name: NAME }))
      .or(page.getByRole('link', { name: NAME }))
      .or(page.locator('#downloadButton'))
      .first();
    await button.click({ timeout: 60000 }).catch(() => {});
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
