"""Two mannequins: A jabs, crosses, then front-kicks B, who falls back.

Run:  ~/blendervenv/bin/python fight.py -- preview OUT_DIR   (low-res key frames)
      ~/blendervenv/bin/python fight.py -- final   OUT_DIR   (720p PNG frames + fight.blend)

Every frame is a weighted blend of clip "layers" (idle, guard, jab, cross, kick,
hit reactions) using smoothstep envelopes, then baked to one action per rig, so
clip changes never pop. The kick is hand-keyed because the pack has none.
"""
import bpy, sys, math
from mathutils import Vector, Quaternion, Matrix

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = ARGS[0] if ARGS else "preview"
OUT = ARGS[1] if len(ARGS) > 1 else "/tmp/fight"
PACK = "/home/user/Animationator/toolkit/3d-pack/animation/"
FPS, END = 30, 170
GAP = 0.80            # distance between the two dummies (m)

bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
S.render.fps = FPS
S.frame_start, S.frame_end = 0, END


def imp(path):
    before = set(bpy.data.objects)
    acts = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:  # drop the camera/light/cube/icosphere that ship in the files
        if o.type not in ("ARMATURE",) and not (o.type == "MESH" and o.name.startswith("Mannequin")):
            bpy.data.objects.remove(o)
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    mesh = next(o for o in new if o.type == "MESH")
    newacts = {a.name.split("|")[-1].split(".")[0]: a for a in bpy.data.actions if a not in acts}
    if rig.animation_data:
        rig.animation_data.action = None
    return rig, mesh, newacts


rigA, meshA, ACT = imp(PACK + "UAL1_unreal_rig_45anims.glb")
rigB, meshB, _ = imp(PACK + "UAL1_unreal_rig_45anims.glb")
r2, m2, ACT2 = imp(PACK + "UAL2_mannequin_43anims.glb")
ACT.update({k: v for k, v in ACT2.items() if k.startswith("Hit_Knockback")})
for a in ACT.values():
    a.use_fake_user = True
bpy.data.objects.remove(m2); bpy.data.objects.remove(r2)
rigB.location = (0, -GAP, 0)
rigB.rotation_mode = "XYZ"
rigB.rotation_euler = (0, 0, math.pi)
BONES = [b.name for b in rigA.pose.bones]

# ---------------------------------------------------------------- sampling
_CH = {}


def channels(act):
    if act.name not in _CH:
        d = {}
        cb = act.layers[0].strips[0].channelbags[0]
        for fc in cb.fcurves:
            if fc.data_path.startswith("pose.bones["):
                bone = fc.data_path.split('"')[1]
                prop = fc.data_path.rsplit(".", 1)[1]
                d.setdefault(bone, {}).setdefault(prop, {})[fc.array_index] = fc
        _CH[act.name] = d
    return _CH[act.name]


IDENT = (Vector((0, 0, 0)), Quaternion(), Vector((1, 1, 1)))


def sample(act, f):
    pose = {}
    for b, props in channels(act).items():
        l, q, s = IDENT
        if "location" in props:
            l = Vector([props["location"][i].evaluate(f) if i in props["location"] else 0 for i in range(3)])
        if "rotation_quaternion" in props:
            q = Quaternion([props["rotation_quaternion"][i].evaluate(f) if i in props["rotation_quaternion"] else (1 if i == 0 else 0) for i in range(4)]).normalized()
        if "scale" in props:
            s = Vector([props["scale"][i].evaluate(f) if i in props["scale"] else 1 for i in range(3)])
        pose[b] = (l, q, s)
    return pose


def mix(a, b, w):
    """Blend pose b over pose a with weight w (0..1)."""
    if w <= 0: return a
    if w >= 1: return b
    out = {}
    for bone in set(a) | set(b):
        la, qa, sa = a.get(bone, IDENT); lb, qb, sb = b.get(bone, IDENT)
        out[bone] = (la.lerp(lb, w), qa.slerp(qb, w), sa.lerp(sb, w))
    return out


def smooth(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def env(t, a, b, c=1e9, d=1e9):
    """0 before a, ramps to 1 by b, holds, ramps down from c to 0 at d."""
    up = smooth((t - a) / max(b - a, 1e-6))
    down = 1 - smooth((t - c) / max(d - c, 1e-6))
    return min(up, down)


def clip(name, t0, loop=False, speed=1.0, src0=None):
    act = ACT[name]; f0, f1 = act.frame_range
    s0 = f0 if src0 is None else src0
    def fn(t):
        f = s0 + (t - t0) * speed
        if loop: f = f0 + (f - f0) % (f1 - f0)
        return sample(act, min(max(f, f0), f1))
    return fn


def root_scaled(fn, k):
    """Shrink a clip's root motion (the pack's knockback travels ~3 m)."""
    def g(t):
        p = dict(fn(t)); l, q, s = p["root"]; p["root"] = (l * k, q, s); return p
    return g


def hold(name, frame):
    p = sample(ACT[name], frame)
    return lambda t: p


# ---------------------------------------------------------------- the kick
def apply(rig, pose):
    for b, (l, q, s) in pose.items():
        pb = rig.pose.bones.get(b)
        if pb is None: continue
        pb.location, pb.rotation_quaternion, pb.scale = l, q, s
    bpy.context.view_layer.update()


def read(rig):
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in rig.pose.bones}


