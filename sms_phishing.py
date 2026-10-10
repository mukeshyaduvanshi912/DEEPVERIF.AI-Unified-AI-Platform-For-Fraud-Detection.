"""
sms_phishing.py — SMS Phishing (Smishing) Detector
Two-layer detection:
  1. RULE-BASED heuristics (transparent, explainable) — the kind of red
     flags a security-aware human would look for: shortened/suspicious
     links, urgency language, fake govt/bank impersonation phrases,
     requests for OTP/PIN/bank details, mismatched sender patterns.
  2. ML LAYER — TF-IDF + Logistic Regression trained on a labelled
     seed dataset of realistic phishing vs legitimate SMS text
     (data/sms_seed_dataset.csv, written by this module). This is a
     genuine trainable classifier — swap the seed CSV for a larger
     real-world labelled dataset any time to improve accuracy.
  3. SOURCE / SENDER analysis — checks whether the message's claimed
     identity (e.g. "SBI", "Income Tax Dept") matches the domain any
     link in it actually points to, and looks for a trailing sender
     signature.
  4. LINK HISTORY — every link found in the text is expanded: shortener
     redirect chain (if reachable), final destination domain, TLD
     reputation, IP-literal check, and (if the 'whois' package + internet
     are available) domain registration age — a brand-new domain is one
     of the strongest phishing signals there is.
"""
import os
import re
import csv
import joblib
from datetime import datetime, timezone
from urllib.parse import urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

try:
    import requests
    REQUESTS_SUPPORT = True
except ImportError:
    REQUESTS_SUPPORT = False

try:
    import whois as pywhois
    WHOIS_SUPPORT = True
except ImportError:
    WHOIS_SUPPORT = False

