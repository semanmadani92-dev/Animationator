"""Render episode 1, "The Bridge" (v2): a side-scrolling game-feel short, 1080x1920 at 24 fps.

Usage: python render_ep01.py <audio_dir> <timings.json> <out.mp4>
audio_dir: one WAV per script line id (24 kHz mono) plus sfx_snap/fall/splash/jingle.wav.
Characters animate on twos (12 fps); camera moves, physics and captions run at 24 fps.
"""
import copy
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pixel"))
sys.path.insert(0, str(ROOT / "pipeline"))
from cast import BUILDERS  # noqa: E402
from chiptune import chiptune  # noqa: E402
from level import GROUND, LEFT_EDGE, RIGHT_EDGE, RIVER_Y, build_level, compose_view  # noqa: E402
from mark import build_mark  # noqa: E402
from ropebridge import RopeBridge  # noqa: E402
from side import IDLE, RUN, SLASH, WALK, bumblewick_side, mark_side, reginald_side  # noqa: E402

FPS, SR = 24, 24000
OUT_W, OUT_H = 1080, 1920
FONT = str(ROOT / "pixel" / "fonts" / "PressStart2P-Regular.ttf")
SCRIPT = json.load(open(ROOT / "episodes" / "ep01_bridge" / "script.json"))
COLOR = {"narrator": "#38c8f0", "mark": "#ff4a4a", "reginald": "#ffd23f", "vexmore": "#c06bff",
         "grub": "#6ad84a", "bumblewick": "#6aa8ff"}
NAME = {"mark": "MARK", "reginald": "SIR REGINALD", "vexmore": "LORD VEXMORE", "grub": "GRUB",
        "bumblewick": "BUMBLEWICK"}
G = 260.0  # gravity for falling characters (world px/s^2)

# camera framings: (view width, view height, ground position from the top of the view)
WIDE, MED, CLOSE = (135, 240, 160), (90, 160, 110), (72, 128, 88)  # ground ~68% down: captions sit below feet

# world positions (centre x)
MARK_START, REG_START, RUN_SPEED = 70, 46, 88
MARK_EDGE, REG_EDGE = 414, 388
VEX_X, GRUB_X = 600, 628  # guarding their own end of the bridge


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


# ---------------------------------------------------------------- timeline
def word_start(timings, line_id, index):
    return timings[line_id]["words"][index]["start"]


def build_timeline(audio_dir, timings):
    lines = {l["id"]: l for l in SCRIPT["lines"]}
    audio = {i: sf.read(audio_dir / f"{i}.wav")[0] for i in lines}
    d = {i: len(a) / SR for i, a in audio.items()}
    T = {"01_narrator": 0.5, "run_start": 1.3}
    T["run_end"] = T["run_start"] + (MARK_EDGE - MARK_START) / RUN_SPEED
    T["pan_start"], T["pan_end"] = T["run_end"] + 0.2, T["run_end"] + 1.6
    T["02_vexmore"] = T["pan_end"] - 0.4
    T["03_reginald"] = T["02_vexmore"] + d["02_vexmore"] + 0.3
    T["04_mark"] = T["03_reginald"] + d["03_reginald"] + 0.3
    T["slash"] = T["04_mark"] + d["04_mark"] + 0.1
    T["snap"] = T["slash"] + 0.32
    T["06_vexmore"] = T["snap"] + 0.35
    T["vex_fall"] = T["06_vexmore"] + word_start(timings, "06_vexmore", 2)  # drops on "NOOO!"
    T["07_grub"] = T["vex_fall"] + 0.45
    T["grub_fall"] = T["07_grub"] + word_start(timings, "07_grub", 2)  # drops on "Oh no"
    T["aftermath"] = None
    # river impact times from the fall heights
    T["vex_y0"], T["grub_y0"] = None, None
    return T, d, audio


def finish_timeline(T, d, vex_y0, grub_y0):
    T["vex_splash"] = T["vex_fall"] + math.sqrt(2 * (RIVER_Y - vex_y0) / G)
    T["grub_splash"] = T["grub_fall"] + math.sqrt(2 * (RIVER_Y - grub_y0) / G)
    T["aftermath"] = max(T["grub_splash"], T["07_grub"] + d["07_grub"]) + 0.6
    T["08_bumblewick"] = T["aftermath"] + 0.9
    T["09_mark"] = T["08_bumblewick"] + d["08_bumblewick"] + 0.3
    T["leave"] = T["09_mark"] + d["09_mark"] + 0.2
    T["10_narrator"] = T["leave"] + 0.4
    T["complete"] = T["10_narrator"] + d["10_narrator"] - 0.2
    T["end"] = T["complete"] + 2.4


