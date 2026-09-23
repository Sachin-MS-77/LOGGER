"""Parallel network witness voting with pinned, distinct signing keys."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import httpx
import json
from pathlib import Path
from types import SimpleNamespace
from .integrity import verify_signature,unb64
from .schema import digest

class RemoteLedger:
    quorum=2
    trust_note='Network witness services verify pinned signatures. Separate machines and administrators must be established by the operator; this is not Byzantine consensus.'
    def __init__(self, config_path):
        config=json.loads(Path(config_path).read_text())
        self.token=Path(config['token_file']).read_text().strip()
        if len(self.token)<24: raise ValueError('witness token too short')
        self.config=config['witnesses']
        if len(self.config)!=3 or len({w['public_key'] for w in self.config})!=3:
            raise ValueError('three distinct witness keys required')
        self.witnesses=[SimpleNamespace(name=w['name'],enabled=True,
            key=SimpleNamespace(public=w['public_key'],id=digest(unb64(w['public_key']))[:16])) for w in self.config]
    @property
    def trusted(self):return [w.key.public for w in self.witnesses]
    def anchor(self,checkpoint,history):
        return anchor(checkpoint,self.config,self.token,history)
    def close(self):pass

def anchor(checkpoint, witnesses, token, history=()):
    if len(witnesses)!=3 or len({w['public_key'] for w in witnesses})!=3:
        raise ValueError('exactly three distinct pinned witness keys are required')
    for w in witnesses:
        url=urlparse(w['url'])
        if url.scheme!='https' and not (url.scheme=='http' and url.hostname in ('localhost','127.0.0.1','::1')):
            raise ValueError('remote witnesses require HTTPS')
    def vote(w):
        with httpx.Client(timeout=5,trust_env=False,headers={'Authorization':'Bearer '+token}) as client:
            state=client.get(w['url']+'/state');state.raise_for_status();state=state.json()
            if state['public_key']!=w['public_key']: raise ValueError('witness key does not match pin')
            for old in history:
                if old['sequence']>state['sequence']:
                    reply=client.post(w['url']+'/vote',json=old);reply.raise_for_status()
                    verify_signature(old,reply.json(),[w['public_key']])
            reply=client.post(w['url']+'/vote',json=checkpoint);reply.raise_for_status()
            signature=reply.json();verify_signature(checkpoint,signature,[w['public_key']]);return signature
    votes=[];errors=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending=[(w,pool.submit(vote,w)) for w in witnesses]
        for w,future in pending:
            try: votes.append(future.result())
            except Exception as exc: errors.append({'witness':w['name'],'error':type(exc).__name__})
    return {'anchored':len(votes)>=2,'votes':votes,'errors':errors,'quorum':2,
            'trust_model':'separate HTTP witness services; administrative independence depends on deployment'}
