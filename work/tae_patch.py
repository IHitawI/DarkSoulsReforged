"""Replace player animations in a00.tae with new ones built from existing pieces.

A new animation = a reference to an existing animation (its motion: a cast, a gesture, ...) + a list of
events (copied from existing animations, retimed, or new effect events). Its data is appended at
the end of the file and the animation list entry is pointed at it, so the vanilla bytes stay.

Spell casts are animations 6400 / 6500 + Magic refType (right / left hand). Player spells
never use refTypes 7, 14, 21, 25, 26: those slots take our own casts.
"""
import struct
from tae import Tae

CAST_BLOCKS = (6400, 6500)   # right / left hand casts (6200/6300: fizzles, no release event)
EV_CAST = 64          # releases the spell (the Magic param's bullet / effect)
EV_FFX = 112          # plays an effect at a dummy poly: (ffx id, dummy poly, ...)


class NewEvent:
    def __init__(self, start, end, type_, params):
        self.start, self.end, self.type, self.params = start, end, type_, bytes(params)


def event_params(t, aid):
    """Events of animation aid as NewEvent with their raw parameter bytes."""
    evs = t.anims[aid]
    # parameter size: up to the next structure that belongs to this animation
    marks = sorted({e.body_off for e in evs} | {e.params_off for e in evs} | {e.start_off for e in evs} |
                   {e.end_off for e in evs} | {struct.unpack_from('<i', t.d, t.body[aid] + 4)[0]})
    out = []
    for e in evs:
        nxt = min((m for m in marks if m > e.params_off), default=e.params_off + 16)
        size = max(0, min(nxt - e.params_off, 64))
        out.append(NewEvent(e.start, e.end, e.type, t.d[e.params_off:e.params_off + size]))
    return out


def ffx_event(frame, ffx, dummy, template):
    """An effect event at `frame` (30 fps) built on an existing EV_FFX event's parameters."""
    p = bytearray(template.params)
    struct.pack_into('<ii', p, 0, ffx, dummy)
    return NewEvent(frame / 30, (frame + 1) / 30, EV_FFX, p)


def motion_name(t, aid):
    fo = struct.unpack_from('<i', t.d, t.body[aid] + 24)[0]
    noff = struct.unpack_from('<i', t.d, fo + 8)[0]
    e = noff
    while t.d[e:e + 2] != b'\0\0':
        e += 2
    return t.d[noff:e].decode('utf-16-le')


def replace(data, target, source, events):
    """data: a00.tae bytes; target: animation id to replace; source: id of the animation whose motion
    it plays (an animation reference, like vanilla 621 -> 620; a motion file name is ignored by the
    game: the animation then kept its own motion and lost its sounds) or None to keep its own motion
    file; events: [NewEvent]."""
    t = Tae(data)
    assert target in t.body, target
    out = bytearray(data)

    def align():
        out.extend(bytes(-len(out) % 16))

    align()
    times = sorted({round(v, 6) for e in events for v in (e.start, e.end)})
    times_off = len(out)
    for v in times:
        out += struct.pack('<f', v)
    toff = {v: times_off + 4 * i for i, v in enumerate(times)}
    align()
    bodies = []
    for e in events:
        bodies.append(len(out))
        out += struct.pack('<ii', e.type, len(out) + 8) + e.params
        out.extend(bytes(-len(out) % 4))
    align()
    ev_off = len(out)
    for e, b in zip(events, bodies):
        out += struct.pack('<3i', toff[round(e.start, 6)], toff[round(e.end, 6)], b)
    align()
    file_off = len(out)
    if source is None:      # keeps its own motion file (a00_<target>.hkx), as vanilla blocks do
        name = motion_name(t, target).encode('utf-16-le') + b'\0\0'
        out += struct.pack('<6i', 0, file_off + 8, file_off + 24, 0, -1, 0) + name
    else:                   # reference block: (1, self + 8, empty name, source animation id, 0, 0, 0)
        out += struct.pack('<7i', 1, file_off + 8, file_off + 28, source, 0, 0, 0) + b'\0\0'
    align()
    body = len(out)
    out += struct.pack('<7i', len(events), ev_off, 0, 0, len(times), times_off, file_off)
    # point the animation list entry at the new body
    count, list_off = struct.unpack_from('<ii', out, 0x54)
    for i in range(count):
        aid, _ = struct.unpack_from('<ii', out, list_off + i * 8)
        if aid == target:
            struct.pack_into('<i', out, list_off + i * 8 + 4, body)
            break
    struct.pack_into('<i', out, 0x0C, len(out))     # file size
    return bytes(out)
