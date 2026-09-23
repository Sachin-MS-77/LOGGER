#!/usr/bin/env python3
"""Full-file dry-run of built-in decoding/mapping/normalization. Never drops errors.
Fresh registry baseline: no learned plugins, drift history, storage or LLM. Unknown
records are discovery-eligible; this command does not approve or deploy parsers.
"""
import argparse,collections,gzip,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ulpf.parsers import decode,built_in_mapping
from ulpf.schema import normalize
from ulpf.store import MAX_EVENT

def measure(path):
    counts=collections.Counter();errors=collections.Counter();digest=hashlib.sha256();started=time.perf_counter()
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb') as stream:
        for raw in stream:
            digest.update(raw);counts['total']+=1
            # Headers and blank lines count explicitly, never in the event denominator.
            if not raw.strip() or raw.startswith(b'#'):counts['metadata']+=1;continue
            try:
                if len(raw)>MAX_EVENT:raise ValueError('oversize')
                decoded=decode(raw);mapping=built_in_mapping(decoded)
                if not mapping:counts['discovery']+=1;continue
                event=normalize(decoded['attributes'],mapping,{'source':path.name,'received_at':'2026-01-01T00:00:00Z'})
                counts['partial' if event['quality']['issues'] else 'normalized']+=1
            except Exception as exc:counts['failed']+=1;errors[type(exc).__name__]+=1
    n=counts['total']-counts['metadata']
    return {'file':str(path.relative_to(Path.cwd())) if path.is_absolute() and path.is_relative_to(Path.cwd()) else str(path),'sha256_uncompressed':digest.hexdigest(),'physical_lines':counts['total'],'metadata_lines':counts['metadata'],'records':n,
      **{k:counts[k] for k in ('normalized','partial','discovery','failed')},
      **{k+'_percent':round(100*counts[k]/n,4) if n else 0 for k in ('normalized','partial','discovery','failed')},'error_types':dict(errors),'seconds':round(time.perf_counter()-started,3)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('files',nargs='*',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--output',default='docs/coverage.json');a=p.parse_args();files=a.files
    unavailable=[]
    if a.manifest:
        for dataset in json.loads(a.manifest.read_text())['datasets']:
            if dataset['status']!='downloaded':unavailable.append(dataset['dataset']);continue
            for f in dataset['files']:
                path=Path(f['path'])
                if path.name.lower() not in ('readme','readme.md','readme.txt','license'):files.append(path)
    results=[]
    for path in files:
        result=measure(path);results.append(result);print(json.dumps(result),flush=True)
    if not results:raise SystemExit('No complete log files available; no coverage result generated.')
    Path(a.output).write_text(json.dumps({'scope':__doc__,'files':results,'unavailable_datasets':unavailable},indent=2)+'\n')
