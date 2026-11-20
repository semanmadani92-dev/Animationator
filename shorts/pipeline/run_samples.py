"""In-episode samples of run styles A, C and E: the opening run with banner, narration and music.

Usage: python run_samples.py <audio_dir> <timings.json> <out.mp4>
"""
import json
import math
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
from run_options import DASH, SMOOTH, WALK, cycle, foot_speed  # noqa: E402
from side import IDLE, mark_side, reginald_side  # noqa: E402

FPS, SR, SEG = 24, 24000, 7.0
RUN_START = 1.3
REG_SPRINT = cycle(6, 48, 15, 75, 45, sword=-100)  # Reginald's big dramatic strides (option E)


def style(name):
    if name == "A":
        return dict(label="A: SMOOTH RUN", mark=[mark_side(p) for p in SMOOTH], mark_speed=foot_speed(SMOOTH),
                    reg=[reginald_side(p) for p in SMOOTH], reg_speed=foot_speed(SMOOTH), fx=False)
    if name == "C":
        return dict(label="C: ANIME DASH", mark=[mark_side(p) for p in DASH], mark_speed=foot_speed(DASH),
                    reg=[reginald_side(dict(p, na=(-80, -88), fa=(-72, -80))) for p in DASH],
                    reg_speed=foot_speed(DASH), fx=True)
    return dict(label="E: MARK WALKS", mark=[mark_side(p, "annoyed") for p in WALK], mark_speed=foot_speed(WALK),
                reg=[reginald_side(p) for p in REG_SPRINT], reg_speed=foot_speed(REG_SPRINT) * 1.2, fx=False)


def dash_fx(view, t, x_feet, cam):
    d = ImageDraw.Draw(view)
    for i in range(3):
        age = (t * 3 + i / 3) % 1.0
        px_, r = x_feet - 14 - age * 26 - cam[0], 1 + age * 3
        d.ellipse([px_ - r, GROUND - r - age * 3 - cam[1], px_ + r, GROUND + r - age * 3 - cam[1]], fill="#d8cfc0")


def segment_frames(name, level, captions, t0):
    st = style(name)
    for f in range(int(SEG * FPS)):
        t = f / FPS
        k = math.floor(t * 12)
        running = t >= RUN_START
        mx = 70 + max(0.0, t - RUN_START) * st["mark_speed"]
        rx = 46 + max(0.0, t - RUN_START) * st["reg_speed"]
        cam = (max(0, mx - 55), GROUND - 160)
        view = compose_view(level, cam[0], cam[1], 135, 240)
        cam = (round(cam[0]), round(cam[1]))
        if running:
            ep.put(view, st["reg"][(k + 2) % len(st["reg"])], rx, GROUND + 1, cam)
            ep.put(view, st["mark"][k % len(st["mark"])], mx, GROUND + 1, cam)
            if st["fx"]:
                dash_fx(view, t, rx, cam)
                dash_fx(view, t + 0.17, mx, cam)
                d = ImageDraw.Draw(view)
                for i in range(7):
                    y = 60 + (i * 23) % 110
                    x = 135 - (t * 300 + i * 41) % 175
                    d.line([x, y, x + 16, y], fill="#ffffff")
        else:
            ep.put(view, ep.front("reginald", "proud"), rx, GROUND - 1, cam)
            ep.put(view, ep.front("mark", "calm"), mx, GROUND - 1, cam)
        frame = view.resize((1080, 1920), Image.NEAREST).convert("RGB")
        ep.draw_banner(frame, t, 0.3, 4.6, "QUEST 1", "DEFEAT LORD VEXMORE")
        for cap in captions:
            if cap[0] <= t < cap[1]:
                ep.draw_caption(frame, cap)
                break
        d = ImageDraw.Draw(frame)
        w = d.textlength(st["label"], font=ep.font(40))
        d.rectangle([(1080 - w) / 2 - 24, 1840 - 20, (1080 + w) / 2 + 24, 1840 + 56], fill="#120c18")
        d.text(((1080 - w) / 2, 1840), st["label"], font=ep.font(40), fill="#ffd23f")
        yield frame


def main():
    audio_dir, timings, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
    level = build_level()
    line = next(l for l in ep.SCRIPT["lines"] if l["id"] == "01_narrator")
    words = [(w["word"], 0.5 + w["start"], 0.5 + w["end"]) for w in timings["01_narrator"]["words"]]
    narr = sf.read(audio_dir / "01_narrator.wav")[0]
    caps = [(c[0][1], (c[-1][2] + 0.25), "narrator", [w[0] for w in c]) for c in ep.caption_chunks(line, words)]
    for i in range(len(caps) - 1):
        caps[i] = (caps[i][0], caps[i + 1][0], *caps[i][2:])
    # audio: three segments, each narration + music
    n = int(SEG * SR)
    seg = chiptune(SEG) * 0.055
    s = int(0.5 * SR)
    seg[s:s + narr.size] += ep.rms_normalise(narr)[: n - s]
    seg[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))
    wav = str(Path(out).with_suffix(".wav"))
    sf.write(wav, np.tile(seg, 3).astype(np.float32), SR)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    for name in ("A", "C", "E"):
        for frame in segment_frames(name, level, caps, 0):
            ff.stdin.write(frame.tobytes())
        print("rendered", name, flush=True)
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
