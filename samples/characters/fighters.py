"""Two original anime fighters on MB-Lab's anime male base (see mbchar.py).

  SORCERER  white upswept hair, black blindfold, navy high-collar jacket and trousers.
  ONI KING  crimson swept-back hair, red eyes plus a second pair below, black face and
            forearm markings, white kimono top, charcoal hakama, dark red sash.

Clothes, blindfold and markings are shells cut from the body mesh itself, so they keep
its skin weights and follow every animation. Hair is curve locks parented to the head.

    import fighters; arm, parts = fighters.build("sorcerer")      # or "oni"
    ~/blendervenv/bin/python fighters.py -- OUT_DIR                # line-up render
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mbchar


def pbr(name, rgb, rough=0.6, sheen=0.0, coat=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if coat: b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = emit
    return m


# ---------------------------------------------------------------- body analysis
class Body:
    def __init__(self, arm, mesh):
        self.arm, self.mesh = arm, mesh
        me = mesh.data
        names = {g.index: g.name for g in mesh.vertex_groups}
        self.vw = [{names[g.group]: g.weight for g in v.groups} for v in me.vertices]
        self.co = [v.co.copy() for v in me.vertices]
        self.dom_v = [max(w, key=w.get) if w else "" for w in self.vw]
        self.dom = []
        for p in me.polygons:
            tot = {}
            for i in p.vertices:
                for n, w in self.vw[i].items(): tot[n] = tot.get(n, 0) + w
            self.dom.append(max(tot, key=tot.get) if tot else "")
        self.mi = [p.material_index for p in me.polygons]
        eyes = [p for p in me.polygons if p.material_index == 3]
        self.eye_faces = [p.index for p in eyes]
        ec = [p.center for p in eyes]
        self.eye_l = sum((c for c in ec if c.x > 0), Vector()) / max(1, len([c for c in ec if c.x > 0]))
        self.eye_r = sum((c for c in ec if c.x < 0), Vector()) / max(1, len([c for c in ec if c.x < 0]))
        self.eye_z = (self.eye_l.z + self.eye_r.z) / 2
        head = [self.co[i] for i, w in enumerate(self.vw) if w.get("head", 0) > 0.6]
        self.head_top = max(c.z for c in head)
        self.head_c = sum(head, Vector()) / len(head)
        self.head_front = min(c.y for c in head)

    def bone_t(self, bone, c):
        b = self.arm.data.bones[bone]
        h, t = b.head_local, b.tail_local
        return (c - h).dot(t - h) / (t - h).length_squared

    def shell(self, name, keep, offset, mat, thick=0.0, subsurf=1, extra_move=None, smooth=0, fix_normals=False):
        """Copy of the body keeping faces where keep(poly_index, centre, normal, dom_bone)."""
        me = self.mesh.data.copy()
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        drop = [f for f in bm.faces if not keep(f.index, f.calc_center_median(), f.normal, self.dom[f.index])]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        if fix_normals:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if extra_move:
            for v in bm.verts: v.co = extra_move(v.co)
        bm.to_mesh(me); bm.free()
        if mat is not None:
            me.materials.clear(); me.materials.append(mat)
            for p in me.polygons: p.material_index = 0
        o = self.mesh.copy(); o.data = me; o.name = name
        bpy.context.scene.collection.objects.link(o)
        for md in list(o.modifiers): o.modifiers.remove(md)
        for s in o.material_slots: s.link = "DATA"
        if smooth:
            sm = o.modifiers.new("Smooth", "SMOOTH"); sm.factor = 1.0; sm.iterations = smooth
        if offset:
            d = o.modifiers.new("Push", "DISPLACE"); d.direction = "NORMAL"; d.mid_level = 0; d.strength = offset
        if thick:
            s = o.modifiers.new("Thick", "SOLIDIFY"); s.thickness = thick; s.offset = 1
        a = o.modifiers.new("Armature", "ARMATURE"); a.object = self.arm
        if subsurf:
            s = o.modifiers.new("Subsurf", "SUBSURF"); s.levels = s.render_levels = subsurf
        return o


TORSO = ("pelvis", "spine01", "spine02", "spine03", "clavicle_L", "clavicle_R", "breast_L", "breast_R")
ARM_UP = ("upperarm_L", "upperarm_R", "upperarm_twist_L", "upperarm_twist_R")
ARM_LO = ("lowerarm_L", "lowerarm_R", "lowerarm_twist_L", "lowerarm_twist_R")
LEGS = ("thigh_L", "thigh_R", "thigh_twist_L", "thigh_twist_R", "calf_L", "calf_R", "calf_twist_L", "calf_twist_R")
FEET = ("foot_L", "foot_R", "toes_L", "toes_R")


# ---------------------------------------------------------------- hair
def attach(obj, arm, bone):
    b = arm.data.bones[bone]
    tail = arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    obj.parent, obj.parent_type, obj.parent_bone = arm, "BONE", bone
    obj.matrix_parent_inverse = tail.inverted()


def hair(body, name, mat, seed, n, style, length, width, hairline_drop, fringe=0):
    """Anime hair: tapered, curved curve-locks rooted on the scalp, plus a scalp cap."""
    rng = random.Random(seed)
    hc, top = body.head_c, body.head_top
    hl_z = body.eye_z + hairline_drop            # front hairline height
    scalp = []
    for i, w in enumerate(body.vw):
        if w.get("head", 0) < 0.6: continue
        c = body.co[i]; nrm = body.mesh.data.vertices[i].normal
        front = c.y < hc.y - 0.02
        if c.z < (hl_z + 0.01 if front else body.eye_z + 0.035): continue
        if nrm.z < -0.2: continue
        scalp.append((c, nrm))
    cap = body.shell(name + "_Cap", lambda i, c, nrm, d: d == "head" and (
        c.z > (hl_z - 0.004 if c.y < hc.y - 0.02 else body.eye_z - 0.035) and body.mi[i] == 2), 0.004, mat)

    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = width; cu.bevel_resolution = 2; cu.resolution_u = 8
    cu.use_fill_caps = True
    for k in range(n):
        c, nrm = scalp[rng.randrange(len(scalp))]
        out = (c - hc).normalized()
        d = (out * 0.6 + nrm * 0.4 + style(c, out)).normalized()
        L = rng.uniform(*length)
        p0 = c - nrm * 0.01
        p1 = c + nrm * 0.02 + d * L * 0.35
        bend = style(c, out) * 0.06
        p2 = c + d * L * 0.75 + bend * L
        p3 = c + d * L + bend * L * 1.6
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(3)
        for bp, p, r in zip(sp.bezier_points, (p0, p1, p2, p3), (1.0, 0.8, 0.4, 0.0)):
            bp.co = p; bp.radius = r * rng.uniform(0.85, 1.15)
            bp.handle_left_type = bp.handle_right_type = "AUTO"
    for k in range(fringe):                       # locks falling over the forehead
        x = rng.uniform(-0.055, 0.055)
        root = Vector((x, hc.y - 0.06, top - 0.03))
        tip = Vector((x * 1.3, body.head_front - 0.025, hl_z - rng.uniform(0.0, 0.03)))
        mid = (root + tip) / 2 + Vector((0, -0.04, 0.02))
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(2)
        for bp, p, r in zip(sp.bezier_points, (root, mid, tip), (0.9, 0.75, 0.0)):
            bp.co = p; bp.radius = r; bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    attach(o, body.arm, "head")
    return [cap, o]


def hair_mat(name, rgb, tip_rgb=None):
    m = pbr(name, rgb, 0.38, sheen=0.6, coat=0.25)
    return m



def is_hand(d):
    return d.startswith(("hand", "thumb", "index", "middle", "ring", "pinky"))


def band(body, name, mat, z0, half_h, pad, bone):
    """Cloth band fitted to the body's cross-section at height z0 (e.g. a sash)."""
    ring = [c for i, c in enumerate(body.co) if abs(c.z - z0) < half_h and not is_hand(body.dom_v[i])
            and abs(c.x) < 0.25]
    xs = [c.x for c in ring]; ys = [c.y for c in ring]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    rx, ry = (max(xs) - min(xs)) / 2 + pad, (max(ys) - min(ys)) / 2 + pad
    bm = bmesh.new(); segs = 48; rings = []
    for dz, dr in ((-half_h, 0), (half_h, 0), (half_h, 0.008), (-half_h, 0.008)):
        rv = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            rv.append(bm.verts.new((cx + (rx + dr) * math.cos(a), cy + (ry + dr) * math.sin(a), z0 + dz)))
        rings.append(rv)
    for k in range(4):
        r0, r1 = rings[k], rings[(k + 1) % 4]
        for i in range(segs):
            j = (i + 1) % segs; bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    s = o.modifiers.new("Subsurf", "SUBSURF"); s.levels = s.render_levels = 1
    attach(o, body.arm, bone)
    return o


