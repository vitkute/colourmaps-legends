#!/usr/bin/env python3
"""Reproducible datasetIdentifier migration. Run on the original tree; dry-run default."""
import argparse, collections, hashlib, json, pathlib, re, subprocess
from urllib.parse import unquote, urlsplit
ROOTS = {'colourmaps', 'data_descriptors', 'legends', 'thumbnails'}
SOURCE_URL = 'https://documentation.dataspace.copernicus.eu/Data/CopernicusServices/CLMS.html'
TARGET = 'https://raw.githubusercontent.com/vitkute/colourmaps-legends/datasetidentifier-layout/'

def tracked(root):
    return subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().strip('\0').split('\0')

def strings(v):
    if isinstance(v,str): yield v
    elif isinstance(v,dict):
        for x in v.values(): yield from strings(x)
    elif isinstance(v,list):
        for x in v: yield from strings(x)

def assetpath(v):
    value=unquote(v).replace('\\','/')
    if value.split('/')[0] in ROOTS: return value
    u=urlsplit(value)
    if u.netloc in ('github.com','raw.githubusercontent.com'):
        parts=u.path.strip('/').split('/')
        # Only this repository and its upstream aliases.
        if len(parts)>3 and parts[0] in ('vitkute','copernicus-land','cgls') and parts[1]=='colourmaps-legends':
            offset=4 if u.netloc=='github.com' and parts[2] in ('blob','raw') else 3
            path='/'.join(parts[offset:])
            if path.split('/')[0] in ROOTS: return path
    return None

def build(root):
    files=tracked(root); known=set(json.loads((root/'docs/migration/documented-dataset-identifiers.json').read_text()))
    matchids=set(known)
    def prefix(name):
        candidates=[i for i in matchids if name==i or name.startswith(i+'_') or name.startswith(i+'.')]
        return max(candidates,key=len) if candidates else None
    descriptors={}; folderids=collections.defaultdict(set); refs=collections.defaultdict(set); provisional=set()
    for name in files:
        p=pathlib.PurePosixPath(name)
        if len(p.parts)<3 or p.parts[0]!='data_descriptors' or p.suffix!='.json': continue
        d=json.loads((root/name).read_text()); candidates=[d.get('datasetIdentifier',''),d.get('name',''),d.get('eodataPath','').rstrip('/').split('/')[-1],p.stem,p.parent.name]
        ds=next((prefix(c) for c in candidates if prefix(c)),None)
        if ds is None:
            # Existing identifiers are provisional; do not treat arbitrary paths as IDs.
            ds=next((c for c in candidates if re.fullmatch(r'[A-Za-z0-9_.-]+',c) and '_v' in c),None)
            if ds is None: raise ValueError('No safe identifier for '+name)
            ds=re.sub(r'(_v[0-9]+(?:\.[0-9]+)?)(?:_[0-9]{4}(?:-[0-9]{4})?)$', r'\1', ds)
            provisional.add(ds)
        descriptors[name]=ds; folderids[p.parent.name].add(ds)
        for value in strings(d):
            path=assetpath(value)
            if path: refs[path].add(ds)
    matchids.update(descriptors.values())
    # Folder-level candidates also cover datasets without descriptors.
    for name in files:
        parts=pathlib.PurePosixPath(name).parts
        if len(parts)>=3 and parts[0] in ROOTS and not folderids[parts[1]]:
            ds=prefix(parts[1])
            if ds: folderids[parts[1]].add(ds)
            elif not parts[1].startswith('clms_') and re.fullmatch(r'[A-Za-z0-9_.-]+_v[0-9.]+',parts[1]):
                folderids[parts[1]].add(parts[1]); provisional.add(parts[1])
    plan=[]; used=set()
    for name in files:
        p=pathlib.PurePosixPath(name)
        if len(p.parts)<3 or p.parts[0] not in ROOTS: continue
        kind,folder,*tail=p.parts; ds=descriptors.get(name); reason='descriptor'
        if not ds:
            ds=prefix(p.stem); reason='identifier filename'
        if not ds:
            candidate=re.match(r'^(clms_(?:vlcc|wsi|vpp|ua|pa|clcplus)_.+?_v[0-9]+(?:\.[0-9]+)?)(?:_|$)',p.stem)
            if candidate:
                proposed=candidate.group(1)
                product=re.split(r'_(?:europe|global|pantropical|northernhemisphere)_',proposed)[0]
                if not folderids[folder] or any(i.startswith(product+'_') for i in folderids[folder]):
                    ds=proposed;provisional.add(ds);reason='provisional filename identifier'
        if not ds and len(refs[name])==1:
            ds=next(iter(refs[name])); reason='descriptor reference'
        if not ds and len(folderids[folder])==1:
            ds=next(iter(folderids[folder])); reason='dataset folder'
        if not ds:
            match=re.match(r'^(clms_(?:vlcc|wsi|vpp|ua|pa|clcplus)_.+?_v[0-9]+(?:\.[0-9]+)?)(?:_|$)',p.stem)
            if match:
                ds=match.group(1);provisional.add(ds);reason='provisional filename identifier'
        if ds:
            new='/'.join(['datasets',ds,kind,*tail])
            if new in used: new='/'.join(['datasets',ds,kind,'variants',folder,*tail])
            status='documented' if ds in known else 'provisional'
        else:
            new='/'.join(['shared',kind,folder,*tail]); reason='shared or unresolved';status='unassigned'
        if new in used: raise ValueError('Collision: '+new)
        used.add(new)
        plan.append(dict(old=name,new=new,datasetIdentifier=ds,status=status,evidence=reason,sha256=hashlib.sha256((root/name).read_bytes()).hexdigest()))
    return dict(baseCommit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip(),identifierSource=SOURCE_URL,sourceChecked='2026-10-28',files=plan)

