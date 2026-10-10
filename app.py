"""
app.py — DeepVerif.AI Unified Fraud Detection Platform
Run: python app.py   then open http://localhost:5000
"""
import os
from flask import Flask, request, jsonify, render_template, send_from_directory

import rppg
import document_forensics
import sms_phishing
import hashchain
import digital_arrest_shield as shield
import data_exposure
import number_check
import ai_explain
import upi_check
import insights

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024   # 25 MB (document / frame uploads)


@app.after_request
def security_headers(resp):
    # Camera + mic are needed by the liveness scan and the live Shield; nothing else is allowed.
    resp.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# ---- PWA / Android (TWA) plumbing -------------------------------------------------
@app.route("/sw.js")
def service_worker():
    r = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    r.headers["Service-Worker-Allowed"] = "/"
    r.headers["Cache-Control"] = "no-cache"
    return r


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")


@app.route("/.well-known/assetlinks.json")
def assetlinks():
    # Digital Asset Links: proves the Play Store app (TWA) owns this site. Edit mobile/assetlinks.json.
    return send_from_directory(os.path.join(os.path.dirname(__file__), "mobile"), "assetlinks.json",
                               mimetype="application/json")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "DeepVerif.AI | Unified AI Platform for Fraud Detection"})


@app.route("/privacy")
def privacy():
    return send_from_directory(os.path.join(os.path.dirname(__file__), "docs"), "PRIVACY_POLICY.md",
                               mimetype="text/markdown; charset=utf-8")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/liveness/analyze", methods=["POST"])
def liveness_analyze():
    data = request.get_json(force=True)
    frames = data.get("frames", [])
    fps = float(data.get("fps", 10))
    source = "screen" if data.get("source") == "screen" else "camera"
    result = rppg.analyze_frames(frames, fps=fps, source=source)
    hashchain.append_log("digital_arrest_liveness", {
        k: v for k, v in result.items() if k != "frames_used"
    })
    return jsonify(result)


@app.route("/api/document/analyze", methods=["POST"])
def document_analyze():
    try:
        return _document_analyze()
    except Exception:                       # corrupt / unsupported file -> clean 400 instead of a 500 crash
        return jsonify({"error": "Could not read this file. Upload a valid JPG/PNG or PDF."}), 400


def _document_analyze():
    data = request.get_json(force=True)
    image_b64 = data.get("image")
    pdf_b64 = data.get("pdf")

    if pdf_b64:
        result = document_forensics.analyze_pdf(pdf_b64)
        if "error" in result:
            return jsonify(result), 400
        log_result = {
            k: v for k, v in result.items()
            if k not in ("pages", "report_text")
        }
        log_result["page_count_scanned"] = len(result.get("pages", []))
        hashchain.append_log("document_forensics_pdf", log_result)
        return jsonify(result)

    if not image_b64:
        return jsonify({"error": "No image or PDF provided"}), 400

    result = document_forensics.analyze_document(image_b64)
    log_result = {k: v for k, v in result.items() if k not in ("heatmap_image_b64", "report_text")}
    hashchain.append_log("document_forensics", log_result)
    return jsonify(result)


@app.route("/api/sms/analyze", methods=["POST"])
def sms_analyze():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text.strip():
        return jsonify({"error": "No SMS text provided"}), 400
    result = sms_phishing.predict(text)
    log_result = {k: v for k, v in result.items() if k != "report_text"}
    hashchain.append_log("sms_phishing", {"text_preview": text[:60], **log_result})
    return jsonify(result)



@app.route("/api/shield/transcript", methods=["POST"])
def shield_transcript():
    data = request.get_json(force=True)
    result = shield.analyze_transcript(data.get("text", ""))
    # Privacy: log only the verdict + matched categories, never the raw conversation
    if result["risk_level"] in ("HIGH", "MEDIUM") and data.get("log", True):
        hashchain.append_log("digital_arrest_shield_script", {
            "risk_level": result["risk_level"],
            "risk_score": result["risk_score"],
            "categories": [m["category"] for m in result["matched_categories"]],
        })
    return jsonify(result)


