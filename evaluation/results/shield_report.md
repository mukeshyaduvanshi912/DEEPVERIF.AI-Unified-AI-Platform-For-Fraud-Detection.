# Digital Arrest Shield — evaluation (AFTER)

Test set: 40 hand-written transcripts (22 scam, 18 benign) — `evaluation/shield_testset.csv`

| | Predicted scam | Predicted benign |
|---|---|---|
| **Actual scam** | 22 (TP) | 0 (FN) |
| **Actual benign** | 0 (FP) | 18 (TN) |

Accuracy 100.0% · Precision 100.0% · Recall 100.0% · F1 100.0%

## Per-style accuracy

| Style | Correct / Total |
|---|---|
| aggressive | 3/3 |
| aggressive_hindi | 1/1 |
| aggressive_hinglish | 2/2 |
| awareness_hinglish | 1/1 |
| awareness_talk | 1/1 |
| awareness_to_you | 1/1 |
| bank_support | 1/1 |
| casual | 1/1 |
| courier | 1/1 |
| fees | 1/1 |
| hinglish_bank | 1/1 |
| hinglish_casual | 1/1 |
| hinglish_money | 1/1 |
| insurance | 1/1 |
| keep_camera_on | 1/1 |
| mentions_deposit | 1/1 |
| mentions_police | 1/1 |
| mixed | 1/1 |
| case_study_hindi | 1/1 |
| case_study_romanized_hindi | 1/1 |
| own_fir | 1/1 |
| polite_english | 4/4 |
| polite_hinglish | 4/4 |
| polite_novel_words | 5/5 |
| reassurance | 1/1 |
| secret_party | 1/1 |
| utility | 1/1 |

> Caveat: this set was written by the project authors, so it is optimistic. Before the final viva, add real reported call transcripts (from news/NCRP awareness material) written by a teammate who has NOT seen the rules, and re-run.