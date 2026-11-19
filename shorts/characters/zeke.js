// Zeke: the recurring main character of the shorts.
// An original blocky 3D character: spiky lime-green hair, orange hoodie with a
// lightning bolt, dark shorts, red sneakers, and a bandage on his cheek.
// Every video builds him from this file, so he always looks the same.
import * as THREE from "three";

export const ZEKE_COLORS = {
  skin: "#f3c79e",
  hair: "#8ee53f",
  hairDark: "#5fb52a",
  hoodie: "#ff7a1a",
  hoodieDark: "#d9580a",
  bolt: "#ffe14a",
  shorts: "#262a40",
  sneaker: "#e8333a",
  sole: "#ffffff",
  outline: "#15161d",
};

const toonRamp = (() => {
  const data = new Uint8Array([90, 170, 255]);
  const tex = new THREE.DataTexture(data, data.length, 1, THREE.RedFormat);
  tex.minFilter = tex.magFilter = THREE.NearestFilter;
  tex.needsUpdate = true;
  return tex;
})();

const toon = (color, map = null) =>
  new THREE.MeshToonMaterial({ color: map ? "#ffffff" : color, map, gradientMap: toonRamp });

function canvasTexture(w, h, draw) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

// Box with a black "inverted hull" outline for the cartoon look.
function part(w, h, d, material, outline = 0.035) {
  const g = new THREE.Group();
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  mesh.castShadow = mesh.receiveShadow = true;
  const hull = new THREE.Mesh(
    new THREE.BoxGeometry(w + outline * 2, h + outline * 2, d + outline * 2),
    new THREE.MeshBasicMaterial({ color: ZEKE_COLORS.outline, side: THREE.BackSide })
  );
  g.add(mesh, hull);
  g.userData.mesh = mesh;
  return g;
}

