"""Three amber herb variants from the DS2 Amber Herb icon."""
import colorsys, sys
from PIL import Image, ImageEnhance, ImageFilter

src = Image.open(sys.argv[1]).convert('RGBA')
out = sys.argv[2]
W, H = src.width * 3, src.height * 3          # work at 3x so the glow is smooth
base = src.resize((W, H), Image.LANCZOS)


def shift(im, hue_deg, sat_mul, val_mul):
    px = im.load()
    res = im.copy(); rp = res.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            h = (h + hue_deg / 360) % 1
            s = min(1, s * sat_mul); v = min(1, v * val_mul)
            r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
            rp[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255), a)
    return res


def glow(im, color, radius, strength):
    pad = radius * 3
    canvas = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    halo = Image.new('RGBA', canvas.size, color + (0,))
    mask = Image.new('L', canvas.size, 0)
    mask.paste(im.split()[3], (pad, pad))
    mask = mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: min(255, int(v * strength)))
    halo.putalpha(mask)
    canvas.alpha_composite(halo)
    canvas.alpha_composite(im, (pad, pad))
    return canvas


plain = base
lush = glow(ImageEnhance.Brightness(shift(base, -6, 1.35, 1.12)).enhance(1.05), (255, 220, 120), 10, 0.55)
ancient = glow(shift(base, -16, 1.25, 0.92), (255, 150, 40), 14, 0.9)
for name, im in (('amber', plain), ('lush', lush), ('ancient', ancient)):
    im.save(f'{out}/{name}.png')
sheet = Image.new('RGBA', (3 * 260, 300), (40, 34, 28, 255))
for k, name in enumerate(('amber', 'lush', 'ancient')):
    im = Image.open(f'{out}/{name}.png'); im.thumbnail((240, 280))
    sheet.alpha_composite(im, (k * 260 + (260 - im.width) // 2, (300 - im.height) // 2))
sheet.save(f'{out}/preview.png')
print('ok')
