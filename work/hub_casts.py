"""Own cast animations for the new spells (player TAE, c0000.anibnd a00.tae).

Cast animation = 6400 (right hand) / 6500 (left hand) + Magic refType. Free refTypes: 7, 14, 25, 26.
  7  Lightning Storm - the raised-talisman cast (Soothing Sunlight) with a golden flash at the talisman
Gesture motions as casts (6825/6830 tried for Blessed Rain / Golden Vow) made the spells uncastable,
so those two use vanilla casts.
"""
from souls import Bnd3, dcx_read, dcx_write
from tae import Tae
import tae_patch as tp

STORM = 7
RAISE_CAST = 4                         # Soothing Sunlight's cast: talisman raised
FLASH = 20236                          # Sunlight Spear impact


def _with_flash(t, events, base_aid):
    """Add a golden flash at the talisman when the spell is released."""
    tmpl = next((e for e in tp.event_params(t, base_aid) if e.type == tp.EV_FFX), None)
    if tmpl is None:
        return events
    dummy = tmpl.params[4] | (tmpl.params[5] << 8)    # same dummy poly the cast glow uses
    out = list(events)
    for e in events:
        if e.type == tp.EV_CAST:
            out.append(tp.ffx_event(round(e.start * 30), FLASH, dummy, tmpl))
    return out


def build(data):
    """data: a00.tae bytes -> patched bytes."""
    t = Tae(data)
    for block in tp.CAST_BLOCKS:
        base = block + RAISE_CAST
        evs = _with_flash(t, tp.event_params(t, base), base)
        data = tp.replace(data, block + STORM, base, evs)
    return data


def patch_anibnd(src_path, out_path, *more):
    """more: further a00.tae transforms (bytes -> bytes) applied after the casts."""
    h, d = dcx_read(src_path)
    bnd = Bnd3(d)
    f = next(f for f in bnd.files if f[2].decode('shift_jis').endswith('a00.tae'))
    f[3] = build(f[3])
    for step in more:
        f[3] = step(f[3])
    dcx_write(out_path, h, bnd.build())
