import pickle, struct, sys
a = pickle.load(open('before.pkl', 'rb')); b = pickle.load(open('after.pkl', 'rb'))
old, new = int(sys.argv[1]), int(sys.argv[2])
for addr, (path, blob) in a['blocks'].items():
    if addr not in b['blocks']: continue
    nb = b['blocks'][addr][1]
    for o in range(0, min(len(blob), len(nb)) - 4, 4):
        if struct.unpack_from('<i', blob, o)[0] == old and struct.unpack_from('<i', nb, o)[0] == new:
            print(f'{path}+{o:#x} (abs {addr+o:#x}): {old}->{new} | after ctx', struct.unpack_from('<12i', nb, max(0, o - 24)))
    for o in range(0, min(len(blob), len(nb))):
        if blob[o] == old and nb[o] == new and o % 4:
            print(f'  byte {path}+{o:#x}: {old}->{new}')
