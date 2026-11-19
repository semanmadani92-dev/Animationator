"""Render episode 1, "The Bridge": 1080x1920, 24 fps, pixel art scaled with nearest-neighbour.

Usage: python render_ep01.py <audio_dir> <timings.json> <out.mp4>
audio_dir holds one WAV per script line id (24 kHz mono) plus sfx_snap.wav and sfx_fall.wav.
Characters animate on twos (12 fps); camera cuts and captions run at the full 24 fps.
"""
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
from bridge import build_backdrop, deck_y, draw_bridge  # noqa: E402
from cast import BUILDERS  # noqa: E402
from chiptune import chiptune  # noqa: E402
from mark import build_mark  # noqa: E402
from village import build_village  # noqa: E402

FPS, SR = 24, 24000
OUT_W, OUT_H = 1080, 1920
FONT = str(ROOT / "pixel" / "fonts" / "PressStart2P-Regular.ttf")
SCRIPT = json.load(open(ROOT / "episodes" / "ep01_bridge" / "script.json"))
COLOR = {"narrator": "#38c8f0", "mark": "#ff4a4a", "reginald": "#ffd23f", "vexmore": "#c06bff",
         "grub": "#6ad84a", "bumblewick": "#6aa8ff"}
NAME = {"mark": "MARK", "reginald": "SIR REGINALD", "vexmore": "LORD VEXMORE", "grub": "GRUB",
        "bumblewick": "BUMBLEWICK"}


# ---------------------------------------------------------------- audio + timeline
def build_timeline(audio_dir, timings):
    lines = {l["id"]: l for l in SCRIPT["lines"]}
    audio = {i: sf.read(audio_dir / f"{i}.wav")[0] for i in lines if "text" in lines[i]}
    dur = {i: len(a) / SR for i, a in audio.items()}
    T = {}
    T["01_narrator"] = 0.3
    T["02_vexmore"] = T["01_narrator"] + dur["01_narrator"] + 0.5
    T["03_reginald"] = T["02_vexmore"] + dur["02_vexmore"] + 0.35
    T["04_mark"] = T["03_reginald"] + dur["03_reginald"] + 0.45
    T["snap"] = T["04_mark"] + dur["04_mark"] + 0.25
    T["06_vexmore"] = T["snap"] + 0.6
    T["fall"] = T["06_vexmore"] + dur["06_vexmore"] + 0.15
    T["07_grub"] = T["fall"] + 0.1
    T["08_bumblewick"] = T["07_grub"] + dur["07_grub"] + 0.7
    T["09_mark"] = T["08_bumblewick"] + dur["08_bumblewick"] + 0.5
    T["end"] = T["09_mark"] + dur["09_mark"] + 1.8
    # word intervals in absolute time, per line
    words = {i: [(w["word"], T[i] + w["start"], T[i] + w["end"]) for w in timings[i]["words"]] for i in audio}
    return T, dur, audio, words


def rms_normalise(y, target=0.09):
    r = np.sqrt(np.mean(y ** 2)) + 1e-9
    y = y * (target / r)
    peak = np.abs(y).max()
    return y * (0.95 / peak) if peak > 0.95 else y


def mix_audio(T, audio, audio_dir, out_wav):
    n = int(T["end"] * SR)
    voice = np.zeros(n)
    for i, y in audio.items():
        s = int(T[i] * SR)
        y = rms_normalise(y.astype(np.float64))
        voice[s:s + y.size] += y[: max(0, n - s)]
    for name, at, gain in (("sfx_snap", T["snap"], 1.4), ("sfx_fall", T["fall"], 1.0)):
        y = sf.read(audio_dir / f"{name}.wav")[0] * gain
        s = int(at * SR)
        voice[s:s + y.size] += y[: max(0, n - s)]
    music = chiptune(T["end"]) * 0.06
    # comic silence: music cuts at the snap and fades back in for the aftermath
    t = np.arange(n) / SR
    env = np.ones(n)
    env[(t >= T["snap"]) & (t < T["08_bumblewick"])] = 0.0
    back = (t >= T["08_bumblewick"]) & (t < T["08_bumblewick"] + 1.0)
    env[back] = (t[back] - T["08_bumblewick"]) / 1.0
    env[t > T["end"] - 1.0] *= np.clip((T["end"] - t[t > T["end"] - 1.0]), 0, 1)
    mix = voice + music * env
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    sf.write(out_wav, mix.astype(np.float32), SR)


