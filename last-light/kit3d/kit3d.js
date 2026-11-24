// Last Light 3D kit: shared loader, D-class character, deterministic animation, low-res retro post pass.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
export { THREE };
const loader = new GLTFLoader();
export const load = url => loader.loadAsync(url);

export async function loadMannequins(base = '../assets/animation/') {
  // both libraries on the Unreal-named rig, so all ~88 clips drive one skeleton
  const [a, b] = await Promise.all([load(base + 'UAL2_mannequin_43anims.glb'), load(base + 'UAL1_unreal_rig_45anims.glb')]);
  for (const c of b.animations) c.name = c.name.replace(/^.*\|/, '');
  const names = new Set(a.animations.map(c => c.name));
  return { scene: a.scene, clips: [...a.animations, ...b.animations.filter(c => !names.has(c.name))] };
}

const SKIN = /head|neck|hand|index|middle|ring|pinky|thumb/i, BOOT = /foot|ball|toe/i;
// A D-class: orange jumpsuit, bare head and hands, dark boots, a simple face and a chest number patch.
export function makeHuman(lib, o = {}) {
  const opt = Object.assign({ suit: 0xc4561c, skin: 0xd2a88c, boots: 0x262220, number: 'D-4172', face: true, cap: null }, o);
  const root = SkeletonUtils.clone(lib.scene); root.updateMatrixWorld(true);
  const bones = {}; let mesh0 = null;
  root.traverse(n => { if (n.isBone) bones[n.name] = n; });
  const bone = nm => bones[nm.replace(/[.\[\]:\/]/g, '')];
  root.traverse(n => {
    if (!n.isSkinnedMesh) return; mesh0 = mesh0 || n;
    const g = n.geometry = n.geometry.clone(), si = g.attributes.skinIndex, sw = g.attributes.skinWeight, cnt = g.attributes.position.count;
    const col = new Float32Array(cnt * 3), seam = n.material.name === 'M_Joints';
    for (let i = 0; i < cnt; i++) {
      let best = 0, bw = -1; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; best = si.getComponent(i, k); } }
      const nm = n.skeleton.bones[best].name;
      let c = new THREE.Color(SKIN.test(nm) ? opt.skin : BOOT.test(nm) ? opt.boots : opt.suit);
      if (seam && !SKIN.test(nm)) c.multiplyScalar(.72);
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    n.material = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true });
    n.castShadow = true; n.receiveShadow = true; n.frustumCulled = false;
  });
  // world-space bounding box of the vertices driven by a bone (rest pose)
  const region = (re) => {
    const box = new THREE.Box3(), v = new THREE.Vector3();
    root.traverse(n => { if (!n.isSkinnedMesh) return; const g = n.geometry, si = g.attributes.skinIndex, sw = g.attributes.skinWeight;
      for (let i = 0; i < g.attributes.position.count; i++) {
        let best = 0, bw = -1; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; best = si.getComponent(i, k); } }
        if (!re.test(n.skeleton.bones[best].name)) continue;
        v.fromBufferAttribute(g.attributes.position, i); n.applyBoneTransform(i, v); v.applyMatrix4(n.matrixWorld); box.expandByPoint(v);
      } });
    return box;
  };
  const head = region(/^Head$/), chest = region(/spine_03/);
  const fwd = 1;  // characters face +z
  const flat = c => new THREE.MeshLambertMaterial({ color: c, flatShading: true });
  // stick a flat feature onto the body surface by raycasting from the front
  const meshes = []; root.traverse(n => { if (n.isSkinnedMesh) meshes.push(n); });
  const ray = new THREE.Raycaster();
  const stick = (obj, x, y, boneName, lift = .003) => {
    ray.set(new THREE.Vector3(x, y, 5 * fwd), new THREE.Vector3(0, 0, -fwd));
    const hit = ray.intersectObjects(meshes, false)[0]; if (!hit) return;
    const nrm = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
    obj.position.copy(hit.point).addScaledVector(nrm, lift); obj.lookAt(obj.position.clone().add(nrm));
    root.add(obj); bone(boneName).attach(obj);
    obj.userData.base = { p: obj.position.clone(), q: obj.quaternion.clone(), s: obj.scale.clone() };
    return obj;
  };
  const face = { eyes: [], brows: [], tears: [], mouth: null };
  const basic = c => new THREE.MeshBasicMaterial({ color: c });
  if (opt.face) {
    const hc = head.getCenter(new THREE.Vector3()), hs = head.getSize(new THREE.Vector3());
    for (const sx of [-1, 1]) {
      face.eyes.push(stick(new THREE.Mesh(new THREE.PlaneGeometry(hs.x * .12, hs.y * .045), basic(0x15110e)), hc.x + sx * hs.x * .17, hc.y + hs.y * .02, 'Head'));
      const brow = stick(new THREE.Mesh(new THREE.PlaneGeometry(hs.x * .17, hs.y * .022), basic(0x3a2618)), hc.x + sx * hs.x * .17, hc.y + hs.y * .1, 'Head', .005);
      brow.userData.side = sx; face.brows.push(brow);
      for (let k = 0; k < 2; k++) {  // tears, hidden until needed
        const tear = stick(new THREE.Mesh(new THREE.PlaneGeometry(hs.x * .03, hs.y * .05), new THREE.MeshBasicMaterial({ color: 0xcfe4ff, transparent: true, opacity: .85 })), hc.x + sx * hs.x * (.13 + k * .07), hc.y - hs.y * .02, 'Head', .008);
        tear.visible = false; tear.userData.k = k; face.tears.push(tear);
      }
    }
    face.mouth = stick(new THREE.Mesh(new THREE.PlaneGeometry(hs.x * .2, hs.y * .022), basic(0x4a2620)), hc.x, hc.y - hs.y * .2, 'Head');
    face.up = new THREE.Vector3(0, 1, 0).applyQuaternion(bone('Head').getWorldQuaternion(new THREE.Quaternion()).invert());
    face.hs = hs.y;
    stick(new THREE.Mesh(new THREE.PlaneGeometry(hs.x * .07, hs.y * .09), new THREE.MeshLambertMaterial({ color: opt.skin })), hc.x, hc.y - hs.y * .07, 'Head', .012);  // nose
    // buzz cut: a dark shell over the top of the head
    const hair = new THREE.Mesh(new THREE.SphereGeometry(.5, 9, 6, 0, Math.PI * 2, 0, Math.PI * .4), new THREE.MeshLambertMaterial({ color: 0x2a211b, flatShading: true }));
    hair.scale.set(hs.x * 1.2, hs.y * 1.06, hs.z * 1.2); hair.position.set(hc.x, hc.y + hs.y * .05, hc.z - hs.z * .07); root.add(hair); bone('Head').attach(hair);
  }
  if (opt.number) {  // chest patch with the prisoner number
    const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const x = cv.getContext('2d');
    x.fillStyle = '#e9e4d8'; x.fillRect(0, 0, 256, 128); x.fillStyle = '#1c1a18'; x.font = 'bold 64px Inter, Arial'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(opt.number, 128, 68);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    const cs = chest.getSize(new THREE.Vector3()), cc = chest.getCenter(new THREE.Vector3());
    const patch = new THREE.Mesh(new THREE.PlaneGeometry(cs.x * .32, cs.x * .16), new THREE.MeshLambertMaterial({ map: tex }));
    patch.position.set(cc.x + cs.x * .2, cc.y + cs.y * .12, (fwd > 0 ? chest.max.z : chest.min.z) + .004 * fwd); root.add(patch); bone('spine_03').attach(patch);
  }
  if (opt.cap) {  // e.g. a guard helmet
    const hc = head.getCenter(new THREE.Vector3()), hs = head.getSize(new THREE.Vector3());
    const cap = new THREE.Mesh(new THREE.SphereGeometry(.5, 8, 5, 0, Math.PI * 2, 0, Math.PI * .5), flat(opt.cap));
    cap.scale.set(hs.x * 1.2, hs.y * 1.05, hs.z * 1.2); cap.position.set(hc.x, hc.y + hs.y * .05, hc.z); root.add(cap); bone('Head').attach(cap);
  }
  const mixer = new THREE.AnimationMixer(root), actions = {};
  for (const c of lib.clips) { const a = mixer.clipAction(c); a.enabled = true; a.setEffectiveWeight(0); a.play(); actions[c.name] = a; }
  return { root, bones, bone, mixer, actions, head, chest, face: opt.face ? face : null };
}

