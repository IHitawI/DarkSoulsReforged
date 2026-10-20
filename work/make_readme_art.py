"""README art: the banner (docs/art/banner.png) and the footer (docs/art/footer.png).

The background is painted here, no outside assets: a dusk sky with a pale ring (the Darksign), a gothic city
in the haze on the horizon (Anor Londo-like), ruined arches and pillars nearer (Firelink-like), layers of fog,
light shafts, ash and a bonfire glow on the right where Elion sits. The left side is darkened for the title.
Stickers: docs/art/stickers/*.png, cut from the author's Elion sticker sheet (docs/art/elion_sheet.png).
Run from work/: python make_readme_art.py
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ART = '../docs/art'
FONT = r'C:\Windows\Fonts\palab.ttf'      # Palatino Linotype Bold: close to DS1's carved serif caps
FONT_R = r'C:\Windows\Fonts\pala.ttf'
W, H = 1600, 480


def spaced(draw, xy, text, font, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def noise(w, h, rng, octaves=((6, 0.5), (14, 0.3), (40, 0.2))):
    """Smooth value noise 0..1 (a few octaves of upscaled random grids)."""
    out = np.zeros((h, w))
    for cells, amp in octaves:
        g = rng.random((max(2, int(cells * h / w)) + 1, cells + 1))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(img) / 255
    return (out - out.min()) / (out.max() - out.min())


def lerp(a, b, t):
    return a + (b - a) * t


def layer(w, h):
    return Image.new('RGBA', (w, h), (0, 0, 0, 0))


def scene(w, h, seed, glow_x=0.82, sun=False):
    rng = np.random.default_rng(seed)
    random.seed(seed)
    horizon = 0.64 * h
    # --- sky: night at the top, a dull amber band at the horizon
    y = np.linspace(0, 1, h)[:, None]
    top, mid, low = np.array([12, 13, 24]), np.array([40, 34, 52]), np.array([132, 84, 58])
    t1 = np.clip(y / (horizon / h), 0, 1)
    sky = np.where(t1 < 0.6, lerp(top, mid, t1 / 0.6), lerp(mid, low, (t1 - 0.6) / 0.4) ** 1.0)
    sky = np.repeat(sky[:, None, :] if sky.ndim == 2 else sky, w, axis=1) if sky.shape[1] != w else sky
    sky = np.broadcast_to(sky, (h, w, 3)).astype(float).copy()
    clouds = noise(w, h, rng, ((5, 0.6), (12, 0.3), (30, 0.1)))
    sky *= (0.82 + 0.3 * clouds[..., None])
    img = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).convert('RGBA')

    # --- stars
    st = layer(w, h)
    d = ImageDraw.Draw(st)
    for _ in range(int(w * h / 6000)):
        x, yy = random.uniform(0, w), random.uniform(0, horizon * 0.7)
        a = int(random.uniform(40, 150) * (1 - yy / horizon))
        d.point((x, yy), fill=(230, 225, 210, a))
    img.alpha_composite(st)

    # --- the ring (Darksign): a dark disc with a burning rim, soft glow
    cx, cy, r = w * 0.705, h * 0.33, h * 0.21
    ring = layer(w, h)
    d = ImageDraw.Draw(ring)
    d.ellipse((cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5), fill=(200, 120, 70, 40))
    ring = ring.filter(ImageFilter.GaussianBlur(r * 0.6))
    d = ImageDraw.Draw(ring)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 214, 150, 245) if sun else (14, 10, 14, 235))
    rim = layer(w, h)
    dr = ImageDraw.Draw(rim)
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 176, 96, 255), width=max(3, int(r * 0.07)))
    ring.alpha_composite(rim.filter(ImageFilter.GaussianBlur(r * 0.35)))
    ring.alpha_composite(rim.filter(ImageFilter.GaussianBlur(r * 0.12)))
    ring.alpha_composite(rim.filter(ImageFilter.GaussianBlur(r * 0.025)))
    img.alpha_composite(ring)

    # --- light shafts from the ring
    rays = layer(w, h)
    d = ImageDraw.Draw(rays)
    for _ in range(9):
        ang = random.uniform(math.radians(60), math.radians(130))
        spread = random.uniform(0.02, 0.06)
        L = w * 1.2
        p = [(cx, cy), (cx + L * math.cos(ang - spread), cy + L * math.sin(ang - spread)),
             (cx + L * math.cos(ang + spread), cy + L * math.sin(ang + spread))]
        d.polygon(p, fill=(255, 190, 130, random.randint(10, 22)))
    img.alpha_composite(rays.filter(ImageFilter.GaussianBlur(18)))

    # --- far city in the haze (gothic towers and spires)
    far = layer(w, h)
    d = ImageDraw.Draw(far)
    col = (52, 44, 58, 255)
    base = horizon + h * 0.03
    x = -20
    while x < w + 20:
        tw = random.uniform(10, 34)
        th = random.uniform(0.06, 0.22) * h
        if random.random() < 0.14:
            th = random.uniform(0.28, 0.42) * h                # a cathedral spire
        d.rectangle((x, base - th, x + tw, base), fill=col)
        d.polygon([(x - 2, base - th), (x + tw / 2, base - th - tw * random.uniform(1.2, 2.6)), (x + tw + 2, base - th)],
                  fill=col)
        if random.random() < 0.35:                              # a bridge / arch between towers
            gap = random.uniform(20, 60)
            d.rectangle((x + tw, base - th * 0.45, x + tw + gap, base - th * 0.38), fill=col)
            x += gap
        x += tw + random.uniform(2, 18)
    img.alpha_composite(far.filter(ImageFilter.GaussianBlur(1.2)))

    def fog(alpha, y0, y1, color, scale):
        n = noise(w, h, rng, scale)
        yy = np.linspace(0, 1, h)[:, None] * h
        band = np.clip(1 - np.abs(yy - (y0 + y1) / 2) / ((y1 - y0) / 2), 0, 1) ** 1.3
        a = np.clip(n * band * alpha, 0, 255).astype(np.uint8)
        f = Image.new('RGBA', (w, h), color + (0,))
        f.putalpha(Image.fromarray(a))
        img.alpha_composite(f)

    fog(230, horizon - h * 0.22, horizon + h * 0.14, (120, 96, 92), ((4, 0.5), (11, 0.35), (26, 0.15)))

    # --- ruins nearer: arches and broken pillars (left and middle, the right stays open for the bonfire)
    ruin = layer(w, h)
    d = ImageDraw.Draw(ruin)
    ground = h * 0.86
    rc = (26, 20, 24, 255)
    x = random.uniform(-40, 10)
    while x < w * glow_x - 140:
        pw = random.uniform(9, 16)
        span = random.uniform(40, 80)
        ph = random.uniform(0.14, 0.30) * h
        broken = random.random() < 0.6
        for px in (x, x + span):
            top = ground - ph * (random.uniform(0.45, 0.8) if broken and px != x else 1)
            d.rectangle((px, top, px + pw, ground), fill=rc)
            d.rectangle((px - 4, top - 8, px + pw + 4, top), fill=rc)             # capital
        if not broken:
            ax0, ax1 = x, x + span + pw
            ar = (ax1 - ax0) / 2
            atop = ground - ph - ar                             # the half circle springs from the pillar tops
            d.pieslice((ax0, atop, ax1, atop + 2 * ar), 180, 360, fill=rc)
            d.pieslice((ax0 + pw, atop + pw, ax1 - pw, atop + 2 * ar - pw), 180, 360, fill=(0, 0, 0, 0))
        x += span + pw + random.uniform(40, 160)
    for _ in range(int(w / 90)):                               # rubble
        rx, rr = random.uniform(0, w), random.uniform(4, 16)
        d.ellipse((rx - rr * 1.6, ground - rr, rx + rr * 1.6, ground + rr), fill=rc)
    img.alpha_composite(ruin.filter(ImageFilter.GaussianBlur(0.6)))

    fog(200, ground - h * 0.20, ground + h * 0.08, (96, 74, 72), ((5, 0.5), (16, 0.35), (40, 0.15)))

    # --- ground
    gr = np.zeros((h, w, 4), np.uint8)
    yy = np.arange(h)[:, None]
    gr[..., :3] = (14, 11, 13)
    gr[..., 3] = np.clip((yy - ground + 6) * 18, 0, 255).astype(np.uint8)
    img.alpha_composite(Image.fromarray(gr, 'RGBA'))

    # --- bonfire glow on the right
    glow = layer(w, h)
    gx, gy = w * glow_x, h * 0.98
    d = ImageDraw.Draw(glow)
    for rad, a in ((h * 1.0, 50), (h * 0.62, 70), (h * 0.34, 90)):
        d.ellipse((gx - rad * 1.3, gy - rad, gx + rad * 1.3, gy + rad), fill=(255, 120, 40, a))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(h * 0.18)))

    # --- ash and embers
    em = layer(w, h)
    d = ImageDraw.Draw(em)
    for _ in range(int(w * h / 4500)):
        x, yy = random.uniform(0, w), random.uniform(0, h)
        heat = max(0.0, 1 - math.hypot((x - gx) / w, (yy - gy) / h) * 1.6)
        r = random.choice((0.8, 1, 1.4, 2))
        if random.random() < 0.55 + 0.45 * heat:
            c = (255, int(150 + 70 * random.random()), 70, int(50 + 200 * heat * random.random()))
        else:
            c = (190, 180, 170, int(30 + 60 * random.random()))
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=c)
    img.alpha_composite(em.filter(ImageFilter.GaussianBlur(0.6)))

    # --- left darkening for the title, then a vignette
    sh = np.zeros((h, w, 4), np.uint8)
    xx = np.linspace(0, 1, w)[None, :]
    sh[..., 3] = (np.clip(1 - xx / 0.62, 0, 1) ** 1.4 * 170).astype(np.uint8)
    img.alpha_composite(Image.fromarray(sh, 'RGBA'))
    yy = np.linspace(-1, 1, h)[:, None]
    xx = np.linspace(-1, 1, w)[None, :]
    v = np.clip((xx ** 2 * 0.6 + yy ** 2 * 0.9) - 0.25, 0, 1) ** 1.2
    vg = np.zeros((h, w, 4), np.uint8)
    vg[..., 3] = (v * 200).astype(np.uint8)
    img.alpha_composite(Image.fromarray(vg, 'RGBA'))
    return img


def sticker(name, height):
    s = Image.open(f'{ART}/stickers/{name}.png').convert('RGBA')
    return s.resize((int(s.width * height / s.height), height), Image.LANCZOS)


def shadowed(img, xy, text, font, fill, spacing):
    sh = layer(*img.size)
    spaced(ImageDraw.Draw(sh), (xy[0] + 3, xy[1] + 4), text, font, (0, 0, 0, 230), spacing)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    spaced(ImageDraw.Draw(img), xy, text, font, fill, spacing)


def banner():
    img = scene(W, H, 7)
    gold, ember, ash = (222, 192, 128), (232, 118, 52), (196, 188, 176)
    shadowed(img, (110, 108), 'DARK SOULS', ImageFont.truetype(FONT, 46), ash, 22)
    shadowed(img, (100, 158), 'REFORGED', ImageFont.truetype(FONT, 128), gold, 14)
    d = ImageDraw.Draw(img)
    d.line((112, 318, 760, 318), fill=(170, 104, 58), width=2)
    d.polygon([(436, 312), (448, 318), (436, 324), (424, 318)], fill=ember)
    sub = layer(W, H)
    ds = ImageDraw.Draw(sub)
    for col, off in (((0, 0, 0, 200), 2), ((230, 222, 208, 255), 0)):
        ds.text((112 + off, 338 + off), 'Оверхол Dark Souls Remastered', font=ImageFont.truetype(FONT_R, 30), fill=col)
        ds.text((112 + off, 378 + off), 'хаб Храма Огня · чемпионы · новые фазы боссов · кооп',
                font=ImageFont.truetype(FONT_R, 24), fill=col if off else (186, 176, 164, 255))
    img.alpha_composite(sub)
    s = sticker('bonfire', 360)
    img.alpha_composite(s, (W - s.width - 60, H - s.height - 24))
    img.convert('RGB').save(f'{ART}/banner.png', optimize=True)


def footer():
    w, h = 1600, 220
    img = scene(w, h, 11, glow_x=0.88, sun=True)   # Praise the Sun: a sun, not the Darksign
    s = sticker('bye', 190)
    img.alpha_composite(s, (w - s.width - 90, h - s.height - 12))
    shadowed(img, (110, 70), 'PRAISE THE SUN', ImageFont.truetype(FONT, 40), (222, 192, 128), 12)
    sub = layer(w, h)
    ds = ImageDraw.Draw(sub)
    ds.text((114, 130), 'и не забудьте отдыхать у костра', font=ImageFont.truetype(FONT_R, 24), fill=(0, 0, 0, 200))
    ds.text((112, 128), 'и не забудьте отдыхать у костра', font=ImageFont.truetype(FONT_R, 24), fill=(186, 176, 164, 255))
    img.alpha_composite(sub)
    img.convert('RGB').save(f'{ART}/footer.png', optimize=True)


if __name__ == '__main__':
    banner()
    footer()
