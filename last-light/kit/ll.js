// Last Light shared drawing kit: minimal cinematic style (dark, lamp light, thin type, grain).
// An episode defines scene(t) -> {body, hud, push, cy, shake, tint} and calls run(). TL comes from the timeline JSON:
// TL.lines[id] = {start, end, words: [[w, s, e]]}, TL.end, TL.channel, TL.credit = [lines for the end card].
const W = 1080, H = 1920;
let TL = null;
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = k => { k = clamp(k); return k * k * (3 - 2 * k); };
const lerp = (a, b, k) => a + (b - a) * k;
const ln = id => TL.lines[id];
const wordT = (id, re) => { const w = ln(id).words.find(w => re.test(w[0])); return w ? w[1] : ln(id).end; };
const prog = (id, pad = 0.3) => clamp((tNow - ln(id).start) / (ln(id).end - ln(id).start + pad));
function rnd(i) { const x = Math.sin(i * 127.1) * 43758.5453; return x - Math.floor(x); }
let tNow = 0;

const DEFS = t => `<defs>
  <radialGradient id="pool" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffe9b8" stop-opacity=".55"/><stop offset="1" stop-color="#ffe9b8" stop-opacity="0"/></radialGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff3d6" stop-opacity=".38"/><stop offset="1" stop-color="#fff3d6" stop-opacity="0"/></linearGradient>
  <radialGradient id="torch" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff3d6" stop-opacity=".5"/><stop offset=".7" stop-color="#fff3d6" stop-opacity=".12"/><stop offset="1" stop-color="#fff3d6" stop-opacity="0"/></radialGradient>
  <radialGradient id="phoneglow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#9fc4ff" stop-opacity=".45"/><stop offset="1" stop-color="#9fc4ff" stop-opacity="0"/></radialGradient>
  <radialGradient id="vig" cx=".5" cy=".5" r=".72"><stop offset=".5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".85"/></radialGradient>
  <radialGradient id="burn" cx=".5" cy=".5" r=".6"><stop offset=".35" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#2a0000" stop-opacity="1"/></radialGradient>
  <linearGradient id="concrete" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9a958c"/><stop offset="1" stop-color="#5e5a54"/></linearGradient>
  <radialGradient id="pale" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#eef0f4"/><stop offset="1" stop-color="#a8adb8"/></radialGradient>
  <filter id="grain"><feTurbulence baseFrequency=".9" seed="${Math.floor(t * 24)}"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .07 0"/></filter>
  <filter id="soft"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="blur12"><feGaussianBlur stdDeviation="12"/></filter>
  <filter id="blur30"><feGaussianBlur stdDeviation="30"/></filter>
  <filter id="rough"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="3" seed="9"/><feDisplacementMap in="SourceGraphic" scale="14"/></filter>
</defs>`;

const T = (txt, x, y, z, op = 1, w = 200, ls = 6, anchor = 'start', fill = '#e8ecf5') =>
  `<text x="${x}" y="${y}" text-anchor="${anchor}" font-family="Inter" font-weight="${w}" font-size="${z}" fill="${fill}" opacity="${op}" letter-spacing="${ls}">${txt}</text>`;
const title = (id, cls) => T(id, 80, 190, 40, .85, 300, 14) + T(`OBJECT CLASS   ${cls}`, 80, 240, 30, .55, 200, 10);
const blink = (t, hz = 3) => (Math.floor(t * hz) % 2 ? 1 : .4);

// you: the small silhouette (orange-brown D-class jumpsuit)
function you(x, y, s, o = {}) {
  const bob = o.walk ? Math.abs(Math.sin(o.walk * 7)) * 10 : 0;
  let c = o.sit ? `<path d="M-55,40 L-150,60 L-150,190 M55,40 L-40,60 L-40,190" stroke="#05060a" stroke-width="44" stroke-linecap="round" fill="none"/>`
    : `<path d="M-55,40 L-60,190 M55,40 L60,190" stroke="#05060a" stroke-width="44" stroke-linecap="round"/>`;
  c += `<path d="M-95,40 Q-110,-150 -70,-200 L70,-200 Q110,-150 95,40 Z" fill="${o.suit || '#2a160c'}"/>`;
  c += o.mop ? `<path d="M85,-170 Q140,-60 150,40 M-85,-170 Q-60,-60 100,-20" stroke="${o.suit || '#2a160c'}" stroke-width="40" fill="none" stroke-linecap="round"/><path d="M120,-120 L220,200" stroke="#3a3026" stroke-width="12"/><path d="M180,190 L270,200 L250,230 L170,220 Z" fill="#6a6258"/>`
    : `<path d="M85,-170 Q140,-100 120,0 M-85,-170 Q-140,-100 -120,0" stroke="${o.suit || '#2a160c'}" stroke-width="40" fill="none" stroke-linecap="round"/>`;
  c += `<circle cx="0" cy="-330" r="135" fill="#05060a"/>`;
  if (o.eyes) c += `<circle cx="-48" cy="-330" r="30" fill="#fff"/><circle cx="48" cy="-330" r="30" fill="#fff"/><circle cx="${-48 + (o.look || 0) * 10}" cy="-324" r="9" fill="#000"/><circle cx="${48 + (o.look || 0) * 10}" cy="-324" r="9" fill="#000"/>`;
  if (o.rim) c += `<path d="M-120,-400 A135,135 0 0 1 60,-460" stroke="${o.rim}" stroke-width="10" fill="none" opacity=".8"/>`;
  return `<g transform="translate(${x},${y - bob * s}) scale(${o.flip ? -s : s},${s})">${c}</g>`;
}

