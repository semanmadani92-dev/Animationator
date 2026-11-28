"""Gojo vs SCP-049 (vertical, for Shorts). SCP-049 walks up and reaches for Gojo; Infinity stops
its hand an inch away; Gojo repels it, charges Hollow Purple and vaporises it.
Sound: gojo_vs_049_sfx.py. Edit (cold open + text): see HANDOFF.md.

  ~/blendervenv/bin/python gojo_vs_049.py -- preview|final OUT_DIR MODELS_DIR [frames | a-b]
  MODELS_DIR holds gojo/gojo.fbx (+ texture). SCP-049 is the CC0 mannequin dressed in code.
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "characters"))

args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT, MODELS = args[0], args[1], args[2]
PACK = os.path.join(HERE, "..", "..", "toolkit", "3d-pack", "animation") + "/"
bpy.ops.wm.read_factory_settings(use_empty=True)
import layers as L, mbchar, vaporise, hpvfx as V
S = bpy.context.scene

# ---------------------------------------------------------------- timing (frames, 30 fps)
WALK_END, REACH, PUSH = 64, 50, 66          # 049 arrives, raises its hand, pushes on Infinity
REPEL, FLY_END = 100, 116                   # Gojo flicks it away; it lands
CALL, RISE, ROAR, CHARGE = 122, 136, 196, 214   # 049 raises the D-class it "cured"; they roar and charge
LAPSE, CRUSH = 228, 262                     # Lapse Blue pulls them into one point and crushes them
RUSH, RED_CAST, RED_HIT, LAND, GETUP = 286, 298, 303, 320, 330   # 049 charges; Reversal Red throws it back
O = 250                                     # the Hollow Purple finish (same as the short cut, shifted)
T_BLUE, T_RED, T_SPIRAL, T_MERGE = 120 + O, 134 + O, 152 + O, 178 + O
SHOOT, LAUNCH, HIT, EXIT = 194 + O, 197 + O, 207 + O, 234 + O
END = 292 + O
B_PT = Vector((0.0, -2.6, 1.15))            # where Lapse Blue opens
ZOMBIES = [(-1.7, -4.6, 0), (1.9, -5.4, 6), (-1.1, -8.2, 12)]   # D-class bodies: x, y, rise delay
DIST = 7.0                                  # where 049 ends up after the repel
STOP = 1.12                                 # how close 049 gets (m)
BLUE, RED, PURPLE = (0.12, 0.38, 1.0), (1.0, 0.07, 0.04), (0.62, 0.16, 1.0)
S.render.fps = 30; S.frame_start, S.frame_end = 0, END
os.makedirs(OUT, exist_ok=True)
sm, env = L.smooth, L.env


# ---------------------------------------------------------------- source animation
def imp(path, keep_mesh=False):
    before, acts = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    for o in new:
        if o.type != "ARMATURE" and not (keep_mesh and o.type == "MESH" and o.parent == rig): bpy.data.objects.remove(o)
    if rig.animation_data: rig.animation_data.action = None
    return rig, {a.name.split("|")[-1].split(".")[0]: a for a in bpy.data.actions if a not in acts}


srcA, ACT = imp(PACK + "UAL1_unreal_rig_45anims.glb")
doc, _ = imp(PACK + "UAL1_unreal_rig_45anims.glb", keep_mesh=True)       # SCP-049 itself
r2, ACT2 = imp(PACK + "UAL2_mannequin_43anims.glb"); bpy.data.objects.remove(r2)
ACT["Hit_Knockback_RM"] = ACT2["Hit_Knockback_RM"]
for a in ACT.values(): a.use_fake_user = True
for pb in doc.pose.bones:
    pb.rotation_mode = "QUATERNION"


# ---------------------------------------------------------------- dress the mannequin as SCP-049
def mat(name, rgb, rough=0.6, spec=0.5, coat=0.0):
    m = bpy.data.materials.new(name); b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = spec; b.inputs["Coat Weight"].default_value = coat
    return m


CLOTH = mat("Robe", (0.018, 0.016, 0.015), 0.85, 0.2)
LEATHER = mat("Leather", (0.03, 0.022, 0.016), 0.45, 0.5)
CERAMIC = mat("Ceramic", (0.78, 0.74, 0.66), 0.25, 0.6, coat=0.6)
GLASS = mat("Lens", (0.0, 0.0, 0.0), 0.05, 1.0)
for o in doc.children:
    o.data.materials.clear(); o.data.materials.append(CLOTH)
doc_mesh = list(doc.children)

S.frame_set(0); bpy.context.view_layer.update()
def bone_w(name, tail=False):
    b = doc.data.bones[name]; return doc.matrix_world @ (b.tail_local if tail else b.head_local)


def attach(obj, bone):
    """Parent to a bone, keeping the object's current world placement (rig at rest)."""
    pb = doc.pose.bones[bone]
    pm = doc.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    obj.parent = doc; obj.parent_type = "BONE"; obj.parent_bone = bone
    obj.matrix_parent_inverse = pm.inverted()


def part(name, build, m, bone, loc, rot=(0, 0, 0), scale=(1, 1, 1), smooth=True):
    o = V.mesh_obj(name, build, m, smooth=smooth)
    o.location = loc; o.rotation_euler = rot; o.scale = scale
    bpy.context.view_layer.update(); attach(o, bone); doc_mesh.append(o); return o


