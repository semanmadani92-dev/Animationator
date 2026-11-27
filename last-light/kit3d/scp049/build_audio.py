"""Narration + sound design for the 3D SCP-049 episode (new hook format). Usage (from the kit dir): python scp049/build_audio.py <ll kit dir>"""
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


def beep(m, a, b, rate, g=1.0):
    k = a
    while k < b:
        th = np.arange(int(.09 * SR)) / SR
        m.add(np.sin(2 * np.pi * 1000 * th) * np.minimum(1, (0.09 - th) / .02) * .07, k, g); k += rate


def flatline(m, a, dur, g=1.0):
    th = np.arange(int(dur * SR)) / SR
    m.add(np.sin(2 * np.pi * 1000 * th) * .05 * np.minimum(1, th / .02) * np.minimum(1, (dur - th) / .1), a, g)


def design(m, tl):
    L = tl["lines"]
    stop, bag, rise, dark, end = W(tl, "04", "stops"), W(tl, "05", "opens"), W(tl, "06", "get") - .2, W(tl, "07", "power"), L["08"]["end"]
    m.sting(0.05, 1.3); m.boom(0.05, 1.0)                     # the cold open hits immediately
    m.hum(m.mask(0, dark), 0.9); m.pad(0.8)
    beep(m, L["02"]["start"], stop, .8, 1.0); flatline(m, stop, rise - stop, 1.0)
    m.clunk(bag, .6)
    beep(m, rise, L["07"]["start"], .35, 1.0)                  # the heart comes back wrong
    m.scrape(rise, .8, .8); m.sting(rise + .1, .8)
    m.clunk(dark, 1.3); m.drone(dark, end, 1.0)
    m.steps(L["07"]["end"] - .5, end, .9, .25, .97, .8)        # slow, formal footsteps getting closer
    m.heartbeat(L["03"]["start"], end, 1.0, .9)
    for a, b, g, sh in [("06", "07", 1.0, .8), ("07", "08", 1.2, 1.0)]:
        gap = L[b]["start"] - L[a]["end"]
        if gap > .3: breath(m, L[a]["end"] + .05, min(.7, gap - .1), g, sh)
    m.sting(end - 1.1, 1.2); m.boom(end + .1, 1.2)            # its hand: back to the start


ids = [f"{i:02d}" for i in range(1, 9)]
gaps = dict(zip(ids, [1.1, 0.45, 0.4, 0.45, 0.45, 0.45, 0.6, 0.5]))
build("scp049", gaps, ["Based on SCP-049 by Gabriel Jade", "rewritten by djkaktus & Gabriel Jade", "scp-wiki.wikidot.com/scp-049  ·  CC BY-SA 3.0"], design, tail=2.6, card_pad=1.3)
