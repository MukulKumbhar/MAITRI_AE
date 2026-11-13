"""
MAITRI 2.0 — Watchdog Router
POST /api/watchdog/ack      — acknowledge / cancel emergency
POST /api/watchdog/simulate — force CHECK_IN state for demos
GET  /api/watchdog/status   — current watchdog state
"""

import logging

from fastapi import APIRouter

from backend.state import get_state

logger = logging.getLogger("maitri.api.watchdog")
router = APIRouter(prefix="/api/watchdog", tags=["watchdog"])


@router.get("/status")
async def get_watchdog_status():
    """Return current watchdog state and countdown."""
    state = get_state()
    import time
    elapsed = time.time() - state.watchdog.last_activity_time
    countdown = max(0, int((state.watchdog.timeout_sec + 15.0) - elapsed))
    return {
        "state": state.watchdog.state,
        "countdown": countdown if state.watchdog.state == "CHECK_IN" else 0,
        "message": (
            f"ASTRONAUT INACTIVITY DETECTED. CHECK-IN REQUIRED WITHIN {countdown}s."
            if state.watchdog.state == "CHECK_IN"
            else "SYSTEM INCAPACITATION PROTOCOL ENGAGED."
            if state.watchdog.state == "INCAPACITATED"
            else ""
        ),
    }


@router.post("/ack")
async def acknowledge_watchdog():
    """
    Acknowledge watchdog alert.
    Resets timer and returns state to NORMAL.
    """
    state = get_state()
    state.watchdog.acknowledge()
    return {"state": state.watchdog.state, "message": "Watchdog acknowledged."}


@router.post("/simulate")
async def simulate_watchdog():
    """
    Force watchdog into CHECK_IN state.
    Used for demo/testing to verify alert UI without waiting 45 seconds.
    """
    state = get_state()
    state.watchdog.trigger_simulation()
    return {"state": state.watchdog.state, "message": "Watchdog simulation triggered."}
