"""Generate speech with Qwen3-TTS VoiceDesign on CPU.

Usage: python design_voice.py <text_file> <out_wav> "<voice description>"
"""
import os
import sys
import time

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

text_file, out_wav, instruct = sys.argv[1], sys.argv[2], sys.argv[3]
torch.set_num_threads(os.cpu_count() or 4)

t0 = time.perf_counter()
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cpu",
    dtype=torch.float32,
    attn_implementation="sdpa",
)
print(f"loaded in {time.perf_counter() - t0:.0f}s", flush=True)

text = open(text_file, encoding="utf-8").read().strip()
t1 = time.perf_counter()
wavs, sr = model.generate_voice_design(text=text, language="English", instruct=instruct)
elapsed = time.perf_counter() - t1
sf.write(out_wav, wavs[0], sr)
print(f"generated {len(wavs[0]) / sr:.1f}s of audio in {elapsed:.0f}s -> {out_wav}", flush=True)
