"""Shorts re-cut of episode 1: cold open on the tree falling, freeze + record scratch, then the tightened story.

Usage: python recut_ep01.py <audio_dir> <timings.json> <out.mp4>
Same audio and timings as render_ep01.py. Drops line 10_mark so the ending goes straight to the narrator.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_ep01 as ep  # noqa: E402
from render_bridge import text_centered  # noqa: E402

FPS, SR = ep.FPS, ep.SR
FREEZE = 1.1
HOOK_TOP = ("HE'S THE ONLY ONE", "WITH COMMON SENSE")


def scratch():
    t = np.arange(int(0.4 * SR)) / SR
    f = 900 * np.exp(-t * 9) + 120
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    noise = np.random.default_rng(1).standard_normal(t.size) * np.exp(-t * 12)
    return (tone * 0.5 + noise * 0.25) * 0.9


def hook_top(frame):
    d = ImageDraw.Draw(frame)
    text_centered(d, HOOK_TOP[0], 44, "#ffffff", 30, stroke=7)
    text_centered(d, HOOK_TOP[1], 44, "#ffd23f", 86, stroke=7)


def main():
    audio_dir, timings_path, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    timings = json.load(open(timings_path))
    lines = {l["id"]: l for l in ep.SCRIPT["lines"] if l["id"] != "10_mark"}
    audio = {i: sf.read(audio_dir / f"{i}.wav")[0] for i in lines}
    fall, t_land, land = ep.simulate_fall()
    T, d, trip = ep.build_timeline(audio, timings, fall, t_land, tight=True)
    words = {i: [(w["word"], T[i] + w["start"], T[i] + w["end"]) for w in timings[i]["words"]] for i in audio}
    by_speaker = {}
    for i, ws in words.items():
        by_speaker.setdefault(lines[i]["speaker"], []).extend(ws)
    captions = ep.build_captions(T, d, words)
    story_wav = str(Path(out).with_suffix(".story.wav"))
    ep.mix_audio(T, audio, audio_dir, story_wav)
    story = sf.read(story_wav)[0]

    # cold open: the tree tipping over and Grub flung off it, cut mid-scream
    c0, c1 = T["release"] - 1.0, T["release"] + 0.7  # tree tipping, Grub flung mid-scream
    cold = story[int(c0 * SR):int(c1 * SR)]
    cut = np.zeros(int(FREEZE * SR))
    sc = scratch()
    cut[: sc.size] += sc
    full = np.concatenate([cold, cut, story])
    wav = str(Path(out).with_suffix(".wav"))
    sf.write(wav, full.astype(np.float32), SR)

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1080x1920",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)

    def caption(frame, t):
        for cap in captions:
            if cap[0] <= t < cap[1]:
                ep.draw_caption(frame, cap)
                break

    # 1) cold open, rendered by its own episode instance (the main one must start from frame 0)
    cold_ep = ep.Episode(T, trip, fall, land, by_speaker)
    n_cold = int((c1 - c0) * FPS)
    last = None
    for f in range(n_cold):
        t = c0 + f / FPS
        frame = cold_ep.frame(t)
        last = frame.copy()
        caption(frame, t)
        ff.stdin.write(frame.tobytes())
    # 2) freeze frame: desaturate, "WAIT... HOW DID WE GET HERE?"
    frozen = ImageEnhance.Color(last).enhance(0.25)
    frozen = ImageEnhance.Brightness(frozen).enhance(0.7)
    for f in range(int(FREEZE * FPS)):
        frame = frozen.copy()
        dd = ImageDraw.Draw(frame)
        text_centered(dd, "WAIT...", 96, "#ffffff", 760)
        if f >= 8:
            text_centered(dd, "HOW DID WE", 64, "#ffd23f", 900)
            text_centered(dd, "GET HERE?", 64, "#ffd23f", 990)
        for y in range(0, 1920, 6):  # rewind scanlines
            if (y // 6 + f) % 9 == 0:
                dd.rectangle([0, y, 1079, y + 2], fill="#ffffff")
        ff.stdin.write(frame.tobytes())
    # 3) the story, tightened
    main_ep = ep.Episode(T, trip, fall, land, by_speaker)
    n = int(T["end"] * FPS)
    for f in range(n):
        t = f / FPS
        frame = main_ep.frame(t)
        ep.draw_banner(frame, t, 0.2, T["dash"] + 1.6, "QUEST 1", "RECOVER THE PIE")
        ep.draw_banner(frame, t, T["complete"], T["end"] + 1, "QUEST 1", "QUEST COMPLETE!")
        if t < T["02_grub"]:
            hook_top(frame)
        caption(frame, t)
        ff.stdin.write(frame.tobytes())
        if f % 240 == 0:
            print(f"frame {f}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    total = n_cold / FPS + FREEZE + n / FPS
    print(f"done: {out} ({total:.1f}s; cold open {n_cold / FPS:.1f}s, story {n / FPS:.1f}s)")


if __name__ == "__main__":
    main()