hd, ht = bone_w("Head"), bone_w("Head", tail=True)
hc = (hd + ht) / 2 + Vector((0, 0, 0.02))                     # centre of the head
F = Vector((0, -1, 0))                                       # the rig faces -Y at rest
cone = lambda r1, r2, d, seg=16, cap=True: (lambda bm: bmesh.ops.create_cone(bm, cap_ends=cap, segments=seg, radius1=r1, radius2=r2, depth=d))
ball = lambda r, seg=24: (lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r))
box = lambda: (lambda bm: bmesh.ops.create_cube(bm, size=1))
# hood over the head and down to the shoulders
part("Hood", ball(1), CLOTH, "Head", hc + Vector((0, 0.02, 0.01)), scale=(0.135, 0.15, 0.155))
part("Cowl", cone(0.27, 0.12, 0.24, 20), CLOTH, "spine_03", hc + Vector((0, 0.03, -0.24)))
# the ceramic plague mask: a face plate, a long curved beak, black glass eyes
part("Mask", ball(1), CERAMIC, "Head", hc + F * 0.08 + Vector((0, 0, 0.01)), scale=(0.088, 0.06, 0.112))
part("Beak", cone(0.045, 0.004, 0.32, 12), CERAMIC, "Head", hc + F * 0.27 + Vector((0, 0, -0.05)),
     rot=(math.radians(90 + 25), 0, 0))
for sx in (-1, 1):
    part(f"Eye{sx}", ball(0.02, 12), GLASS, "Head", hc + F * 0.13 + Vector((sx * 0.04, 0, 0.04)), scale=(1, 0.5, 1))
    part(f"Rim{sx}", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=14, radius1=0.025, radius2=0.025, depth=0.02),
         LEATHER, "Head", hc + F * 0.125 + Vector((sx * 0.04, 0, 0.04)), rot=(math.pi / 2, 0, 0))
# the robe: a long open coat from the chest to the floor (on the pelvis so the legs swing inside)
pel = bone_w("pelvis")
part("Robe", cone(0.42, 0.2, pel.z + 0.05, 20, cap=False), CLOTH, "pelvis", Vector((pel.x, pel.y, (pel.z + 0.05) / 2 - 0.02)))
part("Coat", cone(0.25, 0.2, 0.5, 18, cap=False), CLOTH, "spine_02", pel + Vector((0, 0.0, 0.32)))
part("Belt", cone(0.215, 0.215, 0.05, 18), LEATHER, "pelvis", pel + Vector((0, 0, 0.1)))
# the doctor's bag in the left hand
hl = bone_w("hand_l")
part("Bag", box(), LEATHER, "hand_l", hl + Vector((0.02, 0, -0.17)), scale=(0.1, 0.3, 0.2))
for o in doc_mesh:
    if o.type == "MESH":
        for p in o.data.polygons: p.use_smooth = True


# ---------------------------------------------------------------- animation (mannequin layers, baked)
doc.rotation_mode = "XYZ"; doc.rotation_euler.z = math.pi
A = [(L.clip(ACT["Idle_Loop"], 0, loop=True), lambda t: 1),
     (L.clip(ACT["Spell_Simple_Shoot"], REPEL - 6, speed=1.3), lambda t: env(t, REPEL - 7, REPEL - 4, REPEL + 8, REPEL + 14)),
     (L.clip(ACT["Spell_Simple_Shoot"], LAPSE - 4, speed=0.9), lambda t: env(t, LAPSE - 5, LAPSE - 2, LAPSE + 8, LAPSE + 12)),
     (L.clip(ACT["Spell_Simple_Idle_Loop"], LAPSE + 8, loop=True), lambda t: env(t, LAPSE + 8, LAPSE + 12, CRUSH + 2, CRUSH + 10)),
     (L.clip(ACT["Spell_Simple_Shoot"], RED_CAST - 6, speed=1.3), lambda t: env(t, RED_CAST - 7, RED_CAST - 4, RED_HIT + 8, RED_HIT + 14)),
     (L.clip(ACT["Spell_Simple_Enter"], T_BLUE - 8), lambda t: env(t, T_BLUE - 8, T_BLUE - 6, EXIT, EXIT + 4)),
     (L.clip(ACT["Spell_Simple_Idle_Loop"], T_BLUE + 6, loop=True), lambda t: env(t, T_BLUE + 4, T_BLUE + 7, SHOOT, SHOOT + 2)),
     (L.clip(ACT["Spell_Simple_Shoot"], SHOOT, speed=0.8), lambda t: env(t, SHOOT, SHOOT + 2, SHOOT + 17, SHOOT + 20)),
     (L.clip(ACT["Spell_Simple_Exit"], EXIT, speed=0.8), lambda t: env(t, EXIT, EXIT + 2, EXIT + 15, EXIT + 22))]
B0 = [(L.clip(ACT["Walk_Formal_Loop"], 0, loop=True), lambda t: 1),
      (L.clip(ACT["Idle_Loop"], 0, loop=True), lambda t: env(t, WALK_END - 4, WALK_END + 4))]
AIM = {k: v for k, v in L.sample(ACT["Pistol_Aim_Neutral"], 10).items() if k in ("clavicle_r", "upperarm_r", "lowerarm_r", "hand_r")}
reach = lambda t: {**L.pose_at(B0, t), **AIM}          # only the right arm reaches out; fingers stay open
B = B0 + [(reach, lambda t: env(t, REACH, PUSH, REPEL - 1, REPEL + 1)),
     (L.clip(ACT["Hit_Knockback_RM"], REPEL, speed=0.7, root_scale=0.0), lambda t: env(t, REPEL, REPEL + 2, FLY_END + 18, FLY_END + 30)),
     (L.clip(ACT["Idle_Loop"], 30, loop=True), lambda t: env(t, FLY_END + 18, FLY_END + 30)),
     (L.clip(ACT["Spell_Simple_Enter"], CALL), lambda t: env(t, CALL, CALL + 4, ROAR, ROAR + 10)),       # raises the dead
     (L.clip(ACT["Spell_Simple_Idle_Loop"], CALL + 12, loop=True), lambda t: env(t, CALL + 10, CALL + 14, ROAR, ROAR + 10)),
     (L.clip(ACT["Sprint_Loop"], RUSH, loop=True, speed=1.1), lambda t: env(t, RUSH - 3, RUSH + 2, RED_HIT - 1, RED_HIT + 1)),
     (L.clip(ACT2["Hit_Knockback"], RED_HIT, speed=1.1), lambda t: env(t, RED_HIT - 1, RED_HIT + 1, GETUP - 1, GETUP)),
     (L.clip(ACT2["LayToIdle"], GETUP, speed=0.8), lambda t: env(t, GETUP - 1, GETUP, GETUP + 44, GETUP + 52)),
     (L.clip(ACT["Idle_Loop"], 0, loop=True), lambda t: env(t, GETUP + 44, GETUP + 52))]
