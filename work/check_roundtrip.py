import sys; sys.path.insert(0,'.')
from souls import *
h,gp=dcx_read('orig/GameParam_BetterRolling.parambnd.dcx')
_,pd=dcx_read('orig/paramdef.paramdefbnd.dcx')
g=Bnd3(gp); d=Bnd3(pd)
print('roundtrip bnd', g.build()==gp)
defs={}
for f in d.files:
    t,fl=paramdef_parse(f[3]); defs[t]=fl
for f in g.files:
    p=Param(f[3]); lay=Layout(defs[p.ptype]) if p.ptype in defs else None
    rt = p.build()==f[3]
    print(f[2].decode('shift_jis').split(chr(92))[-1], p.ptype, len(p.rows), p.rowsize, lay and lay.size, 'rt' if rt else 'RT-DIFF')
