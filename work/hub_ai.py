"""Enemies up to newer standards (in the spirit of Nightreign): they notice you sooner, chase longer and gang up.

NpcThinkParam (every enemy row, not the NPCs 6xxx and not bosses that never go home):
  sight +25% (at most 60 m), hearing +50%, they forget you 50% later, chase 60% farther from home,
  and two of them attack at once instead of one (TeamAttackEffectivity 25 -> 50).
Tracking through an attack is already late in vanilla: "Disable Turning" (TAE flag 7) covers only the first
10-18 frames of a wind-up, the turn is free up to the hit (some attacks even snap with SetTurnSpeed 240 right
before it) - what limits it is the turn speed, raised in hub_fixes.py (x1.35). patch_tae() below (start the
early lock just before the hit) changed almost nothing for that reason and is not used by build.py.
"""
import os, struct
from load import *
from souls import Bnd3, dcx_read, dcx_write
from tae import Tae

SIGHT, HEARING, FORGET, CHASE, TEAM = 1.25, 1.5, 1.5, 1.6, 50
LOCK_BEFORE_HIT = (4 / 30, 10 / 30)        # the lock may start this long before the hit (seconds)
DISABLE_TURNING = 7
ATTACKS = range(3000, 4000)
SKIP_CHR = {0, 1000}                         # the player, bonfires


def apply():
    tp, tl, _ = P['NpcThinkParam']
    n = 0
    for rid, row, _ in tp.rows:
        if rid < 100000 or tl.get(row, 'maxBackhomeDist') >= 9999:
            continue
        tl.set(row, 'eye_dist', min(round(tl.get(row, 'eye_dist') * SIGHT), 60))
        tl.set(row, 'ear_dist', round(tl.get(row, 'ear_dist') * HEARING))
        tl.set(row, 'SightTargetForgetTime', round(tl.get(row, 'SightTargetForgetTime') * FORGET))
        tl.set(row, 'SoundTargetForgetTime', round(tl.get(row, 'SoundTargetForgetTime') * FORGET))
        tl.set(row, 'maxBackhomeDist', round(tl.get(row, 'maxBackhomeDist') * CHASE))
        tl.set(row, 'backhomeDist', round(tl.get(row, 'backhomeDist') * CHASE))
        if tl.get(row, 'TeamAttackEffectivity') == 25:
            tl.set(row, 'TeamAttackEffectivity', TEAM)
        n += 1
    return n


def _flag(t, e):
    return struct.unpack_from('<i', t.d, e.params_off)[0]


def patch_tae(data):
    """a TAE -> (patched bytes, changed windows)."""
    t = Tae(data)
    out = bytearray(data)
    changed = 0
    for aid, evs in t.anims.items():
        if aid not in ATTACKS:
            continue
        body = t.body[aid]
        n_ev, ev_off, _, _, n_t, t_off = struct.unpack_from('<6i', data, body)
        times = [(struct.unpack_from('<f', data, t_off + 4 * i)[0], t_off + 4 * i) for i in range(n_t)]
        uses = {}
        for e in evs:
            for off in (e.start_off, e.end_off):
                uses[off] = uses.get(off, 0) + 1
        hits = sorted(e.start for e in evs if e.type == 1)
        for k, e in enumerate(evs):
            if e.type != 0 or _flag(t, e) != DISABLE_TURNING:
                continue
            nxt = [h for h in hits if h > e.start]
            if not nxt:
                continue
            h = nxt[0]
            if e.end <= h - LOCK_BEFORE_HIT[0]:       # the turn is free again before the hit: already tracks
                continue
            if e.start >= h - LOCK_BEFORE_HIT[1]:     # locks late already
                continue
            if uses.get(e.start_off) == 1:            # this time is the lock's own: just move it
                struct.pack_into('<f', out, e.start_off, h - 6 / 30)
                changed += 1
                continue
            good = [(abs(v - (h - 6 / 30)), off) for v, off in times
                    if h - LOCK_BEFORE_HIT[1] <= v <= h - LOCK_BEFORE_HIT[0] and v > e.start]
            if not good:
                continue
            struct.pack_into('<i', out, ev_off + 12 * k, min(good)[1])     # shared: point at a time already there
            changed += 1
    return bytes(out), changed


def patch_all(game, out_dir, chrs):
    """chrs: model ids of the enemies placed in the maps. Writes chr/cXXXX.anibnd.dcx."""
    os.makedirs(out_dir, exist_ok=True)
    total = {}
    for cid in sorted(set(chrs) - SKIP_CHR):
        path = f'{game}/chr/c{cid:04d}.anibnd.dcx'
        if not os.path.exists(path):
            continue
        h, d = dcx_read(path)
        bnd = Bnd3(d)
        n = 0
        for f in bnd.files:
            if f[2].lower().endswith(b'.tae'):
                f[3], c = patch_tae(f[3])
                n += c
        if n:
            dcx_write(f'{out_dir}/c{cid:04d}.anibnd.dcx', h, bnd.build())
            total[cid] = n
    return total
