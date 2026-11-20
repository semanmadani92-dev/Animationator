// Render one style of anim.html to video frames piped into ffmpeg (or stills for checking).
// Usage: node render.js <style> <fps> <words.json> <L> <END> <out.mp4|stills:t1,t2,...>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [style, fps, wordsPath, L, END, out] = process.argv.slice(2);
  const words = require(path.resolve(wordsPath));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'anim.html'));
  await page.evaluate(([w, l, e]) => { WORDS = w; L = l; END = e; }, [words, +L, +END]);
  await page.evaluate(() => document.fonts.ready);
  if (out.startsWith('stills:')) {
    for (const t of out.slice(7).split(',')) {
      await page.evaluate(([s, tt]) => draw(s, tt), [style, +t]);
      await page.waitForTimeout(50);
      await page.screenshot({ path: path.join(__dirname, `still_${style}_${t}.png`) });
    }
  } else {
    // every style is captured at 24 fps; doodle's 12 fps character timing is built into the drawing
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', '24', '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out]);
    const n = Math.round(+END * 24);
    for (let f = 0; f < n; f++) {
      await page.evaluate(([s, tt]) => draw(s, tt), [style, f / 24]);
      const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
  console.log('done', style, out);
})();
