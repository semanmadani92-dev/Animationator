# Toolkit

Voice AI, Blender and the free 3D pack. Nothing project-specific.

## Install (new chat)
```
bash toolkit/setup.sh all
```

## Voice AI (`voice/`)
Qwen3-TTS: free, runs on CPU.
- **Make a new voice from a description:** `python voice/tools/design_voice.py text.txt out.wav "raspy old pirate, slow"`
- **Say new lines in a saved voice:** `python voice/tools/clone_lines.py jobs.json out_dir/`
  (jobs.json: `[{"id":"l1","ref_wav":"voice/narrator.wav","ref_text":"<its words from voices.json>","text":"New line"}]`)
- **Word timings for captions:** `python voice/tools/align.py script.json audio_dir/ out.json`
- **Saved voices:** narrator, mark, reginald, vexmore, bumblewick, grub, lastlight_whisper (see `voices.json`).
- **Rule:** don't clone real people's voices.

## Blender (`blender/`)
Blender as a Python module (no window).
- `fbx2glb.py in_dir out_dir`: convert FBX models to GLB.
- `obj2glb.py in_dir out_dir`: convert OBJ models to GLB.
- Any other Blender job: write a script with `import bpy` and run it with `~/blendervenv/bin/python`.

## 3D pack (`3d-pack/`)
All CC0 (free for monetised videos, no credit needed). See `3d-pack/README.md`.
- 2 mannequins with about 88 animations (walk, run, crouch, fight, die, zombie...).
- Sci-fi rooms, a house interior, furniture, a graveyard, buildings, industrial pieces, a street, monsters.
- Pictures of everything are in `3d-pack/previews/`.
