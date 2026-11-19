"""Cliffs and a rope bridge over a chasm (180x160 logical pixels, camera pans across it).

The backdrop is static; the bridge is drawn per frame so it can be cut at the
left post and swing down, hanging from the right cliff.
"""
import math
import random

from PIL import Image, ImageDraw

BW, BH = 180, 160
LEFT_POST, RIGHT_POST, DECK_Y = 60, 120, 104
SAG = 6


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def deck_y(x):
    """Deck height of the intact bridge at x (sags in the middle)."""
    mid, half = (LEFT_POST + RIGHT_POST) / 2, (RIGHT_POST - LEFT_POST) / 2
    return DECK_Y + SAG * (1 - ((x - mid) / half) ** 2)


def build_backdrop(seed=3):
    rnd = random.Random(seed)
    img = Image.new("RGB", (BW, BH))
    px = img.load()
    d = ImageDraw.Draw(img)
    bands = ["#3f74d6", "#4f86e0", "#6399ea", "#7aaef2", "#95c4f8", "#b3dafd"]
    for y in range(BH):
        i = min(y // 16, len(bands) - 1)
        nxt = min(i + 1, len(bands) - 1)
        for x in range(BW):
            px[x, y] = _rgb(bands[nxt] if y % 16 >= 13 and (x + y) % 2 == 0 else bands[i])
    # clouds
    for cx, cy in ((25, 24), (95, 14), (150, 34)):
        for dx, dy, r in ((0, 0, 5), (-6, 2, 4), (6, 2, 4), (-3, -3, 4), (4, -2, 4)):
            d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill="#ffffff")
        d.rectangle([cx - 9, cy + 3, cx + 9, cy + 5], fill="#d6e6f7")
    # distant mountains
    pts = [(0, 100)]
    for x in range(0, BW + 1, 6):
        pts.append((x, 62 + int(14 * abs(math.sin(x / 23.0))) + rnd.randrange(4)))
    pts.append((BW, 100))
    d.polygon(pts, fill="#7f8fc8")
    d.line(pts[1:-1], fill="#a8b4e0")  # lit ridge line
    # chasm: darkening walls between the cliffs
    for y in range(DECK_Y, BH):
        t = (y - DECK_Y) / (BH - DECK_Y)
        c = tuple(int(a + (b - a) * t) for a, b in zip(_rgb("#5a6aa8"), _rgb("#140f24")))
        d.line([LEFT_POST - 6, y, RIGHT_POST + 6, y], fill=c)
    for _ in range(40):  # mist specks
        x, y = rnd.randrange(LEFT_POST, RIGHT_POST), rnd.randrange(110, 140)
        px[x, y] = _rgb("#8a96c8")
    # cliffs: solid rock with a jagged inner edge, grass on top
    def cliff(x0, x1, inner_x, facing):
        d.rectangle([x0, DECK_Y, x1, BH], fill="#7a6a5a")
        for y in range(DECK_Y + 3, BH, 3):
            jag = rnd.randrange(0, 4)
            if facing < 0:  # left cliff, edge on its right side
                d.rectangle([inner_x - jag, y, inner_x, y + 2], fill="#4a3f36")
            else:
                d.rectangle([inner_x, y, inner_x + jag, y + 2], fill="#4a3f36")
        for _ in range(70):
            rx = rnd.randrange(x0, x1)
            ry = rnd.randrange(DECK_Y + 4, BH)
            d.rectangle([rx, ry, rx + 2, ry + 1], fill=rnd.choice(["#665848", "#8e7c6a", "#5a4d40"]))
        d.rectangle([x0, DECK_Y, x1, DECK_Y + 2], fill="#5fae58")
        d.rectangle([x0, DECK_Y - 1, x1, DECK_Y - 1], fill="#7cc36a")
    cliff(0, LEFT_POST, LEFT_POST, -1)
    cliff(RIGHT_POST, BW - 1, RIGHT_POST, 1)
    # small grass tufts and flowers on top
    for _ in range(18):
        x = rnd.choice([rnd.randrange(0, LEFT_POST - 2), rnd.randrange(RIGHT_POST + 2, BW)])
        px[x, DECK_Y - 2] = _rgb(rnd.choice(["#5fae58", "#ff6b6b", "#ffd93b"]))
    return img


def draw_bridge(img, cut_t=None):
    """Draw the rope bridge onto img. cut_t: seconds since the left rope was cut (None = intact)."""
    d = ImageDraw.Draw(img)
    rope, rope_dark = "#8a6a3a", "#5a4020"
    plank, plank_dark = "#a8743e", "#7a4e26"
    for x in (LEFT_POST, RIGHT_POST):  # posts
        d.rectangle([x - 1, DECK_Y - 12, x, DECK_Y], fill="#6b4426", outline="#3a2414")
    if cut_t is None:
        for x in range(LEFT_POST + 1, RIGHT_POST, 3):
            y = round(deck_y(x))
            d.rectangle([x, y, x + 1, y + 1], fill=plank if (x // 3) % 2 else plank_dark)
        prev = None
        for x in range(LEFT_POST, RIGHT_POST + 1):
            pt = (x, round(deck_y(x)) + 2)
            top = (x, round(DECK_Y - 10 + SAG * 0.6 * (1 - ((x - 90) / 30) ** 2)))
            if prev:
                d.line([prev[0], pt], fill=rope_dark)
                d.line([prev[1], top], fill=rope)
            if x % 6 == 0:
                d.line([top, (x, pt[1] - 2)], fill=rope)
            prev = (pt, top)
        d.line([(LEFT_POST, DECK_Y - 12), (LEFT_POST, DECK_Y - 10)], fill=rope)
        return
    # cut: the bridge swings down, hanging from the right post
    theta = swing_angle(cut_t)
    length = RIGHT_POST - LEFT_POST
    prev = None
    for i in range(0, length + 1):
        dist = i
        bend = 0.08 * dist * math.sin(theta * 2)  # slight curve while swinging
        x = RIGHT_POST - dist * math.cos(theta) + bend * math.sin(theta)
        y = DECK_Y + dist * math.sin(theta) + bend * math.cos(theta) * 0.2
        if i % 3 == 0:
            d.rectangle([round(x), round(y), round(x) + 1, round(y) + 1], fill=plank if (i // 3) % 2 else plank_dark)
        if prev:
            d.line([prev, (round(x), round(y) + 2)], fill=rope_dark)
        prev = (round(x), round(y) + 2)
    # the cut rope end left dangling on the left post
    d.line([(LEFT_POST, DECK_Y - 10), (LEFT_POST + 2, DECK_Y - 4)], fill=rope)


def swing_angle(t):
    """Angle of the falling bridge: drops under gravity, overshoots, settles hanging straight down."""
    if t < 0.7:
        return (math.pi / 2) * (t / 0.7) ** 2
    damp = math.exp(-(t - 0.7) * 3.0)
    return math.pi / 2 - 0.25 * damp * math.sin((t - 0.7) * 9)
