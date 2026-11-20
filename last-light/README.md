# Last Light

Minimal cinematic horror / "what if" Shorts. Dark scenes, lamp light, thin type, film grain; the narrator voice
from `voices/` (narrator). Signature moment: the lights going out.

- `channel/`: profile picture (800x800), banner (2560x1440, `banner_guide.png` shows the safe areas), `brand.html` source.
- `ep01_scp3008/`: "SCP-3008": `script.json` (lines), `tl.json` (timeline with word timings), `video.html` (all scenes,
  `draw(t)`), `shoot.js` (renders frames with Playwright into ffmpeg: `node shoot.js tl.json out.mp4`).

SCP content is CC BY-SA 3.0: every video credits the original article and author in the end card and description.
