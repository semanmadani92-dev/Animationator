"""Soundtrack for sukuna_vs_173.py (timings mirror it).   python3 sukuna_vs_173_sfx.py OUT.wav"""
import sys, numpy as np
import sfxlib as X
from sfxlib import sec

BLINKS = [(22, 5), (168, 4), (206, 4), (240, 5), (272, 5), (302, 10), (560, 6)]
WALK0, WALK1, REVEAL, FALL, LAUGH, TURN, LEAVE, END = 80, 140, 312, 340, 350, 392, 404, 590
X.init(sec(END + 1))
t = X.t


def light(f):
    for b, n in BLINKS:
        if b <= f < b + n: return 0.0
        if b - 4 <= f < b: return (0.55, 0.1, 0.7, 0.2)[f - b + 4]
        if b + n <= f < b + n + 3: return (0.3, 0.85, 0.6)[f - b - n]
    return 0.0 if f >= END - 4 else 1.0


lf = np.interp(t, np.arange(END + 1) / 30, [light(f) for f in range(END + 1)])
X.ambience(0.12)
X.drone(0, sec(END), 38, 0.2)
# fluorescent hum that dies with the lights; a relay clunk at each blackout and each return
hum = sum(X.osc(f) * a for f, a in ((120, 1), (240, 0.5), (360, 0.3), (1800, 0.05)))
X.add(X.stereo(hum * lf), 0.035)
for b, n in BLINKS:
    for tt, g in ((sec(b), 0.9), (sec(b + n), 0.6)):
        X.add(X.band(X.noise(), 60, 1500) * X.decay(tt, 0.05, 0.002), g * 0.5)
        X.add(X.osc(55) * X.decay(tt, 0.08), g * 0.4)
    if b < 560:   # the statue moving in the dark: concrete dragging on concrete
        e = X.env(sec(b), sec(b) + 0.03, sec(b + n) - 0.03, sec(b + n))
        grind = X.band(X.noise(), 250, 2600) * (0.6 + 0.4 * np.abs(X.band(X.noise(), 3, 25)) * 6)
        X.add(grind * e, 0.9, 0.1)
# the D-class: fast breathing, then the snap and the fall
for k in range(4):
    X.add(X.band(X.noise(), 400, 2500) * X.env(0.05 + k * 0.18, 0.1 + k * 0.18, 0.13 + k * 0.18, 0.2 + k * 0.18), 0.25)
ts = sec(26)
X.add(X.band(X.noise(), 1500, 9000) * X.decay(ts, 0.012, 0.0005), 1.3)
X.add(X.band(X.noise(), 200, 2500) * X.decay(ts + 0.01, 0.06, 0.001), 0.8)
X.add(X.osc(np.maximum(40, 160 * np.exp(-np.maximum(t - ts, 0) * 25))) * X.decay(ts, 0.08), 0.6)
X.hit(sec(60), 1.0); X.add(X.band(X.noise(), 100, 1200) * X.decay(sec(63), 0.15), 0.4)
# Sukuna's footsteps, in and out
for f in list(range(WALK0 + 6, WALK1, 16)) + list(range(LEAVE + 6, 480, 16)):
    X.step(sec(f), 0.45 if f < WALK1 else 0.4 * (1 - (f - LEAVE) / 120))
# a heartbeat that speeds up through the blink game
beat, f = [], sec(150)
while f < sec(302):
    beat.append(f); f += 0.75 - 0.4 * (f - sec(150)) / (sec(302) - sec(150))
for b0 in beat:
    for dt, g in ((0, 1), (0.14, 0.6)): X.add(X.osc(46) * X.decay(b0 + dt, 0.09, 0.005), 0.6 * g)
X.add(X.stereo(X.band(X.noise(), 2000, 8000)) * X.env(sec(150), sec(300), sec(301), sec(302)) * 0.3, 0.12)   # rising hiss
# Dismantle in the dark: three cuts
for f, p in ((304, -0.3), (306.5, 0.3), (309, 0.0)): X.slash(sec(f), 1.0, p)
# lights back: a deep sting, the cuts sizzling; then the stone gives way
X.boom(sec(REVEAL), 70, 1.2, 0.9)
X.add(X.stereo(X.band(X.noise(), 3000, 10000)) * X.env(sec(REVEAL), sec(REVEAL) + 0.1, sec(FALL) - 0.2, sec(FALL) + 0.2), 0.12)
X.add(X.band(X.noise(), 200, 3000) * X.decay(sec(FALL) - 0.1, 0.3, 0.02), 0.6)       # crack
X.rocks(sec(FALL + 8), 45, 1.0, 0.7)
X.add(X.band(X.noise(), 60, 600) * X.decay(sec(FALL + 10), 0.6, 0.02), 0.5)          # dust rumble
# Sukuna laughs: a low, breathy "ha-ha-ha" made from pulsed formants
for k in range(6):
    t0 = sec(LAUGH + 6) + k * 0.21 + (0.4 if k > 2 else 0)
    e = X.env(t0, t0 + 0.02, t0 + 0.09, t0 + 0.16)
    v = X.band(X.osc(105 * (1 - 0.03 * k), "saw") + 0.5 * X.noise(), 0, 3000)
    X.add(X.sweep(v * e, 750, None, q=5) * 0.8 + X.band(v * e, 250, 600) * 0.4, 0.5, 0.05)
# the ending: the lights die once more... and the pieces are gone
tl = sec(BLINKS[-1][0] + BLINKS[-1][1])
X.add(X.stereo(X.band(X.noise(), 2000, 9000) * X.env(tl - 0.8, tl - 0.05, tl - 0.05, tl)), 0.3)   # inhale into the cut
X.boom(tl + 0.02, 55, 1.4, 0.8)
X.add(X.stereo(sum(np.sin(2 * np.pi * f * t) for f in (311, 466, 622, 740)) * X.decay(tl, 1.8, 0.02)), 0.05)
X.save(sys.argv[1] if len(sys.argv) > 1 else "sukuna_vs_173.wav")