L.bake(srcA, A, 0, END)
L.bake(doc, B, 0, END)
srcA.hide_render = True
D_HIT = 2.3                                  # where Reversal Red catches 049
for t in range(0, END + 1):                 # 049's path: walk in, stop, thrown back, charges, thrown back again
    z = 0
    if t <= WALK_END:
        y = -6.4 + (6.4 - STOP) * (t / WALK_END) - 0.03 * sm((t - WALK_END + 8) / 8)
        y = min(y, -STOP)
    elif t < REPEL:
        y = -STOP - 0.02 * math.sin((t - PUSH) * 1.7) * (t > PUSH)
    elif t < RUSH:
        y = -STOP - (DIST - STOP) * (1 - (1 - min(1, (t - REPEL) / (FLY_END - REPEL))) ** 2.2)
        if t <= FLY_END: z = 0.35 * math.sin(math.pi * (t - REPEL) / (FLY_END - REPEL))
    elif t < RED_HIT:
        y = -DIST + (DIST - D_HIT) * ((t - RUSH) / (RED_HIT - RUSH)) ** 1.25
    else:
        u = min(1, (t - RED_HIT) / (LAND - RED_HIT))
        y = -D_HIT - (DIST - D_HIT) * (1 - (1 - u) ** 2.2)
        z = 0.55 * math.sin(math.pi * u)
    doc.location = (0, y, z); doc.keyframe_insert("location", frame=t)


# ---------------------------------------------------------------- the D-class 049 "cured": they get up and charge
def zombie_mat():
    m, nt, out = V.nodes_mat("DClassZombie")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = 0.75
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "skin"; at.attribute_type = "GEOMETRY"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs[6].default_value = (0.42, 0.11, 0.02, 1)          # D-class orange jumpsuit
    mx.inputs[7].default_value = (0.2, 0.22, 0.17, 1)           # grey-green dead skin
    nt.links.new(at.outputs["Fac"], mx.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9; nz.inputs["Detail"].default_value = 6
    dirt = nt.nodes.new("ShaderNodeMix"); dirt.data_type = "RGBA"; dirt.blend_type = "MULTIPLY"
    dirt.inputs[0].default_value = 0.7
    nt.links.new(mx.outputs[2], dirt.inputs[6]); nt.links.new(nz.outputs["Fac"], dirt.inputs[7])
    nt.links.new(dirt.outputs[2], b.inputs["Base Color"]); nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


ZMAT = zombie_mat()
EYE = V.emit_mat("ZombieEye", (1.0, 0.12, 0.05))[0]; EYE.node_tree.nodes["Emission"].inputs["Strength"].default_value = 25
SKIN_GROUPS = ("Head", "neck", "hand", "thumb", "index", "middle", "ring", "pinky")
ZRIGS = []
for k, (zx, zy, delay) in enumerate(ZOMBIES):
    z, _ = imp(PACK + "UAL1_unreal_rig_45anims.glb", keep_mesh=True)
    z.name = f"DClass{k}"
    for pb in z.pose.bones: pb.rotation_mode = "QUATERNION"
    for o in z.children:
        o.data.materials.clear(); o.data.materials.append(ZMAT)
        gi = {g.index for g in o.vertex_groups if g.name.startswith(SKIN_GROUPS)}
        att = o.data.attributes.new("skin", "FLOAT", "POINT")
        for v in o.data.vertices:
            att.data[v.index].value = min(1, sum(g.weight for g in v.groups if g.group in gi))
    zh = z.data.bones["Head"]; zc = z.matrix_world @ ((zh.head_local + zh.tail_local) / 2)
    for sx in (-1, 1):                                                     # glowing red eyes
        e = V.mesh_obj(f"ZEye{k}{sx}", V.sphere(0.014, 12), EYE)
        e.location = zc + Vector((sx * 0.035, -0.095, 0.02)); bpy.context.view_layer.update()
        pb = z.pose.bones["Head"]; e.parent = z; e.parent_type = "BONE"; e.parent_bone = "Head"
        e.matrix_parent_inverse = (z.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))).inverted()
    r0 = RISE + delay
    ZL = [(L.clip(ACT2["LayToIdle"], r0, speed=0.75), lambda t: 1),
          (L.clip(ACT2["Zombie_Scratch"], ROAR + k * 2, speed=1.3), lambda t: env(t, ROAR - 4, ROAR + 2, CHARGE - 3, CHARGE + 1)),
          (L.clip(ACT["Sprint_Loop"], CHARGE + k * 5, loop=True), lambda t: env(t, CHARGE - 2, CHARGE + 2, LAPSE + 4, LAPSE + 10)),
          (L.clip(ACT["Jump_Loop"], LAPSE + k * 9, loop=True, speed=2.0), lambda t: env(t, LAPSE + 4, LAPSE + 10))]
    L.bake(z, ZL, 0, CRUSH + 2)
    z.rotation_mode = "XYZ"
    start = Vector((zx, zy, 0)); goal = Vector((zx * 0.3, -1.2, 0)); d = (goal - start).normalized()
    yaw = math.atan2(d.x, -d.y)
    run = lambda t, s=start, d=d: s + d * 0.13 * max(0, t - CHARGE - 2)
    p0 = run(LAPSE + 2)
    for t in range(0, END + 1):
        u = sm((t - LAPSE - 2) / (CRUSH - LAPSE - 2)) ** 1.6                          # 0..1 into the blue
        sc = 1 - sm((t - CRUSH + 12) / 12) if t < CRUSH else 1e-4
        a = k * 2.1 + 9 * u
        swirl = Vector((math.cos(a), math.sin(a), 0)) * 0.9 * (1 - u)
        tgt = B_PT + swirl - Vector((0, 0, 0.95 * sc))                              # body centre into the orb
        z.location = run(t).lerp(tgt, u) if t > LAPSE + 2 else run(t)
        z.location.z += 0.4 * math.sin(math.pi * u) * (1 - u)
        z.rotation_euler = (2.2 * u * math.sin(a), 1.6 * u * math.cos(a * 0.7), math.pi if t < CHARGE else yaw + 6 * u)
        z.scale = (sc,) * 3
        z.keyframe_insert("location", frame=t); z.keyframe_insert("rotation_euler", frame=t); z.keyframe_insert("scale", frame=t)
    ZRIGS.append(z)


