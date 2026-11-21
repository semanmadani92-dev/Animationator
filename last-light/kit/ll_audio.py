"""Last Light audio kit: pick takes, time words, lay out a timeline, and synthesise the sound design.

An episode script calls build(ep_dir, gaps, credit, design) where design(mix, T) adds its sound effects.
Takes are <ep_dir>/<id>_w<n>.wav; writes <ep_dir>/tl.json and <ep_dir>/audio.wav.
"""
import difflib
import glob
import json
import os
import re

import librosa
import numpy as np
import soundfile as sf

SR = 24000
REF = "/home/user/Animationator/voices/lastlight_whisper.wav"
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())  # noqa: E731
_models = {}


def _whisper():
    if "w" not in _models:
        from faster_whisper import WhisperModel
        _models["w"] = WhisperModel("small.en", compute_type="int8")
    return _models["w"]


def pick(ep_dir, line):
    """Best take of a line (word match), with the script's words timed against what was heard."""
    best = None
    for f in sorted(glob.glob(f"{ep_dir}/{line['id']}_w*.wav")):
        y, _ = librosa.load(f, sr=16000)
        segs, _ = _whisper().transcribe(y, word_timestamps=True)
        heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
        sw = line["text"].split()
        match = difflib.SequenceMatcher(None, [norm(w) for w in sw], [norm(w[0]) for w in heard]).ratio()
        print(f"  {os.path.basename(f)} match={match:.2f} | {' '.join(w[0] for w in heard)}")
        if not best or match > best[0]:
            best = (match, f, heard, len(y) / 16000)
    match, f, heard, dur = best
    sw = line["text"].split()
    sm = difflib.SequenceMatcher(None, [norm(w) for w in sw], [norm(w[0]) for w in heard])
    times = [None] * len(sw)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            times[a + k] = (heard[b + k][1], heard[b + k][2])
    for i in range(len(sw)):
        if times[i] is None:
            prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
            nxt = next((times[j][0] for j in range(i + 1, len(sw)) if times[j]), dur)
            times[i] = (prev, prev + (nxt - prev) * 0.5)
    return f, match, [[w, a, b] for w, (a, b) in zip(sw, times)]


