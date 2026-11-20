"""Sample of the ninja dash: crouch, launch, zoom-out sprint with speed lines, skid stop at the canyon.

Usage: python dash_sample.py <audio_dir> <timings.json> <out.mp4>
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pixel"))
sys.path.insert(0, str(ROOT / "pipeline"))
import render_bridge as ep  # noqa: E402
from chiptune import chiptune  # noqa: E402
from level import GROUND, build_level, compose_view  # noqa: E402
from run_options import DASH, foot_speed  # noqa: E402
from side import IDLE, mark_side, reginald_side  # noqa: E402

FPS, SR, END = 24, 24000, 8.0
CROUCH_AT, LAUNCH_AT = 1.3, 1.5
MARK_START, MARK_STOP, REG_START, REG_STOP = 70, 414, 46, 388
SKID = 0.45


def ninja_cycle(n=6):
    poses = []
    for k in range(n):
        ph = 2 * math.pi * k / n

        def leg(p):
            th = 48 * math.sin(p) + 10
            return (th, th - (35 + 70 * max(0.0, math.cos(p))))

        poses.append(dict(nl=leg(ph), fl=leg(ph + math.pi), na=(-105, -112), fa=(-98, -106), tilt=48,
                          up=2 + (-1 if abs(math.sin(ph)) > 0.7 else 0), legs=(6, 6), leg_r=1.8, sword=-100))
    return poses


NINJA = ninja_cycle()
CROUCH = dict(nl=(45, -40), fl=(-10, -90), na=(-100, -110), fa=(-95, -105), tilt=60, up=4, legs=(6, 6), leg_r=1.8,
              sword=-100)
SKIDP = dict(nl=(55, 50), fl=(-15, -70), na=(70, 95), fa=(-40, -10), tilt=-12, up=2, legs=(6, 6), leg_r=1.8,
             sword=-110)
V = foot_speed(NINJA, fps=24)  # ground speed that keeps his feet planted at one pose per video frame
REG_V = 70.0


def mark_x(t):
    run = max(0.0, t - LAUNCH_AT)
    accel = 0.2
    x = MARK_START + (V * run * run / (2 * accel) if run < accel else V * (accel / 2 + run - accel))
    skid_from = MARK_STOP - V * SKID / 2
    if x < skid_from:
        return x, "run"
    t_skid_start = LAUNCH_AT + accel + (skid_from - MARK_START - V * accel / 2) / V
    k = min(1.0, (t - t_skid_start) / SKID)
    return skid_from + (MARK_STOP - skid_from) * (1 - (1 - k) ** 2), ("skid" if k < 1 else "stop")


def zoom_w(t):
    k = ep.ease((t - (LAUNCH_AT - 0.1)) / 1.0)
    return 135 + (180 - 135) * k


def main():
    audio_dir, timings, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
    level = build_level()
    print(f"dash speed {V:.0f} px/s")
    ninja = [mark_side(p) for p in NINJA]
    crouch, skid, idle = mark_side(CROUCH), mark_side(SKIDP), mark_side(IDLE, "annoyed")
    reg_run = [reginald_side(p) for p in DASH]
    line = next(l for l in ep.SCRIPT["lines"] if l["id"] == "01_narrator")
    words = [(w["word"], 0.5 + w["start"], 0.5 + w["end"]) for w in timings["01_narrator"]["words"]]
    chunks = ep.caption_chunks(line, words)
    caps = [(c[0][1], chunks[i + 1][0][1] if i + 1 < len(chunks) else c[-1][2] + 0.3, "narrator", [w[0] for w in c])
            for i, c in enumerate(chunks)]

    # find when he starts skidding and stops, for sound effects
    t_skid = next(f / FPS for f in range(int(END * FPS)) if mark_x(f / FPS)[1] != "run" and f / FPS > LAUNCH_AT)
    t_reg_arrive = CROUCH_AT + 0.1 + (REG_STOP - REG_START) / REG_V

    # ---- audio: narration, music, whoosh on launch, skid scrape
    n = int(END * SR)
    mix = chiptune(END) * 0.055
    narr = sf.read(audio_dir / "01_narrator.wav")[0]
    s = int(0.5 * SR)
    mix[s:s + narr.size] += ep.rms_normalise(narr)[: n - s]
    rng = np.random.default_rng(3)
    wl = int(0.55 * SR)
    noise = rng.standard_normal(wl)
    sweep = np.cumsum(noise) * 0.02
    whoosh = (noise - np.convolve(noise, np.ones(30) / 30, "same")) * np.hanning(wl) * 0.22 + sweep * 0
    a = int(LAUNCH_AT * SR)
    mix[a:a + wl] += whoosh[: n - a]
    sl = int(SKID * SR)
    scrape = rng.uniform(-1, 1, sl) * np.linspace(0.25, 0, sl)
    scrape = np.convolve(scrape, np.ones(6) / 6, "same")
    b = int(t_skid * SR)
    mix[b:b + sl] += scrape[: n - b]
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    wav = str(Path(out).with_suffix(".wav"))
    sf.write(wav, mix.astype(np.float32), SR)

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    puffs = []  # (spawn time, x, kind)
    last_puff = 0.0
    for f in range(int(END * FPS)):
        t = f / FPS
        mx, state = mark_x(t)
        dashing = t >= LAUNCH_AT and state == "run"
        rx = min(REG_STOP, REG_START + max(0.0, t - CROUCH_AT - 0.1) * REG_V)
        vw = zoom_w(t)
        vh = vw * 16 / 9
        lead = 0.3 if state == "run" else 0.45
        cam_x = max(0.0, mx - lead * vw) if t >= CROUCH_AT else max(0.0, mx - 55)
        cam_y = GROUND - 0.68 * vh
        view = compose_view(level, cam_x, cam_y, int(vw), int(vh))
        cam = (round(cam_x), round(cam_y))
        # dust: launch burst, trail while dashing, spray while skidding
        if abs(t - LAUNCH_AT) < 0.5 / FPS:
            puffs += [(t, mx - 4 + i * 3, "burst") for i in range(-3, 3)]
        if (dashing or state == "skid") and t - last_puff > 0.06:
            puffs.append((t, mx - 6, "skid" if state == "skid" else "trail"))
            last_puff = t
        d = ImageDraw.Draw(view)
        for born, px_, kind in puffs:
            age = t - born
            if 0 <= age < 0.6:
                r = 1.5 + age * (8 if kind == "burst" else 5)
                lift = age * (10 if kind == "burst" else 4)
                drift = (age * 20 * (1 if px_ > mx else -1)) if kind == "burst" else -age * 10
                col = "#bda98c" if kind == "skid" else "#e2d8c8"
                cx, cy = px_ + drift - cam[0], GROUND - 1 - lift - cam[1]
                d.ellipse([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], fill=col)
        # Reginald trailing behind
        if t < CROUCH_AT + 0.1:
            ep.put(view, ep.front("reginald", "proud"), rx, GROUND - 1, cam)
        elif rx < REG_STOP:
            ep.put(view, reg_run[math.floor(t * 12) % 4], rx, GROUND + 1, cam)
        else:  # arrived: out of breath (mouth flapping open)
            ep.put(view, ep.front("reginald", "shout", int(t * 6) % 2 == 0), rx, GROUND - 1 - (int(t * 4) % 2), cam)
        # Mark
        if t < CROUCH_AT:
            ep.put(view, ep.front("mark", "calm"), mx, GROUND - 1, cam)
        elif t < LAUNCH_AT:
            ep.put(view, crouch, mx, GROUND + 1, cam)
        elif state == "run":
            ep.put(view, ninja[f % len(ninja)], mx, GROUND + 1, cam)  # one pose per video frame: fast legs
        elif state == "skid":
            ep.put(view, skid, mx, GROUND + 1, cam)
        else:
            ep.put(view, idle, mx, GROUND + 1, cam)
        frame = view.resize((1080, 1920), Image.NEAREST).convert("RGB")
        if dashing:  # speed lines in screen space, crisp at any zoom
            fd = ImageDraw.Draw(frame)
            rnd = random.Random(f)
            for _ in range(14):
                y = rnd.randrange(150, 1500)
                x = rnd.randrange(-200, 1080)
                fd.rectangle([x, y, x + rnd.randrange(120, 320), y + 5], fill="#ffffff")
        ep.draw_banner(frame, t, 0.3, 3.6, "QUEST 1", "DEFEAT LORD VEXMORE")
        for cap in caps:
            if cap[0] <= t < cap[1]:
                ep.draw_caption(frame, cap)
                break
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"saved {out} (skid at {t_skid:.2f}s, Reginald arrives {t_reg_arrive:.2f}s)")


if __name__ == "__main__":
    main()
