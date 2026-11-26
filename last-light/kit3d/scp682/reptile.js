// SCP-682, an original low-poly design: a scarred, half-regrown reptilian mass. Procedural parts on pivots, animated in code.
import { THREE } from '../kit3d.js';

export function makeReptile(seed = 5) {
  let sd = seed; const R = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
  const rough = (g, a) => { g = g.toNonIndexed(); const p = g.attributes.position, map = {};
    for (let i = 0; i < p.count; i++) { const k = [p.getX(i), p.getY(i), p.getZ(i)].map(v => Math.round(v * 1000)).join(); map[k] = map[k] || [(R() - .5) * a, (R() - .5) * a, (R() - .5) * a]; p.setXYZ(i, p.getX(i) + map[k][0], p.getY(i) + map[k][1], p.getZ(i) + map[k][2]); }
    g.computeVertexNormals(); return g; };
  const tint = (g, base, v, scar = 0) => { const n = g.attributes.position.count, c = new Float32Array(n * 3), b = new THREE.Color(base), s = new THREE.Color(0x5a2420);
    for (let f = 0; f < n; f += 3) { const k = 1 + (R() - .5) * v, col = R() < scar ? s : b; for (let j = 0; j < 3; j++) c.set([col.r * k, col.g * k, col.b * k], (f + j) * 3); }
    g.setAttribute('color', new THREE.BufferAttribute(c, 3)); return g; };
  const skin = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true });
  const mesh = (g, base = 0x4a4a36, v = .35, scar = .07, a = .06) => { const m = new THREE.Mesh(tint(rough(g, a), base, v, scar), skin); m.castShadow = true; m.receiveShadow = true; return m; };
  const flat = c => new THREE.MeshLambertMaterial({ color: c, flatShading: true });

  const root = new THREE.Group(), body = new THREE.Group(); root.add(body); body.position.y = .75;
  // torso: a long, lumpy barrel, wider at the shoulders (+z is forward)
  const torso = mesh(new THREE.CylinderGeometry(.62, .5, 2.6, 9, 4), 0x4b4a38, .4, .14, .12); torso.rotation.x = Math.PI / 2; torso.scale.set(1.15, 1, .85); body.add(torso);
  for (let i = 0; i < 9; i++) { const sp = new THREE.Mesh(new THREE.ConeGeometry(.07 + R() * .05, .3 + R() * .35, 4), flat(0x2a2820)); sp.position.set((R() - .5) * .2, .52 + R() * .08, -1.0 + i * .26); sp.rotation.x = -.5; sp.castShadow = true; body.add(sp); }
  // exposed ribs on one flank, where it never finished growing back
  for (let i = 0; i < 5; i++) { const rib = new THREE.Mesh(new THREE.TorusGeometry(.5, .03, 3, 8, Math.PI * .7), flat(0xcfc6b0)); rib.position.set(.52, .05, -.4 + i * .2); rib.rotation.set(0, Math.PI / 2, -.4); body.add(rib); }
  // neck and head on pivots
  const neck = new THREE.Group(); neck.position.set(0, .15, 1.25); body.add(neck);
  const nm = mesh(new THREE.CylinderGeometry(.34, .45, .8, 8, 2), 0x4f4c39); nm.rotation.x = Math.PI / 2 - .3; nm.position.set(0, .12, .3); neck.add(nm);
  const head = new THREE.Group(); head.position.set(0, .28, .7); neck.add(head);
  const skull = mesh(new THREE.BoxGeometry(.62, .34, .9, 3, 2, 3), 0x55523d, .35, .1, .08); skull.position.set(0, .08, .35); head.add(skull);
  const snout = mesh(new THREE.BoxGeometry(.46, .2, .5, 2, 1, 2), 0x55523d); snout.position.set(0, .04, .9); head.add(snout);
  const jaw = new THREE.Group(); jaw.position.set(0, -.08, .05); head.add(jaw);
  const jm = mesh(new THREE.BoxGeometry(.52, .14, 1.2, 3, 1, 3), 0x4a4634); jm.position.set(0, -.07, .6); jaw.add(jm);
  const mouth = new THREE.Mesh(new THREE.BoxGeometry(.44, .02, 1.05), flat(0x5a1a18)); mouth.position.set(0, .0, .58); jaw.add(mouth);
  for (let i = 0; i < 9; i++) for (const sx of [-1, 1]) {
    const up = new THREE.Mesh(new THREE.ConeGeometry(.025, .12 + R() * .06, 4), flat(0xd8d0b8)); up.position.set(sx * .2, -.08, .2 + i * .1); up.rotation.x = Math.PI; head.add(up);
    const dn = new THREE.Mesh(new THREE.ConeGeometry(.022, .1 + R() * .05, 4), flat(0xd0c8b0)); dn.position.set(sx * .2, .04, .2 + i * .1); jaw.add(dn);
  }
  // eyes: lids that open over a burning orange eye
  const eyes = [];
  for (const sx of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(.065, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff7a1a })); eye.position.set(sx * .3, .17, .55); head.add(eye);
    const pupil = new THREE.Mesh(new THREE.BoxGeometry(.012, .09, .02), new THREE.MeshBasicMaterial({ color: 0x110500 })); pupil.position.set(sx * .3 + sx * .02, .17, .615); head.add(pupil);
    const lid = mesh(new THREE.SphereGeometry(.08, 8, 6, 0, Math.PI * 2, 0, Math.PI / 2), 0x3e3b2c, .2, 0, .01); lid.position.copy(eye.position); lid.rotation.x = Math.PI / 2; head.add(lid);
    eyes.push({ eye, pupil, lid });
  }
  for (const sx of [-1, 1]) { const g = new THREE.Mesh(new THREE.BoxGeometry(.05, .04, .08), flat(0x1a0c08)); g.position.set(sx * .12, .12, 1.15); head.add(g); }  // nostril gills
  // the torn throat
  const gash = new THREE.Mesh(new THREE.BoxGeometry(.3, .06, .5), flat(0x8a1e1a)); gash.position.set(0, -.25, .55); neck.add(gash);
  // legs: shoulder/hip pivots, knees, claws
  const legs = [];
  for (const [x, z, front] of [[-.62, .8, 1], [.62, .8, 1], [-.6, -.8, 0], [.6, -.8, 0]]) {
    const hip = new THREE.Group(); hip.position.set(x, -.1, z); body.add(hip);
    const th = mesh(new THREE.CylinderGeometry(.2, .15, .6, 6), 0x4a4836); th.position.set(Math.sign(x) * .15, -.25, 0); th.rotation.z = Math.sign(x) * .5; hip.add(th);
    const knee = new THREE.Group(); knee.position.set(Math.sign(x) * .3, -.5, 0); hip.add(knee);
    const sh = mesh(new THREE.CylinderGeometry(.13, .1, .5, 6), 0x46432f); sh.position.y = -.2; knee.add(sh);
    for (let c = 0; c < 3; c++) { const cl = new THREE.Mesh(new THREE.ConeGeometry(.03, .18, 4), flat(0x1e1c16)); cl.position.set((c - 1) * .07, -.45, .1); cl.rotation.x = Math.PI / 2 + .4; knee.add(cl); }
    legs.push({ hip, knee, front, side: Math.sign(x) });
  }
  // tail: a chain of shrinking segments
  const tail = []; let parent = body, zt = -1.25;
  for (let i = 0; i < 7; i++) { const seg = new THREE.Group(); seg.position.set(0, i === 0 ? -.05 : 0, i === 0 ? zt : -.45); parent.add(seg);
    const r = .38 * (1 - i / 8); const m = mesh(new THREE.CylinderGeometry(r * .8, r, .5, 7), 0x48463a, .35, .1, .04); m.rotation.x = Math.PI / 2; m.position.z = -.22; seg.add(m); tail.push(seg); parent = seg; }
  root.traverse(n => { if (n.isMesh) { n.castShadow = true; n.receiveShadow = true; } });
  return { root, body, neck, head, jaw, eyes, legs, tail, gash };
}

