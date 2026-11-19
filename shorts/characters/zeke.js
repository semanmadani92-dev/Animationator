// Zeke: the recurring main character of the shorts.
// Original blocky character rendered with realistic materials: fluffy lime-green
// hair, orange hoodie, navy shorts, red sneakers, bandage on his cheek.
// Every video builds him from this file, so he always looks the same.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

export const ZEKE_COLORS = {
  skin: "#f1c6a0",
  hair: "#7fd332",
  hoodie: "#ff7a1a",
  shorts: "#2a2f4a",
  sneaker: "#e3343b",
  sole: "#f4f4f4",
};

function canvasTexture(w, h, draw) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

// Seeded random so the fabric looks identical in every video.
function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

// Base colour + soft noise + a few fold shadows: reads as cloth under real lighting.
function fabric(ctx, w, h, color, seed, folds = 6) {
  const r = rng(seed);
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, w, h);
  ctx.filter = "blur(10px)";
  for (let i = 0; i < folds; i++) {
    const x = r() * w, y = r() * h, len = (0.3 + r() * 0.5) * w, ang = (r() - 0.5) * 1.2;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(ang);
    ctx.fillStyle = `rgba(0,0,0,${0.05 + r() * 0.05})`;
    ctx.beginPath();
    ctx.ellipse(0, 0, len / 2, 9, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.05)";
    ctx.beginPath();
    ctx.ellipse(0, -14, len / 2.4, 6, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  ctx.filter = "none";
  const img = ctx.getImageData(0, 0, w, h);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = (r() - 0.5) * 14;
    img.data[i] += n;
    img.data[i + 1] += n;
    img.data[i + 2] += n;
  }
  ctx.putImageData(img, 0, 0);
}

const std = (opts) => new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0, ...opts });
const fabricMat = (color, seed, folds) => std({ map: canvasTexture(256, 256, (c, w, h) => fabric(c, w, h, color, seed, folds)) });

function rbox(w, h, d, material, radius = 0.06) {
  const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, radius), material);
  m.castShadow = m.receiveShadow = true;
  return m;
}

