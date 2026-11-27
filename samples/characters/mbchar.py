"""Anime-style base characters from MB-Lab's *data* (mesh, morphs, weights, joints,
textures) - none of MB-Lab's add-on code is run - plus a retargeter that drives
them with the pack's mannequin animations (UAL1 unreal rig).

MB-Lab data is AGPL-3.0: rendered images/videos are fine to publish/monetise;
redistributing the generated 3D models carries AGPL terms.
"""
import bpy, json, os
from mathutils import Vector, Matrix, Quaternion

MB = os.environ.get("MBLAB_DATA", "/tmp/claude-0/-home-user-Animationator/1dec518a-cc7d-5468-9aaa-16fd636cb409/scratchpad/ext/MB-Lab/data")


def _json(rel):
    with open(os.path.join(MB, rel)) as f: return json.load(f)


# ---------------------------------------------------------------- body
def apply_morphs(mesh, values):
    """values: {"Torso_Mass": 0..1 (0.5 neutral, >1 allowed), ...}"""
    morphs = _json("morphs/anime_male_morphs.json")
    co = [v.co.copy() for v in mesh.data.vertices]
    def side(p):
        v = values.get(p, 0.5)
        return ("min" if v < 0.5 else "max"), abs(v - 0.5) * 2
    done = set()
    for key in morphs:
        base, suf = key.rsplit("_", 1)[0], key.rsplit("_", 1)[1]
        if "-" in key.split("_", 1)[1] and "-" in key.rsplit("_", 1)[1]:     # combined e.g. Torso_Mass-Tone_max-min
            region, pair = base.split("_", 1)
            a, b = pair.split("-")
            pa, pb = f"{region}_{a}", f"{region}_{b}"
            if pa not in values and pb not in values: continue
            (sa, wa), (sb, wb) = side(pa), side(pb)
            k = f"{base}_{sa}-{sb}"; w = wa * wb
        else:
            if base not in values: continue
            s, w = side(base); k = f"{base}_{s}"
        if k in done or k not in morphs or w == 0: continue
        done.add(k)
        for i, dx, dy, dz in morphs[k]:
            co[i] += Vector((dx, dy, dz)) * w
    for v, c in zip(mesh.data.vertices, co): v.co = c


def load_base(name, morph_values):
    S = bpy.context.scene
    with bpy.data.libraries.load(os.path.join(MB, "humanoid_library.blend")) as (src, dst):
        dst.objects = ["MBLab_anime_male", "MBLab_skeleton_base_fk"]
    mesh, arm = dst.objects
    for o in (mesh, arm): S.collection.objects.link(o)
    mesh.name, arm.name = name + "_Body", name + "_Rig"
    mesh.data = mesh.data.copy(); arm.data = arm.data.copy()
    apply_morphs(mesh, morph_values)

    # fit the skeleton to the (morphed) mesh: joint = centroid of listed vertices
    joints = _json("joints/anime_male_joints.json")
    vco = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
    cen = lambda ids: sum((vco[i] for i in ids), Vector()) / len(ids)
    inv = arm.matrix_world.inverted()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for eb in arm.data.edit_bones:
        roll = eb.roll
        if eb.name + "_head" in joints: eb.head = inv @ cen(joints[eb.name + "_head"])
        if eb.name + "_tail" in joints: eb.tail = inv @ cen(joints[eb.name + "_tail"])
        eb.roll = roll
    bpy.ops.object.mode_set(mode="OBJECT")

    # skin weights
    for g, pairs in _json("vgroups/anime_male_vgroups_base.json").items():
        vg = mesh.vertex_groups.new(name=g)
        for i, w in pairs: vg.add([i], w, "REPLACE")
    mesh.parent = arm
    mesh.matrix_parent_inverse = arm.matrix_world.inverted()
    mod = mesh.modifiers.new("Armature", "ARMATURE"); mod.object = arm
    for p in mesh.data.polygons: p.use_smooth = True
    sub = mesh.modifiers.new("Subsurf", "SUBSURF"); sub.levels = sub.render_levels = 1
    return arm, mesh


