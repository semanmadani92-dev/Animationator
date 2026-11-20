"""Render episode 1, "The Pie": 1080x1920 at 24 fps.

Grub steals the baker's pie and hides up a tall oak. Reginald tries to climb it, Bumblewick's spell
floats Reginald instead, and Mark cuts the tree down.

Usage: python render_ep01.py <audio_dir> <timings.json> <out.mp4>
audio_dir: one WAV per script line id (24 kHz mono), sfx_*.wav from sfx.py, and sfx_jingle.wav.
"""
import json
import math
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pixel"))
sys.path.insert(0, str(ROOT / "pipeline"))
from camera import ASPECT, OUT_H, OUT_W, Canvas, Spring  # noqa: E402
from cast import BUILDERS  # noqa: E402
from chiptune import chiptune  # noqa: E402
from gait import SKID, VMAX, VWALK, Trip, pose, smooth, speed_blend, stride  # noqa: E402
from level import GROUND, build_level  # noqa: E402
from mark import build_mark  # noqa: E402
from props import CANOPY, CUT, GRUB_PERCH, OAK_BASE, OAK_H, oak, pie, stump_top  # noqa: E402
from render_bridge import caption_chunks, draw_banner, draw_caption, rms_normalise  # noqa: E402
from run_options import DASH, foot_speed  # noqa: E402
from side import IDLE, SLASH, bumblewick_side, mark_side, reginald_side  # noqa: E402

FPS, SR = 24, 24000
SCRIPT = json.load(open(ROOT / "episodes" / "ep01_pie" / "script.json"))
GA = 0.68  # ground line sits 68% down the view, so captions sit below everyone's feet
WIDE, MED, CLOSE, FAR = 135, 90, 72, 180  # view widths (art pixels)
G = 400.0  # gravity, px/s^2

# world positions
MARK_START, MARK_STOP, MARK_CHOP = 70, 300, 316
REG_START, REG_STOP, REG_TREE, REG_FLOAT = 46, 282, 326, 320
WIZ_VILLAGE, WIZ_FROM, WIZ_X = 24, 212, 262
TREE_X = 336
PIVOT = (TREE_X, GROUND + 1 - CUT)  # where the trunk is cut
GRUB_LAND = 418
REG_V = foot_speed(DASH)  # Reginald's run, 12 poses/s, feet planted
FLOAT_H = 64


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * k * (k * (k * 6 - 15) + 10)  # smootherstep: gentle start and finish


def lerp(a, b, k):
    return a + (b - a) * k


def view_at(cx, vw, feet=GROUND, frac=GA):
    """Camera (left, top, width) that centres cx and puts the `feet` line `frac` of the way down."""
    return (cx - vw / 2, feet - frac * vw * ASPECT, vw)


def rot(p, deg):
    a = math.radians(deg)
    return p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a)


# ---------------------------------------------------------------- tree physics
def simulate_fall():
    """Angle (deg) of the falling oak against time, a rod pivoting at its base, until the crown hits."""
    th, w, t, dt, k = 0.03, 0.0, 0.0, 1 / 480, 8.5
    out = []

    def lowest(deg):  # lowest point of the crown, relative to the pivot
        return max(rot((cx - OAK_BASE[0], cy - (OAK_H - CUT)), deg)[1] + r for cx, cy, r in CANOPY)

    while lowest(math.degrees(th)) < CUT - 1:
        w += k * math.sin(th) * dt
        th += w * dt
        t += dt
        out.append((t, math.degrees(th)))
    t_land, land = t, math.degrees(th)
    for i in range(1, int(0.5 / dt)):  # small rebound, then rest
        tt = i * dt
        out.append((t_land + tt, land - 5 * math.sin(tt * 18) * math.exp(-tt * 9)))
    return out, t_land, land


# ---------------------------------------------------------------- timeline
def word_start(timings, line_id, i):
    return timings[line_id]["words"][i]["start"]


