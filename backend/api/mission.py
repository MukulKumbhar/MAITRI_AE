"""
MAITRI 2.0 — Mission Control Router
GET  /api/mission/status          — current mission + crew + DTN
POST /api/mission/profile         — update mission / crew
POST /api/mission/dossier         — compile clinical dossier + DTN dispatch
GET  /api/mission/dossier/download — download dossier .md
"""

import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from backend.state import get_state

logger = logging.getLogger("maitri.api.mission")
router = APIRouter(prefix="/api/mission", tags=["mission"])


class MissionProfileRequest(BaseModel):
    mission: Optional[str] = None
    crew: Optional[str] = None


@router.get("/status")
async def get_mission_status():
    """Return current mission profile, active astronaut, and DTN queue status."""
    state = get_state()
    return {
        "mission": state.mission_name,
        "crew": state.active_crew,
        "dossier_compiled": state.dossier_md is not None,
        "dtn": {
            "latency_display": state.dtn.format_latency(),
            "latency_formatted": state.dtn.format_latency(),
            "latency_sec": state.dtn.latency_sec,
            "packet_count": len(state.dtn.packets),
            "queued_packets": len(state.dtn.packets),
            "packets": [
                {
                    "packet_id": p.packet_id,
                    "priority": p.priority,
                    "summary": p.summary,
                    "status": p.status,
                }
                for p in state.dtn.packets
            ],
        },
        "mission_catalog": state.mission_catalog,
        "crew_list": state.crew_list,
    }


@router.post("/profile")
async def update_profile(req: MissionProfileRequest):
    """Update the active mission profile and/or astronaut selection."""
    state = get_state()

    if req.mission and req.mission in state.mission_catalog:
        state.mission_name = req.mission
        latency = state.mission_catalog[req.mission]
        state.dtn.set_mission(req.mission, latency)

    if req.crew and req.crew in state.crew_list:
        state.active_crew = req.crew

    return {
        "status": "updated",
        "mission": state.mission_name,
        "crew": state.active_crew,
        "dtn_latency": state.dtn.format_latency(),
    }


@router.post("/dossier")
async def compile_dossier():
    """Compile a Markdown clinical dossier and queue a DTN dispatch packet."""
    state = get_state()

    try:
        from modules.mission_core import compile_native_dossier
        # Build dossier with current telemetry
        stress_pct = getattr(state.fusion, "last_stress", 0.0)
        md = compile_native_dossier(
            crew=state.active_crew,
            mission=state.mission_name,
            hrm=state.heart_rate,
            spo2=state.spo2,
            stress=stress_pct,
        )
        state.dossier_md = md

        # Dispatch DTN packet
        import time
        pkt_id = f"AUDIT-{int(time.time()) % 10000:04d}"
        state.dtn.dispatch(
            pkt_id=pkt_id,
            priority="HIGH",
            summary=f"Clinical dossier for {state.active_crew} — Stress: {stress_pct:.1f}%",
        )

        return {
            "markdown": md,
            "download_url": "/api/mission/dossier/download",
            "packet_id": pkt_id,
        }
    except Exception as exc:
        logger.error("Dossier compile error: %s", exc)
        return {"error": str(exc)}


@router.get("/dossier/download")
async def download_dossier():
    """Download the compiled dossier as a .md file."""
    state = get_state()
    if not state.dossier_md:
        return Response(
            content="No dossier compiled yet. Use POST /api/mission/dossier first.",
            media_type="text/plain",
            status_code=404,
        )
    return Response(
        content=state.dossier_md,
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=Medical_Dossier.md"},
    )
