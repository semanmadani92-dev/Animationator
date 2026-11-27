"""Clip-layer blending for the pack's mannequin rigs (same method as fight_sample/fight.py):
every frame is a stack of clips blended with smoothstep envelopes, then baked."""
import bpy
from mathutils import Vector, Quaternion

_CH = {}
IDENT = (Vector((0, 0, 0)), Quaternion(), Vector((1, 1, 1)))


def channels(act):
    if act.name not in _CH:
        d = {}
        for fc in act.layers[0].strips[0].channelbags[0].fcurves:
            if fc.data_path.startswith("pose.bones["):
                bone = fc.data_path.split('"')[1]; prop = fc.data_path.rsplit(".", 1)[1]
                d.setdefault(bone, {}).setdefault(prop, {})[fc.array_index] = fc
        _CH[act.name] = d
    return _CH[act.name]


def sample(act, f):
    pose = {}
    for b, props in channels(act).items():
        l, q, s = IDENT
        if "location" in props:
            l = Vector([props["location"][i].evaluate(f) if i in props["location"] else 0 for i in range(3)])
        if "rotation_quaternion" in props:
            rq = props["rotation_quaternion"]
            q = Quaternion([rq[i].evaluate(f) if i in rq else (1 if i == 0 else 0) for i in range(4)]).normalized()
        if "scale" in props:
            s = Vector([props["scale"][i].evaluate(f) if i in props["scale"] else 1 for i in range(3)])
        pose[b] = (l, q, s)
    return pose


def mix(a, b, w):
    if w <= 0: return a
    if w >= 1: return b
    return {k: (a.get(k, IDENT)[0].lerp(b.get(k, IDENT)[0], w), a.get(k, IDENT)[1].slerp(b.get(k, IDENT)[1], w),
                a.get(k, IDENT)[2].lerp(b.get(k, IDENT)[2], w)) for k in set(a) | set(b)}


def smooth(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


def env(t, a, b, c=1e9, d=1e9):
    return min(smooth((t - a) / max(b - a, 1e-6)), 1 - smooth((t - c) / max(d - c, 1e-6)))


def clip(act, t0, loop=False, speed=1.0, root_scale=1.0):
    f0, f1 = act.frame_range
    def fn(t):
        f = f0 + (t - t0) * speed
        if loop: f = f0 + (f - f0) % (f1 - f0)
        p = sample(act, min(max(f, f0), f1))
        if root_scale != 1.0 and "root" in p:
            l, q, s = p["root"]; p = dict(p); p["root"] = (l * root_scale, q, s)
        return p
    return fn


def hold(act, frame):
    p = sample(act, frame)
    return lambda t: p


def pose_at(layers, t):
    p = layers[0][0](t)
    for fn, w in layers[1:]:
        ww = w(t)
        if ww > 0: p = mix(p, fn(t), ww)
    return p


def apply(rig, pose):
    for b, (l, q, s) in pose.items():
        pb = rig.pose.bones.get(b)
        if pb: pb.location, pb.rotation_quaternion, pb.scale = l, q, s


def bake(rig, layers, start, end):
    rig.animation_data_create()
    rig.animation_data.action = bpy.data.actions.new(rig.name + "_baked")
    for t in range(start, end + 1):
        apply(rig, pose_at(layers, t))
        for pb in rig.pose.bones:
            pb.keyframe_insert("location", frame=t); pb.keyframe_insert("rotation_quaternion", frame=t)