class Mix:
    def __init__(self, end):
        self.n = int(end * SR)
        self.t = np.arange(self.n) / SR
        self.y = np.zeros(self.n)
        self.rng = np.random.default_rng(5)

    def add(self, y, at, g=1.0):
        s = int(at * SR)
        if 0 <= s < self.n:
            self.y[s:s + y.size] += (y * g)[: self.n - s]

    def mask(self, a, b):
        return (self.t >= a) & (self.t < b)

    # ---- sound palette
    def hum(self, on, g=1.0):
        tt = self.t
        h = (np.sin(2 * np.pi * 60 * tt) * .6 + np.sin(2 * np.pi * 120 * tt) * .3 + np.sin(2 * np.pi * 180 * tt) * .15)
        self.y += h * 0.018 * g * on * (1 + .15 * np.sin(2 * np.pi * .7 * tt))

    def pad(self, g=1.0):
        tt = self.t
        self.y += sum(np.sin(2 * np.pi * f * tt + p) for f, p in ((55, 0), (82.4, 1), (110, 2), (130.8, 3))) * 0.01 * g * \
            (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * tt))

    def drone(self, a, b, g=1.0):
        m = self.mask(a, b)
        td = self.t - a
        self.y += (np.sin(2 * np.pi * 41 * td) + 0.5 * np.sin(2 * np.pi * 61.5 * td)) * 0.04 * g * np.clip(td / 1.5, 0, 1) * m

    def noise(self, n, smooth):
        return np.convolve(self.rng.standard_normal(n), np.ones(smooth) / smooth, "same")

    def clunk(self, at, g=1.0):
        tc = np.arange(int(0.9 * SR)) / SR
        body = np.sin(2 * np.pi * (55 * np.exp(-tc * 3) + 30) * tc) * np.exp(-tc * 7)
        self.add(np.tanh((body + self.noise(tc.size, 8) * np.exp(-tc * 30) * 2) * 2) * 0.8, at, g)

    def scrape(self, at, dur=0.9, g=1.0):
        tc = np.arange(int(dur * SR)) / SR
        grit = self.noise(tc.size, 3) * (0.6 + 0.4 * np.sin(2 * np.pi * 23 * tc))
        env = np.minimum(1, tc / 0.05) * np.minimum(1, (dur - tc) / 0.2)
        self.add(np.tanh(grit * 2) * env * 0.35, at, g)

    def crack(self, at, g=1.0):
        tc = np.arange(int(0.3 * SR)) / SR
        self.add(np.tanh(self.noise(tc.size, 2) * np.exp(-tc * 60) * 6) * 0.8, at, g)

    def boom(self, at, g=1.0):
        tc = np.arange(int(1.4 * SR)) / SR
        self.add(np.sin(2 * np.pi * (45 * np.exp(-tc * 1.5)) * tc) * np.exp(-tc * 2.5) * 0.6, at, g)

    def flicker(self, at, dur=0.9, g=1.0):
        tc = np.arange(int(dur * SR)) / SR
        buzz = np.sign(np.sin(2 * np.pi * 120 * tc)) * (np.sin(2 * np.pi * 9 * tc) > 0.3)
        self.add(buzz * 0.08 * np.exp(-tc * 1.5), at, g)

    def heartbeat(self, a, b, start_rate=1.0, g=1.0):
        k, rate = a, start_rate
        while k < b:
            for off, amp in ((0, 1), (0.17, 0.7)):
                th = np.arange(int(0.15 * SR)) / SR
                self.add(np.sin(2 * np.pi * 48 * th) * np.exp(-th * 30) * 0.45 * amp, k + off, g)
            k += rate
            rate = max(0.45, rate * 0.9)

    def steps(self, a, b, step=0.55, amp=0.25, accel=0.93, g=1.0):
        k = a
        while k < b:
            th = np.arange(int(0.25 * SR)) / SR
            self.add(np.sin(2 * np.pi * 70 * th) * np.exp(-th * 25) * amp + self.noise(th.size, 30) * np.exp(-th * 30) * amp * 2, k, g)
            k += step
            step, amp = max(0.22, step * accel), min(0.8, amp * 1.05)

    def scream(self, at, dur=2.0, g=1.0, far=False):
        """A distant, inhuman wail: detuned rising tones through a formant-ish band, with noise."""
        tc = np.arange(int(dur * SR)) / SR
        f = 420 + 380 * np.sin(np.pi * tc / dur) + 30 * np.sin(2 * np.pi * 7 * tc)
        ph = 2 * np.pi * np.cumsum(f) / SR
        v = np.sin(ph) + .6 * np.sin(ph * 1.5 + 1) + .4 * np.sin(ph * 2.02)
        v = v * (1 + .5 * self.noise(tc.size, 2))
        env = np.minimum(1, tc / 0.15) * np.minimum(1, (dur - tc) / 0.4)
        y = np.tanh(v * 0.8) * env * 0.35
        if far:
            y = np.convolve(y, np.ones(18) / 18, "same") * 0.6
        self.add(y, at, g)

    def cry(self, at, dur=2.5, g=1.0):
        """Faint, far-off sobbing echo (pitched, wavering, heavily filtered)."""
        tc = np.arange(int(dur * SR)) / SR
        f = 520 + 90 * np.sin(2 * np.pi * 1.3 * tc) + 40 * np.sin(2 * np.pi * 5 * tc)
        v = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.2 * tc) ** 2)
        v = np.convolve(v, np.ones(24) / 24, "same")
        echo = np.zeros_like(v)
        d = int(0.31 * SR)
        echo[d:] = v[:-d] * 0.5
        self.add((v + echo) * 0.12 * np.minimum(1, tc / 0.4) * np.minimum(1, (dur - tc) / 0.6), at, g)

    def sting(self, at, g=1.0):
        tc = np.arange(int(1.6 * SR)) / SR
        cl = sum(np.sin(2 * np.pi * f * tc) for f in (233, 247, 262, 466)) / 4
        self.add(np.tanh(cl * 2) * np.exp(-tc * 1.8) * 0.5 + self.noise(tc.size, 4) * np.exp(-tc * 8) * 0.3, at, g)

    def wind(self, a, b, g=1.0):
        self.y += self.noise(self.n, 200) * 0.5 * g * self.mask(a, b)


def build(ep_dir, gaps, credit, design, tail=3.2, card_pad=0.8, channel="LAST LIGHT"):
    script = json.load(open(f"{ep_dir}/script.json"))
    lines, audio, t = {}, {}, 0.0
    for line in script:
        f, match, words = pick(ep_dir, line)
        y, _ = librosa.load(f, sr=SR)
        t += gaps.get(line["id"], 0.4)
        lines[line["id"]] = {"start": t, "end": t + len(y) / SR, "words": [[w, t + a, t + b] for w, a, b in words],
                             "take": os.path.basename(f), "match": round(match, 2)}
        audio[line["id"]] = y
        t += len(y) / SR
    last = script[-1]["id"]
    card = lines[last]["end"] + card_pad
    tl = {"lines": lines, "end": card + tail, "channel": channel, "credit": credit, "cardAt": card}
    mix = Mix(tl["end"])
    for i, y in audio.items():
        y = y * (0.11 / np.sqrt(np.mean(y ** 2)))
        mix.add(y / max(1, np.abs(y).max() / 0.95), lines[i]["start"])
    design(mix, tl)
    mix.boom(card, 0.9)
    mix.y /= max(1, np.abs(mix.y).max() / 0.97)
    sf.write(f"{ep_dir}/audio.wav", mix.y.astype(np.float32), SR)
    json.dump(tl, open(f"{ep_dir}/tl.json", "w"))
    print(f"{ep_dir}: {tl['end']:.1f}s", {k: (round(v['start'], 1), v['match']) for k, v in lines.items()})
    return tl


def W(tl, i, word):
    return next((w[1] for w in tl["lines"][i]["words"] if word in w[0].lower()), tl["lines"][i]["end"])
