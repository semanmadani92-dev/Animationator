"""Narration + sound design for the 3D SCP-173 episode. Usage: python build_audio.py <ll kit dir> (run from the scene dir's parent)."""
import sys
sys.path.insert(0, sys.argv[1])
from ll_audio import W, build


def design(m, tl):
    L = tl["lines"]
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
gaps = dict(zip(ids, [0.3, 0.6, 0.4, 0.45, 0.4, 0.45, 0.5, 0.4, 0.5, 0.8, 0.5, 0.45]))
build("scp173", gaps, ["Based on SCP-173 by Moto42", "scp-wiki.wikidot.com/scp-173", "Licensed CC BY-SA 3.0"], design)
