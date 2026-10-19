"""Snapshot (read-only) of PlayerGameData + player chr blocks, for before/after diffs."""
import sys, struct, pickle
sys.path.insert(0, '.')
from scan import *
h, base, size = find_game()
image = read(h, base, size)
gdm = ptr(h, rip_target(image, base, aob(image, CHR_CLASS_BASE)))
pgd = ptr(h, gdm + 0x10)
wcb = ptr(h, rip_target(image, base, aob(image, WORLD_CHR_BASE)))
chr_ = ptr(h, wcb + 0x68)
blocks = {}
def ok(p): return 0x10000 < p < 0x7fffffffffff
def walk(addr, path, depth, n=0x1000):
    if addr in blocks: return
    blob = read(h, addr, n)
    if not blob: return
    blocks[addr] = (path, blob)
    if depth == 0: return
    for o in range(0, len(blob) - 8, 8):
        p = struct.unpack_from('<Q', blob, o)[0]
        if ok(p): walk(p, f'{path}[{o:#x}]', depth - 1)
walk(pgd, 'PGD', 1, 0x10000)
walk(chr_, 'chr', 2)
walk(gdm, 'GDM', 2)
pickle.dump({'pgd': pgd, 'chr': chr_, 'gdm': gdm, 'blocks': blocks}, open(sys.argv[1], 'wb'))
print('saved', len(blocks), 'blocks', sum(len(b) for _, b in blocks.values()) // 1024, 'KB')
