"""Turn the Yuji model into Sukuna: paint the face markings and red eyes into a copy of
its texture (placed by 3D position on the face, so they land correctly on the UVs).

    ~/blendervenv/bin/python sukuna.py -- YUJI_FBX OUT_PNG [preview.png]
Also importable: sukuna.apply(objects) on an already-imported Yuji.
"""
import bpy, sys, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform, intersect_point_tri

EYEBALL_UV = Vector((0.596, 0.703))      # centre of the eyeball disc in yuji.png


def apply(objs, out_png=None):
    head = next(o for o in objs if o.type == "MESH" and o.name.startswith("head"))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = head.evaluated_get(dg); me = ev.to_mesh()
    mw = head.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    loops = [list(p.loop_indices) for p in me.polygons]
    uvs = [d.uv.copy() for d in me.uv_layers.active.data]
    bvh = BVHTree.FromPolygons(verts, polys)

    # eye centres: faces textured from the eyeball disc
    eye = [sum((verts[i] for i in polys[f]), Vector()) / len(polys[f]) for f in range(len(polys))
           if any((uvs[l] - EYEBALL_UV).length < 0.03 for l in loops[f])]
    el = sum((c for c in eye if c.x > 0), Vector()) / max(1, len([c for c in eye if c.x > 0]))
    er = sum((c for c in eye if c.x < 0), Vector()) / max(1, len([c for c in eye if c.x < 0]))

    mat = head.material_slots[0].material
    node = next(n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and "yuji" in n.image.name.lower())
    src = node.image
    W, H = src.size
    px = np.empty(W * H * 4, dtype=np.float32); src.pixels.foreach_get(px); px = px.reshape(H, W, 4)

    def uv_at(x, z):
        loc, nrm, fi, _ = bvh.ray_cast(Vector((x, -2.0, z)), Vector((0, 1, 0)))
        if fi is None: return None
        vs, ls = polys[fi], loops[fi]
        tris = ((0, 1, 2), (0, 2, 3)) if len(vs) == 4 else ((0, 1, 2),)
        for k, (a, b, c) in enumerate(tris):
            A, B, C = verts[vs[a]], verts[vs[b]], verts[vs[c]]
            if intersect_point_tri(loc, A, B, C) or k == len(tris) - 1:
                uv = barycentric_transform(loc, A, B, C, *(uvs[ls[j]].to_3d() for j in (a, b, c)))
                return uv.x, uv.y

    def dab(cx, cy, r, rgb, soft=0.6):
        x0, x1 = int(max(0, cx - r - 2)), int(min(W, cx + r + 2))
        y0, y1 = int(max(0, cy - r - 2)), int(min(H, cy + r + 2))
        if x0 >= x1 or y0 >= y1: return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        a = np.clip((r - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)) / soft + 0.5, 0, 1)[..., None]
        px[y0:y1, x0:x1, :3] = px[y0:y1, x0:x1, :3] * (1 - a) + np.array(rgb) * a

    def stroke(pts, width_m, rgb=(0.02, 0.015, 0.02), taper=0.85):
        """pts in face-space (x, z) metres; width in metres, converted via local UV scale."""
        n = 80
        for k in range(n + 1):
            t = k / n
            seg = min(int(t * (len(pts) - 1)), len(pts) - 2); u = t * (len(pts) - 1) - seg
            x = pts[seg][0] * (1 - u) + pts[seg + 1][0] * u
            z = pts[seg][1] * (1 - u) + pts[seg + 1][1] * u
            a, b = uv_at(x, z), uv_at(x + 0.004, z)
            if not a or not b: continue
            px_per_m = math.hypot((b[0] - a[0]) * W, (b[1] - a[1]) * H) / 0.004
            r = 0.5 * width_m * px_per_m * (1 - abs(t - 0.5) * 2 * taper)
            dab(a[0] * W, a[1] * H, max(r, 0.6), rgb)

    s = 1 if el.x > 0 else -1
    ex, ez = abs(el.x), el.z
    for side in (1, -1):
        x = ex * side
        # the second eye: a thick dark lid line under each eye, then a thinner stripe below
        stroke([(x - side * 0.007, ez - 0.015), (x + side * 0.004, ez - 0.018), (x + side * 0.015, ez - 0.014)], 0.0022, taper=0.7)
        stroke([(x - side * 0.004, ez - 0.025), (x + side * 0.006, ez - 0.027), (x + side * 0.014, ez - 0.024)], 0.0015)

    # red irises: recolour the pupil dot in the eyeball disc and widen it
    cx, cy = EYEBALL_UV.x * W, EYEBALL_UV.y * H
    ys, xs = np.mgrid[0:H, 0:W]
    disc = (xs - cx) ** 2 + (ys - cy) ** 2 < (0.045 * W) ** 2
    red = disc & (px[..., 0] > px[..., 2] + 0.15) & (px[..., 0] > 0.3)
    if red.any():
        py, pxx = np.nonzero(red); icx, icy = pxx.mean(), py.mean()
    else:
        icx, icy = cx, cy
    dab(icx, icy, 0.017 * W, (0.75, 0.03, 0.03), soft=1.5)
    dab(icx, icy, 0.011 * W, (0.45, 0.0, 0.01), soft=1.2)
    dab(icx, icy, 0.004 * W, (0.03, 0.0, 0.0), soft=1.0)

    out = bpy.data.images.new("sukuna_tex", W, H, alpha=True)
    out.pixels.foreach_set(px.ravel())
    if out_png:
        out.filepath_raw = out_png; out.file_format = "PNG"; out.save()
    out.pack()
    for m in bpy.data.materials:
        if not m.node_tree: continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and n.image.name.lower().startswith("yuji"):
                n.image = out
    ev.to_mesh_clear()
    return el, er


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    S = bpy.context.scene
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=args[0])
    objs = [o for o in bpy.data.objects if o not in before]
    el, er = apply(objs, args[1])
    if len(args) > 2:
        cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); S.collection.objects.link(cam); S.camera = cam
        mid = (el + er) / 2
        loc = mid + Vector((0.12, -0.55, 0.02)); cam.location = loc; cam.data.lens = 50
        cam.rotation_euler = (mid - loc).to_track_quat("-Z", "Y").to_euler()
        for nm, l, r, e in (("k", (-1.5, -2, 2.6), (50, 0, -35), 400), ("f", (2, -2, 1.8), (65, 0, 45), 150)):
            ld = bpy.data.lights.new(nm, "AREA"); ld.energy = e; ld.size = 2
            ob = bpy.data.objects.new(nm, ld); S.collection.objects.link(ob); ob.location = l
            ob.rotation_euler = [math.radians(v) for v in r]
        w = bpy.data.worlds.new("w"); S.world = w; w.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.04, 1)
        S.render.engine = "CYCLES"; S.cycles.samples = 16; S.cycles.use_denoising = True
        S.view_settings.view_transform = "AgX"; S.render.resolution_x = S.render.resolution_y = 640
        S.render.filepath = args[2]; bpy.ops.render.render(write_still=True)
