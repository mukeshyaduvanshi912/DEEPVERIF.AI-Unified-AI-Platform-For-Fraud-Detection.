"""
upi_check.py — QR / UPI-link checker.
Key idea: a UPI QR or payment link ALWAYS sends money from the scanner. Scammers say "scan to receive money".
This is a heuristic warning tool; it cannot verify that a payee is genuine, and LOW never means "safe".
"""
import re
from urllib.parse import urlparse, parse_qs, unquote

import cv2
import numpy as np

import sms_phishing

VPA_RE = re.compile(r"^[A-Za-z0-9._\-]{2,256}@[A-Za-z][A-Za-z0-9]{1,63}$")
SCAM_WORDS = ("refund", "cashback", "prize", "lottery", "reward", "gift", "claim", "kyc", "verify",
              "helpdesk", "customercare", "customer care", "support", "winner", "offer", "lucky")


def parse(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {"kind": "invalid"}
    low = raw.lower()
    if low.startswith("upi://"):
        u = urlparse(raw)
        action = (u.netloc or u.path.strip("/")).lower()
        q = {k.lower(): unquote(v[0]) for k, v in parse_qs(u.query).items() if v}
        return {"kind": "mandate" if action == "mandate" else "pay", "action": action, "q": q}
    if low.startswith(("http://", "https://")):
        return {"kind": "url", "raw": raw}
    if VPA_RE.match(raw):
        return {"kind": "pay", "action": "vpa", "q": {"pa": raw}}
    return {"kind": "other", "raw": raw}


def _amount(v):
    try:
        a = float(v)
        return a if a > 0 else None
    except (TypeError, ValueError):
        return None


def check(raw: str, expecting_to_receive: bool = False) -> dict:
    p = parse(raw)
    kind = p["kind"]
    if kind == "invalid":
        return {"error": "Please enter the QR text or a UPI link."}

    reasons, score = [], 0
    out = {"kind": kind, "headline": "", "payee_vpa": None, "payee_name": None, "amount": None, "note": None}

    if kind == "url":
        try:
            r = sms_phishing.predict(p["raw"])
            score, reasons = int(r.get("fraud_score", 0)), list(r.get("red_flags", []))
        except Exception:
            reasons = ["Could not check the link live."]
        reasons.insert(0, "This QR/text is not a payment; it is a website link. Be careful before entering anything on that site.")
        out["headline"] = "This is a website link"
    elif kind == "other":
        out["headline"] = "No UPI payment or link found in this"
        reasons = ["This QR contains no UPI payment. If someone is telling you to use it to 'receive money', be careful."]
        out["raw_preview"] = p["raw"][:80]
    else:
        q = p["q"]
        vpa, name, note = q.get("pa", ""), q.get("pn", ""), q.get("tn", "")
        amt = _amount(q.get("am"))
        out.update({"payee_vpa": vpa or None, "payee_name": name or None, "amount": amt, "note": note or None})
        if kind == "mandate":
            score += 60
            out["headline"] = "This is an AutoPay MANDATE: permission for repeated deductions"
            reasons.append("If you approve, money can be deducted from your account repeatedly. Never approve an unknown QR/link.")
        else:
            score += 25
            out["headline"] = (f"Rs {amt:,.0f} will be SENT from your account through this QR/link, not received"
                               if amt else "You will SEND money to someone through this QR/link, not receive it")
            reasons.append("A UPI QR / payment link is always for sending money. You never need to scan a QR or enter a UPI PIN to receive money.")
        if expecting_to_receive:
            score += 60
            reasons.append("You were told you will RECEIVE money, but this is a payment link/QR (money will be SENT). This is a classic scam method.")
        if amt and amt >= 10000:
            score += 20; reasons.append(f"Bada amount (Rs {amt:,.0f}).")
        elif amt and amt >= 1000:
            score += 10
        blob = f"{vpa} {name} {note}".lower()
        hit = [w for w in SCAM_WORDS if w in blob]
        if hit:
            score += 25
            reasons.append("The payee name/note contains scam-like words: " + ", ".join(hit[:3]) + ".")
        if not VPA_RE.match(vpa or ""):
            score += 20; reasons.append("Payee ka UPI ID (VPA) missing ya galat format ka hai.")

    score = min(score, 100)
    level = "HIGH" if score >= 55 else "MEDIUM" if score >= 30 else "LOW"
    advice = {
        "HIGH": "Do not approve/pay. Do not share your UPI PIN with anyone. If money is already lost, call 1930 immediately.",
        "MEDIUM": "Wait. First ask someone you trust, and verify the payee through your own source.",
        "LOW": "No major red flag found, but this is not proof of safety. Pay only if you yourself want to pay that person.",
    }[level]
    out.update({"risk_level": level, "risk_score": score, "reasons": reasons, "advice": advice})
    return out


def decode_qr(data: bytes):
    """Return QR text from image bytes, or None. Tries a few variants because phone photos are messy."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    if max(h, w) > 1600:
        s = 1600 / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    variants = [img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)]
    if max(img.shape[:2]) < 900:
        variants.append(cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    det = cv2.QRCodeDetector()
    for v in variants:
        try:
            val, _, _ = det.detectAndDecode(v)
        except cv2.error:
            continue
        if val:
            return val
    return None
