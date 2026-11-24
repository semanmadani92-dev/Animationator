# Last Light 3D kit

The low-poly 3D renderer for Last Light episodes.

- `kit3d.js`
  - `loadMannequins()`: both Quaternius animation libraries (~88 clips) on one Unreal-named rig.
  - `makeHuman(lib, {number, skin, suit, cap})`: a D-class with an orange jumpsuit, skin-coloured head and hands, boots, a face stuck onto the head by raycasting, a buzz cut and a chest number patch.
  - `pose(h, segs, t)`: deterministic clip playback with crossfades, for frame-by-frame rendering.
  - `makeRetro()`: low-res render, nearest-neighbour upscale, ordered dither, vignette and grain, plus a red "burn".
- `shoot3d.js <scene dir> <out.mp4 | stills:t1,t2>`: serves the kit over a local http server, then renders `draw(t)` frames to ffmpeg, muxing `audio.wav` and reading `tl.json` when present.
- `close.js <scene dir> t1,t2`: head close-up stills, for checking faces.

Expected layout next to these files: `three.module.js` and `jsm/` (three@0.170.0), `ll.js` (from `../kit`), and `assets` -> `../assets3d`.

Scenes:
- `dclass/`: character look and movement test.
- `scp173/`: SCP-173, told in first person by D-4172.
