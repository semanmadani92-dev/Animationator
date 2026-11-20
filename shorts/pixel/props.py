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
