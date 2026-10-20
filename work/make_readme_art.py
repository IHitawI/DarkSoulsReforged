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


def firelink(w, h, seed, fire_x=0.82):
    """Firelink Shrine by day, golden hour: a pale blue sky turning peach at the horizon, soft clouds, the sun,
    the Burg castle and its aqueduct on a hill in the haze, a living tree, the shrine's mossy ruined arches,
    sunny grass; light and warm."""
    rng = np.random.default_rng(seed)
    random.seed(seed)
    horizon = 0.60 * h
    ground = h * 0.84

    # --- sky + clouds
    y = np.linspace(0, 1, h)[:, None, None]
    top, mid, low = np.array([132, 178, 210]), np.array([196, 214, 222]), np.array([252, 226, 196])
    t = np.clip(y / (horizon / h), 0, 1)
    sky = np.where(t < 0.55, lerp(top, mid, t / 0.55), lerp(mid, low, (t - 0.55) / 0.45))
    sky = np.broadcast_to(sky, (h, w, 3)).astype(float).copy()
    cl = noise(w, h, rng, ((3, 0.45), (8, 0.35), (22, 0.2)))
    puff = np.clip((cl - 0.52) * 3.2, 0, 1) * (1 - np.clip(y[..., 0] / (horizon / h) - 0.2, 0, 1) * 0.6)
    sky = sky * (1 - puff[..., None] * 0.9) + np.array([255, 250, 242]) * puff[..., None] * 0.9
    img = Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).convert('RGBA')

    sx, sy = w * 0.62, h * 0.18
    sun = layer(w, h)
    d = ImageDraw.Draw(sun)
    for rad, a in ((h * 0.95, 55), (h * 0.5, 90), (h * 0.18, 170), (h * 0.075, 255)):
        d.ellipse((sx - rad, sy - rad, sx + rad, sy + rad), fill=(255, 244, 214, a))
    img.alpha_composite(sun.filter(ImageFilter.GaussianBlur(h * 0.06)))
    rays = layer(w, h)
    d = ImageDraw.Draw(rays)
    for _ in range(12):
        ang = random.uniform(math.radians(55), math.radians(165))
        spread = random.uniform(0.012, 0.04)
        L = w * 1.3
        d.polygon([(sx, sy), (sx + L * math.cos(ang - spread), sy + L * math.sin(ang - spread)),
                   (sx + L * math.cos(ang + spread), sy + L * math.sin(ang + spread))],
                  fill=(255, 246, 220, random.randint(16, 30)))
    img.alpha_composite(rays.filter(ImageFilter.GaussianBlur(12)))

    def paste(lay, blur):
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)) if blur else lay)

    def haze(alpha, y0, y1, scale, color=(255, 246, 232)):
        n = noise(w, h, rng, scale)
        yy = np.linspace(0, 1, h)[:, None] * h
        band = np.clip(1 - np.abs(yy - (y0 + y1) / 2) / ((y1 - y0) / 2), 0, 1) ** 1.2
        f = Image.new('RGBA', (w, h), color + (0,))
        f.putalpha(Image.fromarray(np.clip((0.4 + 0.6 * n) * band * alpha, 0, 255).astype(np.uint8)))
        img.alpha_composite(f)

    # --- far hill, the Burg castle and the aqueduct (lavender-blue in the haze)
    far = layer(w, h)
    d = ImageDraw.Draw(far)
    fc = (164, 172, 196, 255)
    hill = [(0, h)] + [(i, horizon - h * (0.04 + 0.06 * math.exp(-((i / w - 0.62) / 0.22) ** 2)
                                         + 0.01 * math.sin(i / 37))) for i in range(0, w + 20, 20)] + [(w, h)]
    d.polygon(hill, fill=fc)
    cx0, base = w * 0.46, horizon - h * 0.08
    d.rectangle((cx0, base - h * 0.05, w * 0.80, base + h * 0.02), fill=fc)                     # wall
    for i in range(int((w * 0.80 - cx0) / 12)):                                                 # battlements
        if i % 2 == 0:
            d.rectangle((cx0 + i * 12, base - h * 0.065, cx0 + i * 12 + 7, base - h * 0.05), fill=fc)
    for tx, tw, th, roof in ((0.48, 22, 0.13, 1.6), (0.55, 34, 0.20, 0), (0.60, 16, 0.30, 3.2),
                             (0.665, 26, 0.16, 1.4), (0.73, 20, 0.11, 1.8), (0.78, 28, 0.15, 0)):
        x = w * tx
        d.rectangle((x, base - h * th, x + tw, base), fill=fc)
        if roof:
            d.polygon([(x - 3, base - h * th), (x + tw / 2, base - h * th - tw * roof), (x + tw + 3, base - h * th)],
                      fill=fc)
        else:
            for k in range(0, int(tw), 8):
                d.rectangle((x + k, base - h * th - 6, x + k + 5, base - h * th), fill=fc)
    ay = horizon - h * 0.02                                                                    # aqueduct
    d.rectangle((w * 0.12, ay - h * 0.035, w * 0.46, ay - h * 0.02), fill=fc)
    span = 30
    for i in range(int((w * 0.46 - w * 0.12) / span)):
        x0 = w * 0.12 + i * span
        d.rectangle((x0, ay - h * 0.02, x0 + span, ay + h * 0.05), fill=fc)
        d.pieslice((x0 + 5, ay - h * 0.005, x0 + span - 5, ay + h * 0.04), 180, 360, fill=(0, 0, 0, 0))
        d.rectangle((x0 + 5, ay + h * 0.0175, x0 + span - 5, ay + h * 0.05), fill=(0, 0, 0, 0))
    paste(far, 1.0)
    haze(170, horizon - h * 0.30, horizon + h * 0.08, ((4, 0.5), (12, 0.35), (30, 0.15)))

    # --- near slope
    near = layer(w, h)
    d = ImageDraw.Draw(near)
    slope = [(0, h)] + [(i, ground - h * (0.05 + 0.035 * math.sin(i / w * 3.1 + 2.0)) - 2 * random.random())
                        for i in range(0, w + 30, 30)] + [(w, h)]
    d.polygon(slope, fill=(138, 160, 108, 255))
    paste(near, 1.0)

    # --- a living tree between the title and Elion
    tree = layer(w, h)
    d = ImageDraw.Draw(tree)
    tx, tb = w * 0.665, ground - h * 0.02
    bark = (110, 92, 74, 255)
    d.polygon([(tx - 12, tb), (tx - 5, tb - h * 0.36), (tx + 6, tb - h * 0.36), (tx + 14, tb)], fill=bark)
    for ang, ln in ((-0.9, 0.16), (-0.45, 0.13), (0.5, 0.15), (0.95, 0.12)):
        x1, y1 = tx + math.sin(ang) * h * ln, tb - h * 0.30 - math.cos(ang) * h * ln
        d.line((tx, tb - h * 0.28, x1, y1), fill=bark, width=6)
    leaves = [(tx + random.gauss(0, w * 0.045), tb - h * 0.47 + random.gauss(0, h * 0.075)) for _ in range(40)]
    for bx, by in leaves:                                                                       # canopy, then light
        br = random.uniform(h * 0.04, h * 0.085)
        g = random.randint(-10, 10)
        d.ellipse((bx - br * 1.25, by - br, bx + br * 1.25, by + br), fill=(96 + g, 126 + g, 78 + g, 255))
    for bx, by in leaves[::2]:
        br = random.uniform(h * 0.02, h * 0.045)
        d.ellipse((bx - br * 1.2 + 6, by - br - 8, bx + br * 1.2 + 6, by + br - 8), fill=(150, 176, 104, 255))
    paste(tree, 1.3)

    # --- the shrine's ruins: warm stone arches and pillars, broken, mossy, with ivy
    ruin = layer(w, h)
    d = ImageDraw.Draw(ruin)
    stone, lit, shade, seam = (214, 200, 176, 255), (236, 224, 200, 255), (170, 156, 136, 255), (186, 172, 150, 255)
    moss = [(120, 146, 88, 255), (104, 132, 80, 255), (140, 162, 96, 255)]

    def pillar(px, top, pw):
        d.rectangle((px, top, px + pw, ground), fill=stone)
        d.rectangle((px, top, px + pw * 0.28, ground), fill=lit)                     # sunlit side (sun is left-up)
        d.rectangle((px + pw * 0.7, top, px + pw, ground), fill=shade)
        for by in np.arange(top + 14, ground, 16):                                   # block seams
            d.line((px, by, px + pw, by), fill=seam, width=1)
        d.rectangle((px - 5, top - 8, px + pw + 5, top), fill=stone)
        d.rectangle((px - 5, top - 8, px + pw + 5, top - 5), fill=lit)
        for _ in range(random.randint(2, 4)):                                        # moss
            my = random.choice((top - 6, ground - random.uniform(4, 30), random.uniform(top, ground)))
            mw = random.uniform(pw * 0.5, pw * 1.2)
            d.ellipse((px - 3, my - 4, px - 3 + mw, my + random.uniform(4, 9)), fill=random.choice(moss))
        if random.random() < 0.6:                                                    # ivy
            ix = px + random.uniform(2, pw - 2)
            iy = top
            for _ in range(random.randint(6, 14)):
                iy += random.uniform(5, 9)
                ix += random.uniform(-2.5, 2.5)
                d.ellipse((ix - 2.5, iy - 2.5, ix + 2.5, iy + 2.5), fill=random.choice(moss))

    def arch(x0, x1, top, pw, broken_side=None):
        ar = (x1 - x0) / 2
        atop = top - ar
        d.pieslice((x0, atop, x1, atop + 2 * ar), 180, 360, fill=stone)
        d.pieslice((x0 + pw, atop + pw, x1 - pw, atop + 2 * ar - pw), 180, 360, fill=(0, 0, 0, 0))
        d.arc((x0, atop, x1, atop + 2 * ar), 200, 300, fill=lit, width=3)
        if broken_side:                                                              # a chunk missing
            cx_ = x0 + ar + (ar * 0.45 if broken_side > 0 else -ar * 0.45)
            d.polygon([(cx_ - 14, atop - 4), (cx_ + 18, atop - 4), (cx_ + 6, atop + pw + 10), (cx_ - 10, atop + pw + 6)],
                      fill=(0, 0, 0, 0))

    layout = [(0.30, 70, 0.30, None), (0.405, 64, 0.24, 1), (0.50, 0, 0.18, None), (0.555, 76, 0.34, -1)]
    for fx, span_, ph, broken in layout:
        x = w * fx
        pw = 18
        top = ground - h * ph
        if span_:
            pillar(x, top, pw)
            pillar(x + span_, top + (h * 0.05 if broken == 1 else 0), pw)
            arch(x, x + span_ + pw, top, pw, broken)
        else:
            pillar(x, top, pw)
    for _ in range(14):                                                              # rubble
        rx, rr = random.uniform(w * 0.26, w * 0.70), random.uniform(4, 11)
        d.ellipse((rx - rr * 1.5, ground - rr * 0.7, rx + rr * 1.5, ground + rr * 0.6), fill=random.choice((stone, shade)))
    paste(ruin, 0.5)

    # --- sunny grass
    gr = layer(w, h)
    d = ImageDraw.Draw(gr)
    gy = np.linspace(0, 1, h - int(ground))
    for i, t_ in enumerate(gy):
        c = lerp(np.array([150, 172, 104]), np.array([104, 128, 76]), t_)
        d.line((0, ground + i, w, ground + i), fill=tuple(int(v) for v in c) + (255,))
    for _ in range(int(w * 1.4)):
        gx_, gy_ = random.uniform(0, w), random.uniform(ground - 3, h)
        g = random.randint(-12, 22)
        d.line((gx_, gy_, gx_ + random.uniform(-3, 3), gy_ - random.uniform(4, 11)), fill=(130 + g, 156 + g, 92 + g, 255))
    for _ in range(int(w / 14)):                                                     # small flowers
        fx_, fy_ = random.uniform(0, w), random.uniform(ground + 6, h)
        d.ellipse((fx_ - 1.6, fy_ - 1.6, fx_ + 1.6, fy_ + 1.6), fill=random.choice(((255, 246, 220, 255), (250, 214, 120, 255))))
    paste(gr, 0)
    haze(80, ground - h * 0.10, ground + h * 0.04, ((6, 0.5), (18, 0.5)))

    # --- bonfire warmth and floating motes
    glow = layer(w, h)
    d = ImageDraw.Draw(glow)
    fx, fy = w * fire_x, h * 0.95
    for rad, a in ((h * 0.5, 50), (h * 0.26, 80)):
        d.ellipse((fx - rad * 1.3, fy - rad, fx + rad * 1.3, fy + rad), fill=(255, 176, 92, a))
    paste(glow, h * 0.12)
    mo = layer(w, h)
    d = ImageDraw.Draw(mo)
    for _ in range(int(w * h / 6500)):
        mx, my = random.uniform(0, w), random.uniform(0, h * 0.9)
        r = random.choice((0.8, 1.2, 1.7))
        d.ellipse((mx - r, my - r, mx + r, my + r), fill=(255, 240, 200, random.randint(80, 190)))
    paste(mo, 0.6)

    # --- a light veil on the left for the title, a soft warm vignette
    veil = np.zeros((h, w, 4), np.uint8)
    veil[..., :3] = (252, 246, 234)
    xx = np.linspace(0, 1, w)[None, :]
    veil[..., 3] = np.broadcast_to((np.clip(1 - xx / 0.56, 0, 1) ** 1.4 * 140).astype(np.uint8), (h, w))
    img.alpha_composite(Image.fromarray(veil, 'RGBA'))
    yy = np.linspace(-1, 1, h)[:, None]
    xx = np.linspace(-1, 1, w)[None, :]
    v = np.clip((xx ** 2 * 0.5 + yy ** 2 * 0.8) - 0.38, 0, 1) ** 1.3
    vg = np.zeros((h, w, 4), np.uint8)
    vg[..., :3] = (110, 88, 60)
    vg[..., 3] = (v * 110).astype(np.uint8)
    img.alpha_composite(Image.fromarray(vg, 'RGBA'))
    return img