# ---------------------------------------------------------------- Gojo
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
base = gojo.matrix_world.copy()
S.frame_set(0); gojo.matrix_world = srcA.matrix_world.normalized() @ base; bpy.context.view_layer.update()
rt = mbchar.Retarget(srcA, gojo, mbchar.MIXAMO, move=("pelvis",))
gojo.animation_data_create(); gojo.animation_data.action = bpy.data.actions.new("gojo_049"); gojo.rotation_mode = "QUATERNION"
HAND, PALM, DOC_HAND, CHEST = {}, {}, {}, {}
for t in range(0, END + 1):
    S.frame_set(t)
    gojo.matrix_world = srcA.matrix_world.normalized() @ base; bpy.context.view_layer.update(); rt.apply()
    gojo.keyframe_insert("location", frame=t); gojo.keyframe_insert("rotation_quaternion", frame=t)
    for pb in gojo.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=t)
        if pb.bone.name in rt.move: pb.keyframe_insert("location", frame=t)
    bpy.context.view_layer.update()
    HAND[t] = gojo.matrix_world @ gojo.pose.bones["mixamorig:LeftHandMiddle2"].head + Vector((0, -0.14, 0.02))
    DOC_HAND[t] = doc.matrix_world @ doc.pose.bones["middle_02_r"].head
    CHEST[t] = doc.matrix_world @ doc.pose.bones["spine_03"].head

# ---------------------------------------------------------------- Infinity: a ripple in the air where the hand stops
m, nt, out = V.nodes_mat("Infinity")
geo = nt.nodes.new("ShaderNodeNewGeometry")
pt = nt.nodes.new("ShaderNodeCombineXYZ")                       # contact point (keyed)
dist = nt.nodes.new("ShaderNodeVectorMath"); dist.operation = "DISTANCE"
nt.links.new(geo.outputs["Position"], dist.inputs[0]); nt.links.new(pt.outputs[0], dist.inputs[1])
ph = nt.nodes.new("ShaderNodeValue")                            # ripple phase (keyed)
wave = nt.nodes.new("ShaderNodeMath"); wave.operation = "MULTIPLY_ADD"; wave.inputs[1].default_value = 38
nt.links.new(dist.outputs["Value"], wave.inputs[0]); nt.links.new(ph.outputs[0], wave.inputs[2])
sn = nt.nodes.new("ShaderNodeMath"); sn.operation = "SINE"; nt.links.new(wave.outputs[0], sn.inputs[0])
ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "POWER"; ab.inputs[1].default_value = 6.0
pos = nt.nodes.new("ShaderNodeMath"); pos.operation = "ABSOLUTE"; nt.links.new(sn.outputs[0], pos.inputs[0]); nt.links.new(pos.outputs[0], ab.inputs[0])
fall = nt.nodes.new("ShaderNodeMath"); fall.operation = "MULTIPLY"; fall.inputs[1].default_value = -9.0
nt.links.new(dist.outputs["Value"], fall.inputs[0])
ex = nt.nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"; nt.links.new(fall.outputs[0], ex.inputs[0])
k1 = nt.nodes.new("ShaderNodeMath"); k1.operation = "MULTIPLY"; nt.links.new(ab.outputs[0], k1.inputs[0]); nt.links.new(ex.outputs[0], k1.inputs[1])
core = nt.nodes.new("ShaderNodeMath"); core.operation = "MULTIPLY"; core.inputs[1].default_value = -40.0
nt.links.new(dist.outputs["Value"], core.inputs[0])
cex = nt.nodes.new("ShaderNodeMath"); cex.operation = "EXPONENT"; nt.links.new(core.outputs[0], cex.inputs[0])
sumn = nt.nodes.new("ShaderNodeMath"); sumn.operation = "ADD"; nt.links.new(k1.outputs[0], sumn.inputs[0]); nt.links.new(cex.outputs[0], sumn.inputs[1])
gain = nt.nodes.new("ShaderNodeMath"); gain.operation = "MULTIPLY"; nt.links.new(sumn.outputs[0], gain.inputs[0])
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.55, 0.8, 1.0, 1)
nt.links.new(gain.outputs[0], em.inputs["Strength"])
gl = nt.nodes.new("ShaderNodeBsdfRefraction"); gl.inputs["IOR"].default_value = 1.04; gl.inputs["Roughness"].default_value = 0.0
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mixs = nt.nodes.new("ShaderNodeMixShader")                      # a faint lens warp near the contact
nt.links.new(cex.outputs[0], mixs.inputs[0]); nt.links.new(tr.outputs[0], mixs.inputs[1]); nt.links.new(gl.outputs[0], mixs.inputs[2])
add = nt.nodes.new("ShaderNodeAddShader"); nt.links.new(mixs.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
nt.links.new(add.outputs[0], out.inputs["Surface"])
shell = V.mesh_obj("Infinity", lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=1), m)
S.frame_set(PUSH); bpy.context.view_layer.update()
contact = DOC_HAND[PUSH + 10]
centre = Vector((0, 0, contact.z))
shell.location = centre; shell.scale = ((centre - contact).length + 0.02,) * 3
for t in range(0, END + 1):
    c = DOC_HAND[min(max(t, PUSH), REPEL)]
    on = env(t, REACH + 8, PUSH, REPEL + 2, REPEL + 9)
    burst = 6 * math.exp(-max(0, t - REPEL) / 2.5) * (t >= REPEL)
    gain.inputs[1].default_value = 0.45 * on + burst * on
    ph.outputs[0].default_value = -t * 0.55 - 8 * sm((t - REPEL) / 8)
    pt.inputs[0].default_value, pt.inputs[1].default_value, pt.inputs[2].default_value = c
    shell.hide_render = on < 1e-3
    for s in (gain.inputs[1], ph.outputs[0], pt.inputs[0], pt.inputs[1], pt.inputs[2]): s.keyframe_insert("default_value", frame=t)
    shell.keyframe_insert("hide_render", frame=t)
