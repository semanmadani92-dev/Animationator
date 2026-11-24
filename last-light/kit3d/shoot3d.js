// node shoot3d.js <scene dir> <out.mp4 | stills:t1,t2,...> [fps]
// Serves the kit folder over http (ES modules + glTF need it), loads <dir>/index.html, waits for window.ready,
// then renders draw(t) frame by frame into ffmpeg (24 fps), muxing <dir>/audio.wav if present.
const { chromium } = require('playwright'); const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');
const root = __dirname, types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json', '.bin': 'application/octet-stream', '.wav': 'audio/wav' };
const srv = http.createServer((q, r) => { const f = path.join(root, decodeURIComponent(q.url.split('?')[0]));
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); } else { r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); } }); });
(async () => {
  const [ep, out] = process.argv.slice(2), fps = +(process.argv[4] || 24);
  await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
  const dir = path.resolve(root, ep), tlf = path.join(dir, 'tl.json'), tl = fs.existsSync(tlf) ? JSON.parse(fs.readFileSync(tlf)) : null;
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.log('PAGE ERROR', e.message));
  await p.goto(`http://localhost:${port}/${path.relative(root, dir)}/index.html`);
  if (tl) await p.evaluate(x => { window.TL = x; TL = x; }, tl);
  await p.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  await p.evaluate(() => document.fonts.ready);
  if (out.startsWith('stills:')) {
    for (const t of out.slice(7).split(',')) { await p.evaluate(tt => draw(tt), +t); await p.screenshot({ path: path.join(dir, `st_${t}.png`) }); }
  } else {
    const end = await p.evaluate(() => window.END || TL.end), n = Math.round(end * fps), wav = path.join(dir, 'audio.wav');
    const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-'];
    if (fs.existsSync(wav)) args.push('-i', wav, '-c:a', 'aac', '-b:a', '192k', '-shortest');
    args.push('-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path.resolve(out));
    const ff = spawn('ffmpeg', args);
    for (let f = 0; f < n; f++) { await p.evaluate(tt => draw(tt), f / fps); const buf = await p.screenshot({ type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('saved', out, (n / fps).toFixed(1) + 's');
  }
  await b.close(); srv.close();
})();
