"""Hollow Purple VFX parts (orbs, glow materials, mesh helpers), shared by the Gojo scenes.
Import after the scene is reset: it uses the current scene."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix
S = bpy.context.scene

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


