# Start here (new chat): Gojo vs Sukuna 3D animations

Everything is in `samples/` on branch `ccr-326e19d9-4eyypr` of `semanmadani92-dev/Animationator`.
All rendering is done in the cloud container with Blender as a Python module. The user's laptop can't run 3D apps.

## What's been made
| Video | Script | What happens |
|---|---|---|
| `fight_sample.mp4` (committed) | `samples/fight_sample/fight.py` | Two mannequin dummies: jab, cross, front kick, knockback. 170 frames. |
| `gojo_vs_sukuna.mp4` (not committed) | `samples/jjk/fight_jjk.py` | The same fight with the Gojo and Sukuna models. |
| `hollow_purple_vaporise.mp4` (not committed) | `samples/jjk/hollow_purple.py` + `vaporise.py` + `hollow_purple_sfx.py` | Gojo charges blue, then red; they spiral together into purple; he fires; Sukuna is vaporised into embers. Has sound. 6.7 s, 720p, 30 fps. |

The videos and model files are left out of git on purpose because they're fan content of copyrighted characters. Re-render them with the commands below.

## The 3D models
- **Source:** https://github.com/hoch98/3D-Model-Animation-Test, in the folder `model/jjk/`.
  - The repo code is under the MIT licence.
  - The models are fan models by https://www.deviantart.com/risqi26.
- **Characters:**
  - `gojo/gojo.fbx`
  - `yuji/yuji.fbx`
  - `megumi/megumi.fbx` (unused)
  - `nobara/nobara.fbx` (unused)
- **Format:** each model is a Mixamo rig (bones named `mixamorig:*`) with one texture png.
- **Download:** `bash samples/jjk/get_models.sh ~/jjk_models` puts them in `~/jjk_models/<name>/`.
- **Sukuna doesn't exist as a model.** `samples/jjk/sukuna.py` turns Yuji into Sukuna by painting Sukuna's face markings (two lines under each eye) and red eyes into a copy of Yuji's texture. Its `sukuna.apply(objects)` does this at load time.
- **Copyright:** a personal fan video is fine. Monetised uploads can get copyright claims, because Jujutsu Kaisen is copyrighted.
- **Missing maps are harmless.** Cycles warns "Failed to load 4 image files": the FBX files point to the original author's `C:\Users\...` normal maps. They aren't needed, and the models look right without them.

## Setup in a fresh container
```
bash toolkit/setup.sh blender                   # bpy 5.3 -> ~/blendervenv/bin/python
bash samples/jjk/get_models.sh ~/jjk_models
```
The animation clips come from the CC0 mannequin pack in `toolkit/3d-pack/animation/`:
- `UAL1_unreal_rig_45anims.glb`
- `UAL2_mannequin_43anims.glb`

## Commands
```
cd samples/jjk
# Hollow Purple + vaporise (full 720p render about 1-1.5 h; previews about 1 min)
~/blendervenv/bin/python hollow_purple.py -- preview OUT ~/jjk_models 112,119,130     # 640x360 stills
~/blendervenv/bin/python hollow_purple.py -- final   OUT ~/jjk_models [a-b]           # OUT/hpf_####.png
~/blendervenv/bin/python hollow_purple_sfx.py OUT/sfx.wav                            # numpy only, 2 s
ffmpeg -framerate 30 -i OUT/hpf_%04d.png -i OUT/sfx.wav -c:v libx264 -pix_fmt yuv420p -crf 18 \
       -c:a aac -b:a 192k -shortest -movflags +faststart hollow_purple.mp4

# Gojo vs Sukuna fight (needs the mannequin fight scene first)
~/blendervenv/bin/python ../fight_sample/fight.py -- scene OUT
~/blendervenv/bin/python fight_jjk.py -- preview|final OUT ~/jjk_models
```

## How it works
- **`layers.py`:** blends animation clips. Each frame is a stack of clips (idle, spell, shoot, hit) mixed with smoothstep envelopes `env(t, a, b, c, d)`, then baked, so switching clips never pops.
- **`../characters/mbchar.py` `Retarget`:** copies the mannequin's motion onto the Mixamo rigs.
  - It works with world-space bone rotation deltas: `T_pose = S_pose @ S_rest^-1 @ align @ T_rest`.
  - The hips' position is scaled by the ratio of the two rigs' hip heights.
  - The bone-name maps are `MIXAMO` and `MAP` (MB-Lab).
- **`hollow_purple.py`:**
  - **Timing (frames):**
    - Blue appears at 26 and red at 40.
    - They spiral from 58 and merge at 84.
    - Gojo shoots at 100, the sphere launches at 103 and hits at 113.
    - Gojo's exit animation starts at 140; the clip ends at 200.
  - **Orbs:** each orb has a white-centre emissive core, a volume halo, 3 rings of sparks and a point light. The purple core has moving plasma noise.
  - **Other effects:** a beam trail, a glowing scorch line on the floor, a shockwave ring, a flash light, and a bloom compositor.
  - **Shots:**
    - close on Gojo
    - wide side shot at the shot
    - close on Sukuna from frame 116
    - from behind Gojo from frame 166
- **`vaporise.py`:**
  - A per-vertex `vap` attribute gives the burn order: distance from the chest plus noise.
  - Every Sukuna material gets a heat glow and a white-hot burning edge, and is cut to transparent where it has burned.
  - Embers are a geometry-nodes point cloud. Each point is born where and when the surface burns away, then drifts with the blast and cools to ash.
- **`hollow_purple_sfx.py`:** all sounds are synthesised with numpy (oscillators, FFT filters, a sweeping filter, a noise reverb). Its timings mirror the frame numbers above, so if you change one, change both.

## Blender 5.3 gotchas (all already handled in the code)
- **Use Cycles on the CPU only.** EEVEE, Workbench and the GPU compositor crash because libEGL is missing.
  - Set `S.render.compositor_device = "CPU"`.
- **Compositor setup:** create it with `bpy.data.node_groups.new(..., "CompositorNodeTree")` and set `S.compositing_node_group`. Glare inputs are sockets, e.g. `inputs["Type"] = "Bloom"`.
- **Action F-curves** live at `act.layers[0].strips[0].channelbags[0].fcurves`.
- **glTF clips** also key the rig object's transform. Bake new actions, or parent the rig to an empty.
- **FBX Mixamo rigs** come in with rotation (90°, 0, 0) and scale 0.01. Keep `base = tgt.matrix_world` and set `tgt.matrix_world = src.matrix_world.normalized() @ base` each frame.
- **Additive glow materials** use Add(Transparent, Emission × factor). A Mix shader goes black when the strength is 0.

## Other files
- `samples/characters/characters.py`, `fighters.py`: the user's first self-made designs (primitives, then MB-Lab). The user disliked them, so the project switched to the downloaded models.
- **MB-Lab:** only its data is used (https://github.com/animate1978/MB-Lab, AGPL). Its add-on code was never run. `mbchar.py` reads that data from the path in the `MBLAB_DATA` environment variable; `hollow_purple.py` and `fight_jjk.py` only import `Retarget` and don't need it.

## About the user
- Short, skimmable answers.
- Prefers downloaded models over self-made ones.
- Push only to the branch the user names.
- Ideas the user hasn't asked for yet:
  - a slower burn-away
  - slow motion at the impact
  - joining the fight and Hollow Purple into one video
  - using Megumi or Nobara
