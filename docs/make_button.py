# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Draw the download button used in the README.

    python docs/make_button.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

SIZE = (880, 240)          # drawn at 2x and shown at half width in the README
RADIUS = 28
EMBER = ((240, 160, 75), (216, 85, 47))
INK = (22, 16, 12)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download-button.png")


def font(name, size):
    return ImageFont.truetype(os.path.join(os.environ["WINDIR"], "Fonts", name), size)


gradient = Image.new("RGB", SIZE)
draw = ImageDraw.Draw(gradient)
for x in range(SIZE[0]):
    t = x / (SIZE[0] - 1)
    draw.line([(x, 0), (x, SIZE[1])], fill=tuple(round(a + (b - a) * t) for a, b in zip(*EMBER)))

mask = Image.new("L", SIZE, 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE[0] - 1, SIZE[1] - 1], RADIUS, fill=255)

button = Image.new("RGBA", SIZE, (0, 0, 0, 0))
button.paste(gradient, (0, 0), mask)

draw = ImageDraw.Draw(button)
draw.rounded_rectangle([3, 3, SIZE[0] - 4, SIZE[1] - 4], RADIUS - 3, outline=(255, 222, 190, 90), width=3)

# download arrow
x, y = 92, 120
draw.line([(x, y - 44), (x, y + 18)], fill=INK, width=12)
draw.polygon([(x - 30, y + 6), (x + 30, y + 6), (x, y + 46)], fill=INK)
draw.line([(x - 40, y + 62), (x + 40, y + 62)], fill=INK, width=12)

draw.text((170, 66), "DOWNLOAD MOD", font=font("segoeuib.ttf", 56), fill=INK)
draw.text((174, 140), "CasualMod_P.pak  ·  latest release", font=font("segoeui.ttf", 32),
          fill=(60, 40, 28))

button.save(OUT)
print(f"{OUT} {button.size[0]}x{button.size[1]}")
