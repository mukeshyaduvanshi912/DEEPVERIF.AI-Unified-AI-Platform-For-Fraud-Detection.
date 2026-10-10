> **To get started quickly:** read `HOW_TO_RUN.md`, or run `run.bat` (Windows) / `bash run.sh` (Mac/Linux). Feature summary: `FEATURES_IN_10_LINES.md`.

# DeepVerif.AI — Unified Fraud Detection Platform

A unified platform detecting 3 of the most trending, government-recognized
fraud categories in India (NCRP / I4C classification):

| Module | NCRP Category | Technique |
|---|---|---|
| Digital Arrest / Deepfake Video Call Detector | Cheating by Impersonation | rPPG (remote photoplethysmography) — detects real pulse/blood-flow signal from webcam |
| **Digital Arrest Shield** (live call protection) | Cheating by Impersonation, Fraud Call / Vishing | Live-speech scam-script detector + payment guard + family alert |
| Fake / Tampered ID Document Detector (image **or PDF**) | Identity Theft / Profile Hacking | Error Level Analysis (ELA) forensic imaging + EXIF/PDF metadata + source fingerprinting, with a downloadable report |
| Data Exposure ("how did my data leak?") | Identity Theft / Awareness | Private password check (HIBP k-anonymity), optional e-mail check, leak routes + protection steps |
| SMS Phishing (Smishing) Detector | Fraud Call / Vishing, Online Financial Fraud | TF-IDF + Logistic Regression ML model + rule-based red-flag detection + live link-history/WHOIS check + claimed-sender vs link-domain cross-check |

Every detection event is written to a **SHA-256 hash-chained audit log**
(tamper-evident, like a mini blockchain) — useful for generating
evidence reports.

---

## 1. Setup

