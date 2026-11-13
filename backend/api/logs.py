"""
MAITRI 2.0 — Logs Router
GET  /api/logs            — paginated telemetry history
POST /api/logs            — log a manual snapshot
GET  /api/logs/trends     — recent 7-affect trajectory for charts
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.state import get_state

logger = logging.getLogger("maitri.api.logs")
router = APIRouter(prefix="/api/logs", tags=["logs"])


class LogEntryRequest(BaseModel):
    face_emotion: str = "neutral"
    fused_emotion: str = "neutral"
    voice_state: str = "silent"
    heart_rate: float = 75.0
    temperature: float = 36.6
    spo2: float = 98.0
    blink_rate: float = 0.0
    fatigue_label: str = "Normal"
    stress_score: float = 0.0
    stress_level: str = "NOMINAL"
    alert_triggered: str = ""
    response_msg: str = ""
    emotion_probs: Optional[Dict[str, float]] = None
    prob_angry: Optional[float] = None
    prob_disgust: Optional[float] = None
    prob_fear: Optional[float] = None
    prob_happy: Optional[float] = None
    prob_neutral: Optional[float] = None
    prob_sad: Optional[float] = None
    prob_surprise: Optional[float] = None
    rmssd: Optional[float] = 42.0
    sdnn: Optional[float] = 55.0
    baevsky_index: Optional[float] = 95.0
    respiratory_rate: Optional[float] = 14.0
    co2_mmhg: Optional[float] = 3.0
    o2_percent: Optional[float] = 20.9
    pressure_kpa: Optional[float] = 101.3
    ambient_temp_c: Optional[float] = 22.0
    noise_dba: Optional[float] = 58.0


@router.get("")
async def get_logs(
    limit: int = Query(default=200, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
):
    """Return paginated telemetry log records (newest first)."""
    try:
        from modules.database_module import get_logs
        df = get_logs()
        total = len(df)
        page = df.iloc[offset : offset + limit]
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "records": page.to_dict(orient="records"),
        }
    except Exception as exc:
        logger.error("get_logs error: %s", exc)
        return {"total": 0, "offset": offset, "limit": limit, "records": [], "error": str(exc)}


@router.post("")
async def post_log(entry: LogEntryRequest):
    """Manually log a telemetry snapshot to SQLite."""
    try:
        from modules.database_module import log_event
        probs = dict(entry.emotion_probs) if entry.emotion_probs else {}
        for emo in ("angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"):
            val = getattr(entry, f"prob_{emo}", None)
            if val is not None and emo not in probs:
                probs[emo] = float(val)
        if not probs:
            probs = None

        prev_h, rec_h = log_event(
            face_emotion=entry.face_emotion,
            fused_emotion=entry.fused_emotion,
            voice_state=entry.voice_state,
            heart_rate=entry.heart_rate,
            temperature=entry.temperature,
            spo2=entry.spo2,
            blink_rate=entry.blink_rate,
            fatigue_label=entry.fatigue_label,
            stress_score=entry.stress_score,
            stress_level=entry.stress_level,
            alert_triggered=entry.alert_triggered,
            response_msg=entry.response_msg,
            emotion_probs=probs,
            rmssd=entry.rmssd if entry.rmssd is not None else 42.0,
            sdnn=entry.sdnn if entry.sdnn is not None else 55.0,
            baevsky_index=entry.baevsky_index if entry.baevsky_index is not None else 95.0,
            respiratory_rate=entry.respiratory_rate if entry.respiratory_rate is not None else 14.0,
            co2_mmhg=entry.co2_mmhg if entry.co2_mmhg is not None else 3.0,
            o2_percent=entry.o2_percent if entry.o2_percent is not None else 20.9,
            pressure_kpa=entry.pressure_kpa if entry.pressure_kpa is not None else 101.3,
            ambient_temp_c=entry.ambient_temp_c if entry.ambient_temp_c is not None else 22.0,
            noise_dba=entry.noise_dba if entry.noise_dba is not None else 58.0,
        )
        state = get_state()
        if hasattr(state, "hash_chain"):
            state.hash_chain.current_hash = rec_h
            state.hash_chain.entry_count += 1
        return {"status": "logged", "record_hash": rec_h, "prev_hash": prev_h}
    except Exception as exc:
        logger.error("post_log error: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/alarms")
async def get_alarm_logs(
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Return IEC 60601-1-8 alarm events ledger from SQLite."""
    try:
        import pandas as pd
        from modules.database_module import get_alarm_events
        df = get_alarm_events(limit=limit)
        records = [
            {k: (None if pd.isna(v) else v) for k, v in r.items()}
            for r in df.to_dict(orient="records")
        ] if not df.empty else []
        return {
            "total": len(df),
            "records": records,
        }
    except Exception as exc:
        logger.error("get_alarm_logs error: %s", exc)
        return {"total": 0, "records": [], "error": str(exc)}


@router.get("/verify_chain")
async def verify_chains():
    """Verify cryptographic SHA-256 hash chains for telemetry and alarm logs."""
    try:
        from modules.database_module import verify_stress_logs_hash_chain, verify_alarm_events_hash_chain
        stress_valid, stress_err_idx = verify_stress_logs_hash_chain()
        alarm_valid, alarm_err_idx = verify_alarm_events_hash_chain()
        return {
            "status": "verified" if (stress_valid and alarm_valid) else "corrupted",
            "stress_logs": {"valid": stress_valid, "failing_id": stress_err_idx},
            "alarm_events": {"valid": alarm_valid, "failing_id": alarm_err_idx},
        }
    except Exception as exc:
        logger.error("verify_chains error: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/trends")
async def get_trends(n: int = Query(default=60, ge=1, le=500)):
    """
    Return last n records with 7-class emotion probabilities for multi-line charts.
    Matches the data shape expected by the React frontend charts.
    """
    try:
        from modules.database_module import get_recent_trend
        df = get_recent_trend(n)
        if df.empty:
            return {"records": [], "count": 0}

        records = df.to_dict(orient="records")

        # Compute summary statistics
        stress_values = [r.get("stress_score", 0.0) for r in records if r.get("stress_score") is not None]
        emotions = [r.get("fused_emotion", "neutral") for r in records if r.get("fused_emotion")]

        dominant = max(set(emotions), key=emotions.count) if emotions else "neutral"
        affect_switches = sum(
            1 for i in range(1, len(emotions)) if emotions[i] != emotions[i - 1]
        )

        return {
            "records": records,
            "count": len(records),
            "summary": {
                "dominant_affect": dominant,
                "affect_switches": affect_switches,
                "peak_confidence": max(
                    [r.get(f"prob_{dominant.lower()}", 0.0) for r in records] or [0.0]
                ),
                "mean_stress": round(sum(stress_values) / len(stress_values), 2) if stress_values else 0.0,
            },
        }
    except Exception as exc:
        logger.error("get_trends error: %s", exc)
        return {"records": [], "count": 0, "error": str(exc)}