def rms_normalise(y, target=0.09):
    y = y * (target / (np.sqrt(np.mean(y ** 2)) + 1e-9))
    peak = np.abs(y).max()
    return y * (0.95 / peak) if peak > 0.95 else y


def mix_audio(T, audio, audio_dir, out_wav):
    n = int(T["end"] * SR)
    mix = np.zeros(n)

    def add(y, at, gain=1.0):
        s = int(at * SR)
        if s < n:
            mix[s:s + y.size] += (y * gain)[: n - s]

    for i, y in audio.items():
        add(rms_normalise(y.astype(np.float64)), T[i])
    sfx = lambda name: sf.read(audio_dir / f"{name}.wav")[0]  # noqa: E731
    add(sfx("sfx_snap"), T["snap"], 1.4)
    add(sfx("sfx_fall"), T["vex_fall"], 0.9)
    add(sfx("sfx_splash"), T["vex_splash"], 1.6)
    add(sfx("sfx_fall"), T["grub_fall"], 0.7)
    add(sfx("sfx_splash"), T["grub_splash"], 1.3)
    add(sfx("sfx_jingle"), T["complete"], 1.0)
    t = np.arange(n) / SR
    music = chiptune(T["end"]) * 0.055
    env = np.ones(n)
    env[(t >= T["snap"]) & (t < T["aftermath"])] = 0.0  # comic silence while the bridge goes
    back = (t >= T["aftermath"]) & (t < T["aftermath"] + 1.0)
    env[back] = t[back] - T["aftermath"]
    env[t >= T["complete"]] = 0.0  # let the jingle ring out
    mix += music * env
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    sf.write(out_wav, mix.astype(np.float32), SR)


# ---------------------------------------------------------------- captions and UI
FILLER = {"the", "a", "an", "of", "to", "in", "this", "that", "will", "shall", "could", "just", "is", "was",
          "for", "and", "but", "it", "i", "you", "at", "be", "so", "lets", "every", "gets", "take", "do", "least"}


def caption_chunks(line, words):
    """Split a line into 1-5 word chunks; the last word of each is shown big, so never end on filler."""
    keys = {re.sub(r"[^a-z]", "", k.lower()) for k in line.get("keywords", [])}
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        bare = re.sub(r"[^a-z]", "", w[0].lower())
        punct = w[0][-1] in ".!?,:"
        filler = bare in FILLER
        if bare in keys or (punct and not filler) or (len(cur) >= 3 and not filler) or len(cur) >= 5:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_captions(T, d, words):
    caps = []
    for line in SCRIPT["lines"]:
        chunks = caption_chunks(line, words[line["id"]])
        for k, ch in enumerate(chunks):
            end = chunks[k + 1][0][1] if k + 1 < len(chunks) else T[line["id"]] + d[line["id"]] + 0.25
            caps.append((ch[0][1], end, line["speaker"], [w[0] for w in ch]))
    return caps


_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def text_centered(d, text, size, color, y, stroke=8):
    while d.textlength(text, font=font(size)) > OUT_W - 60 and size > 24:
        size -= 8
    w = d.textlength(text, font=font(size))
    x = (OUT_W - w) / 2
    d.text((x, y + 8), text, font=font(size), fill="#000000", stroke_width=stroke, stroke_fill="#000000")
    d.text((x, y), text, font=font(size), fill=color, stroke_width=stroke, stroke_fill="#120c18")


def draw_caption(frame, cap):
    _, _, speaker, ws = cap
    d = ImageDraw.Draw(frame)
    y = 1600
    if speaker != "narrator":
        text_centered(d, NAME[speaker], 40, COLOR[speaker], y - 76, stroke=7)
    if len(ws) > 1:
        text_centered(d, " ".join(ws[:-1]), 48, "#ffffff", y)
    text_centered(d, ws[-1].upper(), 80, COLOR[speaker], y + 78)


