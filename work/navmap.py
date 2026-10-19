"""Top-down plot of Firelink navmeshes around the bonfire, with NPCs and candidate spots."""
import sys, struct, math
sys.path.insert(0, '.')
from souls import dcx_read, Bnd3
from msb import Msb, Part
from PIL import Image, ImageDraw, ImageFont

G = sys.argv[1]
CENTER = (-51.8, 55.7)      # bonfire (x, z)
SPAN = 26.0                 # metres shown
S = 900
def px(x, z):
    return ((x - CENTER[0]) / SPAN + 0.5) * S, ((z - CENTER[1]) / SPAN + 0.5) * S

h, d = dcx_read(G + '/map/m10_02_00_00/m10_02_00_00.nvmbnd.dcx')
img = Image.new('RGB', (S, S), (20, 20, 24))
dr = ImageDraw.Draw(img)
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 13)
edges = []
for f in Bnd3(d).files:
    x = f[3]
    nv, vo, nt, to = struct.unpack_from('<4i', x, 4)
    vs = [struct.unpack_from('<3f', x, vo + i * 12) for i in range(nv)]
    for i in range(nt):
        a, b2, c, e1, e2, e3, _ = struct.unpack_from('<7i', x, to + i * 28)
        tri = [vs[a], vs[b2], vs[c]]
        y = sum(v[1] for v in tri) / 3
        if not -62.5 < y < -57.5:        # upper level around the bonfire only
            continue
        dr.polygon([px(v[0], v[2]) for v in tri], fill=(55, 75, 55), outline=(70, 95, 70))
        for (p, q), e in zip(((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])), (e1, e2, e3)):
            if e == -1:
                edges.append((p, q))
for p, q in edges:
    dr.line([px(p[0], p[2]), px(q[0], q[2])], fill=(230, 120, 60), width=3)
# grid every 2 m
for k in range(-14, 15, 2):
    X, _ = px(CENTER[0] + k, 0); _, Z = px(0, CENTER[1] + k)
    dr.line([(X, 0), (X, S)], fill=(40, 40, 46)); dr.line([(0, Z), (S, Z)], fill=(40, 40, 46))
m = Msb(open(G + '/map/MapStudio/m10_02_00_00.msb', 'rb').read())
for e in m.parts.entries:
    p = Part(e)
    if p.type == 2 and abs(p.pos[0] - CENTER[0]) < SPAN / 2 and abs(p.pos[2] - CENTER[1]) < SPAN / 2 and -63 < p.pos[1] < -57:
        X, Z = px(p.pos[0], p.pos[2])
        dr.ellipse([X - 6, Z - 6, X + 6, Z + 6], fill=(90, 160, 255))
        dr.text((X + 8, Z - 8), f'{p.entity_id} y{p.pos[1]:.1f}', fill=(170, 200, 255), font=font)
for name, (x, z), col in (('BONFIRE', CENTER, (255, 200, 60)), ('spawn', (-47.41, 53.3), (200, 200, 200))):
    X, Z = px(x, z)
    dr.ellipse([X - 8, Z - 8, X + 8, Z + 8], fill=col)
    dr.text((X + 10, Z), name, fill=col, font=font)
dr.text((10, 10), 'top view, x right, z down, grid 2 m; orange = navmesh edge (wall/drop)', fill=(220, 220, 220), font=font)
img.save('icons/firelink_nav.png')
open('hub/nav_edges.txt', 'w').write('\n'.join(f'{p[0]:.2f} {p[1]:.2f} {p[2]:.2f} {q[0]:.2f} {q[1]:.2f} {q[2]:.2f}' for p, q in edges))
print(len(edges), 'edges')
