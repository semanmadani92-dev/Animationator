"""Tiny 16-bit sprite engine: fill named regions, then shade (light from the top left) and outline."""
from PIL import Image

OUTLINE = "#1b1222"


def rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


class Sprite:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [[None] * w for _ in range(h)]

    def _set(self, x, y, region):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = region

    def ellipse(self, cx, cy, rx, ry, region):
        for y in range(self.h):
            for x in range(self.w):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    self.g[y][x] = region

    def rect(self, x0, y0, x1, y1, region):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self._set(x, y, region)

    def line(self, x0, y0, x1, y1, region, width=1):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            x = round(x0 + (x1 - x0) * i / steps)
            y = round(y0 + (y1 - y0) * i / steps)
            for k in range(width):
                self._set(x + k, y, region)

    def poly(self, pts, region):
        """Fill a polygon (even-odd rule, sampled at pixel centres)."""
        for y in range(self.h):
            for x in range(self.w):
                px, py, inside = x + 0.5, y + 0.5, False
                for i in range(len(pts)):
                    (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
                    if (y1 > py) != (y2 > py) and px < (x2 - x1) * (py - y1) / (y2 - y1) + x1:
                        inside = not inside
                if inside:
                    self.g[y][x] = region

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else None

    def render(self, palette, flat=()):
        """palette: region -> (base, shade, highlight). Regions in `flat` are not shaded."""
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        px = img.load()
        for y in range(self.h):
            for x in range(self.w):
                r = self.g[y][x]
                if r is None:
                    continue
                base, shade, hi = palette[r]
                if r in flat:
                    c = base
                elif self.get(x + 1, y) != r or self.get(x + 2, y) != r or self.get(x, y + 1) != r:
                    c = shade
                elif self.get(x - 1, y) != r or self.get(x, y - 1) != r:
                    c = hi
                else:
                    c = base
                px[x, y] = rgba(c)
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] is None and any(
                    self.get(x + dx, y + dy) is not None for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                ):
                    px[x, y] = rgba(OUTLINE)
        return img


def dots(img, points, color):
    px = img.load()
    for x, y in points:
        if 0 <= x < img.width and 0 <= y < img.height:
            px[x, y] = rgba(color)
    return img