rp = bpy.data.lights.new("RepelFlash", "POINT"); rp.color = (0.5, 0.75, 1.0); rp.shadow_soft_size = 0.3
repel_light = bpy.data.objects.new("RepelFlash", rp); S.collection.objects.link(repel_light); repel_light.location = contact
for t in range(0, END + 1):
    k = t - REPEL
    rp.energy = (2500 * math.exp(-k / 2.5) if k >= 0 else 0) + 25 * env(t, PUSH, PUSH + 6, REPEL, REPEL + 1)
    rp.keyframe_insert("energy", frame=t)

# ---------------------------------------------------------------- 049 raises the dead: red glow under each body + an alarm
for k, (zx, zy, delay) in enumerate(ZOMBIES):
    ld = bpy.data.lights.new(f"Raise{k}", "POINT"); ld.color = (1.0, 0.08, 0.05); ld.shadow_soft_size = 0.4
    o = bpy.data.objects.new(f"Raise{k}", ld); S.collection.objects.link(o); o.location = (zx, zy - 0.5, 0.15)
    for t in range(0, END + 1):
        ld.energy = 140 * env(t, CALL + 4 + delay, RISE + delay, RISE + delay + 30, RISE + delay + 55) * (0.75 + 0.25 * math.sin(t * 0.9 + k))
        ld.keyframe_insert("energy", frame=t)
al = bpy.data.lights.new("Alarm", "SPOT"); al.color = (1.0, 0.05, 0.03); al.spot_size = math.radians(70); al.spot_blend = 0.6
alarm = bpy.data.objects.new("Alarm", al); S.collection.objects.link(alarm); alarm.location = (0, -4.5, 5.5)
for t in range(0, END + 1):
    al.energy = 2500 * env(t, CALL, CALL + 6, T_BLUE - 16, T_BLUE - 4) * max(0, math.sin(t * 0.21)) ** 2
    alarm.rotation_euler = (0.35 * math.sin(t * 0.105), 0.35 * math.cos(t * 0.105), 0)
    al.keyframe_insert("energy", frame=t); alarm.keyframe_insert("rotation_euler", frame=t)

# ---------------------------------------------------------------- Lapse Blue: a point that drags the bodies in and crushes them
lapse = V.Orb("Lapse", BLUE, light_w=400, core_strength=9)
wm, wnt, wout = V.nodes_mat("Warp")                         # a lens of bent space around it
rf = wnt.nodes.new("ShaderNodeBsdfRefraction"); rf.inputs["IOR"].default_value = 1.12; rf.inputs["Roughness"].default_value = 0.0
wtr = wnt.nodes.new("ShaderNodeBsdfTransparent"); wlw = wnt.nodes.new("ShaderNodeLayerWeight"); wlw.inputs["Blend"].default_value = 0.5
wmix = wnt.nodes.new("ShaderNodeMixShader")
wnt.links.new(wlw.outputs["Facing"], wmix.inputs[0]); wnt.links.new(rf.outputs[0], wmix.inputs[1]); wnt.links.new(wtr.outputs[0], wmix.inputs[2])
wnt.links.new(wmix.outputs[0], wout.inputs["Surface"])
warp = V.mesh_obj("Warp", V.sphere(1.0, 48), wm)
bshm, bshock_s = V.emit_mat("BlueShock", (0.5, 0.75, 1.0), transparent_edges=True)
bshock = V.mesh_obj("BlueShock", V.sphere(1.0, 48), bshm)
bfl = bpy.data.lights.new("BlueFlash", "POINT"); bfl.color = (0.5, 0.7, 1.0); bfl.shadow_soft_size = 0.5
bflash = bpy.data.objects.new("BlueFlash", bfl); S.collection.objects.link(bflash); bflash.location = B_PT
for t in range(0, END + 1):
    grow = sm((t - LAPSE) / 6)
    k = t - CRUSH
    rad = (0.12 + 0.05 * sm((t - LAPSE) / (CRUSH - LAPSE)) + 0.015 * math.sin(t * 1.7)) * grow
    if k >= 0: rad = 0.3 * math.exp(-k / 1.2) * (k < 6)
    lapse.key(t, B_PT, rad, 1.2 + 1.5 * math.exp(-max(0, t - LAPSE) / 3) * (t >= LAPSE) + 3 * (k >= 0))
    ws = 0.85 * grow * (1 - sm((t - CRUSH + 2) / 4))
    warp.location = B_PT; warp.scale = (max(ws, 1e-4),) * 3; warp.hide_render = ws < 1e-3
    bshock.location = B_PT; bshock.scale = ((0.15 + 1.7 * sm(k / 9)) if k >= 0 else 1e-4,) * 3
    bshock_s.default_value = 2.5 * (1 - sm(k / 9)) if k >= 0 else 0
    bfl.energy = 7000 * math.exp(-k / 2.5) if k >= 0 else 0
    for o in (warp, bshock): o.keyframe_insert("scale", frame=t); o.keyframe_insert("location", frame=t)
    warp.keyframe_insert("hide_render", frame=t); bshock_s.keyframe_insert("default_value", frame=t); bfl.keyframe_insert("energy", frame=t)

