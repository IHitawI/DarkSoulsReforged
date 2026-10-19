"""Read-only view of the DSR menu.drb item icon sprites."""
import re, struct

TAGS = rb'(STR\0|TEXI|SHPR|CTPR|ANIP|INTP|SCDP|SHAP|CTRL|ANIK|ANIO|ANIM|SCDK|SCDO|SCDL|DLGO|DLG\0|END\0)'


class Drb:
    def __init__(self, d):
        self.d = d
        self.sec = {}
        for m in re.finditer(TAGS, d):
            tag = m.group().decode().strip('\0')
            if tag not in self.sec:
                size, count = struct.unpack_from('<ii', d, m.start() + 4)
                self.sec[tag] = (m.start() + 16, size, count)

    def s(self, off):
        p = self.sec['STR'][0] + off
        e = p
        while self.d[e:e + 2] != b'\0\0':
            e += 2
        return self.d[p:e].decode('utf-16-le')

    def textures(self):
        o, _, n = self.sec['TEXI']
        return [self.s(struct.unpack_from('<i', self.d, o + i * 8)[0]) for i in range(n)]

    def dlgo(self):
        o, _, n = self.sec['DLGO']
        for i in range(n):
            vals = struct.unpack_from('<8i', self.d, o + i * 32)
            yield i, self.s(vals[0]), vals

    def shape(self, shap_off):
        o = self.sec['SHAP'][0] + shap_off
        type_off, shpr_off = struct.unpack_from('<ii', self.d, o)
        return self.s(type_off), self.sec['SHPR'][0] + shpr_off