def blindfold(body, mat):
    """Band fitted to the head's cross-section at eye level, parented to the head bone."""
    z0 = body.eye_z
    ring = [c for i, c in enumerate(body.co) if abs(c.z - z0 - 0.014) < 0.03 and
            (body.vw[i].get("head", 0) > 0.5 or body.mi[i] in (0, 3))]
    xmax = max(abs(c.x) for c in ring) + 0.006
    ymin = min(c.y for c in ring) - 0.006; ymax = max(c.y for c in ring) + 0.006
    cy, ry = (ymin + ymax) / 2, (ymax - ymin) / 2
    bm = bmesh.new(); segs = 48; rings = []
    for (dz, dr) in ((-0.026, 0), (0.026, 0), (0.026, 0.005), (-0.026, 0.005)):
        ring_v = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            ca, sa = math.cos(a), math.sin(a)
            # superellipse: squarer front/back like a cloth band
            x = (xmax + dr) * math.copysign(abs(ca) ** 0.8, ca)
            y = cy + (ry + dr) * math.copysign(abs(sa) ** 0.8, sa)
            ring_v.append(bm.verts.new((x, y, z0 + 0.014 + dz + 0.012 * max(0, sa))))   # tilt: higher at back
        rings.append(ring_v)
    for k in range(4):
        r0, r1 = rings[k], rings[(k + 1) % 4]
        for i in range(segs):
            j = (i + 1) % segs; bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    me = bpy.data.meshes.new("Blindfold"); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new("Sorc_Blindfold", me); bpy.context.scene.collection.objects.link(o)
    s = o.modifiers.new("Subsurf", "SUBSURF"); s.levels = s.render_levels = 1
    attach(o, body.arm, "head")
    return o


