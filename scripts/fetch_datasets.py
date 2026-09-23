#!/usr/bin/env python3
"""Download complete public corpora into ignored data/, with hashes and safe extraction.
No sampled fallback, payload execution, or silent replacement on failed downloads.
"""
import argparse,concurrent.futures,gzip,hashlib,json,shutil,tarfile,time,urllib.request
from pathlib import Path
CATALOG={
 'linux':('https://zenodo.org/records/8196385/files/Linux.tar.gz?download=1','tar','Loghub full Linux corpus; research/academic terms'),
 'apache':('https://zenodo.org/records/8196385/files/Apache.tar.gz?download=1','tar','Loghub full Apache corpus; research/academic terms'),
 'openssh':('https://zenodo.org/records/8196385/files/SSH.tar.gz?download=1','tar','Loghub full OpenSSH corpus; research/academic terms'),
 'honeynet30':('https://honeynet.onofri.org/scans/scan30/honeynet-Feb1_FebXX.log.gz','gz','Honeynet Scan of the Month 30 archive mirror'),
 'honeynet34':('https://honeynet.onofri.org/scans/scan34/SotM34-anton.tar.gz','tar','Honeynet Scan of the Month 34 archive mirror'),
 'maccdc2012':('https://www.secrepo.com/maccdc2012/conn.log.gz','gz','SecRepo MACCDC 2012 connection log; see source attribution/terms'),
}
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def extract(archive,dest,kind,limit=4*1024**3):
    dest.mkdir(parents=True,exist_ok=True);total=0;files=[]
    def copy(stream,path,size=None):
        nonlocal total
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('wb') as out:
            while block:=stream.read(1024*1024):
                total+=len(block)
                if total>limit:raise ValueError('uncompressed size limit exceeded')
                out.write(block)
        files.append({'path':str(path.relative_to(Path.cwd())) if path.is_absolute() and path.is_relative_to(Path.cwd()) else str(path),'bytes':path.stat().st_size,'sha256':sha(path)})
    if kind=='gz':
        with gzip.open(archive,'rb') as f:copy(f,dest/'capture.log')
    else:
        with tarfile.open(archive,'r:gz') as tf:
            for member in tf:
                target=(dest/member.name).resolve()
                if not target.is_relative_to(dest.resolve()) or member.issym() or member.islnk():raise ValueError('unsafe archive path/link')
                if member.isfile():
                    if member.size+total>limit:raise ValueError('uncompressed size limit exceeded')
                    with tf.extractfile(member) as f:copy(f,target,member.size)
    return files

def fetch(name,root):
    url,kind,terms=CATALOG[name];folder=root/name;folder.mkdir(parents=True,exist_ok=True);archive=folder/'download.gz';record={'dataset':name,'url':url,'attribution':terms,'sampled':False}
    try:
        if not archive.exists():
            part=folder/'download.part'
            request=urllib.request.Request(url,headers={'User-Agent':'LOGFLUX-research-evaluation/1.0'})
            with urllib.request.urlopen(request,timeout=60) as response,part.open('wb') as out:
                total=0
                while block:=response.read(1024*1024):
                    total+=len(block)
                    if total>1024**3:raise ValueError('compressed size exceeds 1 GiB limit')
                    out.write(block)
            part.replace(archive)
        files=extract(archive,folder/'extracted',kind)
        record.update(status='downloaded',archive_sha256=sha(archive),files=files)
    except Exception as exc:record.update(status='unavailable',error=str(exc))
    print(name,record['status'],flush=True);return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--datasets',nargs='+',choices=list(CATALOG),default=list(CATALOG));p.add_argument('--directory',default='data/datasets');p.add_argument('--manifest',default='docs/dataset-manifest.json');a=p.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:reports=list(pool.map(lambda n:fetch(n,Path(a.directory)),a.datasets))
    Path(a.manifest).write_text(json.dumps({'retrieved_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'datasets':reports},indent=2)+'\n')
    if any(r['status']!='downloaded' for r in reports):raise SystemExit(1)
