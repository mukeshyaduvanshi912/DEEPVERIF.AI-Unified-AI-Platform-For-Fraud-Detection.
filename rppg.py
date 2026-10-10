"""
rppg.py — Remote Photoplethysmography (rPPG) based Liveness Detection
Real human skin shows tiny, periodic colour changes in the face caused by
blood pulsing under the skin with every heartbeat. A photo, screen-replay,
or most deepfake video streams do NOT reproduce this true physiological
signal convincingly. We:
  1. Detect the face in every frame (Haar cascade).
  2. Track the mean GREEN channel intensity of the forehead/cheek ROI
     across frames (green channel carries the strongest pulse signal).
  3. Detrend + bandpass-filter the resulting signal to the plausible
     human heart-rate band (42-180 BPM -> 0.7-3.0 Hz).
  4. Take an FFT; a strong, narrow peak in that band = a real pulse
     present -> REAL. A flat / noisy / out-of-band spectrum -> FAKE.
"""
import base64
import cv2
import numpy as np
from scipy.signal import butter, filtfilt

FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

MIN_HZ, MAX_HZ = 0.7, 3.0  # 42-180 BPM


def _decode_frame(b64_str: str):
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    data = base64.b64decode(b64_str)
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def _forehead_roi(frame, face_box):
    x, y, w, h = face_box
    # forehead/upper-cheek strip: good pulsatile signal, avoids eyes/mouth motion
    rx, ry = x + int(0.25 * w), y + int(0.10 * h)
    rw, rh = int(0.5 * w), int(0.25 * h)
    return frame[ry:ry + rh, rx:rx + rw]


def _bandpass(signal, fps):
    if len(signal) < 10:
        return signal
    nyq = 0.5 * fps
    low, high = MIN_HZ / nyq, min(MAX_HZ / nyq, 0.99)
    if low <= 0 or low >= high:
        return signal - np.mean(signal)
    b, a = butter(3, [low, high], btype="band")
    try:
        return filtfilt(b, a, signal - np.mean(signal))
    except Exception:
        return signal - np.mean(signal)


def _analyze_core(b64_frames: list, fps: float = 10.0, min_face: int = 80) -> dict:
    """Core rPPG pipeline: takes a list of base64 JPEG frames captured at ~fps."""
    green_signal = []
    face_found = 0
    frame_variances = []

    for b64 in b64_frames:
        frame = _decode_frame(b64)
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(min_face, min_face))
        if len(faces) == 0:
            continue
        face_found += 1
        face_box = max(faces, key=lambda f: f[2] * f[3])  # largest face
        roi = _forehead_roi(frame, face_box)
        if roi.size == 0:
            continue
        green_signal.append(float(np.mean(roi[:, :, 1])))
        frame_variances.append(float(np.var(gray)))

    n = len(green_signal)
    if n < 15 or face_found < max(5, int(0.3 * len(b64_frames))):
        return {
            "status": "INCONCLUSIVE",
            "reason": "Face not tracked consistently — move closer / better lighting",
            "frames_used": n,
        }

    sig = np.array(green_signal)
    filtered = _bandpass(sig, fps)

    # FFT power spectrum
    freqs = np.fft.rfftfreq(len(filtered), d=1.0 / fps)
    power = np.abs(np.fft.rfft(filtered)) ** 2
    band_mask = (freqs >= MIN_HZ) & (freqs <= MAX_HZ)

    if not np.any(band_mask) or power.sum() == 0:
        peak_ratio = 0.0
        bpm = 0.0
    else:
        band_power = power[band_mask]
        band_freqs = freqs[band_mask]
        peak_idx = int(np.argmax(band_power))
        peak_freq = band_freqs[peak_idx]
        bpm = float(peak_freq * 60.0)
        peak_ratio = float(band_power[peak_idx] / (power.sum() + 1e-8))

    # Static-image / screen-replay heuristic: near-zero natural micro-variance
    avg_variance = float(np.mean(frame_variances)) if frame_variances else 0.0

    # Decision logic
    is_live_pulse = peak_ratio > 0.15 and 42 <= bpm <= 180
    is_static = avg_variance < 5.0

    if is_static:
        status = "FAKE"
        confidence = 0.90
        reason = "Frame shows almost no natural micro-variation — likely a static photo or screen replay"
    elif is_live_pulse:
        status = "REAL"
        confidence = min(0.55 + peak_ratio, 0.97)
        reason = f"Consistent physiological pulse signal detected (~{bpm:.0f} BPM)"
    else:
        status = "FAKE"
        confidence = min(0.55 + (0.15 - peak_ratio), 0.95)
        reason = "No consistent blood-flow pulse signal found in facial region — possible deepfake/spoof"

    return {
        "status": status,
        "confidence": round(confidence, 2),
        "estimated_bpm": round(bpm, 1),
        "peak_band_power_ratio": round(peak_ratio, 3),
        "frames_used": n,
        "reason": reason,
    }


SCREEN_CAVEAT = ("Video captured from a screen / video call is already compressed, which erases the faint pulse signal "
                 "even for real people. Treat this result as a weak hint and rely on the Shield + Payment Guard.")


def adapt_for_screen(result: dict) -> dict:
    """Screen-captured video: a MISSING pulse is weak evidence, a DETECTED pulse is still good evidence."""
    r = dict(result)
    r["source"] = "screen"
    r["caveat"] = SCREEN_CAVEAT
    if r.get("status") == "FAKE":
        r["status"] = "SUSPICIOUS"
        r["confidence"] = round(min(r.get("confidence", 0.5), 0.6), 2)
        r["reason"] = "Pulse not detected in the caller's face (weak evidence on screen video). " + r.get("reason", "")
    return r


def analyze_frames(b64_frames: list, fps: float = 10.0, source: str = "camera") -> dict:
    """Main entry point. source='camera' (own face, webcam) or 'screen' (caller's face captured via screen share)."""
    if source == "screen":
        # faces are smaller inside a call window, so allow a smaller minimum face size
        return adapt_for_screen(_analyze_core(b64_frames, fps=fps, min_face=56))
    out = _analyze_core(b64_frames, fps=fps, min_face=80)
    out["source"] = "camera"
    return out