# ---------------------------------------------------------------- captions
FILLER = {"the", "a", "an", "of", "to", "in", "this", "that", "will", "shall", "could", "just", "is", "was",
          "for", "and", "but", "it", "i", "you", "at", "be", "so", "lets", "every", "gets", "take", "do", "least"}


def caption_chunks(line, words):
    """Split a line into 1-4 word chunks; the last word of each chunk is shown big, so never end on filler."""
    keys = {re.sub(r"[^a-z]", "", k.lower()) for k in line.get("keywords", [])}
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        bare = re.sub(r"[^a-z]", "", w[0].lower())
        punct = w[0][-1] in ".!?,"
        filler = bare in FILLER
        if bare in keys or (punct and not filler) or (len(cur) >= 3 and not filler) or len(cur) >= 5:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_captions(T, dur, words):
    caps = []
    for line in SCRIPT["lines"]:
        if "text" not in line:
            continue
        chunks = caption_chunks(line, words[line["id"]])
        for k, ch in enumerate(chunks):
            start = ch[0][1]
            end = chunks[k + 1][0][1] if k + 1 < len(chunks) else T[line["id"]] + dur[line["id"]] + 0.25
            caps.append((start, end, line["speaker"], [w[0] for w in ch]))
    return caps


_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


def draw_text_centered(d, text, size, color, y, stroke=8):
    f = font(size)
    w = d.textlength(text, font=f)
    while w > OUT_W - 60 and size > 24:
        size -= 8
        f = font(size)
        w = d.textlength(text, font=f)
    x = (OUT_W - w) / 2
    d.text((x, y + 8), text, font=f, fill="#000000", stroke_width=stroke, stroke_fill="#000000")
    d.text((x, y), text, font=f, fill=color, stroke_width=stroke, stroke_fill="#120c18")


def draw_caption(frame, cap):
    _, _, speaker, ws = cap
    d = ImageDraw.Draw(frame)
    y = 1600
    if speaker != "narrator":
        draw_text_centered(d, NAME[speaker], 40, COLOR[speaker], y - 76, stroke=7)
    head = " ".join(ws[:-1])
    if head:
        draw_text_centered(d, head, 48, "#ffffff", y)
    draw_text_centered(d, ws[-1].upper(), 80, COLOR[speaker], y + 78)


# ---------------------------------------------------------------- characters
def talking(words_by_speaker, speaker, t):
    for _, a, b in words_by_speaker.get(speaker, []):
        if a <= t <= b:
            return int(t * 8) % 2 == 0
    return False


def sprite(name, expr, talk, pose="stand"):
    if name == "mark":
        return build_mark(expr, talk, pose)
    return BUILDERS[name](expr, talk)


def place(scene, spr, x, feet_y):
    scene.paste(spr, (round(x), round(feet_y - spr.height + 1)), spr)


def bob(t, phase):
    return int(t * 2 + phase) % 2  # 1px idle breathing, twice a second


