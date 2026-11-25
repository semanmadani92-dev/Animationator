const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const srv = http.createServer((q, r) => fs.readFile(path.join(__dirname, decodeURIComponent(q.url.split('?')[0])), (e, d) => { r.writeHead(e ? 404 : 200, { 'Content-Type': /\.js$/.test(q.url) ? 'text/javascript' : /\.html$/.test(q.url) ? 'text/html' : 'application/octet-stream' }); r.end(d); }));
(async () => { await new Promise(r => srv.listen(0, r)); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.log('ERR', e.message)); const ep = process.argv[2];
  await p.goto(`http://localhost:${srv.address().port}/${ep}/index.html`); await p.evaluate(x => { window.TL = x; TL = x; }, JSON.parse(fs.readFileSync(path.join(__dirname, ep, 'tl.json'))));
  await p.waitForFunction(() => window.ready); await p.evaluate(x => { window.DBGCAM = x; }, JSON.parse(process.argv[4] || 'null'));
  for (const t of process.argv[3].split(',')) { await p.evaluate(tt => draw(tt), +t); await p.screenshot({ path: `${ep}/dbg_${t}.png` }); }
  await b.close(); srv.close(); })();
