"""Nexus header + main image for AllyHeal from an in-game screenshot (HUD and player names cropped out)."""
import sys, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

SRC, OUT = sys.argv[1], sys.argv[2]
F = 'C:/Windows/Fonts/'
GOLD = (236, 196, 120)
random.seed(7)


def font(name, size):
    return ImageFont.truetype(F + name, size)


def grade(im):
    im = ImageEnhance.Contrast(im).enhance(1.08)
    return ImageEnhance.Color(im).enhance(1.05)


def side_fade(size, start, end, strength=235):
    """Dark gradient on the left side for text."""
    w, h = size
    g = Image.new('L', (w, 1))
    for x in range(w):
        t = 1.0 if x <= start else max(0.0, 1 - (x - start) / (end - start))
        g.putpixel((x, 0), int(strength * t ** 1.3))
    return g.resize((w, h))


def vignette(size, amount=150):
    w, h = size
    v = Image.new('L', (w, h), 255)
    d = ImageDraw.Draw(v)
    for i in range(60):                       # i = 0 is the outer edge: darkest
        a = int(amount * (1 - i / 60) ** 2)
        d.rectangle([i * w // 120, i * h // 120, w - i * w // 120, h - i * h // 120], outline=255 - a)
    return v.filter(ImageFilter.GaussianBlur(min(w, h) // 8))


def embers(im, n, area, avoid=None):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = area
    for _ in range(n):
        x, y = random.uniform(x0, x1), random.uniform(y0, y1)
        if avoid and avoid[0] <= x <= avoid[2] and avoid[1] <= y <= avoid[3]:
            continue
        r = random.uniform(1.0, 3.2)
        a = random.randint(90, 220)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, random.randint(170, 215), 110, a))
    glow = layer.filter(ImageFilter.GaussianBlur(3))
    im.alpha_composite(glow)
    im.alpha_composite(layer)


def glow_text(im, xy, text, fnt, fill, glow=(255, 190, 90), radius=14, spacing=0, anchor='la'):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(xy, text, font=fnt, fill=glow + (200,), anchor=anchor, spacing=spacing)
    im.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius)))
    d2 = ImageDraw.Draw(im)
    d2.text((xy[0] + 3, xy[1] + 4), text, font=fnt, fill=(0, 0, 0, 160), anchor=anchor, spacing=spacing)
    d2.text(xy, text, font=fnt, fill=fill, anchor=anchor, spacing=spacing)


def compose(crop_box, size, layout):
    src = Image.open(SRC).convert('RGB')
    im = grade(src.crop(crop_box).resize(size, Image.LANCZOS)).convert('RGBA')
    w, h = size
    black = Image.new('RGBA', size, (8, 6, 4, 255))
    im = Image.composite(black, im, side_fade(size, *layout['fade']))
    im = Image.composite(im, black, vignette(size))
    s = layout['scale']
    x, y = layout['text_xy']
    embers(im, layout['embers'], (0, 0, w * 0.55, h),
           avoid=(x - 10, y + int(150 * s), x + int(840 * s), y + int(310 * s)))
    glow_text(im, (x, y), 'AllyHeal', font('constanb.ttf', int(150 * s)), (250, 232, 196))
    ty = y + int(178 * s)
    d = ImageDraw.Draw(im)
    d.line([(x + 4, ty), (x + int(520 * s), ty)], fill=GOLD + (230,), width=max(2, int(3 * s)))
    d.ellipse([x + int(520 * s) - 5, ty - 5, x + int(520 * s) + 5, ty + 5], fill=GOLD + (255,))
    glow_text(im, (x + 4, ty + int(26 * s)), 'Group heals & support spells for co-op',
              font('pala.ttf', int(46 * s)), (238, 226, 205), radius=8)
    glow_text(im, (x + 4, ty + int(92 * s)), 'DARK SOULS REMASTERED  ·  MOD ENGINE 2  ·  SEAMLESS CO-OP',
              font('palab.ttf', int(24 * s)), GOLD, radius=6)
    return im.convert('RGB')


# source 1920x1080: clean area right of the player-name box (x >= 790) and below the HUD bars (y >= 190)
header = compose((790, 330, 1920, 612), (1920, 480), dict(fade=(380, 1150), embers=70, scale=1.0, text_xy=(110, 70)))
header.save(f'{OUT}/allyheal_header_1920x480.png', optimize=True)
main = compose((790, 190, 1920, 826), (1280, 720), dict(fade=(250, 820), embers=55, scale=0.82, text_xy=(70, 380)))
main.save(f'{OUT}/allyheal_main_1280x720.png', optimize=True)
print('ok')
