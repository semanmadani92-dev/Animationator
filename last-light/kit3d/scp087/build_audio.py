"""Narration + sound design for the 3D SCP-087 episode. Usage (from the kit dir): python scp087/build_audio.py <ll kit dir>"""
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


def echo_steps(m, a, b, step, g):
    k = a
    while k < b:
        th = np.arange(int(0.5 * SR)) / SR
        hit = np.sin(2 * np.pi * 85 * th) * np.exp(-th * 30) * .3 + m.noise(th.size, 20) * np.exp(-th * 35) * .5
        for d, gg in ((0, 1), (.13, .35), (.29, .15)):  # stairwell echo
            m.add(hit * gg, k + d, g)
        k += step


def knock(m, at, g=1.0):
    th = np.arange(int(0.35 * SR)) / SR
    y = np.sin(2 * np.pi * (140 * np.exp(-th * 8) + 60) * th) * np.exp(-th * 22) + m.noise(th.size, 6) * np.exp(-th * 60) * 1.5
    m.add(np.tanh(y * 1.5) * .5, at, g)


def design(m, tl):
    L = tl["lines"]
    door, cry0, face, run, at_door = W(tl, "02", "door"), L["05"]["start"] + .3, W(tl, "09", "face") - .25, L["10"]["start"], L["11"]["start"]
    knock0, weeks = W(tl, "12", "knock"), W(tl, "12", "weeks")
    m.hum(m.mask(0, door + .5), 0.8)                  # the building hallway
    m.clunk(door, 0.9)
    m.wind(door + .3, at_door, 0.25)                   # cold air rising from below
    m.pad(0.7)
    echo_steps(m, door + .7, L["08"]["start"], 0.62, 0.9)
    for k, a in enumerate(np.arange(cry0, run, 3.2)):
        m.cry(a, 2.6, 0.55 + 0.03 * k)                  # never closer: the level barely changes
    m.drone(L["07"]["start"], at_door, 0.8)
    m.sting(face, 1.1)
    m.flicker(face + .1, 1.2, 0.9)
    m.heartbeat(face, at_door + 2.5, 0.7, 1.0)
    echo_steps(m, run + .1, at_door - .1, 0.27, 1.2)
    for i, (a, b, g, sh) in enumerate([("06", "07", .6, .3), ("07", "08", .7, .4), ("08", "09", .8, .5), ("09", "10", 1.0, .8), ("10", "11", 1.2, 1.0), ("11", "12", 1.0, 1.0)]):
        gap = L[b]["start"] - L[a]["end"]
        if gap > .3: breath(m, L[a]["end"] + .05, min(.7, gap - .1), g, sh)
    k = knock0
    while k < tl["cardAt"] - .2:                       # knock... knock... (every 1 to 2 seconds)
        knock(m, k, 1.0 if k < weeks else 0.55)
        k += 1.0 + 0.6 * ((int(k * 7) % 3) / 2)


ids = [f"{i:02d}" for i in range(1, 13)]
gaps = dict(zip(ids, [0.3, 0.7, 0.45, 0.45, 0.6, 0.5, 0.6, 0.6, 0.5, 0.6, 0.6, 0.6]))
build("scp087", gaps, ["Based on SCP-087 by Zaeyde", "scp-wiki.wikidot.com/scp-087", "Licensed CC BY-SA 3.0"], design, tail=3.6, card_pad=1.6)
