"""DSR player TAE reader: animation events (when to spawn a bullet, play an effect, ...).

DSR keeps the 32-bit DS1 layout (version 0x1000B):
  header: 0x50 id, 0x54 anim count, 0x58 anim list offset ({int id, int body offset} each)
  anim body (28 bytes): event count, event headers offset, group count, groups offset,
                        time count, times offset, anim file offset
  event header: start time offset, end time offset, body offset
  event body: int type, int params offset, params...
Events keep their file offsets, so they can be patched in place (same size).
"""
import struct


class Event:
    __slots__ = ('start', 'end', 'type', 'params_off', 'start_off', 'end_off', 'body_off')

    def __repr__(self):
        return f'{self.start * 30:5.1f}-{self.end * 30:5.1f} t{self.type}'


class Tae:
    def __init__(self, d):
        assert d[:4] == b'TAE ' and struct.unpack_from('<i', d, 8)[0] == 0x1000B
        self.d = d
        self.id, count, list_off = struct.unpack_from('<3i', d, 0x50)
        self.anims = {}
        self.body = {}
        for i in range(count):
            aid, off = struct.unpack_from('<ii', d, list_off + i * 8)
            self.body[aid] = off
            self.anims[aid] = self._anim(off)

    def _anim(self, off):
        d = self.d
        n_ev, ev_off = struct.unpack_from('<ii', d, off)
        events = []
        for k in range(n_ev):
            s_off, e_off, body = struct.unpack_from('<3i', d, ev_off + k * 12)
            e = Event()
            e.start_off, e.end_off, e.body_off = s_off, e_off, body
            e.start = struct.unpack_from('<f', d, s_off)[0]
            e.end = struct.unpack_from('<f', d, e_off)[0]
            e.type, e.params_off = struct.unpack_from('<ii', d, body)
            events.append(e)
        return events

    def ints(self, e, n=6):
        return struct.unpack_from(f'<{n}i', self.d, e.params_off)

    def floats(self, e, n=6):
        return struct.unpack_from(f'<{n}f', self.d, e.params_off)
