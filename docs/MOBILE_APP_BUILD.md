# DeepVerif.AI Mobile App v2

This build turns the existing DeepVerif.AI web project into a mobile-first installable PWA focused on real-time digital-arrest scam protection.

## Main user flow
1. Open DeepVerif.AI on Android Chrome over HTTPS.
2. Tap **Start Call Protection**.
3. Put a suspicious call on speaker (the browser cannot silently access cellular call audio).
4. Allow microphone permission.
5. The app continuously speech-recognises the caller and sends transcript text to the Digital Arrest Shield.
6. When patterns such as police/CBI impersonation + accusation + arrest threat + isolation + money demand appear, the app shows a high-risk warning and speaks an audible warning.
7. User can stop the call, alert family, run Payment Guard, save/share an incident report, call 1930, or open the official cybercrime portal.

## Reporting
The report is generated locally in the browser. It contains the detection summary, user notes, caller number (if entered), recommended actions, and optionally the transcript. Raw conversation text is not written to the server hash-chain audit log by the Shield API.

## Important limitation
A normal third-party Android app/browser cannot silently read another cellular call's audio. This build therefore uses an explicit user-started microphone listener. For a live phone-call demo, use speakerphone and keep the DeepVerif app open. Do not claim that it intercepts or records cellular calls automatically.

## Android installation
- Deploy the Flask app over HTTPS.
- Open the URL in Chrome on Android.
- Choose **Install app / Add to Home screen**.
- For a Play Store APK/AAB, use the existing `mobile/README.md` TWA instructions or PWABuilder after deployment.

## Emergency reporting in India
- Cyber-fraud helpline: **1930**
- Official portal: **https://cybercrime.gov.in/**

## Scope
This is a fraud-risk assistant, not proof that a caller is genuine or guilty. Users should independently verify any caller through an official number and should never transfer money merely because a caller claims to be police, CBI, ED, NIA, a court, a bank, or another authority.