# ---------------------------------------------------------------- Reversal Red: a flick that blasts 049 back down the hall
redshot = V.Orb("RedShot", RED, light_w=250, core_strength=9)
rshm, rshock_s = V.emit_mat("RedShock", (1.0, 0.35, 0.2), transparent_edges=True)
rshock = V.mesh_obj("RedShock", V.sphere(1.0, 48), rshm)
rfl = bpy.data.lights.new("RedFlash", "POINT"); rfl.color = (1.0, 0.3, 0.15); rfl.shadow_soft_size = 0.5
rflash = bpy.data.objects.new("RedFlash", rfl); S.collection.objects.link(rflash)
r_hit = CHEST[RED_HIT] + Vector((0, 0.15, 0))
for t in range(0, END + 1):
    k = t - RED_HIT
    if t < RED_CAST - 6: pos, rad = HAND[t], 0.0
    elif t < RED_CAST: pos, rad = HAND[t], 0.1 * sm((t - RED_CAST + 6) / 4)
    elif k < 0: pos, rad = HAND[RED_CAST].lerp(r_hit, ((t - RED_CAST) / (RED_HIT - RED_CAST)) ** 1.3), 0.11
    else: pos, rad = r_hit, 0.45 * sm(k / 2) * (1 - sm((k - 2) / 5))
    redshot.key(t, pos, rad, 1.3 + 2.5 * (k >= 0))
    rshock.location = r_hit; rshock.scale = ((0.15 + 1.5 * sm(k / 9)) if k >= 0 else 1e-4,) * 3
    rshock_s.default_value = 2.5 * (1 - sm(k / 9)) if k >= 0 else 0
    rflash.location = r_hit + Vector((0, 0.6, 0.2)); rfl.energy = 8000 * math.exp(-k / 2.5) if k >= 0 else 0
    rshock.keyframe_insert("scale", frame=t); rshock.keyframe_insert("location", frame=t)
    rshock_s.keyframe_insert("default_value", frame=t); rflash.keyframe_insert("location", frame=t); rfl.keyframe_insert("energy", frame=t)

# ---------------------------------------------------------------- vaporise 049
VAP = vaporise.Vaporise([o for o in doc_mesh if o.type == "MESH"], CHEST[HIT], start=HIT, burn=26)

blue, red = V.Orb("Blue", BLUE, light_w=250), V.Orb("Red", RED, light_w=250)
purple = V.Orb("Purple", PURPLE, plasma=True, light_w=900, core_strength=10)
tm, trail_s = V.emit_mat("Trail", PURPLE, transparent_edges=True)
trail = V.mesh_obj("Trail", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=1, radius2=1, depth=2), tm)
trail.rotation_euler.x = math.pi / 2
shm, shock_s = V.emit_mat("Shock", (0.8, 0.55, 1.0), transparent_edges=True)
shock = V.mesh_obj("Shock", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=1, radius2=1.25, depth=0.12), shm)
shock.rotation_euler.x = math.pi / 2
scm, scorch_s = V.emit_mat("Scorch", PURPLE, transparent_edges=True)
scorch = V.mesh_obj("Scorch", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5), scm, smooth=False)
fl = bpy.data.lights.new("Flash", "POINT"); fl.color = (0.85, 0.6, 1.0); fl.shadow_soft_size = 1.0
flash = bpy.data.objects.new("Flash", fl); S.collection.objects.link(flash)
bl = bpy.data.lights.new("BurnLight", "POINT"); bl.color = PURPLE; bl.shadow_soft_size = 0.3
burn_light = bpy.data.objects.new("BurnLight", bl); S.collection.objects.link(burn_light)

