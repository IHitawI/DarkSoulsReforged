import sys; sys.path.insert(0,'.')
from souls import *
# game data: vanilla GameParam; row names borrowed from BetterRolling's copy (English, readable; ignored by the game)
# --br-base: build on BetterRolling's GameParam (the standalone AllyHeal mod was built on it)
BASE = 'orig/GameParam_BetterRolling.parambnd.dcx' if '--br-base' in sys.argv else 'orig/GameParam_vanilla.parambnd.dcx'
H,GP=dcx_read(BASE)
_,PD=dcx_read('orig/paramdef.paramdefbnd.dcx')
_,NAMED=dcx_read('orig/GameParam_BetterRolling.parambnd.dcx')
G=Bnd3(GP)
DEFS={}
for f in Bnd3(PD).files:
    t,fl=paramdef_parse(f[3]); DEFS[t]=Layout(fl)
_named={f[2]:Param(f[3]) for f in Bnd3(NAMED).files}
P={}
for f in G.files:
    p=Param(f[3])
    q=_named.get(f[2])
    if q is not None:
        nm={}
        for rid,_,name in q.rows: nm.setdefault(rid,name)
        for r in p.rows:
            if r[0] in nm: r[2]=nm[r[0]]
    P[f[2].decode('shift_jis').split(chr(92))[-1].replace('.param','')]=(p,DEFS[p.ptype],f)
def row(pn,rid):
    p,l,_=P[pn]; return l.dump(p[rid])
def nz(d): return {k:v for k,v in d.items() if v not in (0,-1,0.0)}
# Russian texts
MSG_H, MSG_D = dcx_read('orig/msg/RUSSIAN/item.msgbnd.dcx')
MSG = Bnd3(MSG_D)
def fmg(fid): return Fmg([x for x in MSG.files if x[1]==fid][0][3]).entries