// state: { breathe 0..1, jaw 0..1, eyeOpen 0..1, lookYaw, lookPitch, rise 0..1 (from lying flat to standing), tremble, lunge 0..1 }
export function poseReptile(r, t, s) {
  const br = Math.sin(t * (1.2 + 2 * (s.breathe || 0))) * (.03 + .03 * (s.breathe || 0));
  const rise = s.rise || 0;
  r.body.position.y = lerpN(.38, .95, rise) + br;
  r.body.rotation.x = -.06 * rise + (s.lunge || 0) * -.15;
  r.body.scale.set(1 + br * .5, 1 + br, 1);
  r.neck.rotation.y = (s.lookYaw || 0) * .5; r.neck.rotation.x = lerpN(.35, -.15, rise) - (s.lookPitch || 0) * .5;
  r.head.rotation.y = (s.lookYaw || 0) * .5; r.head.rotation.x = -(s.lookPitch || 0) * .5 + (s.tremble || 0) * Math.sin(t * 31) * .03;
  r.jaw.rotation.x = (s.jaw || 0) * .7 + Math.max(0, Math.sin(t * 9)) * (s.mutter || 0) * .08;
  for (const e of r.eyes) { e.lid.scale.set(1, 1, 1 - .85 * (s.eyeOpen || 0)); e.lid.position.y = e.eye.position.y + .02 * (s.eyeOpen || 0); e.pupil.visible = (s.eyeOpen || 0) > .3; }
  r.legs.forEach((l, i) => { const ph = t * 6 * (s.walk || 0) + i * Math.PI / 2; l.hip.rotation.x = Math.sin(ph) * .5 * (s.walk || 0) + (l.front ? -.2 : .2) * (1 - rise);
    l.hip.rotation.z = l.side * lerpN(.9, .15, rise); l.knee.rotation.z = -l.side * lerpN(.6, .1, rise); });
  r.tail.forEach((sg, i) => { sg.rotation.y = Math.sin(t * 1.4 - i * .6) * (.08 + .1 * (s.breathe || 0)); sg.rotation.x = i === 0 ? .15 - .2 * rise : .04; });
}
const lerpN = (a, b, k) => a + (b - a) * k;
