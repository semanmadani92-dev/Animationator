"""Mark: the recurring main character, as a 16-bit pixel sprite (32x40).

Small teen boy, red/black hoodie with the hood up, red hair poking out,
big round eyes, freckles, a sword resting on his shoulder. Cool and calm;
his signature look is annoyed.

Shapes are filled as named regions, then shaded (light from the top left),
outlined, and finished with per-expression face details. Everything is
deterministic, so Mark looks identical in every video.
"""
from PIL import Image

W, H = 32, 40

PALETTE = {
    # region: (base, shade, highlight)
    "red": ("#c62f3a", "#86202f", "#ef5a4f"),
    "hoodin": ("#5e1626", "#4a1020", "#5e1626"),
    "pocket": ("#9e2430", "#6e1824", "#b8303a"),
    "black": ("#2b2635", "#18141f", "#433c52"),
    "skin": ("#e0a46e", "#b97a4c", "#f2c08e"),
    "hair": ("#f05a24", "#b3361a", "#ff8a3d"),
    "string": ("#efe6dc", "#bfb3a6", "#ffffff"),
    "steel": ("#cfd8e3", "#8692a6", "#ffffff"),
    "gold": ("#f2b33d", "#b07a1e", "#ffd977"),
    "grip": ("#6b4426", "#4a2c16", "#8a5a34"),
    "boot": ("#7a4a2a", "#4e2e18", "#9a6438"),
}
OUTLINE = "#1b1222"
EYE = "#261a2e"
IRIS = "#6a4a9a"
BROW = "#7a2a1a"
MOUTH = "#7a3a3a"
FRECKLE = "#b9683e"
ANGER = "#ff3a46"

EXPRESSIONS = ("calm", "annoyed", "surprised", "smirk")


def _blank():
    return [[None] * W for _ in range(H)]


def _ellipse(g, cx, cy, rx, ry, region):
    for y in range(H):
        for x in range(W):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                g[y][x] = region


def _rect(g, x0, y0, x1, y1, region):
    for y in range(max(0, y0), min(H, y1 + 1)):
        for x in range(max(0, x0), min(W, x1 + 1)):
            g[y][x] = region


def _line(g, x0, y0, x1, y1, region, width=1):
    steps = max(abs(x1 - x0), abs(y1 - y0))
    for i in range(steps + 1):
        x = round(x0 + (x1 - x0) * i / steps)
        y = round(y0 + (y1 - y0) * i / steps)
        for k in range(width):
            if 0 <= x + k < W and 0 <= y < H:
                g[y][x + k] = region


def _shapes():
    g = _blank()
    # sword resting on his shoulder (drawn first, body overlaps it)
    _line(g, 24, 26, 29, 11, "steel", width=2)
    _rect(g, 20, 26, 27, 27, "gold")
    _rect(g, 23, 28, 24, 30, "grip")
    _rect(g, 23, 31, 24, 31, "gold")
    # legs and boots
    _rect(g, 11, 31, 14, 35, "black")
    _rect(g, 17, 31, 20, 35, "black")
    _rect(g, 10, 36, 14, 38, "boot")
    _rect(g, 17, 36, 21, 38, "boot")
    # hoodie body with black hem
    _rect(g, 10, 21, 21, 30, "red")
    _rect(g, 10, 29, 21, 30, "black")
    _rect(g, 12, 25, 19, 28, "pocket")
    # arms: left hangs, right grips the sword
    _rect(g, 7, 22, 9, 28, "red")
    _rect(g, 7, 29, 9, 29, "black")
    _rect(g, 7, 30, 9, 31, "skin")
    _rect(g, 22, 22, 24, 26, "red")
    _rect(g, 22, 27, 24, 27, "black")
    _rect(g, 22, 28, 25, 30, "skin")
    # hood, dark inner hood, face
    _ellipse(g, 15.5, 12, 9.5, 9, "red")
    _rect(g, 14, 2, 17, 3, "red")
    _ellipse(g, 15.5, 13.5, 7.5, 7, "hoodin")
    _ellipse(g, 15.5, 14.5, 6.5, 6, "skin")
    # red hair: spiky fringe plus tufts at the sides of the hood
    fringe_bottom = [10, 11, 10, 9, 10, 11, 11, 10, 9, 10, 11, 10, 9, 10]
    for i, bottom in enumerate(fringe_bottom):
        x = 9 + i
        for y in range(7, bottom + 1):
            if g[y][x] in ("skin", "hoodin"):
                g[y][x] = "hair"
    for x, y0, y1 in ((8, 11, 15), (9, 15, 16), (23, 11, 15), (22, 15, 16)):
        _rect(g, x, y0, x, y1, "hair")
    # drawstrings
    _rect(g, 13, 21, 13, 24, "string")
    _rect(g, 18, 21, 18, 24, "string")
    return g


