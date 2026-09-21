#!/usr/bin/env python3
"""Run on an internet-connected system matching the offline target."""
import hashlib,json,platform,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];dest=root/'wheelhouse';dest.mkdir(exist_ok=True)
subprocess.run([sys.executable,'-m','pip','wheel','--wheel-dir',str(dest),'-r',str(root/'requirements.lock')],check=True)
manifest={'python':platform.python_version(),'system':platform.platform(),'machine':platform.machine(),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.glob('*.whl'))}}
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Offline wheels ready:',dest,'\nTransfer the entire project. Run scripts/setup.sh on the matching target.')