def paint_oni_marks(body):
    """Paint black markings into a copy of the skin texture, placed by 3D position on the face."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import barycentric_transform, intersect_point_tri
    me = body.mesh.data
    skin = me.materials[2]
    node = next(n for n in skin.node_tree.nodes if n.type == "TEX_IMAGE")
    src = node.image
    W, H = src.size
    px = np.empty(W * H * 4, dtype=np.float32); src.pixels.foreach_get(px); px = px.reshape(H, W, 4)
    verts = [v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    uvl = me.uv_layers[0].data
    loops = [list(p.loop_indices) for p in me.polygons]

    def uv_at(x, z, from_y=-1.0):
        loc, nrm, fi, _ = bvh.ray_cast(Vector((x, from_y, z)), Vector((0, 1, 0)))
        if fi is None or body.mi[fi] not in (2,): return None
        vs, ls = polys[fi], loops[fi]
        for a, b, c in ((0, 1, 2), (0, 2, 3)) if len(vs) == 4 else ((0, 1, 2),):
            A, B, C = verts[vs[a]], verts[vs[b]], verts[vs[c]]
            uA, uB, uC = (uvl[ls[k]].uv.to_3d() for k in (a, b, c))
            uv = barycentric_transform(loc, A, B, C, uA, uB, uC)
            if intersect_point_tri(loc, A, B, C) or (a, b, c) == (0, 2, 3) or len(vs) == 3:
                return uv.x, uv.y
        return None

    def stroke(pts, width):
        """pts: list of (x, z) on the face; paints a tapered line."""
        n = 60
        for k in range(n + 1):
            t = k / n
            seg = min(int(t * (len(pts) - 1)), len(pts) - 2); u = t * (len(pts) - 1) - seg
            x = pts[seg][0] * (1 - u) + pts[seg + 1][0] * u
            z = pts[seg][1] * (1 - u) + pts[seg + 1][1] * u
            uv = uv_at(x, z)
            if not uv: continue
            r = width * (1 - abs(t - 0.5) * 0.9) * W
            cx, cy = uv[0] * W, uv[1] * H
            x0, x1 = int(max(0, cx - r - 2)), int(min(W, cx + r + 2))
            y0, y1 = int(max(0, cy - r - 2)), int(min(H, cy + r + 2))
            yy, xx = np.mgrid[y0:y1, x0:x1]
            d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            a = np.clip(r - d + 0.5, 0, 1)[..., None]
            px[y0:y1, x0:x1, :3] = px[y0:y1, x0:x1, :3] * (1 - a) + 0.03 * a

    ez = body.eye_z
    for s in (1, -1):
        ex = abs(body.eye_l.x) * s
        for dz in (-0.03, -0.041):                                   # two stripes under each eye
            stroke([(ex - s * 0.012, ez + dz + 0.004), (ex + s * 0.006, ez + dz), (ex + s * 0.03, ez + dz + 0.006)], 0.0026)
        stroke([(s * 0.012, ez + 0.05), (s * 0.03, ez + 0.042)], 0.0022)   # brow marks
    out = bpy.data.images.new(body.mesh.name + "_skin_marked", W, H, alpha=True)
    out.pixels.foreach_set(px.ravel()); out.pack()
    node.image = out
    # the overlay (slot 0) and copied eyes use the same material, so they pick this up too


# ---------------------------------------------------------------- designs
def sorcerer(body):
    parts = []
    navy = pbr("Sorc_Jacket", (0.025, 0.03, 0.06), 0.7, sheen=0.4)
    trou = pbr("Sorc_Trousers", (0.02, 0.022, 0.04), 0.75, sheen=0.3)
    shoe = pbr("Sorc_Shoes", (0.01, 0.01, 0.012), 0.3, coat=0.5)
    blind = pbr("Sorc_Blindfold", (0.006, 0.006, 0.008), 0.85, sheen=0.2)
    white = hair_mat("Sorc_Hair", (0.9, 0.92, 0.97))
    hz = body.eye_z
    parts.append(body.shell("Sorc_Jacket", lambda i, c, n, d: body.mi[i] in (1, 2) and not is_hand(d) and d not in LEGS + FEET + ("head",) and
                            not (d == "neck" and c.z > 1.53) and c.z > 0.94, 0.013, navy, fix_normals=True, smooth=4))
    parts.append(body.shell("Sorc_Collar", lambda i, c, n, d: d in ("neck", "spine03", "clavicle_L", "clavicle_R") and c.z > 1.36
                            and body.mi[i] == 2, 0.024, navy, smooth=2))
    parts.append(body.shell("Sorc_Trousers", lambda i, c, n, d: body.mi[i] in (1, 2) and (d in LEGS or
                            (d == "pelvis" and c.z < 0.97)), 0.01, trou, fix_normals=True))
    parts.append(body.shell("Sorc_Shoes", lambda i, c, n, d: d in FEET or (d in ("calf_L", "calf_R") and c.z < 0.13),
                            0.016, shoe, subsurf=2, smooth=25))
    parts.append(blindfold(body, blind))
    up = lambda c, out: Vector((out.x * 0.7, out.y * 0.3 + 0.1, 1.0))       # gravity-defying, splayed
    parts += hair(body, "Sorc_Hair", white, 11, 170, up, (0.09, 0.17), 0.0125, 0.06, fringe=7)
    return parts


def oni(body):
    parts = []
    robe = pbr("Oni_Kimono", (0.82, 0.8, 0.74), 0.8, sheen=0.5)
    hakama = pbr("Oni_Hakama", (0.07, 0.065, 0.07), 0.8, sheen=0.4)
    sash = pbr("Oni_Sash", (0.25, 0.02, 0.03), 0.6, sheen=0.4)
    sandal = pbr("Oni_Sandals", (0.05, 0.035, 0.025), 0.6)
    ink = pbr("Oni_Ink", (0.012, 0.01, 0.01), 0.55)
    hairm = hair_mat("Oni_Hair", (0.85, 0.27, 0.38))
    eye2 = pbr("Oni_Eye2", (0.9, 0.05, 0.03), 0.2, coat=0.6, emit=0.6)
    parts.append(body.shell("Oni_Kimono", lambda i, c, n, d: (d in TORSO and c.z > 1.0) or d in ARM_UP or
                            (d == "neck" and c.z < 1.45) or
                            (d in ARM_LO and body.bone_t(d.replace("_twist", ""), c) < 0.25), 0.02, robe, smooth=4))
    parts.append(body.shell("Oni_Hakama", lambda i, c, n, d: body.mi[i] in (1, 2) and (d in LEGS or
                            (d in ("pelvis", "spine01") and c.z <= 1.07)), 0.03, hakama, fix_normals=True, smooth=3))
    parts.append(band(body, "Oni_Sash", sash, 1.045, 0.035, 0.045, "pelvis"))
    parts.append(body.shell("Oni_Sandals", lambda i, c, n, d: d in FEET and c.z < 0.06, 0.006, sandal))
    # forearm bands
    def forearm_band(i, c, n, d):
        if d not in ARM_LO: return False
        t = body.bone_t(d.replace("_twist", ""), c)
        return any(a < t < a + 0.06 for a in (0.38, 0.55, 0.72))
    parts.append(body.shell("Oni_ArmInk", forearm_band, 0.0035, ink))
    # face markings: two stripes under each eye, marks above the brows
    def face(i, c, n, d):
        if d != "head" or n.y > -0.35: return False
        for e in (body.eye_l, body.eye_r):
            dx = abs(c.x - e.x)
            if dx < 0.02 and (e.z - 0.036 < c.z < e.z - 0.029 or e.z - 0.05 < c.z < e.z - 0.043): return True
            if abs(c.x - e.x * 0.6) < 0.008 and e.z + 0.03 < c.z < e.z + 0.05: return True
        return False
    paint_oni_marks(body)
    # second, smaller pair of eyes below the first (copies of the eye + lid geometry)
    drop = Vector((0, -0.006, -0.03))
    def move(c):
        e = body.eye_l if c.x > 0 else body.eye_r
        return e + (c - e) * 0.6 + drop

    back = lambda c, out: Vector((out.x * 0.4, 0.9, 0.55))                  # swept back and up
    parts += hair(body, "Oni_Hair", hairm, 5, 160, back, (0.07, 0.13), 0.012, 0.075, fringe=0)
    return parts


BODIES = {
    "sorcerer": {"Torso_Mass": .85, "Torso_Tone": 1.0, "Shoulders_Mass": .85, "Shoulders_Tone": 1.0, "Torso_Vshape": .9,
                 "Arms_UpperarmMass": .8, "Arms_UpperarmTone": .95, "Arms_ForearmMass": .75, "Arms_ForearmTone": .9,
                 "Neck_Size": .65, "Legs_UpperlegsMass": .75, "Legs_UpperlegsTone": .9, "Legs_UpperlegLength": .7,
                 "Legs_LowerlegLength": .65, "Torso_Length": .6},
    "oni": {"Torso_Mass": 1.2, "Torso_Tone": 1.25, "Shoulders_Mass": 1.2, "Shoulders_Tone": 1.2, "Torso_Vshape": 1.0,
            "Arms_UpperarmMass": 1.2, "Arms_UpperarmTone": 1.25, "Arms_ForearmMass": 1.1, "Arms_ForearmTone": 1.15,
            "Neck_Size": .9, "Neck_Mass": 1.0, "Neck_Tone": 1.0, "Legs_UpperlegsMass": 1.0, "Legs_UpperlegsTone": 1.1,
            "Shoulders_SizeX": .8, "Torso_SizeX": .75, "Back_SizeX": .75},
}


def build(kind):
    name = {"sorcerer": "Sorcerer", "oni": "Oni"}[kind]
    arm, mesh = mbchar.load_base(name, BODIES[kind])
    if kind == "sorcerer":
        mbchar.skin_materials(mesh, name=name, skin_tint=(1.0, 0.97, 0.95))
    else:
        mats = mbchar.skin_materials(mesh, name=name, skin_tint=(0.95, 0.86, 0.8), eye_rgb=(1, 0.05, 0.03), eye_glow=0.6)
        hsv = next(n for n in mats["eyes"].node_tree.nodes if n.type == "HUE_SAT")
        hsv.inputs["Hue"].default_value = 0.03; hsv.inputs["Saturation"].default_value = 1.6
    mesh.data.materials[0] = mesh.data.materials[2]       # MB's eyelid/lash overlay uses the skin texture
    hide = bpy.data.materials.new(name + "_Hidden")            # underwear: hidden under the clothes
    hide.node_tree.nodes.remove(hide.node_tree.nodes["Principled BSDF"])
    tr = hide.node_tree.nodes.new("ShaderNodeBsdfTransparent")
    hide.node_tree.links.new(tr.outputs[0], hide.node_tree.nodes["Material Output"].inputs["Surface"])
    mesh.data.materials[1] = hide
    body = Body(arm, mesh)
    parts = (sorcerer if kind == "sorcerer" else oni)(body)
    return arm, mesh, parts


# ---------------------------------------------------------------- line-up
if __name__ == "__main__":
    OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/fighters"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    S = bpy.context.scene; S.render.fps = 30
    rigs = {k: build(k)[0] for k in ("sorcerer", "oni")}
    bpy.ops.import_scene.gltf(filepath="/home/user/Animationator/toolkit/3d-pack/animation/UAL1_unreal_rig_45anims.glb")
    src = bpy.data.objects["Rig"]
    for o in list(bpy.data.objects):
        if o.name in ("Mannequin", "Cube", "Camera", "Light", "Icosphere"): bpy.data.objects.remove(o)
    src.hide_render = True
    a = bpy.data.actions["Rig|Rig|Idle_Loop"]; src.animation_data_create()
    src.animation_data.action = a; src.animation_data.action_slot = a.slots[0]
    S.frame_set(18)
    for k, x, turn in (("sorcerer", 0.5, 15), ("oni", -0.5, -15)):
        rig = rigs[k]; rig.location.x = x; rig.rotation_euler.z = math.radians(turn)
        bpy.context.view_layer.update()
        mbchar.Retarget(src, rig).apply()

    bpy.ops.mesh.primitive_plane_add(size=30)
    bpy.context.active_object.data.materials.append(pbr("Floor", (0.045, 0.045, 0.05), 0.65))
    w = bpy.data.worlds.new("W"); S.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.022, 0.03, 1)
    for nm, loc, rot, e, c in (("Key", (-2.2, -3.2, 3.4), (50, 0, -35), 650, (1, 0.95, 0.9)),
                               ("Fill", (3, -3, 1.8), (65, 0, 45), 220, (0.8, 0.85, 1)),
                               ("Rim", (0.5, 3, 3), (-55, 0, 175), 700, (0.7, 0.8, 1))):
        ld = bpy.data.lights.new(nm, "AREA"); ld.energy = e; ld.size = 2.5; ld.color = c
        o = bpy.data.objects.new(nm, ld); S.collection.objects.link(o)
        o.location = loc; o.rotation_euler = [math.radians(v) for v in rot]
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); S.collection.objects.link(cam); S.camera = cam
    S.render.engine = "CYCLES"; S.cycles.samples = int(os.environ.get("SAMPLES", 32)); S.cycles.use_denoising = True
    S.view_settings.view_transform = "AgX"; S.view_settings.look = "AgX - Medium High Contrast"
    S.render.resolution_x, S.render.resolution_y = 1280, 720

    def shoot(loc, target, lens, path):
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        S.render.filepath = path; bpy.ops.render.render(write_still=True)
    shoot((0, -4.4, 1.15), (0, 0, 0.92), 40, f"{OUT}/lineup.png")
    hs = rigs["sorcerer"].matrix_world @ rigs["sorcerer"].pose.bones["head"].head
    ho = rigs["oni"].matrix_world @ rigs["oni"].pose.bones["head"].head
    shoot(hs + Vector((0.12, -0.9, 0.08)), hs + Vector((0, 0, 0.07)), 70, f"{OUT}/sorcerer_face.png")
    shoot(ho + Vector((-0.12, -0.9, 0.08)), ho + Vector((0, 0, 0.07)), 70, f"{OUT}/oni_face.png")
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/fighters.blend")
