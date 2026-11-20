// Shared drawing code: one character ("the kid") and props, drawn in three styles.
// style: 'flat' (no outlines, soft shading), 'doodle' (marker lines on paper), 'comic' (inked, cel-shaded)
const PAL = {
  skin: '#f4c29b', skinS: '#e0a47c', hair: '#3a2a22', hairH: '#5a4234', hood: '#ffc93c', hoodS: '#e8a91e',
  jeans: '#3d6fd6', jeansS: '#2f57ad', shoe: '#ffffff', shoeS: '#d9dde6', mouth: '#7a2630', blush: '#ff8f8f',
};

function S(style) {
  if (style === 'flat') return { st: 'none', sw: 0, shade: true };
  if (style === 'comic') return { st: '#111', sw: 8, shade: true };
  return { st: '#1a1a1a', sw: 7, shade: false };
}

function pt(x, y, a, l) { const r = a * Math.PI / 180; return [x + l * Math.sin(r), y + l * Math.cos(r)]; }

function limb(style, x, y, a1, l1, a2, l2, w, col, colS) {
  const s = S(style);
  const [ex, ey] = pt(x, y, a1, l1), [hx, hy] = pt(ex, ey, a2, l2);
  const d = `M${x},${y} L${ex},${ey} L${hx},${hy}`;
  let out = '';
  if (style === 'doodle') {
    out += `<path d="${d}" stroke="#1a1a1a" stroke-width="${w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
    out += `<path d="${d}" stroke="${col === PAL.jeans ? '#ffffff' : '#fbf8f0'}" stroke-width="${w - 14}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
  } else {
    if (s.sw) out += `<path d="${d}" stroke="${s.st}" stroke-width="${w + s.sw * 2}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
    out += `<path d="${d}" stroke="${col}" stroke-width="${w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
    if (s.shade) out += `<path d="${d}" stroke="${colS}" stroke-width="${w * 0.35}" fill="none" stroke-linecap="round" stroke-linejoin="round" transform="translate(${w * 0.22},${w * 0.12})" opacity=".9"/>`;
  }
  return { svg: out, end: [hx, hy], a: a2 };
}

function shape(style, d, col, colS, extra = '') {
  const s = S(style);
  if (style === 'doodle') return `<path d="${d}" fill="${col === 'paper' ? '#fbf8f0' : col}" stroke="#1a1a1a" stroke-width="7" stroke-linejoin="round" ${extra}/>`;
  return `<path d="${d}" fill="${col}" stroke="${s.st}" stroke-width="${s.sw}" stroke-linejoin="round" ${extra}/>`;
}

function circle(style, cx, cy, r, col) {
  const s = S(style);
  if (style === 'doodle') return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${col === 'paper' ? '#fbf8f0' : col}" stroke="#1a1a1a" stroke-width="7"/>`;
  return `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${col}" stroke="${s.st}" stroke-width="${s.sw}"/>`;
}