// ---- Face expressions (drawn on the front of the head) ----
function drawFace(ctx, w, h, expression) {
  ctx.fillStyle = ZEKE_COLORS.skin;
  ctx.fillRect(0, 0, w, h);
  const ink = "#1b1b24";
  const eyeY = h * 0.47;
  const eyeDX = w * 0.2;
  const shocked = expression === "shocked";
  const sad = expression === "sad";
  const happy = expression === "happy";

  // eyebrows
  ctx.strokeStyle = "#3a2a1c";
  ctx.lineWidth = w * 0.05;
  ctx.lineCap = "round";
  // inner end of each brow: lower = determined/angry, higher = sad/worried
  const innerDrop = sad ? -0.045 : shocked || happy ? 0 : 0.035;
  const browY = eyeY - h * (shocked ? 0.25 : 0.17);
  for (const s of [-1, 1]) {
    const cx = w / 2 + s * eyeDX;
    ctx.beginPath();
    ctx.moveTo(cx + s * w * 0.09, browY); // outer end
    ctx.lineTo(cx - s * w * 0.09, browY + innerDrop * h); // inner end
    ctx.stroke();
  }
  // eyes
  for (const s of [-1, 1]) {
    const cx = w / 2 + s * eyeDX;
    if (happy) {
      ctx.strokeStyle = ink;
      ctx.lineWidth = w * 0.045;
      ctx.beginPath();
      ctx.arc(cx, eyeY + h * 0.03, w * 0.07, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();
      continue;
    }
    const r = shocked ? w * 0.095 : w * 0.08;
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.ellipse(cx, eyeY, r, r * 1.2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = w * 0.018;
    ctx.strokeStyle = ink;
    ctx.stroke();
    ctx.fillStyle = ink;
    ctx.beginPath();
    ctx.ellipse(cx + s * w * 0.005, eyeY + h * 0.012, r * (shocked ? 0.38 : 0.55), r * (shocked ? 0.45 : 0.7), 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(cx + w * 0.025, eyeY - h * 0.02, r * 0.2, 0, Math.PI * 2);
    ctx.fill();
  }
  // mouth
  ctx.fillStyle = ink;
  ctx.strokeStyle = ink;
  ctx.lineWidth = w * 0.035;
  const my = h * 0.74;
  ctx.beginPath();
  if (happy) {
    ctx.moveTo(w * 0.33, my - h * 0.03);
    ctx.quadraticCurveTo(w * 0.5, my + h * 0.16, w * 0.67, my - h * 0.03);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(w * 0.38, my - h * 0.02, w * 0.24, h * 0.035);
  } else if (shocked) {
    ctx.ellipse(w * 0.5, my + h * 0.02, w * 0.06, h * 0.08, 0, 0, Math.PI * 2);
    ctx.fill();
  } else if (sad) {
    ctx.moveTo(w * 0.4, my + h * 0.04);
    ctx.quadraticCurveTo(w * 0.5, my - h * 0.04, w * 0.6, my + h * 0.04);
    ctx.stroke();
  } else {
    // determined smirk
    ctx.moveTo(w * 0.4, my);
    ctx.quadraticCurveTo(w * 0.53, my + h * 0.06, w * 0.64, my - h * 0.035);
    ctx.stroke();
  }
  // cheek bandage (his signature detail)
  ctx.save();
  ctx.translate(w * 0.76, h * 0.64);
  ctx.rotate(-0.5);
  ctx.fillStyle = "#f7dfb4";
  ctx.strokeStyle = "#b98b5a";
  ctx.lineWidth = w * 0.01;
  ctx.fillRect(-w * 0.09, -h * 0.03, w * 0.18, h * 0.06);
  ctx.strokeRect(-w * 0.09, -h * 0.03, w * 0.18, h * 0.06);
  ctx.fillStyle = "#e6c592";
  ctx.fillRect(-w * 0.03, -h * 0.03, w * 0.06, h * 0.06);
  ctx.restore();
}

function hoodieFront() {
  return canvasTexture(256, 256, (ctx, w, h) => {
    ctx.fillStyle = ZEKE_COLORS.hoodie;
    ctx.fillRect(0, 0, w, h);
    // pocket
    ctx.fillStyle = ZEKE_COLORS.hoodieDark;
    ctx.fillRect(w * 0.22, h * 0.7, w * 0.56, h * 0.22);
    // lightning bolt
    ctx.fillStyle = ZEKE_COLORS.bolt;
    ctx.strokeStyle = ZEKE_COLORS.outline;
    ctx.lineWidth = 7;
    ctx.beginPath();
    ctx.moveTo(w * 0.56, h * 0.1);
    ctx.lineTo(w * 0.34, h * 0.42);
    ctx.lineTo(w * 0.49, h * 0.42);
    ctx.lineTo(w * 0.4, h * 0.66);
    ctx.lineTo(w * 0.66, h * 0.32);
    ctx.lineTo(w * 0.51, h * 0.32);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  });
}

function luckSprite(text, color) {
  const tex = canvasTexture(512, 256, (ctx, w, h) => {
    ctx.font = "150px 'Luckiest Guy'";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.lineWidth = 26;
    ctx.strokeStyle = "#0d0d12";
    ctx.strokeText(text, w / 2, h / 2 + 10);
    ctx.fillStyle = color;
    ctx.fillText(text, w / 2, h / 2 + 10);
  });
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }));
  sprite.scale.set(2.4, 1.2, 1);
  sprite.renderOrder = 10;
  return sprite;
}

