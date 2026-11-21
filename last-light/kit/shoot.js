// Render an episode: node shoot.js <ep_dir> <out.mp4 | stills:t1,t2,...>
// Loads <ep_dir>/video.html with <ep_dir>/tl.json; frames go to ffmpeg at 24 fps, muxed with <ep_dir>/audio.wav.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [ep, out] = process.argv.slice(2);
  const dir = path.resolve(__dirname, ep);
  const tl = require(path.join(dir, 'tl.json'));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(dir, 'video.html'));
  await page.evaluate(x => { TL = x; }, tl);
  await page.evaluate(() => document.fonts.ready);
  if (out.startsWith('stills:')) {
    for (const t of out.slice(7).split(',')) {
      await page.evaluate(tt => draw(tt), +t);
      await page.screenshot({ path: path.join(dir, `st_${t}.png`) });
    }
  } else {
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '24', '-c:v', 'mjpeg', '-i', '-',
      '-i', path.join(dir, 'audio.wav'), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
      '-shortest', '-movflags', '+faststart', path.resolve(out)]);
    const n = Math.round(tl.end * 24);
    for (let f = 0; f < n; f++) {
      await page.evaluate(tt => draw(tt), f / 24);
      const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('saved', out, (n / 24).toFixed(1) + 's');
  }
  await browser.close();
})();