```bash
cd deepverif-ai
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** in your browser (Chrome recommended for
webcam/mic permissions).

> Webcam access requires either `localhost` or HTTPS — running locally
> on `localhost:5000` works fine in Chrome/Edge/Firefox.

---

## 2. How to demo each module

### A. Digital Arrest / Deepfake Detector (Liveness tab)
1. Allow camera access when prompted.
2. Click **"Start 6-second Liveness Scan"** and sit still, well-lit.
3. The backend tracks your face, extracts a green-channel signal from
   your forehead ROI across ~60 frames, and looks for a periodic pulse
   in the 42-180 BPM band via FFT.
4. **REAL** = a consistent heartbeat signal was found.
   **FAKE** = no physiological signal (static photo, screen replay,
   many deepfake streams don't reproduce this).

   *Demo trick:* run it once live on your own face (→ REAL), then hold
   up a photo or play a recorded video of a face to the camera (→ FAKE).

### A2. Digital Arrest Shield (Shield tab) — stops the scam before money is sent
rPPG only catches fake faces. In most real digital-arrest calls a REAL person in uniform is on camera,
so the Shield listens to what is said and guards the payment step.
1. **Live scam-script detector** — click *Start Listening* (Chrome/Edge, allow mic; pick English or Hindi).
   Speech is converted to text in the browser and matched against the 6 phases of the scam script:
   authority claim, accusation, arrest threat, isolation ("don't tell anyone / don't disconnect"),
   money demand ("safe account / security deposit"), urgency. Isolation + money demand together, or an arrest
   threat with either, = HIGH risk -> red banner + awareness popup + action steps (disconnect, 1930).
   No mic? Use the *Try scam-call sample* button or paste text.
2. **Payment guard** — explainable risk rules: amount vs your usual maximum, new beneficiary, transfer during a
   live call, very long call, plus the live script risk. High risk = transfer PAUSED (cooling-off).
3. **Family alert** — builds a WhatsApp click-to-chat message for a trusted contact, breaking the "isolation"
   the scam depends on.
Privacy: only the verdict + matched categories are written to the audit log, never the raw conversation.

Demo flow: rPPG scan on a photo (FAKE) -> Shield with the scam sample (HIGH + popup) -> Payment guard (PAUSED)
-> Family alert -> Audit Log tab (chain verified).

Honest limits: phrase matching is rule-based, so a scammer using entirely new wording can slip through;
browser speech recognition is weaker on Hindi and needs internet in Chrome; a real deployment would run
on the phone/bank side. Future scope: train an NLP classifier on real reported call transcripts.

### B. Fake ID Document Detector (Document tab)
1. Upload any ID-style file — **image (JPG/PNG) or PDF** (sample Aadhaar/PAN
   mockup, marksheet, etc — **use only sample/dummy data, never a real ID**).
2. The system runs Error Level Analysis: recompresses the image (or every
   rendered page, for a PDF) and diffs it against the original — regions
   with different compression history (pasted/edited/AI-generated parts)
   light up in the heatmap.
3. It also fingerprints file metadata — EXIF for images (Software tag,
   camera Make/Model, Stable-Diffusion/ComfyUI-style PNG text chunks) or
   the document info dictionary for PDFs (Producer/Creator strings,
   incremental-save "%%EOF" count, creation-vs-modification date
   mismatch) — against a table of known editor / AI-generator / online
   PDF-tool signatures, to make a best-effort guess at **which source the
   file was likely produced or edited with**.
4. Click **⬇️ Download Full Report** after analysis for a complete,
   plain-text forensic report (verdict, score, detected source +
   evidence, per-page ELA stats, and honest limitations) — useful to
   attach to a project report or a cyber-crime complaint mock-up.
5. Try one unedited file, then one edited in any photo editor / PDF tool,
   to see the contrast in the demo.

   > Note: ELA sensitivity is tuned for realistic photographed/scanned
   > documents. Perfectly flat, synthetic (vector-text-only) test images
   > show a smaller contrast — for the strongest demo, use a real
   > photograph of a printed document, lightly edited in any photo app.
   > PDF support requires the `PyMuPDF` package (already in
   > `requirements.txt`); only the first 10 pages of a PDF are scanned
   > for performance.
   > Source detection is metadata-based: it is a strong assistive signal,
   > not proof — an attacker can strip or forge metadata.

### C. SMS Phishing Detector (SMS tab)
1. Paste any SMS text, or click a **Try Fake Sample** / **Try Genuine Sample** button.
2. The ML model (trained on `models/sms_seed_dataset.csv`) + rule-based
   red flags (shortened links, urgency language, impersonation
   keywords, OTP/PIN requests) combine into a fraud score, shown as a
   clear **Fake likelihood % vs Real likelihood %**.
3. **Claimed source / sender** — the text is checked for a claimed brand
   (e.g. "SBI", "Income Tax Dept") and a sign-off signature (e.g.
   "-SBI"). If a link is present, its destination domain is cross-checked
   against the brand's real official domain — a mismatch (e.g. "claims
   SBI, links to bit.ly") is flagged as likely spoofing.
4. **Link history** — every link found in the text (even a bare one like
   `bit.ly/xyz` with no `http://`) is actually followed live: the full
   redirect chain, final destination domain, IP-literal / suspicious-TLD
   checks, and (if internet + the `python-whois` package are available)
   the domain's registration age — a domain registered days ago is one of
   the strongest phishing signals there is.
5. Click **⬇️ Download Full Report** for a complete plain-text report
   (verdict, fake/real %, claimed-sender check, full link history,
   honest limitations) to attach as evidence.
6. **Improve accuracy:** replace/expand `models/sms_seed_dataset.csv`
   with a larger real-world labelled smishing dataset, then re-run
   `python sms_phishing.py` to retrain.

   > Note: live link-following and WHOIS lookups need internet access.
   > If a link's host is unreachable, or `python-whois` isn't installed,
   > the report says so explicitly instead of guessing.

### D. Audit Log tab
Shows every detection event as a hash-chained record + a
**"chain verified"** status — this is your tamper-evident evidence
trail for a project report or a cyber-crime complaint mock-up.

---

## 3. Project structure

