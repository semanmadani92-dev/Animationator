"""Naruto vs SCP-096 (vertical Short, ~20 s). Naruto jogs up to the hunched figure at the end of the hall.
It turns: he sees its face. It screams, then sprints at him. His shadow clones are torn apart one by one.
Naruto jumps over it and drives a Rasengan into it, slamming it into the floor. He grins at the camera...
and behind him, SCP-096 gets back up.

  ~/blendervenv/bin/python naruto_vs_096.py -- preview|final OUT ANIME_MODELS [frames | a-b]
  ANIME_MODELS holds naruto/scene.gltf (python3 get_models.py ~/anime_models).
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix, Quaternion
args = sys.argv[sys.argv.index("--") + 1:]
MODE, OUT, MODELS = args[0], args[1], args[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vslib as K
L, V, S, sm, env = K.L, K.V, K.S, K.sm, K.env

# ---------------------------------------------------------------- timing (30 fps)
JOG1 = 80                      # Naruto arrives
TURN0, TURN1 = 86, 112         # 096 turns round: he sees its face
SCREAM0, SCREAM1 = 120, 186    # it covers its face and screams
SIGN, POOF = 166, 178          # shadow clone jutsu
SPRINT = 186                   # 096 sprints
CLASH = (204, 208, 212, 216)   # each clone is torn apart
RASEN0 = 192                   # the Rasengan forms in his hand
JUMP, APEX, HIT = 218, 238, 264    # he jumps over it, then dives onto it
LANDN = 282                    # Naruto lands
GETUP = 486                    # 096 gets back up behind him
RISEN = 540
END = 586
P096 = Vector((0, -10.0, 0))   # where 096 waits
STOP096 = 1.0                  # where its charge ends (y), right under Naruto's dive
NARUTO_Y = -1.8
BLUE = (0.35, 0.65, 1.0)
S.render.fps = 30; S.frame_start, S.frame_end = 0, END
A = K.clips()

# ---------------------------------------------------------------- SCP-096: tall, pale, long-armed
skin = K.pbr("096Skin", (0.78, 0.74, 0.7), 0.55)
b = skin.node_tree.nodes["Principled BSDF"]; b.inputs["Subsurface Weight"].default_value = 0.25
b.inputs["Subsurface Radius"].default_value = (0.9, 0.5, 0.4)
scp = K.mannequin("SCP096", skin)
blk = K.pbr("096Black", (0.005, 0.004, 0.004), 0.3)
hc = K.bone_mid(scp, "Head"); F = Vector((0, -1, 0))
for sx in (-1, 1):
    e = V.mesh_obj(f"096Eye{sx}", V.sphere(0.022, 14), blk); e.location = hc + F * 0.092 + Vector((sx * 0.04, 0, 0.035)); e.scale = (1, 0.4, 0.8)
    K.attach(e, scp, "Head")
mouth = V.mesh_obj("096Mouth", V.sphere(0.03, 18), blk); mouth.location = hc + F * 0.09 + Vector((0, 0, -0.05))
mouth.scale = (0.8, 0.35, 0.35); K.attach(mouth, scp, "Head")

SCB0 = [(L.clip(A["Zombie_Idle_Loop"], 0, loop=True), lambda t: 1)]
tremble = lambda t: (lambda p: {**p, "spine_03": (p["spine_03"][0], p["spine_03"][1] @ Quaternion((0, 1, 0), 0.06 * math.sin(t * 3.7)), p["spine_03"][2]),
                                "Head": (p["Head"][0], p["Head"][1] @ Quaternion((1, 0, 0), 0.08 * math.sin(t * 4.3)), p["Head"][2])})(L.clip(A["Zombie_Scratch"], 0, loop=True, speed=0.6)(t))
look_up = lambda t: (lambda p: {**p, "neck_01": (p["neck_01"][0], p["neck_01"][1] @ Quaternion((1, 0, 0), -0.5), p["neck_01"][2])})(L.pose_at(SCB0, t))
SCB = SCB0 + [
    (tremble, lambda t: env(t, SCREAM0 - 6, SCREAM0, SCREAM1 - 4, SCREAM1)),
    (L.clip(A["Sprint_Loop"], SPRINT, loop=True, speed=1.25), lambda t: env(t, SPRINT - 3, SPRINT + 1, CLASH[0] - 3, CLASH[0])),
    (L.clip(A["Melee_Hook"], CLASH[0] - 2, loop=True, speed=1.6), lambda t: env(t, CLASH[0] - 3, CLASH[0], CLASH[-1] + 2, CLASH[-1] + 5)),
    (L.clip(A["Sprint_Loop"], CLASH[-1], loop=True, speed=1.25), lambda t: env(t, CLASH[-1] + 2, CLASH[-1] + 5, JUMP + 10, JUMP + 16)),
    (look_up, lambda t: env(t, JUMP + 14, JUMP + 22, HIT - 1, HIT)),
    (L.clip(A["Hit_Knockback"], HIT, speed=1.6), lambda t: env(t, HIT - 1, HIT + 1, GETUP - 1, GETUP)),
    (L.clip(A["LayToIdle"], GETUP, speed=0.75), lambda t: env(t, GETUP - 1, GETUP, RISEN, RISEN + 6)),
    (L.clip(A["Zombie_Idle_Loop"], 0, loop=True), lambda t: env(t, RISEN, RISEN + 6))]
L.bake(scp, SCB, 0, END)
for bn in ("upperarm_l", "upperarm_r", "lowerarm_l", "lowerarm_r"): scp.pose.bones[bn].scale = (1, 1.28, 1)
scp.scale = (0.88, 0.88, 1.2)


def scp_path(t):
    if t < TURN0: return P096.x, P096.y, 0, 0                            # back to Naruto
    if t < SPRINT: return P096.x, P096.y, 0, math.pi * sm((t - TURN0) / (TURN1 - TURN0))
    y0, y1 = P096.y, -5.6
    if t < CLASH[0]: return 0, y0 + (y1 - y0) * ((t - SPRINT) / (CLASH[0] - SPRINT)) ** 1.15, 0, math.pi
    if t < CLASH[-1] + 2: return 0, y1 + 0.6 * (t - CLASH[0]) / (CLASH[-1] + 2 - CLASH[0]), 0, math.pi
    u = min(1, (t - CLASH[-1] - 2) / (JUMP + 12 - CLASH[-1] - 2))
    y = y1 + 0.6 + (STOP096 - y1 - 0.6) * (1 - (1 - u) ** 1.6)
    return 0, y, 0, (math.pi + 0.5 * math.sin(max(0, t - JUMP - 12) * 0.08)) if t < HIT else 0.0
K.bake_path(scp, scp_path, END)
for t in range(END + 1):                     # the mouth: shut, then torn open in the scream, open in the charge
    o = max(env(t, SCREAM0, SCREAM0 + 6, SCREAM1 - 6, SCREAM1), 0.6 * env(t, SPRINT, SPRINT + 4, HIT, HIT + 4), env(t, END - 30, END - 22))
    mouth.scale = (0.8 + 0.3 * o, 0.35, 0.35 + 2.6 * o); mouth.keyframe_insert("scale", frame=t)

# ---------------------------------------------------------------- Naruto (the real one)
H = K.Hero(os.path.join(MODELS, "naruto", "scene.gltf"), 1.55, "Naruto")
NB = [(L.clip(A["Jog_Fwd_Loop"], 0, loop=True), lambda t: 1),
      (L.clip(A["Idle_Loop"], 0, loop=True), lambda t: env(t, JOG1 - 6, JOG1 + 4)),
      (L.hold(A["Spell_Simple_Enter"], 12), lambda t: env(t, SIGN - 4, SIGN, POOF + 2, POOF + 8)),
      (L.clip(A["Pistol_Idle_Loop"], 0, loop=True), lambda t: env(t, RASEN0 - 4, RASEN0 + 4, JUMP - 6, JUMP - 2)),
      (L.clip(A["NinjaJump_Start"], JUMP - 6), lambda t: env(t, JUMP - 7, JUMP - 5, JUMP + 8, JUMP + 12)),
      (L.clip(A["NinjaJump_Idle_Loop"], JUMP + 8, loop=True), lambda t: env(t, JUMP + 8, JUMP + 12, HIT - 10, HIT - 6)),
      (L.hold(A["Punch_Cross"], 8), lambda t: env(t, HIT - 10, HIT - 5, HIT + 4, HIT + 8)),
      (L.clip(A["NinjaJump_Land"], LANDN - 4), lambda t: env(t, LANDN - 5, LANDN - 3, LANDN + 14, LANDN + 22)),
      (L.clip(A["Idle_Loop"], 0, loop=True), lambda t: env(t, LANDN + 14, LANDN + 22))]
def nar_path(t):
    if t < JOG1: return 0, 4.0 + (NARUTO_Y - 4.0) * min(1, t / JOG1), 0, 0
    if t < JUMP: return 0, NARUTO_Y, 0, 0
    if t < APEX: u = (t - JUMP) / (APEX - JUMP); return 0, NARUTO_Y + 1.0 * u, 3.4 * (1 - (1 - u) ** 2), math.pi * sm(u)
    if t < HIT: u = (t - APEX) / (HIT - APEX); return 0, NARUTO_Y + 1.0 + (STOP096 - 0.35 - NARUTO_Y - 1.0) * u, 3.4 - 1.5 * u ** 1.5, math.pi
    if t < LANDN:                                     # bounces off it, flips back and lands in front
        u = (t - HIT) / (LANDN - HIT); return 0, STOP096 - 0.35 + (-1.1 - STOP096 + 0.35) * u, 1.9 * (1 - u) + 1.2 * math.sin(math.pi * u), math.pi * (1 - sm(u))
    return 0, -1.1, 0, 0
H.drive(NB, nar_path, END, track=("RightHand", "Hips"))
RH = H.track["RightHand"]

# ---------------------------------------------------------------- the shadow clones: a second Naruto running in, copied four times
C = K.Hero(os.path.join(MODELS, "naruto", "scene.gltf"), 1.55, "Clone")
CB = [(L.hold(A["Spell_Simple_Enter"], 12), lambda t: 1),
      (L.clip(A["Sprint_Loop"], POOF + 6, loop=True), lambda t: env(t, POOF + 4, POOF + 8))]
C.drive(CB, lambda t: (0, NARUTO_Y - 0.9 - 0.2 * max(0, t - POOF - 6), 0, 0), END)
lanes = [(-1.3, 0.0), (1.3, 0.2), (-0.55, -0.3), (0.55, 0.35)]       # x offset, y offset per clone (order they die)
CLONES = []
for k, (dx, dy) in enumerate(lanes):
    objs = K.clone_objects(C.objs, (dx, dy, 0), f"c{k}") if k else C.objs
    if k == 0:
        root = next(o for o in objs if o.parent not in objs); root.location += Vector((dx, dy, 0))
    CLONES.append(objs)
    for o in objs:
        if o.type != "MESH": continue
        for t in (0, POOF + 1, POOF + 2, CLASH[k], CLASH[k] + 1):
            o.hide_render = not (POOF + 2 <= t <= CLASH[k]); o.keyframe_insert("hide_render", frame=t)
for k, (dx, dy) in enumerate(lanes):
    K.puff(f"Poof{k}", (dx, NARUTO_Y - 0.9 + dy, 0.8), POOF, END, size=0.9, dens=3.0, rgb=(0.9, 0.9, 0.92), grow=6, fade=26, height=1.2)
    cy = scp_path(CLASH[k])[1]
    K.puff(f"Kill{k}", (dx * 0.5, cy + 0.6, 0.9), CLASH[k], END, size=0.8, dens=3.0, rgb=(0.9, 0.9, 0.92), grow=5, fade=22, height=1.2)

# ---------------------------------------------------------------- Rasengan: a spinning ball in his right hand
ras = V.Orb("Rasengan", BLUE, light_w=350, core_strength=8)
rm, rs = V.emit_mat("RasenRings", (0.75, 0.9, 1.0))
rings = [V.mesh_obj(f"RasenRing{k}", V.ring_of_sparks(30, 1.25 + 0.15 * k, 0.03, 40 + k), rm, smooth=False) for k in range(4)]
blast_m, blast_s = V.emit_mat("RasenBlast", (0.5, 0.8, 1.0), transparent_edges=True)
blast = V.mesh_obj("RasenBlast", V.sphere(1.0, 48), blast_m)
fl = bpy.data.lights.new("RasenFlash", "POINT"); fl.color = BLUE; fl.shadow_soft_size = 0.8
flash = bpy.data.objects.new("RasenFlash", fl); S.collection.objects.link(flash)
P_HIT = None
for t in range(END + 1):
    k = t - HIT
    if t < RASEN0: pos, rad = RH[t], 0.0
    elif t < HIT: pos, rad = RH[t] + Vector((0, 0, 0.12)) if t < JUMP else RH[t] + Vector((0, 0.05, -0.12)), 0.03 + 0.09 * sm((t - RASEN0) / 24)
    else:
        if P_HIT is None: P_HIT = RH[HIT].copy()
        pos, rad = P_HIT, (0.12 + 0.5 * sm(k / 4)) * (1 - sm((k - 6) / 6))
    ras.key(t, pos, max(rad, 0), 1.2 + 2 * (k >= 0))
    for j, r in enumerate(rings):
        r.parent = ras.e
        r.rotation_euler = (0.7 * j + t * 0.3, 0.4 * j, t * (1.4 + 0.3 * j) * (1 if j % 2 else -1))
        r.keyframe_insert("rotation_euler", frame=t)
    rs.default_value = 9 * (rad > 0.02); rs.keyframe_insert("default_value", frame=t)
    if P_HIT is not None:
        blast.location = P_HIT; blast.scale = ((0.2 + 2.2 * sm(k / 10)),) * 3; blast_s.default_value = 1.3 * (1 - sm(k / 10))
        flash.location = P_HIT + Vector((0, -0.6, 0.3)); fl.energy = 2500 * math.exp(-k / 3)
    else:
        blast.scale = (1e-4,) * 3; blast_s.default_value = 0; fl.energy = 0
    blast.keyframe_insert("location", frame=t); blast.keyframe_insert("scale", frame=t)
    blast_s.keyframe_insert("default_value", frame=t); flash.keyframe_insert("location", frame=t); fl.keyframe_insert("energy", frame=t)
K.puff("Crater", (0, STOP096 + 0.3, 0.2), HIT + 2, END, size=2.3, dens=1.6, grow=20, fade=70)
# a ring of cracked floor around the impact
crm, crs = V.emit_mat("Cracks", BLUE, transparent_edges=True)
crack = V.mesh_obj("Crack", lambda bm: bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=1.0, radius2=1.25, depth=0.01), crm)
crack.location = (0, STOP096 + 0.3, 0.01)
for t in range(END + 1):
    k = t - HIT
    crack.scale = ((0.3 + 1.6 * sm(k / 8)) if k >= 0 else 1e-4,) * 2 + (1,); crs.default_value = 4 * (1 - sm(k / 25)) if k >= 0 else 0
    crack.keyframe_insert("scale", frame=t); crs.keyframe_insert("default_value", frame=t)

# ---------------------------------------------------------------- set + camera
HEAD096 = {}
for t in (TURN1 - 4, TURN1 + 4, SCREAM0):
    S.frame_set(t); bpy.context.view_layer.update(); HEAD096[t] = scp.matrix_world @ scp.pose.bones["Head"].head
def face_cam(i, t, u, loc, look):
    if i != 2: return loc, look
    h = HEAD096[TURN1 - 4].lerp(HEAD096[TURN1 + 4], u) + Vector((0, 0, 0.06))
    return h + Vector((0.06, 0.95 - 0.12 * u, 0.02)), h
strip_s, bg = K.hall(key=0.9)
K.key_lights(lambda t: 0.0 if t >= END - 4 else 1.0, END, strip_s, 1.0)
SHOTS = [
    (0,          (0.7, 6.2, 1.6), (0.6, 2.6, 1.55), (0, -10, 1.2), (0, -10, 1.2), 24),            # behind Naruto: the figure at the end of the hall
    (TURN0 - 2,  (0.5, -7.2, 1.85), (0.45, -7.6, 1.85), (0, -10, 1.95), (0, -10, 2.0), 30),        # it turns...
    (TURN1 - 4,  (0.0, -8.75, 2.15), (0.0, -8.9, 2.15), (0, -10, 2.12), (0, -10, 2.12), 38),         # ...its face
    (SCREAM0,    (1.0, -8.0, 1.05), (0.95, -8.2, 1.05), (0, -10, 1.35), (0, -10, 1.45), 22),          # the scream
    (SIGN - 4,   (0.9, -3.6, 1.2), (0.85, -3.5, 1.2), (0, NARUTO_Y, 1.25), (0, NARUTO_Y, 1.25), 24),  # Naruto: shadow clone jutsu
    (POOF,       (1.2, -6.2, 1.3), (1.15, -6.0, 1.3), (0, -2.6, 1.0), (0, -2.6, 1.0), 20),           # poof: four of him
    (SPRINT,     (4.4, -4.0, 1.4), (4.6, -4.6, 1.4), (0, -5.5, 1.0), (0, -4.5, 1.0), 14),          # the clash
    (CLASH[-1] + 2, (0.8, -3.6, 0.6), (0.8, -3.4, 0.6), (0, 0, 1.4), (0, 1.0, 1.6), 20),            # it keeps coming; Naruto jumps
    (APEX - 4,   (2.6, -0.8, 0.5), (2.5, -0.6, 0.6), (0, 0.6, 2.4), (0, 0.6, 2.0), 18),            # he dives
    (HIT + 1,    (3.8, -1.6, 1.3), (4.0, -2.0, 1.4), (0, 0.6, 0.9), (0, 0.4, 0.9), 15),            # impact
    (LANDN + 10, (0.35, -3.6, 1.35), (0.3, -3.3, 1.35), (0, 0, 1.15), (0, 0, 1.15), 24),            # he grins... and behind him
    (RISEN + 4,  (0.6, -2.7, 1.5), (0.55, -2.5, 1.6), (0, 1.2, 1.8), (0, 1.2, 1.95), 30),            # it is standing
]
K.camera(SHOTS, END, override=face_cam, shakes=((SCREAM0 + 2, 0.03, 30), (HIT, 0.1, 7), (LANDN, 0.03, 4)))
K.render(MODE, OUT, "n096", END, args[3:])
