"""Pick the best take of each line, time every word, lay out the timeline and mix the soundtrack.

Usage: python build_audio.py <take_suffix e.g. w> <reference.wav> <channel name>
Reads script.json and <id>_<suffix><n>.wav; writes pick.json, tl.json and ep_audio.wav.
"""
import difflib
import json
import re
import sys

import librosa
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from resemblyzer import VoiceEncoder, preprocess_wav

SUF, REF, CHANNEL = sys.argv[1], sys.argv[2], sys.argv[3]
SR = 24000
m = WhisperModel("small.en", compute_type="int8")
enc = VoiceEncoder()
ref = enc.embed_utterance(preprocess_wav(REF))
script = json.load(open("script.json"))
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())  # noqa: E731

pick = {}
for line in script:
    best = None
    for n in (1, 2):
        f = f"{line['id']}_{SUF}{n}.wav"
        y, _ = librosa.load(f, sr=16000)
        segs, _ = m.transcribe(y, word_timestamps=True)
        heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
        sw = line["text"].split()
        match = difflib.SequenceMatcher(None, [norm(w) for w in sw], [norm(w[0]) for w in heard]).ratio()
        sim = float(np.dot(ref, enc.embed_utterance(preprocess_wav(f))))
        score = match * 2 + sim
        print(f"{line['id']} take {n}: match={match:.2f} sim={sim:.2f} | {' '.join(w[0] for w in heard)}")
        if not best or score > best[0]:
            best = (score, n, heard, len(y) / 16000)
    sw, heard = line["text"].split(), best[2]
    sm = difflib.SequenceMatcher(None, [norm(w) for w in sw], [norm(w[0]) for w in heard])
    times = [None] * len(sw)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            times[a + k] = (heard[b + k][1], heard[b + k][2])
    for i in range(len(sw)):
        if times[i] is None:
            prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
            nxt = next((times[j][0] for j in range(i + 1, len(sw)) if times[j]), best[3])
            times[i] = (prev, prev + (nxt - prev) * 0.5)
    pick[line["id"]] = {"take": best[1], "dur": best[3], "words": [[w, a, b] for w, (a, b) in zip(sw, times)]}
json.dump(pick, open("pick.json", "w"), indent=0)

# ---- timeline
gap_before = {"01": 0.3, "02": 1.1, "03": 0.35, "04": 0.45, "05": 0.45, "06": 0.3, "07": 0.5, "08": 0.5, "09": 0.8,
              "10": 0.5, "11": 1.2, "12": 0.5}
t, lines, audio = 0.0, {}, {}
for i in sorted(pick):
    y, _ = librosa.load(f"{i}_{SUF}{pick[i]['take']}.wav", sr=SR)
    t += gap_before[i]
    d = len(y) / SR
    lines[i] = {"start": t, "end": t + d, "words": [[w, t + a, t + b] for w, a, b in pick[i]["words"]]}
    audio[i] = y
    t += d
END = lines["12"]["end"] + 0.8 + 3.2
json.dump({"lines": lines, "end": END, "channel": CHANNEL}, open("tl.json", "w"))


def W(i, word):
    return next(w[1] for w in lines[i]["words"] if word in w[0].lower())


out1, out7, back = W("01", "out"), W("07", "out"), W("11", "back")
n = int(END * SR)
tt = np.arange(n) / SR
mix = np.zeros(n)
rng = np.random.default_rng(5)


def add(y, at, g=1.0):
    s = int(at * SR)
    if 0 <= s < n:
        mix[s:s + y.size] += (y * g)[: n - s]


for i, y in audio.items():  # a whisper is quiet: normalise it up so it sits on top of the ambience
    y = y * (0.11 / np.sqrt(np.mean(y ** 2)))
    add(y / max(1, np.abs(y).max() / 0.95), lines[i]["start"])
hum = (np.sin(2 * np.pi * 60 * tt) * .6 + np.sin(2 * np.pi * 120 * tt) * .3 + np.sin(2 * np.pi * 180 * tt) * .15) * .018
on = ((tt < out1 + 0.3) | ((tt >= W("02", "inside")) & (tt < out7 + 0.3)) | (tt >= back)) & \
    ~((tt >= lines["09"]["start"] - 0.8) & (tt < back))
mix += hum * on * (1 + .15 * np.sin(2 * np.pi * .7 * tt))
outside = (tt >= lines["02"]["start"] - 0.5) & (tt < W("02", "inside"))
mix += np.convolve(rng.standard_normal(n), np.ones(200) / 200, "same") * 0.5 * outside
mix += sum(np.sin(2 * np.pi * f * tt + p) for f, p in ((55, 0), (82.4, 1), (110, 2), (130.8, 3))) * 0.01 * \
    (0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * tt))


def clunk(g=1.0):
    tc = np.arange(int(0.9 * SR)) / SR
    body = np.sin(2 * np.pi * (55 * np.exp(-tc * 3) + 30) * tc) * np.exp(-tc * 7)
    click = np.convolve(rng.standard_normal(tc.size), np.ones(8) / 8, "same") * np.exp(-tc * 30) * 2
    return np.tanh((body + click) * 2) * 0.8 * g


add(clunk(), out1)
add(clunk(1.1), out7)
dark = (tt >= out7) & (tt < back)
td = tt - out7
mix += (np.sin(2 * np.pi * 41 * td) + 0.5 * np.sin(2 * np.pi * 61.5 * td)) * 0.04 * np.clip(td / 1.5, 0, 1) * dark
k, step, amp = lines["10"]["start"] - 0.3, 0.55, 0.25
while k < back - 0.2:  # footsteps, closer and faster
    th = np.arange(int(0.25 * SR)) / SR
    add(np.sin(2 * np.pi * 70 * th) * np.exp(-th * 25) * amp +
        np.convolve(rng.standard_normal(th.size), np.ones(30) / 30, "same") * np.exp(-th * 30) * amp * 2, k)
    k += step
    step, amp = max(0.38, step * 0.93), min(0.8, amp * 1.18)
k, rate = lines["09"]["start"], 1.0
while k < back:  # heartbeat speeding up
    for off, a in ((0, 1), (0.17, 0.7)):
        th = np.arange(int(0.15 * SR)) / SR
        add(np.sin(2 * np.pi * 48 * th) * np.exp(-th * 30) * 0.45 * a, k + off)
    k += rate
    rate = max(0.45, rate * 0.9)
tc = np.arange(int(1.2 * SR)) / SR
add(np.tanh(np.sin(2 * np.pi * (90 * np.exp(-tc * 4) + 40) * tc) * np.exp(-tc * 5) * 2) * 0.7, back)
add(np.sin(2 * np.pi * (45 * np.exp(-tc * 1.5)) * tc) * np.exp(-tc * 2.5) * 0.6, lines["12"]["end"] + 0.8)
mix /= max(1, np.abs(mix).max() / 0.97)
sf.write("ep_audio.wav", mix.astype(np.float32), SR)
print(f"END {END:.1f}s", {k: round(v["start"], 2) for k, v in lines.items()})