BASE_DIR = os.path.dirname(__file__)
DATA_CSV = os.path.join(BASE_DIR, "models", "sms_seed_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "sms_model.joblib")

SHORTENER_DOMAINS = ["bit.ly", "tinyurl", "t.co", "cutt.ly", "is.gd", "rb.gy", "shorturl", "tiny.cc"]
URGENCY_WORDS = [
    "urgent", "immediately", "within 24 hours", "within 72 hours", "act now",
    "final notice", "account suspended", "account blocked", "verify now",
    "expire", "expires today", "last warning", "legal action", "penalty",
    "prosecution", "arrest", "block your", "suspend your",
]
SENSITIVE_ASK_WORDS = [
    "share your otp", "share otp", "enter your otp", "enter otp",
    "share your pin", "enter your pin", "share cvv", "enter cvv",
    "share your password", "bank details", "kyc update",
    "click here", "click link", "verify your account", "update your kyc",
    "confirm your identity", "share your bank", "enter your bank",
]
IMPERSONATION_WORDS = [
    "income tax", "gst", "rbi", "sbi", "customs", "courier", "parcel held",
    "electricity board", "kyc", "bank of india", "refund", "lottery", "prize",
    "cashback",
]

# Suspicious / commonly-abused free or cheap TLDs seen a lot in throwaway
# phishing infrastructure.
SUSPICIOUS_TLDS = [
    ".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".work",
    ".loan", ".win", ".bid", ".men", ".party", ".review", ".rest", ".icu",
]

# keyword -> (display name, an official domain fragment that a genuine
# message from that org would actually link to)
CLAIMED_BRAND_DOMAINS = {
    "income tax": ("Income Tax Department", "incometax.gov.in"),
    "gst": ("GST portal", "gst.gov.in"),
    "rbi": ("Reserve Bank of India", "rbi.org.in"),
    "sbi": ("State Bank of India", "sbi.co.in"),
    "bank of india": ("Bank of India", "bankofindia.co.in"),
    "customs": ("Indian Customs", "cbic.gov.in"),
}

# Real SMS links are very often written bare, with no "http://" or "www."
# prefix at all (e.g. "bit.ly/kyc-updt"), so the extractor has to catch
# those too — but generically enough to not also swallow things like
# "Rs.49" or "Rs.1200". We match: full http(s)/www URLs, known shortener
# domains (with or without a path), and bare domain.TLD text using only a
# safe, deliberately non-numeric list of common TLDs.
_SHORTENER_FULL_DOMAINS = ["bit\\.ly", "tinyurl\\.com", "t\\.co", "cutt\\.ly",
                           "is\\.gd", "rb\\.gy", "shorturl\\.at", "tiny\\.cc"]
_GENERIC_TLDS = ["com", "net", "org", "io", "co", "me", "to", "info", "online",
                  "site", "xyz", "top", "click", "tk", "ml", "ga", "cf", "gq",
                  "win", "bid", "men", "party", "review", "rest", "icu",
                  "gov.in", "co.in", "org.in", "nic.in", "in"]

URL_REGEX = re.compile(
    r"(?:https?://[^\s]+)"
    r"|(?:www\.[^\s]+)"
    r"|(?:(?:" + "|".join(_SHORTENER_FULL_DOMAINS) + r")(?:/[^\s]*)?)"
    r"|(?:\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:" + "|".join(_GENERIC_TLDS) + r")(?:/[^\s]*)?\b)",
    re.IGNORECASE,
)


def _seed_dataset():
    """Write a small, original, illustrative labelled dataset (1=phishing, 0=legit)."""
    rows = [
        # --- Phishing examples (label 1) ---
        ("Your a/c will be BLOCKED in 24 hrs. Update your KYC immediately: bit.ly/kyc-updt", 1),
        ("URGENT: Income Tax dept detected irregularity. Pay penalty now or face legal action. Link: tinyurl.com/taxpay", 1),
        ("Dear customer your parcel is held at customs. Pay Rs.49 clearance fee here: cutt.ly/parcel49", 1),
        ("Congratulations! You have won Rs.25,00,000 lottery. Share your bank details to claim now.", 1),
        ("Your SBI account has been suspended. Verify now to avoid permanent block: rb.gy/sbi-verify", 1),
        ("RBI ALERT: Your account KYC is expiring today. Click here to update or account will be blocked.", 1),
        ("Electricity bill unpaid, power will be disconnected tonight. Pay immediately: is.gd/ebillpay", 1),
        ("Your ATM card is blocked. Share OTP received to unblock immediately, else account closed.", 1),
        ("GST registration cancellation notice issued. Reply with PAN and OTP to avoid penalty.", 1),
        ("You have a refund of Rs.4500 pending. Click link and enter bank pin to receive: bit.ly/refund99", 1),
        ("FINAL WARNING: legal action will be taken against you within 72 hours unless you pay via link below.", 1),
        ("Your courier could not be delivered. Confirm your identity and pay Rs.20 redelivery fee: t.co/xyz1", 1),
        ("Dear user your Aadhaar linked bank account will be deactivated today. Verify: shorturl.at/kyc2", 1),
        ("Cashback of Rs.1000 credited! Click to claim before it expires today: bit.ly/cashback1", 1),
        ("Your SIM card will be blocked in 2 hours due to KYC mismatch. Update PIN here to continue service.", 1),
        # --- Legitimate examples (label 0) ---
        ("Your OTP for login is 482910. Do not share this with anyone. -YourBank", 0),
        ("Hi, are we still meeting for lunch tomorrow at 1pm?", 0),
        ("Your Amazon order #4521 has been shipped and will arrive by Friday.", 0),
        ("Reminder: your electricity bill of Rs.1200 is due on 15th. Pay via official app or website.", 0),
        ("Your exam hall ticket has been generated. Download it from the college portal.", 0),
        ("Meeting rescheduled to 4pm today, conference room B.", 0),
        ("Your recharge of Rs.199 was successful. Balance: Rs.35.20", 0),
        ("Thank you for shopping with us! Your invoice has been emailed to you.", 0),
        ("Doctor's appointment confirmed for Monday 10am at City Clinic.", 0),
        ("Your monthly bank statement is now available in net banking.", 0),
        ("Happy Birthday! Wishing you a wonderful year ahead.", 0),
        ("Your Swiggy order is out for delivery, arriving in 15 minutes.", 0),
        ("Project submission deadline extended to next Monday, per faculty notice.", 0),
        ("Your salary has been credited to your account.", 0),
        ("Electricity meter reading has been recorded for this month, no action needed.", 0),
    ]
    os.makedirs(os.path.dirname(DATA_CSV), exist_ok=True)
    with open(DATA_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(rows)
    return rows


def train_model():
    if not os.path.exists(DATA_CSV):
        rows = _seed_dataset()
    else:
        with open(DATA_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [(r["text"], int(r["label"])) for r in reader]

    texts = [t for t, _ in rows]
    labels = [l for _, l in rows]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipeline.fit(texts, labels)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    return pipeline


def _load_model():
    if not os.path.exists(MODEL_PATH):
        return train_model()
    return joblib.load(MODEL_PATH)


_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_model()
    return _MODEL


def _rule_based_flags(text: str) -> list:
    t = text.lower()
    flags = []
    if any(d in t for d in SHORTENER_DOMAINS):
        flags.append("Contains a shortened/obfuscated link (hides real destination)")
    if any(w in t for w in URGENCY_WORDS):
        flags.append("Uses urgency / panic-pressure language")
    if any(w in t for w in SENSITIVE_ASK_WORDS):
        flags.append("Asks you to click a link or share sensitive info (OTP/PIN/KYC)")
    if any(w in t for w in IMPERSONATION_WORDS):
        flags.append("Impersonates a bank/govt/courier/authority brand")
    if re.search(r"https?://[^\s]+", t) and not re.search(r"https?://(www\.)?(gov\.in|nic\.in)", t):
        flags.append("Contains a link to a non-official-looking domain")
    return flags


# --------------------------------------------------------------------------
# Link history / provenance
# --------------------------------------------------------------------------

def _extract_urls(text: str) -> list:
    found = URL_REGEX.findall(text)
    # de-duplicate, preserve order
    seen = set()
    return [u.rstrip(".,)>") for u in found if not (u in seen or seen.add(u))]


def _normalize_url(raw_url: str) -> str:
    return raw_url if raw_url.lower().startswith(("http://", "https://")) else "http://" + raw_url


def _domain_reputation(domain: str) -> dict:
    return {
        "is_shortener": any(d in domain for d in SHORTENER_DOMAINS),
        "suspicious_tld": any(domain.endswith(t) for t in SUSPICIOUS_TLDS),
        "is_ip_literal": bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain)),
    }


def _follow_redirects(url: str, timeout: float = 4.0) -> dict:
    """Best-effort: actually follow the link to see where it really goes.
    Fails gracefully (no crash) if there's no internet access, the host is
    unreachable, or the 'requests' package isn't installed."""
    if not REQUESTS_SUPPORT:
        return {"resolved": False, "error": "'requests' package not installed"}
    try:
        resp = requests.get(url, allow_redirects=True, timeout=timeout, stream=True,
                             headers={"User-Agent": "Mozilla/5.0 (DeepVerif.AI link-checker)"})
        chain = [h.url for h in resp.history] + [resp.url]
        status = resp.status_code
        resp.close()
        return {"resolved": True, "chain": chain, "final_url": chain[-1], "final_status": status}
    except Exception as e:
        return {"resolved": False, "error": str(e)}


def _whois_lookup(domain: str) -> dict:
    if not WHOIS_SUPPORT:
        return {"available": False, "reason": "'python-whois' package not installed"}
    try:
        w = pywhois.whois(domain)
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        age_days = None
        if isinstance(creation_date, datetime):
            cd = creation_date if creation_date.tzinfo else creation_date.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - cd).days
        registrar = w.registrar if isinstance(w.registrar, str) else (w.registrar[0] if w.registrar else None)
        return {
            "available": True,
            "registrar": registrar,
            "creation_date": str(creation_date) if creation_date else None,
            "domain_age_days": age_days,
        }
    except Exception as e:
        return {"available": False, "reason": f"WHOIS lookup failed: {e}"}


