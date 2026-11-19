"""Compose a 1080x1920 pixel-art frame: backdrop + sprites (scaled 12x) + captions."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE = 12
OUT_W, OUT_H = 1080, 1920
FONT = str(Path(__file__).parent / "fonts" / "PressStart2P-Regular.ttf")


def compose(backdrop, sprites, line1="", line2="", line2_color="#ff4a4a", caption_y=1640):
    """sprites: list of (image, x, y) in backdrop pixel coordinates (feet-agnostic top-left)."""
    scene = backdrop.convert("RGBA")
    for sprite, x, y in sprites:
        scene.alpha_composite(sprite, (x, y))
    frame = scene.resize((OUT_W, OUT_H), Image.NEAREST)
    d = ImageDraw.Draw(frame)
    for text, size, color, y in ((line1, 48, "#ffffff", caption_y), (line2, 80, line2_color, caption_y + 80)):
        if not text:
            continue
        font = ImageFont.truetype(FONT, size)
        w = d.textlength(text, font=font)
        x = (OUT_W - w) / 2
        d.text((x, y + 8), text, font=font, fill="#000000", stroke_width=8, stroke_fill="#000000")
        d.text((x, y), text, font=font, fill=color, stroke_width=8, stroke_fill="#120c18")
    return frame.convert("RGB")
