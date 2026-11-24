"""Narration + sound design for the 3D SCP-173 episode. Usage: python build_audio.py <ll kit dir> (run from the scene dir's parent)."""
import sys
sys.path.insert(0, sys.argv[1])
import numpy as np
from ll_audio import W, build


def breath(m, at, dur, g, shaky):
    """A shaky inhale: band-limited noise with a stuttering envelope."""
    n = int(dur * 24000); t = np.arange(n) / 24000
    y = m.noise(n, 3) - m.noise(n, 40)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5 * (1 - shaky * .6 * (np.sin(2 * np.pi * 11 * t) > .3))
    m.add(y * env * .09 * g, at)


def design(m, tl):
    L = tl["lines"]
    for i, (a, b, g, sh) in enumerate([("06", "07", .5, .2), ("07", "08", .7, .4), ("08", "09", .8, .5), ("09", "10", .9, .6), ("10", "11", 1.0, .8), ("11", "12", 1.1, 1.0)]):
        gap = L[b]["start"] - L[a]["end"]
        if gap > .3: breath(m, L[a]["end"] + .05, min(.7, gap - .1), g, sh)
    fl = W(tl, "09", "flicker")
    m.hum(m.mask(0, fl) | m.mask(fl + 1.1, L["12"]["end"]), 1.2)
    m.pad(0.8)
    m.scrape(L["02"]["start"] + 0.2, 1.0, 0.4)            # something heavy shifts in the dark cell
    m.clunk(L["05"]["start"] + 0.05, 0.9)                  # the security door
    m.steps(L["05"]["start"] + 0.3, L["06"]["start"], 0.55, 0.2, 1.0, 0.6)
    m.heartbeat(L["07"]["start"], L["12"]["end"], 1.0, 1.0)
    m.drone(L["07"]["start"], L["12"]["end"] + 0.2, 0.9)
    m.flicker(fl, 1.1, 1.2)
    m.scrape(fl + 0.35, 0.4, 1.2)
    m.scrape(W(tl, "10", "scrapes"), 1.1, 1.6)
    m.scrape(L["10"]["end"] + 0.3, 0.4, 1.4)
    m.scrape(L["12"]["start"] + 1.6, 0.35, 1.6)
    m.crack(L["12"]["end"] + 0.15, 1.4)


ids = [f"{i:02d}" for i in range(1, 13)]
gaps = dict(zip(ids, [0.3, 0.6, 0.4, 0.45, 0.4, 0.45, 0.6, 0.6, 0.7, 0.9, 0.7, 0.7]))
build("scp173", gaps, ["Based on SCP-173 by Moto42", "scp-wiki.wikidot.com/scp-173", "Licensed CC BY-SA 3.0"], design)
