"""
data_exposure.py — "How did the scammer get my data?" awareness + safe exposure checks.

Honest scope: nobody can prove from a call WHO leaked a person's data. This module
(1) explains the usual leak routes, (2) gives concrete steps to find out what is exposed
and to lock it down, (3) optionally checks an e-mail against Have I Been Pwned.

Password checks are done in the BROWSER (static/app.js) with the HIBP k-anonymity API:
only the first 5 characters of a SHA-1 hash ever leave the device. The server never sees passwords.
"""
import os
import re
import requests

LEAK_ROUTES = [
    {"route": "Past data breaches", "detail": "Name, phone, e-mail, address from a breached app/site end up in criminal databases."},
    {"route": "KYC / ID photocopies", "detail": "Copies of Aadhaar/PAN given to shops, SIM sellers, hotels or loan agents are re-sold."},
    {"route": "Fake loan / job / reward apps", "detail": "Apps ask for contacts, SMS and gallery permissions and upload everything."},
    {"route": "Courier / delivery / e-commerce leaks", "detail": "Order and parcel data is used to make 'your parcel has drugs' calls sound real."},
    {"route": "Public social media", "detail": "Birthdate, workplace, family names and photos help scammers script a believable call."},
    {"route": "Insider / agent leaks", "detail": "Staff or agents at telecom, travel or finance intermediaries selling customer lists."},
    {"route": "Data brokers & Telegram/WhatsApp lead groups", "detail": "'Leads' (name + phone + city + what you bought) are sold in bulk."},
]

PROTECT_STEPS = [
    {"step": "Check mobile connections issued on your ID", "how": "Sanchar Saathi portal (DoT) -> 'Know your mobile connections'; report numbers you do not recognise."},
    {"step": "Lock your Aadhaar biometrics", "how": "mAadhaar app or myaadhaar.uidai.gov.in -> Lock/Unlock Biometrics. Use a masked Aadhaar copy when possible."},
    {"step": "Check your e-mail/password exposure", "how": "Use the password check on this tab (safe, private) and haveibeenpwned.com for your e-mail."},
    {"step": "Tighten social media privacy", "how": "Hide birthdate, phone, workplace and family tags; limit who can see your friends list."},
    {"step": "Review app permissions", "how": "Remove SMS / contacts / accessibility permissions from apps that do not need them; uninstall unknown loan apps."},
    {"step": "Report and freeze quickly if money was lost", "how": "Call 1930 (National Cyber Helpline) within the first hour and file at cybercrime.gov.in; tell your bank."},
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def awareness() -> dict:
    return {
        "headline": "Scammers rarely 'hack' you. They usually buy or collect your details and use them to sound real.",
        "honest_note": ("We cannot tell from a single call which company or person leaked your data. "
                        "What we CAN do is show likely routes and reduce what is exposed."),
        "leak_routes": LEAK_ROUTES,
        "protect_steps": PROTECT_STEPS,
    }


def email_breach_check(email: str) -> dict:
    """Optional: needs a (paid) HIBP API key in env HIBP_API_KEY. The e-mail is never stored or logged."""
    email = (email or "").strip()
    if not _EMAIL_RE.match(email):
        return {"status": "error", "message": "Enter a valid e-mail address."}
    key = os.environ.get("HIBP_API_KEY")
    if not key:
        return {"status": "not_configured",
                "message": ("E-mail breach lookup needs a Have I Been Pwned API key (set HIBP_API_KEY). "
                            "Meanwhile check your e-mail manually at haveibeenpwned.com.")}
    try:
        r = requests.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{requests.utils.quote(email)}",
                         params={"truncateResponse": "true"},
                         headers={"hibp-api-key": key, "user-agent": "DeepVerif-AI-student-project"}, timeout=6)
    except requests.RequestException:
        return {"status": "unavailable", "message": "Could not reach the breach service (offline?)."}
    if r.status_code == 404:
        return {"status": "ok", "breaches": 0, "message": "No known breaches for this e-mail."}
    if r.status_code == 200:
        names = [b.get("Name") for b in r.json()]
        return {"status": "ok", "breaches": len(names), "breach_names": names[:20],
                "message": f"Found in {len(names)} known breach(es). Change passwords and enable 2-factor login."}
    return {"status": "unavailable", "message": f"Breach service returned status {r.status_code}."}
