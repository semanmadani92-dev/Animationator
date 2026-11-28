"""Soundtrack for goku_vs_682.py (timings mirror it).   python3 goku_vs_682_sfx.py OUT.wav"""
import sys, numpy as np
import sfxlib as X
from sfxlib import sec

ROAR0, ROAR1, DROP, LAND, CHARGE, PUNCH, SLAM = 14, 62, 70, 90, 128, 164, 192
REGEN, RISE, ROAR2, SSJ0, SSJ = 206, 226, 250, 282, 312
KCHARGE, CHARGE2, FIRE, HIT, BURN, POWERDOWN, END = 334, 352, 376, 381, 44, 452, 600
X.init(sec(END + 1), seed=11)
t = X.t
X.ambience(0.12)
X.drone(0, sec(END), 36, 0.16)


def roar(t0, dur, f0=70, gain=1.0):
    e = X.env(t0, t0 + 0.12, t0 + dur - 0.4, t0 + dur)
    v = np.tanh(3 * (X.osc(f0 * (1 + 0.08 * np.sin(2 * np.pi * 5 * t)), "saw") + X.osc(f0 * 1.51, "saw") * 0.6)) + 1.2 * X.band(X.noise(), 100, 2500)
    X.add(X.stereo(X.sweep(v * e, 380, 900, q=3) + X.band(v * e, 40, 400) * 0.8, 1400), 0.5 * gain)
    X.add(X.band(X.noise(), 20, 90) * e, 0.6 * gain)


roar(sec(ROAR0), sec(ROAR1 - ROAR0) + 0.3)
# Goku drops: rising wind, then the landing impact
X.whoosh(sec(DROP), sec(LAND - DROP), 300, 3000, 0.5)
X.boom(sec(LAND), 90, 0.5, 1.0); X.rocks(sec(LAND) + 0.02, 18, 0.4, 0.4)
# 682 charges: heavy footfalls
for f in range(CHARGE + 3, PUNCH, 6):
    X.add(X.osc(45) * X.decay(sec(f), 0.1), 0.6); X.add(X.band(X.noise(), 60, 700) * X.decay(sec(f), 0.06), 0.5)
