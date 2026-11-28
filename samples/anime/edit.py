"""Final edit for the anime-vs-SCP Shorts: a short cold open (a few frames from the climax), then the
whole clip, upscaled to 1080x1920, with captions.

  python3 edit.py FRAMES_DIR PREFIX SFX.wav OUT.mp4 --cold 312-333 \
      --text "SCP-173 MOVES WHEN YOU BLINK@0-3.2" --text "HE DIDN'T EVEN MOVE@11.1-13.6" \
      --credit "SCP-173 by Moto42 - CC BY-SA 3.0@16"
Times are in seconds of the finished video (the cold open is included).
"""
import argparse, subprocess

FONT = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
ap = argparse.ArgumentParser()
ap.add_argument("frames"); ap.add_argument("prefix"); ap.add_argument("sfx"); ap.add_argument("out")
ap.add_argument("--cold", default=None, help="first-last frame of the cold open")
ap.add_argument("--text", action="append", default=[], help="TEXT@start-end (big caption near the top)")
ap.add_argument("--credit", action="append", default=[], help="TEXT@start (small line near the bottom)")
a = ap.parse_args()


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "’").replace(":", "\\:").replace("%", "\\%")


f = []
if a.cold:
    c0, c1 = map(int, a.cold.split("-"))
    s0, s1 = c0 / 30, (c1 + 1) / 30
    f += ["[0:v]split[v1][v2]", f"[v1]trim=start_frame={c0}:end_frame={c1 + 1},setpts=PTS-STARTPTS[cv]", "[v2]setpts=PTS-STARTPTS[mv]",
          "[1:a]asplit[a1][a2]", f"[a1]atrim=start={s0:.3f}:end={s1:.3f},asetpts=PTS-STARTPTS,afade=t=out:st={s1 - s0 - 0.15:.3f}:d=0.15[ca]",
          "[a2]asetpts=PTS-STARTPTS[ma]", "[cv][ca][mv][ma]concat=n=2:v=1:a=1[v][a]"]
    src, aud = "[v]", "[a]"
else:
    src, aud = "[0:v]", "1:a"
draw = [f"{src}scale=1080:1920:flags=lanczos"]
for k, item in enumerate(a.text):
    txt, span = item.rsplit("@", 1); t0, t1 = span.split("-")
    lines = txt.split("|")
    for j, ln in enumerate(lines):
        draw.append(f"drawtext=fontfile={FONT}:text='{esc(ln)}':fontsize=56:fontcolor=white:borderw=6:bordercolor=black:"
                    f"x=(w-tw)/2:y={250 + j * 72}:enable='between(t,{t0},{t1})'")
for item in a.credit:
    txt, t0 = item.rsplit("@", 1)
    for j, ln in enumerate(txt.split("|")):
        draw.append(f"drawtext=fontfile={FONT}:text='{esc(ln)}':fontsize=28:fontcolor=white@0.85:borderw=3:bordercolor=black:"
                    f"x=(w-tw)/2:y=h-210+{j * 38}:enable='gt(t,{t0})'")
f.append(",".join(draw) + "[vo]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", f"{a.frames}/{a.prefix}_%04d.png", "-i", a.sfx,
       "-filter_complex", ";\n".join(f), "-map", "[vo]", "-map", aud if a.cold else "1:a",
       "-c:v", "libx264", "-crf", "19", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
       "-shortest", "-movflags", "+faststart", a.out]
subprocess.run(cmd, check=True)
print("saved", a.out)
