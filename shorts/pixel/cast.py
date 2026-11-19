"""Supporting cast sprites (16-bit, original designs).

Each builder returns an RGBA image; `talk=True` gives the open-mouth frame used
for lip flap while a character speaks.
"""
from sprite import Sprite, dots

STEEL = ("#c3cbd6", "#7d879a", "#eef3f8")
SKIN = ("#e0a46e", "#b97a4c", "#f2c08e")
GOLD = ("#f2b33d", "#b07a1e", "#ffd977")
BROWN = ("#7a4a2a", "#4e2e18", "#9a6438")
DARK_MOUTH = "#3a1620"


# ---------------- Sir Reginald: the overdramatic knight ----------------
def reginald(expression="proud", talk=False):
    s = Sprite(34, 44)
    pal = {
        "steel": STEEL, "skin": SKIN, "gold": GOLD, "boot": BROWN,
        "plume": ("#3a6fd8", "#26489a", "#6a9af0"),
        "visor": ("#8a93a6", "#5d6578", "#a9b1c2"),
        "tabard": ("#2f5fc4", "#1f3f8a", "#4a7ae0"),
        "mustache": ("#8a5426", "#5e3618", "#a8682e"),
        "grip": ("#6b4426", "#4a2c16", "#8a5a34"),
        "blade": ("#dfe6ee", "#9aa4b4", "#ffffff"),
    }
    # big sword held upright
    s.line(27, 4, 27, 29, "blade", width=2)
    s.rect(24, 30, 31, 30, "gold")
    s.rect(27, 31, 28, 33, "grip")
    # plume and helmet
    s.ellipse(16, 4.5, 3.5, 4, "plume")
    s.ellipse(16, 13.5, 8.5, 8.5, "steel")
    s.rect(10, 8, 21, 10, "visor")
    s.rect(11, 11, 20, 19, "skin")
    s.rect(12, 19, 19, 21, "skin")  # lantern jaw
    # body
    s.ellipse(7.5, 23.5, 3.5, 2.5, "steel")
    s.ellipse(24.5, 23.5, 3.5, 2.5, "steel")
    s.rect(9, 22, 22, 33, "steel")
    s.rect(11, 23, 20, 35, "tabard")
    s.ellipse(15.5, 27.5, 2.5, 2.5, "gold")
    s.rect(9, 33, 22, 33, "boot")
    s.rect(5, 24, 7, 31, "steel")
    s.rect(24, 24, 26, 31, "steel")
    s.rect(10, 36, 14, 39, "steel")
    s.rect(17, 36, 21, 39, "steel")
    s.rect(9, 40, 14, 42, "boot")
    s.rect(17, 40, 22, 42, "boot")
    # mustache with curled ends
    s.rect(12, 16, 19, 17, "mustache")
    s.rect(11, 15, 11, 16, "mustache")
    s.rect(20, 15, 20, 16, "mustache")
    img = s.render(pal)
    ink = "#2a1a14"
    if expression == "proud":
        dots(img, [(13, 13), (14, 12), (15, 13), (17, 13), (18, 12), (19, 13)], ink)  # ^ ^ eyes
    else:
        dots(img, [(13, 12), (14, 12), (13, 13), (14, 13), (17, 12), (18, 12), (17, 13), (18, 13)], ink)
        if expression == "shocked":
            dots(img, [(13, 12), (17, 12)], "#ffffff")
    dots(img, [(12, 11), (13, 11), (14, 11), (17, 11), (18, 11), (19, 11)], "#5e3618")  # brows
    mouth = [(14, 18), (15, 18), (16, 18), (17, 18)]
    if talk or expression == "shocked":
        mouth += [(14, 19), (15, 19), (16, 19), (17, 19)]
    dots(img, mouth, DARK_MOUTH)
    return img


# ---------------- Lord Vexmore: the monologuing villain ----------------
def vexmore(expression="smug", talk=False):
    s = Sprite(36, 46)
    pal = {
        "cape": ("#5a2a7a", "#3a1652", "#7a3ea0"),
        "metal": ("#3a3346", "#221d2c", "#57506a"),
        "shadow": ("#120d1a", "#120d1a", "#120d1a"),
        "horn": ("#e8dcc0", "#b0a284", "#fff6e0"),
        "gem": ("#ff3ad0", "#b01e90", "#ff8ae8"),
    }
    s.poly([(6, 19), (29, 19), (34, 45), (1, 45)], "cape")
    # thick curved horns: wide at the helmet, curling up to a point
    s.poly([(9, 11), (13, 7), (9, 4), (6, 0), (5, 5)], "horn")
    s.poly([(26, 11), (22, 7), (26, 4), (29, 0), (30, 5)], "horn")
    s.ellipse(17.5, 12.5, 7.5, 7.5, "metal")
    s.rect(13, 10, 22, 17, "shadow")
    s.rect(8, 17, 10, 20, "cape")
    s.rect(25, 17, 27, 20, "cape")
    s.rect(11, 20, 24, 34, "metal")
    s.rect(16, 25, 19, 26, "gem")
    s.rect(7, 21, 10, 31, "metal")
    s.rect(25, 21, 28, 31, "metal")
    s.rect(12, 35, 16, 42, "metal")
    s.rect(19, 35, 23, 42, "metal")
    s.rect(11, 43, 16, 45, "shadow")
    s.rect(19, 43, 24, 45, "shadow")
    img = s.render(pal, flat=("shadow",))
    eye = "#ff3040"
    if expression == "shocked":
        dots(img, [(14, 12), (15, 12), (14, 13), (15, 13), (20, 12), (21, 12), (20, 13), (21, 13)], eye)
    else:  # smug: narrow slanted glow
        dots(img, [(14, 12), (15, 13), (16, 13), (19, 13), (20, 13), (21, 12)], eye)
    if talk or expression == "shocked":
        dots(img, [(16, 15), (17, 15), (18, 15), (19, 15), (17, 16), (18, 16)], "#ffffff")
    else:
        dots(img, [(16, 15), (19, 15)], "#d8d0e0")  # grin corners
    return img


