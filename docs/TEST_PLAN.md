# Test Plan — DeepVerif.AI (for testing with the project guide)

**Build under test:** installed PWA / APK on the guide's phone  ·  **Backend:** `https://<your-site>`
**Tools:** (1) automated suite `python -m unittest discover -s tests -v`  (2) manual cases below  (3) feedback form

## A. Automated (31 cases) — run before every demo
`python tools/generate_test_report.py` -> `docs/TEST_REPORT.md`. IDs: TC-LOG, TC-SH, TC-PAY, TC-FAM, TC-SMS, TC-DOC, TC-LIV, TC-EXP, TC-API.

## B. Model accuracy
`python evaluation/evaluate_sms.py` and `python evaluation/evaluate_shield.py` -> `evaluation/results/`. Quote precision/recall, not only accuracy.

## C. Manual cases on the phone (fill Actual / Pass during the session)
| ID | Module | Steps | Expected | Actual | Pass |
|---|---|---|---|---|---|
| M-01 | Install | Open URL in Chrome -> Install app | Icon on home screen, opens full-screen | | |
| M-02 | Liveness | Real face, good light, 6-s scan | REAL with BPM shown | | |
| M-03 | Liveness | Show a printed photo / another phone playing a face video | FAKE / no pulse | | |
| M-04 | Shield | Tap "scam-call sample" | HIGH, red banner + popup | | |
| M-05 | Shield | Tap "polite-scammer sample" | HIGH + tone note | | |
| M-06 | Shield | Tap "normal-call sample" | No alarm | | |
| M-07 | Shield | Start Listening, guide reads a scam script aloud (English, then Hindi) | Transcript appears, risk rises to HIGH | | |
| M-08 | Payment | Rs.2,50,000, new payee, on call | PAUSED | | |
| M-09 | Family | Enter a number -> Create alert | WhatsApp opens with message | | |
| M-10 | Document | Upload an untouched sample ID image | LIKELY GENUINE / low score | | |
| M-11 | Document | Upload same image edited in a photo app | Heatmap highlights edit, higher score | | |
| M-12 | Document | Upload PDF edited with an online tool | Source/tool guess + report downloads | | |
| M-13 | SMS | Fake KYC SMS | PHISHING, fake % high | | |
| M-14 | SMS | Genuine OTP SMS | LIKELY SAFE | | |
| M-15 | SMS | From another app: Share -> DeepVerif | App opens, SMS tab pre-filled and analysed | | |
| M-16 | Exposure | Check password "password123" | Seen many times in breaches | | |
| M-17 | Logs | Open Audit Log tab | Entries + "chain verified" | | |
| M-19 | Liveness (screen share, laptop Chrome) | Choose 'Caller's video', share a video-call window showing a person, pick region | Result shows caller source + caveat; 'pulse not detected' appears as SUSPICIOUS, not FAKE | | |
| M-18 | Offline | Turn off internet, open app | Shell loads; analysis says offline/unavailable | | |

## D. Feedback form (Google Form, 5 questions, 1-5 scale)
1. Was the verdict easy to understand?  2. Did the warning feel trustworthy?  3. Was anything confusing on the small screen?
4. Which module is most useful?  5. One thing to improve (text).

## E. Sign-off
Tested by: ________  Guide: ________  Date: ________  Remarks: ________
