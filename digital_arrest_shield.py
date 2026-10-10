"""
digital_arrest_shield.py — Digital Arrest Shield
Goal: STOP the scam before money leaves the victim's account.

Why this module exists: the rPPG detector only catches fake faces (deepfake /
photo / replay). Most real digital-arrest calls use a REAL person in uniform,
so we also listen to WHAT is being said and guard the payment step.

Three layers:
  1. Scam-script detector  — matches the tell-tale phases of a digital-arrest
     call (authority claim, accusation, arrest threat, isolation, money demand,
     urgency) in English / romanized Hindi / Hindi transcript text.
  2. Payment guard         — explainable risk rules on a transfer made while
     a suspicious call is going on (new payee + big amount + long video call).
  3. Family alert          — ready-to-send message to a trusted contact,
     breaking the "isolation" that the scam depends on.
"""
import re
from urllib.parse import quote

# Each category = one "phase" of a typical digital-arrest call.
CATEGORIES = {
    "authority_claim": {
        "weight": 15,
        "label": "Claims to be police / CBI / ED / TRAI / customs",
        "phrases": ["cbi", "enforcement directorate", "narcotics", "cyber crime branch",
                    "cyber cell", "police", "trai", "customs", "supreme court",
                    "inspector", "mumbai police", "cyber department", "verification wing", "ats pune", "anti terrorist squad", "anti-terrorist squad",
                    "nia officer", "nia investigation", "nia ki", "एटीएस", "एनआईए", "सुप्रीम कोर्ट", "nodal officer",
                    "fraud team", "पुलिस", "सीबीआई", "कस्टम"],
    },
    "accusation": {
        "weight": 15,
        "label": "Accuses you of a crime (drugs / money laundering / parcel / identity misuse)",
        "phrases": ["money laundering", "drugs", "drug", "parcel", "fedex", "illegal",
                    "aadhaar misuse", "aadhar misuse", "identity theft", "hawala",
                    "terror", "terrorist", "terrorism", "आतंकी", "आतंकवादी", "aatank", "fir registered", "case registered", "sim card misuse",
                    "मनी लॉन्ड्रिंग", "पार्सल", "ड्रग"],
    },
    "arrest_threat": {
        "weight": 25,
        "label": "Threatens arrest / 'digital arrest' / warrant",
        "phrases": ["digital arrest", "डिजिटल अरेस्ट", "अरेस्ट वारंट", "arrest warrant", "under arrest", "will be arrested",
                    "arrest you", "warrant", "arrest", "गिरफ्तार", "वारंट"],
    },
    "isolation": {
        "weight": 25,
        "label": "Forces isolation — 'don't tell anyone / don't disconnect the call'",
        "phrases": ["do not tell anyone", "don't tell anyone", "dont tell anyone",
                    "do not disconnect", "don't disconnect", "dont disconnect",
                    "stay on the call", "stay on video", "keep the camera on", "stay connected",
                    "keep this between us", "keep this matter between us", "between us", "discreet",
                    "do not inform", "don't inform", "no need to tell", "no need to inform",
                    "baat apne tak", "apne tak hi rakh", "dusron se baat mat", "mat bolna",
                    "batane ki zarurat nahi", "ghar walon ko pareshan",
                    "national security", "confidential case", "secret",
                    "kisi ko mat batana", "kisi ko na batana", "kisi ko nahi batana",
                    "call cut mat", "call mat kaatna", "video call on rakho",
                    "किसी को मत बताना", "किसी को न बताएं", "फोन मत काटना", "कॉल मत काटना"],
    },
    "money_demand": {
        "weight": 25,
        "label": "Demands money transfer — 'verify account / security deposit / safe account'",
        "phrases": ["transfer the money", "transfer money", "security deposit", "verify your account",
                    "verification amount", "rbi account", "safe account", "clear your name",
                    "pay the fine", "pay fine", "settlement amount", "bail amount",
                    "send money", "fd tod", "fd todkar", "fd break", "एफडी तोड़", "एफडी तोड", "send the refundable", "refundable amount", "shift the funds", "move your money",
                    "move the money", "holding account", "nodal account", "secure account", "secure khate",
                    "transfer the amount", "amount transfer", "amount bhej", "paise bhej", "paisa bhej",
                    "paise daal", "paisa daal", "wapas mil jayenge", "जांच के बाद वापस", "वापस मिल जाएंगे", "lauta denge", "paisa bhejo", "paise bhejo", "paisa transfer", "paise transfer",
                    "पैसे ट्रांसफर", "पैसे भेजो", "जमानत राशि"],
    },
    "trust_building": {
        "weight": 10,
        "label": "Builds false trust — 'don't worry / I am here to help / for your safety'",
        "phrases": ["for your safety", "for your own safety", "to protect you", "to protect your",
                    "i want to help", "i only want to help", "here to help", "trust me",
                    "don't worry", "do not worry", "no need to panic", "don't panic",
                    "everything is under control", "just a formality", "we will help", "hum help karenge",
                    "aapki madad", "madad karna chahta", "tension mat", "ghabrao mat", "ghabrana mat",
                    "chinta mat", "चिंता मत", "आपकी मदद"],
    },
    "urgency": {
        "weight": 10,
        "label": "Creates urgency / panic",
        "phrases": ["immediately", "right now", "within one hour", "within 1 hour",
                    "last chance", "urgent", "abhi ke abhi", "turant", "अभी", "तुरंत"],
    },
}