// The kid. Origin at the hips. pose: arm/leg angles (deg from straight down, + = towards +x).
function kid(style, pose = {}) {
  const P = Object.assign({ la: [-135, -165], ra: [140, 170], ll: [-20, 15], rl: [28, -10], expr: 'shock' }, pose);
  const s = S(style), dd = style === 'doodle';
  const hood = dd ? PAL.hood : PAL.hood;
  let g = '';
  // far arm and legs first
  g += limb(style, -60, -170, P.la[0], 92, P.la[1], 82, 44, PAL.hood, PAL.hoodS).svg;
  const handL = limb(style, -60, -170, P.la[0], 92, P.la[1], 82, 44, PAL.hood, PAL.hoodS).end;
  for (const [x, a] of [[-28, P.ll], [28, P.rl]]) {
    const L = limb(style, x, -10, a[0], 85, a[1], 80, 50, dd ? '#fff' : PAL.jeans, PAL.jeansS);
    g += L.svg;
    const [fx, fy] = L.end, r = (a[1]) * Math.PI / 180;
    g += `<ellipse cx="${fx + 14 * Math.cos(r)}" cy="${fy + 10}" rx="38" ry="22" transform="rotate(${-a[1] * 0.6} ${fx} ${fy})" fill="${dd ? '#fbf8f0' : PAL.shoe}" stroke="${dd ? '#1a1a1a' : s.st}" stroke-width="${dd ? 7 : s.sw}"/>`;
    if (s.shade) g += `<ellipse cx="${fx + 14 * Math.cos(r)}" cy="${fy + 22}" rx="30" ry="7" transform="rotate(${-a[1] * 0.6} ${fx} ${fy})" fill="${PAL.shoeS}"/>`;
  }
  g += circle(style, handL[0], handL[1], 24, dd ? 'paper' : PAL.skin);
  // hoodie body
  const body = 'M-82,0 Q-96,-100 -72,-192 Q0,-222 72,-192 Q96,-100 82,0 Q0,18 -82,0 Z';
  if (dd) {
    g += `<path d="${body}" fill="${PAL.hood}" transform="translate(10,8)" opacity=".85"/>`; // sloppy marker fill
    g += `<path d="${body}" fill="none" stroke="#1a1a1a" stroke-width="7" stroke-linejoin="round"/>`;
  } else {
    g += shape(style, body, hood);
    if (s.shade) g += `<path d="M30,-200 Q90,-160 82,0 Q60,10 40,12 Q60,-90 30,-200 Z" fill="${PAL.hoodS}"/>`;
    g += `<rect x="-50" y="-80" width="100" height="46" rx="18" fill="${PAL.hoodS}" ${style === 'comic' ? 'stroke="#111" stroke-width="5"' : ''}/>`;
    g += `<path d="M-22,-190 L-26,-130 M22,-190 L26,-130" stroke="${style === 'comic' ? '#111' : '#fff6dc'}" stroke-width="6" stroke-linecap="round"/>`;
  }
  if (dd) g += `<path d="M-40,-75 L40,-75" stroke="#1a1a1a" stroke-width="6" stroke-linecap="round"/>`;
  // near arm
  const R = limb(style, 60, -170, P.ra[0], 92, P.ra[1], 82, 44, PAL.hood, PAL.hoodS);
  g += R.svg + circle(style, R.end[0], R.end[1], 24, dd ? 'paper' : PAL.skin);
  // head
  const hy = -305;
  g += circle(style, -112, hy + 10, 24, dd ? 'paper' : PAL.skin) + circle(style, 112, hy + 10, 24, dd ? 'paper' : PAL.skin);
  g += circle(style, 0, hy, 118, dd ? 'paper' : PAL.skin);
  if (s.shade) g += `<path d="M70,${hy - 90} A118,118 0 0 1 60,${hy + 100} Q100,${hy} 70,${hy - 90} Z" fill="${PAL.skinS}" opacity=".7"/>`;
  // messy hair with a cowlick
  const hair = `M-122,${hy - 5} C-140,${hy - 150} 130,${hy - 175} 124,${hy - 10} L104,${hy - 40} L92,${hy - 20} L80,${hy - 62}
    L58,${hy - 38} L40,${hy - 70} L18,${hy - 44} L-4,${hy - 76} L-24,${hy - 46} L-48,${hy - 72} L-66,${hy - 40} L-90,${hy - 64} L-104,${hy - 20} Z
    M-6,${hy - 150} C-20,${hy - 200} 40,${hy - 215} 34,${hy - 168} C24,${hy - 190} 8,${hy - 180} -6,${hy - 150} Z`;
  g += shape(style, hair, dd ? '#1a1a1a' : PAL.hair);
  if (s.shade) g += `<path d="M-70,${hy - 110} Q-20,${hy - 140} 40,${hy - 128}" stroke="${PAL.hairH}" stroke-width="10" fill="none" stroke-linecap="round"/>`;
  // face
  const eye = (x) => {
    let e = `<ellipse cx="${x}" cy="${hy + 5}" rx="31" ry="38" fill="#fff" stroke="${dd || style === 'comic' ? '#1a1a1a' : 'none'}" stroke-width="${dd ? 6 : 5}"/>`;
    e += `<circle cx="${x + 4}" cy="${hy + 10}" r="${P.expr === 'shock' ? 11 : 16}" fill="#1a1a1a"/>`;
    e += `<circle cx="${x + 9}" cy="${hy + 3}" r="5" fill="#fff"/>`;
    return e;
  };
  g += eye(-44) + eye(44);
  const browY = P.expr === 'shock' ? hy - 58 : hy - 44;
  g += `<path d="M-72,${browY + 6} Q-46,${browY - 10} -20,${browY}" stroke="${dd ? '#1a1a1a' : PAL.hair}" stroke-width="10" fill="none" stroke-linecap="round"/>`;
  g += `<path d="M20,${browY} Q46,${browY - 10} 72,${browY + 6}" stroke="${dd ? '#1a1a1a' : PAL.hair}" stroke-width="10" fill="none" stroke-linecap="round"/>`;
  if (!dd) g += `<ellipse cx="-70" cy="${hy + 52}" rx="20" ry="11" fill="${PAL.blush}" opacity=".55"/><ellipse cx="70" cy="${hy + 52}" rx="20" ry="11" fill="${PAL.blush}" opacity=".55"/>`;
  if (P.expr === 'shock') g += `<ellipse cx="0" cy="${hy + 68}" rx="20" ry="27" fill="${dd ? '#1a1a1a' : PAL.mouth}" stroke="${style === 'comic' ? '#111' : 'none'}" stroke-width="5"/>`;
  else g += `<path d="M-30,${hy + 58} Q0,${hy + 92} 30,${hy + 58} Z" fill="${dd ? '#1a1a1a' : PAL.mouth}"/>`;
  return g;
}

