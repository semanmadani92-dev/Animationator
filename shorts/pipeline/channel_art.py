"""YouTube channel art: profile picture (800x800, Mark's face) and banner (2560x1440).

Usage: python channel_art.py <out_dir>
The banner keeps the cast inside YouTube's 1546x423 safe area, so it reads on phones, desktop and TV.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pixel"))
from cast import BUILDERS  # noqa: E402
from level import GROUND, build_level, compose_view  # noqa: E402
from mark import PALETTE, build_mark  # noqa: E402
from props import pie  # noqa: E402
from sprite import Sprite, dots  # noqa: E402

N = 50  # portrait art size; x16 = 800 px

PORTRAIT_PAL = dict(PALETTE)


def portrait():
    """Mark's head and shoulders, drawn bigger than his game sprite but with the same design."""
    s = Sprite(N, N)
    # sword resting on his shoulder, behind everything
    s.seg(37, 46, 47, 12, "steel", 1.3)
    s.seg(33, 43, 41, 47, "gold", 1.1)
    # hoodie shoulders and body
    s.poly([(4, 51), (46, 51), (42, 40), (35, 37), (15, 37), (8, 40)], "red")
    s.rect(19, 37, 31, 41, "hoodin")
    # hood, inner hood, face
    s.ellipse(25, 23.5, 17.5, 16.5, "red")
    s.poly([(21, 8), (25, 3), (29, 8)], "red")
    s.ellipse(25, 26.5, 13.5, 13, "hoodin")
    s.ellipse(25, 28, 11.5, 10.5, "skin")
    s.poly([(15, 30), (35, 30), (31, 37), (25, 39.5), (19, 37)], "skin")
    # red hair: spiky fringe and tufts at the sides of the hood
    fringe = [21, 22, 21, 19, 20, 22, 23, 21, 19, 20, 22, 23, 22, 20, 19, 21, 22, 21, 19, 20, 22, 21, 20]
    for i, bottom in enumerate(fringe):
        x = 14 + i
        for y in range(15, bottom + 1):
            if s.get(x, y) in ("skin", "hoodin"):
                s.g[y][x] = "hair"
    for x, y0, y1 in ((12, 21, 29), (13, 27, 31), (37, 21, 29), (36, 27, 31)):
        s.rect(x, y0, x, y1, "hair")
    # drawstrings with tips
    for x in (20, 30):
        s.rect(x, 39, x, 46, "string")
    img = s.render(PORTRAIT_PAL, flat=("hoodin",))
    # ---- face: the signature annoyed look
    eye, iris, lid, brow = "#261a2e", "#6a4a9a", "#1b1222", "#7a2a1a"
    skin = PALETTE["skin"][0]
    dots(img, [(x, y) for x in range(15, 36) for y in (23, 24)], skin)  # clear the brow line
    for x0 in (16, 29):
        dots(img, [(x, y) for x in range(x0, x0 + 6) for y in range(27, 33)], eye)
        dots(img, [(x0 + 1, y) for y in (30, 31)] + [(x0 + 2, y) for y in (30, 31)] + [(x0 + 3, 31)], iris)
        dots(img, [(x0, y) for y in (32,)] + [(x0 + 5, 32)], skin)  # round the bottom corners
        dots(img, [(x, 26) for x in range(x0 - 1, x0 + 7)], lid)  # heavy flat eyelid: half-lidded
        dots(img, [(x, 27) for x in range(x0, x0 + 6)], lid)
        dots(img, [(x0 + 1, 28), (x0 + 1, 29)], "#ffffff")  # highlights
        dots(img, [(x0 + 4, 31)], "#c8b8ff")
    dots(img, [(15, 23), (16, 24), (17, 24), (18, 24), (19, 25), (20, 25)], brow)  # brows slant in
    dots(img, [(35, 23), (34, 24), (33, 24), (32, 24), (31, 25), (30, 25)], brow)
    dots(img, [(25, 33), (25, 34)], PALETTE["skin"][1])  # nose
    dots(img, [(16, 35), (18, 34), (19, 36), (31, 34), (32, 36), (34, 35)], "#b9683e")  # freckles
    dots(img, [(22, 37), (23, 36), (24, 36), (25, 36), (26, 36), (27, 36)], "#7a3a3a")  # unimpressed mouth
    # anime anger mark
    mark = [(38, 9), (40, 9), (37, 10), (38, 10), (40, 10), (41, 10), (37, 12), (38, 12), (40, 12), (41, 12),
            (38, 13), (40, 13)]
    dots(img, mark, "#ff3a46")
    return img


def sky_disc():
    bg = Image.new("RGBA", (N, N))
    d = ImageDraw.Draw(bg)
    bands = ["#2a54b8", "#3a6cd0", "#4479da", "#4f86e0", "#5b93e6", "#6aa2ec", "#7cb2f2", "#90c2f7"]
    for y in range(N):
        i = min(len(bands) - 1, y * len(bands) // N)
        nxt = min(len(bands) - 1, i + 1)
        for x in range(N):
            edge = (y * len(bands)) % N >= N - 2 and (x + y) % 2 == 0
            d.point((x, y), fill=bands[nxt] if edge else bands[i])
    for cx, cy in ((7, 12), (42, 33), (9, 38)):  # tiny sparkles
        d.point([(cx, cy), (cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)], fill="#bde0fe")
    return bg


def profile(out):
    img = sky_disc()
    img.alpha_composite(portrait())
    img.resize((800, 800), Image.NEAREST).convert("RGB").save(out / "profile_800.png")
    # preview of how YouTube shows it (circle)
    big = img.resize((800, 800), Image.NEAREST)
    mask = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 799, 799], fill=255)
    prev = Image.new("RGBA", (800, 800), "#0f0f0f")
    prev.paste(big, (0, 0), mask)
    prev.convert("RGB").save(out / "profile_preview_circle.png")


def banner(out):
    S = 8
    vw, vh = 2560 // S, 1440 // S
    feet = 113  # art row of the ground line: bottom of the safe band (rows 63.5 to 116.4)
    cam_x, cam_y = 40, GROUND - feet
    view = compose_view(build_level(), cam_x, cam_y, vw, vh)

    def put(spr, wx, dy=0):
        view.alpha_composite(spr, (round(wx - cam_x - spr.width / 2), feet - spr.height + 1 + dy))

    put(BUILDERS["bumblewick"]("confused"), 126)
    put(BUILDERS["reginald"]("proud"), 162)
    put(BUILDERS["vexmore"]("smug"), 274)
    g = BUILDERS["grub"]("sneaky")
    put(g, 238)
    p = pie()
    view.alpha_composite(p, (round(238 - cam_x - 4.5), feet - 30 + 1 + 17))
    put(build_mark("annoyed"), 200, dy=1)
    big = view.resize((2560, 1440), Image.NEAREST).convert("RGB")
    big.save(out / "banner_2560x1440.png")
    # guide overlay: the area every device shows
    guide = big.copy()
    d = ImageDraw.Draw(guide)
    d.rectangle([(2560 - 1546) // 2, (1440 - 423) // 2, (2560 + 1546) // 2, (1440 + 423) // 2], outline="#ffff00", width=6)
    d.rectangle([0, (1440 - 423) // 2, 2559, (1440 + 423) // 2], outline="#00ffff", width=4)
    guide.save(out / "banner_safe_area_guide.png")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    profile(out)
    banner(out)
    print("saved to", out)