POLITENESS = ["sir", "madam", "ma'am", "please", "kindly", "respected", "namaste", "good morning",
              "good afternoon", "thank you", "beta", "ji ", "dhanyavaad", "aap ", "request"]
# Talk ABOUT scams (news, advice, teaching) is not a live scam call.
AWARENESS_CUES = ["scams are", "scam is", "fraud bahut", "fraud badh", "scams badh", "awareness", "beware",
                  "in the news", "news me", "news said", "they said", "teacher said", "said that bank",
                  "never ask", "never asks", "hang up", "ne kaha ki koi", "police ne kaha", "police says"]

AWARENESS = ("No police, CBI or ED officer arrests anyone over a video or phone call, and none ever asks for money. "
             "'Digital arrest' does not exist in Indian law.")
ACTION_STEPS = [
    "Hang up right away. Disconnecting the call cannot get you arrested.",
    "Do not transfer any money and do not share your OTP, PIN or Aadhaar.",
    "Tell a trusted family member right now.",
    "Call 1930 (National Cyber Helpline) or report at cybercrime.gov.in.",
]


def _find_matches(text: str, phrases: list) -> list:
    t = text.lower()
    found = []
    for p in phrases:
        # plain substring match (works for Devanagari too); avoid duplicates
        if p in t and not any(p in f for f in found):
            found.append(p)
    return found