def analyze_link(raw_url: str) -> dict:
    """Builds the full 'history' of a single link: shortener redirect
    chain, final destination, TLD/IP reputation, and domain age."""
    url = _normalize_url(raw_url)
    domain = (urlparse(url).netloc or "").split(":")[0].lower()
    repu = _domain_reputation(domain)

    redirect = _follow_redirects(url) if (repu["is_shortener"] or True) else {"resolved": False}
    final_domain = domain
    if redirect.get("resolved") and redirect.get("final_url"):
        final_domain = (urlparse(redirect["final_url"]).netloc or domain).split(":")[0].lower()

    whois_target = final_domain or domain
    whois_info = _whois_lookup(whois_target) if whois_target else {"available": False}

    notes = []
    risk = 0.0

    if repu["is_shortener"]:
        notes.append(f"'{domain}' is a link-shortening service — it hides the real destination until followed")
        risk += 0.15
        if redirect.get("resolved"):
            notes.append(f"Followed the redirect live: it goes to '{redirect['final_url']}'")
        else:
            notes.append(f"Could not follow the redirect ({redirect.get('error', 'unknown error')}) — treat the destination as unverified")
            risk += 0.10
    elif redirect.get("resolved") and redirect.get("chain", []) and len(redirect["chain"]) > 1:
        notes.append(f"Link redirects through {len(redirect['chain']) - 1} hop(s) before reaching '{redirect['final_url']}'")
        risk += 0.10

    if redirect.get("resolved") and redirect.get("final_status") and redirect["final_status"] >= 400:
        notes.append(f"The destination returned HTTP {redirect['final_status']} — the link may be dead, blocked, or already taken down")

    if repu["is_ip_literal"]:
        notes.append("Link points to a raw IP address instead of a domain name — a strong phishing indicator")
        risk += 0.25
    if repu["suspicious_tld"]:
        tld = "." + domain.rsplit(".", 1)[-1]
        notes.append(f"Domain uses TLD '{tld}', commonly abused for cheap/throwaway phishing sites")
        risk += 0.15

    if whois_info.get("available"):
        age = whois_info.get("domain_age_days")
        if age is not None:
            if age < 30:
                notes.append(f"Domain '{whois_target}' was registered only {age} day(s) ago — brand-new domains are one of the strongest phishing signals")
                risk += 0.30
            elif age < 180:
                notes.append(f"Domain '{whois_target}' is only ~{age} days old")
                risk += 0.15
            else:
                notes.append(f"Domain '{whois_target}' is ~{age} days old ({whois_info.get('creation_date')}) — an established registration")
        if whois_info.get("registrar"):
            notes.append(f"Registrar on record: {whois_info['registrar']}")
    else:
        notes.append(f"Domain age could not be verified ({whois_info.get('reason', 'WHOIS unavailable')})")

    return {
        "original_url": raw_url,
        "domain": domain,
        "is_shortener": repu["is_shortener"],
        "is_ip_literal": repu["is_ip_literal"],
        "suspicious_tld": repu["suspicious_tld"],
        "resolved_live": redirect.get("resolved", False),
        "redirect_chain": redirect.get("chain", []),
        "final_url": redirect.get("final_url"),
        "final_domain": final_domain,
        "whois": whois_info,
        "notes": notes,
        "risk_score_contribution": round(min(risk, 0.6), 3),
    }


