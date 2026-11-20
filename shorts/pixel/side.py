"""Side-view (profile) sprites, facing right, built as a puppet from joint angles.

Angles are in degrees measured from straight down; positive swings forward (to the
right). Run cycles and the sword slash are lists of poses, so every character
moves the same way. Mirror an image to face left.
"""
import math

from sprite import Sprite, dots

SW, SH = 46, 48
HIP = (22, 33)
SHOULDER = (22, 23)


def _pt(x, y, ang, length):
    a = math.radians(ang)
    return x + length * math.sin(a), y + length * math.cos(a)


def _limb(s, joint, a1, l1, a2, l2, region, r):
    knee = _pt(*joint, a1, l1)
    end = _pt(*knee, a2, l2)
    s.seg(*joint, *knee, region, r)
    s.seg(*knee, *end, region, r)
    return end


# leg angles (thigh, shin) for near and far legs; arm angles (upper, fore); body lift
RUN = [  # sword carried pointing backward while running
    dict(nl=(40, 15), fl=(-35, -80), na=(-45, -20), fa=(40, 100), up=0, sword=-100),
    dict(nl=(10, -50), fl=(-5, -5), na=(0, 60), fa=(0, 60), up=-1, sword=-100),
    dict(nl=(-35, -80), fl=(40, 15), na=(40, 100), fa=(-45, -20), up=0, sword=-100),
    dict(nl=(-5, -5), fl=(10, -50), na=(0, 60), fa=(0, 60), up=-1, sword=-100),
]
IDLE = dict(nl=(6, 0), fl=(-6, 0), na=(15, 40), fa=(-8, 10), up=0, sword=25)
WALK = [
    dict(nl=(20, 5), fl=(-18, -15), na=(-15, 0), fa=(15, 30), up=0),
    dict(nl=(-18, -15), fl=(20, 5), na=(15, 30), fa=(-15, 0), up=0),
]
STANCE = dict(nl=(25, 5), fl=(-22, -8))
# sword slash: wind-up, raise overhead, swing (with trail), follow-through
SLASH = [
    dict(STANCE, na=(30, 60), fa=(10, 30), sword=150, up=0),
    dict(STANCE, na=(165, 175), fa=(-10, 20), sword=205, up=-1),
    dict(STANCE, na=(80, 95), fa=(20, 40), sword=105, up=0, trail=True),
    dict(STANCE, na=(45, 40), fa=(15, 35), sword=25, up=0),
]


def _legs_and_body(s, pose, look, far_first=True):
    up = pose.get("up", 0)
    hip = (HIP[0], HIP[1] + up)
    sh = (SHOULDER[0], SHOULDER[1] + up)
    return hip, sh


def _foot(s, end, region, length=4):
    x, y = round(end[0]), round(end[1])
    s.rect(x - 1, y - 1, x + length - 1, y + 1, region)


# ---------------------------------------------------------------- Mark
MARK_PAL = {
    "red": ("#c62f3a", "#86202f", "#ef5a4f"),
    "redfar": ("#8e2230", "#6a1824", "#a82a38"),
    "black": ("#2b2635", "#18141f", "#433c52"),
    "blackfar": ("#1e1a26", "#141018", "#2b2635"),
    "skin": ("#e0a46e", "#b97a4c", "#f2c08e"),
    "skinfar": ("#b98a5a", "#9a6e44", "#c89a68"),
    "hair": ("#f05a24", "#b3361a", "#ff8a3d"),
    "boot": ("#7a4a2a", "#4e2e18", "#9a6438"),
    "bootfar": ("#5a361e", "#3e2412", "#6a4426"),
    "steel": ("#cfd8e3", "#8692a6", "#ffffff"),
    "gold": ("#f2b33d", "#b07a1e", "#ffd977"),
}


