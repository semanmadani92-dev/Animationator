"""Synthesised sound effects (numpy, 24 kHz mono). Usage: python sfx.py <out_dir>"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
rng = np.random.default_rng(7)


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _lowpass(x, n):
    return np.convolve(x, np.ones(n) / n, "same")


def whoosh(sec=0.55):
    n = rng.standard_normal(int(sec * SR))
    return (n - _lowpass(n, 30)) * np.hanning(n.size) * 0.22


def skid(sec=0.45):
    x = _lowpass(rng.uniform(-1, 1, int(sec * SR)), 6)
    return x * np.linspace(0.3, 0, x.size)


def chop():
    t = _t(0.25)
    thock = np.sin(2 * np.pi * (170 - 60 * t / 0.25) * t) * np.exp(-t * 28)
    click = _lowpass(rng.standard_normal(t.size), 3) * np.exp(-t * 90)
    return (thock * 0.8 + click * 0.5) * 0.9


def creak(sec=1.1):
    t = _t(sec)
    f = 95 + 25 * np.sin(2 * np.pi * 1.7 * t) + 10 * rng.standard_normal(t.size).cumsum() / np.sqrt(t.size)
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = 2 * (ph / (2 * np.pi) % 1) - 1
    grit = (rng.uniform(0, 1, t.size) < 0.03) * rng.uniform(-1, 1, t.size)  # crackles
    env = np.minimum(1, t / 0.1) * np.minimum(1, (sec - t) / 0.2)
    return _lowpass(saw * 0.35 + grit * 0.6, 8) * env * 0.7


def thud(sec=0.7):
    t = _t(sec)
    boom = np.sin(2 * np.pi * (70 * np.exp(-t * 3)) * t) * np.exp(-t * 6)
    rumble = _lowpass(rng.standard_normal(t.size), 40) * np.exp(-t * 5) * 3
    return np.tanh((boom + rumble) * 1.5) * 0.9


def clank():
    t = _t(0.35)
    partials = [(520, 9), (1170, 12), (1630, 15), (2310, 18), (3020, 22)]
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in partials) / len(partials)
    return x * 0.8


def magic(sec=1.0):
    t = _t(sec)
    out = np.zeros(t.size)
    for i, f in enumerate((1047, 1319, 1568, 2093, 2637)):
        s = int(i * 0.09 * SR)
        tt = t[: t.size - s]
        out[s:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 5) * 0.25
    sparkle = (rng.uniform(0, 1, t.size) < 0.004) * rng.uniform(-1, 1, t.size)
    shimmer = np.sin(2 * np.pi * 3136 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * t)) * np.exp(-t * 3) * 0.08
    return out + _lowpass(sparkle, 2) * 0.5 + shimmer


def pop():
    t = _t(0.1)
    return np.sin(2 * np.pi * (700 + 2500 * t) * t) * np.exp(-t * 40) * 0.6


def boing():
    t = _t(0.45)
    return np.sin(2 * np.pi * (180 + 90 * np.sin(2 * np.pi * 12 * t) * np.exp(-t * 4)) * t) * np.exp(-t * 7) * 0.7


EFFECTS = dict(whoosh=whoosh, skid=skid, chop=chop, creak=creak, thud=thud, clank=clank, magic=magic, pop=pop,
               boing=boing)

if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in EFFECTS.items():
        sf.write(out / f"sfx_{name}.wav", fn().astype(np.float32), SR)
    print("wrote", ", ".join(EFFECTS))