```
deepverif-ai/
├── app.py                   # Flask app, all API routes
├── rppg.py                  # Deepfake/liveness detection (rPPG)
├── digital_arrest_shield.py # Live scam-script detector, payment guard, family alert
├── document_forensics.py    # Fake ID document detection (ELA)
├── sms_phishing.py          # SMS phishing detection (ML + rules)
├── hashchain.py             # Tamper-evident audit logging
├── data_exposure.py         # Data-leak awareness + optional e-mail breach check
├── evaluation/              # Accuracy scripts, labelled test sets, results
├── tests/                   # Automated test suite
├── tools/                   # Test-report generator
├── mobile/                  # PWA/TWA/Play Store notes, assetlinks.json
├── docs/                    # Test plan, privacy policy, store guide, practice plan
├── Procfile, Dockerfile, render.yaml  # Hosting
├── requirements.txt
├── templates/index.html     # Unified dashboard UI
├── static/app.js            # Webcam capture, API calls, UI logic
├── static/style.css
├── models/                  # SMS training data + saved model (auto-generated)
└── logs/audit_chain.jsonl   # Hash-chain log (auto-generated)
```

---

## 4. Honest limitations (mention these in your viva/report — examiners respect this)

- **rPPG liveness** is a real, published technique, but consumer
  webcams + compressed video streams make it noisier than lab
  conditions. Treat the BPM/REAL-FAKE output as an assistive signal,
  not a certainty — this is true of the real-world state of the art too.
- **ELA** flags *compression inconsistency*, which correlates with
  tampering but isn't proof by itself; pair it with metadata checks
  (already included) and, for a stronger project, add a second cue
  like copy-move forgery detection (mentioned as future scope).
- **Source/provenance fingerprinting** is metadata-based (EXIF for
  images, Producer/Creator + incremental-save markers for PDFs) matched
  against a known-signature table — an attacker who strips or fakes
  metadata can defeat it, so treat the "detected source" as a lead to
  investigate further, not a verified fact.
- **SMS model** is trained on a small hand-written dataset (111 examples) — the
  rule-based layer carries most of the real-world detection weight
  right now. Swapping in a larger public smishing dataset before your
  final demo will make the ML side meaningfully stronger.
- **Shield accuracy numbers are optimistic**: the transcript test set was written by the authors, who also tuned the rules. Add real reported transcripts written by someone who hasn't seen the rules.
- **Screen-share mode** works on desktop Chrome only; compressed call video often hides the pulse, so 'no pulse' is shown as a weak warning. Real digital-arrest callers are often real people, so face check is one layer, not the main defence.
- **Polite scammers** are handled by judging what is asked (money, secrecy, staying on call), not tone. A scam using wording we never listed can still slip through; the Payment Guard is the safety net.
- **We cannot prove who leaked a victim's data.** The Data Exposure tab shows likely routes and reduces exposure only.
- **Android**: no silent SMS/call access (Play policy + privacy). Use Share-to-app and user-started listening.
- **Link history / WHOIS** requires internet access at analysis time;
  in a sandboxed/offline environment (or without `python-whois`
  installed) those specific checks say "unavailable" rather than
  failing silently or guessing.

## 5. Good "future scope" lines for your report
- Android app extension to read live SMS inbox via `SmsManager` /
  `ContentObserver` (needs `READ_SMS` runtime permission) for true
  real-time interception instead of paste-and-test.
- Voice-clone detection module (librosa/MFCC — you already have this
  skillset) to extend "Digital Arrest" coverage to audio-only scam calls.
- Larger, real labelled datasets for both the SMS and document modules.

---

## 6. What's new in this version (v4)
| Area | Change |
|---|---|
| Accuracy / justification | `evaluation/evaluate_sms.py` (repeated 5-fold CV, confusion matrix, P/R/F1), `evaluation/evaluate_shield.py` (38 labelled transcripts incl. polite scammers). SMS dataset 30 -> 111 messages. Results in `evaluation/results/` |
| Polite / loving imposter | Shield adds trust-building + soft-isolation + new money phrases, behavioural rules (money + any pressure = at least MEDIUM), a "discussion about scams" dampener, and a tone note. Baseline vs after is saved in `evaluation/results/` |
| Data leak | New **Data Exposure** tab + `data_exposure.py` |
| Phone | Installable PWA (manifest, service worker, icons), Android **Share -> DeepVerif**, mobile layout, `/health`, gunicorn/Docker/Render files |
| Testing | 31 automated tests (`tests/`), `tools/generate_test_report.py`, `docs/TEST_PLAN.md` |
| Store | `docs/PLAY_STORE_GUIDE.md`, `PRIVACY_POLICY.md` (also at `/privacy`), `STORE_LISTING.md`, `mobile/` |
| Liveness modes | **My face** (self-check) and **Caller's video** (screen share via `getDisplayMedia`, laptop Chrome). Screen mode crops to the caller's tile, and treats 'no pulse' as weak evidence (SUSPICIOUS, not FAKE) because call video is compressed. Android native (MediaProjection) = future scope |
| Bug fix | Corrupt upload to `/api/document/analyze` now returns 400 instead of crashing |

