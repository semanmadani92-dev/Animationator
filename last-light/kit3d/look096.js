// stills of SCP-096 alone in a lit studio, to check proportions
const { chromium } = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const srv = http.createServer((q, r) => fs.readFile(path.join(__dirname, decodeURIComponent(q.url.split('?')[0])), (e, d) => { r.writeHead(e ? 404 : 200, { 'Content-Type': /\.js$/.test(q.url) ? 'text/javascript' : /\.html$/.test(q.url) ? 'text/html' : 'application/octet-stream' }); r.end(d); }));
fs.writeFileSync(path.join(__dirname, 'look096.html'), `<!doctype html><html><body style="margin:0"><canvas id="g" width="1080" height="1080"></canvas>
<script type="importmap">{"imports":{"three":"./three.module.js","three/addons/":"./jsm/"}}</script>
<script type="module">
import { THREE, loadMannequins, makeHuman, pose } from './kit3d.js';
const r = new THREE.WebGLRenderer({ canvas: document.getElementById('g'), antialias: true, preserveDrawingBuffer: true }); r.setSize(1080, 1080, false);
const sc = new THREE.Scene(); sc.background = new THREE.Color(0x202226); sc.add(new THREE.HemisphereLight(0xffffff, 0x333333, 1.6)); const d = new THREE.DirectionalLight(0xffffff, 2); d.position.set(2, 4, 3); sc.add(d);
const lib = await loadMannequins('./assets/animation/');
const me = makeHuman(lib, { number: 'D-4172' }); me.root.position.x = -1.6; sc.add(me.root); pose(me, [{ clip: 'Idle_Loop', t0: 0 }], .5);
const poses = ['Idle_Loop', 'Crouch_Idle_Loop', 'Zombie_Idle_Loop', 'Sprint_Loop'];
poses.forEach((c, i) => { const s = makeHuman(lib, { suit: 0xd8d3c8, skin: 0xe4dfd4, boots: 0xcfc9bc, number: '', face: false }); s.root.scale.set(.72, 1.3, .72);
  for (const x of ['l', 'r']) { s.bone('lowerarm_' + x).scale.set(1, 1.9, 1); s.bone('hand_' + x).scale.set(1, 1 / 1.9, 1); s.bone('upperarm_' + x).scale.set(.8, 1.45, .8); }
  s.root.position.x = -.2 + i * 1.2; s.root.rotation.y = i === 0 ? 0 : .6; sc.add(s.root); pose(s, [{ clip: c, t0: 0 }], .4);
  for (const x of ['l', 'r']) { s.bone('lowerarm_' + x).scale.set(1, 1.6, 1); s.bone('hand_' + x).scale.set(1, 1 / 1.6, 1); s.bone('upperarm_' + x).scale.set(.85, 1.3, .85); } });
const cam = new THREE.PerspectiveCamera(35, 1, .1, 50); cam.position.set(.6, 1.6, 8); cam.lookAt(.6, 1.2, 0); r.render(sc, cam); window.ready = true;
</script></body></html>`);
(async () => { await new Promise(r => srv.listen(0, r)); const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1080 } });
  p.on('pageerror', e => console.log('ERR', e.message)); await p.goto(`http://localhost:${srv.address().port}/look096.html`); await p.waitForFunction(() => window.ready, null, { timeout: 60000 });
  await p.screenshot({ path: 'look096.png' }); await b.close(); srv.close(); })();
