#!/usr/bin/env python3
"""Verify inclusion plus ONE pinned witness signature, offline.
This establishes endorsement by one pinned key; it never claims quorum/custody.
Input: {checkpoint, votes, manifest, proof}. Pin obtained independently of proof.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ulpf.integrity import leaf_hash,verify_proof,verify_signature

def verify(document,pin):
    checkpoint=document['checkpoint']
    if not verify_proof(leaf_hash(document['manifest']),document['proof'],checkpoint['root']):raise ValueError('Merkle inclusion failed')
    vote=next((x for x in document.get('votes',document.get('anchor',{}).get('votes',[])) if x['public_key']==pin),None)
    if vote is None:raise ValueError('requested witness signature missing')
    verify_signature(checkpoint,vote,[pin]);return {'verified':True,'witness_key':pin,'quorum_verified':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('proof',type=Path);p.add_argument('--public-key-file',required=True,type=Path);a=p.parse_args()
    print(json.dumps(verify(json.loads(a.proof.read_text()),a.public_key_file.read_text().strip()),indent=2))
