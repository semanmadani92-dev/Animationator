"""Sukuna vs SCP-173 (vertical Short, ~20 s). A D-class blinks and 173 snaps his neck. Sukuna walks in
and folds his arms. Every time the lights die, the statue is closer, until it has its hands at his neck.
Then the lights come back on: 173 is already cut to pieces (Dismantle). Sukuna laughs and leaves.
Last shot: the pieces on the floor... the lights flicker... they are gone.

  ~/blendervenv/bin/python sukuna_vs_173.py -- preview|final OUT MODELS_JJK [frames | a-b]
  MODELS_JJK holds yuji/yuji.fbx (bash ../jjk/get_models.sh ~/jjk_models).
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Quaternion, Euler
args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT, MODELS = args[0], args[1], args[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vslib as K
import sukuna
L, V, S, sm, env = K.L, K.V, K.S, K.sm, K.env

# ---------------------------------------------------------------- timing (30 fps)
BLINKS = [(22, 5), (168, 4), (206, 4), (240, 5), (272, 5), (302, 10), (560, 6)]   # (first dark frame, length)
WALK0, WALK1 = 80, 140          # Sukuna walks in
REVEAL, FALL = 312, 340         # lights back on: 173 is already cut; the pieces slide apart
LAUGH, TURN, LEAVE = 350, 392, 404
END = 590
S.render.fps = 30; S.frame_start, S.frame_end = 0, END
A = K.clips()


def dark(t):
    return any(b <= t < b + n for b, n in BLINKS)


def light(t):
    """1 = lights on; flicker into and out of each blackout."""
    for b, n in BLINKS:
        if b <= t < b + n: return 0.0
        if b - 4 <= t < b: return (0.55, 0.1, 0.7, 0.2)[t - b + 4]
        if b + n <= t < b + n + 3: return (0.3, 0.85, 0.6)[t - b - n]
    if t >= END - 4: return 0.0                          # hard cut to black (loops into the cold open)
    return 1.0


# ---------------------------------------------------------------- SCP-173: a concrete statue (the mannequin, frozen)
def concrete():
    m, nt, out = V.nodes_mat("Concrete")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = 0.92
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 14; nz.inputs["Detail"].default_value = 10
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].color = (0.05, 0.045, 0.035, 1); rp.color_ramp.elements[1].color = (0.24, 0.21, 0.16, 1)
    nt.links.new(nz.outputs["Fac"], rp.inputs[0]); nt.links.new(rp.outputs[0], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
    nz2 = nt.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 60
    nt.links.new(nz2.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], b.inputs["Normal"])
    # the Dismantle cuts: glowing red lines where each cut plane crosses the surface (strength keyed)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); total = None
    for k in range(3):
        p0 = nt.nodes.new("ShaderNodeCombineXYZ"); pn = nt.nodes.new("ShaderNodeCombineXYZ")
        sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"
        dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"
        nt.links.new(geo.outputs["Position"], sub.inputs[0]); nt.links.new(p0.outputs[0], sub.inputs[1])
        nt.links.new(sub.outputs[0], dot.inputs[0]); nt.links.new(pn.outputs[0], dot.inputs[1])
        ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; nt.links.new(dot.outputs["Value"], ab.inputs[0])
        lt = nt.nodes.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.006
        nt.links.new(ab.outputs[0], lt.inputs[0])
        CUT_SOCKETS.append((p0, pn))
        if total is None: total = lt
        else:
            ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "ADD"
            nt.links.new(total.outputs[0], ad.inputs[0]); nt.links.new(lt.outputs[0], ad.inputs[1]); total = ad
    g = nt.nodes.new("ShaderNodeMath"); g.operation = "MULTIPLY"; nt.links.new(total.outputs[0], g.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (1.0, 0.06, 0.03, 1)
    nt.links.new(g.outputs[0], em.inputs["Strength"])
    ad = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(b.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
    nt.links.new(ad.outputs[0], out.inputs["Surface"])
    return m, g.inputs[1]


CUT_SOCKETS = []
CONC, CUT_GLOW = concrete()
st = K.mannequin("SCP173", CONC)
paint_r, paint_g = K.pbr("PaintRed", (0.5, 0.02, 0.015), 0.55), K.pbr("PaintGreen", (0.05, 0.3, 0.06), 0.55)
hc = K.bone_mid(st, "Head"); F = Vector((0, -1, 0))
decals = []
for sx in (-1, 1):                                   # spray-painted eyes and the scribbled mouth
    e = V.mesh_obj(f"PaintEye{sx}", V.sphere(0.03, 16), paint_r)
    e.location = hc + F * 0.095 + Vector((sx * 0.042, 0, 0.03)); e.scale = (1.0, 0.35, 1.25); decals.append(e)
mo = V.mesh_obj("PaintMouth", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=20, radius1=0.035, radius2=0.035, depth=0.012), paint_g)
mo.location = hc + F * 0.1 + Vector((0, 0, -0.045)); mo.rotation_euler = (math.pi / 2, 0, 0); mo.scale = (1.3, 1, 0.55); decals.append(mo)
for sx in (-1, 1):
    s = V.mesh_obj(f"PaintCheek{sx}", V.sphere(0.022, 12), paint_g)
    s.location = hc + F * 0.085 + Vector((sx * 0.07, 0.01, -0.02)); s.scale = (0.6, 0.35, 1.6); decals.append(s)
for d in decals: K.attach(d, st, "Head")

STAND = L.sample(A["Idle_Loop"], 0)
AIM = L.sample(A["Pistol_Aim_Neutral"], 2)
REACH = {**STAND, **{k: v for k, v in AIM.items() if k.startswith(("clavicle", "upperarm", "lowerarm", "hand"))}}
LEAN = L.mix(STAND, REACH, 0.45)
LEAN = {**LEAN, "spine_02": (LEAN["spine_02"][0], LEAN["spine_02"][1] @ Quaternion((1, 0, 0), 0.18), LEAN["spine_02"][2])}
# where the statue is after each blackout: (x, y, pose, turned towards Sukuna?)
STATES = [(0.0, -5.6, STAND), (0.05, -3.95, REACH), (0.9, -3.2, STAND), (0.75, -2.3, LEAN), (0.5, -1.5, STAND),
          (0.3, -0.95, LEAN), (0.06, -0.6, REACH), (None, None, None)]


def state(t):
    i = sum(1 for b, n in BLINKS[:6] if t >= b + n // 2)
    return STATES[i]


L.bake(st, [(lambda t: state(t)[2], lambda t: 1)], 0, REVEAL)
def st_path(t):
    x, y, _ = state(t)
    yaw = math.pi if y < -3.5 else K.face(-x, -y)
    return x, y, 0, yaw
K.bake_path(st, st_path, REVEAL)
K.constant(st)

# ---------------------------------------------------------------- the D-class
dmat = K.two_tone("DClass", (0.42, 0.11, 0.02), (0.5, 0.33, 0.25), dirt=0.5)
dc = K.mannequin("DClass", dmat); K.skin_attr(dc)
DB0 = [(L.clip(A["Idle_Loop"], 0, loop=True, speed=1.6), lambda t: 1)]
DB = list(DB0)
snap = lambda t: {**L.pose_at(DB0, t), "neck_01": (Vector(), Quaternion((0, 0, 1), 1.25) @ Quaternion((1, 0, 0), 0.3), Vector((1, 1, 1)))}
DB += [(snap, lambda t: env(t, 25, 26, 30, 34)),
       (L.clip(A["Death01"], 27, speed=1.1), lambda t: env(t, 27, 29))]
L.bake(dc, DB, 0, END)
K.bake_path(dc, lambda t: (0, -3.4, 0, 0), END)

# ---------------------------------------------------------------- Sukuna (the Yuji fan model, repainted)
H = K.Hero(os.path.join(MODELS, "yuji", "yuji.fbx"), 1.78, "Sukuna")
sukuna.apply(H.objs)
laugh = lambda t: (lambda p: {**p, "neck_01": (p["neck_01"][0], p["neck_01"][1] @ Quaternion((1, 0, 0), -0.35 - 0.08 * math.sin(t * 1.9)), p["neck_01"][2]),
                              "spine_03": (p["spine_03"][0], p["spine_03"][1] @ Quaternion((1, 0, 0), -0.12 - 0.05 * math.sin(t * 1.9)), p["spine_03"][2])})(L.pose_at(SB0, t))
SB0 = [(L.clip(A["Walk_Loop"], 0, loop=True), lambda t: 1),
       (L.clip(A["Idle_FoldArms_Loop"], 0, loop=True), lambda t: env(t, WALK1 - 6, WALK1 + 6, TURN, TURN + 8))]
SB = SB0 + [(laugh, lambda t: env(t, LAUGH, LAUGH + 8, TURN - 8, TURN)),
            (L.clip(A["Walk_Loop"], 7, loop=True), lambda t: env(t, TURN + 2, LEAVE))]
def su_path(t):
    if t < WALK1: return 0, 3.0 - 3.0 * min(1, max(0, t - WALK0) / (WALK1 - WALK0)), 0, 0
    if t < LEAVE: return 0, 0, 0, math.pi * sm((t - TURN) / 14)
    return 0, 1.35 * (t - LEAVE) / 30, 0, math.pi
H.drive(SB, su_path, END, track=("Head",))
for o in H.objs:                                         # hidden until he walks in
    if o.type == "MESH":
        o.hide_render = True; o.keyframe_insert("hide_render", frame=0)
        o.hide_render = False; o.keyframe_insert("hide_render", frame=WALK0 - 30)

# ---------------------------------------------------------------- the cut: three Dismantle planes through the statue
S.frame_set(REVEAL); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new()
for o in st.children:
    me = o.evaluated_get(dg).to_mesh(); me.transform(o.matrix_world); bm.from_mesh(me)
centre = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
PLANES = [(centre + Vector((0, 0, 0.42)), Vector((0.55, 0.15, 0.82)).normalized()),
          (centre + Vector((0, 0, -0.05)), Vector((-0.62, 0.1, 0.78)).normalized()),
          (centre + Vector((0, 0, -0.45)), Vector((0.3, -0.05, 0.95)).normalized())]
for (p0, pn), (p, n) in zip(CUT_SOCKETS, PLANES):
    for k in range(3): p0.inputs[k].default_value = p[k]; pn.inputs[k].default_value = n[k]


def split(b, co, no):
    halves = []
    for keep in (0, 1):
        c = b.copy()
        bmesh.ops.bisect_plane(c, geom=c.verts[:] + c.edges[:] + c.faces[:], plane_co=co, plane_no=no,
                               clear_inner=keep == 0, clear_outer=keep == 1)
        bmesh.ops.holes_fill(c, edges=[e for e in c.edges if e.is_boundary], sides=0)
        if len(c.verts) > 30: halves.append(c)
    return halves


parts = [bm]
for p, n in PLANES: parts = [h for b in parts for h in split(b, p, n)]
PIECES = []
for k, b in enumerate(parts):
    c = sum((v.co for v in b.verts), Vector()) / len(b.verts)
    for v in b.verts: v.co -= c
    me = bpy.data.meshes.new(f"Piece{k}"); b.to_mesh(me)
    for poly in me.polygons: poly.use_smooth = False
    me.materials.append(CONC)
    o = bpy.data.objects.new(f"Piece{k}", me); S.collection.objects.link(o); o.location = c
    o.rotation_mode = "QUATERNION"; PIECES.append(o)
head_piece = max(PIECES, key=lambda o: o.location.z)
S.frame_set(REVEAL); bpy.context.view_layer.update()
DECAL_COPIES = []
for d in decals:                                      # the paint goes with the head (a copy rides on the piece)
    c = d.copy(); S.collection.objects.link(c); DECAL_COPIES.append(c)
    mw = d.matrix_world.copy(); c.parent = head_piece; c.parent_type = "OBJECT"
    c.matrix_parent_inverse = Matrix.Identity(4); c.matrix_world = head_piece.matrix_world.inverted() @ mw
    c.matrix_basis = head_piece.matrix_world.inverted() @ mw
    for o, shown in ((d, lambda t: t < REVEAL), (c, lambda t: t >= REVEAL)):
        for t in (0, REVEAL - 1, REVEAL):
            o.hide_render = not shown(t); o.keyframe_insert("hide_render", frame=t)
for o in st.children:
    o.hide_render = False; o.keyframe_insert("hide_render", frame=0)
    o.hide_render = True; o.keyframe_insert("hide_render", frame=REVEAL)

# simple rigid-body fall: gravity, a bounce on the floor, friction, spin
rng = random.Random(3)
g, dt = -9.8, 1 / 30
for o in PIECES:
    pos = o.location.copy(); rot = Quaternion()
    away = (pos - centre); away.z = 0
    v = (away.normalized() * 0.5 if away.length > 1e-3 else Vector()) + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.2))
    w = Vector((rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-1, 1)))
    corners = [Vector(c) for c in o.bound_box]
    for t in range(END + 1):
        if t > FALL:
            for _ in range(4):
                h = dt / 4
                slide = min(1, (t - FALL) / 6)              # first it slides along the cut, then it falls
                v.z += g * h * slide; pos += v * h * slide
                if w.length > 1e-6: rot = Quaternion(w.normalized(), w.length * h * slide) @ rot
                low = min((rot @ c).z for c in corners) + pos.z
                if low < 0:
                    pos.z -= low
                    if v.z < 0: v.z = -v.z * 0.22
                    v.x *= 0.7; v.y *= 0.7; w *= 0.6
        o.location = pos; o.rotation_quaternion = rot
        o.keyframe_insert("location", frame=t); o.keyframe_insert("rotation_quaternion", frame=t)
        o.hide_render = t < REVEAL or t >= BLINKS[-1][0] + 3; o.keyframe_insert("hide_render", frame=t)
# during the last blackout every piece vanishes
HEAD_END = head_piece.location.copy()
b_last = BLINKS[-1][0]
for o in PIECES + DECAL_COPIES:
    o.hide_render = True; o.keyframe_insert("hide_render", frame=b_last + 3)
for t in range(END + 1):
    CUT_GLOW.default_value = 14 * env(t, REVEAL, REVEAL + 2, FALL - 4, FALL + 8) * (1 + 0.3 * math.sin(t * 2.3))
    CUT_GLOW.keyframe_insert("default_value", frame=t)

# dust puffs where the pieces land
dust_m, dnt, dout = V.nodes_mat("Dust")
tc = dnt.nodes.new("ShaderNodeTexCoord"); gr = dnt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
dnt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
dn = dnt.nodes.new("ShaderNodeTexNoise"); dn.inputs["Scale"].default_value = 4
dm = dnt.nodes.new("ShaderNodeMath"); dm.operation = "MULTIPLY"; dnt.links.new(gr.outputs["Fac"], dm.inputs[0]); dnt.links.new(dn.outputs["Fac"], dm.inputs[1])
dk = dnt.nodes.new("ShaderNodeMath"); dk.operation = "MULTIPLY"; dnt.links.new(dm.outputs[0], dk.inputs[0])
pv = dnt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (0.45, 0.42, 0.38, 1)
dnt.links.new(dk.outputs[0], pv.inputs["Density"]); dnt.links.new(pv.outputs[0], dout.inputs["Volume"])
dens = dk.inputs[1]
dust = V.mesh_obj("Dust", V.sphere(1.0, 24), dust_m); dust.location = (centre.x, centre.y, 0.15)
for t in range(END + 1):
    k = t - FALL - 8
    dust.scale = (0.3 + 1.1 * sm(k / 30), 0.3 + 1.1 * sm(k / 30), 0.25 + 0.3 * sm(k / 30)) if k > 0 else (1e-3,) * 3
    dens.default_value = 2.5 * (1 - sm(k / 60)) * (k > 0)
    dust.keyframe_insert("scale", frame=t); dens.keyframe_insert("default_value", frame=t)

# ---------------------------------------------------------------- set, blackouts, camera
strip_s, bg = K.hall(key=0.9)
K.key_lights(light, END, strip_s, 1.0)
hp = HEAD_END
OUTW = Vector((hp.x - centre.x + 0.3, hp.y - centre.y + 0.6, 0)).normalized()
SHOTS = [
    (0,      (0.8, -2.15, 1.66), (0.75, -2.3, 1.64), (0, -5.6, 1.2), (0, -5.6, 1.2), 30),          # over the D-class's shoulder
    (27,     (1.5, -3.0, 1.55), (1.45, -3.1, 1.5), (0, -3.7, 1.4), (0, -3.7, 1.35), 24),          # 173 at his neck
    (44,     (3.6, -2.0, 1.0), (3.7, -2.3, 1.1), (0, -3.2, 0.6), (0, -3.2, 0.6), 15),             # he drops
    (WALK0,  (0.7, 4.6, 1.75), (0.6, 3.2, 1.7), (0, -3, 1.1), (0, -3.5, 1.1), 22),               # Sukuna walks in
    (WALK1,  (0.35, -1.25, 1.62), (0.3, -1.15, 1.62), (0, 0, 1.62), (0, 0, 1.6), 30),            # his face: amused
    (171,    (0.55, 1.3, 1.75), (0.5, 1.2, 1.75), (0.5, -3.2, 1.1), (0.5, -3.2, 1.1), 26),         # over his shoulder: it moved
    (209,    (3.8, -0.9, 1.3), (3.8, -1.0, 1.3), (0.3, -1.6, 1.1), (0.3, -1.6, 1.1), 17),          # side
    (244,    (0.5, 1.1, 1.75), (0.48, 1.0, 1.75), (0.5, -1.5, 1.2), (0.5, -1.5, 1.2), 28),         # closer
    (276,    (0.95, -1.95, 1.55), (0.9, -1.85, 1.55), (0, 0, 1.6), (0, 0, 1.6), 26),              # over 173's shoulder
    (REVEAL, (1.9, -0.4, 1.5), (1.85, -0.5, 1.5), (0.05, -0.35, 1.3), (0.05, -0.35, 1.3), 24),     # the cuts glow
    (FALL - 4, (3.4, -0.6, 1.0), (3.5, -0.8, 1.0), (0.1, -0.6, 0.6), (0.1, -0.6, 0.6), 17),        # it falls apart
    (LAUGH,  (0.6, -2.4, 0.6), (0.55, -2.3, 0.62), (0, 0, 1.35), (0, 0, 1.4), 22),               # he laughs
    (LEAVE - 6, (0.4, 4.2, 1.5), (0.35, 4.0, 1.5), (0, 1.0, 1.3), (0, 2.6, 1.4), 26),             # and leaves
    (480,    (centre.x + 1.9, centre.y + 1.2, 0.85), (centre.x + 1.75, centre.y + 1.05, 0.8), (centre.x, centre.y - 0.2, 0.25), (centre.x, centre.y - 0.2, 0.25), 20),   # the pile... then nothing
]
K.camera(SHOTS, END, shakes=((27, 0.03, 4), (FALL + 10, 0.04, 6)))
K.render(MODE, OUT, "s173", END, args[3:])
