// Screenshot scene.html in each style. Usage: node shoot.js <out_dir>
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const out = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const s of ['flat', 'doodle', 'comic']) {
    await page.goto('file://' + path.join(__dirname, 'scene.html') + '?s=' + s);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(out, `style_${s}.png`) });
    console.log('saved', s);
  }
  await browser.close();
})();
