import sys; sys.path.insert(0,".")
from souls import *
for lang in ('RUSSIAN','ENGLISH','GERMAN'):
    _,d=dcx_read(f'out/h/msg_{lang}.dcx'); b=Bnd3(d)
    _,o=dcx_read(f'orig/msg/{lang}/item.msgbnd.dcx'); ob=Bnd3(o)
    F={f[1]:Fmg(f[3]).entries for f in b.files}; OF={f[1]:Fmg(f[3]).entries for f in ob.files}
    changed={fid:[k for k in F[fid] if F[fid].get(k)!=OF[fid].get(k)] for fid in F}
    print('==',lang, {k:v for k,v in changed.items() if v})
    if lang!='GERMAN':
        for gid in (600,601,602,383):
            print(gid, '|', F[10][gid], '|', F[20][gid], '|', F[24][gid].replace('\n',' / '))
        print('patch copies equal:', F[10]==F[111], F[20]==F[110], F[24]==F[100])