def mark_side(pose=IDLE, expression="calm"):
    """Optional pose keys: legs=(thigh, shin) lengths, leg_r (thickness), lean (px the upper body leans forward)."""
    s = Sprite(SW, SH)
    thigh, shin = pose.get("legs", (6, 6))
    leg_r = pose.get("leg_r", 1.6)
    lean = pose.get("lean", 0)
    up = pose.get("up", 0) + (12 - thigh - shin)  # shorter legs: lower the body so feet stay on the ground
    hip, sh = (HIP[0], HIP[1] + up), (SHOULDER[0] + 1 + lean, SHOULDER[1] + up)
    # far limbs (darker, behind the body)
    fa = _limb(s, sh, pose["fa"][0], 5, pose["fa"][1], 5, "redfar", 1.3)
    s.rect(round(fa[0]) - 1, round(fa[1]) - 1, round(fa[0]) + 1, round(fa[1]) + 1, "skinfar")
    fl = _limb(s, hip, pose["fl"][0], thigh, pose["fl"][1], shin, "blackfar", leg_r - 0.1)
    _foot(s, fl, "bootfar")
    # torso (leaning: the top shifts forward)
    s.poly([(18 + lean, 21 + up), (27 + lean, 21 + up), (27, 33 + up), (18, 33 + up)], "red")
    s.rect(18, 31 + up, 27, 33 + up, "black")
    # near leg
    nl = _limb(s, hip, pose["nl"][0], thigh, pose["nl"][1], shin, "black", leg_r)
    _foot(s, nl, "boot")
    # head: hood with face opening at the front
    hc = (23 + lean, 13 + up)
    s.ellipse(hc[0], hc[1], 7.5, 7.5, "red")
    s.rect(16 + lean, 6 + up, 18 + lean, 8 + up, "red")  # hood tip at the back
    s.ellipse(hc[0] + 3.5, hc[1] + 1.5, 4.2, 5.2, "skin")
    for x, bottom in zip(range(24 + lean, 31 + lean), (10, 11, 10, 9, 11, 10, 9)):
        for y in range(8 + up, bottom + 1 + up):
            if s.get(x, y) in ("skin", "red"):
                s.g[y][x] = "hair"
    # sword in the near hand, then the near arm over it
    hand = _pt(*_pt(*sh, pose["na"][0], 5), pose["na"][1], 5)
    sword_ang = pose.get("sword", 25)
    tip = _pt(*hand, sword_ang, 15)
    s.seg(*hand, *tip, "steel", 0.9)
    ga, gb = _pt(*hand, sword_ang + 90, 2.5), _pt(*hand, sword_ang - 90, 2.5)
    s.seg(*ga, *gb, "gold", 0.7)
    _limb(s, sh, pose["na"][0], 5, pose["na"][1], 5, "red", 1.4)
    s.rect(round(hand[0]) - 1, round(hand[1]) - 1, round(hand[0]) + 1, round(hand[1]) + 1, "skin")
    img = s.render(MARK_PAL)
    ex, ey = hc[0] + 5, hc[1] - 1
    if expression == "annoyed":
        dots(img, [(ex, ey + 1), (ex + 1, ey + 1), (ex, ey + 2), (ex + 1, ey + 2)], "#261a2e")
        dots(img, [(ex - 1, ey), (ex, ey), (ex + 1, ey)], "#1b1222")
    else:
        dots(img, [(ex, ey), (ex + 1, ey), (ex, ey + 1), (ex + 1, ey + 1), (ex, ey + 2), (ex + 1, ey + 2)], "#261a2e")
        dots(img, [(ex, ey)], "#ffffff")
    dots(img, [(ex - 1, ey + 4), (ex + 1, ey + 4)], "#b9683e")  # freckles
    dots(img, [(ex + 2, ey + 5)], "#7a3a3a")  # mouth
    if pose.get("trail"):
        cx, cy = sh
        for a in range(110, 206, 6):
            x, y = _pt(cx, cy, a, 17)
            dots(img, [(round(x), round(y))], "#eaf6ff")
            x, y = _pt(cx, cy, a + 3, 15)
            dots(img, [(round(x), round(y))], "#9fd8ff")
    return img


# ---------------------------------------------------------------- Sir Reginald
REG_PAL = {
    "steel": ("#c3cbd6", "#7d879a", "#eef3f8"),
    "steelfar": ("#8f97a6", "#666e80", "#a8b0bd"),
    "tabard": ("#2f5fc4", "#1f3f8a", "#4a7ae0"),
    "plume": ("#3a6fd8", "#26489a", "#6a9af0"),
    "skin": ("#e0a46e", "#b97a4c", "#f2c08e"),
    "mustache": ("#8a5426", "#5e3618", "#a8682e"),
    "boot": ("#7a4a2a", "#4e2e18", "#9a6438"),
    "bootfar": ("#5a361e", "#3e2412", "#6a4426"),
    "blade": ("#dfe6ee", "#9aa4b4", "#ffffff"),
    "gold": ("#f2b33d", "#b07a1e", "#ffd977"),
}


