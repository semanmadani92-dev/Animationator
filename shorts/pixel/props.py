"""Small props drawn per frame: the stolen pie and the big oak that gets cut down (episode 1)."""
from PIL import Image, ImageDraw

PIE_ROWS = [
    "..ooooo..",
    ".oyLyLyo.",
    "oyyLyLyyo",
    "oLLLLLLLo",
    "otttttttO",
    ".ottttto.",
    "..ooooo..",
]
PIE_COL = {"o": "#3a2414", "O": "#3a2414", "y": "#e8a83a", "L": "#ffd977", "t": "#b07a1e"}


def pie():
    img = Image.new("RGBA", (len(PIE_ROWS[0]), len(PIE_ROWS)), (0, 0, 0, 0))
    for y, row in enumerate(PIE_ROWS):
        for x, c in enumerate(row):
            if c in PIE_COL:
                img.putpixel((x, y), (*bytes.fromhex(PIE_COL[c][1:]), 255))
    return img


# ---------------------------------------------------------------- the oak
OAK_W, OAK_H = 66, 108
OAK_BASE = (33, OAK_H - 1)  # trunk base (the cut point is CUT px above it)
CUT = 4
GRUB_PERCH = (9, -80)  # where Grub stands, relative to the base (x right, y up is negative)
CANOPY = ((33, 30, 20), (17, 41, 13), (49, 41, 13), (24, 19, 13), (43, 18, 13), (33, 11, 12), (21, 53, 9),
          (46, 53, 9))


