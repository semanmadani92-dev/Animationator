# Voices

Seven approved voices, made with Qwen3-TTS (free, Apache 2.0, runs on CPU). `voices.json` lists each one with the
description it was designed from and the exact words in its reference take.

| Voice | Sound |
|---|---|
| narrator | hyped 17-year-old boy, Shorts storytelling energy |
| mark | dry, deadpan teen |
| reginald | deep, booming, overdramatic man |
| vexmore | slow, sinister villain |
| bumblewick | wobbly, confused old man |
| grub | squeaky, panicky goblin |
| lastlight_whisper | hushed, breathy near-whisper (Last Light narrator) |

## Speak new lines in one of these voices

```bash
pip install qwen-tts soundfile torch
# jobs.json: [{"id": "line1", "ref_wav": "voices/narrator.wav", "ref_text": "<text from voices.json>", "text": "New line"}]
python voices/tools/clone_lines.py jobs.json out_dir/
```

Cloning from the reference take keeps the voice identical across lines and videos.

## Other tools

- `tools/design_voice.py`: make a brand-new voice from a text description (Qwen3-TTS VoiceDesign).
- `tools/clone_voice.py`: clone a single line.
- `tools/align.py`: word-level timestamps for captions (faster-whisper).
- `tools/prepare_audio.py`: splice out long pauses in a take.