CAM_D = Vector((1.25, -2.15, 1.55))
impact = Vector((0, -DIST + 0.2, 1.15))
_to_cam = (CAM_D - HAND[T_BLUE + 30]).normalized()
UP = Vector((0, 0, 1)); SIDE = _to_cam.cross(UP).normalized(); UP = SIDE.cross(_to_cam).normalized()
P_launch = None
for t in range(0, END + 1):
    P = HAND[t]
    for orb, t0, side in ((blue, T_BLUE, 1), (red, T_RED, -1)):
        grow = sm((t - t0) / 10) * (1 + 0.25 * math.sin(max(0, t - t0) * 0.9) * math.exp(-max(0, t - t0) / 6))
        s = sm((t - T_SPIRAL) / (T_MERGE - T_SPIRAL))
        r = 0.36 * (1 - s) ** 1.2
        a = (0 if side > 0 else math.pi) + s * 4.5 * math.pi
        off = SIDE * (r * math.cos(a)) + UP * (0.08 * (1 - s) + r * math.sin(a) * 0.8)
        rad = 0.07 * grow * (1 - sm((t - T_MERGE + 2) / 3)) * (1 + 0.04 * math.sin(t * 2.3 + side))
        orb.key(t, P + off, rad, 1.0 + 0.6 * s)
    if t < LAUNCH:
        rad = (0.05 + 0.18 * sm((t - T_MERGE) / (SHOOT - T_MERGE))) * (t >= T_MERGE) * (1 + 0.07 * math.sin(t * 1.9))
        pos = P; P_launch = P.copy()
        g = 1.0 + 2.5 * math.exp(-max(0, t - T_MERGE) / 3) * (t >= T_MERGE)
    else:
        dt = t - LAUNCH
        dy = (DIST - 0.9) * (dt / (HIT - LAUNCH)) ** 1.25 if t <= HIT else (DIST - 0.9) + 2.2 * (t - HIT) ** 1.15
        pos = P_launch + Vector((0, -dy, -0.15 * sm(dt / 10)))
        rad = 0.23 + 0.75 * sm(dt / 9)
        g = 1.6 * (1 - sm((t - HIT - 30) / 25)) + 0.001
    purple.key(t, pos, rad, g)
    if t >= LAUNCH and P_launch is not None:
        tail = P_launch + Vector((0, -0.2, -0.1)); length = max(0.01, (tail - pos).length)
        thin = 0.38 * rad * (1 - sm((t - HIT) / 14)) + 1e-4
        trail.location = (tail + pos) / 2; trail.scale = (thin, thin, length / 2)
        trail_s.default_value = 3.5 * (1 - sm((t - HIT) / 14))
        scorch.location = Vector((P_launch.x, (P_launch.y - 0.3 + pos.y) / 2, 0.004))
        scorch.scale = (0.9, max(0.01, abs(pos.y - P_launch.y + 0.3)), 1)
        scorch_s.default_value = (3 + 8 * math.exp(-max(0, t - HIT) / 5)) * (1 - sm((t - HIT) / 60)) + 0.3
    else:
        trail.scale = (1e-4,) * 3; trail_s.default_value = 0
        scorch.scale = (1e-4,) * 3; scorch_s.default_value = 0; scorch.location = (0, 0, -1)
    for o in (trail, scorch): o.keyframe_insert("location", frame=t); o.keyframe_insert("scale", frame=t)
    trail_s.keyframe_insert("default_value", frame=t); scorch_s.keyframe_insert("default_value", frame=t)
    k = t - HIT
    shock.location = impact
    shock.scale = ((0.2 + 4 * sm(k / 14)),) * 2 + (1,) if k >= 0 else (1e-4,) * 3
    shock_s.default_value = 9 * (1 - sm(k / 14)) if k >= 0 else 0
    flash.location = impact + Vector((0, 0.5, 0.3))
    fl.energy = 60000 * math.exp(-k / 2.5) if k >= 0 else 0
    shock.keyframe_insert("location", frame=t); shock.keyframe_insert("scale", frame=t)
    shock_s.keyframe_insert("default_value", frame=t); fl.keyframe_insert("energy", frame=t)
    VAP.key(t)
    burn_light.location = CHEST[t] + Vector((0, 0.3, 0))
    bl.energy = 700 * sm(k / 2) * (1 - sm((k - 18) / 16)) if k >= 0 else 0
    burn_light.keyframe_insert("location", frame=t); bl.keyframe_insert("energy", frame=t)
VAP.embers()


# ---------------------------------------------------------------- set: a dim containment hall
def pbr(name, rgb, rough):
    m = bpy.data.materials.new(name); b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


V.mesh_obj("Floor", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60), pbr("Floor", (0.05, 0.05, 0.055), 0.5), smooth=False)
wallm = pbr("Wall", (0.07, 0.07, 0.075), 0.8)
for x in (-5.6, 5.6):
    for k in range(7):
        w = V.mesh_obj(f"Pillar{x}_{k}", lambda bm: bmesh.ops.create_cube(bm, size=1), wallm, smooth=False)
        w.location = (x, 2 - k * 2.2, 2.2); w.scale = (0.45, 0.45, 4.4)
strip = V.emit_mat("Strip", (1.0, 0.25, 0.12))[0]
for x in (-4.0, 4.0):
    s = V.mesh_obj(f"Strip{x}", lambda bm: bmesh.ops.create_cube(bm, size=1), strip, smooth=False)
    s.location = (x, -5, 0.03); s.scale = (0.04, 18, 0.02)
w = bpy.data.worlds.new("W"); S.world = w; w.node_tree.nodes["Background"].inputs[0].default_value = (0.006, 0.006, 0.01, 1)
for nm, loc, rot, e, c in (("Key", (-3, 1.5, 4.5), (35, 0, -120), 350, (0.8, 0.85, 1)),
                           ("Rim", (3, -9, 3.5), (-60, 0, 20), 400, (0.7, 0.7, 1)),
                           ("Fill", (2.5, -3.2, 2.2), (65, 0, 38), 220, (0.9, 0.9, 1)),
                           ("SideFill", (6, -4.5, 2.5), (70, 0, 90), 350, (0.85, 0.85, 1)),
                           ("MaskFill", (1.5, -0.2, 2.0), (60, 0, 120), 90, (0.9, 0.95, 1))):
    ld = bpy.data.lights.new(nm, "AREA"); ld.energy = e; ld.size = 3; ld.color = c
    o = bpy.data.objects.new(nm, ld); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = [math.radians(v) for v in rot]


