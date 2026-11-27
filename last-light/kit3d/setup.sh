#!/usr/bin/env bash
# Rebuilds everything the 3D kit needs that is too big for git. Run from last-light/kit3d.
# Usage: bash setup.sh            (renderer only, about 1 minute)
#        bash setup.sh voice      (also the voice + timing tools, about 10 minutes, ~8 GB)
set -e
cd "$(dirname "$0")"
# three.js 0.170.0 next to the kit
if [ ! -f three.module.js ]; then
  tmp=$(mktemp -d); (cd "$tmp" && npm pack three@0.170.0 >/dev/null && tar xzf three-0.170.0.tgz)
  cp "$tmp/package/build/three.module.js" "$tmp/package/build/three.core.js" . 2>/dev/null || cp "$tmp/package/build/three.module.js" .
  cp -r "$tmp/package/examples/jsm" jsm; rm -rf "$tmp"
fi
[ -e ll.js ] || ln -s ../kit/ll.js ll.js
[ -e assets ] || ln -s ../assets3d assets
command -v ffmpeg >/dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg)
if [ "$1" = voice ]; then
  V=${VENV:-$HOME/llvenv}
  python3 -m venv "$V"
  "$V/bin/pip" install -q qwen-tts==0.1.1 transformers==4.57.3 soundfile faster-whisper==1.2.1 librosa numpy
  echo "Voice env ready: $V (speak lines with: $V/bin/python ../../voices/tools/clone_lines.py jobs.json outdir)"
fi
echo "Kit ready. Test: node shoot3d.js scp049 stills:1,5"
