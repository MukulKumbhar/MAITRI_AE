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

        log_event(
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
        )
        return {"status": "logged"}
    except Exception as exc:
        logger.error("post_log error: %s", exc)
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
