# Making DeepVerif.AI a phone app

## Recommended: PWA -> Android app via TWA (Trusted Web Activity)
Why: a TWA runs inside Chrome, so the **camera, microphone and Web Speech (live Hindi/English call listening) all keep working**,
and "Share -> DeepVerif" works. This is the same web code you already have — no rewrite.

Steps (about half a day):
1. Deploy backend over HTTPS (`docs/DEPLOYMENT.md`).
2. Open the site in Chrome on Android -> menu -> **Install app** (works as a PWA already; good for sir's testing, no Play Store needed).
3. For an APK/AAB: go to **pwabuilder.com**, enter your HTTPS URL, choose *Android* -> download the package (it contains your signing key — back it up!).
4. Put your app's package name + the SHA-256 fingerprint in `mobile/assetlinks.json` (served at `/.well-known/assetlinks.json`) and redeploy. Without this, the app shows a Chrome address bar.
5. Install the `.apk` on a phone for testing; upload the `.aab` to Play Console (see `docs/PLAY_STORE_GUIDE.md`).

## Alternative: Capacitor (WebView wrapper)
Works for camera, but **Web Speech API does not work inside Android WebView**, so the live-call listener would need a native speech plugin
(e.g. a Capacitor speech-recognition plugin) and extra code. Use only if your guide insists on "native" code.
Minimal `capacitor.config.json`: `{"appId":"com.yourteam.deepverif","appName":"DeepVerif.AI","webDir":"www","server":{"url":"https://YOUR-HTTPS-URL","cleartext":false}}`
Android permissions needed: CAMERA, RECORD_AUDIO, INTERNET.

## What we deliberately do NOT do (and why — good viva answer)
- No automatic reading of the SMS inbox or call audio: Google Play restricts SMS/call permissions to default-handler apps, and silent call recording is a privacy problem. Instead: **Share -> DeepVerif** for suspicious messages, and a mic-based listener the user starts themselves.
- No hooking into UPI apps (not possible for third parties). The Payment Guard is a "check before you pay" screen; bank/UPI integration is future scope.
