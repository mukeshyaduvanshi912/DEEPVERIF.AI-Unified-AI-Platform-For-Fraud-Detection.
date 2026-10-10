# Hosting the backend (needed for the phone app)

The phone app (PWA/APK) is just a window onto this Flask server, so the server must be reachable over **HTTPS**
(camera, microphone and the Play Store all require HTTPS).

## Option A — Render (free tier, easiest)
1. Push this folder to a GitHub repo.
2. render.com -> New -> Web Service -> pick the repo. It reads `render.yaml` automatically.
3. After deploy you get `https://deepverif-ai.onrender.com` (HTTPS included). Check `/health`.
4. Free instances sleep when idle (first request is slow) — open the URL a few minutes before a demo.

## Option B — Docker anywhere
```
docker build -t deepverif .
docker run -p 8080:8080 deepverif
```

## Option C — Local demo on your phone (no hosting)
Run `python app.py`, connect phone and laptop to the same Wi-Fi, open `http://<laptop-ip>:5000` on the phone.
Camera/mic are blocked on plain http for non-localhost, so use this only to check layout, or use a tunnel (e.g. `cloudflared tunnel --url http://localhost:5000`) to get an HTTPS URL for a demo.

## Notes
- `logs/audit_chain.jsonl` lives on the server disk; free hosts wipe it on redeploy. Fine for demo, note it in the report.
- Optional env vars: `HIBP_API_KEY` (e-mail breach check), `FLASK_DEBUG=1` (local only).
