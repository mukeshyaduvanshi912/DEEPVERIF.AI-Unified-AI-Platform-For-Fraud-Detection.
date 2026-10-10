"""
evaluate_shield.py — measure the Digital Arrest Shield on a labelled transcript set.

A call is predicted "scam" when risk_level is MEDIUM or HIGH.
Usage:  python evaluation/evaluate_shield.py
Writes: evaluation/results/shield_report.md  (+ prints it)
"""
import csv, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import digital_arrest_shield as shield

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "shield_testset.csv")
OUT = os.path.join(HERE, "results", "shield_report.md")


def run(tag=""):
    with open(DATA, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tp = fp = tn = fn = 0
    misses, by_style = [], {}
    for r in rows:
        res = shield.analyze_transcript(r["text"])
        pred = "scam" if res["risk_level"] in ("MEDIUM", "HIGH") else "benign"
        gold = r["label"]
        ok = pred == gold
        s = by_style.setdefault(r["style"], [0, 0]); s[0] += ok; s[1] += 1
        if gold == "scam" and pred == "scam": tp += 1
        elif gold == "scam": fn += 1; misses.append(("MISSED SCAM", res["risk_level"], r["text"][:90]))
        elif pred == "scam": fp += 1; misses.append(("FALSE ALARM", res["risk_level"], r["text"][:90]))
        else: tn += 1
    n = tp + fp + tn + fn
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    lines = [f"# Digital Arrest Shield — evaluation {tag}", "",
             f"Test set: {n} hand-written transcripts ({tp+fn} scam, {tn+fp} benign) — `evaluation/shield_testset.csv`", "",
             "| | Predicted scam | Predicted benign |", "|---|---|---|",
             f"| **Actual scam** | {tp} (TP) | {fn} (FN) |", f"| **Actual benign** | {fp} (FP) | {tn} (TN) |", "",
             f"Accuracy {(tp+tn)/n:.1%} · Precision {prec:.1%} · Recall {rec:.1%} · F1 {f1:.1%}", "",
             "## Per-style accuracy", "", "| Style | Correct / Total |", "|---|---|"]
    for k, (a, b) in sorted(by_style.items()):
        lines.append(f"| {k} | {a}/{b} |")
    if misses:
        lines += ["", "## Errors", ""] + [f"- {m[0]} ({m[1]}): {m[2]}..." for m in misses]
    lines += ["", "> Caveat: this set was written by the project authors, so it is optimistic. "
              "Before the final viva, add real reported call transcripts (from news/NCRP awareness material) "
              "written by a teammate who has NOT seen the rules, and re-run."]
    return "\n".join(lines), dict(acc=(tp+tn)/n, prec=prec, rec=rec, f1=f1, fn=fn, fp=fp)


if __name__ == "__main__":
    text, m = run(sys.argv[1] if len(sys.argv) > 1 else "")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(text)
    print(text)
