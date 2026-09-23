"""Separately deployable, authenticated checkpoint witness.

Each instance needs its own directory and key. Use TLS for remote deployment.
Running three instances on one computer is process isolation, not independent custody.
"""
import argparse
from contextlib import asynccontextmanager
import hmac
import json
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from .integrity import Witness

class Checkpoint(BaseModel):
    sequence: int = Field(ge=1)
    previous: str = Field(pattern=r'^[a-f0-9]{64}$')
    root: str = Field(pattern=r'^[a-f0-9]{64}$')
    event_count: int = Field(ge=0)
    created_at: str = Field(min_length=1,max_length=64)

def create_witness_app(directory, name, token):
    if len(token)<24: raise ValueError('witness token must contain at least 24 characters')
    Path(directory).mkdir(parents=True,exist_ok=True)
    witness= Witness(directory,name)
    @asynccontextmanager
    async def lifespan(app):
        yield
        witness.close()
    app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    def authenticate(authorization):
        if not hmac.compare_digest(authorization,'Bearer '+token):
            raise HTTPException(401,'authentication required')
    @app.get('/health')
    def health(): return {'status':'ok','role':'witness'}
    @app.get('/state')
    def state(authorization:str=Header(default='')):
        authenticate(authorization)
        with witness.lock:
            row=witness.db.execute('SELECT seq,hash FROM votes ORDER BY seq DESC LIMIT 1').fetchone()
        return {'name':name,'public_key':witness.key.public,'sequence':row[0] if row else 0,'hash':row[1] if row else '0'*64}
    @app.post('/vote')
    def vote(checkpoint:Checkpoint,authorization:str=Header(default='')):
        authenticate(authorization)
        try: return witness.vote(checkpoint.model_dump())
        except ValueError as exc: raise HTTPException(409,str(exc)) from exc
    return app

if __name__=='__main__':
    import uvicorn
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);p.add_argument('--name',required=True)
    p.add_argument('--token-file',required=True);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,required=True)
    p.add_argument('--cert');p.add_argument('--key');a=p.parse_args()
    if a.host not in ('127.0.0.1','::1','localhost') and not (a.cert and a.key):
        p.error('remote witness binding requires --cert and --key')
    uvicorn.run(create_witness_app(a.directory,a.name,Path(a.token_file).read_text().strip()),host=a.host,port=a.port,ssl_certfile=a.cert,ssl_keyfile=a.key)
