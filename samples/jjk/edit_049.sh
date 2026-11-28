#!/usr/bin/env bash
# Final edit for Gojo vs SCP-049: a 0.7 s cold open on the frozen hand, then the whole fight,
# upscaled to 1080x1920 with the hook text and the SCP credit.
#   bash edit_049.sh FRAMES_DIR SFX_WAV OUT.mp4
set -e
F=$1; A=$2; OUT=$3
FONT=/usr/share/fonts/opentype/inter/Inter-Bold.otf
HOOK="SCP-049 TRIED TO TOUCH GOJO"
CREDIT="SCP-049 by Gabriel Jade - CC BY-SA 3.0"
ffmpeg -y -loglevel error -framerate 30 -i "$F/g49_%04d.png" -i "$A" -filter_complex "
[0:v]split[v1][v2];
[v1]trim=start_frame=78:end_frame=99,setpts=PTS-STARTPTS[cv];
[v2]setpts=PTS-STARTPTS[mv];
[1:a]asplit[a1][a2];
[a1]atrim=start=2.6:end=3.3,asetpts=PTS-STARTPTS,afade=t=out:st=0.55:d=0.15[ca];
[a2]asetpts=PTS-STARTPTS[ma];
[cv][ca][mv][ma]concat=n=2:v=1:a=1[v][a];
[v]scale=1080:1920:flags=lanczos,
drawtext=fontfile=$FONT:text='$HOOK':fontsize=54:fontcolor=white:borderw=6:bordercolor=black:x=(w-tw)/2:y=250:enable='lt(t,3.2)',
drawtext=fontfile=$FONT:text='$CREDIT':fontsize=30:fontcolor=white@0.85:borderw=3:bordercolor=black:x=(w-tw)/2:y=h-170:enable='gt(t,8.6)'[vo]" \
  -map "[vo]" -map "[a]" -c:v libx264 -crf 19 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$OUT"
echo "saved $OUT"
