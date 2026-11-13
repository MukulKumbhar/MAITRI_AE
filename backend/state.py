"""
MAITRI 2.0 — Singleton Shared Application State
Holds all runtime objects that must survive across FastAPI requests and WebSocket connections.
Thread-safe access via asyncio.Lock or threading.Lock depending on context.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Set

# ── Path Setup ────────────────────────────────────────────────────────────────
# Add project root to sys.path so modules/ resolves correctly from any cwd.
_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# ── Determine project root and DB path ────────────────────────────────────────
# Support PyInstaller: use sys._MEIPASS if frozen
_PROJECT_ROOT: Path = Path(getattr(sys, "_MEIPASS", str(_HERE)))

# ── Import MAITRI modules ─────────────────────────────────────────────────────
from modules.live_state import LiveState
from modules.fusion_module import FusionState
from modules.mission_core import NativeWatchdog, NativeDTNOutbox

# ─────────────────────────────────────────────────────────────────────────────
# Global singleton state container
# ─────────────────────────────────────────────────────────────────────────────

class AppState:
    """
    Central application state singleton.
    Instantiated once at startup; imported everywhere.
    """

    def __init__(self) -> None:
        # ── Live telemetry state ───────────────────────────────────────────
        self.live: LiveState = LiveState()
        self.fusion: FusionState = FusionState()

        # ── Mission control objects ────────────────────────────────────────
        self.watchdog: NativeWatchdog = NativeWatchdog(timeout_sec=45.0)
        self.dtn: NativeDTNOutbox = NativeDTNOutbox()

        # ── Current vitals (user-adjustable via WS or REST) ───────────────
        self.heart_rate: float = 75.0
        self.temperature: float = 36.6
        self.spo2: float = 98.0

        # ── Fusion mode ───────────────────────────────────────────────────
        self.manual_override: bool = False
        self.manual_face_ratio: float = 0.60  # 60% face, 40% voice

        # ── Mission profile ───────────────────────────────────────────────
        self.mission_name: str = "ISRO Gaganyaan (LEO)"
        self.active_crew: str = "Cdr. A. Sharma (Pilot / CMO)"
        self.dossier_md: Optional[str] = None

        # ── Audio / microphone settings ───────────────────────────────────
        self.mic_gain: float = 1.0
        self.silence_threshold: float = 0.03

        # ── WebSocket connection registries ───────────────────────────────
        # Active telemetry WebSocket connections (FastAPI WebSocket objects)
        self.telemetry_connections: Set = set()
        self.telemetry_connections_lock: asyncio.Lock = asyncio.Lock()

        # ── Auto-log flag ─────────────────────────────────────────────────
        self.auto_log_enabled: bool = False

        # ── Voice / ASR (Phase 3: populated by voice_service) ─────────────
        self.vosk_ready: bool = False

        # ── ONNX face model readiness ─────────────────────────────────────
        self.face_model_ready: bool = False

        # ── Mission catalog (latency in seconds) ──────────────────────────
        self.mission_catalog: dict = {
            "ISRO Gaganyaan (LEO)":         0.5,
            "Artemis Gateway (Lunar)":      2.4,
            "Mars Transit (Deep Space)":    420.0,
        }
        self.crew_list: list = [
            "Cdr. A. Sharma (Pilot / CMO)",
            "Lt. Cdr. P. Nair (Flight Engineer)",
            "Dr. V. Rao (Mission Specialist)",
        ]

    # ── Convenience helpers ────────────────────────────────────────────────────

    def get_project_root(self) -> Path:
        return _PROJECT_ROOT

    def get_db_path(self) -> str:
        """Return absolute path to the SQLite DB file."""
        return str(_PROJECT_ROOT / "maitri_logs.db")


# Global singleton — imported by all backend modules
_app_state: Optional[AppState] = None


def get_state() -> AppState:
    """Return the global AppState singleton, creating it if needed."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state


def reset_state() -> AppState:
    """Reset to a fresh AppState (used in tests only)."""
    global _app_state
    _app_state = AppState()
    return _app_state
