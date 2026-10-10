"""
evaluate_sms.py — honest accuracy numbers for the SMS phishing module.

Repeated stratified 5-fold cross-validation (never tests on training rows):
  A) ML only (TF-IDF + Logistic Regression)
  B) ML + rule flags (same fusion as sms_phishing.predict, WITHOUT live link lookups so it runs offline)
Usage:  python evaluation/evaluate_sms.py
Writes: evaluation/results/sms_report.md
"""
import csv, os, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import sms_phishing as sp

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "results", "sms_report.md")


def load():
    with open(sp.DATA_CSV, encoding="utf-8") as f:
        rows = [(r["text"], int(r["label"])) for r in csv.DictReader(f)]
    return np.array([r[0] for r in rows], dtype=object), np.array([r[1] for r in rows])


def fused_pred(proba, texts):
    out = []
    for p, t in zip(proba, texts):
        boost = min(0.10 * len(sp._rule_based_flags(t)), 0.30)
        out.append(1 if min(1.0, p * 0.5 + boost) * 100 >= 30 else 0)   # >=30 means SUSPICIOUS or worse
    return np.array(out)


def main():
    X, y = load()
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42)
    yt_all, ml_all, fu_all = [], [], []
    for tr, te in cv.split(X, y):
        pipe = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                         ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])
        pipe.fit(X[tr], y[tr])
        proba = pipe.predict_proba(X[te])[:, 1]
        yt_all += list(y[te]); ml_all += list((proba >= 0.5).astype(int)); fu_all += list(fused_pred(proba, X[te]))

    def block(name, pred):
        cm = confusion_matrix(yt_all, pred)
        p, r, f, _ = precision_recall_fscore_support(yt_all, pred, average="binary")
        return [f"### {name}", "", "| | Pred phishing | Pred legit |", "|---|---|---|",
                f"| **Actual phishing** | {cm[1][1]} | {cm[1][0]} |", f"| **Actual legit** | {cm[0][1]} | {cm[0][0]} |", "",
                f"Accuracy {accuracy_score(yt_all, pred):.1%} · Precision {p:.1%} · Recall {r:.1%} · F1 {f:.1%}", ""]

    lines = ["# SMS Phishing — evaluation", "",
             f"Dataset: {len(y)} messages ({int(y.sum())} phishing / {int((1-y).sum())} legitimate), `models/sms_seed_dataset.csv`.",
             "Method: 5-fold stratified cross-validation repeated 5 times (every number below is on unseen messages).", ""]
    lines += block("A) ML model only", ml_all) + block("B) ML + rule flags (offline fusion)", fu_all)
    lines += ["> Caveat: messages are hand-written by the project team (no real telecom data), so real-world accuracy will be lower. "
              "Next step: retrain on the public UCI *SMS Spam Collection* + a labelled Indian smishing set and report on a held-out split. "
              "If you do, re-run this script and replace the numbers in your report."]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
