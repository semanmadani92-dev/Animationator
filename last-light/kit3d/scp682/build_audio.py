"""Narration + sound design for the 3D SCP-682 episode. Usage (from the kit dir): python scp682/build_audio.py <ll kit dir>"""
import sys
sys.path.insert(0, sys.argv[1])
import numpy as np
from ll_audio import W, build

SR = 24000


def breath(m, at, dur, g, shaky):
    n = int(dur * SR); t = np.arange(n) / SR
    y = m.noise(n, 3) - m.noise(n, 40)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * (1 - shaky * .6 * (np.sin(2 * np.pi * 11 * t) > .3))
    m.add(y * env * .09 * g, at)


def bubbling(m, a, b, g):
    k = a; rng = np.random.default_rng(3)
    while k < b:
        th = np.arange(int(.08 * SR)) / SR; f = 300 + rng.random() * 500
        m.add(np.sin(2 * np.pi * f * th * (1 + th * 8)) * np.exp(-th * 60) * .12, k, g)
        k += .04 + rng.random() * .14
    m.y += m.noise(m.n, 60) * .25 * g * m.mask(a, b)


def gurgle(m, a, b, g):
    t = m.t - a; mk = m.mask(a, b)
    m.y += np.tanh(m.noise(m.n, 120) * 6) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.3 * t)) * .06 * g * mk * np.clip(1 - t / max(.1, b - a), 0, 1)


def growl(m, a, dur, g):
    """A low, wet rumble with a ragged tremble."""
    n = int(dur * SR); t = np.arange(n) / SR
    f = 52 + 8 * np.sin(2 * np.pi * .7 * t)
    y = np.tanh((np.sin(2 * np.pi * np.cumsum(f) / SR) + .6 * m.noise(n, 25) * 8) * 1.5) * (0.6 + 0.4 * np.sin(2 * np.pi * 13 * t))
    env = np.minimum(1, t / .3) * np.minimum(1, (dur - t) / .4)
    m.add(y * env * .22 * g, a)


def siren(m, a, b, g=1.0):
    t = m.t - a; mk = m.mask(a, b)
    f = 620 + 260 * (np.sin(2 * np.pi * 0.55 * t) > 0)
    m.y += np.tanh(np.sin(2 * np.pi * np.cumsum(f * mk) / SR) * 2) * .035 * g * mk * np.clip(t / .3, 0, 1)


def design(m, tl):
    L = tl["lines"]
    drain0, enter, closer = L["05"]["start"], W(tl, "05", "job") - .6, L["08"]["start"] + .2
    eye, word, alarm, end = W(tl, "09", "opens") - .1, W(tl, "10", "disgusting"), W(tl, "11", "alarms"), L["12"]["end"]
    m.hum(m.mask(0, alarm), 0.9); m.pad(0.8)
    bubbling(m, 0, drain0 + 2.0, 0.8)
    gurgle(m, drain0, enter + 1.5, 1.0)
    m.clunk(enter, 1.0); m.steps(enter + .2, enter + 3.2, .55, .2, 1.0, .7)
    for a in np.arange(L["06"]["start"], eye, 3.0): breath(m, a, 1.4, .5, 0)          # its slow breathing
    growl(m, L["07"]["start"] + .3, 1.6, .5)                                                  # the whisper nobody can hear
    m.steps(closer, closer + 1.4, .5, .15, 1.0, .6)
    m.sting(eye, 1.1); m.heartbeat(eye, end, .75, 1.0)
    growl(m, word - .2, 2.4, 1.2)
    siren(m, alarm, end + .2, 1.0); m.steps(alarm + .2, alarm + 2.0, .26, .5, 1.0, .8)
    growl(m, alarm + .4, 3.0, 1.4); m.drone(alarm, end, 1.0)
    for a, b, g, sh in [("08", "09", .8, .5), ("09", "10", 1.0, .8), ("10", "11", 1.1, 1.0), ("11", "12", 1.2, 1.0)]:
        gap = L[b]["start"] - L[a]["end"]
        if gap > .3: breath(m, L[a]["end"] + .05, min(.7, gap - .1), g, sh)
    m.scream(end - .35, 1.6, 1.3)   # the roar
    m.boom(end - .3, 1.3); m.crack(end - .05, 1.3)


ids = [f"{i:02d}" for i in range(1, 13)]
gaps = dict(zip(ids, [0.3, 0.6, 0.45, 0.45, 0.6, 0.6, 0.6, 0.6, 0.7, 0.8, 0.6, 0.6]))
build("scp682", gaps, ["Based on SCP-682 by Dr Gears and Epic Phail Spy", "scp-wiki.wikidot.com/scp-682", "Licensed CC BY-SA 3.0"], design)