// ---- Anime-style face, drawn on the front of the head ----
function drawFace(ctx, w, h, expression) {
  ctx.fillStyle = ZEKE_COLORS.skin;
  ctx.fillRect(0, 0, w, h);
  const ink = "#2a1d18";
  const eyeY = h * 0.5, dx = w * 0.19;
  const e = expression;

  // blush
  ctx.fillStyle = e === "happy" || e === "shocked" ? "rgba(255,110,110,0.35)" : "rgba(255,120,120,0.15)";
  for (const s of [-1, 1]) {
    ctx.beginPath();
    ctx.ellipse(w / 2 + s * w * 0.27, h * 0.63, w * 0.07, h * 0.035, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  // brows
  ctx.strokeStyle = "#4b6e22";
  ctx.lineCap = "round";
  ctx.lineWidth = w * 0.025;
  const innerDrop = e === "sad" ? -0.035 : e === "determined" ? 0.03 : 0;
  const browY = eyeY - h * (e === "shocked" ? 0.2 : 0.15);
  for (const s of [-1, 1]) {
    const cx = w / 2 + s * dx;
    ctx.beginPath();
    ctx.moveTo(cx + s * w * 0.07, browY);
    ctx.lineTo(cx - s * w * 0.06, browY + innerDrop * h);
    ctx.stroke();
  }
  // eyes
  for (const s of [-1, 1]) {
    const cx = w / 2 + s * dx;
    ctx.strokeStyle = ink;
    ctx.fillStyle = ink;
    if (e === "happy" || e === "sleepy") {
      ctx.lineWidth = w * 0.022;
      ctx.beginPath();
      if (e === "happy") ctx.arc(cx, eyeY + h * 0.02, w * 0.05, Math.PI * 1.15, Math.PI * 1.85);
      else ctx.arc(cx, eyeY - h * 0.01, w * 0.05, Math.PI * 0.15, Math.PI * 0.85);
      ctx.stroke();
      continue;
    }
    const rx = w * 0.045, ry = h * (e === "shocked" ? 0.075 : 0.065);
    ctx.beginPath();
    ctx.ellipse(cx, eyeY, rx, ry, 0, 0, Math.PI * 2);
    ctx.fill();
    // iris tint + shine
    ctx.fillStyle = "#3f7d2a";
    ctx.beginPath();
    ctx.ellipse(cx, eyeY + ry * 0.35, rx * 0.7, ry * 0.45, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(cx - rx * 0.3, eyeY - ry * 0.4, rx * 0.38, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx + rx * 0.35, eyeY + ry * 0.25, rx * 0.16, 0, Math.PI * 2);
    ctx.fill();
    // upper lash line
    ctx.lineWidth = w * 0.018;
    ctx.beginPath();
    ctx.moveTo(cx - rx * 1.25, eyeY - ry * 0.85 + (s > 0 ? 0 : -2));
    ctx.quadraticCurveTo(cx, eyeY - ry * 1.25, cx + rx * 1.25, eyeY - ry * 0.85);
    ctx.stroke();
  }
  // mouth
  const my = h * 0.7;
  ctx.fillStyle = "#6b2a26";
  ctx.strokeStyle = ink;
  ctx.lineWidth = w * 0.016;
  ctx.beginPath();
  if (e === "happy") {
    ctx.moveTo(w * 0.42, my - h * 0.01);
    ctx.quadraticCurveTo(w * 0.5, my + h * 0.08, w * 0.58, my - h * 0.01);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  } else if (e === "shocked") {
    ctx.ellipse(w * 0.5, my + h * 0.01, w * 0.03, h * 0.045, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  } else if (e === "sad") {
    ctx.moveTo(w * 0.45, my + h * 0.02);
    ctx.quadraticCurveTo(w * 0.5, my - h * 0.015, w * 0.55, my + h * 0.02);
    ctx.stroke();
  } else if (e === "sleepy") {
    ctx.ellipse(w * 0.5, my, w * 0.015, h * 0.012, 0, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.moveTo(w * 0.45, my);
    ctx.quadraticCurveTo(w * 0.52, my + h * 0.025, w * 0.57, my - h * 0.015);
    ctx.stroke();
  }
  // cheek bandage: his signature detail
  ctx.save();
  ctx.translate(w * 0.73, h * 0.6);
  ctx.rotate(-0.45);
  ctx.fillStyle = "#f6dcb0";
  ctx.strokeStyle = "rgba(150,110,70,0.6)";
  ctx.lineWidth = 2;
  ctx.fillRect(-w * 0.065, -h * 0.022, w * 0.13, h * 0.044);
  ctx.strokeRect(-w * 0.065, -h * 0.022, w * 0.13, h * 0.044);
  ctx.fillStyle = "#e8c896";
  ctx.fillRect(-w * 0.022, -h * 0.022, w * 0.044, h * 0.044);
  ctx.restore();
}

function drawHoodieFront(ctx, w, h, number, numberColor) {
  fabric(ctx, w, h, ZEKE_COLORS.hoodie, 7, 8);
  // kangaroo pocket
  ctx.fillStyle = "rgba(0,0,0,0.10)";
  ctx.fillRect(w * 0.2, h * 0.72, w * 0.6, h * 0.2);
  ctx.strokeStyle = "rgba(0,0,0,0.18)";
  ctx.lineWidth = 3;
  ctx.strokeRect(w * 0.2, h * 0.72, w * 0.6, h * 0.2);
  // drawstrings
  ctx.strokeStyle = "#f2f2f2";
  ctx.lineWidth = 6;
  for (const x of [0.42, 0.58]) {
    ctx.beginPath();
    ctx.moveTo(w * x, 0);
    ctx.lineTo(w * x, h * 0.22);
    ctx.stroke();
  }
  // printed number (changes during the story)
  if (number) {
    const size = number.length > 4 ? 0.23 : 0.3;
    ctx.font = `900 ${Math.round(w * size)}px Nunito`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.lineWidth = w * 0.04;
    ctx.strokeStyle = "#101010";
    ctx.strokeText(number, w / 2, h * 0.47);
    ctx.fillStyle = numberColor;
    ctx.fillText(number, w / 2, h * 0.47);
  }
}

export function createZeke({ expression = "determined", number = null, numberColor = "#16e03c" } = {}) {
  const C = ZEKE_COLORS;
  const zeke = new THREE.Group();
  zeke.name = "Zeke";
  const skin = std({ color: C.skin, roughness: 0.7 });

  // legs (pivot at hip)
  const makeLeg = (x, seed) => {
    const pivot = new THREE.Group();
    pivot.position.set(x, 1.1, 0);
    const shorts = rbox(0.5, 0.5, 0.52, fabricMat(C.shorts, seed, 5), 0.07);
    shorts.position.y = -0.22;
    const shin = rbox(0.44, 0.5, 0.46, skin, 0.08);
    shin.position.y = -0.68;
    const shoe = rbox(0.48, 0.2, 0.62, std({ color: C.sneaker, roughness: 0.6 }), 0.08);
    shoe.position.set(0, -1.0, 0.06);
    const sole = rbox(0.5, 0.08, 0.64, std({ color: C.sole, roughness: 0.9 }), 0.03);
    sole.position.set(0, -1.08, 0.06);
    pivot.add(shorts, shin, shoe, sole);
    return pivot;
  };
  const legL = makeLeg(-0.26, 11);
  const legR = makeLeg(0.26, 12);

  // torso with printed front
  const frontCanvas = document.createElement("canvas");
  frontCanvas.width = frontCanvas.height = 512;
  const frontTex = new THREE.CanvasTexture(frontCanvas);
  frontTex.colorSpace = THREE.SRGBColorSpace;
  frontTex.anisotropy = 8;
  const hoodieSide = fabricMat(C.hoodie, 21, 7);
  const torsoMesh = new THREE.Mesh(new RoundedBoxGeometry(1.04, 1.04, 0.54, 4, 0.08), [
    hoodieSide, hoodieSide, hoodieSide, hoodieSide, std({ map: frontTex }), hoodieSide,
  ]);
  torsoMesh.castShadow = torsoMesh.receiveShadow = true;
  const torso = new THREE.Group();
  torso.position.y = 1.62;
  torso.add(torsoMesh);
  const hood = rbox(0.78, 0.26, 0.24, fabricMat(C.hoodie, 23, 4), 0.1);
  hood.position.set(0, 0.5, -0.3);
  torso.add(hood);

  // arms (pivot at shoulder)
  const makeArm = (side, seed) => {
    const pivot = new THREE.Group();
    pivot.position.set(side * 0.77, 2.08, 0);
    const sleeve = rbox(0.48, 0.82, 0.5, fabricMat(C.hoodie, seed, 6), 0.08);
    sleeve.position.y = -0.36;
    const hand = rbox(0.42, 0.26, 0.44, skin, 0.08);
    hand.position.y = -0.9;
    pivot.add(sleeve, hand);
    return pivot;
  };
  const armL = makeArm(-1, 31);
  const armR = makeArm(1, 32);

  // head with anime face
  const faceCanvas = document.createElement("canvas");
  faceCanvas.width = faceCanvas.height = 512;
  const faceTex = new THREE.CanvasTexture(faceCanvas);
  faceTex.colorSpace = THREE.SRGBColorSpace;
  faceTex.anisotropy = 8;
  const head = new THREE.Group();
  head.position.y = 2.6;
  const headMesh = new THREE.Mesh(new RoundedBoxGeometry(0.98, 0.92, 0.9, 5, 0.2), [
    skin, skin, skin, skin, std({ map: faceTex, roughness: 0.7 }), skin,
  ]);
  headMesh.castShadow = headMesh.receiveShadow = true;
  head.add(headMesh);

  // fluffy hair: clumps of soft blobs plus a few swept spikes
  const r = rng(99);
  const hairMat = (k) =>
    std({ color: new THREE.Color(C.hair).offsetHSL(0, 0, (k - 0.5) * 0.1), roughness: 0.45 });
  const blob = (x, y, z, sx, sy, sz, rx = 0, rz = 0) => {
    const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28, 2), hairMat(r()));
    m.position.set(x, y, z);
    m.scale.set(sx, sy, sz);
    m.rotation.set(rx, 0, rz);
    m.castShadow = true;
    head.add(m);
  };
  // crown and back
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2;
    blob(Math.cos(a) * 0.32, 0.4 + r() * 0.06, Math.sin(a) * 0.3 - 0.05, 1.0, 0.7, 1.0);
  }
  blob(0, 0.5, -0.02, 1.5, 0.6, 1.4);
  for (const x of [-0.3, 0, 0.3]) blob(x, 0.1, -0.42, 0.9, 1.1, 0.5);
  // fringe swept across the forehead
  for (const [x, rz] of [[-0.3, 0.5], [-0.08, 0.25], [0.15, -0.1], [0.34, -0.45]]) {
    blob(x, 0.3, 0.38, 0.6, 0.75, 0.45, 0.4, rz);
  }
  // side tufts
  for (const s of [-1, 1]) blob(s * 0.47, 0.18, 0.05, 0.4, 0.8, 0.8);
  // swept anime spikes: long tapered clumps leaning back and out
  for (const [x, z, rx, rz, len] of [
    [-0.3, 0.1, -0.7, 0.75, 0.9], [-0.1, 0.12, -0.8, 0.25, 1.0], [0.12, 0.12, -0.8, -0.2, 1.0],
    [0.32, 0.08, -0.7, -0.7, 0.9], [-0.18, -0.15, -1.1, 0.4, 0.95], [0.18, -0.15, -1.1, -0.4, 0.95],
  ]) {
    const spike = new THREE.Mesh(new THREE.SphereGeometry(0.17, 20, 14), hairMat(r()));
    spike.geometry.translate(0, 0.17, 0);
    spike.scale.set(1, len * 2.2, 0.8);
    spike.position.set(x, 0.45, z);
    spike.rotation.set(rx, 0, rz);
    spike.castShadow = true;
    head.add(spike);
  }

  zeke.add(legL, legR, torso, armL, armR, head);

  const api = {
    group: zeke,
    head,
    torso,
    armL,
    armR,
    legL,
    legR,
    number,
    numberColor,
    expression,
    setExpression(expr) {
      api.expression = expr;
      drawFace(faceCanvas.getContext("2d"), 512, 512, expr);
      faceTex.needsUpdate = true;
    },
    setNumber(text, color = api.numberColor) {
      api.number = text;
      api.numberColor = color;
      drawHoodieFront(frontCanvas.getContext("2d"), 512, 512, text, color);
      frontTex.needsUpdate = true;
    },
  };
  api.setExpression(expression);
  api.setNumber(number, numberColor);
  return api;
}
