"""Two original fighters built on the pack's mannequin rig (UAL1_unreal_rig), so every
mannequin animation (and fight.py) works on them unchanged.

  SORCERER  - tall, white gravity-defying hair, black blindfold, navy high-collar coat.
  ONI KING  - swept-back crimson hair, four glowing red eyes, black face/arm markings,
              off-white robe with a dark red sash.

Use from another bpy script:
    import characters; characters.dress(rig, mesh, "sorcerer")   # or "oni"
Run directly to render a line-up and export GLBs:
    ~/blendervenv/bin/python characters.py -- OUT_DIR
"""
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

# rest-pose head measurements (metres, rig space; character faces -Y)
HEAD_C = Vector((0.0, -0.003, 1.69))
HEAD_R = Vector((0.087, 0.115, 0.14))


# ---------------------------------------------------------------- helpers
def material(name, rgb, rough=0.5, emit=0.0, metal=0.0, sheen=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def new_obj(name, bm, mat, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    return o


def attach(obj, rig, bone):
    """Parent obj to a bone, keeping its current (rest-pose) placement."""
    b = rig.data.bones[bone]
    tail = rig.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    obj.parent, obj.parent_type, obj.parent_bone = rig, "BONE", bone
    obj.matrix_parent_inverse = tail.inverted()


def aim(direction):
    """Rotation taking +Z to direction."""
    return Vector((0, 0, 1)).rotation_difference(direction.normalized()).to_matrix().to_4x4()


def tube(bm, centre, axis, rx, ry, height, segs=32, thick=0.008):
    """Open band (like a collar/blindfold) as a closed thin ring solid."""
    rot = aim(axis)
    rings = []
    for (r_off, h) in ((0, -height / 2), (0, height / 2), (thick, height / 2), (thick, -height / 2)):
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            p = Vector(((rx + r_off) * math.cos(a), (ry + r_off) * math.sin(a), h))
            ring.append(bm.verts.new(centre + (rot @ p)))
        rings.append(ring)
    for k in range(4):
        r0, r1 = rings[k], rings[(k + 1) % 4]
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))


def rest_bvh(rig, mesh):
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(mesh, dg)
    rig.data.pose_position = "POSE"
    return bvh


def surface(bvh, x, z, from_y=-1.0):
    """Point and normal where a ray from the front (−Y) hits the body at (x, z)."""
    loc, nrm, _, _ = bvh.ray_cast(Vector((x, from_y, z)), Vector((0, 1, 0)))
    return loc, nrm


def paint_regions(mesh, region_of, mats):
    """Assign each face a material by its dominant bone."""
    names = {vg.index: vg.name for vg in mesh.vertex_groups}
    me = mesh.data
    me.materials.clear()
    keys = list(mats)
    for k in keys: me.materials.append(mats[k])
    vw = [{names[g.group]: g.weight for g in v.groups} for v in me.vertices]
    for p in me.polygons:
        tot = {}
        for vi in p.vertices:
            for n, w in vw[vi].items(): tot[n] = tot.get(n, 0) + w
        bone = max(tot, key=tot.get) if tot else "pelvis"
        p.material_index = keys.index(region_of(bone))


def hair(bm, rng, n, up_bias, back_bias, length, radius, front_min_z,
         cap_off=(0, 0.03, 0.075), cap_r=(0.097, 0.118, 0.085)):
    """Spiky hair: a cap plus n cones sprouting from the upper head."""
    cap = Matrix.Translation(HEAD_C + Vector(cap_off)) @ Matrix.Diagonal((*cap_r, 1))
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0, matrix=cap)
    made = 0
    while made < n:
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 1))).normalized()
        if d.y < -0.3 and d.z < front_min_z: continue          # keep the face clear
        if d.z < 0.25 and d.y < 0.2: continue                   # no spikes over the ears
        base = HEAD_C + Vector((d.x * HEAD_R.x, d.y * HEAD_R.y + 0.02, d.z * HEAD_R.z)) * 0.9 + Vector((0, 0, 0.06))
        tip_dir = (d + Vector((0, back_bias, up_bias))).normalized()
        L = rng.uniform(*length); r = rng.uniform(*radius)
        M = Matrix.Translation(base + tip_dir * L / 2) @ aim(tip_dir)
        bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=r, radius2=0.002, depth=L, matrix=M)
        made += 1


