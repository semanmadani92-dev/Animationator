"""Render episode 2, "The Door": 1080x1920 at 24 fps, Shorts format (cold open + freeze, then the story).

Grub kidnaps the village chicken and hides behind his "unbreakable" door. Reginald charges it and bounces
off, Bumblewick's fireball blows up in his own face, and Mark reads the sign: PULL.

Usage: python render_ep02.py <audio_dir> <timings.json> <out.mp4>
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pixel"))
sys.path.insert(0, str(ROOT / "pipeline"))
from camera import ASPECT, Canvas, Spring  # noqa: E402
from chiptune import chiptune  # noqa: E402
from gait import SKID, VMAX, Trip, pose, speed_blend  # noqa: E402
from level import GROUND, build_level  # noqa: E402
from props import DOOR_AT, DOOR_H, FORT_H, FORT_W, chicken, door, fortress, sign_pull, torch_flames  # noqa: E402
from recut_ep01 import FREEZE, hook_top, scratch  # noqa: E402
from render_bridge import caption_chunks, draw_banner, draw_caption, rms_normalise, text_centered  # noqa: E402
from render_ep01 import CLOSE, FAR, GA, MED, WIDE, ease, flip, front, lerp, view_at  # noqa: E402
from run_options import DASH, foot_speed  # noqa: E402
from side import IDLE, mark_side, reginald_side  # noqa: E402

FPS, SR = 24, 24000
SCRIPT = json.load(open(ROOT / "episodes" / "ep02_door" / "script.json"))
G = 400.0

FORT_X = 380  # fortress centre; the door is centred on it
FORT_LEFT = FORT_X - FORT_W // 2
DOOR_X0 = FORT_LEFT + DOOR_AT[0]
DOOR_CX = DOOR_X0 + 9
SIGN_X = 352
MARK_START, MARK_STOP, MARK_PULL = 70, 334, 364
REG_START, REG_STOP, REG_HIT, REG_LAND = 46, 310, 362, 290
WIZ_X = 244
REG_V = foot_speed(DASH)
PULL = dict(nl=(14, 2), fl=(-14, -6), na=(92, 96), fa=(70, 90), sword=-100, tilt=-8)
LAUGH = "02b_grub"  # Grub's "Hehehe!" reused after Reginald bounces off


def soot(img):
    """Bumblewick after the backfire: blackened, but still readable."""
    rgb = Image.new("RGBA", img.size, (44, 36, 44, 255))
    out = Image.blend(img, rgb, 0.55)
    out.putalpha(img.getchannel("A"))
    return out


def build_timeline(audio, timings):
    d = {i: len(a) / SR for i, a in audio.items()}
    T = {"01_narrator": 0.15, "walk": 0.25, "dash": 0.75, "reg_run": 1.0}
    trip = Trip(MARK_START, MARK_STOP, T["walk"], T["dash"])
    T["arrive"] = trip.t_stop
    T["reveal"] = T["arrive"] + 0.25
    T["peep"] = T["reveal"] + 0.7
    T["02_grub"] = T["peep"] + 0.25
    T["peep_shut"] = T["02_grub"] + d["02_grub"] + 0.1
    T["03_reginald"] = T["peep_shut"] + 0.15
    T["charge"] = T["03_reginald"] + d["03_reginald"] + 0.15
    T["hit"] = T["charge"] + 0.45
    T["land"] = T["hit"] + 0.6
    T["peep2"] = T["land"] + 0.25
    T[LAUGH] = T["peep2"] + 0.15
    T["peep2_shut"] = T[LAUGH] + d[LAUGH] + 0.05
    T["poof"] = T["peep2_shut"] + 0.15
    T["04_bumblewick"] = T["poof"] + 0.45
    T["fireball"] = T["04_bumblewick"] + d["04_bumblewick"] + 0.05
    T["boom"] = T["fireball"] + 1.0
    T["05_mark"] = T["boom"] + 1.0
    T["pull"] = T["05_mark"] + d["05_mark"] + 0.15
    T["open"] = T["pull"] + 0.3
    T["06_grub"] = T["open"] + 0.55
    T["chicken"] = T["06_grub"] + d["06_grub"] + 0.05
    T["07_mark"] = T["chicken"] + 0.9
    T["08_narrator"] = T["07_mark"] + d["07_mark"] + 0.3
    T["complete"] = T["08_narrator"] + d["08_narrator"] - 0.2
    T["end"] = T["complete"] + 1.6
    T["kick"] = next(T["walk"] + i * trip.dt for i, s in enumerate(trip.samples) if s[2] > 60)
    T["skid"] = trip.t_skid
    return T, d, trip


def mix_audio(T, audio, audio_dir):
    n = int(T["end"] * SR)
    mix = np.zeros(n)

    def add(y, at, gain=1.0):
        s = int(at * SR)
        if 0 <= s < n:
            mix[s:s + y.size] += (y * gain)[: n - s]

    for i, y in audio.items():
        add(rms_normalise(y.astype(np.float64)), T[i])
    sfx = {p.stem[4:]: sf.read(p)[0] for p in audio_dir.glob("sfx_*.wav")}
    add(sfx["whoosh"], T["kick"])
    add(sfx["skid"], T["skid"])
    for at in (T["peep"], T["peep_shut"], T["peep2"], T["peep2_shut"]):
        add(sfx["pop"], at, 0.5)
    add(sfx["whoosh"][: int(0.4 * SR)], T["charge"], 0.7)
    add(sfx["clang"], T["hit"], 1.3)
    add(sfx["thud"], T["land"], 0.5)
    add(sfx["clank"], T["land"], 0.4)
    add(sfx["magic"], T["poof"], 0.8)
    add(sfx["fizz"], T["fireball"] + 0.15, 0.8)
    add(sfx["boom"], T["boom"], 1.2)
    add(sfx["creak"][: int(0.5 * SR)], T["open"] - 0.05, 0.8)
    add(sfx["cluck"], T["chicken"], 0.9)
    add(sfx["cluck"], T["chicken"] + 0.55, 0.6)
    add(sfx["jingle"], T["complete"])
    t = np.arange(n) / SR
    env = np.ones(n)
    env[(t >= T["boom"]) & (t < T["05_mark"] + 0.4)] = 0.0  # stunned silence after the backfire
    back = (t >= T["05_mark"] + 0.4) & (t < T["05_mark"] + 1.4)
    env[back] = t[back] - (T["05_mark"] + 0.4)
    env[t >= T["complete"]] = 0.0
    mix += chiptune(T["end"]) * 0.05 * env
    return mix / max(1.0, np.abs(mix).max() / 0.97)


def build_captions(T, d, words):
    caps = []
    for line in SCRIPT["lines"] + [{"id": LAUGH, "speaker": "grub", "keywords": ["Hehehe"]}]:
        chunks = caption_chunks(line, words[line["id"]])
        for k, ch in enumerate(chunks):
            end = chunks[k + 1][0][1] if k + 1 < len(chunks) else T[line["id"]] + d[line["id"]] + 0.25
            caps.append((ch[0][1], end, line["speaker"], [w[0] for w in ch]))
    caps.sort()
    return [(a, min(b, caps[i + 1][0]) if i + 1 < len(caps) else b, *r) for i, (a, b, *r) in enumerate(caps)]


class Episode:
    def __init__(self, T, trip, words):
        self.T, self.trip, self.words = T, trip, words
        self.L = build_level(forest=((272, 58), (306, 70), (470, 50)), bushes=(290,))
        self.fort = fortress()
        self.sign = sign_pull()
        self.reg_run = [reginald_side(p) for p in DASH]
        self.mark_idle = mark_side(IDLE, "annoyed")
        self.mark_pull = mark_side(PULL, "annoyed")
        self.skid = mark_side(SKID)
        self.chick = [chicken(0), chicken(1)]
        self.cam_x = Spring(MARK_START - 0.42 * WIDE, 5.0)
        self.cam_w = Spring(WIDE, 3.2)
        self.hold = None
        self.puffs, self.last_puff, self.kicked = [], -1.0, False

    def talk(self, speaker, t):
        return any(a <= t <= b for _, a, b in self.words.get(speaker, [])) and int(t * 8) % 2 == 0

    @staticmethod
    def bob(t, ph):
        return int(t * 2 + ph) % 2

    # ---- camera
    def push(self, cam, t, t0, amount=0.05, dur=4.0):
        x, y, vw = cam
        k = ease((t - t0) / dur) * amount
        nw = vw * (1 - k)
        cx, feet = x + vw / 2, y + GA * vw * ASPECT
        return cx - nw / 2, feet - GA * nw * ASPECT, nw

    def camera(self, t):
        T = self.T
        if t < T["reveal"]:
            mx, v, _, _ = self.trip.at(t)
            k = v / VMAX
            vw = self.cam_w.step(WIDE + (FAR - WIDE) * k, 1 / FPS)
            cx = self.cam_x.step(mx - (0.42 - 0.14 * k) * vw + 2 * v / self.cam_x.w, 1 / FPS)
            self.hold = (max(0.0, cx), GROUND - GA * vw * ASPECT, vw)
            return self.hold
        if t < T["03_reginald"] - 0.05:  # glide over to the door
            b = view_at(DOOR_CX - 4, MED)
            k = ease((t - T["reveal"]) / 0.8)
            return tuple(lerp(p, q, k) for p, q in zip(self.hold, b))
        if t < T["charge"]:
            return self.push(view_at((REG_STOP + MARK_STOP) / 2, MED), t, T["03_reginald"])
        if t < T["04_bumblewick"] - 0.05:
            return view_at(336, WIDE)
        if t < T["fireball"]:
            return self.push(view_at(WIZ_X + 14, MED), t, T["04_bumblewick"])
        if t < T["05_mark"] - 0.05:
            return view_at(290, WIDE)
        if t < T["pull"]:
            return self.push(view_at((MARK_STOP + SIGN_X) / 2 + 2, CLOSE, frac=0.66), t, T["05_mark"], 0.06, 2.5)
        if t < T["chicken"]:
            return self.push(view_at(DOOR_CX - 8, MED), t, T["pull"])
        if t < T["07_mark"] - 0.05:
            return view_at(330, WIDE)
        if t < T["08_narrator"]:
            return self.push(view_at(MARK_PULL - 4, CLOSE), t, T["07_mark"])
        return view_at(314, FAR)

    def shake(self, t):
        s = 0.0
        for at, amp in ((self.T["hit"], 2.0), (self.T["boom"], 2.4)):
            age = t - at
            if 0 <= age < 0.5:
                s += amp * math.exp(-age * 9) * math.sin(age * 70)
        return s

    # ---- one frame
    def frame(self, t):
        T = self.T
        cx, cy, vw = self.camera(t)
        cv = Canvas(self.L, cx + self.shake(t) * 0.6, cy + self.shake(t), vw)
        under, over = cv.overlay(), cv.overlay()
        ox, oy = cv.origin
        du, do = ImageDraw.Draw(under), ImageDraw.Draw(over)

        # ---- the hideout: rock, torches, doorway contents, door, sign
        cv.sprite(self.fort, FORT_LEFT, GROUND + 1 - FORT_H)
        for tx in (DOOR_X0 - 9, DOOR_X0 + 18 + 8):
            for dx, dy, col in torch_flames(t + tx):
                do.point((tx + dx - ox, GROUND + 1 - FORT_H + DOOR_AT[1] + 4 + dy - oy), fill=col)
        door_y = GROUND + 1 - DOOR_H
        open_k = ease((t - T["open"]) / 0.35) if t >= T["open"] else 0.0
        if open_k > 0:  # Grub inside, hugging the chicken until it bolts
            expr = "panic"
            g = front("grub", expr, self.talk("grub", t))
            cv.put(g, DOOR_CX, GROUND - 1)
            if t < T["chicken"]:
                cv.sprite(self.chick[0], DOOR_CX - 13 + 8, GROUND - 30 + 14)
        peep = (T["peep"] <= t < T["peep_shut"]) or (T["peep2"] <= t < T["peep2_shut"])
        cv.sprite(door(open_k, peep), DOOR_X0, door_y)
        cv.sprite(self.sign, SIGN_X - 9, GROUND + 1 - 22)

        # ---- Mark
        mx, v, ph, state = self.trip.at(t)
        if t < T["walk"]:
            cv.put(front("mark", "calm"), mx, GROUND - 1)
        elif t < T["arrive"]:
            cv.put(self.skid if state == "skid" else mark_side(pose(ph, speed_blend(v))), mx, GROUND + 1)
            if not self.kicked and v > 60:
                self.kicked = True
                self.puffs += [(t, mx - 6 + i * 3, GROUND - 1, "burst") for i in range(-3, 3)]
            if (v > 60 or state == "skid") and t - self.last_puff > 0.06:
                self.puffs.append((t, mx - 6, GROUND - 1, "skid" if state == "skid" else "trail"))
                self.last_puff = t
        elif t < T["03_reginald"] - 0.05 or T["05_mark"] - 0.05 <= t < T["pull"]:
            cv.put(self.mark_idle, MARK_STOP, GROUND + 1)  # facing the door / reading the sign
        elif t < T["pull"]:
            cv.put(front("mark", "annoyed", self.talk("mark", t)), MARK_STOP, GROUND - 1 - self.bob(t, 0))
        elif t < T["07_mark"] - 0.05:
            cv.put(self.mark_pull if t < T["open"] + 0.6 else self.mark_idle, MARK_PULL, GROUND + 1)
        else:
            cv.put(front("mark", "annoyed", self.talk("mark", t)), MARK_PULL - 4, GROUND - 1 - self.bob(t, 0))

        # ---- Reginald
        self.draw_reginald(cv, t, do, ox, oy)

        # ---- Bumblewick
        if t < T["reveal"]:
            cv.put(front("bumblewick", "confused"), 24, GROUND - 1)
        elif t >= T["poof"]:
            sooty = t >= T["boom"]
            expr = "calm" if T["04_bumblewick"] <= t < T["boom"] else "confused"
            b = front("bumblewick", expr, self.talk("bumblewick", t))
            cv.put(soot(b) if sooty else b, WIZ_X, GROUND - 1 - self.bob(t, 0.3))
            orb = (WIZ_X + 12, GROUND - 1 - 42)
            if t - T["poof"] < 0.5:  # sparkle burst as he pops in
                age = t - T["poof"]
                for i in range(12):
                    a = i * math.pi / 6
                    r = 4 + age * 40
                    do.point((WIZ_X + r * math.cos(a) - ox, GROUND - 25 + r * math.sin(a) - oy),
                             fill="#c8f8ff" if i % 2 else "#ffe04a")
            if T["fireball"] <= t < T["boom"]:  # the fireball swells and wobbles on the staff
                k = (t - T["fireball"]) / (T["boom"] - T["fireball"])
                r = 1 + 5 * ease(k * 1.4)
                wob = math.sin(t * 40) * k * 1.5
                fx, fy = orb[0] + wob - ox, orb[1] - oy
                for rr, col in ((r + 1, "#ff3a2a"), (r, "#ff8a2a"), (r * 0.6, "#ffd23f"), (r * 0.25, "#ffffff")):
                    do.ellipse([fx - rr, fy - rr, fx + rr, fy + rr], fill=col)
            if 0 <= t - T["boom"] < 0.02:
                self.puffs += [(t, WIZ_X + (i - 4) * 3, GROUND - 30 - (i % 3) * 6, "smoke") for i in range(9)]
            if sooty and int(t * 6) % 3 == 0 and t - self.last_puff > 0.15:  # wisps off the hat
                self.puffs.append((t, WIZ_X - 4 + (int(t * 7) % 3) * 3, GROUND - 49, "wisp"))
                self.last_puff = t

        # ---- the chicken bolts for home
        if t >= T["chicken"]:
            k = t - T["chicken"]
            x = DOOR_CX - 5 - 95 * k
            hop = abs(math.sin(k * 14)) * 3
            c = flip(self.chick[int(k * 10) % 2])
            cv.put(c, x, GROUND - 1 - hop)
            if int(k * 12) % 3 == 0:
                for j in range(2):
                    do.point((x + 6 + j * 2 - ox, GROUND - 9 - hop - j - oy), fill="#f4f1e6")  # loose feathers

        # ---- dust and smoke
        for born, px_, py_, kind in self.puffs:
            age = t - born
            life = 1.2 if kind in ("smoke", "wisp") else 0.6
            if 0 <= age < life:
                if kind == "smoke":
                    r, lift, drift, col = 3 + age * 9, age * 14, (px_ - WIZ_X) * age * 2, "#6a6474"
                elif kind == "wisp":
                    r, lift, drift, col = 1 + age * 2, age * 14, math.sin(age * 6) * 2, "#9a94a8"
                else:
                    r = 1.5 + age * (8 if kind == "burst" else 5)
                    lift = age * (10 if kind == "burst" else 4)
                    drift = (age * 20 * (1 if (px_ % 2) else -1)) if kind == "burst" else -age * 10
                    col = "#bda98c" if kind == "skid" else "#e2d8c8"
                x, y = px_ + drift - ox, py_ - lift - oy
                (do if kind in ("smoke", "wisp") else du).ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=col)
        cv.add_overlay(under)
        cv.add_overlay(over)
        frame = cv.final()
        if T["walk"] <= t < T["arrive"] and v > 0.55 * VMAX:  # speed lines
            fd = ImageDraw.Draw(frame)
            rnd = random.Random(int(t * FPS))
            for _ in range(int(16 * v / VMAX)):
                y, x = rnd.randrange(150, 1500), rnd.randrange(-200, 1080)
                fd.rectangle([x, y, x + rnd.randrange(120, 320), y + 5], fill="#ffffff")
        for at, col, a in ((T["hit"], "#ffffff", 0.6), (T["boom"], "#ffd23f", 0.75)):
            if at <= t < at + 1 / FPS:
                frame = Image.blend(frame, Image.new("RGB", frame.size, col), a)
        return frame

    def draw_reginald(self, cv, t, do, ox, oy):
        T = self.T
        talk = self.talk("reginald", t)
        if t < T["reg_run"]:
            cv.put(front("reginald", "proud"), REG_START, GROUND - 1)
            return
        rx = REG_START + (t - T["reg_run"]) * REG_V
        if rx < REG_STOP and t < T["03_reginald"]:
            cv.put(self.reg_run[math.floor(t * 12) % len(self.reg_run)], rx, GROUND + 1)
            return
        if t < T["charge"]:
            cv.put(front("reginald", "shout" if talk else "proud", talk), REG_STOP, GROUND - 1 - self.bob(t, 0.5))
            return
        if t < T["hit"]:  # full charge, shoulder first
            k = ((t - T["charge"]) / (T["hit"] - T["charge"])) ** 1.6
            cv.put(self.reg_run[math.floor(t * 24) % len(self.reg_run)], lerp(REG_STOP, REG_HIT, k), GROUND + 1)
            return
        if t < T["land"]:  # bounces off, tipping backwards
            k = (t - T["hit"]) / (T["land"] - T["hit"])
            spr = front("reginald", "shocked").rotate(90 * ease(k), expand=True)
            x = lerp(REG_HIT, REG_LAND, k)
            cv.put(spr, x, GROUND - 1 - 16 * math.sin(math.pi * k))
            return
        cv.put(front("reginald", "shocked").rotate(90, expand=True), REG_LAND, GROUND - 1)  # out cold
        for i in range(3):
            a = t * 5 + i * 2.1
            do.point((REG_LAND - 12 + 6 * math.cos(a) - ox, GROUND - 22 + 2 * math.sin(a) - oy), fill="#ffe04a")


def main():
    audio_dir, timings_path, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    timings = json.load(open(timings_path))
    lines = {l["id"]: l for l in SCRIPT["lines"]}
    audio = {i: sf.read(audio_dir / f"{i}.wav")[0] for i in lines}
    laugh_end = timings["02_grub"]["words"][1]["start"] - 0.08  # the whole "Hehehe!", up to the next word
    audio[LAUGH] = audio["02_grub"][: int(laugh_end * SR)]
    timings[LAUGH] = {"words": [dict(timings["02_grub"]["words"][0])]}
    speaker = {i: l["speaker"] for i, l in lines.items()} | {LAUGH: "grub"}
    T, d, trip = build_timeline(audio, timings)
    words = {i: [(w["word"], T[i] + w["start"], T[i] + w["end"]) for w in timings[i]["words"]] for i in audio}
    by_speaker = {}
    for i, ws in words.items():
        by_speaker.setdefault(speaker[i], []).extend(ws)
    captions = build_captions(T, d, words)
    story = mix_audio(T, audio, audio_dir)

    c0, c1 = T["charge"] - 0.1, T["land"] + 0.35  # cold open: Reginald vs the door
    cut = np.zeros(int(FREEZE * SR))
    sc = scratch()
    cut[: sc.size] += sc
    full = np.concatenate([story[int(c0 * SR):int(c1 * SR)], cut, story])
    wav = str(Path(out).with_suffix(".wav"))
    sf.write(wav, full.astype(np.float32), SR)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    stills = {float(s) for s in sys.argv[4].split(",")} if len(sys.argv) > 4 else set()

    def caption(frame, t):
        for cap in captions:
            if cap[0] <= t < cap[1]:
                draw_caption(frame, cap)
                break

    cold = Episode(T, trip, by_speaker)
    for _ in range(int(T["reveal"] * FPS)):  # run the dash camera so the cold open starts from a settled state
        cold.camera(_ / FPS)
    last = None
    n_cold = int((c1 - c0) * FPS)
    for f in range(n_cold):
        t = c0 + f / FPS
        frame = cold.frame(t)
        last = frame.copy()
        caption(frame, t)
        ff.stdin.write(frame.tobytes())
    frozen = ImageEnhance.Brightness(ImageEnhance.Color(last).enhance(0.25)).enhance(0.7)
    for f in range(int(FREEZE * FPS)):
        frame = frozen.copy()
        dd = ImageDraw.Draw(frame)
        text_centered(dd, "WAIT...", 96, "#ffffff", 760)
        if f >= 8:
            text_centered(dd, "HOW DID WE", 64, "#ffd23f", 900)
            text_centered(dd, "GET HERE?", 64, "#ffd23f", 990)
        for y in range(0, 1920, 6):
            if (y // 6 + f) % 9 == 0:
                dd.rectangle([0, y, 1079, y + 2], fill="#ffffff")
        ff.stdin.write(frame.tobytes())
    ep = Episode(T, trip, by_speaker)
    n = int(T["end"] * FPS)
    for f in range(n):
        t = f / FPS
        frame = ep.frame(t)
        draw_banner(frame, t, 0.2, T["dash"] + 1.6, "QUEST 2", "RESCUE THE CHICKEN")
        draw_banner(frame, t, T["complete"], T["end"] + 1, "QUEST 2", "QUEST COMPLETE!")
        if t < T["02_grub"]:
            hook_top(frame)
        caption(frame, t)
        if any(abs(t - s) < 0.5 / FPS for s in stills):
            frame.save(Path(out).parent / f"still_{t:05.2f}.png")
        ff.stdin.write(frame.tobytes())
        if f % 240 == 0:
            print(f"frame {f}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(json.dumps({k: round(v, 2) for k, v in T.items()}))
    print(f"done: {out} ({n_cold / FPS + FREEZE + n / FPS:.1f}s)")


if __name__ == "__main__":
    main()