def build_timeline(audio, timings, fall, t_fall_land):
    d = {i: len(a) / SR for i, a in audio.items()}
    T = {"01_narrator": 0.5, "walk": 1.0, "dash": 1.8, "reg_run": 2.1}
    trip = Trip(MARK_START, MARK_STOP, T["walk"], T["dash"])
    T["arrive"] = trip.t_stop
    T["reveal"] = T["arrive"] + 0.45
    T["02_grub"] = T["reveal"] + 0.75
    T["03_reginald"] = T["02_grub"] + d["02_grub"] + 0.35
    T["climb"] = T["03_reginald"] + d["03_reginald"] + 0.25
    T["hops"] = [T["climb"] + 0.45 + 0.28 * i for i in range(4)]
    T["slide"] = T["hops"][-1] + 0.55
    T["back"] = T["slide"] + 0.25  # lands on his back
    T["getup"] = T["back"] + 0.9
    T["wiz_enter"] = T["back"] - 0.3
    T["wiz_stop"] = T["wiz_enter"] + 1.6
    T["04_bumblewick"] = T["wiz_stop"] + 0.1
    T["spell"] = T["04_bumblewick"] + d["04_bumblewick"] + 0.1
    T["05_reginald"] = T["spell"] + 1.1
    T["06_mark"] = T["05_reginald"] + d["05_reginald"] + 0.35
    T["slash"] = T["06_mark"] + d["06_mark"] + 0.1
    T["chop"] = T["slash"] + 0.32
    T["fall"] = T["chop"] + 0.5
    t45 = next(t for t, a in fall if a >= 45)
    T["release"] = T["fall"] + t45
    T["07_grub"] = T["release"] - word_start(timings, "07_grub", 0)  # screams as he's flung
    T["grub_land"] = T["release"] + 0.8
    T["07b_grub"] = T["grub_land"] - word_start(timings, "07b_grub", 0)  # "OW!" as he lands
    T["tree_land"] = T["fall"] + t_fall_land
    T["catch"] = T["release"] + 1.0
    T["08_mark"] = max(T["07b_grub"] + d["07b_grub"], T["catch"]) + 0.35
    T["drop"] = T["08_mark"] + d["08_mark"] + 0.3
    T["drop_land"] = T["drop"] + math.sqrt(2 * FLOAT_H / G)
    T["09_reginald"] = T["drop_land"] + 0.3
    T["leave"] = T["09_reginald"] + d["09_reginald"] + 0.3
    T["10_mark"] = T["leave"] + 0.15
    T["11_narrator"] = T["10_mark"] + d["10_mark"] + 0.45
    T["complete"] = T["11_narrator"] + d["11_narrator"] - 0.2
    T["end"] = T["complete"] + 2.4
    # the moment the dash kicks in (for the whoosh and the dust burst)
    T["kick"] = next(T["walk"] + i * trip.dt for i, s in enumerate(trip.samples) if s[2] > 60)
    T["skid"] = trip.t_skid
    return T, d, trip


def mix_audio(T, audio, audio_dir, out_wav):
    n = int(T["end"] * SR)
    mix = np.zeros(n)

    def add(y, at, gain=1.0):
        s = int(at * SR)
        if 0 <= s < n:
            mix[s:s + y.size] += (y * gain)[: n - s]

    for i, y in audio.items():
        add(rms_normalise(y.astype(np.float64)), T[i])
    sfx = {p.stem[4:]: sf.read(p)[0] for p in audio_dir.glob("sfx_*.wav")}
    add(sfx["whoosh"], T["kick"], 1.0)
    add(sfx["skid"], T["skid"], 1.0)
    for h in T["hops"]:
        add(sfx["clank"], h, 0.6)
    add(sfx["skid"][: int(0.25 * SR)], T["slide"], 0.8)
    add(sfx["thud"], T["back"], 0.45)
    add(sfx["clank"], T["back"], 0.5)
    add(sfx["magic"], T["spell"], 0.9)
    add(sfx["chop"], T["chop"], 1.3)
    add(sfx["creak"], T["chop"] + 0.15, 0.8)
    add(sfx["thud"], T["tree_land"], 1.1)
    add(sfx["boing"], T["grub_land"], 0.7)
    add(sfx["pop"], T["catch"], 0.8)
    add(sfx["thud"], T["drop_land"], 0.6)
    add(sfx["clank"], T["drop_land"], 0.7)
    add(sfx["jingle"], T["complete"], 1.0)
    t = np.arange(n) / SR
    env = np.ones(n)
    env[(t >= T["chop"]) & (t < T["tree_land"] + 0.4)] = 0.0  # comic silence while the tree goes
    back = (t >= T["tree_land"] + 0.4) & (t < T["tree_land"] + 1.4)
    env[back] = t[back] - (T["tree_land"] + 0.4)
    env[t >= T["complete"]] = 0.0
    mix += chiptune(T["end"]) * 0.05 * env
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    sf.write(out_wav, mix.astype(np.float32), SR)


