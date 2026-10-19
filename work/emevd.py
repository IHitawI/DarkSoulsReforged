"""DS1/DSR EMEVD (32-bit layout, version 0xCC) reader + EMEDF instruction definitions."""
import struct

ARG_FMT = {0: 'B', 1: 'H', 2: 'I', 3: 'b', 4: 'h', 5: 'i', 6: 'f', 8: 'I'}


class Edf:
    def __init__(self, d):
        (self.ver, _size, nbank, boff, ninstr, ioff, narg, aoff) = struct.unpack_from('<ii6i', d, 8)[0:8] \
            if False else (None, None, *struct.unpack_from('<6i', d, 0x10))
        slen, soff = struct.unpack_from('<2i', d, 0x50)
        def st(o):
            e = soff + o
            while d[e:e + 2] != b'\0\0':
                e += 2
            return d[soff + o:e].decode('utf-16-le')
        self.instr = {}  # (bank, id) -> (name, [(argname, type)])
        self.banks = {}
        for b in range(nbank):
            bid, cnt, istart, noff, _ = struct.unpack_from('<5i', d, boff + b * 20)
            self.banks[bid] = st(noff)
            for k in range(cnt):
                iid, ac, astart, inoff, _ = struct.unpack_from('<5i', d, ioff + istart + k * 20)
                args = []
                for a in range(ac):
                    an, at = struct.unpack_from('<2i', d, aoff + astart + a * 36)
                    args.append((st(an), at))
                self.instr[(bid, iid)] = (st(inoff), args)


def decode_args(blob, types):
    out, off = [], 0
    for t in types:
        f = ARG_FMT.get(t, 'i')
        sz = struct.calcsize(f)
        off = (off + sz - 1) // sz * sz
        out.append(struct.unpack_from('<' + f, blob, off)[0] if off + sz <= len(blob) else None)
        off += sz
    return out


class Emevd:
    def __init__(self, d):
        assert d[:4] == b'EVD\0'
        (self.unk, self.version, size, nev, evoff, nins, insoff, _, _, nlay, layoff,
         npar, paroff, nlink, linkoff, arglen, argoff, strlen_, stroff) = struct.unpack_from('<19i', d, 4)
        self.events = []
        for e in range(nev):
            eid, ic, io, pc, po, rest, _ = struct.unpack_from('<7i', d, evoff + e * 28)
            ins = []
            for k in range(ic):
                bank, iid, alen, aoff, lay, _ = struct.unpack_from('<6i', d, insoff + io + k * 24)
                ins.append((bank, iid, d[argoff + aoff:argoff + aoff + alen] if alen else b''))
            params = [struct.unpack_from('<5i', d, paroff + po + k * 20) for k in range(pc)]
            self.events.append({'id': eid, 'rest': rest, 'ins': ins, 'params': params})
        ends = [struct.unpack_from('<6i', d, insoff + k * 24) for k in range(nins)]
        end = max((r[3] + r[2] for r in ends if r[2]), default=0)
        self.arg_pad = arglen - end          # vanilla leaves 0-12 spare bytes; keep them as-is
        self.header_tail = struct.unpack_from('<i', d, 0x50)[0]


def dump(ev, edf, show_params=True):
    lines = [f"EVENT {ev['id']} rest={ev['rest']}"]
    pmap = {}
    for (ii, dst, src, n, _) in ev['params']:
        pmap.setdefault(ii, []).append(f'arg@{dst}<-X{src}({n})')
    for k, (bank, iid, blob) in enumerate(ev['ins']):
        name, args = edf.instr.get((bank, iid), ('?', []))
        vals = decode_args(blob, [t for _, t in args])
        a = ', '.join(f'{n}={v}' for (n, _), v in zip(args, vals))
        p = (' PARAMS ' + ' '.join(pmap[k])) if k in pmap and show_params else ''
        lines.append(f'  {bank}[{iid:02d}] {name}({a}){p}')
    return '\n'.join(lines)


def encode_args(values, types):
    out = bytearray()
    for v, t in zip(values, types):
        f = ARG_FMT.get(t, 'i')
        sz = struct.calcsize(f)
        out += bytes(-len(out) % sz)
        out += struct.pack('<' + f, v)
    out += bytes(-len(out) % 4)
    return bytes(out)


def build(ev, header_tail=None):
    """Rebuild a 32-bit DS1 EMEVD from Emevd-like data (events with raw instruction blobs)."""
    nev = len(ev.events)
    ins_rows, args, params_rows, ev_rows = [], bytearray(), [], []
    for e in ev.events:
        io = len(ins_rows) * 24
        po = len(params_rows) * 20
        for bank, iid, blob in e['ins']:
            aoff = len(args) if blob else -1
            ins_rows.append((bank, iid, len(blob), aoff, -1, 0))
            args += blob
            args += bytes(-len(args) % 4)
        params_rows += e['params']
        ev_rows.append((e['id'], len(e['ins']), io, len(e['params']), po if e['params'] else -1, e['rest'], 0))
    args += bytes(ev.arg_pad)
    evoff = 0x54
    insoff = evoff + nev * 28
    unkoff = insoff + len(ins_rows) * 24
    argoff = unkoff
    paroff = argoff + len(args)
    linkoff = paroff + len(params_rows) * 20
    size = linkoff
    out = bytearray(b'EVD\0')
    out += struct.pack('<19i', ev.unk, ev.version, size, nev, evoff, len(ins_rows), insoff, 0, unkoff,
                       0, unkoff, len(params_rows), paroff, 0, linkoff, len(args), argoff, 0, linkoff)
    out += struct.pack('<i', ev.header_tail if header_tail is None else header_tail)
    for r in ev_rows:
        out += struct.pack('<7i', *r)
    for r in ins_rows:
        out += struct.pack('<6i', *r)
    out += args
    for r in params_rows:
        out += struct.pack('<5i', *r)
    return bytes(out)
