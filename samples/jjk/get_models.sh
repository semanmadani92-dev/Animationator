#!/usr/bin/env bash
# Download the Gojo and Yuji (-> Sukuna) models used by the scripts in this folder.
#   bash samples/jjk/get_models.sh [MODELS_DIR]        (default: ~/jjk_models)
# Result: MODELS_DIR/gojo/gojo.fbx + gojo.png, MODELS_DIR/yuji/yuji.fbx + yuji.png
# (also megumi/ and nobara/). Source: github.com/hoch98/3D-Model-Animation-Test (MIT code;
# the models themselves are fan models by deviantart.com/risqi26 of Jujutsu Kaisen characters).
set -euo pipefail
OUT="${1:-$HOME/jjk_models}"
TMP="$(mktemp -d)"
git clone -q --depth 1 --filter=blob:none --sparse https://github.com/hoch98/3D-Model-Animation-Test "$TMP/src"
git -C "$TMP/src" sparse-checkout set model/jjk/gojo model/jjk/yuji model/jjk/megumi model/jjk/nobara
mkdir -p "$OUT"
cp -r "$TMP/src/model/jjk/"{gojo,yuji,megumi,nobara} "$OUT/"
rm -rf "$TMP"
ls -R "$OUT"
