import bpy, sys, os, glob
src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(os.path.join(src, '**', '*.obj'), recursive=True)):
    out = os.path.join(dst, os.path.splitext(os.path.basename(f))[0] + '.glb')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=f); bpy.ops.export_scene.gltf(filepath=out, export_format='GLB'); print('ok')
