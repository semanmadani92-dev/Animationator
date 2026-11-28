"""Vaporise a skinned character: its body flares with heat, then burns away from an impact
point outwards (a glowing edge eats through every material) while the burned-off surface
becomes embers that drift with the blast and cool into ash.

    import vaporise
    v = vaporise.Vaporise(meshes, centre_world, start=113, burn=24, push=Vector((0, -1, 0)))
    v.key(t)            # per frame, after the character's animation is baked
    v.embers()          # once, after baking: builds the ember particles
"""
import bpy, math, random
import numpy as np
from mathutils import Vector, noise

HEAT_RGB = (0.62, 0.16, 1.0)


def smooth(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)


class Vaporise:
    def __init__(self, meshes, centre, start, burn=24, push=Vector((0, -1, 0)), seed=3):
        self.meshes, self.start, self.burn, self.push = meshes, start, burn, push.normalized()
        self.t0 = start + 3                         # flare for 3 frames, then burn
        self.rng = random.Random(seed)
        S = bpy.context.scene
        S.frame_set(0)
        dg = bpy.context.evaluated_depsgraph_get()
        # burn order per vertex: distance from the impact point + low-frequency noise, in 0..1
        vals = {}
        for o in meshes:
            ev = o.evaluated_get(dg); me = ev.to_mesh(); mw = ev.matrix_world
            vals[o] = [((mw @ v.co) - centre).length + 0.35 * noise.noise((mw @ v.co) * 2.5) for v in me.vertices]
            ev.to_mesh_clear()
        lo = min(min(v) for v in vals.values()); hi = max(max(v) for v in vals.values())
        self.order = {}
        for o in meshes:
            a = np.array([(x - lo) / (hi - lo) for x in vals[o]], dtype=np.float32)
            attr = o.data.attributes.get("vap") or o.data.attributes.new("vap", "FLOAT", "POINT")
            attr.data.foreach_set("value", a)
            self.order[o] = a
        self.thr, self.heat = [], []
        for m in {s.material for o in meshes for s in o.material_slots if s.material}:
            self._patch(m)

    def threshold(self, t):
        return -0.08 + 1.16 * (t - self.t0) / self.burn

    def birth(self, v):                              # frame at which burn-order value v is reached
        return self.t0 + (v + 0.08) / 1.16 * self.burn

    def _patch(self, m):
        """original surface + heat glow + burning edge, cut away where burned"""
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
        if not out.inputs["Surface"].links: return
        orig = out.inputs["Surface"].links[0].from_socket
        N = nt.nodes.new
        at = N("ShaderNodeAttribute"); at.attribute_name = "vap"
        tc = N("ShaderNodeTexCoord"); nz = N("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 14
        nz.inputs["Detail"].default_value = 4
        nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
        jit = N("ShaderNodeMath"); jit.operation = "MULTIPLY_ADD"
        nt.links.new(nz.outputs["Fac"], jit.inputs[0]); jit.inputs[1].default_value = 0.14
        nt.links.new(at.outputs["Fac"], jit.inputs[2])
        thr = N("ShaderNodeValue")
        d = N("ShaderNodeMath"); d.operation = "SUBTRACT"
        nt.links.new(jit.outputs[0], d.inputs[0]); nt.links.new(thr.outputs[0], d.inputs[1])
        d.inputs[1].default_value = 0
        gone = N("ShaderNodeMath"); gone.operation = "LESS_THAN"; gone.inputs[1].default_value = 0.07
        nt.links.new(d.outputs[0], gone.inputs[0])
        edge = N("ShaderNodeMapRange"); edge.inputs["From Min"].default_value = 0.07
        edge.inputs["From Max"].default_value = 0.17; edge.inputs["To Min"].default_value = 1
        edge.inputs["To Max"].default_value = 0; edge.interpolation_type = "SMOOTHSTEP"
        nt.links.new(d.outputs[0], edge.inputs["Value"])
        ramp = N("ShaderNodeValToRGB"); ce = ramp.color_ramp.elements
        ce[0].color = (*HEAT_RGB, 1); ce[1].color = (1, 0.92, 1, 1); ce[1].position = 0.8
        nt.links.new(edge.outputs[0], ramp.inputs["Fac"])
        heat = N("ShaderNodeValue")
        es = N("ShaderNodeMath"); es.operation = "MULTIPLY_ADD"          # edge * 25 + heat
        nt.links.new(edge.outputs[0], es.inputs[0]); es.inputs[1].default_value = 25
        nt.links.new(heat.outputs[0], es.inputs[2])
        em = N("ShaderNodeEmission")
        nt.links.new(ramp.outputs["Color"], em.inputs["Color"]); nt.links.new(es.outputs[0], em.inputs["Strength"])
        add = N("ShaderNodeAddShader"); nt.links.new(orig, add.inputs[0]); nt.links.new(em.outputs[0], add.inputs[1])
        tr = N("ShaderNodeBsdfTransparent"); mix = N("ShaderNodeMixShader")
        nt.links.new(gone.outputs[0], mix.inputs[0]); nt.links.new(add.outputs[0], mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs["Surface"])
        self.thr.append(thr.outputs[0]); self.heat.append(heat.outputs[0])

    def key(self, t):
        th = self.threshold(t) if t >= self.t0 else -1.0
        h = 0.7 * smooth((t - self.start) / 2) * (1 - smooth((t - self.t0 - self.burn * 0.8) / 6))
        for s in self.thr: s.default_value = th; s.keyframe_insert("default_value", frame=t)
        for s in self.heat: s.default_value = h; s.keyframe_insert("default_value", frame=t)

    def embers(self, n=3600, life=(22, 48), name="Embers"):
        """Particles born on the surface where (and when) it burns away."""
        S = bpy.context.scene
        rng = self.rng
        # triangles + areas at the start pose, then pick points
        S.frame_set(self.start); dg = bpy.context.evaluated_depsgraph_get()
        tris, areas = [], []
        for o in self.meshes:
            ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles(); mw = ev.matrix_world
            for lt in me.loop_triangles:
                a, b, c = (mw @ me.vertices[i].co for i in lt.vertices)
                tris.append((o, tuple(lt.vertices))); areas.append(((b - a).cross(c - a)).length / 2)
            ev.to_mesh_clear()
        pick = rng.choices(range(len(tris)), weights=areas, k=n)
        pts = []
        for k in pick:
            o, vs = tris[k]
            u, v = rng.random(), rng.random()
            if u + v > 1: u, v = 1 - u, 1 - v
            w = (1 - u - v, u, v)
            order = sum(self.order[o][i] * wi for i, wi in zip(vs, w))
            b = self.birth(order) + rng.uniform(-1.5, 1.5)
            pts.append((o, vs, w, b))
        # position of every point at its birth frame, on the deforming body
        by_frame = {}
        for i, p in enumerate(pts): by_frame.setdefault(int(round(p[3])), []).append(i)
        pos = [None] * n
        for f in sorted(by_frame):
            S.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
            cache = {}
            for i in by_frame[f]:
                o, vs, w, b = pts[i]
                if o not in cache:
                    ev = o.evaluated_get(dg); me = ev.to_mesh()
                    co = np.empty(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", co)
                    cache[o] = (co.reshape(-1, 3), ev.matrix_world.copy()); ev.to_mesh_clear()
                co, mw = cache[o]
                pos[i] = mw @ Vector(sum(co[j] * wj for j, wj in zip(vs, w)))
        me = bpy.data.meshes.new(name); me.from_pydata([tuple(p) for p in pos], [], [])
        def attr(nm, typ, vals):
            a = me.attributes.new(nm, typ, "POINT")
            a.data.foreach_set("vector" if typ == "FLOAT_VECTOR" else "value", np.array(vals, dtype=np.float32).ravel())
        vel = []
        for i in range(n):
            out = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            vel.append(tuple(self.push * rng.uniform(0.02, 0.14) + out * rng.uniform(0.01, 0.05) + Vector((0, 0, 0.01))))
        attr("vel", "FLOAT_VECTOR", vel)
        attr("birth", "FLOAT", [p[3] for p in pts])
        attr("life", "FLOAT", [rng.uniform(*life) for _ in range(n)])
        attr("size", "FLOAT", [rng.uniform(0.004, 0.012) for _ in range(n)])
        ob = bpy.data.objects.new(name, me); S.collection.objects.link(ob)
        mod = ob.modifiers.new("Embers", "NODES"); mod.node_group = _ember_nodes(_ember_mat())
        return ob


def _ember_mat():
    m = bpy.data.materials.new("Ember"); nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.02, 0.016, 0.02, 1); b.inputs["Roughness"].default_value = 0.9
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "heat"
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ce = ramp.color_ramp.elements
    ce[0].color = (0.25, 0.04, 0.5, 1); ce[0].position = 0.25
    ce[1].color = (1, 0.9, 1, 1); ce[1].position = 0.95
    e = ce.new(0.6); e.color = (*HEAT_RGB, 1)
    nt.links.new(at.outputs["Fac"], ramp.inputs["Fac"])
    p = nt.nodes.new("ShaderNodeMath"); p.operation = "POWER"; p.inputs[1].default_value = 2.5
    nt.links.new(at.outputs["Fac"], p.inputs[0])
    k = nt.nodes.new("ShaderNodeMath"); k.operation = "MULTIPLY"; k.inputs[1].default_value = 18
    nt.links.new(p.outputs[0], k.inputs[0])
    nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"]); nt.links.new(k.outputs[0], b.inputs["Emission Strength"])
    return m


def _ember_nodes(mat, tau=9.0, rise=0.0007):
    ng = bpy.data.node_groups.new("Embers", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, Lk = ng.nodes.new, ng.links.new
    gi, go = N("NodeGroupInput"), N("NodeGroupOutput")

    def named(nm, typ="FLOAT"):
        n = N("GeometryNodeInputNamedAttribute"); n.data_type = typ; n.inputs["Name"].default_value = nm
        return n.outputs["Attribute"]

    def math(op, a, b=None, clamp=False):
        n = N("ShaderNodeMath"); n.operation = op; n.use_clamp = clamp
        for i, x in enumerate((a, b)):
            if x is None: continue
            if isinstance(x, (int, float)): n.inputs[i].default_value = x
            else: Lk(x, n.inputs[i])
        return n.outputs[0]

    frame = N("GeometryNodeInputSceneTime").outputs["Frame"]
    life, size = named("life"), named("size")
    age_raw = math("SUBTRACT", frame, named("birth"))
    age = math("MAXIMUM", age_raw, 0.0)
    damp = math("MULTIPLY", math("SUBTRACT", 1.0, math("EXPONENT", math("MULTIPLY", age, -1.0 / tau))), tau)
    sc = N("ShaderNodeVectorMath"); sc.operation = "SCALE"
    Lk(named("vel", "FLOAT_VECTOR"), sc.inputs[0]); Lk(damp, sc.inputs["Scale"])
    up = N("ShaderNodeCombineXYZ"); Lk(math("MULTIPLY", math("MULTIPLY", age, age), rise), up.inputs["Z"])
    off = N("ShaderNodeVectorMath"); off.operation = "ADD"; Lk(sc.outputs[0], off.inputs[0]); Lk(up.outputs[0], off.inputs[1])
    sp = N("GeometryNodeSetPosition"); Lk(gi.outputs[0], sp.inputs["Geometry"]); Lk(off.outputs[0], sp.inputs["Offset"])
    alive = math("GREATER_THAN", age_raw, 0.0)
    fade = math("DIVIDE", math("SUBTRACT", life, age), 8.0, clamp=True)
    scale = math("MULTIPLY", math("MULTIPLY", size, alive), fade)
    heat = math("SUBTRACT", 1.0, math("DIVIDE", age, life), clamp=True)
    st = N("GeometryNodeStoreNamedAttribute"); st.data_type = "FLOAT"; st.domain = "POINT"
    st.inputs["Name"].default_value = "heat"
    Lk(sp.outputs[0], st.inputs["Geometry"]); Lk(heat, st.inputs["Value"])
    ico = N("GeometryNodeMeshIcoSphere"); ico.inputs["Radius"].default_value = 1.0; ico.inputs["Subdivisions"].default_value = 1
    sm = N("GeometryNodeSetMaterial"); sm.inputs["Material"].default_value = mat; Lk(ico.outputs["Mesh"], sm.inputs["Geometry"])
    iop = N("GeometryNodeInstanceOnPoints")
    Lk(st.outputs[0], iop.inputs["Points"]); Lk(sm.outputs[0], iop.inputs["Instance"]); Lk(scale, iop.inputs["Scale"])
    rz = N("GeometryNodeRealizeInstances"); Lk(iop.outputs[0], rz.inputs[0]); Lk(rz.outputs[0], go.inputs[0])
    return ng
