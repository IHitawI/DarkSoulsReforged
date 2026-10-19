import sys, struct
sys.path.insert(0, '.')
from scan import *
h, base, size = find_game()
image = read(h, base, size)
gdm = ptr(h, rip_target(image, base, aob(image, CHR_CLASS_BASE)))
pgd = ptr(h, gdm + 0x10)
big = read(h, pgd, 0x10000)
# locate Heal's inventory record and print it
off = next(o for o in range(0, 0x2000, 4) if struct.unpack_from('<ii', big, o) == (5000, 1))
rec = struct.unpack_from('<7i', big, off)
print('Heal inventory record @PGD+%#x:' % off, rec)
print('raw before:', struct.unpack_from('<7i', big, off - 28))
handle = rec[2]
targets = {handle: 'handle', }
for o in range(0, len(big) - 4, 4):
    v = struct.unpack_from('<i', big, o)[0]
    if v in targets and o != off + 8:
        print(f'PGD+{o:#x} = {targets[v]} | ctx', struct.unpack_from('<10i', big, max(0, o - 16)))
for root, name in ((pgd, 'PGD'), (gdm, 'GDM')):
    blob = read(h, root, 0x1000) or b''
    for po in range(0, len(blob) - 8, 8):
        p = struct.unpack_from('<Q', blob, po)[0]
        if not (0x10000 < p < 0x7fffffffffff) or p == pgd:
            continue
        sub = read(h, p, 0x1000)
        if sub:
            for o2 in range(0, len(sub) - 4, 4):
                if struct.unpack_from('<i', sub, o2)[0] == handle:
                    print(f'[{name}+{po:#x}] -> {p:#x} +{o2:#x} = handle | ctx', struct.unpack_from('<12i', sub, max(0, o2 - 16)))