def analyze_transcript(text: str) -> dict:
    """Score a (running) call transcript for digital-arrest scam patterns."""
    t = (text or "").strip()
    if not t:
        return {"risk_level": "NONE", "risk_score": 0, "matched_categories": [],
                "highlights": [], "message": "No speech to analyze yet."}

    matched = []
    highlights = []
    score = 0
    hit = set()
    for key, cat in CATEGORIES.items():
        found = _find_matches(t, cat["phrases"])
        if found:
            hit.add(key)
            score += cat["weight"]
            matched.append({"category": key, "label": cat["label"], "phrases": found})
            highlights.extend(found)

    score = min(score, 100)

    # Tone-independent behavioural rules: what is ASKED matters, not how nicely it is said.
    others = hit - {"money_demand", "trust_building"}
    strong_combo = (("isolation" in hit and "money_demand" in hit) or
                    ("arrest_threat" in hit and ("isolation" in hit or "money_demand" in hit)) or
                    ("money_demand" in hit and len(others | ({"trust_building"} & hit)) >= 2))

    if score >= 55 or strong_combo:
        level = "HIGH"
        score = max(score, 80)
    elif score >= 30 or ("money_demand" in hit and (others or "trust_building" in hit)):
        level = "MEDIUM"
        score = max(score, 40)
    elif score > 0:
        level = "LOW"
    else:
        level = "NONE"

    # Discussion ABOUT scams (news / advice) with no live pressure -> do not alarm.
    discussion = False
    low = t.lower()
    if level in ("HIGH", "MEDIUM") and "urgency" not in hit and any(c in low for c in AWARENESS_CUES):
        level, score, discussion = "LOW", min(score, 25), True

    politeness = [w.strip() for w in POLITENESS if w in low + " "]

    result = {
        "risk_level": level,
        "risk_score": score,
        "matched_categories": matched,
        "highlights": sorted(set(highlights), key=len, reverse=True),
    }
    result["politeness_markers"] = politeness
    result["discussion_about_scams"] = discussion
    if level in ("HIGH", "MEDIUM"):
        if politeness or "trust_building" in hit:
            result["tone_note"] = ("Caller sounds polite / friendly. Scammers use this to build trust. "
                                   "Risk is judged by WHAT is asked (money, secrecy, staying on call), not by tone.")
        result["awareness"] = AWARENESS
        result["action_steps"] = ACTION_STEPS
        result["message"] = ("DIGITAL ARREST SCAM LIKELY — end the call now." if level == "HIGH"
                             else "Suspicious call pattern — stay alert, do not send money.")
    elif discussion:
        result["message"] = "Looks like a discussion ABOUT scams, not a live scam call."
    else:
        result["message"] = "No strong scam pattern detected so far."
    return result


def payment_guard(amount: float, new_beneficiary: bool, in_video_call: bool,
                  call_minutes: float = 0, typical_max: float = 10000,
                  shield_risk: str = "NONE") -> dict:
    """Explainable rule-based risk check for a transfer made during a call."""
    amount = float(amount or 0)
    typical_max = float(typical_max or 10000)
    call_minutes = float(call_minutes or 0)
    score = 0
    reasons = []

    if amount > 5 * typical_max:
        score += 30
        reasons.append(f"Amount is more than 5x your usual maximum (Rs.{typical_max:,.0f})")
    if amount >= 50000:
        score += 10
        reasons.append("High-value transfer (Rs.50,000 or more)")
    if new_beneficiary:
        score += 20
        reasons.append("Paying a brand-new beneficiary you never paid before")
    if in_video_call:
        score += 25
        reasons.append("Transfer being made while on an active video / phone call")
    if call_minutes >= 30:
        score += 10
        reasons.append(f"Call has been running for {call_minutes:.0f}+ minutes (typical of digital-arrest isolation)")
    if shield_risk == "HIGH":
        score += 40
        reasons.append("Live call analysis flagged this call as a DIGITAL ARREST SCAM")
    elif shield_risk == "MEDIUM":
        score += 15
        reasons.append("Live call analysis found suspicious scam phrases")

    score = min(score, 100)
    if score >= 60:
        action = "HOLD"
        message = ("Transaction PAUSED for a cooling-off period. Talk to a trusted family member "
                   "and verify with 1930 before sending anything.")
    elif score >= 35:
        action = "WARN"
        message = "Risky transfer. Confirm the receiver through a separate, official channel first."
    else:
        action = "ALLOW"
        message = "No strong fraud signals for this transfer."

    return {"action": action, "risk_score": score, "reasons": reasons, "message": message}


def family_alert(contact_name: str, contact_phone: str, user_name: str = "Me") -> dict:
    """Build a WhatsApp click-to-chat alert for a trusted contact."""
    name = (contact_name or "Family").strip() or "Family"
    text = (f"ALERT ({user_name}): I am getting a 'digital arrest' scam call right now "
            f"(fake police/CBI). If I say I want to transfer money, do NOT let me. "
            f"Please call me immediately. - DeepVerif.AI")
    digits = re.sub(r"\D", "", contact_phone or "")
    if len(digits) == 10:
        digits = "91" + digits
    link = f"https://wa.me/{digits}?text={quote(text)}" if digits else None
    return {"contact": name, "message": text, "whatsapp_link": link}
