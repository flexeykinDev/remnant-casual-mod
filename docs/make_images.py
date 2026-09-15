# Remnant: From the Ashes - Casual Mod | flexeykinDEV
"""Draw the PNG artwork: README download button, plus banner and feature sheet for Nexus.

    python docs/make_images.py

The SVGs in this folder are the versions GitHub renders; these PNGs mirror them for sites that do
not accept SVG.
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
SCALE = 2  # everything is laid out in SVG units and drawn at 2x

INK = (22, 16, 12)
EMBER = ((240, 160, 75), (216, 85, 47))
CARD = (27, 29, 36)
CARD_EDGE = (44, 47, 55)
BG = (21, 23, 28)
WHITE = (244, 245, 247)
GREY = (154, 160, 171)
DIM = (113, 117, 127)
WARN = (216, 130, 95)
ACCENT = (240, 160, 75)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), int(size * SCALE))


BOLD, SEMI, BOOK = "segoeuib.ttf", "seguisb.ttf", "segoeui.ttf"


def px(*values):
    return tuple(v * SCALE for v in values) if len(values) > 1 else values[0] * SCALE


def gradient(size, colors, diagonal=False):
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    width, height = size
    steps = width + height if diagonal else width
    for i in range(steps):
        t = i / (steps - 1)
        stops = len(colors) - 1
        segment = min(int(t * stops), stops - 1)
        local = t * stops - segment
        color = tuple(round(a + (b - a) * local)
                      for a, b in zip(colors[segment], colors[segment + 1]))
        if diagonal:
            draw.line([(i, 0), (0, i)], fill=color)
        else:
            draw.line([(i, 0), (i, height)], fill=color)
    return image


def rounded(image, radius):
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, image.size[0] - 1, image.size[1] - 1],
                                           radius * SCALE, fill=255)
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.paste(image, (0, 0), mask)
    return out


def ember_text(draw, xy, text, size, spacing=0, weight=BOLD, fill=ACCENT):
    if not spacing:
        draw.text(px(*xy), text, font=font(weight, size), fill=fill, anchor="ls")
        return
    x, y = px(*xy)
    f = font(weight, size)
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill, anchor="ls")
        x += draw.textlength(ch, font=f) + spacing * SCALE


def draw_button():
    size = px(440, 120)
    button = rounded(gradient(size, EMBER), 14)
    draw = ImageDraw.Draw(button)
    draw.rounded_rectangle([2, 2, size[0] - 3, size[1] - 3], 12 * SCALE,
                           outline=(255, 222, 190, 90), width=3)
    x, y = px(46, 60)
    draw.line([(x, y - 22 * SCALE), (x, y + 9 * SCALE)], fill=INK, width=6 * SCALE)
    draw.polygon([(x - 15 * SCALE, y + 3 * SCALE), (x + 15 * SCALE, y + 3 * SCALE),
                  (x, y + 23 * SCALE)], fill=INK)
    draw.line([(x - 20 * SCALE, y + 31 * SCALE), (x + 20 * SCALE, y + 31 * SCALE)],
              fill=INK, width=6 * SCALE)
    draw.text(px(85, 58), "DOWNLOAD MOD", font=font(BOLD, 28), fill=INK, anchor="ls")
    draw.text(px(87, 88), "CasualMod_P.pak  ·  latest release", font=font(BOOK, 16),
              fill=(60, 40, 28), anchor="ls")
    button.save(os.path.join(HERE, "download-button.png"))
    return button.size


def draw_banner():
    size = px(1200, 300)
    image = rounded(gradient(size, [(21, 23, 28), (27, 29, 36), (36, 26, 22)], diagonal=True), 18)
    lines = Image.new("RGBA", size, (0, 0, 0, 0))  # PIL replaces pixels, so blend separately
    line_draw = ImageDraw.Draw(lines)
    for y in (80, 150, 220):
        line_draw.line([(0, px(y)), (size[0], px(y))], fill=(255, 255, 255, 14), width=SCALE)
    image = Image.alpha_composite(image, lines)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, px(8), size[1]], px(4), fill=EMBER[0])

    ember_text(draw, (70, 96), "REMNANT: FROM THE ASHES", 22, spacing=7, weight=BOOK, fill=(141, 144, 153))
    draw.text(px(70, 180), "CASUAL MOD", font=font(BOLD, 82), fill=WHITE, anchor="ls")
    draw.text(px(70, 226), "Loot x100 · easy fights · everything buffed", font=font(SEMI, 26),
              fill=ACCENT, anchor="ls")
    draw.text(px(70, 266), "by flexeykinDEV", font=font(BOOK, 19), fill=(111, 114, 123), anchor="ls")

    cx, cy = px(980, 150)
    draw.ellipse([cx - px(86), cy - px(86), cx + px(86), cy + px(86)], outline=CARD_EDGE, width=2 * SCALE)
    draw.arc([cx - px(66), cy - px(66), cx + px(66), cy + px(66)], -35, 225, fill=EMBER[1], width=3 * SCALE)
    draw.ellipse([cx - px(30), cy - px(30), cx + px(30), cy + px(30)], fill=(31, 34, 41), outline=(58, 62, 72))
    draw.text((cx, cy + px(10)), "x100", font=font(BOLD, 26), fill=ACCENT, anchor="ms")
    image.save(os.path.join(HERE, "banner.png"))
    return image.size


CARDS = [
    (40, 130, 368, 160, "Loot", "x100",
     ["scrap, iron, ammo, lumenite, simulacrum", "normal enemies always drop"]),
    (416, 130, 368, 160, "Fights", "-50% / -60%",
     ["enemy health and damage", "player: 250 HP, x2 stamina"]),
    (792, 130, 368, 160, "Weapon mods (F)", "4x faster",
     ["damage, shields, summons x2", "cooldowns halved"]),
    (40, 310, 368, 160, "Traits", "x3, cap 60",
     ["every trait, level-1 value and growth", "Elder Knowledge and Scavenger x10"]),
    (416, 310, 368, 160, "Rings and amulets", "x2",
     ["every positive bonus, 130 items", "downsides left untouched"]),
    (792, 310, 368, 160, "Buffs and potions", "x10 time",
     ["food lasts 10 hours, effects x2", "Dragon Heart: full heal, 10 charges"]),
    (40, 490, 368, 150, "Weapons", "x2", ["damage, clip size and reserve ammo"]),
    (416, 490, 368, 150, "Trading and crafting", "-90%", ["prices and upgrade costs, full refunds"]),
    (792, 490, 368, 150, "Travel", "0 weight", ["no armor encumbrance, endless sprint"]),
]


def draw_features():
    size = px(1200, 866)
    image = Image.new("RGBA", size, BG + (255,))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([px(40), px(42), px(46), px(84)], px(3), fill=EMBER[0])
    draw.text(px(62, 64), "What the mod changes", font=font(BOLD, 30), fill=WHITE, anchor="ls")
    draw.text(px(62, 92), "322 game assets rebuilt from your own installation", font=font(BOOK, 18),
              fill=DIM, anchor="ls")

    for x, y, w, h, title, value, lines in CARDS:
        draw.rounded_rectangle([px(x), px(y), px(x + w), px(y + h)], px(14), fill=CARD, outline=CARD_EDGE)
        draw.text(px(x + 28, y + 42), title, font=font(SEMI, 21), fill=WHITE, anchor="ls")
        draw.text(px(x + 28, y + 92), value, font=font(BOLD, 40), fill=ACCENT, anchor="ls")
        for i, line in enumerate(lines):
            draw.text(px(x + 28, y + 124 + i * 22), line, font=font(BOOK, 17), fill=GREY, anchor="ls")

    highlight = rounded(gradient(px(1120, 150), [(36, 26, 22), (27, 29, 36)]), 14)
    image.paste(highlight, px(40, 660), highlight)
    draw.rounded_rectangle([px(40), px(660), px(1160), px(810)], px(14), outline=(74, 51, 40))
    draw.rounded_rectangle([px(40), px(660), px(45), px(810)], px(2), fill=EMBER[0])
    draw.text(px(72, 700), "Boss weapon mods, now on any weapon", font=font(SEMI, 21), fill=WHITE, anchor="ls")
    for i, line in enumerate([
            "12 new crafting recipes at McCabe — pay the same boss material the weapon costs",
            "(Undying, Gravity Core, Hive Shot, Vampiric, Flamethrower, Skewer and more),",
            "and the Ward 13 merchant keeps one of each in stock."]):
        draw.text(px(72, 732 + i * 24), line, font=font(BOOK, 17), fill=GREY, anchor="ls")
    draw.text(px(800, 706), "12 mods", font=font(BOLD, 40), fill=ACCENT, anchor="ls")
    draw.text(px(800, 740), "installed for good: taking the", font=font(BOOK, 17), fill=WARN, anchor="ls")
    draw.text(px(800, 762), "weapon off destroys the mod", font=font(BOOK, 17), fill=WARN, anchor="ls")
    draw.text(px(40, 850), "flexeykinDEV", font=font(BOOK, 18), fill=DIM, anchor="ls")

    image.convert("RGB").save(os.path.join(HERE, "features.png"))
    return image.size


for name, size in [("download-button.png", draw_button()), ("banner.png", draw_banner()),
                   ("features.png", draw_features())]:
    print(f"{name} {size[0]}x{size[1]}")
