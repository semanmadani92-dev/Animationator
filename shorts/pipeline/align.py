"""Word timings for each voiced line: Whisper timestamps mapped onto the script's own words.

Usage: python align.py <script.json> <audio_dir> <out.json>
The displayed words always come from the script; Whisper only supplies timing.
Words Whisper missed are spread evenly between their matched neighbours.
"""
import difflib
import json
import re
import sys
from pathlib import Path

import librosa
from faster_whisper import WhisperModel


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align_line(model, wav, text):
    y, sr = librosa.load(wav, sr=16000)
    duration = len(y) / sr
    segs, _ = model.transcribe(y, word_timestamps=True)
    heard = [w for s in segs for w in s.words]
    words = text.split()
    times = [None] * len(words)
    sm = difflib.SequenceMatcher(a=[norm(w) for w in words], b=[norm(w.word) for w in heard], autojunk=False)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            h = heard[block.b + k]
            times[block.a + k] = (h.start, h.end)
    # fill gaps by interpolating between known neighbours
    known = [i for i, t in enumerate(times) if t]
    for i, t in enumerate(times):
        if t:
            continue
        prev = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        start = times[prev][1] if prev is not None else 0.0
        end = times[nxt][0] if nxt is not None else duration
        span = (nxt if nxt is not None else len(words)) - (prev if prev is not None else -1)
        pos = i - (prev if prev is not None else -1)
        a = start + (end - start) * (pos - 1) / span
        times[i] = (a, start + (end - start) * pos / span)
    return duration, [{"word": w, "start": round(s, 3), "end": round(e, 3)} for w, (s, e) in zip(words, times)], len(known)


if __name__ == "__main__":
    script = json.load(open(sys.argv[1]))
    audio_dir = Path(sys.argv[2])
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    out = {}
    for line in script["lines"]:
        if "text" not in line:
            continue
        dur, words, matched = align_line(model, audio_dir / f"{line['id']}.wav", line["text"])
        out[line["id"]] = {"duration": round(dur, 3), "words": words}
        print(f"{line['id']}: {matched}/{len(words)} words matched, {dur:.1f}s", flush=True)
    json.dump(out, open(sys.argv[3], "w"), indent=1)
