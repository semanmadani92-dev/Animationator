// node shoot.js <timeline.json> <out.mp4 | stills:t1,t2,...>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [tlPath, out] = process.argv.slice(2);
  const TLd = require(path.resolve(tlPath));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'video.html'));
  await page.evaluate(tl => { TL = tl; }, TLd);
  await page.evaluate(() => document.fonts.ready);
  if (out.startsWith('stills:')) {
    for (const t of out.slice(7).split(',')) {
      await page.evaluate(tt => draw(tt), +t);
      await page.screenshot({ path: path.join(__dirname, `st_${t}.png`) });
    }
  } else {
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '24', '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out]);
    const n = Math.round(TLd.end * 24);
    for (let f = 0; f < n; f++) {
      await page.evaluate(tt => draw(tt), f / 24);
      const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (f % 240 === 0) console.log('frame', f, '/', n);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
