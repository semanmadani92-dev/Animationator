"""A rope bridge simulated as a Verlet chain of planks.

Intact, both ends are pinned and the deck sags naturally. Cut the near (left) end
and the chain swings down under gravity until it hangs against the far canyon
wall like a ladder, the way a real rope bridge falls.
"""
import math

from PIL import ImageDraw


class RopeBridge:
    def __init__(self, left, right, wall_x, ground_y, n=60, slack=1.01, gravity=300.0):
        self.n = n
        self.left, self.right = left, right
        self.wall_x, self.ground_y = wall_x, ground_y
        span = math.dist(left, right)
        self.rest = span * slack / (n - 1)
        self.g = gravity
        self.p = [(left[0] + (right[0] - left[0]) * i / (n - 1), left[1] + (right[1] - left[1]) * i / (n - 1))
                  for i in range(n)]
        self.prev = list(self.p)
        self.left_pinned = True
        for _ in range(4000):  # settle into the natural sag
            self.step(1 / 240, damping=0.95)

    def cut(self):
        self.left_pinned = False

    def step(self, dt, damping=0.995, iterations=24):
        new = []
        for (x, y), (px, py) in zip(self.p, self.prev):
            vx, vy = (x - px) * damping, (y - py) * damping
            new.append((x + vx, y + vy + self.g * dt * dt))
        self.prev, self.p = self.p, new
        for _ in range(iterations):
            for i in range(self.n - 1):
                (x1, y1), (x2, y2) = self.p[i], self.p[i + 1]
                dx, dy = x2 - x1, y2 - y1
                dist = math.hypot(dx, dy) or 1e-9
                diff = (dist - self.rest) / dist / 2
                self.p[i] = (x1 + dx * diff, y1 + dy * diff)
                self.p[i + 1] = (x2 - dx * diff, y2 - dy * diff)
            if self.left_pinned:
                self.p[0] = self.left
            self.p[-1] = self.right
            # the far canyon wall: hanging planks can't pass into the rock
            self.p = [(min(x, self.wall_x - 1) if y > self.ground_y + 1 else x, y) for x, y in self.p]

    def deck_y(self, x):
        """Deck height under world x (intact bridge)."""
        for (x1, y1), (x2, y2) in zip(self.p, self.p[1:]):
            if x1 <= x <= x2:
                return y1 + (y2 - y1) * (x - x1) / ((x2 - x1) or 1e-9)
        return None

    def draw(self, img, cam_x, cam_y, cut=False):
        d = ImageDraw.Draw(img)
        ox, oy = -cam_x, -cam_y
        rope, plank, plank_dark = "#8a6a3a", "#a8743e", "#6b4426"
        # posts at both ends
        for x, y in (self.left, self.right):
            d.rectangle([x - 1 + ox, y - 14 + oy, x + 1 + ox, y + 1 + oy], fill="#6b4426", outline="#3a2414")
        rail = []
        for i, (x, y) in enumerate(self.p):
            a = self.p[max(0, i - 1)]
            b = self.p[min(self.n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1
            nx, ny = dy / ln, -dx / ln  # normal pointing "up" from the deck
            rail.append((x + nx * 9, y + ny * 9))
        # handrail rope, uprights, then the deck planks on top
        d.line([(x + ox, y + oy) for x, y in rail], fill=rope)
        for i in range(0, self.n, 3):
            d.line([(self.p[i][0] + ox, self.p[i][1] + oy), (rail[i][0] + ox, rail[i][1] + oy)], fill=rope)
        if not cut:
            d.line([(self.left[0] + ox, self.left[1] - 12 + oy), (rail[0][0] + ox, rail[0][1] + oy)], fill=rope)
        d.line([(self.right[0] + ox, self.right[1] - 12 + oy), (rail[-1][0] + ox, rail[-1][1] + oy)], fill=rope)
        for i in range(self.n - 1):
            (x1, y1), (x2, y2) = self.p[i], self.p[i + 1]
            d.line([(x1 + ox, y1 + oy), (x2 + ox, y2 + oy)], fill=plank if i % 2 else plank_dark, width=2)
        if cut:  # frayed rope ends left on the near post
            lx, ly = self.left
            d.line([(lx + ox, ly - 12 + oy), (lx + 2 + ox, ly - 7 + oy)], fill=rope)
            d.line([(lx + ox, ly + oy), (lx + 3 + ox, ly + 4 + oy)], fill=rope)
