"""Synthesised soundtrack for gojo_vs_049.py (adapted from hollow_purple_sfx.py): 049's footsteps,
the Infinity hum while its hand is frozen, the repel boom and landing, then the orb
hums, the spiral and merge, the purple drone, the launch boom, beam roar, impact explosion,
the sizzle and ember crackle of the vaporise, and the wind after.

    python gojo_vs_049_sfx.py OUT.wav
    ffmpeg -i video.mp4 -i OUT.wav -c:v copy -c:a aac -b:a 192k -shortest out.mp4
"""
import sys, wave
import numpy as np

SR, FPS, END = 48000, 30, 292                       # frame timings mirror gojo_vs_049.py
WALK_END, REACH, PUSH, REPEL, FLY_END = 64, 50, 66, 100, 116
T_BLUE, T_RED, T_SPIRAL, T_MERGE = 120, 134, 152, 178
SHOOT, LAUNCH, HIT = 194, 197, 207
CUT1, CUT2 = HIT + 3, 260                            # camera cuts
sec = lambda f: f / FPS
DUR = sec(END + 1)
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def env(a, b, c=1e9, d=1e9):
    return np.minimum(smooth((t - a) / max(b - a, 1e-6)), 1 - smooth((t - c) / max(d - c, 1e-6)))


def decay(t0, tau, attack=0.004):
    x = t - t0
    return np.where(x < 0, 0, np.exp(-np.maximum(x, 0) / tau) * smooth(x / attack))


def osc(freq, shape="sin"):
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, t.shape)) / SR
    if shape == "sin": return np.sin(ph)
    if shape == "saw": return 2 * ((ph / (2 * np.pi)) % 1) - 1
    raise ValueError(shape)


def band(x, lo, hi):
    """zero-phase band-pass with soft edges (FFT)"""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo > 0: m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def sweep(x, f0, f1, q=2.0):
    """band-pass whose centre glides from f0 to f1 (arrays allowed): state-variable filter"""
    fc = np.broadcast_to(np.asarray(f0 if f1 is None else np.geomspace(f0, f1, len(x))), x.shape)
    g = 2 * np.sin(np.pi * np.minimum(fc, SR / 6) / SR); damp = 1 / q
    lp = bp = 0.0; out = np.empty_like(x)
    for i in range(len(x)):
        hp = x[i] - lp - damp * bp
        bp += g[i] * hp; lp += g[i] * bp
        out[i] = bp
    return out


def noise(): return rng.standard_normal(N)


def crackle(rate, lo=2000, hi=None):
    """sparse random clicks (rate: clicks per second, array allowed)"""
    p = np.broadcast_to(rate, t.shape) / SR
    clicks = (rng.random(N) < p) * rng.uniform(0.3, 1, N) * rng.choice([-1, 1], N)
    return band(clicks, lo, hi)


def pan(x, p):
    """p in -1 (left) .. 1 (right), constant power"""
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


L = np.zeros((2, N))

def add(x, gain=1.0, p=0.0):
    global L
    L += gain * (pan(x, p) if x.ndim == 1 else x)


# ------------------------------------------------------------------ ambience
add(band(noise(), 40, 260) * 0.5, 0.15)

# ------------------------------------------------------------------ blue orb (screen left)
s_spiral = smooth((t - sec(T_SPIRAL)) / sec(T_MERGE - T_SPIRAL))       # 0..1 through the spiral
rise = 1 + 0.7 * s_spiral ** 1.5
angle = s_spiral * 4.5 * np.pi
on_b = env(sec(T_BLUE), sec(T_BLUE) + 0.12, sec(T_MERGE) - 0.05, sec(T_MERGE) + 0.05)
bell = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((880, 1), (1318, 0.6), (1760 * 1.004, 0.4), (2637, 0.25)))
add(bell * decay(sec(T_BLUE), 0.9), 0.3, -0.45)
hum_b = (osc(440 * rise) + osc(441.8 * rise) * 0.8 + osc(220 * rise) * 0.7) * (0.75 + 0.25 * np.sin(2 * np.pi * 6 * t))
add(pan(hum_b * on_b, np.where(t < sec(T_SPIRAL), -0.45, -0.45 * np.cos(angle))), 0.14)
add(crackle(60 * on_b, 4000) * on_b, 0.5, -0.4)

