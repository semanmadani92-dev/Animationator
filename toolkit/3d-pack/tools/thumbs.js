// node thumbs.js <pack dir under glb/> : renders a labelled contact sheet glb/<pack>.png
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path'); const { execSync } = require('child_process');
(async () => {
  const pack = process.argv[2], dir = path.join(__dirname, 'glb', pack);
  const files = fs.readdirSync(dir).filter(f => /\.(glb|gltf)$/.test(f)).sort();
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 256, height: 256 } });
  await p.goto('http://localhost:8765/thumbs.html'); await p.waitForFunction(() => window.ready);
  const tdir = path.join(__dirname, 'thumbs', pack); fs.mkdirSync(tdir, { recursive: true }); const meta = {};
  for (const f of files) {
    try { meta[f] = await p.evaluate(u => thumb(u), `glb/${pack}/${f}`); await p.screenshot({ path: path.join(tdir, f + '.png') }); }
    catch (e) { console.log('fail', f, e.message.slice(0, 80)); }
  }
  fs.writeFileSync(path.join(__dirname, 'glb', pack + '.json'), JSON.stringify(meta, null, 1));
  await b.close(); console.log(pack, Object.keys(meta).length);
})();
