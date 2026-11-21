"""Timelines and sound design for the Last Light SCP episodes. Usage: python episodes.py scp173 [scp096 scp087]"""
import sys

from ll_audio import W, build


def credit(num, author):
    return [f"Based on SCP-{num} by {author}", f"scp-wiki.wikidot.com/scp-{num}", "Licensed CC BY-SA 3.0"]


def d173(m, tl):
    L = tl["lines"]
    fl = W(tl, "08", "flicker")
    m.hum(m.mask(0, fl) | m.mask(fl + 1.2, L["11"]["end"]), 1.2)
    m.pad(0.8)
    m.scrape(0.2, 1.2, 0.5)  # stone scraping in the empty cell
    m.flicker(fl, 1.1, 1.2)
    m.scrape(fl + 0.25, 0.4, 1.2)
    m.scrape(fl + 0.75, 0.4, 1.3)
    m.scrape(W(tl, "09", "scrapes"), 1.1, 1.6)
    m.scrape(L["09"]["end"] + 0.25, 0.4, 1.4)
    m.heartbeat(L["06"]["start"], L["11"]["end"], 1.0, 1.0)
    m.drone(L["06"]["start"], L["11"]["end"] + 0.2, 0.9)
    m.scrape(L["10"]["end"] + 0.2, 0.35, 1.6)
    m.crack(L["11"]["end"] + 0.15, 1.4)


def d096(m, tl):
    L = tl["lines"]
    m.pad(0.9)
    m.hum(m.mask(0, L["04"]["start"]), 0.8)
    m.scream(W(tl, "05", "screaming"), 2.4, 1.0)
    m.steps(L["06"]["start"] + 0.6, L["08"]["start"], 0.32, 0.5, 0.97, 1.0)
    m.drone(L["06"]["start"], L["08"]["start"], 0.8)
    m.scream(W(tl, "09", "scream") - 0.2, 2.6, 0.7, far=True)
    m.heartbeat(L["09"]["start"], L["11"]["end"], 1.0, 0.8)
    m.scream(L["11"]["end"] + 0.15, 1.2, 1.4)
    m.boom(L["11"]["end"] + 0.15, 0.8)


def d087(m, tl):
    L = tl["lines"]
    m.pad(0.9)
    m.hum(m.mask(0, L["02"]["start"]), 0.9)
    m.clunk(W(tl, "01", "staircase"), 0.5)  # the closet door
    m.steps(L["02"]["start"], L["07"]["start"], 0.5, 0.18, 1.0, 0.8)
    m.cry(L["04"]["start"] + 0.4, 3.0, 0.9)
    m.cry(L["05"]["start"] + 1.0, 3.0, 0.8)
    m.cry(L["06"]["start"] + 0.5, 2.5, 0.8)
    m.sting(L["08"]["start"] - 0.05, 1.0)
    m.drone(L["07"]["start"], L["11"]["end"], 1.0)
    m.steps(L["09"]["start"] + 0.3, L["11"]["start"], 0.26, 0.5, 0.99, 1.1)
    m.heartbeat(L["09"]["start"], L["11"]["end"], 0.7, 1.0)
    m.flicker(W(tl, "11", "isn"), 1.0, 1.2)


EPISODES = {
    "scp173": (dict(zip(["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
                        [0.3, 0.6, 0.4, 0.4, 0.35, 0.5, 0.4, 0.5, 0.9, 0.5, 0.45])), credit("173", "Moto42"), d173),
    "scp096": (dict(zip(["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
                        [0.3, 0.6, 0.4, 0.4, 0.3, 0.6, 0.4, 0.6, 0.5, 0.9, 0.6])), credit("096", "Dr Dan"), d096),
    "scp087": (dict(zip(["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"],
                        [0.3, 0.6, 0.4, 0.4, 0.4, 0.4, 0.5, 0.5, 0.4, 0.4, 0.6])), credit("087", "Zaeyde"), d087),
}

if __name__ == "__main__":
    for ep in sys.argv[1:]:
        gaps, cr, design = EPISODES[ep]
        build(ep, gaps, cr, design)