def draw_banner(frame, t, t_in, t_out, title, subtitle, title_color="#ffd23f"):
    if not (t_in <= t < t_out):
        return
    k = ease((t - t_in) / 0.25) * ease((t_out - t) / 0.25)
    y = int(-260 + (150 + 260) * k)
    d = ImageDraw.Draw(frame)
    d.rectangle([90, y, OUT_W - 90, y + 230], fill="#1b1222")
    for inset, col in ((0, "#ffd23f"), (12, "#8a6a1a")):
        d.rectangle([90 + inset, y + inset, OUT_W - 90 - inset, y + 230 - inset], outline=col, width=6)
    text_centered(d, title, 40, title_color, y + 50, stroke=0)
    text_centered(d, subtitle, 44, "#ffffff", y + 130, stroke=0)


# ---------------------------------------------------------------- drawing helpers
def put(view, spr, cx, feet, cam, clip_y=None):
    """Draw a sprite with its feet at world (cx, feet); optionally clip everything below clip_y (water)."""
    x = round(cx - spr.width / 2 - cam[0])
    y = round(feet - spr.height + 1 - cam[1])
    if clip_y is not None:
        visible = round(clip_y - cam[1]) - y
        if visible <= 0:
            return
        spr = spr.crop((0, 0, spr.width, min(spr.height, visible)))
    view.paste(spr, (x, y), spr)


def front(name, expr, talk=False):
    return build_mark(expr, talk) if name == "mark" else BUILDERS[name](expr, talk)


def flip(img):
    return img.transpose(Image.FLIP_LEFT_RIGHT)


def splash(view, x, age, cam):
    if not (0 <= age < 0.9):
        return
    d = ImageDraw.Draw(view)
    for k in range(16):
        vx, vy = (k - 7.5) * 8, -70 - (k % 4) * 20
        px, py = x + vx * age, RIVER_Y + vy * age + 0.5 * G * age * age
        if py <= RIVER_Y:
            d.rectangle([px - cam[0], py - cam[1], px - cam[0] + (k % 2), py - cam[1] + 1],
                        fill="#ffffff" if k % 3 else "#9fd8ff")
    if age < 0.45:
        r = 4 + age * 26
        d.line([x - r - cam[0], RIVER_Y - cam[1], x + r - cam[0], RIVER_Y - cam[1]], fill="#ffffff")


def talking(words_by_speaker, speaker, t):
    return any(a <= t <= b for _, a, b in words_by_speaker.get(speaker, [])) and int(t * 8) % 2 == 0


def bob(t, phase):
    return int(t * 2 + phase) % 2


