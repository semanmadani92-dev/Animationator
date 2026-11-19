// Zeke's bedroom: plank walls, wooden floor, bed, clothes rack, shelf with alarm clock.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

function tex(w, h, draw, repeat = [1, 1]) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repeat);
  t.anisotropy = 8;
  return t;
}

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

const std = (o) => new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0, ...o });

function rbox(w, h, d, mat, r = 0.05) {
  const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, r), mat);
  m.castShadow = m.receiveShadow = true;
  return m;
}

// Soft cloth noise for bedding.
function cloth(color, seed) {
  return tex(256, 256, (ctx, w, h) => {
    const r = rng(seed);
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 14; i++) {
      ctx.save();
      ctx.translate(r() * w, r() * h);
      ctx.rotate((r() - 0.5) * 2);
      const g = ctx.createLinearGradient(0, -16, 0, 16);
      g.addColorStop(0, "rgba(0,0,0,0)");
      g.addColorStop(0.5, `rgba(90,60,20,${0.05 + r() * 0.07})`);
      g.addColorStop(1, "rgba(255,255,255,0.05)");
      ctx.fillStyle = g;
      ctx.fillRect(-w * 0.3, -16, w * 0.6, 32);
      ctx.restore();
    }
  });
}

function shirt(color, seed) {
  const g = new THREE.Group();
  const mat = std({ map: cloth(color, seed), side: THREE.DoubleSide });
  const body = rbox(0.62, 0.95, 0.06, mat, 0.03);
  body.position.y = -0.55;
  const shoulders = rbox(0.95, 0.22, 0.06, mat, 0.03);
  shoulders.position.y = -0.14;
  const hanger = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.012, 8, 16, Math.PI * 1.4), std({ color: "#8a8f99", metalness: 0.6, roughness: 0.4 }));
  hanger.rotation.z = Math.PI * 0.8;
  g.add(body, shoulders, hanger);
  return g;
}

function alarmClock() {
  const g = new THREE.Group();
  const shell = std({ color: "#c9c4b8", metalness: 0.3, roughness: 0.45 });
  const face = tex(256, 256, (ctx, w, h) => {
    ctx.fillStyle = "#f4efe4";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#333";
    ctx.lineCap = "round";
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.moveTo(w / 2 + Math.cos(a) * w * 0.36, h / 2 + Math.sin(a) * h * 0.36);
      ctx.lineTo(w / 2 + Math.cos(a) * w * 0.42, h / 2 + Math.sin(a) * h * 0.42);
      ctx.stroke();
    }
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(w / 2, h / 2);
    ctx.lineTo(w / 2, h * 0.22);
    ctx.moveTo(w / 2, h / 2);
    ctx.lineTo(w * 0.68, h * 0.55);
    ctx.stroke();
  });
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.12, 32), [shell, std({ map: face, roughness: 0.4 }), shell]);
  body.rotation.x = Math.PI / 2;
  body.castShadow = true;
  g.add(body);
  for (const s of [-1, 1]) {
    const bell = new THREE.Mesh(new THREE.SphereGeometry(0.09, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), shell);
    bell.position.set(s * 0.15, 0.2, 0);
    bell.rotation.z = -s * 0.5;
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.12), shell);
    leg.position.set(s * 0.13, -0.24, 0);
    leg.rotation.z = s * 0.4;
    g.add(bell, leg);
  }
  return g;
}