# ------------------------------------------------------------------ red orb (screen right)
on_r = env(sec(T_RED), sec(T_RED) + 0.1, sec(T_MERGE) - 0.05, sec(T_MERGE) + 0.05)
add(band(noise(), 60, 600) * decay(sec(T_RED), 0.35, 0.03), 0.8, 0.45)         # whump
growl = np.tanh(2.5 * (osc(110 * rise, "saw") + osc(165.5 * rise, "saw") * 0.6)) * (0.7 + 0.3 * np.sin(2 * np.pi * 9 * t))
add(pan(band(growl, 0, 1400) * on_r, np.where(t < sec(T_SPIRAL), 0.45, 0.45 * np.cos(angle))), 0.15)
add(crackle(40 * on_r, 1500, 6000) * on_r, 0.5, 0.4)

# ------------------------------------------------------------------ spiral whoosh into the merge
wh = sweep(noise(), 250, 4500, q=3) * env(sec(T_SPIRAL), sec(T_MERGE) - 0.1, sec(T_MERGE), sec(T_MERGE) + 0.15)
add(pan(wh, 0.3 * np.sin(angle)), 0.35)

# ------------------------------------------------------------------ merge
tm = sec(T_MERGE)
add(osc(np.maximum(38, 95 * np.exp(-np.maximum(t - tm, 0) * 4))) * decay(tm, 0.45), 0.9)
add(band(noise(), 2000, 9000) * decay(tm, 0.5), 0.35)
add(sum(np.sin(2 * np.pi * f * t) for f in (587, 740, 880, 1175)) * decay(tm, 1.4, 0.05), 0.05)

# ------------------------------------------------------------------ purple drone (swells to the shot)
on_p = env(tm, tm + 0.25, sec(LAUNCH) - 0.03, sec(LAUNCH))
swell = 0.5 + 0.5 * smooth((t - tm) / (sec(SHOOT) - tm))
drone = np.stack([sum(osc(f * k, "saw") for f, k in ((55, 1), (82.5, 1.002), (110, 0.998), (165, 1.003))),
                  sum(osc(f * k, "saw") for f, k in ((55, 1.003), (82.5, 0.997), (110, 1.002), (165, 0.999)))])
for ch in range(2): drone[ch] = band(np.tanh(drone[ch] * 0.8), 30, 900)
add(drone * on_p * swell, 0.12)
add(crackle(80 + 400 * smooth((t - tm) / 0.7), 2500) * on_p, 0.55)
# inhale before the shot: rising air that stops dead at the launch
add(band(noise(), 800, 6000) * env(sec(SHOOT) - 0.15, sec(LAUNCH)) * (t < sec(LAUNCH)), 0.25)

# ------------------------------------------------------------------ launch boom + beam roar
tl = sec(LAUNCH)
add(osc(np.maximum(30, 90 * np.exp(-np.maximum(t - tl, 0) * 3))) * decay(tl, 0.9), 1.1)
add(band(noise(), 0, 900) * decay(tl, 0.35), 0.8)
fly = env(tl, tl + 0.04, sec(HIT), sec(HIT) + 0.25)
roar = sweep(noise(), 1800, 400, q=1.2) * fly
add(pan(roar, np.clip(0.6 - 1.2 * (t - tl) / (sec(HIT) - tl), -0.6, 0.6)), 0.8)
add(band(noise(), 0, 300) * fly, 0.6)


# ------------------------------------------------------------------ SCP-049: footsteps, Infinity, repel
for k in range(0, WALK_END, 16):                                      # slow, formal steps on concrete
    t0 = sec(k + 6)
    add(band(noise(), 80, 1800) * decay(t0, 0.05, 0.002), 0.5 + 0.4 * k / WALK_END, -0.1)
    add(osc(70) * decay(t0, 0.06), 0.25)
on_i = env(sec(REACH + 8), sec(PUSH), sec(REPEL), sec(REPEL) + 0.05)   # Infinity: a glassy, unstable hum
glass = sum(np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * 0.7 * t * j)) * a
            for j, (f, a) in enumerate(((1567, 1), (2349, 0.6), (3135, 0.35), (783, 0.5)), 1))
