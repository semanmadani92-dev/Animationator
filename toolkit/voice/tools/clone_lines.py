"""Speak several lines, each in the voice of a reference take (Qwen3-TTS Base, one model load).

Usage: python clone_lines.py <jobs.json> <out_dir>
jobs.json: [{"id": "...", "ref_wav": "...", "ref_text": "...", "text": "..."}, ...]
Only use reference voices made in this project or used with permission.
"""
import json
import os
import sys
import time

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

jobs = json.load(open(sys.argv[1]))
out_dir = sys.argv[2]
torch.set_num_threads(os.cpu_count() or 4)
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32, attn_implementation="sdpa"
)
for job in jobs:
    t = time.perf_counter()
    wavs, sr = model.generate_voice_clone(
        text=job["text"], language="English", ref_audio=job["ref_wav"], ref_text=job["ref_text"]
    )
    sf.write(os.path.join(out_dir, f"{job['id']}.wav"), wavs[0], sr)
    print(f"{job['id']}: {len(wavs[0]) / sr:.1f}s in {time.perf_counter() - t:.0f}s", flush=True)
