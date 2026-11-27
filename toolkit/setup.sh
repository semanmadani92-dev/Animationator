#!/usr/bin/env bash
# Installs the toolkit in a fresh container. Run from the repo root or this folder.
#   bash toolkit/setup.sh voice     voice AI (Qwen3-TTS + faster-whisper), ~10 min
#   bash toolkit/setup.sh blender   Blender as a Python module (bpy 5.3), ~2 min
#   bash toolkit/setup.sh all       both
set -e
cd "$(dirname "$0")"
want=${1:-all}
py313() { command -v python3.13 || { command -v uv >/dev/null || pip install -q uv; uv python install 3.13 >/dev/null; uv python find 3.13; }; }
if [ "$want" = voice ] || [ "$want" = all ]; then
  python3 -m venv ~/voicevenv
  ~/voicevenv/bin/pip install -q qwen-tts==0.1.1 transformers==4.57.3 soundfile faster-whisper==1.2.1 numpy
  echo "Voice ready:  ~/voicevenv/bin/python toolkit/voice/tools/design_voice.py text.txt out.wav \"a deep calm man\""
fi
if [ "$want" = blender ] || [ "$want" = all ]; then
  "$(py313)" -m venv ~/blendervenv
  ~/blendervenv/bin/pip install -q bpy==5.3.0
  echo "Blender ready: ~/blendervenv/bin/python toolkit/blender/fbx2glb.py in_dir out_dir"
fi
