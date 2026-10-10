"""
make_checklist.py — one-page printable phone test checklist (tick boxes) for testing with the guide.
Usage: python tools/make_checklist.py      -> docs/DeepVerif_Phone_Test_Checklist.pdf   (needs reportlab)
IDs match docs/TEST_PLAN.md (manual cases M-xx).
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "DeepVerif_Phone_Test_Checklist.pdf")
DARK, GREEN, LINE = colors.HexColor("#0d1117"), colors.HexColor("#2da44e"), colors.HexColor("#d0d7de")

cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=9.6)
bold = ParagraphStyle("bold", parent=cell, fontName="Helvetica-Bold")
head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=DARK)
sub = ParagraphStyle("sub", parent=cell, fontSize=8.5, textColor=colors.HexColor("#57606a"))

rows = [
 ("SETUP", None, None),
 ("S-1", "App icon is on the home screen; opens full-screen (no Chrome address bar on top)", "Full-screen app"),
 ("S-2", "If asked for Camera + Microphone permission, tap Allow", "Permission granted"),
 ("LIVENESS", None, None),
 ("M-02", "Real face, good light, sit still facing the camera for 6 sec", "REAL + BPM shown"),
 ("M-03", "Show a photo or a video on another phone to the camera", "FAKE / SUSPICIOUS"),
 ("M-19", "(Laptop Chrome) Screen-share mode, choose the video-call window", "Caveat + result shown"),
 ("SHIELD", None, None),
 ("M-04", "Tap 'Try scam-call sample'", "HIGH + red banner + popup"),
 ("M-05", "'Try polite-scammer sample'", "HIGH + tone note"),
 ("M-05b", "'Digital arrest case study (Hindi)' sample", "HIGH risk"),
 ("M-06", "'Try normal-call sample'", "No alarm"),
 ("M-07", "Start Listening, read a scam script aloud (English, then Hindi)", "Transcript appears, risk rises"),
 ("PAYMENT / FAMILY", None, None),
 ("M-08", "Rs 2,50,000, new payee, call ON -> Check", "TRANSACTION PAUSED"),
 ("M-08b", "Rs 500, new payee OFF, call OFF -> Check", "LOOKS NORMAL"),
 ("M-09", "Enter another number -> Create alert -> Send on WhatsApp", "WhatsApp message opens"),
 ("DOCUMENT", None, None),
 ("M-10", "Upload a dummy ID image (from gallery)", "Low score / genuine"),
 ("M-11", "Edit the same image and upload it", "Heatmap + score rises"),
 ("M-12", "Edited PDF upload; report download", "Source guess + report"),
 ("SMS / SHARE", None, None),
 ("M-13", "'Try Fake Sample'", "PHISHING"),
 ("M-14", "'Try Genuine Sample'", "LIKELY SAFE"),
 ("M-15", "In another app, select an SMS -> Share -> DeepVerif", "SMS tab opens and analyses it"),
 ("OTHERS", None, None),
 ("M-16", "Data Exposure: password 'password123' check", "Found in breaches"),
 ("M-17", "Audit Log tab", "'chain verified'"),
 ("M-18", "Turn off the internet and open the app", "Opens; offline message; no crash"),
]

data = [[Paragraph("ID", head), Paragraph("What to do", head), Paragraph("Expected", head), Paragraph("Pass", head), Paragraph("Remarks", head)]]
style = [("BACKGROUND", (0, 0), (-1, 0), DARK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
         ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
for r in rows:
    i = len(data)
    if r[1] is None:
        data.append([Paragraph(r[0], bold), "", "", "", ""])
        style += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#e6f4ea"))]
    else:
        data.append([Paragraph(r[0], bold), Paragraph(r[1], cell), Paragraph(r[2], cell), Paragraph("[   ] Y  [   ] N", cell), ""])

t = Table(data, colWidths=[13 * mm, 69 * mm, 40 * mm, 24 * mm, 36 * mm], repeatRows=1)
t.setStyle(TableStyle(style))

info = Table([
    [Paragraph("Phone model: ______________", cell), Paragraph("Android version: ________", cell), Paragraph("Network:  [  ] Wi-Fi   [  ] Mobile data", cell)],
    [Paragraph("App link / APK version: __________________", cell), Paragraph("Tester: ______________", cell), Paragraph("Date: ____________", cell)],
], colWidths=[62 * mm, 55 * mm, 65 * mm])
info.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

foot = Table([[Paragraph("Total pass: ____ / 22", bold),
               Paragraph("If you find bugs: take a screenshot and note the phone model, Android version, what you tapped and what happened.", cell)],
              [Paragraph("Tester sign: ______________", cell), Paragraph("Guide sign: ______________   Remarks: ____________________________", cell)]],
             colWidths=[60 * mm, 122 * mm])
foot.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 4)]))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=11 * mm, bottomMargin=10 * mm,
                        title="DeepVerif.AI - Phone Test Checklist")
doc.build([Paragraph("DeepVerif.AI - Phone Test Checklist", title),
           Paragraph("After installing, try every case and tick Pass. Use dummy IDs only. Detail: docs/TEST_PLAN.md", sub),
           Spacer(1, 4), info, Spacer(1, 3), t, Spacer(1, 4), foot])
print("Saved", os.path.abspath(OUT), "| rows:", sum(1 for r in rows if r[1]))