// Deterministic pose: segs = [{clip, t0, speed=1, offset=0, hold=false}]; crossfades `fade` seconds into each new segment.
export function pose(h, segs, t, fade = .25) {
  let i = 0; for (let k = 0; k < segs.length; k++) if (t >= segs[k].t0) i = k;
  for (const a of Object.values(h.actions)) a.setEffectiveWeight(0);
  const set = (s, w) => { const a = h.actions[s.clip]; if (!a) throw new Error('no clip ' + s.clip);
    let tt = (t - s.t0) * (s.speed || 1) + (s.offset || 0); const d = a.getClip().duration;
    tt = s.hold ? Math.min(tt, d - .001) : ((tt % d) + d) % d;
    a.time = tt; a.setEffectiveWeight(a.getEffectiveWeight() + w); };
  const k = i > 0 ? Math.min(1, (t - segs[i].t0) / fade) : 1;
  if (k < 1) set(segs[i - 1], 1 - k);
  set(segs[i], k);
  h.mixer.update(0);
}

// Low-res render + nearest upscale + ordered dither + vignette + grain (+ red burn at the edges).
export function makeRetro(renderer, w, h) {
  const rt = new THREE.WebGLRenderTarget(w, h, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter });
  const mat = new THREE.ShaderMaterial({
    uniforms: { tex: { value: rt.texture }, t: { value: 0 }, burn: { value: 0 }, fade: { value: 1 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }',
    fragmentShader: `uniform sampler2D tex; uniform float t, burn, fade; varying vec2 vUv;
      float bayer(vec2 p){ int i=int(mod(p.x,4.))+int(mod(p.y,4.))*4; float m[16];
        m[0]=0.;m[1]=8.;m[2]=2.;m[3]=10.;m[4]=12.;m[5]=4.;m[6]=14.;m[7]=6.;m[8]=3.;m[9]=11.;m[10]=1.;m[11]=9.;m[12]=15.;m[13]=7.;m[14]=13.;m[15]=5.;
        for(int k=0;k<16;k++){ if(k==i) return m[k]/16.; } return 0.; }
      float hh(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + t*7.) * 43758.5453); }
      void main(){ vec2 px = floor(vUv * vec2(${w}., ${h}.));
        vec3 c = texture2D(tex, (px + .5) / vec2(${w}., ${h}.)).rgb;
        float lv = 24.; c = floor(c * lv + bayer(px)) / lv;
        vec2 d = vUv - .5; float v = 1. - smoothstep(.3, .8, length(d * vec2(1., 1.2)));
        c *= mix(.3, 1., v); c = mix(c, c * vec3(1.25, .45, .4), burn * (1. - v * .7));
        c += (hh(px) - .5) * .04; gl_FragColor = vec4(c * fade, 1.); }`
  });
  const sc = new THREE.Scene(); sc.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat)); const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  return { u: mat.uniforms, render(scene, camera, t) { mat.uniforms.t.value = t; renderer.setRenderTarget(rt); renderer.render(scene, camera); renderer.setRenderTarget(null); renderer.render(sc, cam); } };
}

