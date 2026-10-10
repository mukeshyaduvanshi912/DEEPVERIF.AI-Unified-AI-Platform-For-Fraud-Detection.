"""
document_forensics.py — Fake / Tampered ID Document Detection
Now supports BOTH image uploads (JPG/PNG/etc) and PDF uploads.

Techniques used:
  1. Error Level Analysis (ELA) — re-save at a known JPEG quality and diff
     against the original. Regions that were edited/pasted-in later (or are
     AI-generated with a different original compression history) show a
     DIFFERENT error level than the rest of a uniformly-compressed genuine
     image/scan — they light up in the ELA heatmap.
     For PDFs, every page is rendered to an image first and the same ELA
     pass runs on each page.
  2. Metadata / provenance fingerprinting — EXIF (images) or document info
     dictionary (PDFs) is scanned against a table of known editor / AI
     tool / online-PDF-editor signatures to make a best-effort guess at
     *which source the file was produced or edited with*.
  3. Document-integrity checks for PDFs — incremental-save count
     (multiple "%%EOF" markers = the file was re-saved after creation),
     creation-vs-modification date mismatch, and encryption status.
  4. A human-readable "complete report" string is assembled from all of
     the above so it can be shown on screen, saved to the audit log, and
     downloaded by the user as evidence.

Honest limitation: none of this is legal proof of forgery — ELA flags
*compression inconsistency* and metadata can be stripped or forged by an
attacker, so these are strong assistive signals, not certainty. This is
stated in the generated report too.
"""
import base64
import io
import re
from datetime import datetime

import numpy as np
from PIL import Image, ImageChops, ExifTags

try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def _decode_b64(b64_str: str) -> bytes:
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    return base64.b64decode(b64_str)


def _encode_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def _ela_diff(img: Image.Image, quality: int = 90) -> np.ndarray:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    resaved = Image.open(buf)
    diff = ImageChops.difference(img.convert("RGB"), resaved)
    return np.array(diff).astype(np.float32)


def _analyze_pixels(img: Image.Image, quality: int = 90) -> dict:
    """Runs ELA on a single image (or a single rendered PDF page) and
    returns the suspicious-area stats + a red heatmap overlay."""
    diff_arr = _ela_diff(img, quality=quality)
    error_map = diff_arr.max(axis=2)
    mean_error = float(np.mean(error_map))
    std_error = float(np.std(error_map))

    threshold = mean_error + 1.5 * std_error
    suspicious_mask = error_map > max(threshold, 6)
    suspicious_pct = float(100.0 * np.sum(suspicious_mask) / suspicious_mask.size)

    heat = np.array(img.convert("RGB")).astype(np.float32)
    heat[suspicious_mask] = [255, 0, 0]
    heat_img = Image.fromarray(heat.astype(np.uint8))

    return {
        "suspicious_area_pct": round(suspicious_pct, 2),
        "error_std": round(std_error, 2),
        "heatmap_image_b64": _encode_image(heat_img),
    }


def _fuse_score(suspicious_pct: float, std_error: float, metadata_penalty: float = 0.0) -> float:
    score = min(1.0, (suspicious_pct / 3.0) * 0.75 + metadata_penalty + min(std_error / 60, 0.15))
    return round(score * 100, 1)


def _verdict_for(fraud_score: float) -> str:
    if fraud_score >= 55:
        return "SUSPICIOUS / LIKELY TAMPERED"
    elif fraud_score >= 30:
        return "NEEDS MANUAL REVIEW"
    return "LIKELY AUTHENTIC"


# --------------------------------------------------------------------------
# Source / provenance fingerprinting
# --------------------------------------------------------------------------