@app.route("/api/shield/payment", methods=["POST"])
def shield_payment():
    d = request.get_json(force=True)
    result = shield.payment_guard(
        amount=d.get("amount", 0),
        new_beneficiary=bool(d.get("new_beneficiary")),
        in_video_call=bool(d.get("in_video_call")),
        call_minutes=d.get("call_minutes", 0),
        typical_max=d.get("typical_max", 10000),
        shield_risk=d.get("shield_risk", "NONE"),
    )
    hashchain.append_log("digital_arrest_shield_payment", result)
    return jsonify(result)


@app.route("/api/shield/family-alert", methods=["POST"])
def shield_family_alert():
    d = request.get_json(force=True)
    result = shield.family_alert(d.get("contact_name"), d.get("contact_phone"), d.get("user_name", "Me"))
    hashchain.append_log("digital_arrest_shield_family_alert", {"contact": result["contact"]})
    return jsonify(result)

@app.route("/api/number/check", methods=["POST"])
def number_check_api():
    d = request.get_json(force=True)
    result = number_check.check(d.get("number", ""))
    if "error" in result:
        return jsonify(result), 400
    # Privacy: only the masked number is logged
    hashchain.append_log("number_check", {"number": result["number_masked"], "risk_level": result["risk_level"],
                                          "community_reports": result["community_reports"]})
    return jsonify(result)


@app.route("/api/number/report", methods=["POST"])
def number_report_api():
    d = request.get_json(force=True)
    result = number_check.report(d.get("number", ""), d.get("category", "other"))
    if "error" in result:
        return jsonify(result), 400
    hashchain.append_log("number_reported", {"number": result["number_masked"], "category": result["category"]})
    return jsonify(result)

@app.route("/api/ai/explain", methods=["POST"])
def ai_explain_api():
    d = request.get_json(force=True)
    r = ai_explain.explain(d.get("text", ""), d.get("score"), d.get("flags") or [], request.remote_addr or "local")
    hashchain.append_log("ai_explain", {"ok": "explanation" in r})      # never log the message text
    return jsonify(r), (429 if r.get("rate_limited") else 200)


@app.route("/api/upi/check", methods=["POST"])
def upi_check_api():
    d = request.get_json(force=True)
    r = upi_check.check(d.get("text", ""), bool(d.get("expecting_to_receive")))
    if "error" in r:
        return jsonify(r), 400
    hashchain.append_log("upi_check", {"kind": r["kind"], "risk_level": r["risk_level"], "risk_score": r["risk_score"]})
    return jsonify(r)


@app.route("/api/upi/scan-image", methods=["POST"])
def upi_scan_image():
    f = request.files.get("image")
    if not f:
        return jsonify({"error": "No image received."}), 400
    data = f.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        return jsonify({"error": "Image 5 MB se badi hai."}), 413
    text = upi_check.decode_qr(data)
    if not text:
        return jsonify({"error": "Could not read the QR. Take a clear, straight photo or paste the UPI link yourself."}), 422
    r = upi_check.check(text, request.form.get("expecting_to_receive") == "1")
    hashchain.append_log("upi_check", {"kind": r["kind"], "risk_level": r["risk_level"], "risk_score": r["risk_score"]})
    r["scanned_text"] = text[:300]
    return jsonify(r)


@app.route("/api/feedback", methods=["POST"])
def feedback_api():
    d = request.get_json(force=True)
    r = insights.record_feedback(d.get("tool", ""), d.get("verdict", ""), d.get("level", ""), d.get("score"))
    return jsonify(r), (400 if "error" in r else 200)


@app.route("/api/insights")
def insights_api():
    return jsonify(insights.stats(demo=request.args.get("demo") == "1"))

@app.route("/api/exposure/awareness")
def exposure_awareness():
    return jsonify(data_exposure.awareness())


@app.route("/api/exposure/email", methods=["POST"])
def exposure_email():
    d = request.get_json(force=True)
    result = data_exposure.email_breach_check(d.get("email", ""))
    # Privacy: never log the e-mail itself, only that a check happened and its outcome.
    hashchain.append_log("data_exposure_email_check", {"status": result.get("status"), "breaches": result.get("breaches")})
    return jsonify(result)


@app.route("/api/logs")
def logs():
    return jsonify({
        "logs": hashchain.get_all_logs(50),
        "chain_status": hashchain.verify_chain(),
    })


if __name__ == "__main__":
    # Pre-train / load SMS model once at startup so first request isn't slow
    sms_phishing.train_model()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