def place_sticker(img, s, x, y):
    """Sticker on the scene: a soft contact shadow under it and its flat bottom edge melting into the grass."""
    sh = layer(*img.size)
    ImageDraw.Draw(sh).ellipse((x + s.width * 0.08, y + s.height * 0.86, x + s.width * 0.95, y + s.height * 1.04),
                               fill=(60, 48, 34, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    a = np.asarray(s.split()[3]).astype(float)
    fade = np.clip((s.height - np.arange(s.height)) / 22.0, 0, 1)[:, None]          # last 22 px fade out
    s = s.copy()
    s.putalpha(Image.fromarray((a * fade).astype(np.uint8)))
    img.alpha_composite(s, (int(x), int(y)))


def sticker(name, height):
    s = Image.open(f'{ART}/stickers/{name}.png').convert('RGBA')
    return s.resize((int(s.width * height / s.height), height), Image.LANCZOS)


def shadowed(img, xy, text, font, fill, spacing, halo=(0, 0, 0, 230), offset=(3, 4), blur=4):
    sh = layer(*img.size)
    spaced(ImageDraw.Draw(sh), (xy[0] + offset[0], xy[1] + offset[1]), text, font, halo, spacing)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    spaced(ImageDraw.Draw(img), xy, text, font, fill, spacing)


# palettes: the light Firelink one (default) and the dusk one (python make_readme_art.py --dusk)
LIGHT = dict(scene=firelink, title=(104, 70, 38), small=(112, 100, 88), line=(170, 126, 80), ember=(214, 120, 52),
             sub=(74, 64, 56), sub2=(108, 96, 86), halo=(255, 250, 238, 220), offset=(0, 0), blur=6)
DUSK = dict(scene=scene, title=(222, 192, 128), small=(196, 188, 176), line=(170, 104, 58), ember=(232, 118, 52),
            sub=(230, 222, 208), sub2=(186, 176, 164), halo=(0, 0, 0, 230), offset=(3, 4), blur=4)


def text_block(img, p, lines):
    """lines: [(xy, text, font, colour)] with the palette's halo behind each."""
    for xy, text, font, col in lines:
        sh = layer(*img.size)
        ImageDraw.Draw(sh).text((xy[0] + p['offset'][0], xy[1] + p['offset'][1]), text, font=font, fill=p['halo'])
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(p['blur'] * 0.7)))
        ImageDraw.Draw(img).text(xy, text, font=font, fill=col)


