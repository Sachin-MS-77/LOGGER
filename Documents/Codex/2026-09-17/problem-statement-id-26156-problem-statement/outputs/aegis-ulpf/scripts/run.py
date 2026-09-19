#!/usr/bin/env python3
"""Start LOGFLUX from any directory, with private data beside the application."""
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
os.environ.setdefault('LOGFLUX_DATA_DIR',os.getenv('LOGFLUX_DATA_DIR',str(root/'data')))
from ulpf.app import create_app
import uvicorn
if __name__=='__main__':
    uvicorn.run(create_app(),host=os.getenv('LOGFLUX_HOST',os.getenv('LOGFLUX_HOST','127.0.0.1')),port=int(os.getenv('LOGFLUX_PORT',os.getenv('LOGFLUX_PORT','8765'))))
