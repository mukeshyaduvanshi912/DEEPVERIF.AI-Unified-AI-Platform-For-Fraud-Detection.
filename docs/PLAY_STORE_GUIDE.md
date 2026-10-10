# Play Store — steps, time, and a fallback

> Google changes Play Console rules often. Verify the points marked (verify) in Play Console / Google's help pages before you rely on them.

## One-time setup
1. Play Console developer account: one-time fee (about US$25) + identity verification — allow a few days.
   Personal account vs Organisation account (organisation needs a D-U-N-S number; usually not practical for students).
2. Build the Android App Bundle (`.aab`) via PWABuilder/TWA (`mobile/README.md`).

## Before you can go to Production (verify)
- Newly created **personal** developer accounts must run a **closed test with ~12 testers for 14 continuous days** before applying for production access. Start this *first* — it is the longest wait. Use classmates + faculty; they must opt in with their Google accounts.
- Review of the production release: from a few days to ~2 weeks.

## Required listing items
- App name, short + full description (draft in `docs/STORE_LISTING.md`), icon 512x512 (`static/icons/icon-512.png`), feature graphic 1024x500, 2+ phone screenshots
- **Privacy policy URL** -> your deployed `https://<site>/privacy` (text in `docs/PRIVACY_POLICY.md`; replace the contact e-mail first)
- **Data safety form**: camera frames and mic text are processed for detection; no data sold; audit log stores only verdicts (see policy)
- Content rating questionnaire; target audience 18+; declare it is not a government app
- Permissions you will request: CAMERA, RECORD_AUDIO, INTERNET only

## Realistic timeline
| Week | Work |
|---|---|
| 0 | Deploy backend, create PWA package, create developer account |
| 1 | Internal testing (instant, up to 100 testers) to fix bugs |
| 1-3 | Closed test, 12 testers x 14 days (verify) |
| 3-4 | Apply for production, review |

## If time is short (very likely before the viva)
Show: (1) installed PWA, (2) signed APK on phone, (3) the Play Console closed-test page with testers joined + screenshot of the test track. Examiners accept "published to closed testing" with proof.
