import sys, struct
sys.path.insert(0, '.')
from scan import *
h, base, size = find_game()
image = read(h, base, size)
wcb = ptr(h, rip_target(image, base, aob(image, WORLD_CHR_BASE)))
chr_ = ptr(h, wcb + 0x68)
print(f'player chr {chr_:#x}')
def ok(p): return 0x10000 < p < 0x7fffffffffff
seen = set()
def search(addr, path, depth):
    if addr in seen: return
    seen.add(addr)
    blob = read(h, addr, 0x1000)
    if not blob: return
    for o in range(0, len(blob) - 8, 4):
        sid, cnt = struct.unpack_from('<ii', blob, o)
        if sid == 5000 and 0 < cnt <= 30:
            print(f'{path}+{o:#x}: 5000,{cnt} | ctx', struct.unpack_from('<10i', blob, max(0, o - 8)))
    if depth == 0: return
    for o in range(0, len(blob) - 8, 8):
        p = struct.unpack_from('<Q', blob, o)[0]
        if ok(p): search(p, f'{path}[{o:#x}]', depth - 1)
search(chr_, 'chr', 2)
print('searched', len(seen), 'blocks')
