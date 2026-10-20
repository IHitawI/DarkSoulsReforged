"""README art: the banner (docs/art/banner.png) and the footer (docs/art/footer.png).

Stickers: docs/art/stickers/*.png, cut from the author's Elion sticker sheet (docs/art/elion_sheet.png).
Run from work/: python make_readme_art.py
"""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ART = '../docs/art'
FONT = r'C:\Windows\Fonts\palab.ttf'      # Palatino Linotype Bold: close to DS1's carved serif caps
FONT_R = r'C:\Windows\Fonts\pala.ttf'
W, H = 1600, 480


def spaced(draw, xy, text, font, fill, spacing, anchor_center=False):
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + spacing
    return total


def background(w, h, seed):
    random.seed(seed)
    bg = Image.new('RGB', (w, h), (10, 9, 11))
    px = bg.load()
    for y in range(h):                                       # dark top, ember glow at the bottom right
        for x in range(w):
            d = math.hypot((x - w * 0.80) / w, (y - h * 1.05) / h)
            g = max(0.0, 1.0 - d * 1.55)
            px[x, y] = (int(12 + 150 * g ** 2.2), int(10 + 58 * g ** 2.6), int(12 + 18 * g ** 3))
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for _ in range(140):                                     # ash / embers rising
        x, y = random.uniform(0, w), random.uniform(0, h)
        r = random.choice((1, 1, 1.5, 2, 2.5))
        heat = max(0.0, 1 - math.hypot((x - w * 0.8) / w, (y - h) / h) * 1.3)
        c = (255, int(140 + 80 * random.random()), 60, int(60 + 180 * heat * random.random()))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    glow = glow.filter(ImageFilter.GaussianBlur(0.8))
    bg = bg.convert('RGBA')
    bg.alpha_composite(glow)
    vign = Image.new('L', (w, h), 0)                         # vignette
    dv = ImageDraw.Draw(vign)
    for i in range(60):
        sx, sy = i * w / 520, i * h / 240                    # 60 rings, never crossing (thin footer too)
        dv.rectangle((sx, sy, w - sx, h - sy), outline=int(255 * (1 - i / 60) ** 2))
    vign = vign.filter(ImageFilter.GaussianBlur(30))
    dark = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    bg = Image.composite(dark, bg, vign.point(lambda v: int(v * 0.85)))
    return bg


def sticker(name, height):
    s = Image.open(f'{ART}/stickers/{name}.png').convert('RGBA')
    return s.resize((int(s.width * height / s.height), height), Image.LANCZOS)


def banner():
    img = background(W, H, 7)
    d = ImageDraw.Draw(img)
    gold, ember, ash = (214, 184, 120), (232, 118, 52), (176, 168, 158)
    spaced(d, (110, 108), 'DARK SOULS', ImageFont.truetype(FONT, 46), ash, 22)
    big = ImageFont.truetype(FONT, 128)
    for off, col in (((3, 4), (0, 0, 0)), ((0, 0), gold)):
        spaced(d, (100 + off[0], 158 + off[1]), 'REFORGED', big, col, 14)
    d.line((112, 318, 760, 318), fill=(150, 92, 52), width=2)
    d.polygon([(436, 312), (448, 318), (436, 324), (424, 318)], fill=ember)
    sub = ImageFont.truetype(FONT_R, 30)
    d.text((112, 338), 'Оверхол Dark Souls Remastered', font=sub, fill=(222, 214, 200))
    d.text((112, 378), 'хаб Храма Огня · чемпионы · новые фазы боссов · кооп', font=ImageFont.truetype(FONT_R, 24),
           fill=(168, 158, 146))
    s = sticker('bonfire', 360)
    halo = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((1080, 150, 1560, 520), fill=(255, 120, 40, 70))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(60)))
    img.alpha_composite(s, (W - s.width - 60, H - s.height - 24))
    img.convert('RGB').save(f'{ART}/banner.png', optimize=True)


def footer():
    w, h = 1600, 220
    img = background(w, h, 11)
    d = ImageDraw.Draw(img)
    s = sticker('bye', 190)
    img.alpha_composite(s, (w - s.width - 90, h - s.height - 12))
    spaced(d, (110, 70), 'PRAISE THE SUN', ImageFont.truetype(FONT, 40), (214, 184, 120), 12)
    d.text((112, 128), 'и не забудьте отдыхать у костра', font=ImageFont.truetype(FONT_R, 24), fill=(168, 158, 146))
    img.convert('RGB').save(f'{ART}/footer.png', optimize=True)


if __name__ == '__main__':
    banner()
    footer()
