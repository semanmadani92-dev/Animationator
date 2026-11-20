"""Speak new text in the voice of a reference clip (Qwen3-TTS Base, CPU).

Usage: python clone_voice.py <ref_wav> <ref_text_file> <text_file> <out_wav>
Only use reference voices you made yourself or have permission to use.
"""
import os
import sys
import time

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

ref_wav, ref_text_file, text_file, out_wav = sys.argv[1:5]
torch.set_num_threads(os.cpu_count() or 4)

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cpu", dtype=torch.float32, attn_implementation="sdpa"
)
t = time.perf_counter()
wavs, sr = model.generate_voice_clone(
    text=open(text_file, encoding="utf-8").read().strip(),
    language="English",
    ref_audio=ref_wav,
    ref_text=open(ref_text_file, encoding="utf-8").read().strip(),
)
sf.write(out_wav, wavs[0], sr)
print(f"generated {len(wavs[0]) / sr:.1f}s of audio in {time.perf_counter() - t:.0f}s -> {out_wav}", flush=True)