export function makeRenderer(canvas) {
  const r = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true });
  r.setSize(1080, 1920, false); r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFShadowMap; r.outputColorSpace = THREE.SRGBColorSpace;
  return r;
}

// Fear on the face: f 0..1 (wide eyes, raised and pinched brows, open trembling mouth), tears 0..1 (running tears).
export function setFear(h, f, t, tears = 0) {
  const F = h.face; if (!F) return;
  const zq = new THREE.Quaternion(), Z = new THREE.Vector3(0, 0, 1);
  for (const e of F.eyes) { const b = e.userData.base; e.scale.set(b.s.x * (1 - .08 * f), b.s.y * (1 + .6 * f), 1); }
  for (const w of F.brows) { const b = w.userData.base, sx = w.userData.side;
    w.position.copy(b.p).addScaledVector(F.up, F.hs * .05 * f);
    w.quaternion.copy(b.q).multiply(zq.setFromAxisAngle(Z, -sx * .38 * f)); }
  { const m = F.mouth, b = m.userData.base, tr = 1 + Math.sin(t * 31) * .25 * f;
    m.scale.set(b.s.x * (1 - .3 * f), b.s.y * (1 + 3 * f * tr), 1); m.position.copy(b.p).addScaledVector(F.up, -F.hs * .03 * f); }
  for (const d of F.tears) { const b = d.userData.base; d.visible = tears > 0 && (d.userData.k === 0 || tears > .6);
    if (!d.visible) continue; const run = ((t * .5 + d.userData.k * .37) % 1);
    d.position.copy(b.p).addScaledVector(F.up, -F.hs * (.05 + .3 * run * tears)); d.scale.set(.8, .8 + 1.2 * run, 1); d.material.opacity = .85 * (1 - run * .6) * Math.min(1, tears * 2); }
}

// Fear in the body, applied after pose(): fast shallow breathing, trembling, and a flinch (0..1) that throws the head and chest back.
export function bodyFear(h, f, t, flinch = 0) {
  const b = n => h.bone(n), rate = 2.0 + 6 * f;
  b('spine_02').rotation.x += Math.sin(t * rate) * (.015 + .03 * f);
  b('spine_03').rotation.x += Math.sin(t * rate) * (.01 + .02 * f) - .3 * flinch;
  const tr = .012 * f; b('Head').rotation.x += Math.sin(t * 37) * tr - .25 * flinch; b('Head').rotation.z += Math.sin(t * 29 + 1) * tr;
  for (const s of ['l', 'r']) { b('hand_' + s).rotation.z += Math.sin(t * 41 + (s === 'l' ? 0 : 2)) * .08 * f; b('lowerarm_' + s).rotation.x += Math.sin(t * 33) * .03 * f; }
}
