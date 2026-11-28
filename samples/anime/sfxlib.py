"""Tiny numpy synth kit shared by the anime-vs-SCP soundtracks (same tools as ../jjk/gojo_vs_049_sfx.py).

    import sfxlib as X
    X.init(duration_s)        # sets X.t, X.N, the stereo bus
    X.add(X.band(X.noise(), 80, 900) * X.decay(1.2, 0.2), gain, pan)
    X.save("out.wav")         # reverb, fade, soft limit
"""
import wave
import numpy as np

SR, FPS = 48000, 30
t = N = BUS = None
rng = np.random.default_rng(7)
sec = lambda f: f / FPS


def init(dur, seed=7):
    global t, N, BUS, rng
    N = int(dur * SR); t = np.arange(N) / SR; BUS = np.zeros((2, N)); rng = np.random.default_rng(seed)


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
    if shape == "sq": return np.sign(np.sin(ph))
    raise ValueError(shape)


def band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo > 0: m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def sweep(x, f0, f1, q=2.0):
    """band-pass whose centre glides f0 -> f1 (or follows an array f0 when f1 is None)"""
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
    p = np.broadcast_to(rate, t.shape) / SR
    clicks = (rng.random(N) < p) * rng.uniform(0.3, 1, N) * rng.choice([-1, 1], N)
    return band(clicks, lo, hi)


def pan(x, p):
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def add(x, gain=1.0, p=0.0):
    global BUS
    BUS += gain * (pan(x, p) if x.ndim == 1 else x)


def stereo(x, delay=900):
    return np.stack([x, np.roll(x, delay)])


# ---------------------------------------------------------------- ready-made sounds
def boom(t0, f0=110, tau=0.6, gain=1.0):
    add(osc(np.maximum(28, f0 * np.exp(-np.maximum(t - t0, 0) * 4))) * decay(t0, tau), gain)
    add(band(noise(), 0, 900) * decay(t0, tau * 0.5), gain * 0.6)


def hit(t0, gain=1.0, p=0.0):
    """a body blow: low thump + short crack"""
    add(osc(np.maximum(40, 120 * np.exp(-np.maximum(t - t0, 0) * 18))) * decay(t0, 0.12), gain, p)
    add(band(noise(), 300, 4000) * decay(t0, 0.03, 0.001), gain * 0.7, p)


def whoosh(t0, dur, f0=400, f1=2500, gain=0.5, p=0.0):
    e = env(t0, t0 + dur * 0.5, t0 + dur * 0.5, t0 + dur)
    add(sweep(noise(), f0, f1, q=1.5) * e, gain, p)


def step(t0, gain=0.4, p=0.0, hard=False):
    add(band(noise(), 80, 2500 if hard else 1500) * decay(t0, 0.04, 0.002), gain, p)
    add(osc(70) * decay(t0, 0.05), gain * 0.4, p)


def slash(t0, gain=0.8, p=0.0):
    """a blade cut: a fast whoosh into a bright metallic ring"""
    whoosh(t0 - 0.08, 0.12, 1500, 7000, gain * 0.7, p)
    ring = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((2900, 1), (4350, 0.6), (6100, 0.4), (7900, 0.25)))
    add(ring * decay(t0, 0.35, 0.001), gain * 0.25, p)
    add(band(noise(), 3000, 12000) * decay(t0, 0.05, 0.001), gain * 0.6, p)


def rocks(t0, n=40, spread=0.8, gain=0.6):
    """stone pieces hitting a concrete floor"""
    for _ in range(n):
        tt = t0 + rng.uniform(0, spread) ** 1.4; g = rng.uniform(0.2, 1)
        add(band(noise(), rng.uniform(150, 600), rng.uniform(2000, 6000)) * decay(tt, rng.uniform(0.02, 0.08), 0.001), gain * g, rng.uniform(-0.6, 0.6))
        add(osc(rng.uniform(60, 140)) * decay(tt, 0.06), gain * g * 0.5)


def drone(a, b, f=40, gain=0.25):
    e = env(a, a + 0.8, b - 0.8, b)
    add(stereo(band(osc(f * (1 + 0.01 * np.sin(2 * np.pi * 0.13 * t)), "saw") + osc(f * 1.5 * 1.003, "saw") * 0.5, 0, 260) * e, 1700), gain)


def ambience(gain=0.15):
    add(band(noise(), 40, 260) * 0.5, gain)


def save(path, fade=0.5, wet=0.35):
    def ir(seed, length=1.6):
        r = np.random.default_rng(seed); n = int(length * SR); x = np.arange(n) / SR
        return r.standard_normal(n) * np.exp(-x / 0.45) * 0.03
    rv = np.stack([np.fft.irfft(np.fft.rfft(BUS[c], 2 * N) * np.fft.rfft(ir(c + 1), 2 * N), 2 * N)[:N] for c in range(2)])
    mix = BUS + wet * rv
    mix *= 1 - smooth((t - (t[-1] - fade)) / fade)
    mix = np.tanh(1.3 * mix / np.max(np.abs(mix))) / np.tanh(1.3) * 0.94
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())
    print("wrote", path, f"{N / SR:.2f}s")
