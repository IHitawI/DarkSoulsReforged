import sys; sys.path.insert(0,".")
from souls import *
_,a=dcx_read('orig/GameParam_vanilla.parambnd.dcx'); _,b=dcx_read('out/h/GameParam.parambnd.dcx')
A=Bnd3(a); B=Bnd3(b)
_,pd=dcx_read('orig/paramdef.paramdefbnd.dcx'); D={}
for f in Bnd3(pd).files:
    t,fl=paramdef_parse(f[3]); D[t]=Layout(fl)
same=0
for fa,fb in zip(A.files,B.files):
    nm=fa[2].decode('shift_jis').split(chr(92))[-1]
    pa,pb=Param(fa[3]),Param(fb[3]); l=D[pa.ptype]
    old={r[0]:r[1] for r in pa.rows}
    new=[r for r in pb.rows if r[0] not in old]
    chg=[r for r in pb.rows if r[0] in old and old[r[0]]!=r[1]]
    if not new and not chg: same+=1; continue
    print(f'== {nm}: +{len(new)} new, {len(chg)} changed')
    if nm in ('EquipParamGoods.param','ShopLineupParam.param'):
        for rid,row,name in new+chg:
            d=l.dump(row); o=l.dump(old[rid]) if rid in old else None
            print('  ',rid, {k:(o[k],d[k]) for k in d if o[k]!=d[k]} if o else {k:d[k] for k in ('refId','goodsUseAnim','iconId','sellValue','equipType','equipId','value','sellQuantity','eventFlag') if k in d})
print('unchanged param files', same, 'of', len(A.files))
sp=Param(B.get('SpEffectParam.param')[3]); l=D[sp.ptype]
for i in (92200,92202,92210,92212): d=l.dump(sp[i]); print(i, {k:d[k] for k in ('changeHpPoint','effectEndurance','motionInterval','soulRate','iconId','stateInfo','staminaRecoverChangeSpeed')})
