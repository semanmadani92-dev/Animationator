"""Soundtrack for naruto_vs_096.py (timings mirror it).   python3 naruto_vs_096_sfx.py OUT.wav"""
import sys, numpy as np
import sfxlib as X
from sfxlib import sec

JOG1, TURN0, TURN1, SCREAM0, SCREAM1, SIGN, POOF, SPRINT = 80, 86, 112, 120, 186, 166, 178, 186
CLASH, RASEN0, JUMP, APEX, HIT, LANDN, GETUP, RISEN, END = (204, 208, 212, 216), 192, 218, 238, 264, 282, 486, 540, 586
X.init(sec(END + 1), seed=5)
t = X.t
X.ambience(0.12)
X.drone(0, sec(END), 41, 0.15)
for f in range(4, JOG1, 9): X.step(sec(f), 0.3, 0.0)                     # Naruto jogging in
# 096 turning: a wet creak, then a heartbeat stop... and the face
X.add(X.band(X.noise(), 300, 2500) * X.env(sec(TURN0), sec(TURN0) + 0.3, sec(TURN1) - 0.2, sec(TURN1)) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t)), 0.25)
X.add(X.stereo(sum(np.sin(2 * np.pi * f * t) for f in (220, 233, 311, 466))) * X.env(sec(TURN0), sec(TURN1), sec(TURN1) + 0.1, sec(SCREAM0)), 0.05)
X.boom(sec(TURN1), 60, 0.8, 0.6)


def scream(t0, dur, gain=1.0):
    """096's shriek: a high, wavering, distorted voice over noise"""
    e = X.env(t0, t0 + 0.25, t0 + dur - 0.3, t0 + dur)
    f = 620 * (1 + 0.04 * np.sin(2 * np.pi * 6.5 * t) + 0.25 * X.smooth((t - t0) / dur))
    v = np.tanh(4 * (X.osc(f, "saw") + 0.7 * X.osc(f * 1.49, "saw") + 0.5 * X.osc(f * 0.5, "saw"))) + 1.5 * X.band(X.noise(), 1500, 7000)
    X.add(X.stereo(X.sweep(v * e, 1800, None, q=2) + X.band(v * e, 300, 5000) * 0.5, 700), 0.35 * gain)


scream(sec(SCREAM0), sec(SCREAM1 - SCREAM0) + 0.2)
scream(sec(SPRINT + 4), sec(HIT - SPRINT - 4), 0.55)
# Naruto's hand sign and the poof of the clones
X.add(X.band(X.noise(), 1500, 6000) * X.decay(sec(SIGN), 0.05, 0.002), 0.5)
for k in range(4):
    tt = sec(POOF) + k * 0.03
    X.add(X.band(X.noise(), 200, 4000) * X.decay(tt, 0.18, 0.003), 0.6, (-0.6, 0.6, -0.2, 0.2)[k])
    X.add(X.osc(np.maximum(60, 300 * np.exp(-np.maximum(t - tt, 0) * 20))) * X.decay(tt, 0.1), 0.3)
# 096 sprinting: fast, heavy footfalls; the clones' feet
for f in range(SPRINT + 2, JUMP + 14, 4): X.step(sec(f), 0.45, 0.0, hard=True)
for f in range(POOF + 6, CLASH[-1], 5): X.step(sec(f), 0.25, X.rng.uniform(-0.5, 0.5))
# each clone torn apart: a hit, then the poof
for k, f in enumerate(CLASH):
    X.whoosh(sec(f) - 0.12, 0.14, 800, 4000, 0.4, (-0.5, 0.5, -0.2, 0.2)[k])
    X.hit(sec(f), 1.0, (-0.5, 0.5, -0.2, 0.2)[k])
    X.add(X.band(X.noise(), 300, 4000) * X.decay(sec(f) + 0.02, 0.15, 0.003), 0.5, (-0.5, 0.5, -0.2, 0.2)[k])
# the Rasengan: a rising, whirring spin
rs = X.env(sec(RASEN0), sec(RASEN0) + 0.4, sec(HIT), sec(HIT) + 0.02)
spin = X.sweep(X.noise(), 1200 + 600 * np.sin(2 * np.pi * 14 * t), None, q=4) * (1 + 0.5 * X.smooth((t - sec(RASEN0)) / sec(HIT - RASEN0)))
X.add(X.stereo(spin * rs, 400), 0.45)
X.add(X.stereo(X.osc(220 * (1 + 1.5 * X.smooth((t - sec(RASEN0)) / sec(HIT - RASEN0)))) * rs, 800), 0.06)
X.whoosh(sec(JUMP), 0.5, 300, 2500, 0.5)
X.whoosh(sec(APEX), sec(HIT - APEX), 400, 5000, 0.6)
# impact: the slam into the floor
X.boom(sec(HIT), 70, 1.5, 1.5)
X.add(X.stereo(X.band(X.noise(), 0, 9000)) * X.decay(sec(HIT), 0.4, 0.002), 0.9)
X.add(X.stereo(X.sweep(X.noise(), 3000, 300, q=2)) * X.env(sec(HIT), sec(HIT) + 0.05, sec(HIT) + 0.6, sec(HIT) + 1.2), 0.5)
X.rocks(sec(HIT) + 0.05, 50, 1.0, 0.6)
X.step(sec(LANDN), 0.8, 0.0, hard=True); X.add(X.osc(60) * X.decay(sec(LANDN), 0.15), 0.5)
# calm: wind and settling dust
X.add(X.stereo(X.sweep(X.noise(), 300 + 200 * np.sin(2 * np.pi * 0.3 * t), None, q=4), 4000) * X.env(sec(LANDN + 10), sec(LANDN + 50), sec(GETUP), sec(RISEN)), 0.18)
# 096 getting up behind him: bones creaking, quiet breathing... then the scream starts and cuts
X.add(X.stereo(X.crackle(60 * X.env(sec(GETUP), sec(GETUP) + 0.3, sec(RISEN), sec(RISEN) + 0.2), 800, 5000)), 0.6)
for k in range(5):
    t0 = sec(GETUP + 20) + k * 0.9
    X.add(X.band(X.noise(), 300, 1800) * X.env(t0, t0 + 0.3, t0 + 0.4, t0 + 0.8), 0.2)
X.add(X.stereo(X.band(X.noise(), 2000, 9000)) * X.env(sec(END - 40), sec(END - 26)), 0.25)
scream(sec(END - 26), sec(26) + 0.3, 1.2)
X.save(sys.argv[1] if len(sys.argv) > 1 else "naruto_vs_096.wav", fade=0.05)
