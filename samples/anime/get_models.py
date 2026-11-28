"""Download the free (CC-BY-4.0) anime fan models used by the anime-vs-SCP Shorts.
They are Sketchfab exports kept in public GitHub repos; this fetches scene.gltf plus every
buffer and texture it points to.   python3 get_models.py ~/anime_models"""
import json, os, sys, urllib.request, urllib.parse
MODELS = {   # name: raw base URL   (credits: see CREDITS.md)
    "goku": "https://raw.githubusercontent.com/oscarburga/GLEngine/HEAD/Content/GLTF/goku_rigged__animated",
    "naruto": "https://raw.githubusercontent.com/gabriel654165/JapanFight/HEAD/Assets/Models3D/SketchFab/Naruto/source",
}
out = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/anime_models")
for name, base in MODELS.items():
    d = os.path.join(out, name); os.makedirs(d, exist_ok=True)
    def get(rel):
        dst = os.path.normpath(os.path.join(d, urllib.parse.unquote(rel)))
        assert dst.startswith(d + os.sep), rel          # never write outside the model folder
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            urllib.request.urlretrieve(base + "/" + urllib.parse.quote(urllib.parse.unquote(rel)), dst)
        return dst
    for f in ("license.txt",): get(f)
    g = json.load(open(get("scene.gltf")))
    for x in g.get("buffers", []) + g.get("images", []):
        if "uri" in x and not x["uri"].startswith("data:"): get(x["uri"])
    print(name, "ok", d)
