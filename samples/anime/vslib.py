"""Shared kit for the anime-vs-SCP Shorts (vertical 720x1280, Cycles on the CPU).
Import it right after bpy.ops.wm.read_factory_settings(use_empty=True).

  heroes : Hero(path, height)        a downloaded fan model (FBX or Sketchfab glTF, Mixamo rig) driven by
                                     the CC0 mannequin clips through mbchar.Retarget
  bodies : mannequin()               the CC0 mannequin itself (used to build SCPs and D-class)
  set    : hall()                    the dim containment hall used by every episode
  camera : camera(SHOTS, end, ...)   hard cuts between slowly moving shots, plus shakes
  output : render(mode, out, prefix, end, args)
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, "..", "jjk"), os.path.join(HERE, "..", "characters")):
    if p not in sys.path: sys.path.insert(0, p)
import layers as L, mbchar, hpvfx as V
PACK = os.path.join(HERE, "..", "..", "toolkit", "3d-pack", "animation") + "/"
S = bpy.context.scene
sm, env = L.smooth, L.env
FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"


# ---------------------------------------------------------------- mannequin + its clips
def imp(path, keep_mesh=False):
    before, acts = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == "ARMATURE")
    for o in new:
        if o.type != "ARMATURE" and not (keep_mesh and o.type == "MESH" and o.parent == rig): bpy.data.objects.remove(o)
    if rig.animation_data: rig.animation_data.action = None
    for pb in rig.pose.bones: pb.rotation_mode = "QUATERNION"
    rig.rotation_mode = "XYZ"
    return rig, {a.name.split("|")[-1].split(".")[0]: a for a in bpy.data.actions if a not in acts}


ACT = {}
def clips():
    """All 88 CC0 clips by name (UAL1 + UAL2)."""
    if not ACT:
        for f in ("UAL2_mannequin_43anims.glb", "UAL1_unreal_rig_45anims.glb"):
            r, a = imp(PACK + f); ACT.update(a); bpy.data.objects.remove(r)
        for a in ACT.values(): a.use_fake_user = True
    return ACT


def mannequin(name, mat=None):
    rig, _ = imp(PACK + "UAL1_unreal_rig_45anims.glb", keep_mesh=True)
    rig.name = name
    if mat:
        for o in rig.children: o.data.materials.clear(); o.data.materials.append(mat)
    return rig


def bake_path(rig, path, end):
    """path(t) -> (x, y, z, yaw); yaw 0 = facing -Y (the mannequin's rest facing)."""
    for t in range(end + 1):
        x, y, z, yaw = path(t)
        rig.location = (x, y, z); rig.rotation_euler = (0, 0, yaw)
        rig.keyframe_insert("location", frame=t); rig.keyframe_insert("rotation_euler", frame=t)


def face(dx, dy):
    """yaw that makes a mannequin face the direction (dx, dy)."""
    return math.atan2(dx, -dy)


def skin_attr(rig, groups=("Head", "neck", "hand", "thumb", "index", "middle", "ring", "pinky")):
    """Per-vertex 'skin' attribute (1 on head and hands) for two-tone mannequin materials."""
    for o in rig.children:
        gi = {g.index for g in o.vertex_groups if g.name.startswith(groups)}
        att = o.data.attributes.new("skin", "FLOAT", "POINT")
        for v in o.data.vertices: att.data[v.index].value = min(1, sum(g.weight for g in v.groups if g.group in gi))


def two_tone(name, body, skin, rough=0.7, dirt=0.6):
    m, nt, out = V.nodes_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = rough
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "skin"
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs[6].default_value = (*body, 1); mx.inputs[7].default_value = (*skin, 1)
    nt.links.new(at.outputs["Fac"], mx.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 9; nz.inputs["Detail"].default_value = 6
    dm = nt.nodes.new("ShaderNodeMix"); dm.data_type = "RGBA"; dm.blend_type = "MULTIPLY"; dm.inputs[0].default_value = dirt
    nt.links.new(mx.outputs[2], dm.inputs[6]); nt.links.new(nz.outputs["Fac"], dm.inputs[7])
    nt.links.new(dm.outputs[2], b.inputs["Base Color"]); nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def attach(obj, rig, bone):
    """Parent obj to a bone, keeping its current world placement."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]
    pm = rig.matrix_world @ pb.matrix @ Matrix.Translation((0, pb.bone.length, 0))
    obj.parent = rig; obj.parent_type = "BONE"; obj.parent_bone = bone
    obj.matrix_parent_inverse = pm.inverted()


def bone_mid(rig, name):
    b = rig.data.bones[name]; return rig.matrix_world @ ((b.head_local + b.tail_local) / 2)


# ---------------------------------------------------------------- heroes (downloaded models)
def _strip(n):
    base, _, tail = n.rpartition("_")
    return base if base and tail.isdigit() else n


class Hero:
    """A Mixamo-rigged fan model, scaled to `height` m, standing at the origin facing -Y.
    drive(layers, path, end, track) bakes clip layers on a hidden mannequin and copies them over."""
    def __init__(self, path, height=None, name="Hero"):
        before = set(bpy.data.objects)
        if path.lower().endswith(".fbx"): bpy.ops.import_scene.fbx(filepath=path)
        else: bpy.ops.import_scene.gltf(filepath=path)
        self.objs = [o for o in bpy.data.objects if o not in before]
        self.rig = next(o for o in self.objs if o.type == "ARMATURE"); self.rig.name = name
        if self.rig.animation_data: self.rig.animation_data.action = None
        for pb in self.rig.pose.bones:
            pb.rotation_mode = "QUATERNION"; pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
        for o in self.objs:
            if o.animation_data: o.animation_data.action = None
        bpy.context.view_layer.update()
        self.meshes = [o for o in self.objs if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
        self.src, _ = imp(PACK + "UAL1_unreal_rig_45anims.glb"); self.src.name = name + "_src"
        self.src.hide_render = True
        dg = bpy.context.evaluated_depsgraph_get()
        zs = [(o.matrix_world @ v.co).z for o in self.meshes for v in o.evaluated_get(dg).to_mesh().vertices]
        lo, hi = min(zs), max(zs)
        k = (height / (hi - lo)) if height else 1.0
        S.frame_set(0)
        w = self.rig.matrix_world.copy()
        self.base = Matrix.Translation((-w.translation.x * k, -w.translation.y * k, -lo * k)) @ Matrix.Scale(k, 4) @ w
        self.rig.matrix_world = self.src.matrix_world.normalized() @ self.base
        bpy.context.view_layer.update()
        mapping = {}
        names = {_strip(b.name): b.name for b in self.rig.data.bones}
        for s, t in mbchar.MIXAMO.items():
            if t in names: mapping[s] = names[t]
        self.rt = mbchar.Retarget(self.src, self.rig, mapping, move=("pelvis",))
        self.bname = names                                # clean mixamo name -> real bone name
        self.track = {}

    def bone(self, clean):
        return self.rig.pose.bones[self.bname["mixamorig:" + clean]]

    def drive(self, layers, path, end, track=()):
        """track: clean bone names ('LeftHand', 'Head', ...) whose world head is recorded per frame."""
        L.bake(self.src, layers, 0, end)
        bake_path(self.src, path, end)
        rig = self.rig
        rig.animation_data_create(); rig.animation_data.action = bpy.data.actions.new(rig.name + "_drv")
        rig.rotation_mode = "QUATERNION"
        self.track = {b: {} for b in track}
        for t in range(end + 1):
            S.frame_set(t)
            rig.matrix_world = self.src.matrix_world.normalized() @ self.base
            bpy.context.view_layer.update(); self.rt.apply()
            rig.keyframe_insert("location", frame=t); rig.keyframe_insert("rotation_quaternion", frame=t)
            rig.keyframe_insert("scale", frame=t)
            for pb in rig.pose.bones:
                pb.keyframe_insert("rotation_quaternion", frame=t)
                if pb.bone.name in self.rt.move: pb.keyframe_insert("location", frame=t)
            bpy.context.view_layer.update()
            for b in track: self.track[b][t] = rig.matrix_world @ self.bone(b).head


# ---------------------------------------------------------------- set
def pbr(name, rgb, rough):
    m = bpy.data.materials.new(name); b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


LIGHTS = []          # (light data, base energy) of the set lights, for blackouts
def hall(strip_rgb=(1.0, 0.25, 0.12), key=1.0):
    V.mesh_obj("Floor", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60), pbr("Floor", (0.05, 0.05, 0.055), 0.5), smooth=False)
    wallm = pbr("Wall", (0.07, 0.07, 0.075), 0.8)
    for x in (-5.6, 5.6):
        for k in range(8):
            w = V.mesh_obj(f"Pillar{x}_{k}", lambda bm: bmesh.ops.create_cube(bm, size=1), wallm, smooth=False)
            w.location = (x, 4.2 - k * 2.2, 2.2); w.scale = (0.45, 0.45, 4.4)
    strip, strip_s = V.emit_mat("Strip", strip_rgb)
    for x in (-4.0, 4.0):
        s = V.mesh_obj(f"Strip{x}", lambda bm: bmesh.ops.create_cube(bm, size=1), strip, smooth=False)
        s.location = (x, -5, 0.03); s.scale = (0.04, 22, 0.02)
    w = bpy.data.worlds.new("W"); S.world = w; bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.006, 0.006, 0.01, 1)
    for nm, loc, rot, e, c in (("Key", (-3, 1.5, 4.5), (35, 0, -120), 350, (0.8, 0.85, 1)),
                               ("Rim", (3, -9, 3.5), (-60, 0, 20), 400, (0.7, 0.7, 1)),
                               ("Fill", (2.5, -3.2, 2.2), (65, 0, 38), 220, (0.9, 0.9, 1)),
                               ("SideFill", (6, -4.5, 2.5), (70, 0, 90), 350, (0.85, 0.85, 1)),
                               ("FrontFill", (1.5, -0.2, 2.0), (60, 0, 120), 90, (0.9, 0.95, 1)),
                               ("BackFill", (-1.5, 3.5, 2.4), (-60, 0, 200), 160, (0.9, 0.9, 1))):
        ld = bpy.data.lights.new(nm, "AREA"); ld.energy = e * key; ld.size = 3; ld.color = c
        o = bpy.data.objects.new(nm, ld); S.collection.objects.link(o); o.location = loc
        o.rotation_euler = [math.radians(v) for v in rot]
        LIGHTS.append((ld, ld.energy))
    return strip_s, bg


def key_lights(factor, end, strip_s=None, strip_base=1.0):
    """Multiply every set light (and the floor strips) by factor(t): flickers and blackouts."""
    for t in range(end + 1):
        f = factor(t)
        for ld, e in LIGHTS: ld.energy = e * f; ld.keyframe_insert("energy", frame=t)
        if strip_s is not None: strip_s.default_value = strip_base * f; strip_s.keyframe_insert("default_value", frame=t)


# ---------------------------------------------------------------- camera
def camera(shots, end, override=None, shakes=()):
    """shots: (first frame, loc0, loc1, look0, look1, lens). override(i, t, u, loc, look) -> (loc, look).
    shakes: (frame, amplitude m, decay frames)."""
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); S.collection.objects.link(cam); S.camera = cam
    cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24
    for t in range(end + 1):
        i = max(k for k, s in enumerate(shots) if s[0] <= t)
        f0, l0, l1, k0, k1, lens = shots[i]; f1 = shots[i + 1][0] if i + 1 < len(shots) else end + 1
        u = sm((t - f0) / max(1, f1 - f0))
        loc = Vector(l0).lerp(Vector(l1), u); look = Vector(k0).lerp(Vector(k1), u)
        if override: loc, look = override(i, t, u, loc, look)
        for th, amp, tau in shakes:
            k = t - th
            if 0 <= k < 40: s = amp * math.exp(-k / tau); loc = loc + Vector((s * math.sin(k * 2.7), s * math.sin(k * 2.1), s * math.sin(k * 3.3)))
        cam.location = loc; cam.rotation_euler = (look - loc).to_track_quat("-Z", "Y").to_euler(); cam.data.lens = lens
        cam.keyframe_insert("location", frame=t); cam.keyframe_insert("rotation_euler", frame=t); cam.data.keyframe_insert("lens", frame=t)
    for a in (cam.animation_data.action, cam.data.animation_data.action):
        for fc in a.layers[0].strips[0].channelbags[0].fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"
    return cam


def constant(obj_or_data):
    """Make every key of an object's (or datablock's) action step instead of blend."""
    ad = obj_or_data.animation_data
    if ad and ad.action:
        for fc in ad.action.layers[0].strips[0].channelbags[0].fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"


# ---------------------------------------------------------------- output
def render(mode, out, prefix, end, args, bloom=0.9):
    ng = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers"); gl = ng.nodes.new("CompositorNodeGlare"); go = ng.nodes.new("NodeGroupOutput")
    gl.inputs["Type"].default_value = "Bloom"; gl.inputs["Quality"].default_value = "High"
    gl.inputs["Threshold"].default_value = 0.9; gl.inputs["Strength"].default_value = bloom; gl.inputs["Size"].default_value = 0.9
    ng.links.new(rl.outputs["Image"], gl.inputs["Image"]); ng.links.new(gl.outputs["Image"], go.inputs[0])
    S.compositing_node_group = ng; S.render.compositor_device = "CPU"
    S.render.engine = "CYCLES"; S.cycles.device = "CPU"; S.cycles.use_denoising = True
    S.view_settings.view_transform = "AgX"; S.view_settings.look = "AgX - Medium High Contrast"
    S.cycles.volume_step_rate = 4.0
    os.makedirs(out, exist_ok=True)
    if mode == "preview":
        S.render.resolution_x, S.render.resolution_y = 360, 640; S.cycles.samples = 10
        frames = [int(f) for f in args[0].split(",")] if args else list(range(0, end + 1, 30))
        for f in frames:
            S.frame_set(f); S.render.filepath = os.path.join(out, f"{prefix}_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        S.render.resolution_x, S.render.resolution_y = 720, 1280; S.cycles.samples = 16
        S.render.use_motion_blur = True; S.render.motion_blur_shutter = 0.5
        S.render.filepath = os.path.join(out, prefix + "_")
        S.frame_start, S.frame_end = 0, end
        if args:
            a, b = args[0].split("-"); S.frame_start, S.frame_end = int(a), int(b)
        S.render.use_overwrite = False                 # resume: skip frames already on disk
        bpy.ops.render.render(animation=True)


# ---------------------------------------------------------------- smoke / dust puffs and clones
def puff(name, loc, t0, end, size=1.4, dens=2.0, rgb=(0.45, 0.43, 0.4), grow=25, fade=55, height=0.35):
    """A volume cloud that swells from frame t0 and thins out (dust, smoke, a clone's 'poof')."""
    m, nt, out = V.nodes_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord"); gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    dn = nt.nodes.new("ShaderNodeTexNoise"); dn.inputs["Scale"].default_value = 4
    a = nt.nodes.new("ShaderNodeMath"); a.operation = "MULTIPLY"; nt.links.new(gr.outputs["Fac"], a.inputs[0]); nt.links.new(dn.outputs["Fac"], a.inputs[1])
    b = nt.nodes.new("ShaderNodeMath"); b.operation = "MULTIPLY"; nt.links.new(a.outputs[0], b.inputs[0])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (*rgb, 1)
    nt.links.new(b.outputs[0], pv.inputs["Density"]); nt.links.new(pv.outputs[0], out.inputs["Volume"])
    o = V.mesh_obj(name, V.sphere(1.0, 24), m); o.location = loc
    for t in range(end + 1):
        k = t - t0
        o.scale = (0.3 + size * sm(k / grow), 0.3 + size * sm(k / grow), 0.2 + height * size * sm(k / grow)) if k > 0 else (1e-3,) * 3
        b.inputs[1].default_value = dens * (1 - sm(k / fade)) * (k > 0)
        o.hide_render = not (0 < k < fade + 2)
        o.keyframe_insert("scale", frame=t); b.inputs[1].keyframe_insert("default_value", frame=t); o.keyframe_insert("hide_render", frame=t)
    return o


def clone_objects(objs, offset, tag):
    """Copy an imported hierarchy (shared bone animation), moved by offset. Returns the copies."""
    mp = {o: o.copy() for o in objs}
    for o, c in mp.items():
        S.collection.objects.link(c); c.name = f"{o.name}_{tag}"
        if o.parent in mp: c.parent = mp[o.parent]
        for md in c.modifiers:
            if md.type == "ARMATURE" and md.object in mp: md.object = mp[md.object]
        if c.type == "MESH" and c.animation_data: c.animation_data_clear()
    for o, c in mp.items():
        if o.parent not in mp: c.location = o.location + Vector(offset)
    return list(mp.values())
