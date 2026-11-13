"""
MAITRI 2.0 — Telemetry Service
Runs the continuous fusion loop in the FastAPI background, broadcasting
computed state at 10 Hz to all connected WebSocket clients.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict

from backend.state import get_state

# Import MAITRI ML modules
from modules.vitals_module import compute_vitals_strain
from modules.fusion_module import fuse
from modules.alert_module import get_alert
from modules.database_module import log_event

logger = logging.getLogger("maitri.telemetry")

# Target telemetry broadcast rate
_TARGET_HZ: float = 10.0
_INTERVAL: float = 1.0 / _TARGET_HZ


def _build_telemetry_payload(state) -> Dict[str, Any]:
    """
    Build a full telemetry JSON payload by running the fusion pipeline.
    This mirrors what app.py does on each Streamlit rerun, but in async FastAPI.
    """
    # ── 1. Snapshot latest live sensor state ──────────────────────────────
    face_snap = state.live.snapshot_face()
    voice_snap = state.live.snapshot_voice()

    # ── 2. Vitals strain ──────────────────────────────────────────────────
    vitals_result = compute_vitals_strain(
        heart_rate=state.heart_rate,
        temperature=state.temperature,
        spo2=state.spo2,
    )

    # ── 3. Multimodal fusion ──────────────────────────────────────────────
    fusion_result = fuse(
        state=state.fusion,
        face_probs=face_snap["emotion_probs"],
        face_quality=face_snap["face_quality"],
        vitals_strain=vitals_result.vitals_strain,
        fatigue_strain=face_snap["fatigue_strain"],
        eye_quality=float(face_snap["eye_available"]),
        voice_probs=voice_snap["voice_probs"] if voice_snap["is_speaking"] else None,
        voice_quality=voice_snap["voice_quality"],
        is_speaking=voice_snap["is_speaking"],
        manual_override=state.manual_override,
        manual_face_ratio=state.manual_face_ratio,
    )

    # ── 4. Alert engine ───────────────────────────────────────────────────
    alert_result = get_alert(
        stress_pct=fusion_result.stress_pct,
        dominant_emotion=fusion_result.dominant_emotion,
        fatigue_label=face_snap["fatigue_label"],
    )

    # ── 5. Watchdog update ────────────────────────────────────────────────
    watchdog_status = state.watchdog.update(
        is_speaking=voice_snap["is_speaking"],
        ear=face_snap["ear"],
        face_quality=face_snap["face_quality"],
    )

    # ── 6. Auto-log if enabled ────────────────────────────────────────────
    if state.auto_log_enabled:
        try:
            log_event(
                face_emotion=face_snap["face_emotion"],
                fused_emotion=fusion_result.dominant_emotion,
                voice_state="speaking" if voice_snap["is_speaking"] else "silent",
                heart_rate=state.heart_rate,
                temperature=state.temperature,
                spo2=state.spo2,
                blink_rate=face_snap["blink_rate"],
                fatigue_label=face_snap["fatigue_label"],
                stress_score=fusion_result.stress_pct,
                stress_level=alert_result.stress_level,
                alert_triggered=alert_result.header,
                response_msg=alert_result.body,
                emotion_probs=fusion_result.fused_probs,
            )
        except Exception as exc:
            logger.debug("Auto-log error: %s", exc)

    # ── 7. Assemble canonical payload (matches Section 2.3 schema) ────────
    voice_rms = voice_snap["voice_rms"]
    voice_db = round(20 * __import__("math").log10(max(voice_rms, 1e-9)), 1) if voice_rms > 0 else -90.0

    return {
        "type": "telemetry_update",
        "timestamp": time.time(),
        "face": {
            "emotion": face_snap["face_emotion"],
            "confidence": round(face_snap["face_confidence"], 4),
            "quality": round(face_snap["face_quality"], 4),
            "is_blurry": face_snap["is_blurry"],
            "blur_score": round(face_snap["blur_score"], 2),
            "probs": {k: round(v, 4) for k, v in face_snap["emotion_probs"].items()},
        },
        "eye": {
            "ear": round(face_snap["ear"], 4),
            "blink_rate": round(face_snap["blink_rate"], 2),
            "fatigue_label": face_snap["fatigue_label"],
            "fatigue_strain": round(face_snap["fatigue_strain"], 4),
            "frame_count": face_snap["frame_count"],
            "eye_available": face_snap.get("eye_available", True),
        },
        "voice": {
            "emotion": voice_snap["voice_emotion"],
            "confidence": round(voice_snap["voice_confidence"], 4),
            "is_speaking": voice_snap["is_speaking"],
            "rms": round(voice_snap["voice_rms"], 6),
            "db": voice_db,
            "probs": {k: round(v, 4) for k, v in voice_snap["voice_probs"].items()},
        },
        "vitals": {
            "heart_rate": state.heart_rate,
            "temperature": state.temperature,
            "spo2": state.spo2,
            "hr_strain": round(vitals_result.hr_strain, 4),
            "temp_strain": round(vitals_result.temp_strain, 4),
            "spo2_strain": round(vitals_result.spo2_strain, 4),
            "composite_strain": round(vitals_result.vitals_strain, 4),
            "status": vitals_result.status,
        },
        "fusion": {
            "stress_pct": fusion_result.stress_pct,
            "stress_level": alert_result.stress_level,
            "dominant_emotion": fusion_result.dominant_emotion,
            "weights": {
                "face": round(fusion_result.face_weight, 4),
                "voice": round(fusion_result.voice_weight, 4),
                "vitals": round(fusion_result.vitals_weight, 4),
                "eye": round(fusion_result.eye_weight, 4),
            },
            "fused_probs": {k: round(v, 4) for k, v in fusion_result.fused_probs.items()},
            "is_speaking": fusion_result.is_speaking,
            "manual_override": state.manual_override,
            "manual_face_ratio": state.manual_face_ratio,
        },
        "alert": {
            "level": alert_result.stress_level,
            "icon": alert_result.icon,
            "color": alert_result.color,
            "header": alert_result.header,
            "body": alert_result.body,
            "technique": alert_result.technique,
        },
        "watchdog": {
            "state": watchdog_status.state,
            "countdown": _get_watchdog_countdown(state.watchdog),
            "message": watchdog_status.alert_message,
        },
        "settings": {
            "mic_gain": state.mic_gain,
            "silence_threshold": state.silence_threshold,
        },
    }


def _get_watchdog_countdown(watchdog) -> int:
    """Calculate remaining seconds in watchdog check-in window."""
    import time as _time
    if watchdog.state == "CHECK_IN":
        elapsed = _time.time() - watchdog.last_activity_time
        return max(0, int((watchdog.timeout_sec + 15.0) - elapsed))
    return 0


async def telemetry_broadcast_loop() -> None:
    """
    Background task: runs continuously, building telemetry payloads and
    broadcasting to all connected WebSocket clients at 10 Hz.
    """
    state = get_state()
    logger.info("Telemetry broadcast loop started at %.0f Hz", _TARGET_HZ)

    while True:
        t0 = time.monotonic()

        try:
            payload = _build_telemetry_payload(state)
            payload_json = json.dumps(payload)

            # Broadcast to all connected WebSocket clients
            async with state.telemetry_connections_lock:
                dead_conns = set()
                for ws in state.telemetry_connections:
                    try:
                        await ws.send_text(payload_json)
                    except Exception:
                        dead_conns.add(ws)
                state.telemetry_connections -= dead_conns

        except Exception as exc:
            logger.warning("Telemetry loop error: %s", exc)

        # Sleep remainder of interval to maintain target rate
        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, _INTERVAL - elapsed))