def skin_materials(mesh, skin_tint=(1, 1, 1), eye_rgb=(0.2, 0.45, 1.0), eye_glow=0.0, name="Char"):
    """Cycles materials: textured skin, coloured anime eyes, black lashes/brows."""
    tex = bpy.data.images.load(os.path.join(MB, "textures/anime_male_albedo.png"), check_existing=True)
    def principled(n):
        m = bpy.data.materials.new(n); m.use_nodes = True
        return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]
    skin, nt, b = principled(name + "_Skin")
    img = nt.nodes.new("ShaderNodeTexImage"); img.image = tex
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    ins = {i.identifier: i for i in mix.inputs}; outs = {o.identifier: o for o in mix.outputs}
    ins["Factor_Float"].default_value = 1.0; ins["B_Color"].default_value = (*skin_tint, 1)
    nt.links.new(img.outputs["Color"], ins["A_Color"]); nt.links.new(outs["Result_Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    # (no subsurface: it goes dark on this mesh because of the eye/mouth shells inside the head)
    eyes, nt, b = principled(name + "_Eyes")
    img = nt.nodes.new("ShaderNodeTexImage"); img.image = tex
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    nt.links.new(img.outputs["Color"], hsv.inputs["Color"]); nt.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.15
    b.inputs["Coat Weight"].default_value = 0.6
    if eye_glow:
        b.inputs["Emission Color"].default_value = (*eye_rgb, 1); b.inputs["Emission Strength"].default_value = eye_glow
    black, nt, b = principled(name + "_Lash")
    b.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1); b.inputs["Roughness"].default_value = 0.8
    inner, nt, b = principled(name + "_Mouth")
    b.inputs["Base Color"].default_value = (0.35, 0.08, 0.08, 1)
    # slots in MB-Lab order: toon_black(lash/brow), generic(mouth), skin, eyes
    idx = [0] * len(mesh.data.polygons)        # materials.clear() resets face indices: keep them
    mesh.data.polygons.foreach_get("material_index", idx)
    mesh.data.materials.clear()
    for m in (black, inner, skin, eyes): mesh.data.materials.append(m)
    mesh.data.polygons.foreach_set("material_index", idx)
    mesh.data.update()
    for slot in mesh.material_slots:          # MB-Lab links its slots per object; use the mesh's
        slot.link = "DATA"
    return {"skin": skin, "eyes": eyes}


# ---------------------------------------------------------------- retarget
MAP = {"root": "root", "pelvis": "pelvis", "spine_01": "spine01", "spine_02": "spine02",
       "spine_03": "spine03", "neck_01": "neck", "Head": "head"}
for s, t in (("l", "L"), ("r", "R")):
    MAP.update({f"clavicle_{s}": f"clavicle_{t}", f"upperarm_{s}": f"upperarm_{t}",
                f"lowerarm_{s}": f"lowerarm_{t}", f"hand_{s}": f"hand_{t}",
                f"thigh_{s}": f"thigh_{t}", f"calf_{s}": f"calf_{t}", f"foot_{s}": f"foot_{t}",
                f"ball_{s}": f"toes_{t}"})
    for f in ("index", "middle", "ring", "pinky"):
        for i in (1, 2, 3): MAP[f"{f}_0{i}_{s}"] = f"{f}0{i}_{t}"
    for i in (1, 2, 3): MAP[f"thumb_0{i}_{s}"] = f"thumb0{i}_{t}"
INV = {t: s for s, t in MAP.items()}


class Retarget:
    def __init__(self, src, tgt):
        self.src, self.tgt = src, tgt
        sw, tw = src.matrix_world.to_3x3().normalized(), tgt.matrix_world.to_3x3().normalized()
        self.align = {}
        for tb in tgt.data.bones:
            sname = INV.get(tb.name)
            if not sname or sname not in src.data.bones: continue
            S_rest = sw @ src.data.bones[sname].matrix_local.to_3x3()
            T_rest = tw @ tb.matrix_local.to_3x3()
            q = T_rest.col[1].rotation_difference(S_rest.col[1]).to_matrix()
            self.align[tb.name] = (sname, S_rest.inverted(), q @ T_rest)
        sp = src.data.bones["pelvis"].head_local.z
        tp = tgt.data.bones["pelvis"].head_local.z
        self.k = tp / sp

    def apply(self):
        """Pose tgt from src's current (evaluated) pose."""
        src, tgt = self.src, self.tgt
        sw = src.matrix_world.to_3x3().normalized()
        tw_inv = tgt.matrix_world.inverted()
        tw3_inv = tgt.matrix_world.to_3x3().normalized().inverted()
        posed = {}                                            # armature-space 4x4 of each target bone
        for tb in tgt.data.bones:                             # parents come before children
            pb = tgt.pose.bones[tb.name]
            if tb.parent:
                base = posed[tb.parent.name] @ (tb.parent.matrix_local.inverted() @ tb.matrix_local)
            else:
                base = tb.matrix_local.copy()
            if tb.name in self.align:
                sname, S_rest_inv, T_rest_al = self.align[tb.name]
                S_pose = sw @ src.pose.bones[sname].matrix.to_3x3()
                T_arm = tw3_inv @ (S_pose @ S_rest_inv @ T_rest_al)
                local_rot = (base.to_3x3().inverted() @ T_arm).to_quaternion()
            else:
                local_rot = Quaternion()
            loc = Vector()
            if tb.name in ("root", "pelvis"):
                s_head_w = src.matrix_world @ src.pose.bones[INV[tb.name]].head
                s_org, t_org = src.matrix_world.translation, tgt.matrix_world.translation
                want_w = t_org + (s_head_w - s_org) * self.k
                want = tw_inv @ want_w
                loc = base.inverted() @ want
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = local_rot
            pb.location = loc
            posed[tb.name] = base @ Matrix.Translation(loc) @ local_rot.to_matrix().to_4x4()