def turned(rig, base, rots):
    """base pose + rotations about rig axes (default X; degrees), applied in order."""
    apply(rig, base)
    for bone, deg, *axis in rots:
        pb = rig.pose.bones[bone]
        h = pb.head.copy()
        R = Matrix.Rotation(math.radians(deg), 4, axis[0] if axis else "X")
        pb.matrix = Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ pb.matrix
        bpy.context.view_layer.update()
    return read(rig)


GUARD = sample(ACT["Punch_Jab"], 1)
# rig faces -Y: rotating about +X by a negative angle swings a leg forward.
KICK_KEYS = [  # (frame offset, rotations)
    (0, []),
    (7, [("spine_01", -10), ("thigh_r", -132), ("thigh_r", 12, "Z"), ("calf_r", 135), ("foot_r", 10)]),   # knee up, chamber
    (11, [("spine_01", -22), ("thigh_r", -124), ("thigh_r", 16, "Z"), ("calf_r", 16), ("foot_r", -30)]),  # snap out: impact
    (15, [("spine_01", -21), ("thigh_r", -120), ("thigh_r", 16, "Z"), ("calf_r", 24), ("foot_r", -25)]),  # brief hold
    (22, [("spine_01", -10), ("thigh_r", -126), ("thigh_r", 12, "Z"), ("calf_r", 130), ("foot_r", 10)]),  # re-chamber
    (32, []),
]
KICK_IMPACT = 11
KPOSES = [(f, turned(rigA, GUARD, rots)) for f, rots in KICK_KEYS]
apply(rigA, GUARD)


def kick(t0):
    def fn(t):
        x = t - t0
        if x <= 0: return KPOSES[0][1]
        for (fa, pa), (fb, pb) in zip(KPOSES, KPOSES[1:]):
            if x <= fb:
                u = (x - fa) / (fb - fa)
                # snap out fast (ease-out) on the extension, smooth elsewhere
                w = 1 - (1 - u) ** 3 if fa == 7 else smooth(u)
                return mix(pa, pb, w)
        return KPOSES[-1][1]
    return fn


# ---------------------------------------------------------------- timeline
JAB, CROSS, KICK = 36, 58, 88
JAB_HIT, CROSS_HIT, KICK_HIT = JAB + 8, CROSS + 10, KICK + KICK_IMPACT

A_LAYERS = [
    (clip("Idle_Loop", 0, loop=True), lambda t: 1),
    (hold("Punch_Jab", 1), lambda t: env(t, 14, 30, 150, 168)),
    (clip("Punch_Jab", JAB), lambda t: env(t, JAB, JAB + 1, JAB + 21, JAB + 25)),
    (clip("Punch_Cross", CROSS), lambda t: env(t, CROSS, CROSS + 2, CROSS + 25, CROSS + 29)),
    (kick(KICK), lambda t: env(t, KICK, KICK + 1, KICK + 30, KICK + 32)),
]
B_LAYERS = [
    (clip("Idle_Loop", -23, loop=True), lambda t: 1),
    (clip("Hit_Head", JAB_HIT - 1), lambda t: env(t, JAB_HIT - 1, JAB_HIT + 1, JAB_HIT + 8, JAB_HIT + 13)),
    (clip("Hit_Chest", CROSS_HIT, speed=0.8), lambda t: env(t, CROSS_HIT - 1, CROSS_HIT + 1, CROSS_HIT + 8, CROSS_HIT + 13)),
    (root_scaled(clip("Hit_Knockback_RM", KICK_HIT, src0=1, speed=0.85), 0.55), lambda t: env(t, KICK_HIT - 1, KICK_HIT + 2)),
]
# A leans in a little on the cross so it reaches
A_STEP = lambda t: -0.07 * env(t, CROSS + 4, CROSS + 10, CROSS + 22, CROSS + 32)


def pose_at(layers, t):
    p = layers[0][0](t)
    for fn, w in layers[1:]:
        ww = w(t)
        if ww > 0: p = mix(p, fn(t), ww)
    return p