# (substring to look for in metadata, case-insensitive) -> (friendly source label, suspicion weight)
# Suspicion weight is added to the fraud score when this signature is the
# apparent origin of what is supposed to be an official scanned document.
IMAGE_SOURCE_SIGNATURES = [
    ("stable diffusion", "AI image generator — Stable Diffusion", 0.30),
    ("midjourney", "AI image generator — Midjourney", 0.30),
    ("dall-e", "AI image generator — DALL-E", 0.30),
    ("dalle", "AI image generator — DALL-E", 0.30),
    ("comfyui", "AI image generator — ComfyUI (Stable Diffusion workflow)", 0.30),
    ("automatic1111", "AI image generator — Stable Diffusion WebUI", 0.30),
    ("firefly", "AI image generator — Adobe Firefly", 0.25),
    ("nightcafe", "AI image generator — NightCafe", 0.25),
    ("leonardo.ai", "AI image generator — Leonardo.Ai", 0.25),
    ("bing image creator", "AI image generator — Bing Image Creator", 0.25),
    ("photoshop", "Image editor — Adobe Photoshop", 0.15),
    ("gimp", "Image editor — GIMP", 0.15),
    ("canva", "Design tool — Canva", 0.15),
    ("pixlr", "Online editor — Pixlr", 0.15),
    ("paint.net", "Image editor — Paint.NET", 0.12),
    ("lightroom", "Photo editor — Adobe Lightroom", 0.05),
    ("snapseed", "Mobile photo editor — Snapseed", 0.10),
]

# Stable-Diffusion-style tools write extra text chunks into PNG metadata
# (Automatic1111 uses "parameters", ComfyUI uses "prompt"/"workflow").
AI_PNG_TEXT_KEYS = ["parameters", "prompt", "workflow", "Comment", "Description"]
AI_PNG_TEXT_HINTS = ["steps:", "sampler", "cfg scale", "seed", "model hash", "checkpoint", "negative prompt", "nodes"]

PDF_SOURCE_SIGNATURES = [
    ("reportlab", "Programmatically generated PDF — ReportLab library (typical of scripted/fabricated fake documents, not a real scan)", 0.35),
    ("img2pdf", "img2pdf — a single image wrapped as a PDF (often used to disguise an edited image as a 'scanned' document)", 0.30),
    ("wkhtmltopdf", "wkhtmltopdf — HTML-to-PDF conversion (typical of templated/auto-generated documents)", 0.25),
    ("pikepdf", "pikepdf — programmatic PDF editing library", 0.25),
    ("pypdf", "PyPDF / pypdf — programmatic PDF editing library", 0.25),
    ("pdfkit", "pdfkit — HTML-to-PDF conversion library", 0.20),
    ("skia/pdf", "Google Chrome 'Print to PDF' (Skia PDF engine)", 0.10),
    ("ilovepdf", "iLovePDF — online PDF editing tool", 0.20),
    ("smallpdf", "Smallpdf — online PDF editing tool", 0.20),
    ("sejda", "Sejda — online PDF editing tool", 0.20),
    ("pdf-xchange", "PDF-XChange Editor", 0.15),
    ("photoshop", "Adobe Photoshop (unusual producer for an official document scan)", 0.20),
    ("canva", "Canva design export", 0.15),
    ("libreoffice", "LibreOffice Writer/Calc export", 0.05),
    ("microsoft word", "Microsoft Word export", 0.05),
    ("microsoft powerpoint", "Microsoft PowerPoint export", 0.05),
    ("adobe acrobat", "Adobe Acrobat (manual PDF editing tool)", 0.10),
    ("scan", "Physical scanner software (consistent with a genuine scanned document)", -0.10),
    ("epson", "Epson scanner driver (consistent with a genuine scanned document)", -0.10),
    ("canon", "Canon scanner/printer driver (consistent with a genuine scanned document)", -0.10),
    ("hp scanjet", "HP ScanJet driver (consistent with a genuine scanned document)", -0.10),
]


