#!/usr/bin/env python3
"""Validate asset preservation, catalogue coverage, and repository-link rewrites."""
import hashlib, json, pathlib, re, subprocess, sys
import restructure_datasets as migration

def validate(root):
    plan=json.loads((root/'docs/migration/path-map.json').read_text()); mapping={e['old']:e['new'] for e in plan['files']}
    failures=[];existing_broken=[];changed_json=0
    def original(path):
        return subprocess.check_output(['git','-C',str(root),'show',plan['baseCommit']+':'+path])
    original_files=set(subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',plan['baseCommit']]).decode().splitlines())
    destinations=set()
    for e in plan['files']:
        path=root/e['new'];destinations.add(e['new'])
        if not path.is_file():failures.append('Missing '+e['new']);continue
        if (root/e['old']).exists():failures.append('Old path still exists: '+e['old'])
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',e['datasetIdentifier'] or ''):failures.append('Invalid identifier: '+str(e['datasetIdentifier']))
        if path.parts and e['new'].split('/')[1]!=e['datasetIdentifier']:failures.append('Folder/identifier mismatch '+e['new'])
        if hashlib.sha256(original(e['old'])).hexdigest()!=e['sha256']:failures.append('Manifest checksum does not match base: '+e['old'])
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=e['sha256']:
            if path.suffix!='.json':failures.append('Asset bytes changed: '+e['new']);continue
            expected=migration.rewrite(json.loads(original(e['old'])),mapping)
            if json.loads(data)!=expected:failures.append('Unexpected JSON edit: '+e['new'])
            changed_json+=1
        if path.suffix=='.json':
            old=json.loads(original(e['old']));updated=json.loads(data)
            # Validate every original repository reference, distinguishing baseline defects.
            for value in migration.strings(old):
                target=migration.assetpath(value)
                if target and target not in original_files:
                    existing_broken.append({'source':e['new'],'target':target})
            for value in migration.strings(updated):
                target=migration.assetpath(value)
                # Updated URLs use datasets/, so inspect their new prefix too.
                if value.startswith(migration.TARGET):target=value[len(migration.TARGET):]
                elif value.startswith(('datasets/','shared/')):target=value
                if target and target in mapping:failures.append('Old mapped link remains: '+target)
                if target and target.startswith(('datasets/','shared/')) and not (root/target).is_file():failures.append('New link missing: '+target)
    if len(destinations)!=len(plan['files']):failures.append('Destination collision')
    catalogue=json.loads((root/'catalogue.json').read_text());indexed=[]
    for ds,record in catalogue['datasets'].items():
        if record['datasetIdentifier']!=ds:failures.append('Catalogue key mismatch: '+ds)
        for files in record['assets'].values():indexed.extend(files)
    expected={e['new'] for e in plan['files'] if e['datasetIdentifier'] and pathlib.PurePosixPath(e['new']).name!='.gitkeep'}
    if set(indexed)!=expected or len(indexed)!=len(set(indexed)):failures.append('Catalogue coverage mismatch')
    # All original files must remain, whether moved, archived, or unchanged.
    for old in original_files:
        if old in mapping:continue
        path=root/old
        if not path.exists():
            archive='docs/migration/legacy-metadata.json' if old=='metadata.json' else 'docs/migration/legacy-indexes/'+old
            path=root/archive
        if not path.is_file():failures.append('Unaccounted original file: '+old)
    return {'baseCommit':plan['baseCommit'],'movedFiles':len(plan['files']),
            'datasetIdentifiers':len(catalogue['datasets']),
            'documentedIdentifiers':sum(r['identifierStatus']=='documented' for r in catalogue['datasets'].values()),
            'provisionalIdentifiers':sorted(k for k,v in catalogue['datasets'].items() if v['identifierStatus']=='provisional'),
            'rewrittenJsonFiles':changed_json,'failures':failures,'preExistingUnresolvedLinks':existing_broken}

def main():
    root=pathlib.Path(__file__).resolve().parents[1];result=validate(root)
    if '--report' in sys.argv:
        (root/'docs/migration/validation-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('preExistingUnresolvedLinks','provisionalIdentifiers')},indent=2))
    print(f"Pre-existing unresolved link occurrences: {len(result['preExistingUnresolvedLinks'])}; provisional identifiers: {len(result['provisionalIdentifiers'])}")
    return bool(result['failures'])

if __name__=='__main__':sys.exit(main())