# ---------------------------------------------------------------- designs
def sorcerer(rig, mesh):
    skin = material("Sorc_Skin", (0.80, 0.62, 0.52), 0.55)
    coat = material("Sorc_Coat", (0.018, 0.022, 0.045), 0.65, sheen=0.3)
    shoe = material("Sorc_Shoe", (0.01, 0.01, 0.012), 0.35)
    white = material("Sorc_Hair", (0.92, 0.94, 0.98), 0.45, sheen=0.5)
    cloth = material("Sorc_Blindfold", (0.008, 0.008, 0.01), 0.8)

    def region(b):
        if b in ("Head", "neck_01") or b.startswith(("hand", "index", "middle", "ring", "pinky", "thumb")):
            return "skin"
        if b.startswith(("foot", "ball")): return "shoe"
        return "coat"
    paint_regions(mesh, region, {"skin": skin, "coat": coat, "shoe": shoe})

    rng = random.Random(7)
    bm = bmesh.new()
    hair(bm, rng, 70, up_bias=0.9, back_bias=0.15, length=(0.09, 0.17), radius=(0.026, 0.04), front_min_z=0.45,
         cap_off=(0, 0.008, 0.045), cap_r=(0.097, 0.124, 0.095))
    attach(new_obj("Sorc_Hair", bm, white), rig, "Head")

    bm = bmesh.new()   # blindfold across the eyes
    tube(bm, HEAD_C + Vector((0, 0.002, 0.0)), Vector((0, 0, 1)), 0.091, 0.12, 0.05, thick=0.006)
    attach(new_obj("Sorc_Blindfold", bm, cloth), rig, "Head")

    bm = bmesh.new()   # tall stiff collar
    tube(bm, Vector((0, -0.006, 1.535)), Vector((0, 0.08, 1)), 0.085, 0.09, 0.12, thick=0.01)
    attach(new_obj("Sorc_Collar", bm, coat), rig, "spine_03")


def oni(rig, mesh):
    skin = material("Oni_Skin", (0.72, 0.48, 0.36), 0.5)
    robe = material("Oni_Robe", (0.86, 0.83, 0.76), 0.75, sheen=0.4)
    sash = material("Oni_Sash", (0.22, 0.015, 0.02), 0.6, sheen=0.3)
    shoe = material("Oni_Sandal", (0.04, 0.03, 0.025), 0.5)
    hairm = material("Oni_Hair", (0.75, 0.16, 0.24), 0.5, sheen=0.4)
    ink = material("Oni_Ink", (0.01, 0.008, 0.008), 0.6)
    eye = material("Oni_Eye", (1.0, 0.02, 0.01), 0.3, emit=1.2)

    def region(b):
        if b in ("Head", "neck_01") or b.startswith(("lowerarm", "hand", "index", "middle", "ring", "pinky", "thumb")):
            return "skin"
        if b.startswith(("foot", "ball")): return "shoe"
        return "robe"
    paint_regions(mesh, region, {"skin": skin, "robe": robe, "shoe": shoe})

    rng = random.Random(3)
    bm = bmesh.new()
    hair(bm, rng, 55, up_bias=0.25, back_bias=1.5, length=(0.07, 0.13), radius=(0.024, 0.036), front_min_z=0.55)
    attach(new_obj("Oni_Hair", bm, hairm), rig, "Head")

    bvh = rest_bvh(rig, mesh)
    bm_eye, bm_ink = bmesh.new(), bmesh.new()
    for s in (-1, 1):
        for x, z, r in ((0.034, 1.695, 0.012), (0.041, 1.66, 0.009)):        # four eyes
            p, n = surface(bvh, s * x, z)
            tilt = Matrix.Rotation(s * 0.22, 4, "Z")                           # angry upward slant
            M = Matrix.Translation(p + n * 0.001) @ aim(n) @ tilt @ Matrix.Diagonal((r * 1.7, r * 0.55, r * 0.4, 1))
            bmesh.ops.create_uvsphere(bm_eye, u_segments=12, v_segments=8, radius=1.0, matrix=M)
            M = Matrix.Translation(p - n * 0.001) @ aim(n) @ tilt @ Matrix.Diagonal((r * 2.2, r * 1.05, r * 0.35, 1))
            bmesh.ops.create_uvsphere(bm_ink, u_segments=12, v_segments=8, radius=1.0, matrix=M)   # dark socket
        for z in (1.628, 1.614):                                               # cheek stripes
            p, n = surface(bvh, s * 0.058, z)
            M = Matrix.Translation(p) @ aim(n) @ Matrix.Rotation(s * 0.25, 4, "Z") @ Matrix.Diagonal((0.024, 0.0035, 0.003, 1))
            bmesh.ops.create_cube(bm_ink, size=2.0, matrix=M)
        p, n = surface(bvh, s * 0.03, 1.728)                                   # brow marks
        M = Matrix.Translation(p) @ aim(n) @ Matrix.Rotation(s * 0.5, 4, "Z") @ Matrix.Diagonal((0.018, 0.004, 0.003, 1))
        bmesh.ops.create_cube(bm_ink, size=2.0, matrix=M)
    attach(new_obj("Oni_Eyes", bm_eye, eye), rig, "Head")
    attach(new_obj("Oni_FaceInk", bm_ink, ink, smooth=False), rig, "Head")

    for side, bone in ((1, "lowerarm_l"), (-1, "lowerarm_r")):                # forearm bands
        bm = bmesh.new()
        for x in (0.55, 0.61, 0.67):
            tube(bm, Vector((side * x, 0.071, 1.433)), Vector((1, 0, 0)), 0.064, 0.061, 0.012, thick=0.003)
        attach(new_obj(f"Oni_ArmInk_{side}", bm, ink), rig, bone)

    bm = bmesh.new()                                                           # sash
    tube(bm, Vector((0, 0.003, 1.03)), Vector((0, 0, 1)), 0.152, 0.13, 0.07, thick=0.012)
    attach(new_obj("Oni_Sash", bm, sash), rig, "pelvis")


