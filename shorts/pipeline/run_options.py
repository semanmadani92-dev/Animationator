"""Preview video comparing run-cycle styles for Mark, side by side (1080x1920, 24 fps).

Usage: python run_options.py <out.mp4>
"""
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pixel"))
from level import GROUND, build_level, compose_view  # noqa: E402
from side import RUN, mark_side, reginald_side  # noqa: E402

FPS = 24
PW, PH, SCALE = 108, 128, 5  # each panel: 108x128 logical -> 540x640
FONT = ImageFont.truetype(str(ROOT / "pixel" / "fonts" / "PressStart2P-Regular.ttf"), 24)


def cycle(n, thigh_amp, bend_base, bend_extra, arm_amp, **extra):
    """A run/walk cycle of n poses. Knees fold while a leg swings forward; arms swing opposite."""
    poses = []
    for k in range(n):
        ph = 2 * math.pi * k / n

        def leg(p):
            th = thigh_amp * math.sin(p)
            return (th, th - (bend_base + bend_extra * max(0.0, math.cos(p))))

        a = arm_amp * math.sin(ph)
        pose = dict(nl=leg(ph), fl=leg(ph + math.pi), na=(-a, -a + 70), fa=(a, a + 70),
                    up=-1 if abs(math.sin(ph)) > 0.7 else 0, sword=-100)
        pose.update(extra)
        poses.append(pose)
    return poses


def foot_speed(poses, fps=12):  # fps: poses per second
    """Ground speed (px/s) that keeps the planted foot from sliding."""
    th, sh = poses[0].get("legs", (6, 6))
    xs = [th * math.sin(math.radians(p["nl"][0])) + sh * math.sin(math.radians(p["nl"][1])) for p in poses]
    return (max(xs) - min(xs)) / (len(poses) / 2 / fps)


SMOOTH = cycle(6, 32, 10, 60, 35, legs=(5, 5), leg_r=2.0, lean=1)
CHIBI = [
    dict(nl=(30, 20), fl=(-30, -45), na=(-40, 0), fa=(40, 90), up=0, legs=(4, 4), leg_r=2.3, sword=-100),
    dict(nl=(12, -40), fl=(-8, -55), na=(0, 50), fa=(0, 50), up=-3, legs=(4, 4), leg_r=2.3, sword=-100),
    dict(nl=(-30, -45), fl=(30, 20), na=(40, 90), fa=(-40, 0), up=0, legs=(4, 4), leg_r=2.3, sword=-100),
    dict(nl=(-8, -55), fl=(12, -40), na=(0, 50), fa=(0, 50), up=-3, legs=(4, 4), leg_r=2.3, sword=-100),
]
DASH = cycle(6, 50, 15, 80, 0, legs=(6, 6), leg_r=1.8, lean=3, sword=-95)
for p in DASH:  # arms trailing straight back
    p["na"], p["fa"] = (-80, -88), (-72, -80)
CHARGE = cycle(6, 32, 10, 60, 35, legs=(5, 5), leg_r=2.0, lean=1)
for p in CHARGE:  # sword held up and forward
    p["na"], p["sword"] = (135, 150), 165
WALK = cycle(6, 18, 4, 28, 15, legs=(5, 5), leg_r=2.0, sword=25)

OPTIONS = [
    ("CURRENT", [mark_side(p) for p in RUN], None, "stutter"),
    ("A: SMOOTH RUN", [mark_side(p) for p in SMOOTH], foot_speed(SMOOTH), None),
    ("B: CHIBI HOP", [mark_side(p) for p in CHIBI], foot_speed(CHIBI), None),
    ("C: ANIME DASH", [mark_side(p) for p in DASH], foot_speed(DASH), "dash"),
    ("D: HERO CHARGE", [mark_side(p) for p in CHARGE], foot_speed(CHARGE), None),
    ("E: MARK WALKS", [mark_side(p, "annoyed") for p in WALK], foot_speed(WALK), "knight"),
]
REG_RUN = [reginald_side(p) for p in RUN]


def panel(level, label, frames, speed, extra, t):
    speed = speed or 88
    cam_x = (t * speed) % 300
    cam_y = GROUND - 100
    view = compose_view(level, cam_x, cam_y, PW, PH)
    d = ImageDraw.Draw(view)
    k = math.floor(t * 12)  # one pose per 2 video frames: even 12 fps timing
    if extra == "stutter":  # the original timing: 10 fps cycle sampled at 12 fps
        k = int(math.floor(t * 12) / 12 * 10)
    spr = frames[k % len(frames)]
    if extra == "dash":
        for i in range(6):  # speed lines
            y = 30 + (i * 13) % 70
            x = (PW - (t * 260 + i * 37) % (PW + 40))
            d.line([x, y, x + 14, y], fill="#ffffff")
        for i in range(3):  # dust puffs trailing behind
            age = (t * 3 + i / 3) % 1.0
            px_, r = 54 - 12 - age * 26, 1 + age * 3
            d.ellipse([px_ - r, 100 - r - age * 3, px_ + r, 100 + r - age * 3], fill="#d8cfc0")
    if extra == "knight":  # Reginald sprints ahead dramatically while Mark strolls
        rx = (t * 70) % (PW + 60) - 30 + 30
        view.paste(REG_RUN[k % 4], (int(rx - 25), 100 - REG_RUN[0].height + 3), REG_RUN[k % 4])
    view.paste(spr, (54 - spr.width // 2, 101 - spr.height + 1), spr)
    big = view.resize((PW * SCALE, PH * SCALE), Image.NEAREST).convert("RGB")
    bd = ImageDraw.Draw(big)
    w = bd.textlength(label, font=FONT)
    bd.text(((PW * SCALE - w) / 2, 26), label, font=FONT, fill="#ffffff", stroke_width=5, stroke_fill="#120c18")
    bd.rectangle([0, 0, PW * SCALE - 1, PH * SCALE - 1], outline="#120c18", width=4)
    return big


def main():
    out = sys.argv[1]
    level = build_level()
    for label, _, speed, _ in OPTIONS:
        print(f"{label}: ground speed {speed or 88:.0f} px/s")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out],
                          stdin=subprocess.PIPE)
    for f in range(FPS * 6):
        t = f / FPS
        frame = Image.new("RGB", (1080, 1920))
        for i, (label, frames, speed, extra) in enumerate(OPTIONS):
            frame.paste(panel(level, label, frames, speed, extra, t), ((i % 2) * 540, (i // 2) * 640))
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    print("saved", out)


if __name__ == "__main__":
    main()
