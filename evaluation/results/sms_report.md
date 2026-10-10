# SMS Phishing — evaluation

Dataset: 111 messages (55 phishing / 56 legitimate), `models/sms_seed_dataset.csv`.
Method: 5-fold stratified cross-validation repeated 5 times (every number below is on unseen messages).

### A) ML model only

| | Pred phishing | Pred legit |
|---|---|---|
| **Actual phishing** | 271 | 4 |
| **Actual legit** | 25 | 255 |

Accuracy 94.8% · Precision 91.6% · Recall 98.5% · F1 94.9%

### B) ML + rule flags (offline fusion)

| | Pred phishing | Pred legit |
|---|---|---|
| **Actual phishing** | 250 | 25 |
| **Actual legit** | 9 | 271 |

Accuracy 93.9% · Precision 96.5% · Recall 90.9% · F1 93.6%

> Caveat: messages are hand-written by the project team (no real telecom data), so real-world accuracy will be lower. Next step: retrain on the public UCI *SMS Spam Collection* + a labelled Indian smishing set and report on a held-out split. If you do, re-run this script and replace the numbers in your report.