Measured results (cross-validated / hand-made sets — be honest about this in the viva):
- SMS (111 msgs, 5x5-fold CV): ML only 94.8% accuracy, recall 98.5%; ML+rules (offline) 93.9% accuracy, precision 96.5%.
- Shield (40 transcripts): old rules 78.9% -> new rules 100%, but the set is author-written and the rules were tuned on it, so treat 100% as an upper bound.

### Quick commands
```bash
python -m unittest discover -s tests -v        # 44 automated tests
python tools/generate_test_report.py           # writes docs/TEST_REPORT.md
python tools/make_handout.py https://YOUR-SITE  # one-page install handout with QR -> docs/DeepVerif_Install_Handout.pdf
python tools/make_checklist.py                  # printable phone test checklist -> docs/DeepVerif_Phone_Test_Checklist.pdf
python evaluation/evaluate_sms.py              # SMS metrics
python evaluation/evaluate_shield.py           # Shield metrics
```
Phone app: see `mobile/README.md` and `docs/DEPLOYMENT.md`. Other docs: `docs/TEST_PLAN.md`, `docs/PLAY_STORE_GUIDE.md`, `docs/PRESENTATION_PRACTICE_PLAN.md`, `docs/DELIVERABLES_CHECKLIST.md`.

---

## 6. NEW: Alerts, Help & Report (1930) and Number Check

**Help & Report tab** (`🚨`): one-tap *Call 1930*, cybercrime.gov.in and Sanchar Saathi links, "what to do if money is lost" steps,
Hindi scam-awareness cards, clipboard "Check copied message", and a caller-number checker.

**Alerts:** when the SMS detector scores >= 30 or the live Shield hits HIGH, a red/amber alert bar appears with the *reasons*
and Call-1930 / Report buttons. After the user taps *Allow notifications*, the same alert is also sent as a phone notification
(tap -> opens the Help tab). Notifications fire while the app is open or recently active; there is no push server, so this is not
background monitoring.

**Number check** (`number_check.py`, `/api/number/check`, `/api/number/report`): heuristics (foreign number, odd format, 140-series)
plus community reports. Numbers are stored only as salted SHA-256 hashes (set `NUMBER_SALT` in production). A LOW result is not proof of
safety. Reports are not rate-limited yet (future scope: abuse protection, stronger hashing/HMAC).

**App shortcuts:** long-press the installed app icon -> *Check a message / Help 1930 / Live Call Shield*.

**Still NOT possible in a PWA/TWA:** automatic reading of the SMS inbox, automatic incoming-call screening, background call audio.
That needs a native Android app (SMS/NotificationListener + `CallScreeningService`) and Google Play policy approval.

---

## 7. NEW: AI explanation, QR/UPI check, feedback + dashboard

* **AI explanation** (`ai_explain.py`): optional button under an SMS result. Needs `ANTHROPIC_API_KEY` on the server (otherwise it politely says it is off).
  Opt-in with a confirm dialog; the message goes to the Anthropic API for that request only and is never logged. The message is wrapped as untrusted
  data (prompt-injection hardening), rate-limited per IP, and answers in simple English. Model defaults to `claude-haiku-5-5` (override with `ANTHROPIC_MODEL`).
* **QR / UPI Check** (`upi_check.py`): take a photo of a QR (server decodes it with OpenCV) or paste a `upi://` link. Explains that a UPI QR always sends
  money OUT, flags AutoPay mandates, "receive money" claims, scam words, large amounts, bad payee IDs. It cannot verify that a payee is genuine; LOW is not "safe".
* **Feedback + Dashboard** (`insights.py`): 👍/👎 on results (stores only tool, verdict, level, score, never text). The Dashboard reads the audit chain.
  **"Demo data" is clearly labelled SAMPLE data**; use the real data for evaluation numbers.
