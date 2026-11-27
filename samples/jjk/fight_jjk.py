"""Gojo vs Sukuna: re-renders the mannequin fight (../fight_sample/fight.py) with the
downloaded Gojo and Yuji->Sukuna models, retargeting every baked frame onto their
Mixamo skeletons.

  1) ~/blendervenv/bin/python ../fight_sample/fight.py -- scene OUT_DIR
  2) ~/blendervenv/bin/python fight_jjk.py -- preview|final OUT_DIR MODELS_DIR [frames]
     MODELS_DIR holds gojo/gojo.fbx and yuji/yuji.fbx (+ textures).
"""
import bpy, sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "characters"))
import mbchar, sukuna

args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT, MODELS = args[0], args[1], args[2]
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "fight_scene.blend"))
S = bpy.context.scene
rigs = sorted([o for o in S.objects if o.type == "ARMATURE"], key=lambda o: o.name)   # Rig = attacker, Rig.001 = target
srcA, srcB = rigs[0], rigs[1]
for o in S.objects:
    if o.type == "MESH" and o.name.startswith("Mannequin"): o.hide_render = o.hide_viewport = True


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MODELS, name, name + ".fbx"))
    objs = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in objs if o.type == "ARMATURE")
    if arm.animation_data: arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"; pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0)
    return arm, objs


gojo, _ = load("gojo")
suk, suk_objs = load("yuji")
sukuna.apply(suk_objs)

pairs = []
for src, tgt in ((srcA, gojo), (srcB, suk)):
    base = tgt.matrix_world.copy()                     # FBX axis/scale fix
    S.frame_set(S.frame_start)
    tgt.matrix_world = src.matrix_world.normalized() @ base
    bpy.context.view_layer.update()
    pairs.append((src, tgt, base, mbchar.Retarget(src, tgt, mbchar.MIXAMO, move=("pelvis",))))

for src, tgt, base, rt in pairs:
    tgt.animation_data_create(); tgt.animation_data.action = bpy.data.actions.new(tgt.name + "_fight")
    tgt.rotation_mode = "QUATERNION"

for t in range(S.frame_start, S.frame_end + 1):
    S.frame_set(t)
    for src, tgt, base, rt in pairs:
        tgt.matrix_world = src.matrix_world.normalized() @ base
        bpy.context.view_layer.update()
        rt.apply()
        tgt.keyframe_insert("location", frame=t); tgt.keyframe_insert("rotation_quaternion", frame=t)
        for pb in tgt.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=t)
            if pb.bone.name in rt.move: pb.keyframe_insert("location", frame=t)

# a little wider (Sukuna's fall) and brighter (dark uniforms)
cam = S.camera
cam.data.lens = 31
S.view_settings.exposure = 0.6
if MODE == "preview":
    S.render.resolution_x, S.render.resolution_y = 640, 360
    S.cycles.samples = 12; S.render.use_motion_blur = False
    frames = [int(f) for f in args[3].split(",")] if len(args) > 3 else list(range(0, S.frame_end + 1, 10))
    for f in frames:
        S.frame_set(f); S.render.filepath = os.path.join(OUT, f"j_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    S.cycles.samples = 24
    S.render.filepath = os.path.join(OUT, "jf_")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "fight_jjk.blend"))
    if len(args) > 3:
        a, b = args[3].split("-"); S.frame_start, S.frame_end = int(a), int(b)
    bpy.ops.render.render(animation=True)