def banner(p):
    img = p['scene'](W, H, 7)
    shadowed(img, (110, 108), 'DARK SOULS', ImageFont.truetype(FONT, 46), p['small'], 22, p['halo'], p['offset'], p['blur'])
    shadowed(img, (100, 158), 'REFORGED', ImageFont.truetype(FONT, 128), p['title'], 14, p['halo'], p['offset'], p['blur'])
    d = ImageDraw.Draw(img)
    d.line((112, 318, 760, 318), fill=p['line'], width=2)
    d.polygon([(436, 312), (448, 318), (436, 324), (424, 318)], fill=p['ember'])
    text_block(img, p, [((112, 338), 'Оверхол Dark Souls Remastered', ImageFont.truetype(FONT_R, 30), p['sub']),
                        ((112, 378), 'хаб Храма Огня · чемпионы · новые фазы боссов · кооп',
                         ImageFont.truetype(FONT_R, 24), p['sub2'])])
    s = sticker('bonfire', 360)
    place_sticker(img, s, W - s.width - 60, H - s.height - 24)
    img.convert('RGB').save(f'{ART}/banner.png', optimize=True)


def footer(p):
    w, h = 1600, 220
    img = p['scene'](w, h, 11, 0.88) if p is LIGHT else scene(w, h, 11, glow_x=0.88, sun=True)
    s = sticker('bye', 190)
    place_sticker(img, s, w - s.width - 90, h - s.height - 12)
    shadowed(img, (110, 70), 'PRAISE THE SUN', ImageFont.truetype(FONT, 40), p['title'], 12, p['halo'], p['offset'],
             p['blur'])
    text_block(img, p, [((112, 128), 'и не забудьте отдыхать у костра', ImageFont.truetype(FONT_R, 24), p['sub2'])])
    img.convert('RGB').save(f'{ART}/footer.png', optimize=True)


