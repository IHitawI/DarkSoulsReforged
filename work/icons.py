"""Put new item icons into the DSR icon atlas Icon21 (menu/menu_3.tpf) at unused DRB icon slots."""
import io, struct
from PIL import Image, ImageFilter
from souls import dcx_read, dcx_write
from tpf import Tpf

# unused icon ids defined in menu.drb, pointing at empty cells of Icon21: id -> (col, row)
# Vanilla placeholder cells 'C1'..'C16' are drawn in Icon21, but menu.drb only has sprites (EquIcon_<id>) for
# 2159-2167 (C1-C9): ids 2168-2174 show nothing in game.
FREE_SLOTS = {2159 + k: ((3 + k) % 12, 2 + (3 + k) // 12) for k in range(9)}
# more ids with a DRB sprite that no item uses and whose atlas cell no used sprite shares (empty or cut art):
# id -> atlas texture (the sprite's box is read from menu.drb)
# (1252 / 1260 point below the 1024 px of Icon12: unusable)
EXTRA_SLOTS = {3032: 'Icon30', 1268: 'Icon12', 2008: 'Icon20', 2018: 'Icon20', 2033: 'Icon20', 2044: 'Icon20',
               4012: 'Icon40', 112: 'Icon01'}
CELL = (160, 180)  # DSR atlas pixels (DRB uses half-size coordinates: 80x90, step 82x92)


def cell_box(col, row):
    x, y = (1 + 82 * col) * 2, (1 + 92 * row) * 2
    return x, y


def prepare(png_path):
    im = png_path.convert('RGBA') if isinstance(png_path, Image.Image) else Image.open(png_path).convert('RGBA')
    im = im.crop(im.getbbox())
    s = min((CELL[0] - 14) / im.width, (CELL[1] - 14) / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=70, threshold=2))
    cell = Image.new('RGBA', CELL, (0, 0, 0, 0))
    cell.alpha_composite(im, ((CELL[0] - im.width) // 2, (CELL[1] - im.height) // 2))
    return cell


def encode_dxt5_mips(img, orig_dds):
    """DXT5 data for every mip level, under the original DDS header."""
    mips = struct.unpack_from('<i', orig_dds, 28)[0] or 1
    out = bytearray(orig_dds[:128])
    w, h = img.size
    for level in range(mips):
        lw, lh = max(1, w >> level), max(1, h >> level)
        mip = img if level == 0 else img.resize((lw, lh), Image.LANCZOS)
        if lw < 4 or lh < 4:     # DXT works on 4x4 blocks
            pad = Image.new('RGBA', (max(4, lw), max(4, lh)), (0, 0, 0, 0)); pad.paste(mip, (0, 0)); mip = pad
        b = io.BytesIO()
        mip.save(b, 'DDS', pixel_format='DXT5')
        out += b.getvalue()[128:]
    return bytes(out)


def _dxt5(img):
    b = io.BytesIO()
    img.save(b, 'DDS', pixel_format='DXT5')
    return b.getvalue()[128:]


def patch_region(dds, icon, x0, y0):
    """Put `icon` at (x0, y0) of a DXT5 atlas, re-encoding only the 4x4 blocks it covers
    (on every mip level), so the rest of the atlas keeps its original bytes."""
    h, w = struct.unpack_from('<ii', dds, 12)     # DDS header: height, width
    mips = struct.unpack_from('<i', dds, 28)[0] or 1
    full = Image.open(io.BytesIO(dds)).convert('RGBA')
    full.paste(Image.new('RGBA', icon.size, (0, 0, 0, 0)), (x0, y0))
    full.alpha_composite(icon, (x0, y0))
    out = bytearray(dds)
    pos = 128
    for level in range(mips):
        lw, lh = max(1, w >> level), max(1, h >> level)
        bw, bh = max(1, (lw + 3) // 4), max(1, (lh + 3) // 4)
        if lw >= 4 and lh >= 4:
            img = full if level == 0 else full.resize((lw, lh), Image.LANCZOS)
            bx0, by0 = (x0 >> level) // 4, (y0 >> level) // 4
            # round the end up at both steps: a cell at the atlas edge must not shrink to no block
            bx1 = min(bw, -(-(-(-(x0 + icon.width) // (1 << level))) // 4))
            by1 = min(bh, -(-(-(-(y0 + icon.height) // (1 << level))) // 4))
            blocks = _dxt5(img.crop((bx0 * 4, by0 * 4, bx1 * 4, by1 * 4)))
            n = bx1 - bx0
            for r in range(by1 - by0):
                dst = pos + ((by0 + r) * bw + bx0) * 16
                out[dst:dst + n * 16] = blocks[r * n * 16:(r + 1) * n * 16]
        pos += bw * bh * 16
    assert pos == len(dds), (pos, len(dds))
    return bytes(out)


def patch_texture_cell(src_path, out_path, tex_name, png, box):
    """Draw a ready-made icon (exact cell size) into one cell of an atlas texture of a menu TPF."""
    h, d = dcx_read(src_path)
    t = Tpf.parse_raw(d)
    tex = next(x for x in t.tex if x['name'] == tex_name)
    icon = Image.open(png).convert('RGBA')
    assert icon.size == (box[2] - box[0], box[3] - box[1]), icon.size
    tex['data'] = patch_region(tex['data'], icon, box[0], box[1])
    dcx_write(out_path, h, t.build())


def patch_atlas(src_path, out_path, icons):
    """icons: {icon id: png path}"""
    h, d = dcx_read(src_path)
    t = Tpf.parse_raw(d)
    tex = next(x for x in t.tex if x['name'] == 'Icon21')
    atlas = Image.open(io.BytesIO(tex['data'])).convert('RGBA')
    for icon_id, png in icons.items():
        col, row = FREE_SLOTS[icon_id]
        x, y = cell_box(col, row)
        atlas.paste(Image.new('RGBA', CELL, (0, 0, 0, 0)), (x, y))
        atlas.alpha_composite(prepare(png), (x, y))
    new = encode_dxt5_mips(atlas, tex['data'])
    assert len(new) == len(tex['data']), (len(new), len(tex['data']))
    tex['data'] = new
    dcx_write(out_path, h, t.build())
    return atlas


def sprite_boxes(game):
    """icon id -> atlas box (x0, y0, x1, y1) from menu.drb."""
    import re
    from drb import Drb
    _, d = dcx_read(f'{game}/menu/menu.drb.dcx')
    r = Drb(d)
    out = {}
    for _, n, v in r.dlgo():
        m = re.fullmatch(r'EquIcon_(\d+)', n)
        if m:
            _, so = r.shape(v[1])
            out[int(m.group(1))] = struct.unpack_from('<12h', d, so)[8:12]
    return out


def patch_extra(game, out_dir, icons):
    """icons: {icon id in EXTRA_SLOTS: png path or Image}. Patches whichever menu_N.tpf holds each atlas,
    starting from an already patched copy in out_dir if there is one."""
    import os
    boxes = sprite_boxes(game)
    by_tex = {}
    for iid, png in icons.items():
        by_tex.setdefault(EXTRA_SLOTS[iid], []).append((iid, png))
    for n in range(6):
        name = f'menu_{n}.tpf.dcx'
        src = f'{out_dir}/{name}' if os.path.exists(f'{out_dir}/{name}') else f'{game}/menu/{name}'
        h, d = dcx_read(src)
        t = Tpf.parse_raw(d)
        hit = False
        for tex in t.tex:
            for iid, png in by_tex.get(tex['name'], []):
                box = boxes[iid]
                assert (box[2] - box[0], box[3] - box[1]) == CELL, (iid, box)
                th, tw = struct.unpack_from('<ii', tex['data'], 12)
                assert box[2] <= tw and box[3] <= th, (iid, box, tw, th)
                tex['data'] = patch_region(tex['data'], prepare(png), box[0], box[1])
                hit = True
        if hit:
            dcx_write(f'{out_dir}/{name}', h, t.build())
