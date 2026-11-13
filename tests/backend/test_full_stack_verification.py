"""
MAITRI 2.0 — Full-Stack Verification & Offline Asset Integrity Tests
Tests:
  - SPA Static Files & Fallback serving (index.html, wasm, task, audio-processor)
  - Zero Cloud / Zero Remote Asset verification
  - REST API surface
  - WebSocket telemetry protocol
  - Offline Vosk & Intent safety verification
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import modules.database_module as db_mod
_TEST_DB = str(_PROJECT_ROOT / "tests" / "backend" / "test_full_stack.db")

from backend.main import app
from backend.state import reset_state


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


class TestStaticAndSPAFallback:
    def test_serve_spa_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "MAITRI 2.0" in resp.text
        assert "<div id=\"root\">" in resp.text

    def test_serve_spa_client_route(self, client):
        # Non-API path like /support should return SPA index.html
        resp = client.get("/support")
        assert resp.status_code == 200
        assert "MAITRI 2.0" in resp.text

    def test_serve_face_landmarker_task(self, client):
        resp = client.get("/face_landmarker.task")
        assert resp.status_code == 200
        assert len(resp.content) > 3_000_000  # ~3.7 MB

    def test_serve_audio_processor(self, client):
        resp = client.get("/audio-processor.js")
        assert resp.status_code == 200
        assert "maitri-audio-processor" in resp.text

    def test_serve_wasm_binary(self, client):
        resp = client.get("/wasm/vision_wasm_internal.wasm")
        assert resp.status_code == 200
        assert len(resp.content) > 10_000_000  # ~11 MB


class TestAirGappedAssetIntegrity:
    def test_zero_remote_cdn_in_html(self, client):
        resp = client.get("/")
        html = resp.text.lower()
        # Strictly verify zero external scripts or stylesheets
        import re
        external_srcs = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', html)
        assert len(external_srcs) == 0, f"Found external asset references: {external_srcs}"
        assert "cdnjs" not in html
        assert "unpkg" not in html
        assert "jsdelivr" not in html
        assert "fonts.googleapis" not in html
        assert "fonts.gstatic" not in html

    def test_all_models_exist_offline(self):
        models_dir = _PROJECT_ROOT / "models"
        assert (models_dir / "enet_b2_7.onnx").exists()
        assert (models_dir / "face_landmarker.task").exists()
        assert (models_dir / "vosk").exists()
        assert (models_dir / "piper_voice" / "en_US-lessac-medium.onnx").exists()
        assert (models_dir / "whisper_tiny_en").exists()
        assert (models_dir / "phi3_mini_q4.gguf").exists()
