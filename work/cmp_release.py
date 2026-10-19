import sys; sys.path.insert(0,".")
from souls import *
_,a=dcx_read(sys.argv[1]); _,b=dcx_read(sys.argv[2]); _,v=dcx_read('orig/GameParam_vanilla.parambnd.dcx')
diff=0
for fa,fb,fv in zip(Bnd3(a).files,Bnd3(b).files,Bnd3(v).files):
    pa,pb,pv=Param(fa[3]),Param(fb[3]),Param(fv[3])
    da=[(r[0],bytes(r[1])) for r in pa.rows]; db=[(r[0],bytes(r[1])) for r in pb.rows]
    if da!=db: diff+=1; print('DATA DIFF', fa[2][-30:])
    if len(pa.rows)!=len(pv.rows): print(fa[2].decode('shift_jis').split(chr(92))[-1], 'rows vanilla', len(pv.rows), '->', len(pa.rows))
print('param files with different data:', diff)