def oak():
    """A tall oak, trunk base at OAK_BASE. Returns (tree, stump): the stump is the bottom CUT rows of the trunk."""
    img = Image.new("RGBA", (OAK_W, OAK_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bx, by = OAK_BASE
    # trunk, slightly flared at the root, bark lines
    d.polygon([(bx - 5, by), (bx + 5, by), (bx + 3, 44), (bx - 3, 44)], fill="#6b4426", outline="#3a2414")
    d.polygon([(bx - 7, by), (bx - 4, by - 5), (bx + 4, by - 5), (bx + 7, by)], fill="#6b4426", outline="#3a2414")
    for x, y0, y1 in ((bx - 2, 60, 80), (bx + 1, 70, 95), (bx - 1, 88, 100)):
        d.line([x, y0, x, y1], fill="#4e3018")
    d.line([bx + 3, 50, bx + 3, by - 6], fill="#8a5a34")  # lit edge
    # branch Grub perches on
    px, py = bx + GRUB_PERCH[0], by + GRUB_PERCH[1]
    d.line([bx, py + 8, px + 6, py + 1], fill="#3a2414", width=3)
    d.line([bx, py + 8, px + 6, py + 1], fill="#6b4426", width=1)
    # canopy: outline pass, fill pass, highlight pass so clumps merge into one crown
    for cx, cy, r in CANOPY:
        d.ellipse([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], fill="#1f4a26")
    for cx, cy, r in CANOPY:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#3f8f4a")
    for cx, cy, r in CANOPY:
        d.ellipse([cx - r * 0.75, cy - r * 0.85, cx + r * 0.35, cy + r * 0.2], fill="#4fa553")
    for cx, cy, r in CANOPY[:6]:
        d.ellipse([cx - r * 0.55, cy - r * 0.75, cx - r * 0.05, cy - r * 0.3], fill="#6cc260")
    # the perch shows through the leaves
    d.line([px - 2, py + 1, px + 8, py + 1], fill="#3a2414", width=2)
    d.line([px - 1, py, px + 7, py], fill="#8a5a34")
    stump = img.crop((0, OAK_H - CUT, OAK_W, OAK_H))
    tree = img.copy()
    ImageDraw.Draw(tree).rectangle([0, OAK_H - CUT, OAK_W, OAK_H], fill=(0, 0, 0, 0))
    return tree, stump


def stump_top(stump):
    """Stump with a pale cut face on top (after the chop)."""
    s = stump.copy()
    d = ImageDraw.Draw(s)
    bx = OAK_BASE[0]
    d.line([bx - 4, 0, bx + 4, 0], fill="#e8c890")
    d.line([bx - 1, 0, bx + 1, 0], fill="#c99a5a")
    return s


if __name__ == "__main__":
    t, s = oak()
    sheet = Image.new("RGBA", (OAK_W + 20, OAK_H + 10), "#7cb2f2")
    sheet.alpha_composite(t, (0, 0))
    sheet.alpha_composite(stump_top(s), (0, OAK_H - 4))
    sheet.alpha_composite(pie(), (OAK_W + 4, 10))
    sheet.resize((sheet.width * 6, sheet.height * 6), Image.NEAREST).save("props_preview.png")


# ---------------------------------------------------------------- episode 2: Grub's hideout
def _pixels(rows, colors):
    img = Image.new("RGBA", (max(len(r) for r in rows), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in colors:
                img.putpixel((x, y), (*bytes.fromhex(colors[c][1:]), 255))
    return img


FONT3 = {"P": ["111", "101", "111", "100", "100"], "U": ["101", "101", "101", "101", "111"],
         "L": ["100", "100", "100", "100", "111"], "K": ["101", "110", "100", "110", "101"],
         "E": ["111", "100", "110", "100", "111"], "O": ["111", "101", "101", "101", "111"],
         "T": ["111", "010", "010", "010", "010"], " ": ["000"] * 5}


def pixel_text(d, x, y, text, fill):
    for ch in text:
        for r, row in enumerate(FONT3[ch]):
            for c, bit in enumerate(row):
                if bit == "1":
                    d.point((x + c, y + r), fill=fill)
        x += len(FONT3[ch][0]) + 1


FORT_W, FORT_H = 96, 92
DOOR_W, DOOR_H = 18, 26
DOOR_AT = (39, FORT_H - DOOR_H)  # top-left of the doorway inside the fortress image


def fortress():
    """A goblin hideout carved into a rock: rough boulder face, skull, torches, crude flag, dark doorway.
    Bottom row sits on the ground. The door itself is drawn separately (door())."""
    img = Image.new("RGBA", (FORT_W, FORT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rock = [(2, FORT_H), (6, 60), (14, 44), (24, 30), (36, 22), (50, 18), (62, 24), (74, 32), (84, 46), (90, 62),
            (94, FORT_H)]
    d.polygon(rock, fill="#6e6880", outline="#1b1222")
    for cx, cy, r, col in ((30, 52, 16, "#7c7690"), (62, 48, 18, "#7c7690"), (48, 34, 12, "#86809a"),
                           (18, 72, 12, "#746e86"), (80, 72, 12, "#746e86")):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        d.arc([cx - r, cy - r, cx + r, cy + r], 200, 300, fill="#a49eb6")  # lit top-left edges
        d.arc([cx - r, cy - r, cx + r, cy + r], 20, 120, fill="#56506a")
    for x0, y0, x1, y1 in ((20, 40, 26, 46), (70, 58, 76, 52), (12, 82, 18, 78), (84, 84, 88, 78)):
        d.line([x0, y0, x1, y1], fill="#4a4458")  # cracks
    # moss along the bottom
    for x in range(4, FORT_W - 4, 3):
        d.line([x, FORT_H - 1, x, FORT_H - 2 - (x * 7) % 4], fill="#4f9a48")
    # doorway: dark arch with a timber frame
    x0, y0 = DOOR_AT
    d.rectangle([x0 - 3, y0 - 1, x0 + DOOR_W + 2, FORT_H - 1], fill="#5a3a20", outline="#1b1222")
    d.rectangle([x0, y0 + 2, x0 + DOOR_W - 1, FORT_H - 1], fill="#140e1a")
    d.rectangle([x0 - 4, y0 - 3, x0 + DOOR_W + 3, y0], fill="#7a4e2a", outline="#1b1222")  # lintel
    # skull over the door
    sx, sy = x0 + DOOR_W // 2, y0 - 9
    d.ellipse([sx - 4, sy - 4, sx + 4, sy + 3], fill="#efe6dc", outline="#1b1222")
    d.rectangle([sx - 2, sy + 2, sx + 2, sy + 5], fill="#efe6dc", outline="#1b1222")
    d.point([(sx - 2, sy), (sx + 2, sy)], fill="#1b1222")
    d.point([(sx - 1, sy), (sx + 1, sy), (sx, sy + 2)], fill="#1b1222")
    # torches either side
    for tx in (x0 - 9, x0 + DOOR_W + 8):
        d.rectangle([tx - 1, y0 + 4, tx + 1, y0 + 12], fill="#6b4426", outline="#1b1222")
    # crude flag on the top
    d.line([50, 18, 50, 2], fill="#3a2414", width=1)
    d.polygon([(51, 2), (63, 4), (58, 7), (63, 10), (51, 10)], fill="#5aa83a", outline="#1b1222")
    d.point([(55, 5), (58, 5)], fill="#ffe04a")  # goblin eyes on the flag
    return img


def torch_flames(t):
    """List of (dx, dy, color) flame pixels relative to a torch top, flickering with time."""
    k = int(t * 10)
    tall = 3 + (k % 3)
    pts = []
    for i in range(tall):
        w = 1 if i < tall - 1 else 0
        for dx in range(-w, w + 1):
            pts.append((dx + ((k + i) % 2 if i == tall - 1 else 0), -1 - i, "#ffd23f" if i < 2 else "#ff6a2a"))
    return pts


def door(open_k=0.0, peep=False):
    """The door; open_k 0 (shut) to 1 (swung fully open on its right-hand hinge). Peep shows the slot open."""
    w = max(2, round(DOOR_W * (1 - open_k)))
    img = Image.new("RGBA", (DOOR_W, DOOR_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = DOOR_W - w
    base = "#8a5a34" if open_k < 0.5 else "#6b4426"
    d.rectangle([x0, 2, DOOR_W - 1, DOOR_H - 1], fill=base, outline="#1b1222")
    if w > 6:
        for px in range(x0 + 4, DOOR_W - 1, 4):
            d.line([px, 3, px, DOOR_H - 2], fill="#5e3a1e")
        for by in (6, DOOR_H - 7):
            d.line([x0 + 1, by, DOOR_W - 2, by], fill="#3a3346")  # iron bands
        if open_k == 0:
            d.ellipse([x0 + 2, 13, x0 + 5, 16], outline="#c3cbd6")  # ring handle on the left
            d.rectangle([5, 8, 12, 10], fill="#140e1a" if peep else "#5e3a1e", outline="#1b1222")
            if peep:
                d.point([(7, 9), (10, 9)], fill="#ffe04a")
    return img


def sign_pull():
    img = Image.new("RGBA", (19, 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 9, 10, 21], fill="#6b4426", outline="#3a2414")
    d.rectangle([0, 0, 18, 9], fill="#c9a46a", outline="#3a2414")
    pixel_text(d, 2, 2, "PULL", "#3a2414")
    return img


CHICKEN_COL = {"W": "#f4f1e6", "w": "#c9c3b6", "r": "#e8303a", "o": "#f2a33d", "k": "#1b1222", "y": "#f2a33d",
               "O": "#1b1222"}
CHICKEN = [
    ["....rr.....", "...OrrO....", "..OWWWWOo..", "..OWkWWOoo.", "OOOWWWWWO..", "OWWwwwWWO..", "OWWWwwWWO..",
     ".OWWWWWO...", "..OOOOO....", "...y..y....", "..yy.yy...."],
    ["....rr.....", "...OrrO....", "..OWWWWOo..", "..OWkWWOoo.", "OOOWWWWWO..", "OWwwWWWWO..", "OWWWWWWWO..",
     ".OWWWWWO...", "..OOOOO....", "....yy.....", "...yy.y...."],
]


def chicken(frame=0):
    return _pixels(CHICKEN[frame % 2], CHICKEN_COL)
