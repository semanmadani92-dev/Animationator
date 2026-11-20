"""A side-scrolling level: village -> forest path -> canyon with a long rope bridge -> Vexmore's castle.

World is WORLD_W x WORLD_H logical pixels. Layers (back to front): sky, mountains
(parallax 0.25), hills (parallax 0.5), ground/foreground (1.0). The bridge and
characters are drawn per frame on top.
"""
import math
import random

from PIL import Image, ImageDraw

from village import _cottage, _lamp

WORLD_W, WORLD_H = 800, 400
GROUND = 250
LEFT_EDGE, RIGHT_EDGE = 440, 680  # canyon walls (bridge posts stand on them)
RIVER_Y = 384
PARALLAX = {"mountains": 0.25, "hills": 0.5}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _sky():
    img = Image.new("RGB", (WORLD_W, WORLD_H))
    px = img.load()
    bands = ["#3a6cd0", "#4479da", "#4f86e0", "#5b93e6", "#6aa2ec", "#7cb2f2", "#90c2f7", "#a6d2fb", "#bde0fe"]
    bh = 26
    for y in range(WORLD_H):
        i = min(y // bh, len(bands) - 1)
        nxt = min(i + 1, len(bands) - 1)
        for x in range(WORLD_W):
            px[x, y] = _rgb(bands[nxt] if y % bh >= bh - 3 and (x + y) % 2 == 0 else bands[i])
    return img


def _cloud(d, cx, cy, k=1.0):
    for dx, dy, r in ((0, 0, 6), (-8, 2, 5), (8, 2, 5), (-4, -4, 5), (5, -3, 5), (13, 3, 4)):
        d.ellipse([cx + dx * k - r * k, cy + dy * k - r * k, cx + dx * k + r * k, cy + dy * k + r * k], fill="#ffffff")
    d.rectangle([cx - 12 * k, cy + 4 * k, cx + 16 * k, cy + 6 * k], fill="#d6e6f7")


def _mountains(rnd):
    w = int(WORLD_W * PARALLAX["mountains"]) + 200
    img = Image.new("RGBA", (w, WORLD_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for cx, cy in ((30, 70), (150, 52), (250, 84)):
        _cloud(d, cx, cy)
    pts = [(0, GROUND)]
    for x in range(0, w + 8, 8):
        pts.append((x, 150 + int(30 * abs(math.sin(x / 37.0))) + int(10 * math.sin(x / 11.0)) + rnd.randrange(4)))
    pts.append((w, GROUND))
    d.polygon(pts, fill="#8094cc")
    d.line(pts[1:-1], fill="#a9b6e2")
    for x, y in pts[1:-1]:
        if y < 162:
            d.polygon([(x - 4, y + 5), (x, y), (x + 4, y + 5)], fill="#eef2ff")
    return img


def _hills(rnd):
    w = int(WORLD_W * PARALLAX["hills"]) + 200
    img = Image.new("RGBA", (w, WORLD_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(0, GROUND + 4)]
    for x in range(0, w + 4, 4):
        pts.append((x, 205 + int(12 * math.sin(x / 29.0 + 1)) + int(5 * math.sin(x / 9.0))))
    pts.append((w, GROUND + 4))
    d.polygon(pts, fill="#5f9e6a")
    d.line(pts[1:-1], fill="#7cbd7a")
    for x in range(6, w, 11):  # distant tree line
        y = 205 + int(12 * math.sin(x / 29.0 + 1)) + int(5 * math.sin(x / 9.0))
        d.ellipse([x - 5, y - 8, x + 5, y + 2], fill="#3f7d4f")
    return img


def _tree(d, x, base, h, rnd):
    d.rectangle([x - 2, base - h * 0.45, x + 2, base], fill="#6b4426", outline="#3a2414")
    for dx, dy, r in ((0, -0.75, 0.32), (-0.28, -0.55, 0.26), (0.28, -0.55, 0.26), (0, -0.48, 0.24)):
        cx, cy, rr = x + dx * h, base + dy * h, r * h
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill="#3f8f4a", outline="#24502a")
    d.ellipse([x - h * 0.22, base - h * 0.98, x + h * 0.02, base - h * 0.78], fill="#5fb35a")


def _dead_tree(d, x, base):
    d.line([x, base, x, base - 30], fill="#3a2e34", width=3)
    for (dx, dy, ex, ey) in ((0, -18, -9, -28), (0, -22, 8, -34), (-5, -24, -11, -31), (5, -30, 10, -38)):
        d.line([x + dx, base + dy, x + ex, base + ey], fill="#3a2e34", width=1)


def _castle(d, x, base):
    dark, mid, win = "#3a3346", "#4a4258", "#ff3a46"
    d.rectangle([x - 14, base - 95, x + 14, base], fill=dark, outline="#1b1222")
    d.polygon([(x - 18, base - 95), (x, base - 125), (x + 18, base - 95)], fill="#5a2a7a", outline="#1b1222")
    for sx in (-30, 30):
        d.rectangle([x + sx - 8, base - 60, x + sx + 8, base], fill=mid, outline="#1b1222")
        for bx in range(-8, 9, 4):
            d.rectangle([x + sx + bx - 1, base - 64, x + sx + bx + 1, base - 60], fill=mid)
        d.rectangle([x + sx - 1, base - 45, x + sx + 1, base - 40], fill=win)
    for wy in (-80, -60, -40):
        d.rectangle([x - 2, base + wy, x + 2, base + wy + 6], fill=win)
    d.rectangle([x - 5, base - 14, x + 5, base], fill="#1b1222")


def _sign(d, x, base):
    d.rectangle([x - 1, base - 22, x + 1, base], fill="#6b4426", outline="#3a2414")
    d.polygon([(x - 12, base - 24), (x + 12, base - 24), (x + 17, base - 19), (x + 12, base - 14), (x - 12, base - 14)],
              fill="#a8743e", outline="#3a2414")
    for px_, py_ in ((x - 7, base - 21), (x - 6, base - 21), (x - 8, base - 20), (x - 5, base - 20), (x - 7, base - 18)):
        d.point((px_, py_), fill="#f4f1e6")  # tiny skull
    d.line([x - 1, base - 19, x + 9, base - 19], fill="#3a2414")
    d.polygon([(x + 9, base - 22), (x + 13, base - 19), (x + 9, base - 16)], fill="#3a2414")


FOREST = ((280, 58), (318, 74), (352, 52), (388, 66), (420, 46))
BUSHES = (300, 340, 372, 405)


def _ground(rnd, forest=FOREST, bushes=BUSHES):
    img = Image.new("RGBA", (WORLD_W, WORLD_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    px = img.load()
    # canyon back: dark gradient between the walls, river at the bottom
    for y in range(GROUND, WORLD_H):
        t = (y - GROUND) / (WORLD_H - GROUND)
        c = tuple(int(a + (b - a) * t) for a, b in zip(_rgb("#56659e"), _rgb("#141024")))
        d.line([LEFT_EDGE, y, RIGHT_EDGE, y], fill=c)
    for _ in range(140):
        x, y = rnd.randrange(LEFT_EDGE, RIGHT_EDGE), rnd.randrange(GROUND + 20, RIVER_Y - 10)
        px[x, y] = (*_rgb("#7d88bb"), 255)
    d.rectangle([LEFT_EDGE, RIVER_Y, RIGHT_EDGE, WORLD_H], fill="#2f6fc4")
    for x in range(LEFT_EDGE, RIGHT_EDGE, 7):
        d.line([x, RIVER_Y + 2 + (x // 7) % 3, x + 3, RIVER_Y + 2 + (x // 7) % 3], fill="#9fd8ff")
    d.line([LEFT_EDGE, RIVER_Y, RIGHT_EDGE, RIVER_Y], fill="#6ab0ff")
    # solid ground on both sides of the canyon
    for x0, x1 in ((0, LEFT_EDGE), (RIGHT_EDGE, WORLD_W - 1)):
        d.rectangle([x0, GROUND, x1, WORLD_H], fill="#6e5a48")
        for _ in range(int((x1 - x0) * 1.4)):
            rx, ry = rnd.randrange(x0, x1), rnd.randrange(GROUND + 10, WORLD_H)
            d.rectangle([rx, ry, rx + 2, ry + 1], fill=rnd.choice(["#5e4c3c", "#7e6a56", "#54443a"]))
        d.rectangle([x0, GROUND, x1, GROUND + 7], fill="#7a5a3a")
        d.rectangle([x0, GROUND, x1, GROUND + 3], fill="#5fae58")
        d.line([x0, GROUND - 1, x1, GROUND - 1], fill="#7cc36a")
    # jagged canyon walls
    for y in range(GROUND + 4, WORLD_H, 4):
        j = rnd.randrange(0, 5)
        d.rectangle([LEFT_EDGE - j, y, LEFT_EDGE, y + 3], fill="#463a32")
        j = rnd.randrange(0, 5)
        d.rectangle([RIGHT_EDGE, y, RIGHT_EDGE + j, y + 3], fill="#463a32")
    # village: cobblestone street and cottages
    for x in range(0, 262, 8):
        d.rounded_rectangle([x, GROUND + 1, x + 6, GROUND + 4], radius=1, fill="#c9bba6", outline="#8f826e")
    _cottage(d, 8, 58, GROUND - 46, GROUND, "#b44a32", "#8a3424", GROUND - 76)
    _cottage(d, 92, 136, GROUND - 40, GROUND, "#3f6fb5", "#2f548c", GROUND - 66, chimney=True)
    _cottage(d, 172, 226, GROUND - 48, GROUND, "#c98a2e", "#9a6820", GROUND - 80)
    for lx in (72, 154, 244):
        _lamp(d, lx, GROUND)
    for fx in range(232, 262, 4):  # fence
        d.rectangle([fx, GROUND - 7, fx + 1, GROUND], fill="#a8743e")
    d.line([232, GROUND - 5, 262, GROUND - 5], fill="#7a4e26")
    # forest path
    for tx, th in forest:
        _tree(d, tx, GROUND, th, rnd)
    for bx in bushes:
        d.ellipse([bx - 7, GROUND - 7, bx + 7, GROUND + 2], fill="#4f9a48", outline="#24502a")
    _sign(d, 428, GROUND)
    # far side: dead trees and the castle
    _dead_tree(d, 700, GROUND)
    _dead_tree(d, 788, GROUND)
    _castle(d, 748, GROUND)
    for _ in range(30):
        x = rnd.randrange(0, WORLD_W)
        if LEFT_EDGE - 2 <= x <= RIGHT_EDGE + 2:
            continue
        px[x, GROUND - 2] = (*_rgb(rnd.choice(["#5fae58", "#ff6b6b", "#ffd93b", "#ffffff"])), 255)
    return img


def build_level(seed=11, forest=FOREST, bushes=BUSHES):
    """forest: (x, height) of the background trees; leave a gap where an episode puts its own prop tree."""
    rnd = random.Random(seed)
    return {"sky": _sky(), "mountains": _mountains(rnd), "hills": _hills(rnd), "ground": _ground(rnd, forest, bushes)}


def compose_view(layers, cam_x, cam_y, vw, vh):
    """Return an RGBA view (vw x vh) of the world with parallax, top-left at (cam_x, cam_y)."""
    cam_x, cam_y = int(round(cam_x)), int(round(cam_y))
    view = layers["sky"].crop((0, cam_y, vw, cam_y + vh)).convert("RGBA")
    for name in ("mountains", "hills"):
        ox = int(cam_x * PARALLAX[name])
        view.alpha_composite(layers[name].crop((ox, cam_y, ox + vw, cam_y + vh)))
    view.alpha_composite(layers["ground"].crop((cam_x, cam_y, cam_x + vw, cam_y + vh)))
    return view


if __name__ == "__main__":
    L = build_level()
    full = compose_view(L, 0, 0, WORLD_W, WORLD_H)
    full.resize((WORLD_W * 2, WORLD_H * 2), Image.NEAREST).save("level_preview.png")