def rewrite(v,mapping):
    if isinstance(v,dict):return {k:rewrite(x,mapping) for k,x in v.items()}
    if isinstance(v,list):return [rewrite(x,mapping) for x in v]
    if isinstance(v,str):
        path=assetpath(v)
        if path in mapping:
            return TARGET+mapping[path] if urlsplit(v).netloc else mapping[path]
    return v

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    root=pathlib.Path(__file__).resolve().parents[1]
    if (root/'datasets').exists():raise ValueError('Migration already applied; use validate_layout.py instead')
    if args.apply:
        branch=subprocess.check_output(['git','-C',str(root),'branch','--show-current']).decode().strip()
        if not branch or branch in ('main','master'):raise ValueError('Use a migration branch')
    plan=build(root);mapping={e['old']:e['new'] for e in plan['files']}
    out=root/'docs/migration/path-map.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(plan,indent=2)+'\n')
    print(collections.Counter(e['status'] for e in plan['files']))
    if not args.apply: print('Dry run: wrote docs/migration/path-map.json');return
    for e in plan['files']:
        dest=root/e['new']
        if dest.exists():raise ValueError('Existing destination '+e['new'])
    for e in plan['files']:
        dest=root/e['new'];dest.parent.mkdir(parents=True,exist_ok=True);(root/e['old']).rename(dest)
    for e in plan['files']:
        p=root/e['new']
        if p.suffix=='.json':
            old=json.loads(p.read_text());new=rewrite(old,mapping)
            if old!=new:p.write_text(json.dumps(new,indent=2,ensure_ascii=False)+'\n')
    # Old indexes are historical snapshots, never active inventories.
    for kind in ROOTS:
        p=root/kind/'index.json'
        if p.exists():
            dest=root/'docs/migration/legacy-indexes'/kind/'index.json';dest.parent.mkdir(parents=True,exist_ok=True);p.rename(dest)
    p=root/'metadata.json'
    if p.exists():p.rename(root/'docs/migration/legacy-metadata.json')
    catalogue={'schemaVersion':'1.0','key':'datasetIdentifier','datasets':{}}
    for e in plan['files']:
        ds=e['datasetIdentifier']
        if not ds or pathlib.PurePosixPath(e['new']).name=='.gitkeep':continue
        record=catalogue['datasets'].setdefault(ds,{'datasetIdentifier':ds,'identifierStatus':e['status'],'assets':{}})
        record['assets'].setdefault(e['old'].split('/')[0],[]).append(e['new'])
    (root/'catalogue.json').write_text(json.dumps(catalogue,indent=2)+'\n')
    print('Applied; run scripts/validate_layout.py and review docs/migration.')

if __name__=='__main__':main()
