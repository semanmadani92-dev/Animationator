"""Narration + sound design for the 3D SCP-096 episode. Usage (from the kit dir): python scp096/build_audio.py <ll kit dir>"""
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


def static(m, at, dur, g=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = m.noise(n, 1) * (0.6 + 0.4 * (np.sin(2 * np.pi * 13 * t) > 0)) * np.minimum(1, t / .05) * np.minimum(1, (dur - t) / .1)
    m.add(y * .05 * g, at)


def siren(m, a, b, g=1.0):
    t = m.t - a; mk = m.mask(a, b)
    f = 620 + 260 * (np.sin(2 * np.pi * 0.55 * t) > 0)
    ph = 2 * np.pi * np.cumsum(f * mk) / SR
    m.y += np.tanh(np.sin(ph) * 2) * .035 * g * mk * np.clip(t / .3, 0, 1)


def tear(m, at, g=1.0):
    """Steel ripping: a bright crack, a metallic screech, a heavy boom."""
    m.crack(at, 1.6 * g); m.boom(at, 1.0 * g)
    tc = np.arange(int(1.2 * SR)) / SR
    f = 900 - 500 * tc + 80 * np.sin(2 * np.pi * 23 * tc)
    sc = np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 + .6 * m.noise(tc.size, 3)) * np.exp(-tc * 2.5)
    m.add(np.tanh(sc * 1.5) * .25 * g, at + .02)
    for k in range(5): m.clunk(at + .25 + k * .13, .5 * g)   # plates hitting the floor


def design(m, tl):
    L = tl["lines"]
    flick, seen, run = W(tl, "05", "flickers"), W(tl, "06", "face"), W(tl, "09", "run")
    alarm, doors, breach = W(tl, "09", "alarms"), W(tl, "09", "doors"), W(tl, "10", "tears")
    quiet = L["12"]["start"]; end = L["12"]["end"]
    m.hum(m.mask(0, quiet), 1.0)
    m.pad(0.8)
    static(m, flick, seen - flick + 1.2, 1.0)
    m.sting(seen - .05, 1.0)
    m.heartbeat(seen, quiet + 3.5, 0.9, 1.0)
    m.scream(L["07"]["start"] + .9, 4.5, 0.9, far=True)
    m.scream(L["08"]["start"] + .4, 3.0, 0.7, far=True)
    siren(m, alarm, quiet, 1.0)
    m.clunk(doors, 1.2)
    m.steps(run, quiet - .2, 0.33, 0.45, 0.99, 1.0)
    tear(m, breach, 1.0)
    m.drone(L["07"]["start"], quiet, 1.0)
    m.scream(L["11"]["start"], 2.6, 1.0)
    for i, (a, b, g, sh) in enumerate([("06", "07", .6, .3), ("07", "08", .7, .4), ("08", "09", .8, .5), ("10", "11", 1.0, .8), ("11", "12", 1.1, 1.0)]):
        gap = L[b]["start"] - L[a]["end"]
        if gap > .3: breath(m, L[a]["end"] + .05, min(.7, gap - .1), g, sh)
    breath(m, quiet + 2.2, .8, 1.2, 1.0)
    m.scream(end - .25, 1.4, 1.6)   # it's right behind him
    m.boom(end - .2, 1.2)
    m.crack(end + .1, 1.4)


ids = [f"{i:02d}" for i in range(1, 13)]
gaps = dict(zip(ids, [0.3, 0.6, 0.45, 0.45, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.6, 1.0]))
build("scp096", gaps, ["Based on SCP-096 by Dr Dan", "scp-wiki.wikidot.com/scp-096", "Licensed CC BY-SA 3.0"], design)