// a lamp hanging at (x, y) lighting the floor at floorY
function lamp(x, y, floorY, spread = 300, b = 1) {
  if (b <= 0.01) return `<rect x="${x - 50}" y="${y}" width="100" height="10" fill="#1c2030"/>`;
  return `<g opacity="${b}"><rect x="${x - 50}" y="${y}" width="100" height="10" fill="#fff6e0"/>
    <path d="M${x - 44},${y + 10} L${x + 44},${y + 10} L${x + spread},${floorY} L${x - spread},${floorY} Z" fill="url(#beam)"/>
    <ellipse cx="${x}" cy="${floorY}" rx="${spread * 1.15}" ry="${spread * .2}" fill="url(#pool)"/></g>`;
}

// a bare concrete cell in one-point perspective (back wall, floor, ceiling)
function cell({ floor = '#16171b', wall = '#1b1c21', side = '#121317', stains = 0, door = false }) {
  const bx0 = 250, bx1 = 830, by0 = 520, by1 = 1220;  // back wall rectangle
  let s = `<rect width="${W}" height="${H}" fill="${side}"/>`;
  s += `<polygon points="0,1920 1080,1920 ${bx1},${by1} ${bx0},${by1}" fill="${floor}"/>`;
  s += `<polygon points="0,0 1080,0 ${bx1},${by0} ${bx0},${by0}" fill="#0c0d10"/>`;
  s += `<rect x="${bx0}" y="${by0}" width="${bx1 - bx0}" height="${by1 - by0}" fill="${wall}"/>`;
  for (const [x0, y0, x1, y1] of [[bx0, by0, 0, 0], [bx1, by0, W, 0], [bx0, by1, 0, H], [bx1, by1, W, H]]) s += `<line x1="${x0}" y1="${y0}" x2="${x1}" y2="${y1}" stroke="#2a2c33" stroke-width="2"/>`;
  for (let i = 1; i < 5; i++) { const y = by1 + (H - by1) * (i / 5) ** 1.6; s += `<line x1="0" y1="${y}" x2="${W}" y2="${y}" stroke="#202228" stroke-width="2" opacity=".6"/>`; }
  if (door) s += `<rect x="${bx0 + 40}" y="${by1 - 330}" width="170" height="330" fill="#101114" stroke="#2f3138" stroke-width="3"/><circle cx="${bx0 + 185}" cy="${by1 - 165}" r="7" fill="#4a4d55"/>`;
  for (let i = 0; i < stains; i++) {  // dried reddish-brown stains on the floor
    const x = 200 + rnd(i * 3) * 680, y = 1300 + rnd(i * 5) * 420, r = 30 + rnd(i * 7) * 80;
    s += `<ellipse cx="${x}" cy="${y}" rx="${r}" ry="${r * .3}" fill="#3a1a12" opacity="${.35 + .3 * rnd(i)}" filter="url(#rough)"/>`;
  }
  return s;
}

// end card: channel mark + licence credit (TL.credit)
function endCard(t, at) {
  const a = ease((t - at) / 0.6);
  if (a <= 0) return '';
  let s = `<rect width="${W}" height="${H}" fill="#050608" opacity="${a}"/><g opacity="${a}">`;
  s += `<rect x="514" y="760" width="52" height="8" fill="#fff6e0"/><path d="M520,768 L560,768 L700,1060 L380,1060 Z" fill="url(#beam)"/><ellipse cx="540" cy="1060" rx="200" ry="34" fill="url(#pool)"/>`;
  s += T(TL.channel, 540, 1180, 72, 1, 200, 30, 'middle') + T('NEW FILE EVERY WEEK', 540, 1240, 26, .5, 300, 10, 'middle');
  TL.credit.forEach((c, i) => { s += T(c, 540, 1640 + i * 45, 26, .6, 300, 2, 'middle'); });
  return s + '</g>';
}

function caption(t) {
  for (const id in TL.lines) {
    const ws = ln(id).words, chunks = []; let cur = [];
    ws.forEach((w, i) => { cur.push(w); if (cur.length === 3 || /[.!?,:]$/.test(w[0]) || i === ws.length - 1) { chunks.push(cur); cur = []; } });
    for (let i = 0; i < chunks.length; i++) {
      const a = chunks[i][0][1], b = i + 1 < chunks.length ? chunks[i + 1][0][1] : chunks[i][chunks[i].length - 1][2] + 0.35;
      if (a <= t && t < b) {
        const txt = chunks[i].map(w => w[0]).join(' ');
        return `<text x="540" y="1700" text-anchor="middle" font-family="Inter" font-weight="400" font-size="64" fill="#000" opacity=".6" filter="url(#soft)">${txt}</text>
          <text x="540" y="1700" text-anchor="middle" font-family="Inter" font-weight="400" font-size="64" fill="#fff" letter-spacing="1">${txt}</text>`;
      }
    }
  }
  return '';
}

function draw(t) {
  tNow = t;
  const sc = scene(t), sh = sc.shake || 0;
  let g = DEFS(t) + `<rect width="${W}" height="${H}" fill="#0a0c12"/>`;
  g += `<g transform="translate(${540 + sh},${(sc.cy || 960) + (sc.shakeY || 0)}) scale(${sc.push || 1}) translate(-540,${-(sc.cy || 960)})">${sc.body}</g>`;
  if (sc.over) g += sc.over;  // full-frame effects (flash, eyelids, tint), not zoomed
  g += `<rect width="${W}" height="${H}" fill="url(#vig)"/><rect width="${W}" height="${H}" filter="url(#grain)"/>`;
  g += sc.hud || '';
  if (!sc.noCaption) g += caption(t);
  g += endCard(t, TL.cardAt);
  document.getElementById('c').innerHTML = g;
}
