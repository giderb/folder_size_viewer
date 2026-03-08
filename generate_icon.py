#!/usr/bin/env python
"""Generate src/icon.ico and src/icon.png for Folder Size Viewer."""
from pathlib import Path
from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]
OUT_DIR = Path(__file__).parent / "src"


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = max(2, size // 16)    # corner radius
    gap = max(1, size // 85)  # gap between blocks

    # Background rounded rect
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(6, 6, 18, 255))

    # Block layout (proportional)
    mid_x = int(size * 0.60)
    mid_y = int(size * 0.55)

    # Large block — cyan (#00d4ff)
    d.rectangle([gap, gap, mid_x - gap, mid_y - gap], fill=(0, 212, 255, 255))

    # Top-right block — violet (#6d28d9)
    d.rectangle([mid_x + gap, gap, size - gap - 1, mid_y - gap], fill=(109, 40, 217, 255))

    # Bottom-left block — dim cyan (#004d5e)
    d.rectangle([gap, mid_y + gap, mid_x - gap, size - gap - 1], fill=(0, 77, 94, 255))

    # Bottom-right block — dim violet (#3b1470)
    d.rectangle([mid_x + gap, mid_y + gap, size - gap - 1, size - gap - 1], fill=(59, 20, 112, 255))

    return img


frames = [draw_icon(s) for s in SIZES]
frames[-1].save(
    OUT_DIR / "icon.ico",
    format="ICO",
    sizes=[(s, s) for s in SIZES],
    append_images=frames[:-1],
)
frames[-1].save(OUT_DIR / "icon.png")
print(f"Icons written to {OUT_DIR}")