# the punch: crack + boom, 682 flies, slams down the hall
X.whoosh(sec(PUNCH - 6), 0.22, 600, 4000, 0.5)
X.hit(sec(PUNCH), 1.4); X.boom(sec(PUNCH), 120, 0.7, 1.1)
X.add(X.band(X.noise(), 3000, 12000) * X.decay(sec(PUNCH), 0.04, 0.001), 1.0)
X.whoosh(sec(PUNCH + 2), sec(SLAM - PUNCH), 2500, 300, 0.4)
X.boom(sec(SLAM), 60, 0.9, 1.0); X.rocks(sec(SLAM), 40, 0.8, 0.6)
# regeneration: wet crackling flesh, a hiss, then the bigger roar
reg = X.env(sec(REGEN), sec(REGEN) + 0.3, sec(RISE + 30) - 0.3, sec(RISE + 30))
X.add(X.stereo(X.crackle(220 * reg, 300, 3000)) * reg, 0.7)
X.add(X.band(X.noise(), 2500, 9000) * reg, 0.12)
X.add(X.stereo(X.band(X.osc(55 + 20 * np.sin(2 * np.pi * 0.7 * t), "saw"), 0, 300) * reg, 900), 0.2)
roar(sec(ROAR2), 1.6, 58, 1.3)
# Super Saiyan: rising rumble and scream-like tone, crackling energy, then the burst and the aura's roar
up = X.env(sec(SSJ0), sec(SSJ) - 0.05, sec(SSJ), sec(SSJ) + 0.02)
X.add(X.stereo(X.band(X.noise(), 25, 180)) * up, 0.8)
X.add(X.stereo(X.osc(110 * (1 + 2 * X.smooth((t - sec(SSJ0)) / sec(SSJ - SSJ0))), "saw") * up * 0.3, 1200), 0.12)
X.add(X.stereo(X.crackle(400 * up, 2000)), 0.5)
X.boom(sec(SSJ), 80, 1.2, 1.2)
X.add(X.stereo(X.band(X.noise(), 2000, 10000)) * X.decay(sec(SSJ), 0.5), 0.5)
aura = X.env(sec(SSJ), sec(SSJ) + 0.1, sec(POWERDOWN), sec(POWERDOWN) + 0.3)
X.add(X.stereo(X.sweep(X.noise(), 500 + 150 * np.sin(2 * np.pi * 3 * t), None, q=2)) * aura, 0.22)
X.add(X.stereo(X.crackle(30 * aura, 3000)) * aura, 0.5)
# Kamehameha: the charge whine, the blast, the beam's roar, the burn
ch = X.env(sec(KCHARGE), sec(FIRE) - 0.05, sec(FIRE), sec(FIRE) + 0.02)
whine = X.osc(300 * (1 + 3 * X.smooth((t - sec(KCHARGE)) / sec(FIRE - KCHARGE))))
X.add(X.stereo(whine * ch, 600), 0.1); X.add(X.stereo(X.crackle(120 * ch, 4000)), 0.4)
roar(sec(CHARGE2), sec(HIT - CHARGE2) + 0.1, 64, 0.9)
for f in range(CHARGE2 + 3, HIT, 6): X.add(X.osc(45) * X.decay(sec(f), 0.1), 0.6)
X.boom(sec(FIRE), 70, 1.4, 1.4)
beam = X.env(sec(FIRE), sec(FIRE) + 0.05, sec(418), sec(440))
X.add(X.stereo(X.band(X.noise(), 0, 1500)) * beam, 0.9)
X.add(X.stereo(X.sweep(X.noise(), 900 + 300 * np.sin(2 * np.pi * 4 * t), None, q=1.5)) * beam, 0.5)
X.boom(sec(HIT), 50, 1.6, 1.2)
burn = X.env(sec(HIT), sec(HIT) + 0.2, sec(HIT + BURN), sec(HIT + BURN) + 0.6)
X.add(X.stereo(X.crackle(700 * burn, 1000)) * burn, 0.8)
X.add(X.stereo(X.band(X.noise(), 3000, 11000)) * burn, 0.15)
tw = np.zeros(X.N)
for _ in range(60):
    t0 = X.rng.uniform(sec(HIT + 10), sec(470)); f = X.rng.uniform(2500, 6500)
    tw += np.sin(2 * np.pi * f * t) * X.decay(t0, X.rng.uniform(0.08, 0.3), 0.002) * X.rng.uniform(0.3, 1)
X.add(X.stereo(tw, 1200), 0.05)
# power down: a falling tone and the aura dying
X.add(X.stereo(X.osc(400 * np.exp(-np.maximum(t - sec(POWERDOWN), 0) * 3)) * X.env(sec(POWERDOWN), sec(POWERDOWN) + 0.05, sec(POWERDOWN) + 0.4, sec(POWERDOWN) + 0.8)), 0.08)
# wind, then the lump: a wet heartbeat getting stronger
X.add(X.stereo(X.sweep(X.noise(), 300 + 200 * np.sin(2 * np.pi * 0.3 * t), None, q=4), 4000) * X.env(sec(440), sec(480), sec(END) - 0.5, sec(END)), 0.2)
k = 0
for f in np.arange(520, END, 7.0):
    g = 0.3 + 0.7 * (f - 520) / (END - 520)
    for dt, a in ((0, 1), (0.13, 0.6)):
        X.add(X.osc(42) * X.decay(sec(f) + dt, 0.1, 0.005), 0.8 * g * a)
        X.add(X.crackle(400 * X.decay(sec(f) + dt, 0.05), 400, 3000), 0.25 * g * a)
X.save(sys.argv[1] if len(sys.argv) > 1 else "goku_vs_682.wav")