export function createBedroom() {
  const room = new THREE.Group();

  // walls: horizontal planks
  const planks = tex(512, 512, (ctx, w, h) => {
    const r = rng(5);
    for (let y = 0; y < h; y += 32) {
      const v = 228 + Math.floor(r() * 14);
      ctx.fillStyle = `rgb(${v},${v - 2},${v - 6})`;
      ctx.fillRect(0, y, w, 32);
      ctx.fillStyle = "rgba(0,0,0,0.10)";
      ctx.fillRect(0, y + 30, w, 2);
    }
  }, [3, 2]);
  const wallMat = std({ map: planks, roughness: 0.9 });
  const back = new THREE.Mesh(new THREE.PlaneGeometry(14, 7), wallMat);
  back.position.set(0, 3.5, -3);
  back.receiveShadow = true;
  const side = new THREE.Mesh(new THREE.PlaneGeometry(10, 7), wallMat);
  side.position.set(-6, 3.5, 2);
  side.rotation.y = Math.PI / 2;
  side.receiveShadow = true;

  // wooden floor
  const wood = tex(512, 512, (ctx, w, h) => {
    const r = rng(8);
    for (let x = 0; x < w; x += 64) {
      const v = r() * 18;
      ctx.fillStyle = `rgb(${168 + v},${120 + v},${78 + v})`;
      ctx.fillRect(x, 0, 64, h);
      ctx.fillStyle = "rgba(60,30,10,0.25)";
      ctx.fillRect(x + 62, 0, 2, h);
      for (let i = 0; i < 6; i++) {
        ctx.fillStyle = `rgba(90,50,20,${0.05 + r() * 0.08})`;
        ctx.fillRect(x + r() * 60, r() * h, 2, 40 + r() * 120);
      }
    }
  }, [4, 4]);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 12), std({ map: wood, roughness: 0.6 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.z = 2;
  floor.receiveShadow = true;

  // ceiling trim (dark wood beam like the reference rooms)
  const beam = rbox(14, 0.4, 0.4, std({ color: "#5a3a22", roughness: 0.6 }), 0.04);
  beam.position.set(0, 6.8, -2.8);

  room.add(back, side, floor, beam);

  // bed
  const bed = new THREE.Group();
  const frame = rbox(3.0, 0.5, 4.2, std({ color: "#b98a5c", roughness: 0.55 }), 0.05);
  frame.position.y = 0.25;
  const mattress = rbox(2.85, 0.45, 4.0, std({ color: "#f3f1ec" }), 0.15);
  mattress.position.y = 0.72;
  const blanket = rbox(2.95, 0.3, 2.7, std({ map: cloth("#f3d35a", 3) }), 0.14);
  blanket.position.set(0, 0.98, 0.7);
  const fold = rbox(2.95, 0.22, 0.45, std({ map: cloth("#f6de7c", 4) }), 0.1);
  fold.position.set(0, 1.12, -0.55);
  bed.add(frame, mattress, blanket, fold);
  for (const [x, c, s] of [[-0.7, "#efe3c6", 9], [0.7, "#f2c75a", 10]]) {
    const p = rbox(1.25, 0.42, 0.75, std({ map: cloth(c, s) }), 0.2);
    p.position.set(x, 1.13, -1.45);
    p.rotation.x = -0.35;
    bed.add(p);
  }
  bed.position.set(1.2, 0, -0.9);
  bed.userData.surfaceY = 1.1;
  room.add(bed);

  // clothes rack with hanging shirts
  const rodMat = std({ color: "#7a5434", roughness: 0.5 });
  const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 4.2, 16), rodMat);
  rod.rotation.z = Math.PI / 2;
  rod.position.set(-1.2, 5.0, -2.7);
  rod.castShadow = true;
  room.add(rod);
  ["#f08a24", "#f3a33f", "#f4f1ea", "#d9583e", "#ecebe6"].forEach((c, i) => {
    const s = shirt(c, 40 + i);
    s.position.set(-2.8 + i * 0.75, 5.0, -2.6);
    s.rotation.y = 0.15;
    room.add(s);
  });

  // wall shelf with alarm clock
  const shelf = rbox(1.6, 0.1, 0.5, std({ color: "#8a5a36", roughness: 0.5 }), 0.02);
  shelf.position.set(3.4, 4.0, -2.72);
  const sideL = rbox(0.1, 0.9, 0.5, std({ color: "#8a5a36" }), 0.02);
  sideL.position.set(2.65, 4.4, -2.72);
  const sideR = sideL.clone();
  sideR.position.x = 4.15;
  const top = shelf.clone();
  top.position.y = 4.85;
  const clock = alarmClock();
  clock.position.set(3.4, 4.36, -2.62);
  room.add(shelf, sideL, sideR, top, clock);

  return { group: room, bed };
}

// Soft, warm interior lighting with image-based fill.
export function lightBedroom(scene, renderer, RoomEnvironment) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.55;
  scene.background = new THREE.Color("#e9e4dc");

  const key = new THREE.DirectionalLight("#fff1dc", 2.2);
  key.position.set(4, 8, 6);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.radius = 6;
  key.shadow.bias = -0.0004;
  Object.assign(key.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 30 });
  scene.add(key);

  const fill = new THREE.DirectionalLight("#dfe8ff", 0.5);
  fill.position.set(-6, 4, 4);
  scene.add(fill);
}