def _image_source_analysis(img: Image.Image) -> dict:
    evidence = []
    detected = []
    penalty = 0.0

    # 1. EXIF Software / camera tags
    try:
        exif_raw = img.getexif()
        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif_raw.items()} if exif_raw else {}
    except Exception:
        tags = {}

    software = str(tags.get("Software", ""))
    make = tags.get("Make")
    model = tags.get("Model")

    haystack = software.lower()
    for needle, label, weight in IMAGE_SOURCE_SIGNATURES:
        if needle in haystack:
            detected.append(label)
            evidence.append(f"EXIF 'Software' tag contains '{software}'")
            penalty += weight

    if not tags:
        evidence.append("No EXIF metadata at all — common in screenshots, messaging-app re-saves, or AI-generated images")
        penalty += 0.10
    elif make or model:
        evidence.append(f"Camera metadata present (Make/Model: {make or '?'} {model or ''}) — consistent with a real camera photo")
        penalty -= 0.05

    # 2. PNG text chunks used by Stable-Diffusion-family tools
    info = getattr(img, "info", {}) or {}
    for key in AI_PNG_TEXT_KEYS:
        if key in info:
            val = str(info[key]).lower()
            if any(hint in val for hint in AI_PNG_TEXT_HINTS) or key in ("prompt", "workflow"):
                detected.append(f"AI image generator — Stable Diffusion / ComfyUI-style tool (found '{key}' metadata chunk)")
                evidence.append(f"PNG metadata chunk '{key}' contains generation parameters (prompt/sampler/seed-style data)")
                penalty += 0.35

    if detected:
        # de-duplicate while keeping order
        seen = set()
        detected = [d for d in detected if not (d in seen or seen.add(d))]
        label = detected[0]
        confidence = "HIGH" if penalty >= 0.3 else "MEDIUM"
    elif tags and (make or model):
        label = "No editing/AI signature found — appears to be a direct, unedited camera photo"
        confidence = "LOW (absence of a signature is not proof of authenticity)"
    else:
        label = "Unknown — no usable metadata (stripped, screenshot, or messaging-app re-compression)"
        confidence = "LOW"

    return {
        "detected_source": label,
        "all_signatures_found": detected,
        "confidence": confidence,
        "evidence": evidence,
        "score_penalty": max(-0.10, penalty),
    }


def _pdf_source_analysis(meta: dict, raw_bytes: bytes) -> dict:
    evidence = []
    detected = []
    penalty = 0.0

    producer = str(meta.get("producer", "") or "")
    creator = str(meta.get("creator", "") or "")
    haystack = (producer + " " + creator).lower()

    for needle, label, weight in PDF_SOURCE_SIGNATURES:
        if needle in haystack:
            detected.append(label)
            field = "Producer" if needle in producer.lower() else "Creator"
            evidence.append(f"PDF {field} field contains '{producer if field == 'Producer' else creator}'")
            penalty += weight

    if not producer and not creator:
        evidence.append("No Producer/Creator metadata present — often stripped intentionally before circulating a fake")
        penalty += 0.15

    # Incremental update / re-save detection
    eof_count = raw_bytes.count(b"%%EOF")
    if eof_count > 1:
        evidence.append(f"File contains {eof_count} '%%EOF' markers — the PDF was incrementally saved/edited {eof_count - 1} time(s) after its original creation")
        penalty += 0.15

    # Creation vs modification date mismatch
    cdate, mdate = meta.get("creationDate"), meta.get("modDate")
    if cdate and mdate and cdate != mdate:
        evidence.append(f"Creation date ({cdate}) differs from modification date ({mdate}) — the file was edited after it was first created")
        penalty += 0.10

    if meta.get("encryption"):
        evidence.append(f"Document is encrypted/permission-restricted ({meta.get('encryption')})")

    if detected:
        seen = set()
        detected = [d for d in detected if not (d in seen or seen.add(d))]
        label = detected[0]
        confidence = "HIGH" if penalty >= 0.3 else "MEDIUM"
    elif not producer and not creator:
        label = "Unknown — Producer/Creator metadata missing or stripped"
        confidence = "LOW"
    else:
        label = f"{producer or creator} (no known tampering-tool signature matched)"
        confidence = "LOW"

    return {
        "detected_source": label,
        "all_signatures_found": detected,
        "confidence": confidence,
        "evidence": evidence,
        "score_penalty": max(-0.10, penalty),
        "eof_marker_count": eof_count,
    }


# --------------------------------------------------------------------------
# Report builder
# --------------------------------------------------------------------------

