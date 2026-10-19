import sys; sys.path.insert(0,".")
from souls import *
_,a=dcx_read('orig/GameParam_BetterRolling.parambnd.dcx'); _,b=dcx_read('out/GameParam.parambnd.dcx')
A=Bnd3(a); B=Bnd3(b)
_,pd=dcx_read('orig/paramdef.paramdefbnd.dcx'); D={}
for f in Bnd3(pd).files:
    t,fl=paramdef_parse(f[3]); D[t]=Layout(fl)
for fa,fb in zip(A.files,B.files):
    assert fa[2]==fb[2] and fa[0]==fb[0] and fa[1]==fb[1]
    if fa[3]!=fb[3]:
        pa,pb=Param(fa[3]),Param(fb[3]); l=D[pa.ptype]
        nm=fa[2].decode().split(chr(92))[-1]
        old={r[0]:r[1] for r in pa.rows}
        for rid,row,name in pb.rows:
            if rid not in old: print(nm,'NEW',rid,name.decode(), {k:v for k,v in l.dump(row).items() if k in('changeHpPoint','effectTargetSelf','effectTargetFriend','effectTargetEnemy','spEffectIDForShooter','spEffectId0','hitRadiusMax','spreadTime','life','effectEndurance')})
            elif old[rid]!=row:
                o=l.dump(old[rid]); n=l.dump(row); print(nm,'CHANGED',rid,name.decode(),{k:(o[k],n[k]) for k in o if o[k]!=n[k]})
        print(nm, 'rows', len(pa.rows),'->',len(pb.rows))
print('other files identical:', sum(fa[3]==fb[3] for fa,fb in zip(A.files,B.files)), 'of', len(A.files))
