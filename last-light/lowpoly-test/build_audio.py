import sys
sys.path.insert(0, sys.argv[1])
from ll_audio import W, build
def design(m, tl):
    L = tl["lines"]
    fl = W(tl, "08", "flicker")
    m.hum(m.mask(0, fl) | m.mask(fl + 1.1, L["11"]["end"]), 1.2)
    m.pad(0.8)
    m.flicker(fl, 1.1, 1.2)
    m.scrape(fl + 0.3, 0.4, 1.2)
    m.scrape(W(tl, "09", "scrapes"), 1.1, 1.6)
    m.scrape(L["09"]["end"] + 0.3, 0.4, 1.4)
    m.heartbeat(L["09"]["start"], L["11"]["end"], 1.2, 1.0)
    m.drone(L["08"]["start"], L["11"]["end"] + 0.2, 0.9)
    m.crack(L["11"]["end"] + 0.15, 1.4)
build("s173", {"01": 0.3, "08": 0.6, "09": 0.8, "11": 0.6}, ["Based on SCP-173 by Moto42", "scp-wiki.wikidot.com/scp-173", "Licensed CC BY-SA 3.0"], design, tail=1.6, card_pad=0.6)
