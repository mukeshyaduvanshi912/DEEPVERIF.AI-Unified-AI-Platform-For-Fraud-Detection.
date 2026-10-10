"""
hashchain.py — Tamper-evident audit logging for DeepVerif.AI
Every fraud-detection event is appended to a hash-chained log file
(similar to a mini blockchain), so any tampering with past records
is immediately detectable by re-verifying the chain.
"""
import hashlib
import json
import os
import time

LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "audit_chain.jsonl")


def _hash_entry(prev_hash: str, entry: dict) -> str:
    payload = json.dumps({"prev_hash": prev_hash, "entry": entry}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_last_hash() -> str:
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        return "0" * 64  # genesis hash
    with open(LOG_FILE, "rb") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        buf = b""
        while pos > 0:
            pos -= 1
            f.seek(pos)
            char = f.read(1)
            if char == b"\n" and buf:
                break
            buf = char + buf
        last_line = buf.decode("utf-8").strip()
    if not last_line:
        return "0" * 64
    return json.loads(last_line)["hash"]


def append_log(module: str, result: dict) -> dict:
    """Append a new fraud-detection event to the hash chain and return the record."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    prev_hash = get_last_hash()
    entry = {
        "timestamp": time.time(),
        "module": module,
        "result": result,
    }
    entry_hash = _hash_entry(prev_hash, entry)
    record = {"prev_hash": prev_hash, "entry": entry, "hash": entry_hash}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


def get_all_logs(limit: int = 100) -> list:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    return lines[-limit:][::-1]


def verify_chain() -> dict:
    """Re-walk the whole chain and confirm no record has been altered."""
    if not os.path.exists(LOG_FILE):
        return {"valid": True, "count": 0}
    prev_hash = "0" * 64
    count = 0
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            expected = _hash_entry(prev_hash, record["entry"])
            if expected != record["hash"] or record["prev_hash"] != prev_hash:
                return {"valid": False, "broken_at": count, "count": count}
            prev_hash = record["hash"]
            count += 1
    return {"valid": True, "count": count}
