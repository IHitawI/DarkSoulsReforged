"""Elite looks: recoloured textures instead of a glow.

Hollows (c2500) take their body textures from a texture-only character, c2509 (NpcParam
normalChangeTexChrId = 2509: a chrbnd with a tpf and an empty flver). Every elite gets such a texture
character of its own, one per (model, trait), numbered from FIRST_ID: the same texture names the model
asks for, with the colour maps recoloured (normal / specular maps are copied as they are).
The game looks a texture up with the model's id in its name replaced by the texture character's id:
c4531 asks for "c4531_1" and, with normalChangeTexChrId 5369, shows "c5369_1" (c2231 -> c2239 likewise).
So the copies are renamed: cMMMM_... -> cNNNN_... (NNNN = the new texture character).
The model's textures come from its texture character (if it has one), its chrbnd tpf or its
chrtpfbhd/.chrtpfbdt pair.
"""
import io, os, struct
from PIL import Image, ImageOps
import numpy as np
from souls import Bnd3, dcx_read, dcx_write
from tpf import Tpf
from texbank import wanted_textures, build_tpf, _undcx

TEMPLATE = 2509                 # vanilla texture character: its dcx header, bnd layout and empty flver
FIRST_ID = 9000                 # c9000.. are free
DXT5 = 5                        # TPF format code
NOT_COLOUR = ('_n', '_s', '_h', '_r', '_em', '_m')


def _recolour(img, trait):
    a = np.asarray(img.convert('RGBA')).astype(np.float32)
    alpha = a[..., 3:]
    lum = (a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    if trait == 'stone':        # grey, cold, a little lighter: a statue
        out = lum * 0.85 + 30 + np.array([0, 2, 8], np.float32)
    elif trait == 'abyss':      # near black with a violet sheen
        out = lum * np.array([0.32, 0.22, 0.42], np.float32)
    elif trait == 'plague':     # sickly yellow, bile
        out = lum * np.array([0.95, 0.88, 0.25], np.float32)
    elif trait == 'vampire':    # blood red
        out = lum * np.array([1.15, 0.35, 0.35], np.float32)
    elif trait == 'regen':      # teal, like living water
        out = lum * np.array([0.25, 0.8, 0.75], np.float32)
    elif trait == 'rage':       # charred, ember orange in the light parts
        out = lum * np.array([1.2, 0.55, 0.18], np.float32) * (lum / 255 + 0.35)
    else:
        raise ValueError(trait)
    return Image.fromarray(np.concatenate([np.clip(out, 0, 255), alpha], -1).astype(np.uint8), 'RGBA')


def _dds_dxt5(img):
    """DXT5 DDS with a full mip chain."""
    levels = []
    w, h = img.size
    while True:
        lw, lh = max(1, w >> len(levels)), max(1, h >> len(levels))
        mip = img if not levels else img.resize((lw, lh), Image.LANCZOS)
        if lw < 4 or lh < 4:
            pad = Image.new('RGBA', (max(4, lw), max(4, lh))); pad.paste(mip, (0, 0)); mip = pad
        b = io.BytesIO(); mip.save(b, 'DDS', pixel_format='DXT5')
        levels.append(b.getvalue())
        if lw == 1 and lh == 1:
            break
    head = bytearray(levels[0][:128])
    struct.pack_into('<I', head, 8, struct.unpack_from('<I', head, 8)[0] | 0x20000)     # DDSD_MIPMAPCOUNT
    struct.pack_into('<I', head, 28, len(levels))
    struct.pack_into('<I', head, 108, struct.unpack_from('<I', head, 108)[0] | 0x400008)  # COMPLEX | MIPMAP
    return bytes(head) + b''.join(l[128:] for l in levels)


def _chr_textures(game, cid):
    """name (lower) -> texture of c<cid>: its chrbnd tpf and its chrtpfbhd/bdt."""
    out = {}
    path = f'{game}/chr/c{cid:04d}.chrbnd.dcx'
    if not os.path.exists(path):
        return out, b''
    _, d = dcx_read(path)
    flver = b''
    for f in Bnd3(d).files:
        name = f[2].decode('shift_jis').lower()
        if f[1] == 100 and name.endswith('.tpf'):
            out.update({t['name'].lower(): t for t in Tpf(f[3]).tex})
        elif name.endswith('.flver'):
            flver = f[3]
        elif name.endswith('.chrtpfbhd'):
            bhd, bdt = f[3], open(f'{game}/chr/c{cid:04d}.chrtpfbdt', 'rb').read()
            assert bhd[:4] == b'BHF3' and bhd[0xC] in (0x54, 0x74), bhd[:16]
            for i in range(struct.unpack_from('<i', bhd, 0x10)[0]):
                _, size, off, _, _, _ = struct.unpack_from('<IiiiiI', bhd, 0x20 + i * 0x18)
                out.update({t['name'].lower(): t for t in Tpf(_undcx(bdt[off:off + size])).tex})
    return out, flver


def build(game, wanted, out_dir, first=FIRST_ID):
    """wanted: {(model id, texture chr id or -1, trait)}; writes the texture characters,
    returns {(model, trait): new texture chr id}."""
    os.makedirs(out_dir, exist_ok=True)
    h, d = dcx_read(f'{game}/chr/c{TEMPLATE}.chrbnd.dcx')
    tmpl = Bnd3(d)
    head = Tpf(next(f for f in tmpl.files if f[1] == 100)[3]).head
    ids, nid = {}, first
    for model, tex, trait in sorted(wanted):
        textures, flver = _chr_textures(game, model)
        if tex > 0:
            textures.update(_chr_textures(game, tex)[0])
        names = wanted_textures(flver)
        picked = [textures[n] for n in sorted(names) if n in textures]
        while os.path.exists(f'{game}/chr/c{nid}.chrbnd.dcx'):
            nid += 1
        prefixes = tuple(f'c{x:04d}' for x in (model, tex) if x and x > 0)
        out = []
        for t in picked:
            t = dict(t)
            if t['name'].lower().startswith(prefixes):
                t['name'] = f'c{nid}' + t['name'][5:]
            if not t['name'].lower().endswith(NOT_COLOUR):
                img = Image.open(io.BytesIO(t['data'])); img.load()
                t.update(data=_dds_dxt5(_recolour(img, trait)), fmt=DXT5, mips=0)
            out.append(t)
        if not any(not t['name'].lower().endswith(NOT_COLOUR) for t in out):
            print(f'elite looks: c{model:04d} has no colour textures, skipped')
            continue
        bnd = Bnd3(d)
        for f in bnd.files:
            f[2] = f[2].replace(f'c{TEMPLATE}'.encode(), f'c{nid}'.encode())
            if f[1] == 100:
                f[3] = build_tpf(head, out)
        dcx_write(f'{out_dir}/c{nid}.chrbnd.dcx', h, bnd.build())
        ids[(model, trait)] = nid
        nid += 1
    return ids


def preview(game, traits, path):
    """One strip with every trait on a hollow's face, for a look without the game."""
    tex, _ = _chr_textures(game, TEMPLATE)
    base = Image.open(io.BytesIO(tex['c2509']['data'])); base.load()
    crop = base.crop((870, 0, 1024, 220))
    strip = Image.new('RGBA', (crop.width * (len(traits) + 1), crop.height))
    strip.paste(crop, (0, 0))
    for k, trait in enumerate(traits, 1):
        strip.paste(_recolour(crop, trait), (k * crop.width, 0))
    ImageOps.contain(strip, (strip.width * 2, strip.height * 2)).save(path)
