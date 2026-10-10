# DeepVerif.AI — Automated Test Report

Generated: 10 Oct 2026, 12:57  
Result: **44/44 passed**

| Test ID | What is checked | Result |
|---|---|---|
| TC-AI-01 | no API key -> graceful 'available: False', no network call | ✅ PASS |
| TC-AI-02 | untrusted text stays inside one <message> block (prompt-injection hardening) | ✅ PASS |
| TC-AI-03 | per-IP rate limit; API failure returns a safe error | ✅ PASS |
| TC-API-01 | / and /health respond 200 | ✅ PASS |
| TC-API-02 | manifest and service worker are served | ✅ PASS |
| TC-API-03 | /api/shield/transcript works and logs only the verdict | ✅ PASS |
| TC-API-04 | empty SMS -> 400 | ✅ PASS |
| TC-API-05 | audit log endpoint reports a valid chain | ✅ PASS |
| TC-DOC-01 | image analysis returns verdict, score and report | ✅ PASS |
| TC-DOC-02 | corrupt upload returns a clean 400 (no server crash) | ✅ PASS |
| TC-EXP-01 | awareness has leak routes + protect steps | ✅ PASS |
| TC-EXP-02 | invalid e-mail rejected | ✅ PASS |
| TC-EXP-03 | without API key e-mail check says not_configured | ✅ PASS |
| TC-FAM-01 | family alert builds a wa.me link with +91 | ✅ PASS |
| TC-INS-01 | feedback is validated, stores no text, accuracy computed | ✅ PASS |
| TC-INS-02 | stats count audit-chain events; demo data is labelled and writes nothing | ✅ PASS |
| TC-LIV-01 | frames without a face return a result (not a crash) | ✅ PASS |
| TC-LIV-02 | empty frame list handled | ✅ PASS |
| TC-LIV-03 | screen-share 'no pulse' is downgraded from FAKE to SUSPICIOUS with a caveat | ✅ PASS |
| TC-LIV-04 | screen-share with a detected pulse stays REAL | ✅ PASS |
| TC-LIV-05 | analyze_frames reports which source was used | ✅ PASS |
| TC-LOG-01 | freshly written chain verifies | ✅ PASS |
| TC-LOG-02 | editing a past record breaks verification | ✅ PASS |
| TC-NUM-01 | ordinary Indian mobile with no reports is LOW | ✅ PASS |
| TC-NUM-02 | non +91 number is at least MEDIUM | ✅ PASS |
| TC-NUM-03 | community reports raise risk; plain number is never stored | ✅ PASS |
| TC-NUM-04 | garbage input returns an error | ✅ PASS |
| TC-PAY-01 | big transfer, new payee, on call, scam flagged -> HOLD | ✅ PASS |
| TC-PAY-02 | small normal transfer -> ALLOW | ✅ PASS |
| TC-SH-01 | classic digital-arrest script -> HIGH | ✅ PASS |
| TC-SH-02 | Romanized-Hindi script -> HIGH | ✅ PASS |
| TC-SH-03 | polite / loving scammer is still caught (tone-independent) | ✅ PASS |
| TC-SH-04 | ordinary call -> NONE/LOW | ✅ PASS |
| TC-SH-05 | talking ABOUT scams (news) does not raise an alarm | ✅ PASS |
| TC-SH-06 | empty transcript handled | ✅ PASS |
| TC-SH-07 | Case-study style Hindi script (ATS/NIA/SC warrant, FD break) -> HIGH | ✅ PASS |
| TC-SH-08 | ordinary words like 'thats/stats/cats' do not trigger ATS/NIA rules | ✅ PASS |
| TC-SMS-01 | fake KYC SMS flagged (no live lookup needed) | ✅ PASS |
| TC-SMS-02 | genuine reminder SMS is LIKELY SAFE | ✅ PASS |
| TC-SMS-03 | fake% + real% = 100 | ✅ PASS |
| TC-UPI-01 | 'scan to receive' + a pay QR is HIGH | ✅ PASS |
| TC-UPI-02 | AutoPay mandate is HIGH | ✅ PASS |
| TC-UPI-03 | ordinary small payment is not HIGH but still says money goes OUT | ✅ PASS |
| TC-UPI-04 | empty input errors; QR image round-trips through decode_qr | ✅ PASS |

## Model accuracy (see `evaluation/results/`)

Run `python evaluation/evaluate_sms.py` and `python evaluation/evaluate_shield.py` and paste the tables here.

## Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| Tester (student) | | | |
| Project guide / Sir | | | |