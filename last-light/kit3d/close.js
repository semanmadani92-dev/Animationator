const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const srv = http.createServer((q, r) => fs.readFile(path.join(__dirname, decodeURIComponent(q.url.split('?')[0])), (e, d) => { r.writeHead(e ? 404 : 200, { 'Content-Type': /\.js$/.test(q.url) ? 'text/javascript' : /\.html$/.test(q.url) ? 'text/html' : 'application/octet-stream' }); r.end(d); }));
(async () => { await new Promise(r => srv.listen(0, r)); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.log(e.message)); await p.goto(`http://localhost:${srv.address().port}/${process.argv[2]}/index.html`); await p.waitForFunction(() => window.ready);
  await p.evaluate(() => { window.CLOSE = true; });
  for (const t of process.argv[3].split(',')) { await p.evaluate(tt => draw(tt), +t); await p.screenshot({ path: `${process.argv[2]}/close_${t}.png` }); }
  await b.close(); srv.close(); })();