# ---------------------------------------------------------------- camera (vertical)
SHOTS = [  # (first frame, start loc, end loc, look start, look end, lens)
    (0,          (0.7, 1.9, 1.8),  (0.6, 1.5, 1.75), (0, -4, 1.25), (0, -3, 1.3), 26),           # behind Gojo: 049 approaches
    (44,         (3.1, -0.8, 1.45), (2.8, -0.75, 1.45), (0, -0.78, 1.3), (0, -0.72, 1.35), 16),    # profile: the reach
    (72,         (0.5, 0.45, 1.62), (0.42, 0.38, 1.6), (0, -0.9, 1.42), (0, -0.9, 1.44), 34),     # over Gojo's shoulder: the hand frozen
    (REPEL,      (4.9, -3.4, 1.4), (5.0, -3.9, 1.4), (0, -3.6, 1.0), (0, -4.2, 1.0), 13),       # wide: thrown back
    (FLY_END + 4, (-2.7, -3.5, 0.4), (-2.5, -3.8, 0.45), (-0.8, -6.6, 0.95), (-0.8, -6.6, 1.0), 17),  # low by a body: 049 calls
    (RISE + 30,  (-0.95, -2.75, 0.55), (-1.05, -2.95, 0.7), (-1.6, -4.9, 0.75), (-1.6, -4.9, 1.05), 19),  # a body gets up
    (ROAR - 2,   (0.75, 1.7, 1.7), (0.65, 1.45, 1.65), (0, -5, 1.05), (0, -4, 1.1), 22),         # over Gojo: they roar and charge
    (LAPSE - 1,  (4.6, -1.5, 1.45), (4.9, -1.9, 1.55), (0, -2.3, 1.1), (0, -2.5, 1.1), 14),       # wide: Lapse Blue drags them in
    (CRUSH + 14, (0.55, -5.0, 1.45), (0.45, -5.3, 1.45), (0, -7, 1.45), (0, -7, 1.45), 30),       # 049 alone
    (RUSH + 7,   (4.3, -1.7, 1.3), (4.5, -2.6, 1.3), (0, -2.6, 1.1), (0, -5.3, 0.85), 15),        # side: it charges, Red throws it
    (LAND - 3,   (1.35, -5.0, 0.4), (1.2, -5.2, 0.5), (0, -7.3, 0.45), (0, -7.1, 0.95), 22),      # low: 049 lands and gets up
    (T_BLUE - 2, (1.35, -2.3, 1.55), (0.95, -1.8, 1.5), (0.12, -0.55, 1.42), (0.12, -0.55, 1.42), 30),  # Gojo charges
    (SHOOT - 3,  (5.0, -3.4, 1.45), (5.1, -4.6, 1.6), (0, -3.6, 1.1), (0, -5.6, 0.9), 12.5),       # wide: the shot
    (HIT + 3,    (2.3, -4.6, 1.4), (1.8, -5.3, 1.3), (0, -7.5, 1.05), (0, -7.5, 1.05), 28),     # 049 burns away
    (EXIT + 26,  (1.3, 2.6, 1.75), (1.1, 2.1, 1.65), (-0.2, -6.0, 0.7), (-0.2, -6.0, 0.7), 24),  # behind Gojo: nothing left
]
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); S.collection.objects.link(cam); S.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
for t in range(0, END + 1):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t)
    f0, l0, l1, k0, k1, lens = SHOTS[i]; f1 = SHOTS[i + 1][0] if i + 1 < len(SHOTS) else END + 1
    u = sm((t - f0) / max(1, f1 - f0))
    loc = Vector(l0).lerp(Vector(l1), u); look = Vector(k0).lerp(Vector(k1), u)
    if i == 2:                                     # aim at the frozen hand, the mask behind it
        look = DOC_HAND[min(t, REPEL)] + Vector((0, -0.25, 0.08)); loc = look + Vector((0.6 - 0.08 * u, 1.55 - 0.2 * u, 0.16))
    for t_hit, amp, tau in ((REPEL, 0.08, 5), (CRUSH, 0.1, 5), (RED_HIT, 0.1, 5), (LAND, 0.05, 4), (HIT, 0.12, 6)):
        k = t - t_hit
        if 0 <= k < 40: sh = amp * math.exp(-k / tau); loc = loc + Vector((0, sh * math.sin(k * 2.1), sh * math.sin(k * 3.3)))
    cam.location = loc; cam.rotation_euler = (look - loc).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = lens
    cam.keyframe_insert("location", frame=t); cam.keyframe_insert("rotation_euler", frame=t); cam.data.keyframe_insert("lens", frame=t)
for a in (cam.animation_data.action, cam.data.animation_data.action):
    for fc in a.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"

# bloom
ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rl = ng.nodes.new("CompositorNodeRLayers"); gl = ng.nodes.new("CompositorNodeGlare"); go = ng.nodes.new("NodeGroupOutput")
gl.inputs["Type"].default_value = "Bloom"; gl.inputs["Quality"].default_value = "High"
gl.inputs["Threshold"].default_value = 0.9; gl.inputs["Strength"].default_value = 0.9; gl.inputs["Size"].default_value = 0.9
ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], go.inputs[0])
S.compositing_node_group = ng; S.render.compositor_device = "CPU"

S.render.engine = "CYCLES"; S.cycles.device = "CPU"; S.cycles.use_denoising = True
S.view_settings.view_transform = "AgX"; S.view_settings.look = "AgX - Medium High Contrast"
S.cycles.volume_step_rate = 4.0
if MODE == "preview":
    S.render.resolution_x, S.render.resolution_y = 360, 640; S.cycles.samples = 10
    frames = [int(f) for f in args[3].split(",")] if len(args) > 3 else list(range(0, END + 1, 24))
    for f in frames:
        S.frame_set(f); S.render.filepath = os.path.join(OUT, f"g49_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    S.render.resolution_x, S.render.resolution_y = 720, 1280; S.cycles.samples = 16
    S.render.use_motion_blur = True; S.render.motion_blur_shutter = 0.5
    S.render.filepath = os.path.join(OUT, "g49_")
    if len(args) > 3:
        a, b = args[3].split("-"); S.frame_start, S.frame_end = int(a), int(b)
    bpy.ops.render.render(animation=True)
