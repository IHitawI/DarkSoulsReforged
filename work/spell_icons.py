"""Spell icons for the new spells: the effect from a wiki icon (DS2/DS3/ER) on a DS1 spell background.

Backgrounds are made from the vanilla DSR spell icons of the same school (atlas Icon30): for every
pixel take the darker samples, so the per-spell effects (mostly bright) drop out and the bare paper
stays. The wiki icons carry their own paper; only what is brighter than that paper is kept and
added on top as light, which suits glowing effects (lightning, crystals, golden light).
"""
import io
import struct
import numpy as np
from PIL import Image, ImageFilter
from souls import dcx_read
from tpf import Tpf
from drb import Drb

SRC = '../tools_dl/spell_icons'
OUT = 'icons/spells'
SCHOOL_ICONS = {   # vanilla icons whose paper is used, effects that are mostly light
    'miracle': [3031, 3037, 3038, 3039, 3044, 3045, 3046, 3048, 3049, 3051, 3052],
    'sorcery': [3000, 3001, 3002, 3003, 3006, 3007, 3010, 3011, 3012, 3014, 3058, 3059],
    'pyromancy': [3020, 3021, 3024, 3026, 3027, 3028, 3030, 3035, 3036],
}


def vanilla_icons(game):
    _, d = dcx_read(f'{game}/menu/menu.drb.dcx')
    r = Drb(d)
    uv = {}
    for _, n, v in r.dlgo():
        if n.startswith('EquIcon_30'):
            _, so = r.shape(v[1])
            uv[int(n[8:])] = struct.unpack_from('<12h', d, so)[8:12]
    _, m0 = dcx_read(f'{game}/menu/menu_0.tpf.dcx')
    t = next(t for t in Tpf(m0).tex if t['name'] == 'Icon30')
    atlas = Image.open(io.BytesIO(t['data'])).convert('RGBA')
    return {k: atlas.crop(b) for k, b in uv.items()}


def background(icons, school):
    st = np.stack([np.asarray(icons[k]).astype(np.float32) for k in SCHOOL_ICONS[school]])
    rgb = st[..., :3]
    alpha = np.median(st[..., 3], axis=0)
    # paper colour: what the card looks like near its edges, where the effects rarely reach
    h, w = alpha.shape
    edge = np.zeros_like(alpha, bool)
    edge[:, :28] = edge[:, -28:] = True
    edge[:30, :] = edge[-45:, :] = True
    ref = np.median(rgb[:, edge & (alpha > 200)].reshape(-1, 3), axis=0)
    score = np.linalg.norm(rgb - ref, axis=-1)          # per sample: how far from bare paper
    order = np.argsort(score, axis=0)
    pick = np.stack([np.take_along_axis(st, order[j][None, ..., None].repeat(4, -1), 0)[0] for j in range(2)])
    out = np.median(pick, axis=0)
    out[..., 3] = alpha
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


def effect_layer(png, crop_bottom, box):
    """Light that the wiki icon adds over its own paper, fitted into `box` (w, h)."""
    im = Image.open(png).convert('RGBA')
    im = im.crop((0, 0, im.width, round(im.height * (1 - crop_bottom))))   # DS3 icons stand on a disc
    a = np.asarray(im).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3] / 255
    lum = rgb.mean(-1)
    paper = np.median(lum[alpha > 0.9])                                       # its own paper brightness
    k = np.clip((lum - paper) / max(255 - paper, 1), 0, 1) ** 0.8             # how much brighter than paper
    light = rgb * (k * alpha)[..., None]                                      # keep the effect's own colour
    light = Image.fromarray(light.astype(np.uint8), 'RGB')
    bbox = light.convert('L').point(lambda v: 255 if v > 18 else 0).getbbox() or (0, 0, im.width, im.height)
    light = light.crop(bbox)
    s = min(box[0] / light.width, box[1] / light.height)
    return light.resize((max(1, round(light.width * s)), max(1, round(light.height * s))), Image.LANCZOS)


def compose(bg, png, crop_bottom=0.0, gain=1.25, box=(118, 128), centre=(80, 84)):
    light = effect_layer(png, crop_bottom, box)
    layer = Image.new('RGB', bg.size, (0, 0, 0))
    layer.paste(light, (centre[0] - light.width // 2, centre[1] - light.height // 2))
    layer = layer.filter(ImageFilter.UnsharpMask(radius=1.2, percent=50, threshold=2))
    b = np.asarray(bg).astype(np.float32)
    l = np.asarray(layer).astype(np.float32) * gain
    out = b.copy()
    out[..., :3] = 255 - (255 - b[..., :3]) * (255 - np.clip(l, 0, 255)) / 255      # screen blend
    out[..., :3] = out[..., :3] * (b[..., 3:4] > 8) + b[..., :3] * (b[..., 3:4] <= 8)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')


# spell key -> (school, wiki file, part of the image cut from the bottom (DS3 stand), gain)
SPELLS = {
    'golden_vow': ('miracle', 'golden_vow.png', 0.0, 1.2),
    'perseverance': ('miracle', 'perseverance.png', 0.0, 1.6),
    'blessed_rain': ('miracle', 'blessed_rain.png', 0.0, 1.2),
    'lightning_stake': ('miracle', 'lightning_stake.png', 0.17, 1.3),
    'lightning_storm': ('miracle', 'lightning_storm.png', 0.17, 1.3),
    'farron_hail': ('sorcery', 'farron_hail.png', 0.17, 1.2),
    'black_serpent': ('pyromancy', 'black_serpent.png', 0.17, 1.3),
}


def build(game):
    import os
    os.makedirs(OUT, exist_ok=True)
    icons = vanilla_icons(game)
    bgs = {s: background(icons, s) for s in SCHOOL_ICONS}
    bgs['miracle'] = Image.open('icons/escape_death/parchment.png').convert('RGBA')   # cleaner, made for Escape Death
    out = {}
    for key, (school, png, cut, gain) in SPELLS.items():
        img = compose(bgs[school], f'{SRC}/{png}', cut, gain)
        img.save(f'{OUT}/{key}.png')
        out[key] = f'{OUT}/{key}.png'
    # Cleric starters: lesser versions of existing icons (Lightning Spear dimmed, Golden Vow drained of colour)
    from PIL import ImageEnhance
    spark = icons[3048].convert('RGBA')
    ImageEnhance.Brightness(spark).enhance(0.8).save(f'{OUT}/lightning_spark.png')
    out['lightning_spark'] = f'{OUT}/lightning_spark.png'
    vow = Image.open(out['golden_vow']).convert('RGBA')
    ImageEnhance.Color(vow).enhance(0.35).save(f'{OUT}/lesser_vow.png')
    out['lesser_vow'] = f'{OUT}/lesser_vow.png'
    for s, im in bgs.items():
        im.save(f'{OUT}/bg_{s}.png')
    return out


if __name__ == '__main__':
    G = r'C:\Program Files (x86)\Steam\steamapps\common\DARK SOULS REMASTERED'
    paths = build(G)
    sheet = Image.new('RGBA', (len(paths) * 168 + 3 * 168, 190), (60, 60, 60, 255))
    for i, p in enumerate(list(paths.values()) + [f'{OUT}/bg_{s}.png' for s in SCHOOL_ICONS]):
        sheet.alpha_composite(Image.open(p), (i * 168, 5))
    sheet.save('out/dbg/spell_icons.png')
