# Last Light episode kit

- `ll.js`: shared drawing kit (lamps, cells, the silhouette, type, captions, end card with licence credit).
- `ll_audio.py`: picks the best voice take per line, times words, and synthesises the sound design (hum, scrapes, screams, steps...).
- `episodes.py`: each episode's pacing, credit and sound design. `python episodes.py scp173` writes `scp173/tl.json` and `scp173/audio.wav`.
- `shoot.js`: renders an episode: `node shoot.js scp173 out.mp4`.
- `<episode>/video.html`: that episode's scenes; `<episode>/script.json`: its narration.

Narration: voices/lastlight_whisper.wav cloned with voices/tools/clone_lines.py (one job per line, ids like `scp173/01_w1`).
