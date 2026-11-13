"""
MAITRI 2.0 — Backend REST API Tests
Tests all /api/* endpoints using FastAPI TestClient.
"""

import sys
import os
from pathlib import Path

import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── Patch DB path before any imports ─────────────────────────────────────────
import modules.database_module as db_mod
_TEST_DB = str(_PROJECT_ROOT / "tests" / "backend" / "test_maitri.db")
db_mod.DB_FILE = _TEST_DB

# ── Import after path/db setup ────────────────────────────────────────────────
from fastapi.testclient import TestClient
from backend.main import app
from backend.state import reset_state

# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_state():
    """Reset app state and use a fresh test DB for each test."""
    db_mod.DB_FILE = _TEST_DB
    # Ensure test DB directory exists
    os.makedirs(os.path.dirname(_TEST_DB), exist_ok=True)
    # Remove leftover test DB
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    db_mod.init_db()
    reset_state()
    yield
    # Cleanup
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)


@pytest.fixture
def client():
    """Return a synchronous TestClient (no lifespan events in tests)."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "models_loaded" in data
        assert "models_on_disk" in data
        assert "version" in data

    def test_health_contains_mission(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "mission" in data
        assert "crew" in data


# ─────────────────────────────────────────────────────────────────────────────
# Logs
# ─────────────────────────────────────────────────────────────────────────────

class TestLogs:
    def test_get_logs_empty(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert data["total"] == 0

    def test_post_log(self, client):
        payload = {
            "face_emotion": "happy",
            "fused_emotion": "happy",
            "voice_state": "speaking",
            "heart_rate": 80.0,
            "temperature": 36.8,
            "spo2": 97.0,
            "blink_rate": 15.0,
            "fatigue_label": "Normal",
            "stress_score": 25.5,
            "stress_level": "NOMINAL",
            "alert_triggered": "All Systems Nominal",
            "response_msg": "Continue mission.",
            "emotion_probs": {
                "angry": 0.0, "disgust": 0.0, "fear": 0.0,
                "happy": 0.85, "neutral": 0.15, "sad": 0.0, "surprise": 0.0
            }
        }
        resp = client.post("/api/logs", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged"

    def test_post_then_get_log(self, client):
        client.post("/api/logs", json={
            "face_emotion": "neutral",
            "stress_score": 30.0,
            "stress_level": "NOMINAL",
        })
        resp = client.get("/api/logs")
        assert resp.json()["total"] == 1
        record = resp.json()["records"][0]
        assert record["face_emotion"] == "neutral"
        assert record["stress_score"] == 30.0

    def test_get_trends_empty(self, client):
        resp = client.get("/api/logs/trends")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert data["count"] == 0

    def test_get_trends_with_data(self, client):
        # Insert a few records
        for i in range(5):
            client.post("/api/logs", json={
                "face_emotion": "happy",
                "fused_emotion": "happy",
                "stress_score": float(20 + i),
                "stress_level": "NOMINAL",
            })
        resp = client.get("/api/logs/trends?n=5")
        data = resp.json()
        assert data["count"] == 5
        assert "summary" in data

    def test_logs_pagination(self, client):
        # Insert 10 records
        for i in range(10):
            client.post("/api/logs", json={"stress_score": float(i)})
        resp = client.get("/api/logs?limit=3&offset=0")
        data = resp.json()
        assert data["total"] == 10
        assert len(data["records"]) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Watchdog
# ─────────────────────────────────────────────────────────────────────────────

class TestWatchdog:
    def test_watchdog_initial_normal(self, client):
        resp = client.get("/api/watchdog/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "NORMAL"

    def test_watchdog_simulate(self, client):
        resp = client.post("/api/watchdog/simulate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "CHECK_IN"

    def test_watchdog_ack_after_simulate(self, client):
        client.post("/api/watchdog/simulate")
        resp = client.post("/api/watchdog/ack")
        assert resp.status_code == 200
        assert resp.json()["state"] == "NORMAL"

    def test_watchdog_status_after_simulate(self, client):
        client.post("/api/watchdog/simulate")
        resp = client.get("/api/watchdog/status")
        data = resp.json()
        assert data["state"] == "CHECK_IN"


# ─────────────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────────────

class TestSettings:
    def test_get_settings_defaults(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mic_gain"] == 1.0
        assert data["silence_threshold"] == 0.03
        assert data["manual_override"] is False

    def test_update_mic_gain(self, client):
        resp = client.post("/api/settings", json={"mic_gain": 2.0})
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"
        assert resp.json()["updated"]["mic_gain"] == 2.0

    def test_update_manual_override(self, client):
        resp = client.post("/api/settings", json={"manual_override": True, "manual_face_ratio": 0.7})
        assert resp.status_code == 200
        updated = resp.json()["updated"]
        assert updated["manual_override"] is True
        assert updated["manual_face_ratio"] == 0.7

    def test_mic_gain_clamping(self, client):
        # Above max should clamp to 3.0
        resp = client.post("/api/settings", json={"mic_gain": 10.0})
        assert resp.json()["updated"]["mic_gain"] == 3.0
        # Below min should clamp to 0.5
        resp = client.post("/api/settings", json={"mic_gain": 0.1})
        assert resp.json()["updated"]["mic_gain"] == 0.5

    def test_auto_log_toggle(self, client):
        resp = client.post("/api/settings", json={"auto_log_enabled": True})
        assert resp.json()["updated"]["auto_log_enabled"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Mission
# ─────────────────────────────────────────────────────────────────────────────

class TestMission:
    def test_get_mission_status(self, client):
        resp = client.get("/api/mission/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "mission" in data
        assert "crew" in data
        assert "dtn" in data
        assert "mission_catalog" in data
        assert len(data["mission_catalog"]) == 3

    def test_update_mission_profile(self, client):
        resp = client.post("/api/mission/profile", json={
            "mission": "Artemis Gateway (Lunar)",
            "crew": "Lt. Cdr. P. Nair (Flight Engineer)"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["mission"] == "Artemis Gateway (Lunar)"
        assert data["crew"] == "Lt. Cdr. P. Nair (Flight Engineer)"

    def test_dtn_latency_changes_with_profile(self, client):
        client.post("/api/mission/profile", json={"mission": "Mars Transit (Deep Space)"})
        resp = client.get("/api/mission/status")
        assert "420" in resp.json()["dtn"]["latency_display"]

    def test_compile_dossier(self, client):
        resp = client.post("/api/mission/dossier")
        assert resp.status_code == 200
        data = resp.json()
        assert "markdown" in data
        assert "FLIGHT SURGEON" in data["markdown"]
        assert "download_url" in data

    def test_download_dossier_no_compile(self, client):
        resp = client.get("/api/mission/dossier/download")
        assert resp.status_code == 404

    def test_download_dossier_after_compile(self, client):
        client.post("/api/mission/dossier")
        resp = client.get("/api/mission/dossier/download")
        assert resp.status_code == 200
        assert "FLIGHT SURGEON" in resp.text


# ─────────────────────────────────────────────────────────────────────────────
# Psych
# ─────────────────────────────────────────────────────────────────────────────

class TestPsych:
    def test_engine_status_not_loaded(self, client):
        resp = client.get("/api/psych/status")
        assert resp.status_code == 200
        assert resp.json()["is_loaded"] is False

    def test_get_psych_logs_empty(self, client):
        resp = client.get("/api/psych/logs")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_get_presets(self, client):
        resp = client.get("/api/psych/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        # Always at least 2 permanent presets
        assert len(data["presets"]) >= 2
        # Check permanent presets present as [label, prompt] pairs per Step 0 specification contract
        labels = [p[0] if isinstance(p, (list, tuple)) else p.get("label", "") for p in data["presets"]]
        assert any("4-7-8" in l for l in labels)
        assert any("Telemetry" in l for l in labels)

    def test_engine_init_handles_empty_or_dict_config(self, client):
        """Verify POST /api/psych/init handles empty payload, None config, or dict config without AttributeError."""
        import backend.services.psych_service as ps
        orig_mgr = ps._phase2_manager
        orig_loaded = ps._phase2_loaded
        try:
            ps._phase2_loaded = False
            # Call with empty body {}
            resp = client.post("/api/psych/init", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert "success" in data
            assert "'dict' object has no attribute 'asr_enabled'" not in data["message"]

            # Reset and call with explicit dict config
            ps._phase2_loaded = False
            resp2 = client.post("/api/psych/init", json={"config": {"asr_enabled": False, "llm_enabled": False, "tts_enabled": False}})
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["success"] is True
            assert data2["is_loaded"] is True
        finally:
            ps._phase2_manager = orig_mgr
            ps._phase2_loaded = orig_loaded

    def test_phase2_manager_load_models_accepts_dict(self):
        """Verify Phase2Manager.load_models accepts dict or None directly."""
        from modules.phase2_core import Phase2Manager
        mgr = Phase2Manager()
        # Should not raise AttributeError when passed a dict
        mgr.load_models({"asr_enabled": False, "llm_enabled": False, "tts_enabled": False})
        assert mgr.is_loaded is True

    def test_chat_without_engine(self, client):
        # Should return a helpful message, not crash
        resp = client.post("/api/psych/chat", json={"query": "How am I doing?", "channel": "text"})
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "not initialized" in data["reply"].lower()

    def test_chat_with_mock_engine(self, client):
        """Verify chat when engine is initialized off-thread (no TypeError await on sync method)."""
        import backend.services.psych_service as ps
        from unittest.mock import MagicMock
        orig_mgr = ps._phase2_manager
        orig_loaded = ps._phase2_loaded
        try:
            ps._phase2_loaded = True
            mock_mgr = MagicMock()
            mock_mgr.generate_response.return_value = "Everything looks nominal Commander."
            mock_mgr.speak.return_value = b"RIFF_FAKE_WAV"
            ps._phase2_manager = mock_mgr

            resp = client.post("/api/psych/chat", json={"query": "Vitals check", "channel": "text"})
            assert resp.status_code == 200
            data = resp.json()
            assert "Everything looks nominal" in data["reply"]
            assert data["audio_base64"] is not None
        finally:
            ps._phase2_manager = orig_mgr
            ps._phase2_loaded = orig_loaded

    def test_grounding_with_mock_engine(self, client):
        """Verify grounding synthesis off-thread (no TypeError await on sync speak)."""
        import backend.services.psych_service as ps
        from unittest.mock import MagicMock
        orig_mgr = ps._phase2_manager
        orig_loaded = ps._phase2_loaded
        try:
            ps._phase2_loaded = True
            mock_mgr = MagicMock()
            mock_mgr.speak.return_value = b"RIFF_GROUNDING_WAV"
            ps._phase2_manager = mock_mgr

            resp = client.post("/api/psych/grounding", json={"crew": "Cdr. Sharma", "stress": 65.0})
            assert resp.status_code == 200
            data = resp.json()
            assert "4-7-8 breathing protocol" in data["script"]
            assert data["audio_base64"] is not None
        finally:
            ps._phase2_manager = orig_mgr
            ps._phase2_loaded = orig_loaded

    def test_post_log_persists_individual_probs(self, client):
        """Verify individual prob_* fields from React frontend are persisted into SQLite."""
        payload = {
            "face_emotion": "happy",
            "fused_emotion": "happy",
            "voice_state": "speaking",
            "heart_rate": 82.0,
            "temperature": 36.7,
            "spo2": 98.0,
            "prob_happy": 0.88,
            "prob_neutral": 0.12,
            "prob_angry": 0.0,
        }
        resp = client.post("/api/logs", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "logged"

        trends_resp = client.get("/api/logs/trends?n=5")
        assert trends_resp.status_code == 200
        records = trends_resp.json()["records"]
        assert len(records) > 0
        latest = records[0]
        assert latest.get("prob_happy") == pytest.approx(0.88, abs=0.01)
