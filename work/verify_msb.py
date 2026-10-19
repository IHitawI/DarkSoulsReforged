import sys,struct,math; sys.path.insert(0,".")
import hub_npc as h
from msb import *
from place import load_nav, floor_y
G=sys.argv[1]
def refs(m):
    names=[Part(e).name for e in m.parts.entries]; mods=model_names(m)
    out=[]
    for kind,e,off in h.part_refs(m):
        v=struct.unpack_from('<i',e,off)[0]; owner=cstr(e,struct.unpack_from('<i',e,0)[0])
        out.append((kind,owner,names[v] if 0<=v<len(names) else v))
    for e in m.parts.entries:
        out.append(('model',Part(e).name,mods[Part(e).model_index]))
    return out
for sub in ('MapStudio','MapStudioNew'):
    a=Msb(open(f'{G}/map/{sub}/m10_02_00_00.msb','rb').read()); b=Msb(open(f'out/h/{sub}/m10_02_00_00.msb','rb').read())
    newnames={Part(e).name for e in b.parts.entries}-{Part(e).name for e in a.parts.entries}
    ra=refs(a); rb=[r for r in refs(b) if r[1] not in newnames]
    print(sub,'vanilla refs unchanged:', sorted(ra)==sorted(rb), len(ra))
    def runs(entries,typef):
        seq=[]
        for e in entries:
            t=typef(e)
            if not seq or seq[-1]!=t: seq.append(t)
        return seq
    print('  part types grouped:', len(runs(b.parts.entries,lambda e:Part(e).type))==len(set(Part(e).type for e in b.parts.entries)),
          '| model types grouped:', len(runs(b.models.entries,lambda e:struct.unpack_from('<i',e,4)[0]))==len(set(struct.unpack_from('<i',e,4)[0] for e in b.models.entries)))
    ok=all(Part(e).type_index==sum(1 for x in b.parts.entries[:i] if Part(x).type==Part(e).type) for i,e in enumerate(b.parts.entries))
    mt=[struct.unpack_from('<i',e,4)[0] for e in b.models.entries]
    okm=all(struct.unpack_from('<i',e,8)[0]==sum(1 for t in mt[:i] if t==mt[i]) for i,e in enumerate(b.models.entries))
    from collections import Counter
    use=Counter(Part(e).model_index for e in b.parts.entries)
    okc=all(struct.unpack_from('<i',e,0x10)[0]==use.get(i,0) for i,e in enumerate(b.models.entries))
    print('  part typeIndex ok:',ok,'| model typeIndex ok:',okm,'| instance counts ok:',okc,'| models',len(a.models.entries),'->',len(b.models.entries),'parts',len(a.parts.entries),'->',len(b.parts.entries))
    mods=model_names(b); names=[Part(e).name for e in b.parts.entries]
    for e in b.parts.entries:
        p=Part(e)
        if p.name in newnames:
            extra=''
            if p.type==2:
                t=struct.unpack_from('<16i',e,p.type_off); extra=f'talk {t[4]} coll {names[t[7]]} anim {t[14]}'
            print('   NEW',p.name,PART_TYPES[p.type],mods[p.model_index],'ent',p.entity_id,'pos',tuple(round(x,2) for x in p.pos),'rotY',round(p.rot[1],1),extra)
