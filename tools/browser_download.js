// Download a public share (OneDrive) the way a person does: open its page
// in a browser and press Download.
//
//     node tools/browser_download.js URL DIR   -> prints the saved file's path
//
// Needs `playwright` (npm) and its Chromium.
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [url, dir] = process.argv.slice(2);
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ acceptDownloads: true });
    const page = await ctx.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    const button = page.getByRole('button', { name: /^\s*(download|ダウンロード)\s*$/i }).first();
    await button.waitFor({ timeout: 60000 });
    const [dl] = await Promise.all([
      page.waitForEvent('download', { timeout: 120000 }),
      button.click(),
    ]);
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