export function createZeke({ expression = "determined", luck = null, luckColor = "#ff3b3b" } = {}) {
  const C = ZEKE_COLORS;
  const zeke = new THREE.Group();
  zeke.name = "Zeke";

  // legs (pivot at hip)
  const makeLeg = (x) => {
    const pivot = new THREE.Group();
    pivot.position.set(x, 1.15, 0);
    const shorts = part(0.48, 0.45, 0.5, toon(C.shorts));
    shorts.position.y = -0.2;
    const shin = part(0.4, 0.55, 0.42, toon(C.skin));
    shin.position.y = -0.68;
    const shoe = part(0.46, 0.22, 0.62, toon(C.sneaker));
    shoe.position.set(0, -1.04, 0.07);
    const sole = part(0.47, 0.07, 0.63, toon(C.sole), 0.02);
    sole.position.set(0, -1.15, 0.07);
    pivot.add(shorts, shin, shoe, sole);
    return pivot;
  };
  const legL = makeLeg(-0.26);
  const legR = makeLeg(0.26);

  // torso (hoodie)
  const torsoMats = [C.hoodie, C.hoodie, C.hoodie, C.hoodieDark, null, C.hoodie].map((c) => (c ? toon(c) : null));
  torsoMats[4] = toon(null, hoodieFront());
  const torso = new THREE.Group();
  const torsoMesh = new THREE.Mesh(new THREE.BoxGeometry(1.05, 1.05, 0.56), torsoMats);
  torsoMesh.castShadow = true;
  const torsoHull = new THREE.Mesh(
    new THREE.BoxGeometry(1.12, 1.12, 0.63),
    new THREE.MeshBasicMaterial({ color: C.outline, side: THREE.BackSide })
  );
  torso.add(torsoMesh, torsoHull);
  torso.position.y = 1.68;
  const hood = part(0.8, 0.28, 0.22, toon(C.hoodieDark));
  hood.position.set(0, 2.15, -0.3);
  const strings = [-0.14, 0.14].map((x) => {
    const s = part(0.04, 0.3, 0.04, toon("#ffffff"), 0.012);
    s.position.set(x, 1.98, 0.3);
    return s;
  });

  // arms (pivot at shoulder)
  const makeArm = (side) => {
    const pivot = new THREE.Group();
    pivot.position.set(side * 0.78, 2.12, 0);
    const sleeve = part(0.42, 0.8, 0.44, toon(C.hoodie));
    sleeve.position.y = -0.36;
    const cuff = part(0.44, 0.1, 0.46, toon(C.hoodieDark), 0.02);
    cuff.position.y = -0.79;
    const hand = part(0.34, 0.28, 0.36, toon(C.skin));
    hand.position.y = -0.98;
    pivot.add(sleeve, cuff, hand);
    return pivot;
  };
  const armL = makeArm(-1);
  const armR = makeArm(1);

  // head with face texture on the front
  const faceCanvas = document.createElement("canvas");
  faceCanvas.width = faceCanvas.height = 256;
  const faceTex = new THREE.CanvasTexture(faceCanvas);
  faceTex.colorSpace = THREE.SRGBColorSpace;
  const skin = toon(C.skin);
  const headMesh = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.0, 1.0), [skin, skin, skin, skin, toon(null, faceTex), skin]);
  headMesh.castShadow = true;
  const headHull = new THREE.Mesh(
    new THREE.BoxGeometry(1.17, 1.07, 1.07),
    new THREE.MeshBasicMaterial({ color: C.outline, side: THREE.BackSide })
  );
  const head = new THREE.Group();
  head.position.y = 2.75;
  head.add(headMesh, headHull);

  // spiky hair: a cap plus blocky spikes
  const hairMat = toon(C.hair);
  const cap = part(1.18, 0.3, 1.08, hairMat);
  cap.position.set(0, 0.42, -0.02);
  const back = part(1.18, 0.6, 0.2, hairMat);
  back.position.set(0, 0.15, -0.48);
  head.add(cap, back);
  const spikes = [
    [-0.38, 0.62, 0.25, 0.35, 0.5],
    [0.0, 0.7, 0.3, 0.0, 0.42],
    [0.38, 0.62, 0.25, -0.35, 0.5],
    [-0.25, 0.68, -0.2, 0.25, -0.25],
    [0.25, 0.68, -0.2, -0.25, -0.25],
    [0.0, 0.62, -0.4, 0.0, -0.6],
  ];
  for (const [x, y, z, rz, rx] of spikes) {
    const geo = new THREE.ConeGeometry(0.24, 0.62, 4);
    const spike = new THREE.Mesh(geo, toon(Math.abs(rz) > 0.2 ? C.hairDark : C.hair));
    spike.position.set(x, y, z);
    spike.rotation.set(rx, Math.PI / 4, rz);
    spike.castShadow = true;
    const hull = new THREE.Mesh(
      new THREE.ConeGeometry(0.27, 0.68, 4),
      new THREE.MeshBasicMaterial({ color: C.outline, side: THREE.BackSide })
    );
    spike.add(hull);
    head.add(spike);
  }
  // front fringe
  const fringe = part(1.0, 0.16, 0.1, hairMat, 0.02);
  fringe.position.set(0, 0.3, 0.52);
  fringe.rotation.x = -0.25;
  head.add(fringe);

  zeke.add(legL, legR, torso, hood, ...strings, armL, armR, head);

  const api = {
    group: zeke,
    head,
    torso,
    armL,
    armR,
    legL,
    legR,
    luck: null,
    setExpression(expr) {
      drawFace(faceCanvas.getContext("2d"), 256, 256, expr);
      faceTex.needsUpdate = true;
    },
    setLuck(text, color = "#ff3b3b") {
      if (api.luck) zeke.remove(api.luck);
      api.luck = text == null ? null : luckSprite(text, color);
      if (api.luck) {
        api.luck.position.set(0, 4.05, 0);
        zeke.add(api.luck);
      }
    },
  };
  api.setExpression(expression);
  if (luck != null) api.setLuck(luck, luckColor);
  return api;
}
