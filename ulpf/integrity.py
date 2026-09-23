"""Ed25519 signatures, domain-separated Merkle proofs, permissioned witnesses.

The default three witnesses are local and do not form independent trust domains.
They implement signed checkpoint replication, not Byzantine consensus.
"""
import base64
import json
import os
from pathlib import Path
import sqlite3
import threading
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from .schema import canonical, digest, utcnow

def b64(value): return base64.b64encode(value).decode()
def unb64(value): return base64.b64decode(value, validate=True)

class SigningKey:
    def __init__(self, path):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            self.key = Ed25519PrivateKey.from_private_bytes(path.read_bytes())
        else:
            self.key = Ed25519PrivateKey.generate()
            fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            with os.fdopen(fd,"wb") as f:
                f.write(self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
        self.public = b64(self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
        self.id = digest(unb64(self.public))[:16]
    def sign(self, document):
        return {"key_id": self.id, "public_key": self.public, "signature": b64(self.key.sign(canonical(document)))}

def verify_signature(document, signature, trusted_keys):
    if signature["public_key"] not in trusted_keys:
        raise ValueError("signature is not from a pinned trusted key")
    Ed25519PublicKey.from_public_bytes(unb64(signature["public_key"])).verify(unb64(signature["signature"]), canonical(document))
    return True

def leaf_hash(manifest): return digest(b"\x00" + canonical(manifest))
def parent_hash(left, right): return digest(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right))

def merkle(leaves):
    if not leaves: raise ValueError("cannot seal an empty batch")
    levels = [leaves[:]]
    while len(levels[-1]) > 1:
        row = levels[-1]
        levels.append([parent_hash(row[i], row[i+1] if i+1<len(row) else row[i]) for i in range(0,len(row),2)])
    proofs = []
    for index in range(len(leaves)):
        pos, proof = index, []
        for row in levels[:-1]:
            sibling = pos ^ 1
            proof.append({"side":"left" if pos%2 else "right", "hash":row[sibling] if sibling<len(row) else row[pos]})
            pos //= 2
        proofs.append(proof)
    return levels[-1][0], proofs

def verify_proof(leaf, proof, root):
    current = leaf
    for item in proof:
        current = parent_hash(item["hash"], current) if item["side"] == "left" else parent_hash(current, item["hash"])
    return current == root

class Witness:
    def __init__(self, directory, name):
        self.name = name
        self.key = SigningKey(Path(directory)/f"{name}.key")
        self.db = sqlite3.connect(Path(directory)/f"{name}.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS votes(seq INTEGER PRIMARY KEY, hash TEXT NOT NULL, payload TEXT NOT NULL, signature TEXT NOT NULL)")
        self.db.commit(); self.lock = threading.Lock(); self.enabled = True
    def vote(self, checkpoint):
        if not self.enabled: raise ConnectionError(f"{self.name} unavailable")
        with self.lock:
            found = self.db.execute("SELECT hash,signature FROM votes WHERE seq=?",(checkpoint["sequence"],)).fetchone()
            h = digest(canonical(checkpoint))
            if found:
                if found[0] != h: raise ValueError("witness refuses conflicting checkpoint")
                return json.loads(found[1])
            last = self.db.execute("SELECT seq,hash FROM votes ORDER BY seq DESC LIMIT 1").fetchone()
            if checkpoint["sequence"] != (last[0]+1 if last else 1) or checkpoint["previous"] != (last[1] if last else "0"*64):
                raise ValueError("witness needs ordered checkpoint synchronization")
            signature = self.key.sign(checkpoint); signature["witness"] = self.name
            self.db.execute("INSERT INTO votes VALUES(?,?,?,?)",(checkpoint["sequence"],h,json.dumps(checkpoint),json.dumps(signature)))
            self.db.commit(); return signature
    def close(self): self.db.close()

class WitnessLedger:
    trust_note='Local witnesses share one host. Verification detects inconsistency; it does not prove source truth or independent custody.'
    def __init__(self, directory):
        self.witnesses = [Witness(directory, f"witness-{i}") for i in range(1,4)]
        self.quorum = 2
    @property
    def trusted(self): return [w.key.public for w in self.witnesses]
    def anchor(self, checkpoint, history):
        votes, errors = [], []
        for witness in self.witnesses:
            try:
                with witness.lock:
                    last = witness.db.execute("SELECT COALESCE(MAX(seq),0) FROM votes").fetchone()[0]
                for old in history:
                    if old["sequence"] > last: witness.vote(old)
                votes.append(witness.vote(checkpoint))
            except Exception as exc: errors.append({"witness":witness.name,"error":str(exc)})
        return {"votes":votes,"errors":errors,"quorum":self.quorum,"anchored":len(votes)>=self.quorum,
                "trust_model":"three local permissioned witnesses; no independent administrative isolation"}
    def close(self):
        for w in self.witnesses: w.close()
