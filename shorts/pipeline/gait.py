"""Mark's gait: one continuous cycle that blends from a calm walk (s=0) into the low ninja dash (s=1).

The leg phase advances with ground speed, so the planted foot never slides at any speed, and the body
leans further forward, drops lower and swings the arms back as he speeds up.
"""
import math

VWALK, VMAX = 22.0, 140.0  # px/s


def smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def lerp(a, b, k):
    return a + (b - a) * k


def _leg_params(s):
    return lerp(18, 48, s), lerp(0, 10, s), lerp(4, 35, s), lerp(28, 70, s)


def _leg(p, s):
    amp, off, base, extra = _leg_params(s)
    th = amp * math.sin(p) + off
    return th, th - (base + extra * max(0.0, math.cos(p)))


def stride(s):
    """How far the planted foot travels backward over half a cycle (px)."""
    xs = []
    for k in range(48):
        th, sh = _leg(2 * math.pi * k / 48, s)
        xs.append(6 * math.sin(math.radians(th)) + 6 * math.sin(math.radians(sh)))
    return max(xs) - min(xs)


def speed_blend(v):
    return max(0.0, min(1.0, (v - VWALK) / (VMAX - VWALK)))


def pose(phase, s):
    arm = smooth(s * 1.6)  # arms sweep back early in the speed-up
    a = 15 * math.sin(phase) * (1 - arm)
    walk_na, walk_fa = (-a, -a + 40), (a, a + 40)
    run_na, run_fa = (-105, -112), (-98, -106)
    bob = -1 if abs(math.sin(phase)) > 0.7 else 0
    return dict(nl=_leg(phase, s), fl=_leg(phase + math.pi, s),
                na=(lerp(walk_na[0], run_na[0], arm), lerp(walk_na[1], run_na[1], arm)),
                fa=(lerp(walk_fa[0], run_fa[0], arm), lerp(walk_fa[1], run_fa[1], arm)),
                tilt=48 * smooth(s), up=lerp(0, 2, s) + bob, legs=(6, 6), leg_r=1.8,
                sword=lerp(-72 + 6 * math.sin(phase), -100, arm))  # trailing back, clear of the ground


SKID = dict(nl=(55, 50), fl=(-15, -70), na=(70, 95), fa=(-40, -10), tilt=-12, up=2, legs=(6, 6), leg_r=1.8, sword=-110)


class Trip:
    """Simulates one walk -> dash -> skid trip and answers 'where is he and how is he moving' at time t.

    walk_at: starts walking; dash_at: starts speeding up (accel seconds to full speed);
    stops exactly at x_stop after a skid of `skid` seconds.
    """

    def __init__(self, x0, x_stop, walk_at, dash_at, accel=0.9, skid=0.45, dt=1 / 480):
        self.samples = []
        t, x, v, ph = walk_at, x0, VWALK, 0.0
        state = "walk"
        t_skid, v_skid = None, None
        while True:
            if state != "skid":
                v = VWALK + (VMAX - VWALK) * smooth((t - dash_at) / accel) if t >= dash_at else VWALK
                if x >= x_stop - v * skid / 2:  # decelerating linearly covers v * skid / 2
                    state, t_skid, v_skid = "skid", t, v
                elif t >= dash_at:
                    state = "dash"
            if state == "skid":
                k = (t - t_skid) / skid
                if k >= 1:
                    break
                v = v_skid * (1 - k)
            ph += math.pi * v / stride(speed_blend(v)) * dt if state != "skid" else 0
            x += v * dt
            t += dt
            self.samples.append((t, x, v, ph, state))
        self.walk_at, self.t_skid, self.t_stop, self.x_stop = walk_at, t_skid, t, x_stop
        self.x0, self.dt = x0, dt

    def at(self, t):
        """(x, v, phase, state) where state is 'idle', 'walk', 'dash', 'skid' or 'stop'."""
        if t < self.walk_at:
            return self.x0, 0.0, 0.0, "idle"
        i = int((t - self.walk_at) / self.dt)
        if i >= len(self.samples):
            return self.x_stop, 0.0, self.samples[-1][3], "stop"
        _, x, v, ph, st = self.samples[i]
        return x, v, ph, st
