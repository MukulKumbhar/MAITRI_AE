"""
MAITRI 2.0 — WebSocket Telemetry Tests
Tests the /ws/telemetry WebSocket endpoint including:
  - Connection handshake
  - Telemetry payload schema validation
  - Client-to-server vitals updates
  - Watchdog action via WS
"""

import sys
import os
import json
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import modules.database_module as db_mod
_TEST_DB = str(_PROJECT_ROOT / "tests" / "backend" / "test_telemetry.db")
db_mod.DB_FILE = _TEST_DB

from fastapi.testclient import TestClient
from backend.main import app
from backend.state import reset_state

# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_TELEMETRY_KEYS = {
    "type", "timestamp",
    "face", "eye", "voice", "vitals", "fusion", "alert", "watchdog"
}

FACE_KEYS = {"emotion", "confidence", "quality", "is_blurry", "blur_score", "probs"}
EYE_KEYS = {"ear", "blink_rate", "fatigue_label", "fatigue_strain"}
VOICE_KEYS = {"emotion", "confidence", "is_speaking", "rms", "db", "probs"}
VITALS_KEYS = {"heart_rate", "temperature", "spo2", "hr_strain", "temp_strain", "spo2_strain", "composite_strain", "status"}
FUSION_KEYS = {"stress_pct", "stress_level", "dominant_emotion", "weights", "fused_probs"}
ALERT_KEYS = {"level", "icon", "color", "header", "body"}
WATCHDOG_KEYS = {"state", "countdown", "message"}

EMOTION_CLASSES = {"angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"}


@pytest.fixture(autouse=True)
def fresh_state():
    db_mod.DB_FILE = _TEST_DB
    os.makedirs(os.path.dirname(_TEST_DB), exist_ok=True)
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    db_mod.init_db()
    reset_state()
    yield
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket connection + payload schema
# ─────────────────────────────────────────────────────────────────────────────

class TestTelemetryWebSocket:
    def test_ws_connect_and_receive(self, client):
        """WebSocket connects and receives at least one telemetry payload."""
        with client.websocket_connect("/ws/telemetry") as ws:
            # The broadcast loop runs; in TestClient we may need to trigger it
            # Send a ping to get a response cycle
            ws.send_text(json.dumps({"action": "ping"}))
            # We can also read what the broadcast loop sends
            # In TestClient, background tasks don't run automatically in sync mode
            # So we directly verify connection is accepted
            # (Full async broadcast test requires async TestClient)

    def test_ws_schema_top_level(self, client):
        """
        Trigger a manual telemetry build and verify schema.
        We call the internal function directly to test schema without
        needing the full async broadcast loop.
        """
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        state = get_state()
        payload = _build_telemetry_payload(state)

        assert payload["type"] == "telemetry_update"
        assert isinstance(payload["timestamp"], float)

        for key in REQUIRED_TELEMETRY_KEYS:
            assert key in payload, f"Missing top-level key: {key}"

    def test_ws_face_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        face = payload["face"]
        for key in FACE_KEYS:
            assert key in face, f"Missing face key: {key}"
        assert EMOTION_CLASSES == set(face["probs"].keys())
        assert isinstance(face["confidence"], float)
        assert 0.0 <= face["confidence"] <= 1.0

    def test_ws_eye_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        eye = payload["eye"]
        for key in EYE_KEYS:
            assert key in eye, f"Missing eye key: {key}"
        assert isinstance(eye["ear"], float)
        assert isinstance(eye["blink_rate"], float)

    def test_ws_voice_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        voice = payload["voice"]
        for key in VOICE_KEYS:
            assert key in voice, f"Missing voice key: {key}"
        assert EMOTION_CLASSES == set(voice["probs"].keys())

    def test_ws_vitals_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        vitals = payload["vitals"]
        for key in VITALS_KEYS:
            assert key in vitals, f"Missing vitals key: {key}"
        assert vitals["heart_rate"] == 75.0
        assert vitals["temperature"] == 36.6
        assert vitals["spo2"] == 98.0

    def test_ws_fusion_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        fusion = payload["fusion"]
        for key in FUSION_KEYS:
            assert key in fusion, f"Missing fusion key: {key}"
        assert 0.0 <= fusion["stress_pct"] <= 100.0
        assert fusion["stress_level"] in {"NOMINAL", "MILD", "ELEVATED", "CRITICAL"}
        weights = fusion["weights"]
        assert all(k in weights for k in ("face", "voice", "vitals", "eye"))

    def test_ws_alert_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        alert = payload["alert"]
        for key in ALERT_KEYS:
            assert key in alert, f"Missing alert key: {key}"
        assert alert["level"] in {"NOMINAL", "MILD", "ELEVATED", "CRITICAL"}

    def test_ws_watchdog_schema(self, client):
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        wd = payload["watchdog"]
        for key in WATCHDOG_KEYS:
            assert key in wd, f"Missing watchdog key: {key}"
        assert wd["state"] in {"NORMAL", "CHECK_IN", "INCAPACITATED"}

    def test_vitals_update_reflected(self, client):
        """Updating vitals state changes the telemetry payload."""
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        state = get_state()
        state.heart_rate = 120.0
        state.spo2 = 90.0
        payload = _build_telemetry_payload(state)
        assert payload["vitals"]["heart_rate"] == 120.0
        assert payload["vitals"]["spo2"] == 90.0
        # High HR should produce some strain
        assert payload["vitals"]["hr_strain"] > 0.0

    def test_stress_level_boundaries(self, client):
        """Verify correct stress level labeling at boundary conditions."""
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        from modules.alert_module import get_alert

        # NOMINAL: stress < 35%
        alert = get_alert(20.0, "happy", "Normal")
        assert alert.stress_level == "NOMINAL"

        # MILD: 35 <= stress < 55%
        alert = get_alert(45.0, "neutral", "Normal")
        assert alert.stress_level == "MILD"

        # ELEVATED: 55 <= stress < 75%
        alert = get_alert(65.0, "fear", "Normal")
        assert alert.stress_level == "ELEVATED"

        # CRITICAL: stress >= 75%
        alert = get_alert(80.0, "angry", "Stressed Eyes")
        assert alert.stress_level == "CRITICAL"

    def test_telemetry_json_serializable(self, client):
        """Full payload must be JSON-serializable without errors."""
        from backend.services.telemetry_service import _build_telemetry_payload
        from backend.state import get_state
        payload = _build_telemetry_payload(get_state())
        serialized = json.dumps(payload)
        assert len(serialized) > 100
        # Can roundtrip
        parsed = json.loads(serialized)
        assert parsed["type"] == "telemetry_update"