def build_captions(T, d, words):
    caps = []
    for line in SCRIPT["lines"]:
        chunks = caption_chunks(line, words[line["id"]])
        for k, ch in enumerate(chunks):
            end = chunks[k + 1][0][1] if k + 1 < len(chunks) else T[line["id"]] + d[line["id"]] + 0.25
            caps.append((ch[0][1], end, line["speaker"], [w[0] for w in ch]))
    caps.sort()
    return [(a, min(b, caps[i + 1][0]) if i + 1 < len(caps) else b, *rest) for i, (a, b, *rest) in enumerate(caps)]


# ---------------------------------------------------------------- the episode
def front(name, expr, talk=False):
    return build_mark(expr, talk) if name == "mark" else BUILDERS[name](expr, talk)


def flip(img):
    return img.transpose(Image.FLIP_LEFT_RIGHT)


class Episode:
    def __init__(self, T, trip, fall, fall_land, words_by_speaker):
        self.T, self.trip, self.words = T, trip, words_by_speaker
        self.fall, self.fall_land = fall, fall_land
        self.L = build_level(forest=((272, 58), (390, 66), (420, 46)), bushes=(286, 372, 405))
        self.tree, stump = oak()
        self.stump, self.stump_cut = stump, stump_top(stump)
        self.pie = pie()
        self.reg_run = [reginald_side(p) for p in DASH]
        self.slash = [mark_side(p) for p in SLASH]
        self.mark_idle = mark_side(IDLE, "annoyed")
        self.skid = mark_side(SKID)
        self.wiz_walk = [bumblewick_side(0), bumblewick_side(1)]
        self._rot = {}
        self.cam_x = Spring(MARK_START - 0.42 * WIDE, 5.0)
        self.cam_w = Spring(WIDE, 3.2)
        self.cam_hold = None
        self.puffs = []  # (born, x, y, kind)
        self.last_puff = -1.0
        self.kicked = False

    # ---- helpers
    def talk(self, speaker, t):
        return any(a <= t <= b for _, a, b in self.words.get(speaker, [])) and int(t * 8) % 2 == 0

    def angle(self, t):
        if t < self.T["fall"]:
            return 0.0
        dt = t - self.T["fall"]
        for tt, a in self.fall:
            if tt >= dt:
                return a
        return self.fall[-1][1]

    def rotated_tree(self, deg):
        key = round(deg * 2) / 2
        if key not in self._rot:
            R = OAK_H
            sq = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
            sq.alpha_composite(self.tree, (R - OAK_BASE[0], R - (OAK_H - CUT)))
            self._rot[key] = sq.rotate(-key, resample=Image.NEAREST, center=(R, R))
        return self._rot[key]

    def perch(self, t):
        """World position of Grub's feet on the branch (moves with the falling tree)."""
        rel = (GRUB_PERCH[0], GRUB_PERCH[1] + CUT)
        rx, ry = rot(rel, self.angle(t))
        return PIVOT[0] + rx, PIVOT[1] + ry

    def grub_pos(self, t):
        T = self.T
        if t < T["release"]:
            x, y = self.perch(t)
            return x, y, "perch"
        x0, y0 = self.perch(T["release"])
        tf = T["grub_land"] - T["release"]
        if t >= T["grub_land"]:
            return GRUB_LAND, GROUND - 1, "landed"
        k = t - T["release"]
        vx = (GRUB_LAND - x0) / tf
        vy = (GROUND - 1 - y0 - 0.5 * G * tf * tf) / tf
        return x0 + vx * k, y0 + vy * k + 0.5 * G * k * k, "fly"

    def mark_hand(self, mx, feet):
        return mx - 18 + 8, feet - 39 + 26  # front sprite's left hand

    def pie_pos(self, t):
        T = self.T
        if t < T["release"]:
            gx, gy, _ = self.grub_pos(t)
            return gx, gy - 29 + 21 - (self.bob(t, 0.7) if t < T["chop"] else 0)
        hx, hy = self.mark_hand(MARK_CHOP, GROUND - 1)
        if t >= T["catch"]:
            return None
        x0, y0 = self.pie_pos(T["release"] - 1e-6)
        tf, k = T["catch"] - T["release"], t - T["release"]
        vx, vy = (hx - x0) / tf, (hy - y0 - 0.5 * G * tf * tf) / tf
        return x0 + vx * k, y0 + vy * k + 0.5 * G * k * k

    @staticmethod
    def bob(t, phase):
        return int(t * 2 + phase) % 2

    # ---- camera
    def camera(self, t):
        T = self.T
        if t < T["reveal"]:  # follow the dash: glide, zoom out with speed, lead ahead of him
            mx, v, _, _ = self.trip.at(t)
            k = v / VMAX
            vw = self.cam_w.step(WIDE + (FAR - WIDE) * k, 1 / FPS)
            lead = 0.42 - 0.14 * k
            target = mx - lead * vw + 2 * v / self.cam_x.w  # feed-forward cancels the follow lag
            cx = self.cam_x.step(target, 1 / FPS)
            self.cam_hold = (max(0.0, cx), GROUND - GA * vw * ASPECT, vw)
            return self.cam_hold
        if t < T["03_reginald"] - 0.1:  # glide up to Grub in the tree
            a = self.cam_hold
            b = view_at(TREE_X + 6, MED, feet=GROUND - 79, frac=0.6)
            k = ease((t - T["reveal"]) / 1.1)
            return tuple(lerp(p, q, k) for p, q in zip(a, b))
        if t < T["climb"]:
            return self.push(view_at((REG_STOP + MARK_STOP) / 2, MED), t, T["03_reginald"])
        if t < T["04_bumblewick"] - 0.05:
            return view_at(300, WIDE)
        if t < T["spell"]:
            return self.push(view_at(WIZ_X + 12, MED), t, T["04_bumblewick"])
        if t < T["06_mark"] - 0.1:
            return view_at(300, WIDE)
        if t < T["slash"]:
            return self.push(view_at(MARK_STOP, CLOSE), t, T["06_mark"])
        if t < T["fall"] - 0.15:
            return view_at((MARK_CHOP + TREE_X) / 2 + 4, MED)
        if t < T["08_mark"] - 0.1:
            return view_at(344, FAR)
        if t < T["drop"]:
            return self.push(view_at(MARK_CHOP, CLOSE), t, T["08_mark"])
        if t < T["09_reginald"] - 0.05:
            return view_at(344, FAR)
        if t < T["leave"]:
            return self.push(view_at(REG_FLOAT + 6, MED), t, T["09_reginald"])
        return view_at(340, FAR)

    def push(self, cam, t, t0, amount=0.05, dur=4.0):
        """Slow push-in during a dialogue shot (only smooth because the camera is sub-pixel)."""
        x, y, vw = cam
        k = ease((t - t0) / dur) * amount
        nw = vw * (1 - k)
        cx, feet = x + vw / 2, y + GA * vw * ASPECT
        return cx - nw / 2, feet - GA * nw * ASPECT, nw

    def shake(self, t):
        s = 0.0
        for at, amp in ((self.T["tree_land"], 2.2), (self.T["drop_land"], 1.0)):
            age = t - at
            if 0 <= age < 0.5:
                s += amp * math.exp(-age * 9) * math.sin(age * 70)
        return s

    # ---- one frame
    def frame(self, t):
        T = self.T
        cx, cy, vw = self.camera(t)
        sh = self.shake(t)
        cv = Canvas(self.L, cx, cy + sh, vw)
        under, over = cv.overlay(), cv.overlay()
        ox, oy = cv.origin
        du, do = ImageDraw.Draw(under), ImageDraw.Draw(over)

        # ---- the oak
        tree_top_left = (TREE_X - OAK_BASE[0], GROUND + 1 - (OAK_H - 1))
        stump_y = GROUND + 1 - CUT + 1
        cv.sprite(self.stump_cut if t >= T["chop"] else self.stump, tree_top_left[0], stump_y)
        ang = self.angle(t)
        if ang == 0.0:
            cv.sprite(self.tree, *tree_top_left)
        else:
            img = self.rotated_tree(ang)
            cv.sprite(img, PIVOT[0] - OAK_H, PIVOT[1] - OAK_H)
        if 0 <= t - T["tree_land"] < 0.05:  # dust where the crown hits
            for i in range(9):
                self.puffs.append((t, TREE_X + 40 + i * 7, GROUND - 1, "burst"))

        # ---- Mark
        mx, v, ph, state = self.trip.at(t)
        if t < T["walk"]:
            cv.put(front("mark", "calm"), mx, GROUND - 1 - self.bob(t, 0))
        elif t < T["arrive"]:
            if state == "skid":
                cv.put(self.skid, mx, GROUND + 1)
            else:
                cv.put(mark_side(pose(ph, speed_blend(v))), mx, GROUND + 1)
            if not self.kicked and v > 60:
                self.kicked = True
                self.puffs += [(t, mx - 6 + i * 3, GROUND - 1, "burst") for i in range(-3, 3)]
            if (v > 60 or state == "skid") and t - self.last_puff > 0.06:
                self.puffs.append((t, mx - 6, GROUND - 1, "skid" if state == "skid" else "trail"))
                self.last_puff = t
        elif t < T["02_grub"]:
            cv.put(self.mark_idle, MARK_STOP, GROUND + 1)
        elif t < T["slash"]:
            expr = "annoyed"
            if T["06_mark"] <= t:
                expr = "smirk" if t > T["06_mark"] + 1.2 else "calm"
            cv.put(front("mark", expr, self.talk("mark", t)), MARK_STOP, GROUND - 1 - self.bob(t, 0))
        elif t < T["fall"] + 0.2:
            i = min(3, int((t - T["slash"]) / 0.11))
            cv.put(self.slash[i], MARK_CHOP, GROUND + 1)
        elif t < T["leave"]:
            expr = "annoyed" if t >= T["08_mark"] - 0.2 else "calm"
            feet = GROUND - 1 - self.bob(t, 0)
            cv.put(front("mark", expr, self.talk("mark", t)), MARK_CHOP, feet)
            if t >= T["catch"]:
                hx, hy = self.mark_hand(MARK_CHOP, feet)
                cv.sprite(self.pie, hx - 4.5, hy - 5)
        else:  # walks home, pie in hand
            k = t - T["leave"]
            wx = MARK_CHOP - VWALK * k
            phase = math.pi * VWALK / stride(0) * k
            cv.put(flip(mark_side(pose(phase, 0.0), "annoyed")), wx, GROUND + 1)
            cv.sprite(self.pie, wx - 10, GROUND - 19)

        # ---- Reginald
        self.draw_reginald(cv, t, do, ox, oy)

        # ---- Bumblewick
        if t < T["reveal"]:
            cv.put(front("bumblewick", "confused"), WIZ_VILLAGE, GROUND - 1 - self.bob(t, 0.3))
        elif T["wiz_enter"] <= t < T["wiz_stop"]:
            k = (t - T["wiz_enter"]) / (T["wiz_stop"] - T["wiz_enter"])
            cv.put(self.wiz_walk[int(t * 4) % 2], lerp(WIZ_FROM, WIZ_X, k), GROUND + 1)
        elif t >= T["wiz_stop"]:
            expr = "calm" if T["04_bumblewick"] <= t < T["06_mark"] else "confused"
            cv.put(front("bumblewick", expr, self.talk("bumblewick", t)), WIZ_X, GROUND - 1 - self.bob(t, 0.3))
            if T["spell"] <= t < T["spell"] + 0.8:  # beam from the orb to Reginald
                x0, y0 = WIZ_X + 10 - ox, GROUND - 46 - oy
                x1, y1 = REG_TREE - ox, GROUND - 22 - oy
                for i in range(18):
                    k = (i / 18 + t * 3) % 1.0
                    px_, py_ = lerp(x0, x1, k), lerp(y0, y1, k) - 10 * math.sin(k * math.pi)
                    do.point((px_, py_), fill="#c8f8ff" if i % 2 else "#ffe04a")

        # ---- Grub (and the pie)
        gx, gy, gstate = self.grub_pos(t)
        if gstate == "perch":
            expr = "panic" if t >= T["chop"] else "sneaky"
            talk = self.talk("grub", t)
            g = front("grub", expr, talk)
            cv.put(g, gx, gy - (self.bob(t, 0.7) if t < T["chop"] else 0))
        elif gstate == "fly":
            g = front("grub", "panic", self.talk("grub", t)).rotate(-(t - T["release"]) * 720, expand=True)
            cv.put(g, gx, gy + (g.height - 30) / 2)
        else:
            cv.put(front("grub", "panic", self.talk("grub", t)), gx, gy)
            for i in range(3):  # dazed stars
                a = t * 5 + i * 2.1
                do.point((gx + 7 * math.cos(a) - ox, gy - 31 + 2 * math.sin(a) - oy), fill="#ffe04a")
        pp = self.pie_pos(t)
        if pp is not None:
            cv.sprite(self.pie, pp[0] - 4.5, pp[1] - 3.5)

        # ---- dust
        for born, px_, py_, kind in self.puffs:
            age = t - born
            if 0 <= age < 0.6:
                r = 1.5 + age * (8 if kind == "burst" else 5)
                lift = age * (10 if kind == "burst" else 4)
                drift = (age * 20 * (1 if (px_ % 2) else -1)) if kind == "burst" else -age * 10
                col = "#bda98c" if kind == "skid" else "#e2d8c8"
                x, y = px_ + drift - ox, py_ - lift - oy
                du.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=col)
        cv.add_overlay(under)  # (drawn last: puffs read best on top)
        cv.add_overlay(over)
        frame = cv.final()

        # ---- screen-space effects
        if T["walk"] <= t < T["arrive"] and v > 0.55 * VMAX:
            fd = ImageDraw.Draw(frame)
            rnd = random.Random(int(t * FPS))
            for _ in range(int(16 * (v / VMAX))):
                y = rnd.randrange(150, 1500)
                x = rnd.randrange(-200, 1080)
                fd.rectangle([x, y, x + rnd.randrange(120, 320), y + 5], fill="#ffffff")
        if T["chop"] <= t < T["chop"] + 1 / FPS:
            frame = Image.blend(frame, Image.new("RGB", frame.size, "#ffffff"), 0.7)
        return frame

    def draw_reginald(self, cv, t, do, ox, oy):
        T = self.T
        bob = self.bob(t, 0.5)
        talk = self.talk("reginald", t)
        if t < T["reg_run"]:
            cv.put(front("reginald", "proud"), REG_START, GROUND - 1 - bob)
            return
        rx = REG_START + (t - T["reg_run"]) * REG_V
        if rx < REG_STOP:
            cv.put(self.reg_run[math.floor(t * 12) % len(self.reg_run)], rx, GROUND + 1)
            return
        if t < T["climb"]:
            cv.put(front("reginald", "shout" if talk else "proud", talk), REG_STOP, GROUND - 1 - bob)
            return
        if t < T["hops"][0]:  # runs to the trunk
            k = (t - T["climb"]) / (T["hops"][0] - T["climb"])
            cv.put(self.reg_run[math.floor(t * 12) % len(self.reg_run)], lerp(REG_STOP, REG_TREE, k), GROUND + 1)
            return
        if t < T["slide"]:  # hauls himself up, a few px per clank
            n = sum(1 for h in T["hops"] if t >= h)
            spr = front("reginald", "shout")
            cv.put(spr if n % 2 else flip(spr), REG_TREE, GROUND - 1 - 5 * n)
            return
        if t < T["back"]:  # slides down
            k = (t - T["slide"]) / (T["back"] - T["slide"])
            cv.put(front("reginald", "shocked"), REG_TREE, GROUND - 1 - 20 * (1 - k * k))
            return
        if t < T["getup"]:  # flat on his back
            cv.put(front("reginald", "shocked").rotate(90, expand=True), REG_TREE - 4, GROUND - 1)
            return
        if t < T["spell"] + 0.3:
            cv.put(front("reginald", "shocked"), REG_TREE, GROUND - 1 - bob)
            return
        if t < T["drop"]:  # levitated, turned upside down, bobbing
            k = ease((t - T["spell"] - 0.3) / 1.4)
            turn = 180 * ease((t - T["spell"] - 0.3) / 0.8)
            spr = front("reginald", "shout" if talk else "shocked", talk).rotate(turn, expand=True,
                                                                               resample=Image.NEAREST)
            x = lerp(REG_TREE, REG_FLOAT, k)
            feet = GROUND - 1 - FLOAT_H * k - (math.sin(t * 3) * 1.5 if k >= 1 else 0)
            cv.put(spr, x, feet)
            for i in range(6):  # sparkles
                a = t * 4 + i * 1.05
                do.point((x + 14 * math.cos(a) - ox, feet - 22 + 18 * math.sin(a * 1.3) - oy),
                         fill="#c8f8ff" if i % 2 else "#ffe04a")
            return
        # spell broken: falls and plants head-first
        k = min(t - T["drop"], T["drop_land"] - T["drop"])
        feet = GROUND - 1 - FLOAT_H + 0.5 * G * k * k
        spr = front("reginald", "shout" if talk else "shocked", talk).rotate(180)
        cv.put(spr, REG_FLOAT, min(GROUND + 2, feet))