# ---------------- Bumblewick: the confused old wizard ----------------
def bumblewick(expression="confused", talk=False):
    s = Sprite(36, 50)
    pal = {
        "hat": ("#3a4fb0", "#26358a", "#5a70d0"),
        "robe": ("#4a5fd0", "#33439a", "#6a80e8"),
        "skin": SKIN,
        "beard": ("#f4f4f4", "#c9cfd8", "#ffffff"),
        "staff": ("#8a5a34", "#5e3a1e", "#a87244"),
        "orb": ("#5ae8ff", "#22a8d0", "#c8f8ff"),
        "boot": BROWN,
    }
    s.line(29, 10, 29, 47, "staff", width=2)
    s.ellipse(30, 7.5, 3, 3, "orb")
    s.poly([(8, 17), (26, 17), (21, 6), (24, 1), (17, 4)], "hat")
    s.ellipse(17, 17, 11, 2.2, "hat")
    s.rect(12, 18, 22, 23, "skin")
    s.poly([(9, 25), (25, 25), (28, 47), (6, 47)], "robe")
    s.poly([(11, 22), (23, 22), (21, 34), (17, 40), (13, 34)], "beard")
    s.rect(26, 28, 28, 30, "skin")
    s.rect(10, 48, 15, 49, "boot")
    s.rect(19, 48, 24, 49, "boot")
    img = s.render(pal)
    dots(img, [(13, 10), (19, 13), (15, 7), (22, 9)], "#ffe04a")  # hat stars
    dots(img, [(12, 18), (13, 18), (14, 18), (19, 18), (20, 18), (21, 18)], "#ffffff")  # bushy brows
    if expression == "confused":
        dots(img, [(19, 17), (20, 17)], "#ffffff")  # one brow raised
        dots(img, [(30, 14), (31, 14), (32, 15), (31, 16), (31, 18)], "#ffe04a")  # "?" mark
    dots(img, [(14, 20), (20, 20)], "#2a1a14")
    dots(img, [(17, 21), (17, 22)], SKIN[1])  # nose
    if talk:
        dots(img, [(16, 25), (17, 25), (18, 25), (17, 26)], DARK_MOUTH)
    return img


# ---------------- Grub: the panicky goblin minion ----------------
def grub(expression="sneaky", talk=False):
    s = Sprite(26, 30)
    pal = {
        "green": ("#6ab43c", "#48862a", "#8ad25a"),
        "rag": ("#7a5a3a", "#54391f", "#9a7450"),
        "blade": ("#c9d1dc", "#8a94a6", "#ffffff"),
    }
    s.line(21, 13, 21, 19, "blade")
    s.poly([(2, 5), (7, 8), (6, 12)], "green")
    s.poly([(24, 5), (19, 8), (20, 12)], "green")
    s.ellipse(13, 11, 7, 6.5, "green")
    s.poly([(7, 18), (19, 18), (20, 25), (17, 24), (15, 25), (12, 24), (9, 25), (6, 25)], "rag")
    s.rect(4, 18, 6, 22, "green")
    s.rect(19, 18, 21, 22, "green")
    s.rect(8, 25, 10, 27, "green")
    s.rect(15, 25, 17, 27, "green")
    s.rect(7, 28, 10, 29, "rag")
    s.rect(15, 28, 18, 29, "rag")
    img = s.render(pal)
    big = expression == "panic"
    for x in (9, 15):
        eye = [(x, 9), (x + 1, 9), (x, 10), (x + 1, 10)] + ([(x, 8), (x + 1, 8)] if big else [])
        dots(img, eye, "#ffe04a")
        dots(img, [(x + 1, 10)], "#120d1a")
    dots(img, [(12, 12), (13, 12)], "#48862a")
    if talk or big:
        dots(img, [(10, 14), (11, 14), (12, 14), (13, 14), (14, 14), (15, 14), (11, 15), (12, 15), (13, 15), (14, 15)], DARK_MOUTH)
        dots(img, [(11, 14), (14, 14)], "#ffffff")  # fangs
    else:
        dots(img, [(10, 14), (11, 15), (12, 15), (13, 15), (14, 15), (15, 14)], DARK_MOUTH)
        dots(img, [(11, 15)], "#ffffff")
    if big:
        dots(img, [(20, 6), (20, 7), (21, 8)], "#6ac8ff")  # sweat drop
    return img


BUILDERS = {"reginald": reginald, "vexmore": vexmore, "bumblewick": bumblewick, "grub": grub}

if __name__ == "__main__":
    import sys

    from PIL import Image

    out = sys.argv[1] if len(sys.argv) > 1 else "cast_sheet.png"
    variants = [("reginald", "proud", False), ("reginald", "shout", True), ("vexmore", "smug", False),
                ("vexmore", "shocked", True), ("bumblewick", "confused", False), ("bumblewick", "calm", True),
                ("grub", "sneaky", False), ("grub", "panic", True)]
    scale = 6
    sheet = Image.new("RGBA", (len(variants) * 40 * scale // 1 + 20, 52 * scale), "#2a3348")
    for i, (name, expr, talk) in enumerate(variants):
        im = BUILDERS[name](expr, talk)
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        sheet.alpha_composite(im, (10 + i * 40 * scale, 52 * scale - im.height - 6))
    sheet.save(out)
    print("saved", out)