function car(style, col = '#ff5a5f', colS = '#d63b44') {
  const dd = style === 'doodle', s = S(style);
  let g = shape(style, 'M-170,0 Q-175,-60 -130,-66 L-80,-70 L-40,-120 L70,-120 L120,-70 L160,-62 Q180,-50 176,0 Z', dd ? 'paper' : col);
  if (s.shade) g += `<path d="M-170,0 L176,0 Q178,-16 170,-24 L-168,-24 Z" fill="${colS}"/>`;
  g += shape(style, 'M-26,-108 L64,-108 L100,-72 L-56,-72 Z', dd ? 'paper' : '#bfe6ff');
  for (const x of [-100, 100]) {
    g += circle(style, x, 0, 38, dd ? 'paper' : '#2b2b33') + circle(style, x, 0, 16, dd ? 'paper' : '#c9ced8');
  }
  return g;
}

function cat(style) {
  const dd = style === 'doodle', c = dd ? 'paper' : '#ff9f43', s = S(style);
  let g = shape(style, 'M-70,10 Q-80,-50 0,-52 Q80,-50 70,10 Q0,40 -70,10 Z', c);
  g += shape(style, 'M60,-20 Q130,-60 110,-120', 'none', '', `fill="none" stroke-width="${dd ? 8 : 18}" stroke="${dd ? '#1a1a1a' : '#ff9f43'}" stroke-linecap="round"`);
  g += circle(style, -66, -60, 46, c);
  g += shape(style, 'M-104,-80 L-100,-128 L-72,-100 Z M-60,-104 L-36,-130 L-28,-88 Z', c);
  if (s.shade) g += `<path d="M-30,-40 L-20,-10 M0,-44 L8,-12 M30,-40 L36,-10" stroke="#e07b22" stroke-width="8" stroke-linecap="round"/>`;
  g += `<circle cx="-82" cy="-62" r="8" fill="#1a1a1a"/><circle cx="-52" cy="-62" r="8" fill="#1a1a1a"/><ellipse cx="-67" cy="-40" rx="8" ry="10" fill="#1a1a1a"/>`;
  return g;
}

function cup(style) {
  const dd = style === 'doodle';
  let g = shape(style, 'M-40,-60 L40,-60 L32,30 L-32,30 Z', dd ? 'paper' : '#ffffff');
  g += shape(style, 'M40,-40 Q74,-30 36,10', 'none', '', `fill="none" stroke-width="${dd ? 7 : 12}" stroke="${dd ? '#1a1a1a' : '#ffffff'}"`);
  for (const [x, y, r] of [[-10, -100, 16], [22, -140, 11], [-30, -160, 8], [8, -186, 6]]) g += circle(style, x, y, r, dd ? 'paper' : '#8b5a3c');
  return g;
}

function bowl(style) {
  const dd = style === 'doodle';
  let g = shape(style, 'M-110,-20 L110,-20 Q100,60 0,64 Q-100,60 -110,-20 Z', dd ? 'paper' : '#4fb3ff');
  g += `<ellipse cx="0" cy="-20" rx="110" ry="18" fill="${dd ? '#fbf8f0' : '#ffffff'}" stroke="${S(style).st}" stroke-width="${S(style).sw}"/>`;
  return g;
}

function loops(cx, cy, n, r, col, seed = 1) {  // floating cereal / debris
  let g = '';
  for (let i = 0; i < n; i++) {
    const a = (i * 137.5 + seed * 50) * Math.PI / 180, d = r * Math.sqrt((i + 1) / n);
    g += `<circle cx="${cx + d * Math.cos(a)}" cy="${cy + d * Math.sin(a)}" r="13" fill="none" stroke="${col[i % col.length]}" stroke-width="9"/>`;
  }
  return g;
}

function motion(x, y, len, n, col, w = 8) {
  let g = '';
  for (let i = 0; i < n; i++) g += `<path d="M${x},${y + i * 28} l0,${len - i * 18}" stroke="${col}" stroke-width="${w}" stroke-linecap="round" opacity=".8"/>`;
  return g;
}

function T(x, y, r, s, inner) { return `<g transform="translate(${x},${y}) rotate(${r}) scale(${s})">${inner}</g>`; }
