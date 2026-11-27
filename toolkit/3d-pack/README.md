# Last Light 3D asset library

Every asset here is **CC0 (public domain)**. They're free to use in monetised videos, and no credit is required. Sources are listed below.

| Folder | What | Source |
|---|---|---|
| `animation/UAL1_mannequin_46anims.glb` | Faceless mannequin + 46 animations (walk, jog, sprint, crouch, idle with torch, death, hit, push, sit, interact, pistol, punch, roll, swim...) | Quaternius, Universal Animation Library (opengameart.org/content/universal-animation-library) |
| `animation/UAL2_mannequin_43anims.glb` | Same rig + 43 more (zombie walk/idle/scratch, phone call, lantern idle, knockback, climb, carry, lay-to-idle, folded arms...) | Quaternius, Universal Animation Library 2 |
| `animation/Mannequin_F.glb` | Female mannequin on the same rig | Quaternius, UAL 2 |
| `props/scifi_megakit/` | Facility walls (incl. padded walls), platforms, columns, doors, lights, vents, rails, crates, terminals; textured glTF | Quaternius, Modular Sci-Fi MegaKit |
| `props/scifi_modular/` | Simpler modular sci-fi corridors, doors, staircase, props | Quaternius, Ultimate Modular Sci-Fi |
| `props/house_interior/` | 123 house furniture/props (beds, tables, kitchens, bathrooms, lamps, TVs...) | Quaternius, Ultimate House Interior |
| `props/kenney_furniture/` | 120 furniture pieces | Kenney, Furniture Kit |
| `props/kenney_graveyard/` | Graves, fences, crypts, trees, lanterns | Kenney, Graveyard Kit |
| `props/kenney_modular_buildings/`, `kenney_industrial/`, `kenney_retro_urban/` | Building/street/industrial pieces | Kenney |
| `props/monsters/` | Skeleton, slime, bat, dragon (animated) | Quaternius, Animated Monster Pack |

The chibi Quaternius "Ultimate Animated Character Pack" (52 characters: doctors, soldiers, workers, zombies) was also downloaded and converted. It isn't stored here because the cute proportions clash with the horror tone. The mannequins can be recoloured instead, e.g. an orange jumpsuit for D-class or a white coat for researchers.

`previews/` holds contact sheets of each pack, plus `mannequin_animations.png` (walk, sprint, idle torch, crouch, death, hit).

## Tools
- `tools/fbx2glb.py`, `tools/obj2glb.py`: batch-convert FBX/OBJ to GLB with Blender as a Python module (`pip install bpy==5.3.0`, Python 3.13). This fixes the alpha-0 materials that FBX imports produce.
- `tools/thumbs.html` + `thumbs.js` + `sheet.py`: render a labelled contact sheet of a folder of models (serve the folder with `python -m http.server 8765`).
- `tools/animtest.html`: load the mannequin and pose it from several clips with `AnimationMixer.setTime` (deterministic per frame, as the video renderer needs).

Also installed for the renderer (npm): `three@0.170.0`, `@mesmotronic/three-retropass` (pixelate/dither pass), `playshader-one` (PS1-style shader), `@gltf-transform/cli` (optimise/merge glTF), `fbx2gltf`.
