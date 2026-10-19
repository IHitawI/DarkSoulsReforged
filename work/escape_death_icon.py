"""Escape Death icon: the hand-and-halo from the wiki icon on a DSR miracle parchment.

Vanilla DSR leaves icon 3042 (Escape Death) empty. parchment.png is a clean miracle parchment
made from the other DSR miracle icons; the glyph comes from the (low-res) wiki icon, scaled up,
colour-matched to the parchment and blended in with a soft mask.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIKI = '../tools_dl/escape_death/Escapedeath.png'
PARCH = 'icons/escape_death/parchment.png'
OUT = 'icons/escape_death/escape_death.png'
HALO = (55.1, 46.4, 24.0)      # centre and radius of the halo in the wiki icon
SCALE = 1.75
TARGET = (82, 80)              # where the halo centre goes on the parchment


def mask_wiki(size):
    m = Image.new('L', size, 0)
    d = ImageDraw.Draw(m)
    cx, cy, r = HALO
    r += 5
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    d.polygon([(cx - 15, cy + 10), (cx + 14, cy + 10), (cx + 12, cy + 40), (cx - 10, cy + 40)], fill=255)  # wrist
    return m.filter(ImageFilter.GaussianBlur(4))


def build():
    wiki = Image.open(WIKI).convert('RGBA')
    parch = Image.open(PARCH).convert('RGBA')
    m = mask_wiki(wiki.size)
    big = (round(wiki.width * SCALE), round(wiki.height * SCALE))
    wiki = wiki.resize(big, Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
    m = m.resize(big, Image.LANCZOS)
    ox, oy = round(TARGET[0] - HALO[0] * SCALE), round(TARGET[1] - HALO[1] * SCALE)
    layer = Image.new('RGBA', parch.size, (0, 0, 0, 0))
    layer.paste(wiki, (ox, oy))
    lm = Image.new('L', parch.size, 0)
    lm.paste(m, (ox, oy))
    p = np.asarray(parch).astype(np.float32)
    w = np.asarray(layer).astype(np.float32)
    a = np.asarray(lm).astype(np.float32) / 255 * (w[..., 3] / 255) * (p[..., 3] / 255)
    # colour match: the wiki parchment near the mask edge -> this parchment's colour there
    ring = (a > 0.15) & (a < 0.6)
    for c in range(3):
        w[..., c] += p[..., c][ring].mean() - w[..., c][ring].mean()   # shift only: keeps the glow's contrast
    out = p.copy()
    out[..., :3] = p[..., :3] * (1 - a[..., None]) + np.clip(w[..., :3], 0, 255) * a[..., None]
    Image.fromarray(out.astype(np.uint8), 'RGBA').save(OUT)
    return OUT


if __name__ == '__main__':
    print(build())
