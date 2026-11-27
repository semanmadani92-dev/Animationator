"""Gojo's Hollow Purple: a blue orb and a red orb charge, spiral together and merge into a
purple sphere that Gojo fires at Sukuna, scorching the floor and blasting him away.

  ~/blendervenv/bin/python hollow_purple.py -- preview|final OUT_DIR MODELS_DIR [frames | a-b]
  MODELS_DIR holds gojo/gojo.fbx and yuji/yuji.fbx (+ textures).
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "characters"))
import layers as L, mbchar, sukuna

args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT, MODELS = args[0], args[1], args[2]
PACK = "/home/user/Animationator/toolkit/3d-pack/animation/"
END = 200
DIST = 7.0                                   # Sukuna's distance from Gojo (m)
T_BLUE, T_RED, T_SPIRAL, T_MERGE = 26, 40, 58, 84
SHOOT, LAUNCH, HIT, EXIT = 100, 103, 113, 140
BLUE, RED, PURPLE = (0.12, 0.38, 1.0), (1.0, 0.07, 0.04), (0.62, 0.16, 1.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
S = bpy.context.scene
S.render.fps = 30; S.frame_start, S.frame_end = 0, END
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- source animation (mannequin rigs)
def imp(path):
    before, acts = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.type != "ARMATURE": bpy.data.objects.remove(o)
    rig = next(o for o in bpy.data.objects if o not in before)
    if rig.animation_data: rig.animation_data.action = None
    return rig, {a.name.split("|")[-1].split(".")[0]: a for a in bpy.data.actions if a not in acts}


srcA, ACT = imp(PACK + "UAL1_unreal_rig_45anims.glb")
srcB, _ = imp(PACK + "UAL1_unreal_rig_45anims.glb")
r2, ACT2 = imp(PACK + "UAL2_mannequin_43anims.glb"); bpy.data.objects.remove(r2)
ACT["Hit_Knockback_RM"] = ACT2["Hit_Knockback_RM"]
for a in ACT.values(): a.use_fake_user = True
srcB.rotation_mode = "XYZ"; srcB.location = (0, -DIST, 0); srcB.rotation_euler.z = math.pi
env = L.env
A = [(L.clip(ACT["Idle_Loop"], 0, loop=True), lambda t: 1),
     (L.clip(ACT["Spell_Simple_Enter"], 16), lambda t: env(t, 16, 18, EXIT, EXIT + 4)),
     (L.clip(ACT["Spell_Simple_Idle_Loop"], 32, loop=True), lambda t: env(t, 30, 33, SHOOT, SHOOT + 2)),
     (L.clip(ACT["Spell_Simple_Shoot"], SHOOT, speed=0.8), lambda t: env(t, SHOOT, SHOOT + 2, SHOOT + 17, SHOOT + 20)),
     (L.clip(ACT["Spell_Simple_Exit"], EXIT, speed=0.8), lambda t: env(t, EXIT, EXIT + 2, EXIT + 15, EXIT + 22))]
B = [(L.clip(ACT["Idle_Loop"], -17, loop=True), lambda t: 1),
     (L.hold(ACT["Punch_Jab"], 1), lambda t: env(t, 40, 56)),
     (L.clip(ACT["Hit_Knockback_RM"], HIT - 1, speed=0.75, root_scale=1.5), lambda t: env(t, HIT - 2, HIT))]
L.bake(srcA, A, 0, END)
L.bake(srcB, B, 0, END)
for o in (srcA, srcB): o.hide_render = True


# ---------------------------------------------------------------- Gojo and Sukuna
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
    base = tgt.matrix_world.copy()
    S.frame_set(0); tgt.matrix_world = src.matrix_world.normalized() @ base
    bpy.context.view_layer.update()
    pairs.append((src, tgt, base, mbchar.Retarget(src, tgt, mbchar.MIXAMO, move=("pelvis",))))
    tgt.animation_data_create(); tgt.animation_data.action = bpy.data.actions.new(tgt.name + "_hp")
    tgt.rotation_mode = "QUATERNION"

HAND = {}                                     # Gojo's casting point per frame (in front of his left hand)
for t in range(0, END + 1):
    S.frame_set(t)
    for src, tgt, base, rt in pairs:
        tgt.matrix_world = src.matrix_world.normalized() @ base
        bpy.context.view_layer.update()
        rt.apply()
        tgt.keyframe_insert("location", frame=t); tgt.keyframe_insert("rotation_quaternion", frame=t)
        for pb in tgt.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=t)
            if pb.bone.name in rt.move: pb.keyframe_insert("location", frame=t)
    bpy.context.view_layer.update()
    h = gojo.matrix_world @ gojo.pose.bones["mixamorig:LeftHandMiddle2"].head
    HAND[t] = h + Vector((0, -0.14, 0.02))


# ---------------------------------------------------------------- VFX building blocks
def nodes_mat(name):
    m = bpy.data.materials.new(name); nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL": nt.nodes.remove(n)
    return m, nt, nt.nodes["Material Output"]


def core_mat(name, rim, plasma=False):
    """Bright white centre, coloured rim; optional moving plasma noise. Returns (mat, strength socket, noise W)."""
    m, nt, out = nodes_mat(name)
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.45
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1); ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].color = (*rim, 1); ramp.color_ramp.elements[1].position = 0.32
    fac = lw.outputs["Facing"]; w = None
    if plasma:
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
        nz.inputs["Scale"].default_value = 3.5; nz.inputs["Detail"].default_value = 8; nz.inputs["Distortion"].default_value = 0.6
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"
        nt.links.new(nz.outputs["Fac"], add.inputs[0]); add.inputs[1].default_value = 0.9
        nt.links.new(fac, add.inputs[2]); fac = add.outputs[0]; w = nz.inputs["W"]
    nt.links.new(fac, ramp.inputs["Fac"])
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m, em.inputs["Strength"], w


def halo_mat(name, color):
    """Glow volume that fades out from the centre of a unit sphere."""
    m, nt, out = nodes_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord"); gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.2
    nt.links.new(gr.outputs["Fac"], pw.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; nt.links.new(pw.outputs[0], mul.inputs[0])
    vol = nt.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0
    vol.inputs["Emission Color"].default_value = (*color, 1)
    nt.links.new(mul.outputs[0], vol.inputs["Emission Strength"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m, mul.inputs[1]


def emit_mat(name, color, transparent_edges=False):
    m, nt, out = nodes_mat(name)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    if transparent_edges:       # additive glow: fully transparent when the strength is 0
        lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.6
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(lw.outputs["Facing"], inv.inputs[1])
        k = nt.nodes.new("ShaderNodeMath"); k.operation = "MULTIPLY"; nt.links.new(inv.outputs[0], k.inputs[0])
        nt.links.new(k.outputs[0], em.inputs["Strength"])
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); add = nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(tr.outputs[0], add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs["Surface"])
        return m, k.inputs[1]
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m, em.inputs["Strength"]


def mesh_obj(name, build, mat, parent=None, smooth=True):
    bm = bmesh.new(); build(bm)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); S.collection.objects.link(o)
    if parent: o.parent = parent
    return o


def sphere(r=1.0, seg=32):
    return lambda bm: bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)


def ring_of_sparks(n, radius, size, seed):
    rng = random.Random(seed)
    def build(bm):
        for k in range(n):
            a = 2 * math.pi * k / n + rng.uniform(-0.1, 0.1)
            p = Vector((math.cos(a) * radius * rng.uniform(0.9, 1.15), math.sin(a) * radius * rng.uniform(0.9, 1.15), rng.uniform(-0.12, 0.12)))
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size * rng.uniform(0.5, 1.3), matrix=Matrix.Translation(p))
    return build


class Orb:
    def __init__(self, name, color, plasma=False, light_w=300, core_strength=7):
        self.e = bpy.data.objects.new(name, None); S.collection.objects.link(self.e)
        cm, self.core_s, self.w = core_mat(name + "_Core", color, plasma)
        self.core = mesh_obj(name + "_Core", sphere(), cm, self.e)
        hm, self.halo_s = halo_mat(name + "_Halo", color)
        self.halo = mesh_obj(name + "_Halo", sphere(1.0, 24), hm, self.e); self.halo.scale = (2.6,) * 3
        sm, self.spark_s = emit_mat(name + "_Sparks", tuple(min(1, c * 1.2 + 0.25) for c in color))
        self.rings = []
        for k, (tilt, rad) in enumerate(((0.5, 1.55), (-0.9, 1.85), (1.4, 1.35))):
            r = mesh_obj(f"{name}_Ring{k}", ring_of_sparks(22, rad, 0.05, k * 7 + len(name)), sm, self.e, smooth=False)
            r.rotation_euler = (tilt, tilt * 0.6, 0); r.rotation_mode = "XYZ"; self.rings.append(r)
        ld = bpy.data.lights.new(name + "_Light", "POINT"); ld.color = color; ld.shadow_soft_size = 0.15
        self.light = bpy.data.objects.new(name + "_Light", ld); S.collection.objects.link(self.light); self.light.parent = self.e
        self.light_w = light_w
        self.cs = core_strength

    def key(self, t, pos, radius, glow=1.0):
        on = radius > 1e-4
        self.e.location = pos; self.e.scale = (max(radius, 1e-4),) * 3
        self.core_s.default_value = self.cs * glow
        self.halo_s.default_value = 9 * glow
        self.spark_s.default_value = 7 * glow
        if self.w: self.w.default_value = t * 0.08
        self.light.data.energy = self.light_w * glow * min(1, radius / 0.08) if on else 0
        for k, r in enumerate(self.rings):
            r.rotation_euler.z = t * (0.35 + 0.12 * k) * (1 if k % 2 == 0 else -1)
            r.keyframe_insert("rotation_euler", frame=t)
        for o in (self.core, self.halo, *self.rings):
            o.hide_render = not on; o.keyframe_insert("hide_render", frame=t)
        self.e.keyframe_insert("location", frame=t); self.e.keyframe_insert("scale", frame=t)
        for s in (self.core_s, self.halo_s, self.spark_s) + ((self.w,) if self.w else ()):
            s.keyframe_insert("default_value", frame=t)
        self.light.data.keyframe_insert("energy", frame=t)


sm = L.smooth
blue, red = Orb("Blue", BLUE, light_w=250), Orb("Red", RED, light_w=250)
purple = Orb("Purple", PURPLE, plasma=True, light_w=900, core_strength=10)

# beam trail, floor scorch, impact shockwave and flash
tm, trail_s = emit_mat("Trail", PURPLE, transparent_edges=True)
trail = mesh_obj("Trail", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=1, radius2=1, depth=2), tm)
trail.rotation_euler.x = math.pi / 2

scm, scnt, scout = nodes_mat("Scorch")
tc = scnt.nodes.new("ShaderNodeTexCoord"); sep = scnt.nodes.new("ShaderNodeSeparateXYZ"); scnt.links.new(tc.outputs["Generated"], sep.inputs[0])
d = scnt.nodes.new("ShaderNodeMath"); d.operation = "PINGPONG"; d.inputs[1].default_value = 0.5; scnt.links.new(sep.outputs["X"], d.inputs[0])
stripe = scnt.nodes.new("ShaderNodeMath"); stripe.operation = "POWER"; stripe.inputs[1].default_value = 3.0
mul2 = scnt.nodes.new("ShaderNodeMath"); mul2.operation = "MULTIPLY"; mul2.inputs[1].default_value = 2.0
scnt.links.new(d.outputs[0], mul2.inputs[0]); scnt.links.new(mul2.outputs[0], stripe.inputs[0])
bsdf = scnt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.inputs["Base Color"].default_value = (0.008, 0.006, 0.008, 1)
bsdf.inputs["Roughness"].default_value = 0.9; bsdf.inputs["Emission Color"].default_value = (*PURPLE, 1)
glow = scnt.nodes.new("ShaderNodeMath"); glow.operation = "MULTIPLY"; scnt.links.new(stripe.outputs[0], glow.inputs[0])
scnt.links.new(glow.outputs[0], bsdf.inputs["Emission Strength"])
alpha = scnt.nodes.new("ShaderNodeMath"); alpha.operation = "POWER"; alpha.inputs[1].default_value = 0.35
scnt.links.new(mul2.outputs[0], alpha.inputs[0]); scnt.links.new(alpha.outputs[0], bsdf.inputs["Alpha"])
scnt.links.new(bsdf.outputs[0], scout.inputs["Surface"])
scorch_glow = glow.inputs[1]
scorch = mesh_obj("Scorch", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5), scm, smooth=False)

shm, shock_s = emit_mat("Shock", (0.8, 0.55, 1.0), transparent_edges=True)
shock = mesh_obj("Shock", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=1, radius2=1.25, depth=0.12), shm)
shock.rotation_euler.x = math.pi / 2
fl = bpy.data.lights.new("Flash", "POINT"); fl.color = (0.85, 0.6, 1.0); fl.shadow_soft_size = 1.0
flash = bpy.data.objects.new("Flash", fl); S.collection.objects.link(flash)

impact = Vector((0, -DIST + 0.2, 1.15))
# orbit plane faces the close-up camera, so blue and red flank the hand on screen
_to_cam = (Vector((1.15, -2.0, 1.52)) - HAND[60]).normalized()
UP = Vector((0, 0, 1)); SIDE = _to_cam.cross(UP).normalized(); UP = SIDE.cross(_to_cam).normalized()
P_launch = None
for t in range(0, END + 1):
    P = HAND[t]
    # blue and red: appear, hover beside the hand, spiral in and merge
    for orb, t0, side in ((blue, T_BLUE, 1), (red, T_RED, -1)):
        grow = sm((t - t0) / 10) * (1 + 0.25 * math.sin(max(0, t - t0) * 0.9) * math.exp(-max(0, t - t0) / 6))
        s = sm((t - T_SPIRAL) / (T_MERGE - T_SPIRAL))
        r = 0.42 * (1 - s) ** 1.2
        a = (0 if side > 0 else math.pi) + s * 4.5 * math.pi
        off = SIDE * (r * math.cos(a)) + UP * (0.08 * (1 - s) + r * math.sin(a) * 0.8)
        rad = 0.07 * grow * (1 - sm((t - T_MERGE + 2) / 3)) * (1 + 0.04 * math.sin(t * 2.3 + side))
        orb.key(t, P + off, rad, 1.0 + 0.6 * s)
    # purple: born at the merge, swells, then launched
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
    # trail behind the sphere
    if t >= LAUNCH and P_launch is not None:
        tail = P_launch + Vector((0, -0.2, -0.1))
        length = max(0.01, (tail - pos).length)
        thin = 0.38 * rad * (1 - sm((t - HIT) / 14)) + 1e-4
        trail.location = (tail + pos) / 2; trail.scale = (thin, thin, length / 2)
        trail_s.default_value = 3.5 * (1 - sm((t - HIT) / 14))
        scorch.location = Vector((P_launch.x, (P_launch.y - 0.3 + pos.y) / 2, 0.004))
        scorch.scale = (1.5, max(0.01, abs(pos.y - P_launch.y + 0.3)), 1)
        scorch_glow.default_value = 14 * (1 - sm((t - HIT) / 60)) + 0.3
    else:
        trail.scale = (1e-4,) * 3; trail_s.default_value = 0
        scorch.scale = (1e-4,) * 3; scorch_glow.default_value = 0
        scorch.location = (0, 0, -1)
    trail.keyframe_insert("location", frame=t); trail.keyframe_insert("scale", frame=t)
    trail_s.keyframe_insert("default_value", frame=t)
    scorch.keyframe_insert("location", frame=t); scorch.keyframe_insert("scale", frame=t)
    scorch_glow.keyframe_insert("default_value", frame=t)
    # impact
    k = t - HIT
    shock.location = impact
    shock.scale = ((0.2 + 4 * sm(k / 14)),) * 2 + (1,) if k >= 0 else (1e-4,) * 3
    shock_s.default_value = 9 * (1 - sm(k / 14)) if k >= 0 else 0
    flash.location = impact + Vector((0, 0.5, 0.3))
    fl.energy = 60000 * math.exp(-k / 3.5) if k >= 0 else 0
    shock.keyframe_insert("location", frame=t); shock.keyframe_insert("scale", frame=t)
    shock_s.keyframe_insert("default_value", frame=t); fl.keyframe_insert("energy", frame=t)


# ---------------------------------------------------------------- set, lights, camera
def pbr(name, rgb, rough):
    m = bpy.data.materials.new(name); b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


floor = mesh_obj("Floor", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60), pbr("Floor", (0.05, 0.05, 0.055), 0.55), smooth=False)
w = bpy.data.worlds.new("W"); S.world = w; w.node_tree.nodes["Background"].inputs[0].default_value = (0.006, 0.006, 0.01, 1)
for nm, loc, rot, e, c in (("Key", (-3, 1.5, 4.5), (35, 0, -120), 350, (0.8, 0.85, 1)),
                           ("Rim", (3, -9, 3.5), (-60, 0, 20), 400, (0.7, 0.7, 1)),
                           ("Fill", (2.5, -3.2, 2.2), (65, 0, 38), 220, (0.9, 0.9, 1)),
                           ("SideFill", (6, -4.5, 2.5), (70, 0, 90), 350, (0.85, 0.85, 1))):
    ld = bpy.data.lights.new(nm, "AREA"); ld.energy = e; ld.size = 3; ld.color = c
    o = bpy.data.objects.new(nm, ld); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = [math.radians(v) for v in rot]

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); S.collection.objects.link(cam); S.camera = cam
for t in range(0, END + 1):
    if t < SHOOT - 3:                                   # close on Gojo charging
        u = t / (SHOOT - 3)
        loc = Vector((1.35, -2.3, 1.55)).lerp(Vector((0.95, -1.75, 1.5)), sm(u)); look = Vector((0.12, -0.55, 1.42)); lens = 32
    else:                                               # wide side shot of the blast
        u = sm((t - HIT) / 50)
        loc = Vector((8.2, -4.2, 1.55)).lerp(Vector((8.6, -6.0, 1.7)), u); look = Vector((0, -4.0, 1.1)).lerp(Vector((0, -6.5, 0.9)), u); lens = 22
        k = t - HIT
        if k >= 0:
            sh = 0.12 * math.exp(-k / 6)
            loc = loc + Vector((0, sh * math.sin(k * 2.1), sh * math.sin(k * 3.3)))
    cam.location = loc; cam.rotation_euler = (look - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.keyframe_insert("location", frame=t); cam.keyframe_insert("rotation_euler", frame=t)
    cam.data.keyframe_insert("lens", frame=t)
for a in (cam.animation_data.action, cam.data.animation_data.action):     # hard cut, no blending
    for fc in a.layers[0].strips[0].channelbags[0].fcurves:
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"

# bloom
ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rl = ng.nodes.new("CompositorNodeRLayers"); gl = ng.nodes.new("CompositorNodeGlare"); go = ng.nodes.new("NodeGroupOutput")
gl.inputs["Type"].default_value = "Bloom"; gl.inputs["Quality"].default_value = "High"
gl.inputs["Threshold"].default_value = 0.9; gl.inputs["Strength"].default_value = 0.9; gl.inputs["Size"].default_value = 0.9
ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], go.inputs[0])
S.compositing_node_group = ng
S.render.compositor_device = "CPU"

S.render.engine = "CYCLES"; S.cycles.device = "CPU"; S.cycles.use_denoising = True
S.view_settings.view_transform = "AgX"; S.view_settings.look = "AgX - Medium High Contrast"
S.cycles.volume_step_rate = 4.0
if MODE == "preview":
    S.render.resolution_x, S.render.resolution_y = 640, 360; S.cycles.samples = 12
    frames = [int(f) for f in args[3].split(",")] if len(args) > 3 else list(range(0, END + 1, 12))
    for f in frames:
        S.frame_set(f); S.render.filepath = os.path.join(OUT, f"hp_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
else:
    S.render.resolution_x, S.render.resolution_y = 1280, 720; S.cycles.samples = 24
    S.render.use_motion_blur = True; S.render.motion_blur_shutter = 0.5
    S.render.filepath = os.path.join(OUT, "hpf_")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hollow_purple.blend"))
    if len(args) > 3:
        a, b = args[3].split("-"); S.frame_start, S.frame_end = int(a), int(b)
    bpy.ops.render.render(animation=True)
