# Presentation: roles, 2-day practice plan, viva Q&A

## Who owns what (everyone must still understand everything)
| Member | Owns | Speaks (~min) |
|---|---|---|
| **A** | Opening: problem + statistics, objectives, architecture, hash-chain log, conclusion + future scope | 3 + 1 |
| **B** | Module 1: Digital Arrest Shield (script detector, polite scammers, payment guard, family alert) + rPPG liveness | 4 |
| **C** | Module 2 + 3: Fake ID forensics (ELA + metadata) and SMS phishing + data exposure tab | 4 |
Mobile app, testing and accuracy slide: B shows app and live demo, C shows test report + accuracy, A closes.

## Day 1 — learn
1. Morning: each writes own speech (half-page, simple words, no reading from slides). 2. Afternoon: everyone teaches their module to the others in 5 min.
3. Evening: each person reads the other two modules' README sections and writes 5 questions for them.

## Day 2 — rehearse
1. Full timed run x2 (use a timer, phone recording). 2. Swap-test: random person answers questions on any module. 3. Demo rehearsal on the actual phone + Wi-Fi + hotspot backup; keep a 2-minute backup screen recording and screenshots.
4. Last run: say the first sentence of every slide from memory.

## Likely questions (everyone should answer)
- **How do you know it works?** Cross-validated SMS metrics, labelled call-transcript test set, 31 automated tests; limits stated honestly (hand-made data; real data is future work).
- **What if the scammer is polite or loving?** We judge what is asked (money, secrecy, staying on call), not the tone; plus the Payment Guard works whatever the caller says. Proof: the polite test cases.
- **How did the scammer get my data?** We cannot prove that from a call. Common routes: breaches, ID copies, fake apps, social media, courier data. The Data Exposure tab helps you check and reduce exposure.
- **Why not read SMS / record calls automatically?** Play Store policy and privacy; we use Share-to-app and user-started listening.
- **Why rPPG, and when does it fail?** Real skin shows a pulse signal; low light, motion and compression make it noisy; it's an assistive signal.
- **The camera only shows my own face; how do you check the caller?** Two modes: self-check (KYC style) and screen-share mode that reads the caller's face from the call window (laptop Chrome). Phone-native capture (MediaProjection) is future scope; compressed video makes it a weak signal, so main defence is Shield + Payment Guard.
- **Can a deepfake beat rPPG?** Some may in future; hence the layered design (voice/script + payment guard).
- **ELA limits?** Detects compression inconsistency; metadata can be stripped; it's a lead, not proof.
- **Why a hash chain?** Tamper-evident evidence trail for complaints; not a public blockchain.
- **What's new vs Truecaller / Google Messages / bank apps?** Unified, India-specific digital-arrest scripts in Hindi and English, payment pause during call, family alert, forensic reports. (Check current features of those apps before claiming a gap.)
- **Future scope:** real transcript dataset + multilingual NLP model, voice-clone detection, bank/UPI API integration, copy-move forgery detection.
