"""Goku vs SCP-682 (vertical Short, ~20 s). 682 roars in the containment hall. Goku drops in, one punch
throws it down the hall. It regenerates, bigger. Goku goes Super Saiyan and fires a Kamehameha that
burns it away... but one small piece on the scorched floor is still twitching.

  ~/blendervenv/bin/python goku_vs_682.py -- preview|final OUT ANIME_MODELS SCP682_GLB [frames | a-b]
  ANIME_MODELS holds goku/scene.gltf (python3 get_models.py ~/anime_models).
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Quaternion
args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT, MODELS, GLB682 = args[0], args[1], args[2], args[3]
bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vslib as K
import vaporise
L, V, S, sm, env = K.L, K.V, K.S, K.sm, K.env

# ---------------------------------------------------------------- timing (30 fps)
ROAR0, ROAR1 = 14, 62           # 682 roars
DROP, LAND = 70, 90             # Goku falls from the ceiling
CHARGE, PUNCH = 128, 164        # 682 charges; the punch lands
SLAM = 192                      # 682 hits the floor far down the hall
REGEN, RISE, ROAR2 = 206, 226, 250   # it heals, gets up bigger, roars again
SSJ0, SSJ = 282, 312            # Goku powers up; Super Saiyan
KCHARGE, CHARGE2, FIRE, HIT = 334, 352, 376, 381   # Kamehameha
BURN = 44
POWERDOWN = 452
END = 600
BEAM_C = (0.45, 0.8, 1.0)
GOLD = (1.0, 0.72, 0.16)
S.render.fps = 30; S.frame_start, S.frame_end = 0, END
A = K.clips()

# ---------------------------------------------------------------- SCP-682 (the low-poly reptile from last-light/kit3d, posed by its joint empties)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB682)
R = {o.name: o for o in bpy.data.objects if o not in before}
root = R["SCP682"]
for o in R.values():
    o.rotation_mode = "XYZ"
M682 = [o for o in R.values() if o.type == "MESH"]
for m in {s.material for o in M682 for s in o.material_slots if s.material}:      # wet, bumpy hide
    b = m.node_tree.nodes.get("Principled BSDF")
    if not b: continue
    b.inputs["Roughness"].default_value = 0.42; b.inputs["Coat Weight"].default_value = 0.25
    nz = m.node_tree.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18; nz.inputs["Detail"].default_value = 8
    bp = m.node_tree.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    m.node_tree.links.new(nz.outputs["Fac"], bp.inputs["Height"]); m.node_tree.links.new(bp.outputs[0], b.inputs["Normal"])
EYES = [o for o in M682 if o.parent and o.parent.name == "head" and o.name.startswith("eye")]
eye_m, eye_s = V.emit_mat("682Eye", (1.0, 0.35, 0.05))
for e in EYES: e.data.materials.clear(); e.data.materials.append(eye_m)


def x682(t):
    """root y, z, roll about its long axis, scale, gait speed"""
    TAU = 2 * math.pi
    if t < CHARGE: return -8.5, 0, 0, 1.0, 0.0
    if t < PUNCH: u = (t - CHARGE) / (PUNCH - CHARGE); return -8.5 + 6.1 * u ** 1.2, 0, 0, 1.0, 1.0
    if t < SLAM:                                                   # thrown: one full spin, lands on its side
        u = (t - PUNCH) / (SLAM - PUNCH)
        return -2.4 - 10.0 * (1 - (1 - u) ** 1.8), 1.6 * math.sin(math.pi * u), (TAU + 1.4) * u, 1.0, 0.0
    grow = 1.0 + 0.35 * sm((t - RISE) / 30)
    y = -12.4 - 0.6 * sm((t - SLAM) / 10)
    roll = TAU + 1.4 * (1 - sm((t - RISE) / 16))
    if t < CHARGE2: return y, 0, roll, grow, 0.0
    u = min(1, (t - CHARGE2) / (HIT - CHARGE2))
    return y + 6.0 * u ** 1.1, 0, roll, grow, 1.0 if t < HIT else 0.0


gait = 0.0
HEAD682 = {}
for t in range(END + 1):
    y, z, roll, sc, spd = x682(t)
    gait += spd * 0.55
    root.location = (0, y, z); root.rotation_euler = (0, roll, math.pi); root.scale = (sc,) * 3
    for k, off in ((0, 0), (3, 0), (1, math.pi), (2, math.pi)):
        R[f"hip{k}"].rotation_euler.x = 0.55 * math.sin(gait + off) * spd
        R[f"knee{k}"].rotation_euler.x = -0.6 * max(0, math.sin(gait + off + 1.2)) * spd
    for k in range(7):
        R[f"tail{k}"].rotation_euler.z = 0.12 * math.sin(t * 0.09 + gait * 0.5 - k * 0.6)
        R[f"tail{k}"].rotation_euler.x = 0.05 * math.sin(t * 0.07 - k * 0.4)
    roar = env(t, ROAR0, ROAR0 + 8, ROAR1 - 10, ROAR1) + env(t, ROAR2, ROAR2 + 6, ROAR2 + 30, ROAR2 + 40) + 0.6 * env(t, CHARGE2, CHARGE2 + 6, HIT, HIT + 4)
    shake = 0.04 * math.sin(t * 2.7) * roar
    R["neck"].rotation_euler.x = -0.3 * roar + 0.05 * math.sin(t * 0.06)
    R["head"].rotation_euler.x = -0.25 * roar + shake
    R["head"].rotation_euler.z = 0.15 * math.sin(t * 0.05) * (1 - roar)
    R["jaw"].rotation_euler.x = 0.7 * roar + 0.05 * math.sin(t * 0.2) + 0.6 * env(t, PUNCH, PUNCH + 2, PUNCH + 10, PUNCH + 20)
    R["body"].location.z = 0.03 * math.sin(gait * 2) * spd
    for o in [root] + [R[n] for n in R if n.startswith(("hip", "knee", "tail", "neck", "head", "jaw", "body"))]:
        o.keyframe_insert("rotation_euler", frame=t)
    root.keyframe_insert("location", frame=t); root.keyframe_insert("scale", frame=t); R["body"].keyframe_insert("location", frame=t)
    eye_s.default_value = 6 + 10 * roar
    eye_s.keyframe_insert("default_value", frame=t)
    bpy.context.view_layer.update()
    HEAD682[t] = R["head"].matrix_world.translation.copy()

# ---------------------------------------------------------------- Goku
H = K.Hero(os.path.join(MODELS, "goku", "scene.gltf"), 1.75, "Goku")
for o in H.objs:
    if o.type == "MESH" and o.name.startswith("Icosphere"): o.hide_render = True
GUARD = L.hold(A["Punch_Cross"], 0)
POWER = L.hold(A["Hit_Chest"], 5)
GB0 = [(L.clip(A["NinjaJump_Idle_Loop"], 0, loop=True), lambda t: 1),
       (L.clip(A["NinjaJump_Land"], LAND - 4), lambda t: env(t, LAND - 5, LAND - 3)),
       (GUARD, lambda t: env(t, LAND + 16, LAND + 26, SSJ0 - 6, SSJ0)),
       (L.clip(A["Punch_Cross"], PUNCH - 9, speed=1.0), lambda t: env(t, PUNCH - 10, PUNCH - 8, PUNCH + 10, PUNCH + 18)),
       (POWER, lambda t: env(t, SSJ0 - 4, SSJ0 + 4, KCHARGE - 4, KCHARGE + 2)),
       (L.clip(A["Spell_Simple_Idle_Loop"], KCHARGE, loop=True), lambda t: env(t, KCHARGE - 2, KCHARGE + 4, FIRE - 2, FIRE)),
       (L.hold(A["Spell_Simple_Shoot"], 9), lambda t: env(t, FIRE - 2, FIRE + 1, POWERDOWN - 10, POWERDOWN)),
       (L.clip(A["Idle_Loop"], 0, loop=True), lambda t: env(t, POWERDOWN - 10, POWERDOWN + 6))]
tremble = lambda t: (lambda p: {**p, "spine_03": (p["spine_03"][0], p["spine_03"][1] @ Quaternion((1, 0, 0), 0.04 * math.sin(t * 3.1)), p["spine_03"][2])})(L.pose_at(GB0, t))
GB = GB0 + [(tremble, lambda t: env(t, SSJ0, SSJ0 + 4, SSJ + 10, SSJ + 20))]
def goku_path(t):
    if t < LAND: return 0, 0.2, 7.0 * (1 - ((t - DROP) / (LAND - DROP)) ** 2) if t >= DROP else 40, 0
    return 0, 0.2 - 0.45 * env(t, PUNCH - 8, PUNCH, PUNCH + 6, PUNCH + 30), 0, 0
H.drive(GB, goku_path, END, track=("LeftHand", "RightHand", "Hips", "Head"))
HANDS = {t: (H.track["LeftHand"][t] + H.track["RightHand"][t]) / 2 + Vector((0, -0.12, 0)) for t in range(END + 1)}
HIPS = H.track["Hips"]

# Super Saiyan hair: blend the hair's texture to glowing gold
hair = next(o for o in H.objs if o.name == "Object_10")
hm = hair.data.materials[0].copy(); hair.data.materials[0] = hm
bs = hm.node_tree.nodes["Principled BSDF"]
src = bs.inputs["Base Color"].links[0].from_socket if bs.inputs["Base Color"].links else None
mx = hm.node_tree.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = (*GOLD, 1)
if src: hm.node_tree.links.new(src, mx.inputs[6])
hm.node_tree.links.new(mx.outputs[2], bs.inputs["Base Color"])
bs.inputs["Emission Color"].default_value = (*GOLD, 1)
def ssj(t): return env(t, SSJ - 2, SSJ + 1, POWERDOWN, POWERDOWN + 8)
for t in range(END + 1):
    mx.inputs[0].default_value = ssj(t); bs.inputs["Emission Strength"].default_value = 0.6 * ssj(t)
    mx.inputs[0].keyframe_insert("default_value", frame=t); bs.inputs["Emission Strength"].keyframe_insert("default_value", frame=t)

# ---------------------------------------------------------------- the aura: flickering gold flame around him + sparks
am, ant, aout = V.nodes_mat("Aura")
tc = ant.nodes.new("ShaderNodeTexCoord"); gr = ant.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
ant.links.new(tc.outputs["Object"], gr.inputs["Vector"])
mp = ant.nodes.new("ShaderNodeMapping"); ant.links.new(tc.outputs["Object"], mp.inputs["Vector"]); mp.inputs["Scale"].default_value = (2.5, 2.5, 0.9)
nz = ant.nodes.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"; nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 4
ant.links.new(mp.outputs[0], nz.inputs["Vector"])
pw = ant.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 1.6; ant.links.new(gr.outputs["Fac"], pw.inputs[0])
ml = ant.nodes.new("ShaderNodeMath"); ml.operation = "MULTIPLY"; ant.links.new(pw.outputs[0], ml.inputs[0]); ant.links.new(nz.outputs["Fac"], ml.inputs[1])
th = ant.nodes.new("ShaderNodeMath"); th.operation = "SUBTRACT"; th.inputs[1].default_value = 0.12; th.use_clamp = True; ant.links.new(ml.outputs[0], th.inputs[0])
gk = ant.nodes.new("ShaderNodeMath"); gk.operation = "MULTIPLY"; ant.links.new(th.outputs[0], gk.inputs[0])
vol = ant.nodes.new("ShaderNodeVolumePrincipled"); vol.inputs["Density"].default_value = 0.0; vol.inputs["Emission Color"].default_value = (*GOLD, 1)
ant.links.new(gk.outputs[0], vol.inputs["Emission Strength"]); ant.links.new(vol.outputs[0], aout.inputs["Volume"])
aura = V.mesh_obj("Aura", V.sphere(1.0, 32), am); aura.scale = (0.75, 0.75, 1.35)
sp_m, sp_s = V.emit_mat("AuraSparks", (1.0, 0.85, 0.4))
sparks = [V.mesh_obj(f"AuraSparks{k}", V.ring_of_sparks(18, 0.55 + 0.1 * k, 0.009, 11 + k), sp_m, smooth=False) for k in range(3)]
al = bpy.data.lights.new("AuraLight", "POINT"); al.color = GOLD; al.shadow_soft_size = 0.6
aura_light = bpy.data.objects.new("AuraLight", al); S.collection.objects.link(aura_light)
for t in range(END + 1):
    on = ssj(t) + 0.35 * env(t, SSJ0 + 6, SSJ - 2, SSJ, SSJ + 2) * (1 - ssj(t))
    burst = 3.0 * math.exp(-max(0, t - SSJ) / 4) * (t >= SSJ)
    c = HIPS[t] + Vector((0, 0, 0.12))
    aura.location = c; aura.hide_render = on < 1e-3
    gk.inputs[1].default_value = (4 + 2.5 * math.sin(t * 1.3)) * on + 10 * burst
    nz.inputs["W"].default_value = t * 0.12; mp.inputs["Location"].default_value = (0, 0, -t * 0.045)
    for k, s in enumerate(sparks):
        s.location = c + Vector((0, 0, -0.7 + ((t * 0.06 + k * 0.45) % 1.4))); s.rotation_euler = (0.2 * k, 0.1, t * (0.3 + 0.1 * k))
        s.hide_render = on < 0.3
        s.keyframe_insert("location", frame=t); s.keyframe_insert("rotation_euler", frame=t); s.keyframe_insert("hide_render", frame=t)
    sp_s.default_value = 4 * on
    aura_light.location = c + Vector((0, -0.5, 0.4)); al.energy = (150 + 60 * math.sin(t * 1.7)) * on + 1200 * burst
    for s_, d in ((gk.inputs[1], "default_value"), (nz.inputs["W"], "default_value"), (mp.inputs["Location"], "default_value"), (sp_s, "default_value")):
        s_.keyframe_insert(d, frame=t)
    aura.keyframe_insert("location", frame=t); aura.keyframe_insert("hide_render", frame=t)
    aura_light.keyframe_insert("location", frame=t); al.keyframe_insert("energy", frame=t)

# ---------------------------------------------------------------- Kamehameha: the ball between his hands, then the beam
ball = V.Orb("Kame", BEAM_C, light_w=250, core_strength=7)
cm, core_s = V.emit_mat("BeamCore", (0.85, 0.95, 1.0))
gm, glow_s = V.emit_mat("BeamGlow", BEAM_C, transparent_edges=True)
beam_core = V.mesh_obj("BeamCore", lambda bm: bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=1, radius2=1, depth=2), cm)
beam_glow = V.mesh_obj("BeamGlow", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=32, radius1=1, radius2=1, depth=2), gm)
for b in (beam_core, beam_glow): b.rotation_euler.x = math.pi / 2
bfl = bpy.data.lights.new("BeamFlash", "POINT"); bfl.color = BEAM_C; bfl.shadow_soft_size = 1.0
bflash = bpy.data.objects.new("BeamFlash", bfl); S.collection.objects.link(bflash)
blights = []
for k in range(4):
    ld = bpy.data.lights.new(f"BeamL{k}", "POINT"); ld.color = BEAM_C; ld.shadow_soft_size = 0.5
    o = bpy.data.objects.new(f"BeamL{k}", ld); S.collection.objects.link(o); blights.append(o)
P_FIRE = HANDS[FIRE].copy()
TIP_FAR = -24.0
for t in range(END + 1):
    k = t - FIRE
    rad = 0.0
    if KCHARGE + 4 <= t < FIRE + 2:
        rad = 0.05 + 0.12 * sm((t - KCHARGE - 4) / (FIRE - KCHARGE - 4)) + 0.01 * math.sin(t * 2.1)
    ball.key(t, HANDS[t] if t < FIRE else P_FIRE, rad, 1.2 + 0.8 * sm((t - KCHARGE) / 40))
    if k >= 0:
        reach = P_FIRE.y + (TIP_FAR - P_FIRE.y) * sm(k / 6)
        width = (0.1 + 0.32 * sm(k / 4)) * (1 - 0.55 * sm((t - HIT - 8) / 10)) * (1 - sm((t - 418) / 22)) * (1 + 0.06 * math.sin(t * 3.3)) + 1e-4
        length = max(0.01, P_FIRE.y - reach)
        mid = Vector((P_FIRE.x, P_FIRE.y - length / 2, P_FIRE.z))
        beam_core.location = mid; beam_core.scale = (width * 0.45, width * 0.45, length / 2)
        beam_glow.location = mid; beam_glow.scale = (width, width, length / 2)
        core_s.default_value = 5 * (1 - sm((t - 418) / 22)); glow_s.default_value = 1.6 * (1 - sm((t - 418) / 22))
        for j, o in enumerate(blights):
            o.location = P_FIRE + Vector((0, -(j + 0.5) * length / 4, 0)); o.data.energy = 110 * (1 - sm((t - 418) / 22))
    else:
        for b in (beam_core, beam_glow): b.scale = (1e-4,) * 3; b.location = (0, 0, -2)
        core_s.default_value = glow_s.default_value = 0
        for o in blights: o.data.energy = 0
    bflash.location = P_FIRE + Vector((0, -0.5, 0.2)); bfl.energy = 3500 * math.exp(-k / 3) if k >= 0 else 0
    for b in (beam_core, beam_glow): b.keyframe_insert("location", frame=t); b.keyframe_insert("scale", frame=t)
    core_s.keyframe_insert("default_value", frame=t); glow_s.keyframe_insert("default_value", frame=t); bfl.keyframe_insert("energy", frame=t)
    for o in blights: o.keyframe_insert("location", frame=t); o.data.keyframe_insert("energy", frame=t)

# 682 burns away from the face backwards (burn order is measured at frame 0, so use the head's frame-0 spot)
vaporise.HEAT_RGB = BEAM_C
VAP = vaporise.Vaporise(M682, HEAD682[0], start=HIT, burn=BURN, push=Vector((0, -1, 0)))
for t in range(END + 1): VAP.key(t)
VAP.embers(n=4000)

# the piece that survives: a twitching, healing lump on the scorched floor
lump_m = K.pbr("Lump", (0.08, 0.02, 0.015), 0.35)
lump = V.mesh_obj("Lump", lambda bm: bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.06), lump_m)
for v in lump.data.vertices: v.co *= 1 + 0.35 * __import__('mathutils').noise.noise(v.co * 40)
LUMP = Vector((0.15, -7.05, 0.035))
ll = bpy.data.lights.new("LumpGlow", "POINT"); ll.color = (0.35, 1.0, 0.25); ll.shadow_soft_size = 0.05
lglow = bpy.data.objects.new("LumpGlow", ll); S.collection.objects.link(lglow); lglow.location = LUMP + Vector((0, 0, 0.08))
for t in range(END + 1):
    on = t > HIT + BURN + 30
    pulse = max(0, math.sin((t - 500) * 0.45)) ** 6 * (t > 520)
    lump.location = LUMP + Vector((0, 0, 0.012 * pulse)); s = 1 + 0.25 * pulse + 0.4 * sm((t - 540) / 60)
    lump.scale = (1.3 * s, 1.0 * s, 0.6 * s); lump.hide_render = not on
    ll.energy = 6 * pulse + 2 * sm((t - 530) / 40)
    lump.keyframe_insert("location", frame=t); lump.keyframe_insert("scale", frame=t); lump.keyframe_insert("hide_render", frame=t)
    ll.keyframe_insert("energy", frame=t)

# scorch line on the floor where the beam passed
scm, scorch_s = V.emit_mat("Scorch", BEAM_C, transparent_edges=True)
scorch = V.mesh_obj("Scorch", lambda bm: bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5), scm, smooth=False)
scorch.location = (P_FIRE.x, (P_FIRE.y - 0.6 + TIP_FAR) / 2, 0.004); scorch.scale = (1.0, abs(TIP_FAR - P_FIRE.y), 1)
for t in range(END + 1):
    scorch_s.default_value = (1.2 * sm((t - FIRE) / 6)) * (1 - 0.85 * sm((t - 420) / 60)) if t >= FIRE else 0
    scorch_s.keyframe_insert("default_value", frame=t)

# ---------------------------------------------------------------- dust: Goku's landing, the slam
dust_objs = []
def dust(name, loc, t0, size=1.4, dens=2.0):
    m, nt, out = V.nodes_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord"); gr = nt.nodes.new("ShaderNodeTexGradient"); gr.gradient_type = "SPHERICAL"
    nt.links.new(tc.outputs["Object"], gr.inputs["Vector"])
    dn = nt.nodes.new("ShaderNodeTexNoise"); dn.inputs["Scale"].default_value = 4
    a = nt.nodes.new("ShaderNodeMath"); a.operation = "MULTIPLY"; nt.links.new(gr.outputs["Fac"], a.inputs[0]); nt.links.new(dn.outputs["Fac"], a.inputs[1])
    b = nt.nodes.new("ShaderNodeMath"); b.operation = "MULTIPLY"; nt.links.new(a.outputs[0], b.inputs[0])
    pv = nt.nodes.new("ShaderNodeVolumePrincipled"); pv.inputs["Color"].default_value = (0.45, 0.43, 0.4, 1)
    nt.links.new(b.outputs[0], pv.inputs["Density"]); nt.links.new(pv.outputs[0], out.inputs["Volume"])
    o = V.mesh_obj(name, V.sphere(1.0, 24), m); o.location = loc
    for t in range(END + 1):
        k = t - t0
        o.scale = (0.3 + size * sm(k / 25), 0.3 + size * sm(k / 25), 0.2 + 0.35 * size * sm(k / 25)) if k > 0 else (1e-3,) * 3
        b.inputs[1].default_value = dens * (1 - sm(k / 55)) * (k > 0)
        o.keyframe_insert("scale", frame=t); b.inputs[1].keyframe_insert("default_value", frame=t)
dust("DustLand", (0, 0.2, 0.1), LAND, 1.6)
dust("DustSlam", (0, -12.6, 0.2), SLAM, 2.4, 2.5)
dust("DustBurn", (0, -7.0, 0.3), HIT + 6, 1.6, 0.35)

# regeneration: green steam and light around 682 while it heals
rl = bpy.data.lights.new("Regen", "POINT"); rl.color = (0.4, 1.0, 0.3); rl.shadow_soft_size = 1.0
regen = bpy.data.objects.new("Regen", rl); S.collection.objects.link(regen); regen.location = (0, -12.6, 1.5)
for t in range(END + 1):
    rl.energy = 600 * env(t, REGEN, REGEN + 8, RISE + 20, RISE + 36) * (0.7 + 0.3 * math.sin(t * 1.4)); rl.keyframe_insert("energy", frame=t)

# ---------------------------------------------------------------- set + camera
strip_s, bg = K.hall(key=0.9)
for nm, loc, aim, e in (("Spot682", (3.5, -5.0, 4.5), (0, -9, 0.8), 2500), ("Spot682b", (-3.0, -10.5, 4.0), (0, -9, 0.8), 1800)):
    ld = bpy.data.lights.new(nm, "SPOT"); ld.energy = e; ld.spot_size = math.radians(60); ld.spot_blend = 0.5; ld.color = (0.9, 0.95, 1.0)
    o = bpy.data.objects.new(nm, ld); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
SHOTS = [
    (0,        (1.2, -3.6, 0.6), (1.0, -3.9, 0.7), (0, -6.6, 1.5), (0, -6.6, 1.7), 22),           # 682 roars
    (44,       (5.0, -2.6, 2.0), (5.0, -2.4, 2.1), (0, -5.0, 1.2), (0, -3.0, 1.6), 14),           # the hall; Goku drops in
    (DROP + 6, (0.8, 2.1, 0.5), (0.85, 2.0, 0.5), (0, 0.2, 1.7), (0, 0.2, 0.9), 20),            # he lands
    (LAND + 14, (0.6, 1.7, 1.75), (0.55, 1.5, 1.7), (0, -7, 1.2), (0, -7, 1.2), 24),            # over his shoulder at 682
    (CHARGE,   (4.2, -1.8, 1.4), (4.4, -2.2, 1.4), (0, -2.0, 1.0), (0, -2.0, 1.0), 15),           # the charge
    (PUNCH - 1, (1.35, -0.75, 1.35), (1.4, -0.85, 1.35), (0, -0.6, 1.15), (0, -0.7, 1.15), 22),  # the punch lands
    (PUNCH + 8, (5.5, -5.5, 1.6), (5.6, -6.5, 1.5), (0, -6, 1.0), (0, -12, 0.8), 14),           # 682 flies
    (SLAM + 10, (2.4, -10.2, 0.8), (2.2, -10.5, 0.9), (0, -12.8, 0.8), (0, -12.8, 1.2), 20),     # it heals
    (ROAR2 - 2, (1.4, -8.4, 0.55), (1.3, -8.6, 0.6), (0, -10.8, 2.0), (0, -10.6, 2.2), 20),      # bigger
    (SSJ0,     (0.8, -2.2, 0.7), (0.7, -2.0, 0.8), (0, 0, 1.25), (0, 0, 1.3), 22),               # Goku powers up
    (KCHARGE,  (1.6, -0.6, 1.3), (1.5, -0.7, 1.3), (0, -0.2, 1.15), (0, -0.2, 1.15), 24),         # Ka-me-ha-me...
    (CHARGE2 + 4, (0.9, -3.4, 0.7), (0.9, -3.3, 0.75), (0, -10, 1.6), (0, -8, 1.6), 22),          # 682 charges
    (FIRE,     (5.2, -3.0, 1.4), (5.3, -3.6, 1.45), (0, -3.5, 1.1), (0, -4.5, 1.1), 13),          # HA!
    (FIRE + 6, (0.7, 1.7, 1.6), (0.65, 1.5, 1.6), (0, -8, 1.1), (0, -8, 1.1), 20),             # down the beam
    (FIRE + 14, (3.4, -4.6, 2.9), (3.2, -4.9, 2.8), (0, -8.2, 0.8), (0, -8.2, 0.8), 22),         # it burns
    (POWERDOWN - 16, (0.5, -2.0, 1.5), (0.45, -1.8, 1.5), (0, 0, 1.4), (0, 0, 1.4), 26),        # done
    (510,      (0.75, -6.0, 0.45), (0.7, -6.2, 0.42), tuple(LUMP), tuple(LUMP), 30),               # ...or is it
]
K.camera(SHOTS, END, shakes=((LAND, 0.05, 5), (PUNCH, 0.08, 5), (SLAM, 0.06, 6), (SSJ, 0.05, 8), (FIRE, 0.06, 8), (HIT, 0.08, 7)))
K.render(MODE, OUT, "g682", END, args[4:])
