import sys; sys.path.insert(0,".")
from souls import *
_,pd=dcx_read('orig/paramdef.paramdefbnd.dcx'); D={}
for f in Bnd3(pd).files:
    t,fl=paramdef_parse(f[3]); D[t]=Layout(fl)
_,b=dcx_read('out/h/GameParam.parambnd.dcx'); B=Bnd3(b)
def P(n): p=Param(B.get(n+'.param')[3]); return p,D[p.ptype]
bp,bl=P('Bullet'); sp,sl=P('SpEffectParam'); gp,gl=P('EquipParamGoods')
for i in (161,150,3550,3551): d=bl.dump(bp[i]); print('bullet',i,{k:d[k] for k in ('spEffectIDForShooter','spEffectId0','spEffectId1','spEffectId2','HitBulletID','life')})
d=sl.dump(sp[92300]); print('vuln',{k:d[k] for k in ('slashDamageCutRate','fireDamageCutRate','effectEndurance','stateInfo','effectTargetSelf','effectTargetFriend','effectTargetEnemy')})
d=gl.dump(gp[380]); print('rubbish',{k:d[k] for k in ('refCategory','refId','goodsUseAnim','enable_live')})
for lang in ('RUSSIAN','ENGLISH','GERMAN'):
    _,m=dcx_read(f'out/h/msg_{lang}.dcx'); F={f[1]:Fmg(f[3]).entries for f in Bnd3(m).files}
    for g in (296,293,380): print(lang,g,'|',F[20][g],'|',F[24][g].replace('\n',' / ')[-110:])