def _shade(g):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()

    def same(x, y, r):
        return 0 <= x < W and 0 <= y < H and g[y][x] == r

    for y in range(H):
        for x in range(W):
            r = g[y][x]
            if r is None:
                continue
            base, shade, hi = PALETTE[r]
            if not same(x + 1, y, r) or not same(x + 2, y, r) or not same(x, y + 1, r):
                c = shade
            elif not same(x - 1, y, r) or not same(x, y - 1, r):
                c = hi
            else:
                c = base
            px[x, y] = _rgba(c)
    # 1px dark outline around the silhouette
    filled = [[g[y][x] is not None for x in range(W)] for y in range(H)]
    for y in range(H):
        for x in range(W):
            if filled[y][x]:
                continue
            if any(0 <= x + dx < W and 0 <= y + dy < H and filled[y + dy][x + dx]
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[x, y] = _rgba(OUTLINE)
    return img


def _rgba(hex_color):
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def _face(img, expression):
    px = img.load()

    def put(x, y, c):
        px[x, y] = _rgba(c)

    # skin under the eye/brow area first, so the hair fringe never hides the face
    for x in range(10, 22):
        put(x, 12, PALETTE["skin"][0]) if expression != "surprised" else None
    eyes = ((11, 13), (18, 20))
    for x0, x1 in eyes:
        top = 14 if expression == "annoyed" else 13
        for x in range(x0, x1 + 1):
            for y in range(top, 17):
                put(x, y, EYE)
        put(x0 + 1, 16, IRIS)
        put(x0 + 2, 16, IRIS)
        put(x0, top, "#ffffff")  # highlight
        if expression == "annoyed":
            for x in range(x0, x1 + 1):  # heavy flat eyelid
                put(x, 13, OUTLINE)
        if expression == "surprised":
            put(x0 + 1, 14, EYE)
            put(x0 + 2, 13, "#ffffff")

    brows = {
        "calm": [(11, 12), (12, 12), (19, 12), (20, 12)],
        "annoyed": [(11, 11), (12, 12), (13, 12), (18, 12), (19, 12), (20, 11)],
        "surprised": [(11, 11), (12, 11), (19, 11), (20, 11)],
        "smirk": [(11, 12), (12, 12), (19, 11), (20, 11)],
    }[expression]
    for x, y in brows:
        put(x, y, BROW)

    for x, y in ((10, 17), (12, 18), (11, 18), (19, 18), (20, 18), (21, 17)):
        put(x, y, FRECKLE)

    mouth = {
        "calm": [(15, 18), (16, 18)],
        "annoyed": [(14, 19), (15, 18), (16, 18), (17, 18)],
        "surprised": [(15, 18), (16, 18), (15, 19), (16, 19)],
        "smirk": [(14, 18), (15, 18), (16, 18), (17, 17)],
    }[expression]
    for x, y in mouth:
        put(x, y, MOUTH)

    if expression == "annoyed":
        # anime anger mark floating by his head
        mark = ((27, 1), (29, 1), (26, 2), (27, 2), (29, 2), (30, 2),
                (26, 4), (27, 4), (29, 4), (30, 4), (27, 5), (29, 5))
        for x, y in mark:
            put(x, y, ANGER)
    return img


def build_mark(expression="calm"):
    if expression not in EXPRESSIONS:
        raise ValueError(f"expression must be one of {EXPRESSIONS}")
    return _face(_shade(_shapes()), expression)


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "mark_sheet.png"
    scale = 8
    sheet = Image.new("RGBA", (W * scale * 4 + 50, H * scale + 20), "#2a3348")
    for i, e in enumerate(EXPRESSIONS):
        sprite = build_mark(e).resize((W * scale, H * scale), Image.NEAREST)
        sheet.alpha_composite(sprite, (10 + i * (W * scale + 10), 10))
    sheet.save(out)
    print("saved", out)