# ---------------------------------------------------------------- shots
def render_frame(t, T, words_by_speaker, backdrops):
    ta = math.floor(t * 12) / 12  # character animation on twos
    talk = lambda s: talking(words_by_speaker, s, t)  # noqa: E731

    if t < T["02_vexmore"] - 0.15:  # Shot A: village intro
        scene = backdrops["village"].copy()
        walk_end = 3.0
        k = min(1.0, max(0.0, (t - 0.3) / (walk_end - 0.3)))
        walking = 0.3 <= t < walk_end
        pose = ("walk1" if int(ta * 6) % 2 else "walk2") if walking else "stand"
        mx = -36 + (27 + 36) * k
        rx = -75 + (75 - 4) * k
        expr = "annoyed" if t > T["01_narrator"] + 3.6 else "calm"
        place(scene, sprite("reginald", "proud", False), rx, 134 - (0 if walking else bob(ta, 0.5)))
        place(scene, sprite("mark", expr, False, pose), mx, 134 - (0 if walking else bob(ta, 0)))
        return scene, (0, 0, 90, 160)

    scene = backdrops["bridge"].copy()
    cut_t = t - T["snap"] if t >= T["snap"] else None
    draw_bridge(scene, cut_t)

    def villains():
        fall = max(0.0, t - T["fall"])
        vy = round(deck_y(90)) + 1 + 0.5 * 170 * fall ** 2
        gy = round(deck_y(108)) + 1 + 0.5 * 170 * max(0.0, fall - 0.15) ** 2
        v_expr = "shocked" if t >= T["snap"] else "smug"
        g_expr = "panic" if t >= T["snap"] else "sneaky"
        place(scene, sprite("vexmore", v_expr, talk("vexmore")), 72, vy - (0 if cut_t else bob(ta, 0.2)))
        place(scene, sprite("grub", g_expr, talk("grub")), 96 + (3 * math.sin(fall * 20) if fall else 0),
              gy - (0 if cut_t else bob(ta, 0.7)))

    if t < T["03_reginald"] - 0.1:  # Shot B: villain monologue
        villains()
        return scene, (45, 0, 90, 160)
    if t < T["04_mark"] - 0.1:  # Shot C: the knight's boast
        villains()
        place(scene, sprite("reginald", "proud" if not talk("reginald") else "shout", talk("reginald")), 2,
              103 - bob(ta, 0.5))
        place(scene, sprite("mark", "annoyed", False), 26, 103 - bob(ta, 0))
        return scene, (0, 20, 72, 128)
    if t < T["snap"] + 0.35:  # Shot D: Mark's simple solution
        pose = "swing" if t >= T["snap"] - 0.08 else "stand"
        expr = "smirk" if t >= T["04_mark"] + 1.0 else "calm"
        villains()
        place(scene, sprite("mark", expr, talk("mark"), pose), 26, 103 - bob(ta, 0))
        return scene, (17, 40, 54, 96)
    if t < T["08_bumblewick"] - 0.1:  # Shot E: the bridge goes down
        villains()
        return scene, (45, 0, 90, 160)
    if t < T["09_mark"] - 0.1:  # Shot F: the wizard arrives, the knight mourns his duel
        k = min(1.0, (t - (T["08_bumblewick"] - 0.1)) / 0.6)
        place(scene, sprite("bumblewick", "confused", talk("bumblewick")), -36 + 38 * k, 103 - bob(ta, 0.3))
        place(scene, sprite("reginald", "shocked", False), 34, 103 - bob(ta, 0.6))
        return scene, (0, 0, 90, 160)
    # Shot G: Mark wraps it up and walks home
    leave = max(0.0, t - (T["09_mark"] + 0.3 + 3.6))
    walking = leave > 0
    pose = ("walk1" if int(ta * 6) % 2 else "walk2") if walking else "stand"
    flipped = sprite("mark", "calm" if not walking else "annoyed", talk("mark"), pose)
    if walking:
        flipped = flipped.transpose(Image.FLIP_LEFT_RIGHT)
    place(scene, flipped, 26 - 30 * leave, 103 - (0 if walking else bob(ta, 0)))
    return scene, (17, 40, 54, 96)


def main():
    audio_dir, timings_path, out_mp4 = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    timings = json.load(open(timings_path))
    T, dur, audio, words = build_timeline(audio_dir, timings)
    speaker_of = {l["id"]: l.get("speaker") for l in SCRIPT["lines"]}
    words_by_speaker = {}
    for i, ws in words.items():
        words_by_speaker.setdefault(speaker_of[i], []).extend(ws)
    captions = build_captions(T, dur, words)
    wav = str(Path(out_mp4).with_suffix(".wav"))
    mix_audio(T, audio, audio_dir, wav)
    backdrops = {"village": build_village().convert("RGBA"), "bridge": build_backdrop().convert("RGBA")}
    n_frames = int(T["end"] * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_mp4],
        stdin=subprocess.PIPE,
    )
    for f in range(n_frames):
        t = f / FPS
        scene, (x0, y0, vw, vh) = render_frame(t, T, words_by_speaker, backdrops)
        frame = scene.crop((x0, y0, x0 + vw, y0 + vh)).resize((OUT_W, OUT_H), Image.NEAREST).convert("RGB")
        if T["snap"] <= t < T["snap"] + 2 / FPS:
            frame = Image.blend(frame, Image.new("RGB", frame.size, "#ffffff"), 0.75)
        for cap in captions:
            if cap[0] <= t < cap[1]:
                draw_caption(frame, cap)
                break
        ff.stdin.write(frame.tobytes())
        if f % 120 == 0:
            print(f"frame {f}/{n_frames}", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"done: {out_mp4} ({n_frames / FPS:.1f}s)")


if __name__ == "__main__":
    main()
