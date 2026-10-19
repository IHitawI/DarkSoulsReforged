import sys; sys.path.insert(0,".")
from souls import *
_,pd=dcx_read('orig/paramdef.paramdefbnd.dcx'); D={}
for f in Bnd3(pd).files:
    t,fl=paramdef_parse(f[3]); D[t]=Layout(fl)
old_path, new_path = sys.argv[1], sys.argv[2]
_,a=dcx_read(old_path); _,b=dcx_read(new_path)
for fa,fb in zip(Bnd3(a).files,Bnd3(b).files):
    if fa[3]==fb[3]: continue
    pa,pb=Param(fa[3]),Param(fb[3]); l=D[pa.ptype]
    assert len(pa.rows)==len(pb.rows)
    for ra,rb in zip(pa.rows,pb.rows):
        if ra[1]!=rb[1]:
            o,n=l.dump(ra[1]),l.dump(rb[1]); print(ra[0], ra[2].decode('shift_jis','replace'), {k:(o[k],n[k]) for k in o if o[k]!=n[k]})
