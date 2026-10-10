# DeepVerif.AI: How to Run (step by step)

## A. On a laptop (5 minutes)
1. Install Python 3.10 to 3.12 (python.org). On Windows, tick **"Add Python to PATH"**.
2. Double-click **run.bat** in this folder (Mac/Linux: run `bash run.sh` in a terminal).
   The first run installs packages and takes 2 to 5 minutes.
3. Open in your browser: **http://localhost:5000**
4. To stop, press `Ctrl + C` in the terminal.

To run it manually:
```
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```

## B. Enabling the AI button (optional)
Before `python app.py`, run: `set ANTHROPIC_API_KEY=your-key` (Mac/Linux: `export ANTHROPIC_API_KEY=your-key`).
Without a key everything else still works, and the AI button will say "currently off".

## C. On a phone (mic, camera and notifications need HTTPS)
* **Reliable way:** deploy on Render.com (`render.yaml` is ready; details in `docs/DEPLOYMENT.md`). Set `NUMBER_SALT` to a long random string.
* **Quick test:** `cloudflared tunnel --url http://localhost:5000` gives you an HTTPS link.
* Open the link in Chrome on the phone, then menu, **Install app**.

## D. Tests and report
```
python -m unittest discover -s tests -v
python tools/generate_test_report.py
```

## E. Troubleshooting
* `python not recognized`: reinstall Python and tick PATH.
* `pip install` fails: use Python 3.10 to 3.12.
* Port 5000 busy: run `set PORT=5001`, then start the app and open `localhost:5001`.
* Mic/camera not working: use `localhost` on a laptop, or an HTTPS link on a phone.
