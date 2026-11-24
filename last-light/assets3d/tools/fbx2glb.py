"""Convert every .fbx under a folder to .glb (keeps materials, skins and animations). Usage: python fbx2glb.py <in_dir> <out_dir>"""
import bpy, sys, os, glob
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(os.path.join(src, '**', '*.fbx'), recursive=True)):
    out = os.path.join(dst, os.path.splitext(os.path.basename(f))[0].replace(' ', '_') + '.glb')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.fbx(filepath=f)
        for m in bpy.data.materials:  # FBX imports often carry alpha 0, which makes the glTF invisible
            if m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED': n.inputs['Alpha'].default_value = 1.0
            if hasattr(m, 'surface_render_method'): m.surface_render_method = 'DITHERED'
            m.diffuse_color[3] = 1.0
        bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_animations=True)
        print('ok', os.path.basename(out))
    except Exception as e:
        print('FAIL', f, e)
