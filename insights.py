"""
insights.py — user feedback (thumbs up/down) + dashboard statistics from the audit chain.
Feedback stores NO message text: only tool, verdict, and the risk level/score shown.
demo=True returns clearly-labelled SAMPLE numbers for presentations and writes nothing.
"""
import json
import os
import time
from collections import Counter

import hashchain

FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "data", "feedback.jsonl")
TOOLS = ("sms", "upi", "number", "shield", "ai")
CHECK_EXCLUDE = ("number_reported", "ai_explain")


def record_feedback(tool: str, verdict: str, level: str = "", score=None) -> dict:
    if tool not in TOOLS or verdict not in ("correct", "wrong"):
        return {"error": "Invalid feedback."}
    rec = {"ts": int(time.time()), "tool": tool, "verdict": verdict, "level": str(level)[:12],
           "score": score if isinstance(score, (int, float)) else None}
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return {"status": "saved"}


def _feedback_summary() -> dict:
    c = Counter()
    try:
        with open(FEEDBACK_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    c[json.loads(line)["verdict"]] += 1
                except (ValueError, KeyError):
                    pass
    except FileNotFoundError:
        pass
    total = c["correct"] + c["wrong"]
    return {"correct": c["correct"], "wrong": c["wrong"],
            "accuracy": round(100 * c["correct"] / total, 1) if total else None}


def _demo() -> dict:
    return {"demo": True, "total_checks": 1284, "high_risk_alerts": 412, "numbers_reported": 96,
            "by_tool": [{"name": "sms_phishing", "count": 604}, {"name": "digital_arrest_shield_script", "count": 281},
                        {"name": "number_check", "count": 214}, {"name": "upi_check", "count": 123},
                        {"name": "document_forensics", "count": 62}],
            "scam_categories": [{"name": "authority_impersonation", "count": 174}, {"name": "secrecy_isolation", "count": 131},
                                {"name": "money_transfer", "count": 118}, {"name": "arrest_threat", "count": 97},
                                {"name": "urgency", "count": 76}],
            "last_7_days": [{"day": d, "count": c} for d, c in
                            zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], [120, 164, 143, 201, 188, 260, 208])],
            "feedback": {"correct": 318, "wrong": 27, "accuracy": 92.2}}


def stats(demo: bool = False) -> dict:
    if demo:
        return _demo()
    by_module, cats, per_day = Counter(), Counter(), Counter()
    high = reported = 0
    for rec in hashchain.get_all_logs(limit=10 ** 9):
        e = rec["entry"]; m = e["module"]; r = e.get("result", {})
        by_module[m] += 1
        per_day[time.strftime("%Y-%m-%d", time.localtime(e["timestamp"]))] += 1
        if r.get("risk_level") == "HIGH" or (m == "sms_phishing" and (r.get("fraud_score") or 0) >= 55):
            high += 1
        if m == "digital_arrest_shield_script":
            cats.update(r.get("categories", []))
        if m == "number_reported":
            reported += 1
    days = [time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400 * i)) for i in range(6, -1, -1)]
    return {"demo": False,
            "total_checks": sum(v for k, v in by_module.items() if k not in CHECK_EXCLUDE),
            "high_risk_alerts": high, "numbers_reported": reported,
            "by_tool": [{"name": k, "count": v} for k, v in by_module.most_common() if k not in CHECK_EXCLUDE],
            "scam_categories": [{"name": k, "count": v} for k, v in cats.most_common(6)],
            "last_7_days": [{"day": d[5:], "count": per_day.get(d, 0)} for d in days],
            "feedback": _feedback_summary()}
