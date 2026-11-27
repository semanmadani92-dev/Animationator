# Start here (new chat)

Everything for the Last Light 3D episodes is in this folder and `../assets3d`.

## What's here
- **Narrator:** D-class prisoner D-4172 tells each SCP story in first person, scared whisper voice.
- **Episodes:** `scp173`, `scp096`, `scp087`, `scp682` (the lizard), `scp049` (the newest, in the new hook format).
  Each has `index.html` (scene), `script.json` (lines), `jobs.json` (voice jobs), `takes/` (every voice take),
  `tl.json` (word timings), `build_audio.py` (mix), `audio.wav` (final mix) and the finished mp4.
- **Voice references:** `scp173/voice_refs/` (`nervous_*.wav`, `terrified_*.wav`, made with Qwen3-TTS VoiceDesign; not anyone's real voice).
  Jobs pick a tier per line: nervous for calm lines, terrified for scary ones.
- **Characters and props:** `../assets3d` (all CC0: Quaternius, Kenney).

## Setup in a fresh container
```
cd last-light/kit3d
bash setup.sh          # three.js, links, ffmpeg
bash setup.sh voice    # also Qwen3-TTS + faster-whisper (only to record new lines)
```

## Making an episode
1. `script.json`: about 8 lines, about 40 s.
2. `jobs.json` → `python ../../voices/tools/clone_lines.py <ep>/jobs.json <ep>/takes` (2 takes per line, CPU, slow).
3. Pick the best take per line (whisper check for mispronounced words), then `python fake_tl.py` / timings → `tl.json`.
4. Copy `scp049/index.html` as a template; build the set; check with `node shoot3d.js <ep> stills:1,5,10`.
5. `python <ep>/build_audio.py ../kit` → `audio.wav`.
6. `node shoot3d.js <ep> <ep>_raw.mp4`, then `ffmpeg -i <ep>_raw.mp4 -c:v libx264 -crf 25 -preset slow -c:a aac <ep>_3d_dclass.mp4`.

## Hook format (use for every new episode)
- Cold open on the scariest frame, with a sting.
- First line states the danger in 6 words or fewer.
- About 40 s total.
- The end loops back to the opening shot.

## Rules
- Credit the SCP authors in the end card and the description: "Based on SCP-XXX by <author>", link, CC BY-SA 3.0.
- Don't use the original SCP-173 image. Don't clone real people's voices.
- Low-poly look: render at 450×800, nearest-neighbour upscale, dither, grain (see `makeRetro` in `kit3d.js`).
- The user has ADHD: keep answers short and skimmable.
