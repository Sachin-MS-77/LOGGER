#!/usr/bin/env python3
"""Start AEGIS from any directory, with private data beside the application."""
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
os.environ.setdefault('AEGIS_DATA_DIR',str(root/'data'))
from ulpf.app import create_app
import uvicorn
if __name__=='__main__':
    uvicorn.run(create_app(),host=os.getenv('AEGIS_HOST','127.0.0.1'),port=int(os.getenv('AEGIS_PORT','8765')))
