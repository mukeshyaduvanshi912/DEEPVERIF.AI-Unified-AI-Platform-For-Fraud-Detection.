"""
number_check.py — Caller-number reputation check + community scam-number reports.

Honest scope: this is a HEURISTIC + community-report check. A "LOW" result does NOT prove a
number is safe (scammers also use ordinary Indian SIMs). Numbers are never stored in plain
text: the community store keeps only a salted SHA-256 hash, a count and category tallies.
"""
import hashlib
import json
import os
import re
import threading
import time

STORE_FILE = os.path.join(os.path.dirname(__file__), "data", "reported_numbers.json")
SALT = os.environ.get("NUMBER_SALT", "deepverif-dev-salt")
CATEGORIES = ("digital_arrest", "kyc_bank", "courier_parcel", "investment_job", "other")
_lock = threading.Lock()


def normalize(raw: str) -> dict:
    """Return {'ok', 'e164', 'kind'} where kind is india_mobile / india_other / international / invalid."""
    s = re.sub(r"[\s\-().]", "", str(raw or ""))
    if not s:
        return {"ok": False, "kind": "invalid", "e164": ""}
    if s.startswith("00"):
        s = "+" + s[2:]
    if s.startswith("+"):
        digits = re.sub(r"\D", "", s)
        if not (8 <= len(digits) <= 15):
            return {"ok": False, "kind": "invalid", "e164": ""}
        if digits.startswith("91") and len(digits) == 12:
            s = digits[2:]
        else:
            return {"ok": True, "kind": "international", "e164": "+" + digits}
    else:
        digits = re.sub(r"\D", "", s)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        s = digits
    if not s.isdigit() or len(s) != 10:
        return {"ok": False, "kind": "invalid", "e164": ""}
    kind = "india_mobile" if s[0] in "6789" else "india_other"
    return {"ok": True, "kind": kind, "e164": "+91" + s}


def mask(e164: str) -> str:
    return "X" * max(0, len(e164) - 4) + e164[-4:]


def _key(e164: str) -> str:
    return hashlib.sha256((SALT + e164).encode()).hexdigest()


def _load() -> dict:
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _save(store: dict) -> None:
    os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
    tmp = STORE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f)
    os.replace(tmp, STORE_FILE)


def check(raw: str) -> dict:
    n = normalize(raw)
    if not n["ok"]:
        return {"error": "Please enter a valid phone number (e.g. 98xxxxxxxx or +91 98xxxxxxxx)."}
    e164, reasons, score = n["e164"], [], 0

    if n["kind"] == "international":
        score += 40
        reasons.append("Foreign (non +91) number. Indian police / CBI / banks / courier companies' "
                       "official calls usually come from Indian numbers.")
    elif n["kind"] == "india_other":
        score += 10
        reasons.append("This does not look like a normal Indian mobile number (starting with 6-9).")
    if n["kind"] != "international" and e164.startswith("+91140"):
        score += 15
        reasons.append("140-series number: used for telemarketing / promotional calls.")

    rec = _load().get(_key(e164))
    reports = int(rec["count"]) if rec else 0
    if reports:
        score += 20 if reports == 1 else 40 if reports < 10 else 60
        top = max(rec["categories"], key=rec["categories"].get)
        reasons.append(f"{reports} user(s) have reported this number as a scam (most common: {top}).")

    score = min(score, 100)
    level = "HIGH" if score >= 50 else "MEDIUM" if score >= 20 else "LOW"
    advice = {
        "HIGH": "Do not answer / hang up immediately. Never give money, OTP or Aadhaar details. If you have already been scammed, call 1930.",
        "MEDIUM": "Be careful. If the caller claims to be police/bank/courier, verify by calling the official number yourself.",
        "LOW": "No major red flag found, but this is not proof of safety. If anyone mentions 'digital arrest' or asks for money, hang up immediately.",
    }[level]
    return {"number_masked": mask(e164), "kind": n["kind"], "risk_level": level, "risk_score": score,
            "community_reports": reports, "reasons": reasons, "advice": advice}


def report(raw: str, category: str = "other") -> dict:
    n = normalize(raw)
    if not n["ok"]:
        return {"error": "Please enter a valid phone number."}
    category = category if category in CATEGORIES else "other"
    with _lock:
        store = _load()
        rec = store.setdefault(_key(n["e164"]), {"count": 0, "categories": {}, "last": 0})
        rec["count"] += 1
        rec["categories"][category] = rec["categories"].get(category, 0) + 1
        rec["last"] = int(time.time())
        _save(store)
    return {"status": "reported", "number_masked": mask(n["e164"]), "category": category,
            "community_reports": rec["count"]}