def dress(rig, mesh, kind):
    {"sorcerer": sorcerer, "oni": oni}[kind](rig, mesh)


# ---------------------------------------------------------------- line-up
if __name__ == "__main__":
    OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/chars"
    PACK = "/home/user/Animationator/toolkit/3d-pack/animation/UAL1_unreal_rig_45anims.glb"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    S = bpy.context.scene

    def load():
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=PACK)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.type != "ARMATURE" and not o.name.startswith("Mannequin"): bpy.data.objects.remove(o)
        new = [o for o in bpy.data.objects if o not in before]
        return next(o for o in new if o.type == "ARMATURE"), next(o for o in new if o.type == "MESH")

    for kind in ("sorcerer", "oni"):   # export each from a clean scene: one set of 45 clips
        bpy.ops.wm.read_factory_settings(use_empty=True)
        rig, mesh = load(); dress(rig, mesh, kind)
        rig.name = kind.capitalize() + "_Rig"
        bpy.ops.object.select_all(action="DESELECT")
        for o in [rig] + list(rig.children_recursive): o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=f"{OUT}/{kind}.glb", use_selection=True, export_animation_mode="ACTIONS")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    S = bpy.context.scene
    chars = {}
    for kind in ("sorcerer", "oni"):
        rig, mesh = load(); dress(rig, mesh, kind); chars[kind] = rig
        rig.name = kind.capitalize() + "_Rig"

    idle = bpy.data.actions["Rig|Rig|Idle_Loop"]
    # the pack's clips also key the rig object's transform, so place each via a parent empty
    for kind, x, turn in (("sorcerer", 0.55, 18), ("oni", -0.55, -18)):
        rig = chars[kind]
        rig.animation_data_create(); rig.animation_data.action = idle
        rig.animation_data.action_slot = idle.slots[0]
        e = bpy.data.objects.new(kind + "_place", None); S.collection.objects.link(e)
        e.location.x = x; e.rotation_euler.z = math.radians(turn); rig.parent = e
    S.frame_set(20)

    bpy.ops.mesh.primitive_plane_add(size=30)
    bpy.context.active_object.data.materials.append(material("Floor", (0.05, 0.05, 0.055), 0.7))
    w = bpy.data.worlds.new("W"); S.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.015, 0.016, 0.022, 1)
    for name, loc, rot, e, c in (("Key", (-2.5, -3.5, 3.5), (50, 0, -35), 700, (1, 0.95, 0.9)),
                                 ("Fill", (3, -3, 2), (60, 0, 45), 250, (0.8, 0.85, 1)),
                                 ("Rim", (0, 3, 3), (-55, 0, 180), 600, (0.7, 0.8, 1))):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = e; ld.size = 2.5; ld.color = c
        o = bpy.data.objects.new(name, ld); S.collection.objects.link(o)
        o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]

    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); S.collection.objects.link(cam); S.camera = cam
    S.render.engine = "CYCLES"; S.cycles.samples = 48; S.cycles.use_denoising = True
    S.view_settings.view_transform = "AgX"; S.view_settings.look = "AgX - Medium High Contrast"
    S.render.resolution_x, S.render.resolution_y = 1280, 720

    def shoot(loc, target, lens, path):
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        S.render.filepath = path; bpy.ops.render.render(write_still=True)

    shoot((0, -4.6, 1.2), (0, 0, 0.95), 40, f"{OUT}/lineup.png")
    shoot((0.55 + 0.25, -1.1, 1.72), (0.55, 0, 1.66), 60, f"{OUT}/sorcerer_face.png")
    shoot((-0.55 - 0.25, -1.1, 1.72), (-0.55, 0, 1.66), 60, f"{OUT}/oni_face.png")
    bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/characters.blend")
