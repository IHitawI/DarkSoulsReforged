"""Allies can hit an enemy while you riposte or backstab it.

During a throw (backstab / riposte) the victim's animation carries the action flag 67
"Invincible Excluding Throw Attacks", so nobody else can hurt it. For every enemy the player can
throw (ThrowParam rows with a player attacker and an enemy defender) that flag is turned into
0 "Do Nothing" in the victim animation, in place (same size). Player-vs-player throws stay vanilla.
Flag names: DSAnimStudio's TAE.Template.DS1.xml (action 0 = ChrActionFlag).
"""
import os
import struct
from collections import defaultdict
from load import *
from souls import Bnd3, dcx_read, dcx_write
from tae import Tae

INVINCIBLE_EXCEPT_THROW = 67
DO_NOTHING = 0


def victims():
    """chr id -> set of victim animation ids."""
    tp, tl, _ = P['ThrowParam']
    out = defaultdict(set)
    for rid, *_ in tp.rows:
        r = tp[rid]
        if tl.get(r, 'AtkChrId') == 0 and tl.get(r, 'DefChrId') > 0 and tl.get(r, 'defAnimId') > 0:
            out[tl.get(r, 'DefChrId')].add(tl.get(r, 'defAnimId'))
    return out


def patch_all(game, out_dir):
    """Write patched chr/cXXXX.anibnd.dcx files; returns {chr: number of flags removed}."""
    os.makedirs(out_dir, exist_ok=True)
    done = {}
    for chr_id, anims in sorted(victims().items()):
        path = f'{game}/chr/c{chr_id:04d}.anibnd.dcx'
        if not os.path.exists(path):
            continue
        h, d = dcx_read(path)
        d = bytearray(d)
        entry = Bnd3(bytes(d)).entry
        count = 0
        # patch each TAE where it lies inside the archive: same size, nothing else moves
        for i in range(struct.unpack_from('<i', d, 0x10)[0]):
            _, size, off, _, noff = struct.unpack_from('<Iiiii', d, 0x20 + i * entry)
            name = bytes(d[noff:d.index(b'\0', noff)]).decode('shift_jis').lower()
            if not name.endswith('.tae'):
                continue
            t = Tae(bytes(d[off:off + size]))
            for aid in anims & set(t.anims):
                for e in t.anims[aid]:
                    at = off + e.params_off
                    if e.type == 0 and struct.unpack_from('<i', d, at)[0] == INVINCIBLE_EXCEPT_THROW:
                        struct.pack_into('<i', d, at, DO_NOTHING)
                        count += 1
        if count:
            dcx_write(f'{out_dir}/c{chr_id:04d}.anibnd.dcx', h, bytes(d))
            done[chr_id] = count
    return done