# --------------------------------------------------------------------------
# Claimed-sender / source analysis
# --------------------------------------------------------------------------

def analyze_source(text: str, link_reports: list) -> dict:
    t = text.lower()
    claimed_brand = None
    official_domain = None
    for kw, (name, domain) in CLAIMED_BRAND_DOMAINS.items():
        if kw in t:
            claimed_brand = name
            official_domain = domain
            break

    mismatch_notes = []
    if claimed_brand:
        for link in link_reports:
            target_domain = link.get("final_domain") or link.get("domain") or ""
            if official_domain not in target_domain:
                mismatch_notes.append(
                    f"Message claims to be from {claimed_brand}, but the link goes to "
                    f"'{target_domain}', not the official '{official_domain}' domain"
                )

    sig_match = re.search(r"-\s*([A-Za-z][A-Za-z0-9]{2,15})\s*$", text.strip())
    sender_signature = sig_match.group(1) if sig_match else None

    if claimed_brand and mismatch_notes:
        verdict = f"Claims to be from {claimed_brand}, but the linked domain does not match — likely SPOOFED"
        confidence = "HIGH"
    elif claimed_brand:
        verdict = f"Claims to be from {claimed_brand} (no link to cross-check, or domain matches)"
        confidence = "MEDIUM"
    elif sender_signature:
        verdict = f"No recognized official brand claimed; message signs off as '{sender_signature}' (unverifiable from text alone)"
        confidence = "LOW"
    else:
        verdict = "No sender identity/signature could be determined from the message text"
        confidence = "LOW"

    return {
        "claimed_sender": claimed_brand,
        "official_domain_expected": official_domain,
        "sender_signature_found": sender_signature,
        "mismatch_notes": mismatch_notes,
        "source_verdict": verdict,
        "confidence": confidence,
    }


