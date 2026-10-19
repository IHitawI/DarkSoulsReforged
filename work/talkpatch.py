"""Put compiled ESDs into the vanilla talkesdbnd, keeping vanilla file IDs and paths."""
import sys; sys.path.insert(0, '.')
from souls import Bnd3, dcx_read, dcx_write


def patch(vanilla_path, compiled_path, out_path):
    h, v = dcx_read(vanilla_path)
    _, c = dcx_read(compiled_path)
    vb, cb = Bnd3(v), Bnd3(c)
    sep = '\\'
    base = lambda p: p.decode('shift_jis').split(sep)[-1]
    vmap = {base(f[2]): f for f in vb.files}
    changed, added = [], []
    for f in cb.files:
        n = base(f[2])
        if n in vmap:
            if vmap[n][3] != f[3]:
                vmap[n][3] = f[3]
                changed.append(n)
        else:
            tmpl = vb.files[-1]
            path = tmpl[2].decode('shift_jis').rsplit(sep, 1)[0] + sep + n
            vb.files.append([tmpl[0], max(x[1] for x in vb.files) + 1, path.encode('shift_jis'), f[3]])
            added.append(n)
    dcx_write(out_path, h, vb.build())
    return changed, added


if __name__ == '__main__':
    print(patch(*sys.argv[1:4]))