# ---------------------------------------------------------------- the episode
class Episode:
    def __init__(self, T, words_by_speaker):
        self.T = T
        self.words = words_by_speaker
        self.L = build_level()
        self.bridge = RopeBridge((LEFT_EDGE, GROUND), (RIGHT_EDGE, GROUND), RIGHT_EDGE, GROUND)
        self.intact = copy.deepcopy(self.bridge)
        self.sim_t = 0.0
        self.vex_y0 = self.intact.deck_y(VEX_X) + 1
        self.grub_y0 = self.intact.deck_y(GRUB_X) + 1
        self.mark_run = [mark_side(p) for p in RUN]
        self.reg_run = [reginald_side(p) for p in RUN]
        self.mark_slash = [mark_side(p) for p in SLASH]
        self.mark_idle = {e: mark_side(IDLE, e) for e in ("calm", "annoyed")}
        self.reg_idle = reginald_side(IDLE)
        self.wiz_walk = [bumblewick_side(0), bumblewick_side(1)]

    def talk(self, s, t):
        return talking(self.words, s, t)

    def frame(self, t):
        T, ta = self.T, math.floor(t * 12) / 12
        cut = t >= T["snap"]
        if cut:  # advance the bridge physics in lock-step with the video
            if not self.bridge.left_pinned is False:
                self.bridge.cut()
            while self.sim_t < t - T["snap"]:
                for _ in range(10):
                    self.bridge.step(1 / 240)
                self.sim_t += 1 / FPS
        run_k = (t - T["run_start"]) * RUN_SPEED
        mark_x = min(MARK_EDGE, MARK_START + max(0.0, run_k))
        reg_x = min(REG_EDGE, REG_START + max(0.0, run_k))
        running = T["run_start"] <= t < T["run_end"]
        run_frame = int(ta * 10) % 4

        # ---- choose the shot
        if t < T["pan_start"]:  # 1. the run through the village and forest
            frame_def = WIDE
            cam_x = max(0, mark_x - 55)
            cast = []
            if t < T["run_start"]:
                cast += [("reginald_f", reg_x, "proud"), ("mark_f", mark_x, "calm")]
            elif running:
                cast += [("reginald_run", reg_x, run_frame), ("mark_run", mark_x, (run_frame + 1) % 4)]
            else:
                cast += [("reginald_side", reg_x, None), ("mark_side", mark_x, "calm")]
        elif t < T["02_vexmore"] + 3.2:  # 2. boss reveal: pan across the bridge
            frame_def = WIDE
            k = ease((t - T["pan_start"]) / (T["pan_end"] - T["pan_start"]))
            cam_x = (MARK_EDGE - 55) + ((VEX_X + 12 - 67) - (MARK_EDGE - 55)) * k
            cast = [("reginald_side", REG_EDGE, None), ("mark_side", MARK_EDGE, "annoyed"), ("villains",)]
        elif t < T["03_reginald"] - 0.1:  # 3. close on the villains
            frame_def = MED
            cam_x = (VEX_X + GRUB_X) / 2 - 45
            cast = [("villains",)]
        elif t < T["04_mark"] - 0.1:  # 4. the heroes
            frame_def = MED
            cam_x = (REG_EDGE + MARK_EDGE) / 2 - 45
            cast = [("reginald_f", REG_EDGE, "shout" if self.talk("reginald", t) else "proud"),
                    ("mark_f", MARK_EDGE, "annoyed")]
        elif t < T["slash"]:  # 5. Mark's idea
            frame_def = CLOSE
            cam_x = MARK_EDGE - 36
            expr = "smirk" if t > T["04_mark"] + 1.2 else "calm"
            cast = [("mark_f", MARK_EDGE, expr)]
        elif t < T["snap"] + 0.1:  # 6. the slash, side view at the post
            frame_def = MED
            cam_x = LEFT_EDGE - 60
            i = min(3, int((t - T["slash"]) / 0.11))
            cast = [("mark_slash", LEFT_EDGE - 14, i), ("villains",)]
        elif t < T["aftermath"]:  # 7. the bridge goes, the camera follows them down
            frame_def = WIDE
            cam_x = RIGHT_EDGE + 12 - 135  # frame the far wall so the bridge is seen swinging over to it
            cast = [("villains",)]
        elif t < T["09_mark"] - 0.1:  # 8. the wizard arrives (wide, so all three fit)
            frame_def = WIDE
            cam_x = 317
            cast = [("reginald_f", REG_EDGE, "shocked"), ("mark_f", MARK_EDGE, "annoyed")]
            k = (t - T["aftermath"]) / 0.9
            wiz_x = 302 + 48 * min(1.0, k)
            cast.insert(0, ("wiz_walk", wiz_x, int(ta * 4) % 2) if k < 1 else ("wiz_f", wiz_x, "confused"))
        elif t < T["leave"]:  # 9. Mark's verdict
            frame_def = CLOSE
            cam_x = MARK_EDGE - 36
            cast = [("mark_f", MARK_EDGE, "calm")]
        else:  # 10. heading home, mission (technically) complete
            frame_def = WIDE
            cam_x = MARK_EDGE - 90
            gone = (t - T["leave"]) * 70
            cast = [("wiz_f", 350, "confused"), ("reginald_f", REG_EDGE, "shocked"),
                    ("mark_home", MARK_EDGE - gone, run_frame)]

        vw, vh, ground_at = frame_def
        cam_y = GROUND - ground_at
        if frame_def is WIDE and T["vex_fall"] <= t < T["aftermath"]:  # tilt down with the fall
            cam_y += (400 - vh - cam_y) * ease((t - T["vex_fall"]) / 0.9)
        cam_x = max(0, min(800 - vw, cam_x))
        cam = (cam_x, cam_y)
        view = compose_view(self.L, cam_x, cam_y, vw, vh)
        self.bridge.draw(view, round(cam_x), round(cam_y), cut=cut)
        for c in cast:
            self.draw_actor(view, c, t, ta, cam)
        splash(view, VEX_X, t - T["vex_splash"], (round(cam_x), round(cam_y)))
        splash(view, GRUB_X, t - T["grub_splash"], (round(cam_x), round(cam_y)))
        return view

    def draw_actor(self, view, c, t, ta, cam):
        T = self.T
        kind = c[0]
        cam = (round(cam[0]), round(cam[1]))
        if kind == "villains":
            vf, gf = max(0.0, t - T["vex_fall"]), max(0.0, t - T["grub_fall"])
            vy = self.vex_y0 + 0.5 * G * vf * vf - (0 if t >= T["snap"] else bob(ta, 0.2))
            gy = self.grub_y0 + 0.5 * G * gf * gf - (0 if t >= T["snap"] else bob(ta, 0.7))
            v_expr = "shocked" if t >= T["snap"] else "smug"
            g_expr = "panic" if t >= T["snap"] else "sneaky"
            put(view, front("vexmore", v_expr, self.talk("vexmore", t)), VEX_X, vy, cam, clip_y=RIVER_Y + 1)
            put(view, front("grub", g_expr, self.talk("grub", t)), GRUB_X, gy, cam, clip_y=RIVER_Y + 1)
            return
        x, arg = c[1], c[2]
        if kind == "mark_f":
            put(view, front("mark", arg, self.talk("mark", t)), x, GROUND - 1 - bob(ta, 0), cam)
        elif kind == "reginald_f":
            put(view, front("reginald", arg, self.talk("reginald", t)), x, GROUND - 1 - bob(ta, 0.5), cam)
        elif kind == "wiz_f":
            put(view, front("bumblewick", arg, self.talk("bumblewick", t)), x, GROUND - 1 - bob(ta, 0.3), cam)
        elif kind == "mark_run":
            put(view, self.mark_run[arg], x, GROUND + 1, cam)
        elif kind == "mark_home":
            put(view, flip(self.mark_run[arg]), x, GROUND + 1, cam)
        elif kind == "reginald_run":
            put(view, self.reg_run[arg], x, GROUND + 1, cam)
        elif kind == "mark_side":
            put(view, self.mark_idle[arg], x, GROUND + 1, cam)
        elif kind == "reginald_side":
            put(view, self.reg_idle, x, GROUND + 1, cam)
        elif kind == "mark_slash":
            put(view, self.mark_slash[arg], x, GROUND + 1, cam)
        elif kind == "wiz_walk":
            put(view, self.wiz_walk[arg], x, GROUND + 1, cam)