SHOT = f'{ART}/firelink_screenshot.webp'     # official Dark Souls screenshot of Firelink Shrine (the default)


def photo(box, w, h, blur=1.6):
    """A crop of the screenshot, scaled, softly blurred (depth of field; hides the upscale), brightened and warmed
    a little, with a dark veil on the left for the text."""
    from PIL import ImageEnhance
    src = Image.open(SHOT).convert('RGB').crop(box).resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur))
    src = ImageEnhance.Brightness(src).enhance(1.18)
    src = ImageEnhance.Color(src).enhance(1.12)
    src = ImageEnhance.Contrast(src).enhance(1.05)
    img = src.convert('RGBA')
    warm = Image.new('RGBA', (w, h), (255, 196, 120, 26))
    img.alpha_composite(warm)
    sh = np.zeros((h, w, 4), np.uint8)
    xx = np.linspace(0, 1, w)[None, :]
    sh[..., :3] = (14, 10, 8)
    sh[..., 3] = np.broadcast_to((np.clip(1 - xx / 0.60, 0, 1) ** 1.25 * 175).astype(np.uint8), (h, w))
    img.alpha_composite(Image.fromarray(sh, 'RGBA'))
    yy = np.linspace(-1, 1, h)[:, None]
    xx = np.linspace(-1, 1, w)[None, :]
    v = np.clip((xx ** 2 * 0.45 + yy ** 2 * 0.7) - 0.4, 0, 1) ** 1.3
    vg = np.zeros((h, w, 4), np.uint8)
    vg[..., 3] = (v * 150).astype(np.uint8)
    img.alpha_composite(Image.fromarray(vg, 'RGBA'))
    return img


