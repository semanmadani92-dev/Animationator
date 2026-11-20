"""Smooth pixel-art camera: sub-pixel pans and any zoom level without uneven pixels.

Each frame is composed at an integer upscale F (so every art pixel is an F x F block), with every layer
and sprite placed at its exact sub-pixel position. The result is then resized to 1080x1920 by a factor
just under 1, which keeps pixels crisp and evenly sized while the camera glides and zooms.
"""
import math

from PIL import Image, ImageDraw

from level import PARALLAX

OUT_W, OUT_H = 1080, 1920
ASPECT = OUT_H / OUT_W


class Canvas:
    def __init__(self, layers, cam_x, cam_y, vw):
        self.cam_x, self.cam_y, self.vw = cam_x, cam_y, vw
        self.vh = vw * ASPECT
        self.F = F = math.ceil(OUT_W / vw - 1e-9)
        self.size = (math.ceil(vw * F), math.ceil(self.vh * F))
        self.lw, self.lh = math.ceil(vw) + 2, math.ceil(self.vh) + 2
        self.x0, self.y0 = math.floor(cam_x), math.floor(cam_y)
        y0, fy = self.y0, cam_y - self.y0
        sky = layers["sky"].crop((0, y0, self.lw, y0 + self.lh)).convert("RGBA")
        self.img = Image.new("RGBA", self.size)
        self._paste_layer(sky, 0, fy)
        for name in ("mountains", "hills"):
            ox = cam_x * PARALLAX[name]
            ix = math.floor(ox)
            self._paste_layer(layers[name].crop((ix, y0, ix + self.lw, y0 + self.lh)), ox - ix, fy)
        self._paste_layer(layers["ground"].crop((self.x0, y0, self.x0 + self.lw, y0 + self.lh)), cam_x - self.x0, fy)

    def _paste_layer(self, small, fx, fy):
        F = self.F
        big = small.resize((small.width * F, small.height * F), Image.NEAREST)
        self.img.alpha_composite(big, (-round(fx * F), -round(fy * F)))

    def overlay(self):
        """A transparent world-locked layer at art resolution; draw on it with world coords minus .origin."""
        return Image.new("RGBA", (self.lw, self.lh), (0, 0, 0, 0))

    @property
    def origin(self):
        return self.x0, self.y0

    def add_overlay(self, ov):
        self._paste_layer(ov, self.cam_x - self.x0, self.cam_y - self.y0)

    def sprite(self, spr, wx, wy):
        """Paste an art-resolution sprite with its top-left at world (wx, wy), sub-pixel accurate."""
        F = self.F
        big = spr.resize((spr.width * F, spr.height * F), Image.NEAREST)
        self.img.alpha_composite(big, (round((wx - self.cam_x) * F), round((wy - self.cam_y) * F)))

    def put(self, spr, cx, feet):
        """Sprite with its bottom-centre (feet) at world (cx, feet)."""
        self.sprite(spr, cx - spr.width / 2, feet - spr.height + 1)

    def final(self):
        F = self.F
        return self.img.convert("RGB").resize((OUT_W, OUT_H), Image.BILINEAR,
                                              box=(0, 0, self.vw * F, self.vh * F))

    def draw(self, ov):
        return ImageDraw.Draw(ov)


class Spring:
    """Critically damped follow: glides to a moving target with no overshoot."""

    def __init__(self, value, omega):
        self.x, self.v, self.w = value, 0.0, omega

    def step(self, target, dt, substeps=8):
        h = dt / substeps
        for _ in range(substeps):
            a = self.w * self.w * (target - self.x) - 2 * self.w * self.v
            self.v += a * h
            self.x += self.v * h
        return self.x
