import sys, struct
sys.path.insert(0, '.')
from scan import *
h, base, size = find_game()
image = read(h, base, size)
gdm = ptr(h, rip_target(image, base, aob(image, CHR_CLASS_BASE)))
pgd = ptr(h, gdm + 0x10)
def hits(blob, label):
    for off in range(0, len(blob) - 8, 4):
        if struct.unpack_from('<i', blob, off)[0] == 5000:
            ctx = struct.unpack_from('<8i', blob, off - 8) if off >= 8 and off + 24 <= len(blob) else ()
            print(f'{label}+{off:#x}: 5000 | ctx {ctx}')
big = read(h, pgd, 0x10000) or b''
print('PlayerGameData readable bytes', hex(len(big)))
hits(big[0x2000:], 'PGD(+0x2000)')
# one level of pointers from the first 0x1000 of PlayerGameData and GameDataMan
for root, name in ((pgd, 'PGD'), (gdm, 'GDM')):
    blob = read(h, root, 0x1000) or b''
    for off in range(0, len(blob) - 8, 8):
        p = struct.unpack_from('<Q', blob, off)[0]
        if not (0x10000 < p < 0x7fffffffffff) or p == pgd:
            continue
        sub = read(h, p, 0x800)
        if sub:
            for o2 in range(0, len(sub) - 8, 4):
                sid, cnt = struct.unpack_from('<ii', sub, o2)
                if sid == 5000 and 1 < cnt <= 30:
                    print(f'[{name}+{off:#x}] -> {p:#x} +{o2:#x}: 5000, {cnt} | ctx', struct.unpack_from('<12i', sub, max(0, o2 - 16)))
