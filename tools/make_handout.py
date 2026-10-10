"""
make_handout.py — one-page install handout (with QR code) for the guide / testers.

Usage:
    python tools/make_handout.py https://your-site.onrender.com [feedback-form-url]
    python tools/make_handout.py                      # no URL yet -> empty QR box to fill later
Output: docs/DeepVerif_Install_Handout.pdf     (needs only reportlab: pip install reportlab)
"""
import os, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

url = sys.argv[1].strip() if len(sys.argv) > 1 else ""
form = sys.argv[2].strip() if len(sys.argv) > 2 else ""
out = os.path.join(os.path.dirname(__file__), "..", "docs", "DeepVerif_Install_Handout.pdf")

W, H = A4
c = canvas.Canvas(out, pagesize=A4)
c.setTitle("DeepVerif.AI - Install & Test Guide")
GREEN, DARK, GREY = colors.HexColor("#2da44e"), colors.HexColor("#0d1117"), colors.HexColor("#57606a")
M = 42

# header band
c.setFillColor(DARK); c.rect(0, H - 92, W, 92, fill=1, stroke=0)
c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 24); c.drawString(M, H - 50, "DeepVerif.AI")
c.setFont("Helvetica", 11.5); c.setFillColor(colors.HexColor("#c9d1d9"))
c.drawString(M, H - 70, "Unified fraud detection - install & test guide")

# QR block
qx, qy, qs = W - M - 150, H - 270, 150
if url:
    w = QrCodeWidget(url); b = w.getBounds()
    d = Drawing(qs, qs, transform=[qs / (b[2] - b[0]), 0, 0, qs / (b[3] - b[1]), 0, 0]); d.add(w)
    renderPDF.draw(d, c, qx, qy)
else:
    c.setStrokeColor(GREY); c.setDash(4, 3); c.rect(qx, qy, qs, qs); c.setDash()
    c.setFillColor(GREY); c.setFont("Helvetica", 9.5)
    c.drawCentredString(qx + qs / 2, qy + qs / 2 + 4, "QR code goes here")
    c.drawCentredString(qx + qs / 2, qy + qs / 2 - 9, "(run the script after deploying)")
c.setFillColor(DARK); c.setFont("Helvetica-Bold", 10.5)
c.drawCentredString(qx + qs / 2, qy - 15, "Scan or open the link")
c.setFont("Helvetica", 9); c.setFillColor(GREEN)
c.drawCentredString(qx + qs / 2, qy - 28, url if url else "____________________________")

from reportlab.lib.utils import simpleSplit
BODY = colors.HexColor("#24292f")


def para(text, x, y, width, font="Helvetica", size=10.5, lead=14, color=BODY):
    """Draw wrapped text; return the y below the last line."""
    c.setFont(font, size); c.setFillColor(color)
    for line in simpleSplit(text, font, size, width):
        c.drawString(x, y, line); y -= lead
    return y


def heading(text, y):
    c.setFillColor(DARK); c.setFont("Helvetica-Bold", 13); c.drawString(M, y, text); return y - 8


LEFT_W = qx - M - 18          # left column stops before the QR code
FULL_W = W - 2 * M

# what it does (left of QR)
y = heading("What this app does", H - 122) - 12
for t in ["Digital Arrest Shield: detects scam-call scripts (even from a polite caller) and pauses payments",
          "Deepfake check: reads a real pulse signal from the camera in 6 seconds",
          "Fake ID check: finds edited Aadhaar/PAN images or PDFs",
          "SMS phishing check: checks fake SMS and link history"]:
    y = para("-  " + t, M + 6, y, LEFT_W - 6, lead=13) - 4

# install steps (below the QR)
y = min(y, qy - 40) - 14
y = heading("How to install (Android + Chrome, 2 minutes)", y) - 8
steps = ["Scan the QR or open the link above in Chrome (the first load may take 30-60 seconds).",
         "Chrome menu (three dots) -> tap 'Install app' or 'Add to Home screen'.",
         "Open the 'DeepVerif' icon from the home screen. It runs like a full-screen app.",
         "Tap 'Allow' for Camera and Microphone permission (only for the liveness scan and Shield)."]
for i, t in enumerate(steps, 1):
    c.setFillColor(GREEN); c.circle(M + 10, y + 3, 8, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 10); c.drawCentredString(M + 10, y, str(i))
    y = para(t, M + 28, y, FULL_W - 28, lead=13) - 9

# quick test
y -= 6
y = heading("How to test in 5 minutes", y) - 8
tests = [("Shield tab", "'Try scam-call sample' -> HIGH risk + red banner. 'polite-scammer sample' -> bhi HIGH."),
         ("Liveness tab", "Real face -> REAL. Show a photo or a video on another phone -> FAKE."),
         ("SMS tab", "'Try Fake Sample' -> PHISHING. 'Try Genuine Sample' -> SAFE."),
         ("Document tab", "Upload a dummy ID, then upload an edited copy and compare."),
         ("Audit Log tab", "'chain verified' should be shown."),
         ("Data Exposure tab", "Check a password (it is hashed in the browser itself).")]
for k, v in tests:
    c.setFont("Helvetica-Bold", 10); c.setFillColor(DARK); c.drawString(M + 6, y, k)
    y = para(v, M + 112, y, FULL_W - 112, size=10, lead=13) - 4

# notes
y -= 8
y = heading("Keep in mind", y) - 8
for t in ["Use dummy / sample IDs only; never upload a real Aadhaar or PAN.",
          "Results are assistive, not a 100% guarantee. If fraud happens, call 1930 or visit cybercrime.gov.in.",
          "If you get an APK: Settings -> allow 'Install unknown apps'; if Play Protect warns, tap 'Install anyway'.",
          "iPhone: Safari -> Share -> Add to Home Screen. Android Chrome is better for the live mic listener."]:
    y = para("-  " + t, M + 6, y, FULL_W - 6, size=10, lead=13) - 3

# feedback / sign-off
y -= 14
c.setStrokeColor(colors.HexColor("#d0d7de")); c.line(M, y + 12, W - M, y + 12)
y -= 6
y = heading("Feedback & sign-off", y) - 10
c.setFont("Helvetica", 10); c.setFillColor(BODY)
c.drawString(M + 6, y, "Feedback form: " + (form if form else "__________________________________________"))
y -= 26
c.drawString(M + 6, y, "Tested by: ______________   Guide: ______________   Date: ___________")
y -= 22
c.drawString(M + 6, y, "Remarks: ____________________________________________________________")

c.setFillColor(GREY); c.setFont("Helvetica", 8.5)
c.drawCentredString(W / 2, 24, "DeepVerif.AI  |  Full test plan: docs/TEST_PLAN.md")
c.save()
print("Saved", os.path.abspath(out), "| QR for:", url or "(empty box)")
