# Digital Arrest Shield — evaluation (BASELINE v2 — harder set, old rules)

Test set: 38 hand-written transcripts (20 scam, 18 benign) — `evaluation/shield_testset.csv`

| | Predicted scam | Predicted benign |
|---|---|---|
| **Actual scam** | 15 (TP) | 5 (FN) |
| **Actual benign** | 3 (FP) | 15 (TN) |

Accuracy 78.9% · Precision 83.3% · Recall 75.0% · F1 78.9%

## Per-style accuracy

| Style | Correct / Total |
|---|---|
| aggressive | 3/3 |
| aggressive_hindi | 1/1 |
| aggressive_hinglish | 2/2 |
| awareness_hinglish | 0/1 |
| awareness_talk | 0/1 |
| awareness_to_you | 0/1 |
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
| own_fir | 1/1 |
| polite_english | 4/4 |
| polite_hinglish | 4/4 |
| polite_novel_words | 0/5 |
| reassurance | 1/1 |
| secret_party | 1/1 |
| utility | 1/1 |

## Errors

- FALSE ALARM (HIGH): Did you watch the news? They said digital arrest scams are increasing, and police says nev...
- MISSED SCAM (NONE): Sir, aapke account se kuch galat transaction hue hain. Main aapki madad ke liye hoon. Aap ...
- MISSED SCAM (NONE): Madam, I am from the verification wing. Your documents show a mismatch. To protect your sa...
- MISSED SCAM (NONE): Aapki madad karna chahta hoon. Ek chhoti si problem hai aapke number me. Please paise hama...
- MISSED SCAM (NONE): Hello sir, calling from the cyber department. Everything is under control, no need to pani...
- MISSED SCAM (NONE): Beta tension mat lo, hum tumhari help karenge. Sirf ek chhota amount bhej do, case apne aa...
- FALSE ALARM (HIGH): Our school teacher said that bank officers never ask for a safe account transfer. If a str...
- FALSE ALARM (HIGH): Aaj ki news me aaya ki digital arrest fraud bahut badh gaye hain. Police ne kaha koi bhi v...

> Caveat: this set was written by the project authors, so it is optimistic. Before the final viva, add real reported call transcripts (from news/NCRP awareness material) written by a teammate who has NOT seen the rules, and re-run.