def reginald_side(pose=IDLE):
    s = Sprite(SW + 4, SH + 4)
    up = pose.get("up", 0) + 4
    hip, sh = (HIP[0], HIP[1] + up), (SHOULDER[0] + 1, SHOULDER[1] + up)
    fa = _limb(s, sh, pose["fa"][0], 5, pose["fa"][1], 5, "steelfar", 1.5)
    fl = _limb(s, hip, pose["fl"][0], 6, pose["fl"][1], 6, "steelfar", 1.7)
    _foot(s, fl, "bootfar")
    s.rect(17, 21 + up, 28, 33 + up, "steel")
    s.rect(24, 22 + up, 28, 35 + up, "tabard")
    nl = _limb(s, hip, pose["nl"][0], 6, pose["nl"][1], 6, "steel", 1.8)
    _foot(s, nl, "boot")
    hc = (23, 12 + up)
    s.ellipse(hc[0] - 3, hc[1] - 8, 4.5, 3, "plume")
    s.ellipse(hc[0], hc[1], 7.5, 7.5, "steel")
    s.rect(25, 9 + up, 30, 17 + up, "skin")
    s.rect(25, 17 + up, 29, 20 + up, "skin")  # lantern jaw
    s.rect(26, 15 + up, 31, 16 + up, "mustache")
    hand = _pt(*_pt(*sh, pose["na"][0], 5), pose["na"][1], 5)
    tip = _pt(*hand, 160, 18)  # big sword held high, charging
    s.seg(*hand, *tip, "blade", 1.1)
    s.seg(*_pt(*hand, 250, 3), *_pt(*hand, 70, 3), "gold", 0.8)
    _limb(s, sh, pose["na"][0], 5, pose["na"][1], 5, "steel", 1.6)
    img = s.render(REG_PAL)
    dots(img, [(28, 11 + up), (28, 12 + up)], "#2a1a14")
    dots(img, [(27, 10 + up), (28, 10 + up), (29, 10 + up)], "#5e3618")
    dots(img, [(29, 18 + up), (30, 18 + up)], "#3a1620")  # open, shouting mouth
    return img


# ---------------------------------------------------------------- Bumblewick
WIZ_PAL = {
    "hat": ("#3a4fb0", "#26358a", "#5a70d0"),
    "robe": ("#4a5fd0", "#33439a", "#6a80e8"),
    "skin": ("#e0a46e", "#b97a4c", "#f2c08e"),
    "beard": ("#f4f4f4", "#c9cfd8", "#ffffff"),
    "staff": ("#8a5a34", "#5e3a1e", "#a87244"),
    "orb": ("#5ae8ff", "#22a8d0", "#c8f8ff"),
    "boot": ("#7a4a2a", "#4e2e18", "#9a6438"),
}


def bumblewick_side(step=0):
    s = Sprite(SW, SH + 6)
    o = 6
    s.seg(33, 6 + o, 33, 47 + o, "staff", 1.0)
    s.ellipse(33.5, 4 + o, 2.5, 2.5, "orb")
    s.poly([(16, 21 + o), (27, 21 + o), (30, 44 + o), (13, 44 + o)], "robe")
    feet = ((17, 45), (24, 45)) if step == 0 else ((15, 45), (25, 45))
    for fx, fy in feet:
        s.rect(fx, fy + o, fx + 4, fy + 1 + o, "boot")
    s.ellipse(23, 15 + o, 6, 6, "skin")
    s.poly([(10, 4 + o), (16, 8 + o), (28, 11 + o), (17, 12 + o), (12, 10 + o)], "hat")
    s.ellipse(22, 11 + o, 9, 2, "hat")
    s.poly([(21, 17 + o), (30, 17 + o), (29, 27 + o), (25, 33 + o), (22, 26 + o)], "beard")
    s.seg(24, 23 + o, 32, 27 + o, "robe", 1.6)
    s.rect(31, 26 + o, 33, 28 + o, "skin")
    img = s.render(WIZ_PAL)
    dots(img, [(14, 6 + o), (20, 9 + o)], "#ffe04a")
    dots(img, [(26, 13 + o), (27, 13 + o), (28, 13 + o)], "#ffffff")
    dots(img, [(27, 15 + o)], "#2a1a14")
    dots(img, [(29, 16 + o), (30, 17 + o)], "#b97a4c")  # nose
    return img


if __name__ == "__main__":
    import sys

    from PIL import Image

    frames = [mark_side(p) for p in RUN] + [mark_side(p) for p in SLASH] + [mark_side(IDLE, "annoyed")]
    frames += [reginald_side(p) for p in RUN] + [bumblewick_side(0), bumblewick_side(1)]
    scale = 6
    sheet = Image.new("RGBA", (len(frames) * 56 * scale // 1, 60 * scale), "#2a3348")
    for i, f in enumerate(frames):
        big = f.resize((f.width * scale, f.height * scale), Image.NEAREST)
        sheet.alpha_composite(big, (i * 56 * scale // 1, 60 * scale - big.height))
    sheet.save(sys.argv[1] if len(sys.argv) > 1 else "side_sheet.png")
    print("ok")