def main():
    audio_dir, timings_path, out_mp4 = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    timings = json.load(open(timings_path))
    lines = {l["id"]: l for l in SCRIPT["lines"]}
    audio = {i: sf.read(audio_dir / f"{i}.wav")[0] for i in lines}
    fall, t_fall_land, fall_land = simulate_fall()
    T, d, trip = build_timeline(audio, timings, fall, t_fall_land)
    by_speaker = {}
    words = {i: [(w["word"], T[i] + w["start"], T[i] + w["end"]) for w in timings[i]["words"]] for i in audio}
    for i, ws in words.items():
        by_speaker.setdefault(lines[i]["speaker"], []).extend(ws)
    captions = build_captions(T, d, words)
    wav = str(Path(out_mp4).with_suffix(".wav"))
    mix_audio(T, audio, audio_dir, wav)
    ep = Episode(T, trip, fall, fall_land, by_speaker)
    n_frames = int(T["end"] * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_mp4],
        stdin=subprocess.PIPE,
    )
    stills = {float(s) for s in sys.argv[4].split(",")} if len(sys.argv) > 4 else set()
    for f in range(n_frames):
        t = f / FPS
        frame = ep.frame(t)
        draw_banner(frame, t, 0.3, T["dash"] + 1.6, "QUEST 1", "RECOVER THE PIE")
        draw_banner(frame, t, T["complete"], T["end"] + 1, "QUEST 1", "QUEST COMPLETE!")
        for cap in captions:
            if cap[0] <= t < cap[1]:
                draw_caption(frame, cap)
                break
        if any(abs(t - s) < 0.5 / FPS for s in stills):
            frame.save(Path(out_mp4).parent / f"still_{t:05.2f}.png")
        ff.stdin.write(frame.tobytes())
        if f % 240 == 0:
            print(f"frame {f}/{n_frames}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(json.dumps({k: round(v, 2) for k, v in T.items() if isinstance(v, float)}))
    print(f"done: {out_mp4} ({n_frames / FPS:.1f}s)")


if __name__ == "__main__":
    main()
