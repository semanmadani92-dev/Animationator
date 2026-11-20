"""Copy each line's take into the episode audio folder, splicing 'keep' segments where the script asks.

Usage: python prepare_audio.py <script.json> <takes_dir> <out_dir>
Segments are joined with a short gap and 10 ms fades so the cuts don't click.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

GAP = 0.18


def splice(y, sr, keep):
    fade = int(0.01 * sr)
    parts = []
    for a, b in keep:
        seg = y[int(a * sr):int(b * sr)].copy()
        seg[:fade] *= np.linspace(0, 1, min(fade, seg.size))
        seg[-fade:] *= np.linspace(1, 0, min(fade, seg.size))
        parts += [seg, np.zeros(int(GAP * sr))]
    return np.concatenate(parts[:-1])


if __name__ == "__main__":
    script = json.load(open(sys.argv[1]))
    takes, out = Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    for line in script["lines"]:
        src = takes / f"{line['id']}.wav"
        if "keep" in line:
            y, sr = sf.read(src)
            sf.write(out / src.name, splice(y, sr, line["keep"]), sr)
            print(f"{line['id']}: spliced {len(line['keep'])} segments")
        elif src.resolve() != (out / src.name).resolve():
            shutil.copy(src, out / src.name)
    for sfx in takes.glob("sfx_*.wav"):
        if sfx.resolve() != (out / sfx.name).resolve():
            shutil.copy(sfx, out / sfx.name)