add(np.stack([glass, np.roll(glass, 700)]) * on_i * (0.6 + 0.4 * np.sin(2 * np.pi * 5.5 * t)), 0.05)
add(band(noise(), 30, 120) * on_i, 0.35)                                 # pressure rumble
add(crackle(25 * on_i, 3000) * on_i, 0.25, 0.1)
tr = sec(REPEL)                                                          # repel: a deep boom + air burst
add(osc(np.maximum(32, 120 * np.exp(-np.maximum(t - tr, 0) * 5))) * decay(tr, 0.6), 1.0)
add(band(noise(), 200, 7000) * decay(tr, 0.25, 0.002), 0.7)
add(sweep(noise(), 2500, 300, q=1.5) * env(tr, tr + 0.03, sec(FLY_END) - 0.1, sec(FLY_END)), 0.5)
tf = sec(FLY_END)                                                         # 049 hits the floor
add(band(noise(), 40, 900) * decay(tf, 0.18, 0.003), 0.9)
add(osc(55) * decay(tf, 0.2), 0.5)

# ------------------------------------------------------------------ impact
th = sec(HIT)
add(band(noise(), 0, 12000) * decay(th, 0.18, 0.002), 1.2)
add(band(noise(), 0, 500) * decay(th, 1.6, 0.01), 1.1)
add(osc(np.maximum(28, 70 * np.exp(-np.maximum(t - th, 0) * 1.5))) * decay(th, 1.5, 0.005), 1.1)
add(np.stack([crackle(900 * decay(th, 0.5), 800), crackle(900 * decay(th, 0.5), 800)]), 0.8)

# ------------------------------------------------------------------ vaporise: sizzle, crackle, ember twinkles
tb0, tb1 = sec(CUT1), sec(HIT + 3 + 26)                                 # burn start / end
burn = env(tb0 - 0.05, tb0 + 0.15, tb1 - 0.1, tb1 + 0.6)
siz = band(noise(), 3000, 12000) * (0.6 + 0.4 * np.abs(band(noise(), 2, 30)) * 8)
add(np.stack([siz * burn, np.roll(siz, 900) * burn]), 0.18)
add(np.stack([crackle(500 * burn, 1200), crackle(500 * burn, 1200)]) * burn, 0.9)
add(band(noise(), 150, 900) * burn, 0.18)                               # the body "burning" whoosh
tw = np.zeros(N)
for _ in range(70):                                                     # embers ringing as they drift off
    t0 = rng.uniform(tb0 + 0.2, sec(CUT2) + 0.6); f = rng.uniform(2500, 6500)
    tw += np.sin(2 * np.pi * f * t) * decay(t0, rng.uniform(0.08, 0.3), 0.002) * rng.uniform(0.3, 1)
add(np.stack([tw * rng.uniform(0.4, 1), np.roll(tw, 1200)]), 0.05)

# ------------------------------------------------------------------ aftermath wind
wind = sweep(noise(), 300 + 200 * np.sin(2 * np.pi * 0.3 * t), None, q=4)
add(np.stack([wind, np.roll(wind, 4000)]) * env(tb1 - 0.4, tb1 + 0.8, DUR - 0.6, DUR), 0.2)

# ------------------------------------------------------------------ reverb, master
def ir(seed, length=1.6):
    r = np.random.default_rng(seed); n = int(length * SR); x = np.arange(n) / SR
    return r.standard_normal(n) * np.exp(-x / 0.45) * 0.03

wet = np.stack([np.fft.irfft(np.fft.rfft(L[c], 2 * N) * np.fft.rfft(ir(c + 1), 2 * N), 2 * N)[:N] for c in range(2)])
mix = L + 0.35 * wet
mix *= 1 - smooth((t - (DUR - 0.5)) / 0.5)
mix = np.tanh(1.3 * mix / np.max(np.abs(mix))) / np.tanh(1.3) * 0.94
out = sys.argv[1] if len(sys.argv) > 1 else "gojo_vs_049_sfx.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix.T * 32767).astype("<i2").tobytes())
print("wrote", out, f"{DUR:.2f}s")
