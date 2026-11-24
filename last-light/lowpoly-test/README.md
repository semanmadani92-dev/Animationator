# Low-poly 3D test (SCP-173)

A 16-second test of a low-poly 3D look for Last Light, built with three.js and rendered through the same
pipeline as the 2D episodes (`kit/shoot.js`; the HUD, captions and end card come from `kit/ll.js`).

- `s173/video.html`: the 3D scene. It's rendered at 360x640, upscaled with nearest-neighbour, plus ordered dither, vignette and grain.
- `build_audio.py`: narration (4 lines from the SCP-173 episode) and the sound design, using `kit/ll_audio.py`.

To render: put `ll.js`, `shoot.js` and `three.cjs` (three@0.170.0, wrapped in `(function(module, exports){ ... })(module, module.exports);`)
next to the episode folder, run `python build_audio.py <kit dir>`, then run `node shoot.js s173 out.mp4`.