def photo_banner():
    p = DUSK                                                  # light text with a dark halo on the photo
    img = photo((0, 0, 690, 207), W, H)                       # the ruins, the sky, the tree (left of the knight)
    shadowed(img, (110, 108), 'DARK SOULS', ImageFont.truetype(FONT, 46), (226, 218, 204), 22, p['halo'], p['offset'], 6)
    shadowed(img, (100, 158), 'REFORGED', ImageFont.truetype(FONT, 128), (232, 200, 132), 14, p['halo'], p['offset'], 6)
    d = ImageDraw.Draw(img)
    d.line((112, 318, 760, 318), fill=(200, 140, 80), width=2)
    d.polygon([(436, 312), (448, 318), (436, 324), (424, 318)], fill=p['ember'])
    text_block(img, dict(p, blur=6), [((112, 338), 'Оверхол Dark Souls Remastered', ImageFont.truetype(FONT_R, 30),
                                        (240, 232, 218)),
                                       ((112, 378), 'хаб Храма Огня · чемпионы · новые фазы боссов · кооп',
                                        ImageFont.truetype(FONT_R, 24), (214, 204, 190))])
    s = sticker('bonfire', 380)
    place_sticker(img, s, W - s.width - 50, H - s.height + 6)    # sits on the bottom edge, not in the air
    img.convert('RGB').save(f'{ART}/banner.png', optimize=True)


def photo_footer():
    w, h = 1600, 220
    img = photo((0, 40, 690, 135), w, h, 2.0)                # the arches against the sky
    s = sticker('bye', 190)
    place_sticker(img, s, w - s.width - 90, h - s.height - 12)
    shadowed(img, (110, 70), 'PRAISE THE SUN', ImageFont.truetype(FONT, 40), (232, 200, 132), 12, (0, 0, 0, 230), (3, 4), 6)
    text_block(img, dict(DUSK, blur=6), [((112, 128), 'и не забудьте отдыхать у костра', ImageFont.truetype(FONT_R, 24),
                                          (226, 216, 202))])
    img.convert('RGB').save(f'{ART}/footer.png', optimize=True)


if __name__ == '__main__':
    import sys, os
    if '--dusk' in sys.argv or '--painted' in sys.argv or not os.path.exists(SHOT):
        pal = DUSK if '--dusk' in sys.argv else LIGHT       # the painted scenes
        banner(pal)
        footer(pal)
    else:
        photo_banner()
        photo_footer()
