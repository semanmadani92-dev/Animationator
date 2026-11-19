"""Fantasy village backdrop for Mark's shorts, drawn at 90x160 pixels (scaled 12x to 1080x1920)."""
import math
import random

from PIL import Image, ImageDraw

SW, SH = 90, 160


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _sky(px):
    bands = ["#3f74d6", "#4f86e0", "#6399ea", "#7aaef2", "#95c4f8", "#b3dafd"]
    band_h = 16
    for y in range(0, 100):
        i = min(y // band_h, len(bands) - 1)
        nxt = min(i + 1, len(bands) - 1)
        for x in range(SW):
            # checker dither in the last 3 rows of each band
            if y % band_h >= band_h - 3 and (x + y) % 2 == 0:
                px[x, y] = _rgb(bands[nxt])
            else:
                px[x, y] = _rgb(bands[i])


def _cloud(d, cx, cy, s):
    for dx, dy, r in ((0, 0, 5), (-6, 2, 4), (6, 2, 4), (-3, -3, 4), (4, -2, 4)):
        d.ellipse([cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s], fill="#ffffff")
    d.rectangle([cx - 9 * s, cy + 3 * s, cx + 9 * s, cy + 5 * s], fill="#d6e6f7")


def _hills(px):
    for x in range(SW):
        far = int(84 + 5 * math.sin(x / 9.0) + 3 * math.sin(x / 4.0 + 1))
        near = int(96 + 4 * math.sin(x / 7.0 + 2))
        for y in range(far, 112):
            px[x, y] = _rgb("#8aa6d8" if y < far + 2 else "#7b97cc")
        for y in range(near, 112):
            px[x, y] = _rgb("#7cc36a" if y < near + 2 else "#5fae58")


def _cottage(d, x0, x1, wall_top, ground, roof, roof_dark, peak_y, window=True, chimney=False):
    if chimney:
        d.rectangle([x1 - 10, peak_y + 4, x1 - 6, wall_top - 4], fill="#8f7a6a", outline="#4a3a30")
    # walls with timber frame
    d.rectangle([x0, wall_top, x1, ground], fill="#f0e2c0")
    d.rectangle([x1 - 3, wall_top, x1, ground], fill="#d9c79f")
    for x in range(x0, x1 + 1, 11):
        d.line([x, wall_top, x, ground], fill="#6b4426")
    d.line([x0, wall_top + 18, x1, wall_top + 18], fill="#6b4426")
    d.line([x0, wall_top, x1, wall_top], fill="#6b4426")
    # roof
    mid = (x0 + x1) / 2
    d.polygon([(x0 - 5, wall_top + 1), (mid, peak_y), (x1 + 5, wall_top + 1)], fill=roof, outline="#2a1a1a")
    for y in range(peak_y + 4, wall_top, 4):
        half = (y - peak_y) / (wall_top - peak_y) * ((x1 - x0) / 2 + 5)
        d.line([mid - half + 1, y, mid + half - 1, y], fill=roof_dark)
    if window:
        wx = x0 + 5
        d.rectangle([wx, wall_top + 5, wx + 8, wall_top + 13], fill="#ffd36b", outline="#4a2c16")
        d.line([wx + 4, wall_top + 5, wx + 4, wall_top + 13], fill="#4a2c16")
        d.line([wx, wall_top + 9, wx + 8, wall_top + 9], fill="#4a2c16")
        d.rectangle([wx - 1, wall_top + 14, wx + 9, wall_top + 15], fill="#7a4a2a")


def _tree(d, cx, base):
    d.rectangle([cx - 1, base - 10, cx + 1, base], fill="#6b4426")
    for dx, dy, r in ((0, -18, 7), (-5, -13, 5), (5, -13, 5)):
        d.ellipse([cx + dx - r, base + dy - r, cx + dx + r, base + dy + r], fill="#3f8f4a")
    d.ellipse([cx - 5, base - 25, cx + 1, base - 19], fill="#5fb35a")


def _path(px, d, rnd):
    for y in range(112, SH):
        for x in range(SW):
            px[x, y] = _rgb("#5fae58" if y < 116 else "#b9aa94")
    # flowers in the grass strip
    for _ in range(14):
        x, y = rnd.randrange(SW), rnd.randrange(112, 116)
        px[x, y] = _rgb(rnd.choice(["#ff6b6b", "#ffd93b", "#ffffff"]))
    # cobblestones
    for row, y in enumerate(range(117, SH, 6)):
        off = (row % 2) * 4
        for x in range(-4 + off, SW, 8):
            w = 6 + rnd.randrange(2)
            d.rounded_rectangle([x, y, x + w, y + 4], radius=1, fill="#c9bba6", outline="#8f826e")
            d.line([x + 1, y + 1, x + w - 2, y + 1], fill="#ddd2bf")


def _lamp(d, x, ground):
    d.rectangle([x, ground - 30, x + 1, ground], fill="#3a3040")
    d.rectangle([x - 2, ground - 35, x + 3, ground - 30], fill="#ffd36b", outline="#3a3040")
    d.line([x - 3, ground - 36, x + 4, ground - 36], fill="#3a3040")


def build_village(seed=7):
    rnd = random.Random(seed)
    img = Image.new("RGB", (SW, SH))
    px = img.load()
    d = ImageDraw.Draw(img)
    _sky(px)
    _cloud(d, 22, 22, 1)
    _cloud(d, 70, 38, 1)
    _hills(px)
    _tree(d, 47, 112)
    _tree(d, 56, 112)
    _cottage(d, 0, 33, 76, 112, "#b44a32", "#8a3424", 54)
    _cottage(d, 62, 92, 80, 112, "#3f6fb5", "#2f548c", 60, chimney=True)
    # door on the left cottage
    d.rectangle([20, 96, 28, 112], fill="#7a4a2a", outline="#4a2c16")
    d.point([26, 104], fill="#f2b33d")
    _lamp(d, 40, 116)
    _path(px, d, rnd)
    return img


if __name__ == "__main__":
    build_village().resize((SW * 6, SH * 6), Image.NEAREST).save("village_preview.png")