# --------------------------------------------------------------------------
# Report builder
# --------------------------------------------------------------------------

def _build_report_text(verdict: str, fake_pct: float, real_pct: float, ml_probability: float,
                        red_flags: list, source_analysis: dict, link_reports: list) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("DeepVerif.AI — SMS Phishing (Smishing) Report")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"VERDICT: {verdict}")
    lines.append(f"Fake likelihood: {fake_pct}%   |   Real likelihood: {real_pct}%")
    lines.append(f"(ML model component: {ml_probability}% probability of phishing)")
    lines.append("")
    if red_flags:
        lines.append("-- Red flags --")
        for f in red_flags:
            lines.append(f"  - {f}")
        lines.append("")
    lines.append("-- Claimed source / sender --")
    lines.append(f"  Verdict: {source_analysis['source_verdict']} (confidence: {source_analysis['confidence']})")
    if source_analysis["sender_signature_found"]:
        lines.append(f"  Sign-off found in text: '-{source_analysis['sender_signature_found']}'")
    for m in source_analysis["mismatch_notes"]:
        lines.append(f"  - {m}")
    lines.append("")
    if link_reports:
        lines.append("-- Link history --")
        for i, l in enumerate(link_reports, 1):
            lines.append(f"  [{i}] {l['original_url']}")
            if l["is_shortener"]:
                lines.append(f"      Shortener -> {'resolved live to ' + l['final_url'] if l['resolved_live'] else 'could not resolve'}")
            for n in l["notes"]:
                lines.append(f"      - {n}")
        lines.append("")
    lines.append("-- Honest limitations --")
    lines.append("  Live redirect-following and WHOIS lookups need internet access and the")
    lines.append("  'requests' / 'python-whois' packages; when unavailable this report says")
    lines.append("  so explicitly rather than guessing. Sender/source identity is inferred")
    lines.append("  from the message text only — a real investigation should also check the")
    lines.append("  actual originating number/sender ID via your telecom operator.")
    lines.append("=" * 60)
    return "\n".join(lines)


def predict(text: str) -> dict:
    model = _get_model()
    proba = float(model.predict_proba([text])[0][1])  # P(phishing)
    flags = _rule_based_flags(text)

    urls = _extract_urls(text)
    link_reports = [analyze_link(u) for u in urls]
    source_analysis = analyze_source(text, link_reports)

    rule_boost = min(0.10 * len(flags), 0.30)
    link_penalty = min(sum(l["risk_score_contribution"] for l in link_reports), 0.5)
    mismatch_penalty = 0.25 if source_analysis["mismatch_notes"] else 0.0

    fused_score = min(1.0, proba * 0.5 + rule_boost + link_penalty + mismatch_penalty)
    fraud_score = round(fused_score * 100, 1)
    real_percent = round(100.0 - fraud_score, 1)

    verdict = "PHISHING / SCAM SMS" if fraud_score >= 55 else (
        "SUSPICIOUS — REVIEW" if fraud_score >= 30 else "LIKELY SAFE"
    )

    report_text = _build_report_text(verdict, fraud_score, real_percent, round(proba * 100, 1),
                                      flags, source_analysis, link_reports)

    return {
        "verdict": verdict,
        "fraud_score": fraud_score,
        "fake_percent": fraud_score,
        "real_percent": real_percent,
        "ml_probability": round(proba * 100, 1),
        "red_flags": flags,
        "source_analysis": source_analysis,
        "link_analysis": link_reports,
        "report_text": report_text,
        "advice": (
            "Do not click any link or share OTP/PIN. Block the sender and report to "
            "sms.gov.in or call the 1930 National Cyber Helpline."
            if fraud_score >= 30 else
            "No major red flags detected — still avoid sharing OTP/PIN over SMS as a rule."
        ),
    }


if __name__ == "__main__":
    train_model()
    print("Model trained and saved to", MODEL_PATH)

