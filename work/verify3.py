import sys; sys.path.insert(0,".")
from souls import *
_,a=dcx_read('orig/GameParam_vanilla.parambnd.dcx'); _,b=dcx_read('out/h/GameParam.parambnd.dcx')
for fa,fb in zip(Bnd3(a).files,Bnd3(b).files):
    nm=fa[2].decode('shift_jis').split(chr(92))[-1]
    pa,pb=Param(fa[3]),Param(fb[3])
    n=len(pa.rows)
    data_chg=[pa.rows[i][0] for i in range(n) if pa.rows[i][0]!=pb.rows[i][0] or pa.rows[i][1]!=pb.rows[i][1]]
    if data_chg or len(pb.rows)!=n: print(nm, 'existing rows changed:', data_chg[:20], '| appended:', len(pb.rows)-n)