def _build_report_text(file_kind: str, verdict: str, fraud_score: float,
                        source_analysis: dict, extra_flags: list,
                        page_summaries: list = None) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("DeepVerif.AI — Document Forensic Report")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"File type analyzed: {file_kind}")
    lines.append("")
    lines.append(f"VERDICT: {verdict}")
    lines.append(f"Overall fraud score: {fraud_score}%")
    lines.append("")
    lines.append("-- Likely source / provenance --")
    lines.append(f"Detected source: {source_analysis['detected_source']}")
    lines.append(f"Confidence: {source_analysis['confidence']}")
    if source_analysis["evidence"]:
        lines.append("Evidence:")
        for e in source_analysis["evidence"]:
            lines.append(f"  - {e}")
    lines.append("")
    if extra_flags:
        lines.append("-- Additional flags --")
        for f in extra_flags:
            lines.append(f"  - {f}")
        lines.append("")
    if page_summaries:
        lines.append("-- Per-page Error Level Analysis --")
        for p in page_summaries:
            lines.append(f"  Page {p['page']}: suspicious area {p['suspicious_area_pct']}%, error variance {p['error_std']}")
        lines.append("")
    lines.append("-- Honest limitations --")
    lines.append("  ELA flags compression inconsistency, which correlates with tampering")
    lines.append("  but is not proof by itself. Metadata can be stripped or forged by an")
    lines.append("  attacker, so 'source' is a best-effort signal, not a certainty.")
    lines.append("  Use this report as supporting evidence alongside manual review, not")
    lines.append("  as a sole basis for a legal/administrative decision.")
    lines.append("=" * 60)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def analyze_document(b64_image: str) -> dict:
    """Analyze a single uploaded image (JPG/PNG/etc.)."""
    raw = _decode_b64(b64_image)
    img = Image.open(io.BytesIO(raw))
    img_rgb = img.convert("RGB")

    pixel_result = _analyze_pixels(img_rgb)
    source_analysis = _image_source_analysis(img)

    metadata_flags = []
    if not source_analysis["evidence"]:
        pass
    metadata_flags.extend([e for e in source_analysis["evidence"]])

    fraud_score = _fuse_score(
        pixel_result["suspicious_area_pct"],
        pixel_result["error_std"],
        metadata_penalty=source_analysis["score_penalty"],
    )
    verdict = _verdict_for(fraud_score)

    report_text = _build_report_text("Image", verdict, fraud_score, source_analysis, [])

    return {
        "file_kind": "image",
        "verdict": verdict,
        "fraud_score": fraud_score,
        "suspicious_area_pct": pixel_result["suspicious_area_pct"],
        "error_std": pixel_result["error_std"],
        "metadata_flags": metadata_flags,
        "heatmap_image_b64": pixel_result["heatmap_image_b64"],
        "source_analysis": source_analysis,
        "report_text": report_text,
    }


def analyze_pdf(b64_pdf: str, dpi: int = 150, max_pages: int = 10) -> dict:
    """Analyze an uploaded PDF: renders each page and runs the same ELA
    pass on it, plus document-metadata / provenance fingerprinting."""
    if not PDF_SUPPORT:
        return {
            "error": (
                "PDF support requires the 'PyMuPDF' package. "
                "Install it with: pip install PyMuPDF"
            )
        }

    raw = _decode_b64(b64_pdf)
    doc = fitz.open(stream=raw, filetype="pdf")

    meta = dict(doc.metadata or {})
    meta["encryption"] = doc.metadata.get("encryption") if doc.metadata else None
    page_count = doc.page_count

    source_analysis = _pdf_source_analysis(meta, raw)

    pages_out = []
    worst_suspicious = 0.0
    worst_std = 0.0
    n_pages_to_scan = min(page_count, max_pages)

    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for i in range(n_pages_to_scan):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        page_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        pixel_result = _analyze_pixels(page_img)
        pages_out.append({
            "page": i + 1,
            "suspicious_area_pct": pixel_result["suspicious_area_pct"],
            "error_std": pixel_result["error_std"],
            "heatmap_image_b64": pixel_result["heatmap_image_b64"],
        })
        worst_suspicious = max(worst_suspicious, pixel_result["suspicious_area_pct"])
        worst_std = max(worst_std, pixel_result["error_std"])

    extra_flags = []
    if page_count > max_pages:
        extra_flags.append(f"PDF has {page_count} pages — only the first {max_pages} were scanned for performance")

    fraud_score = _fuse_score(worst_suspicious, worst_std, metadata_penalty=source_analysis["score_penalty"])
    verdict = _verdict_for(fraud_score)

    report_text = _build_report_text(
        "PDF", verdict, fraud_score, source_analysis, extra_flags, page_summaries=pages_out
    )

    doc.close()

    return {
        "file_kind": "pdf",
        "verdict": verdict,
        "fraud_score": fraud_score,
        "page_count": page_count,
        "pages": pages_out,
        "metadata": {
            "title": meta.get("title"),
            "author": meta.get("author"),
            "creator": meta.get("creator"),
            "producer": meta.get("producer"),
            "creationDate": meta.get("creationDate"),
            "modDate": meta.get("modDate"),
        },
        "metadata_flags": extra_flags,
        "source_analysis": source_analysis,
        "report_text": report_text,
    }