def main():
    audio_dir, timings_path, out_mp4 = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    timings = json.load(open(timings_path))
    T, d, audio = build_timeline(audio_dir, timings)
    speaker_of = {l["id"]: l["speaker"] for l in SCRIPT["lines"]}
    by_speaker = {}
    ep = Episode(T, by_speaker)
    finish_timeline(T, d, ep.vex_y0, ep.grub_y0)  # lines after the fall depend on the fall heights
    words = {i: [(w["word"], T[i] + w["start"], T[i] + w["end"]) for w in timings[i]["words"]] for i in audio}
    for i, ws in words.items():
        by_speaker.setdefault(speaker_of[i], []).extend(ws)
    captions = build_captions(T, d, words)
    wav = str(Path(out_mp4).with_suffix(".wav"))
    mix_audio(T, audio, audio_dir, wav)
    n_frames = int(T["end"] * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_mp4],
        stdin=subprocess.PIPE,
    )
    for f in range(n_frames):
        t = f / FPS
        view = ep.frame(t)
        frame = view.resize((OUT_W, OUT_H), Image.NEAREST).convert("RGB")
        if T["snap"] <= t < T["snap"] + 1 / FPS:
            frame = Image.blend(frame, Image.new("RGB", frame.size, "#ffffff"), 0.7)
        draw_banner(frame, t, 0.3, T["run_end"] - 0.6, "QUEST 1", "DEFEAT LORD VEXMORE")
        draw_banner(frame, t, T["pan_end"] - 0.6, T["pan_end"] + 1.6, "BOSS", "LORD VEXMORE", "#c06bff")
        draw_banner(frame, t, T["complete"], T["end"] + 1, "QUEST 1", "QUEST COMPLETE!")
        for cap in captions:
            if cap[0] <= t < cap[1]:
                draw_caption(frame, cap)
                break
        ff.stdin.write(frame.tobytes())
        if f % 240 == 0:
            print(f"frame {f}/{n_frames}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"done: {out_mp4} ({n_frames / FPS:.1f}s)")


if __name__ == "__main__":
    main()
