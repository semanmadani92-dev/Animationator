"""Generate a short original chiptune loop (square-wave lead and bass, noise hats) with numpy."""
import numpy as np

SR = 24000


def _note_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _square(freq, dur, duty=0.5, vol=1.0):
    t = np.arange(int(SR * dur)) / SR
    wave = np.where((t * freq) % 1.0 < duty, 1.0, -1.0) * vol
    env = np.minimum(1.0, np.linspace(1.2, 0.0, wave.size) + 0.3)  # quick decay, keeps a tail
    return wave * env


def _noise(dur, vol):
    rng = np.random.default_rng(1)
    n = rng.uniform(-1, 1, int(SR * dur)) * vol
    return n * np.linspace(1, 0, n.size) ** 3


def chiptune(seconds, bpm=132):
    beat = 60.0 / bpm
    eighth = beat / 2
    # a cheeky adventure-ish progression (MIDI note numbers), one bar per chord
    chords = [(57, 60, 64), (53, 57, 60), (55, 59, 62), (52, 56, 59)]  # Am F G E
    melody = [72, 76, 74, 72, 71, 72, 74, 76,  69, 72, 71, 69, 67, 69, 71, 72,
              71, 74, 72, 71, 69, 71, 72, 74,  76, 75, 76, 71, 68, 71, 76, 0]
    total = int(SR * seconds)
    out = np.zeros(total + SR)
    pos, step = 0.0, 0
    while pos < seconds:
        bar = (step // 8) % len(chords)
        chord = chords[bar]
        i = int(pos * SR)
        # bass on every beat, arpeggio on eighths, melody on eighths
        if step % 2 == 0:
            b = _square(_note_hz(chord[0] - 12), beat * 0.9, 0.5, 0.35)
            out[i:i + b.size] += b
        arp = _square(_note_hz(chord[step % 3] + 12), eighth * 0.6, 0.25, 0.12)
        out[i:i + arp.size] += arp
        m = melody[step % len(melody)]
        if m:
            lead = _square(_note_hz(m), eighth * 0.85, 0.125, 0.22)
            out[i:i + lead.size] += lead
        if step % 2 == 1:
            h = _noise(0.04, 0.12)
            out[i:i + h.size] += h
        pos += eighth
        step += 1
    out = out[:total]
    return out / (np.abs(out).max() + 1e-9)