def bake(rig, layers, loc_fn=None):
    rig.animation_data_create()
    rig.animation_data.action = bpy.data.actions.new(rig.name + "_baked")
    for t in range(0, END + 1):
        apply(rig, pose_at(layers, t))
        for pb in rig.pose.bones:
            pb.keyframe_insert("location", frame=t)
            pb.keyframe_insert("rotation_quaternion", frame=t)
        if loc_fn:
            rig.location.y = loc_fn(t); rig.keyframe_insert("location", frame=t)


bake(rigA, A_LAYERS, A_STEP)
bake(rigB, B_LAYERS)

# ---------------------------------------------------------------- look
def mat(name, rgb, rough=0.45):
    m = bpy.data.materials.new(name); m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


for mesh, m in ((meshA, mat("Attacker", (0.85, 0.28, 0.06))), (meshB, mat("Target", (0.62, 0.66, 0.72)))):
    mesh.data.materials.clear(); mesh.data.materials.append(m)

bpy.ops.mesh.primitive_plane_add(size=40)
floor = bpy.context.active_object
floor.data.materials.append(mat("Floor", (0.06, 0.06, 0.065), 0.7))

world = bpy.data.worlds.new("W"); S.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.013, 0.018, 1)


def light(name, kind, loc, rot, energy, size=None, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if size: ld.size = size
    o = bpy.data.objects.new(name, ld); S.collection.objects.link(o)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    return o


light("Key", "AREA", (3.5, 1.5, 4.0), (35, 0, 115), 900, 3)
light("Rim", "AREA", (-3.0, -3.5, 3.0), (-50, 0, -35), 600, 2, (0.6, 0.75, 1.0))
spot = light("Pool", "SPOT", (0, -1.2, 6), (0, 0, 0), 1500, None, (1.0, 0.9, 0.8))
spot.data.spot_size = math.radians(55); spot.data.spot_blend = 0.6

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); S.collection.objects.link(cam)
cam.data.lens = 35; S.camera = cam
target = bpy.data.objects.new("CamTarget", None); S.collection.objects.link(target)
tc = cam.constraints.new("TRACK_TO"); tc.target = target
tc.track_axis, tc.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
for t in range(0, END + 1):
    u = t / END
    cam.location = (4.6 - 0.5 * u, -0.2 - 0.9 * u, 1.45)          # slow push in and drift
    shake = 0.0
    for hit, amp in ((JAB_HIT, 0.012), (CROSS_HIT, 0.018), (KICK_HIT, 0.035)):
        if t >= hit: shake += amp * math.exp(-(t - hit) / 3) * math.sin((t - hit) * 2.3)
    target.location = (0, -0.75 - 0.6 * smooth((t - KICK_HIT) / 30) + shake, 1.0 + shake * 0.6)
    cam.keyframe_insert("location", frame=t); target.keyframe_insert("location", frame=t)

S.render.engine = "CYCLES"
S.cycles.device = "CPU"
S.cycles.use_denoising = True
S.view_settings.view_transform = "AgX"
S.view_settings.look = "AgX - Medium High Contrast"
S.render.image_settings.file_format = "PNG"

if MODE == "scene":            # just save the baked fight (used by ../jjk/fight_jjk.py)
    S.render.resolution_x, S.render.resolution_y = 1280, 720
    S.render.use_motion_blur = True; S.render.motion_blur_shutter = 0.5
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/fight_scene.blend")
elif MODE == "preview":
    S.render.resolution_x, S.render.resolution_y = 480, 270
    S.cycles.samples = 12
    frames = [int(a) for a in ARGS[2].split(",")] if len(ARGS) > 2 else list(range(0, END + 1, 8))
    # contact report
    for name, t, bone, rig in (("jab", JAB_HIT, "hand_l", rigA), ("cross", CROSS_HIT, "hand_r", rigA), ("kick", KICK_HIT, "ball_r", rigA)):
        S.frame_set(t)
        p = rig.matrix_world @ rig.pose.bones[bone].tail
        hb = rigB.matrix_world @ rigB.pose.bones["Head"].head
        ch = rigB.matrix_world @ rigB.pose.bones["spine_03"].head
        print(f"CONTACT {name} t={t} {bone}={tuple(round(x,2) for x in p)}  B head={tuple(round(x,2) for x in hb)} B chest={tuple(round(x,2) for x in ch)}")
    for f in frames:
        S.frame_set(f); S.render.filepath = f"{OUT}/p_{f:04d}.png"
        bpy.ops.render.render(write_still=True)
else:
    S.render.resolution_x, S.render.resolution_y = 1280, 720
    S.cycles.samples = 20
    S.render.use_motion_blur = True
    S.render.motion_blur_shutter = 0.5
    S.render.filepath = f"{OUT}/f_"
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/fight.blend")
    fr = ARGS[2].split("-") if len(ARGS) > 2 else None
    if fr: S.frame_start, S.frame_end = int(fr[0]), int(fr[1])
    bpy.ops.render.render(animation=True)
