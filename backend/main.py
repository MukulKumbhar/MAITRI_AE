"""
MAITRI 2.0 — FastAPI Main Application
Offline Astronaut Well-Being Monitor — React Migration Backend

Usage:
    cd /home/mikey/maitri_local
    ./venv311/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

One-command startup (after frontend is built):
    ./venv311/bin/python -m backend.main

Serves:
  - REST API at /api/*
  - WebSocket endpoints at /ws/*
  - React SPA at / (all non-API paths → frontend/dist/index.html)
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Path setup: project root → sys.path so modules/ resolves ─────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Support PyInstaller: use sys._MEIPASS when frozen
_STATIC_ROOT = Path(getattr(sys, "_MEIPASS", str(_PROJECT_ROOT)))

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Configure logging before any imports that use it ─────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("maitri.main")

# ── Import application state and services ─────────────────────────────────────
from backend.state import get_state

# ── Import routers ────────────────────────────────────────────────────────────
from backend.api.health import router as health_router
from backend.api.logs import router as logs_router
from backend.api.psych import router as psych_router
from backend.api.mission import router as mission_router
from backend.api.watchdog import router as watchdog_router
from backend.api.settings import router as settings_router
from backend.api.clinical import router as clinical_router

from backend.ws.telemetry import router as telemetry_ws_router
from backend.ws.audio import router as audio_ws_router
from backend.ws.video_crop import router as video_ws_router


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan:
      - Startup: init DB, pre-warm ONNX, start telemetry broadcast loop
      - Shutdown: cancel background tasks
    """
    state = get_state()
    logger.info("=" * 60)
    logger.info("🛰️  MAITRI 2.0 — Offline Astronaut Well-Being Monitor")
    logger.info("=" * 60)

    # ── 1. Initialize database ────────────────────────────────────────────
    try:
        from modules.database_module import init_db
        # Point DB module at correct path
        import modules.database_module as db_mod
        if "MAITRI_DB_PATH" in os.environ:
            db_mod.DB_FILE = os.environ["MAITRI_DB_PATH"]
        elif db_mod.DB_FILE == "maitri_logs.db":
            db_mod.DB_FILE = str(_PROJECT_ROOT / "maitri_logs.db")
        init_db()
        state.sync_hash_chain(db_mod.DB_FILE)
        logger.info("✅ SQLite database initialized: %s", db_mod.DB_FILE)
    except Exception as exc:
        logger.error("❌ Database init error: %s", exc)

    # ── 2. Pre-warm EfficientNet ONNX & Vosk ASR ──────────────────────────
    try:
        from backend.services.vision_service import _get_face_module, get_model_status
        fm = _get_face_module()
        status = get_model_status()
        state.face_model_ready = status.get("onnx", False)
        logger.info("✅ Face ONNX model: %s", "ready" if state.face_model_ready else "not available")
    except Exception as exc:
        logger.warning("⚠️  Face model pre-warm error: %s", exc)

    try:
        from backend.services.voice_service import get_voice_service
        vs = get_voice_service()
        state.vosk_ready = vs.init_vosk()
        logger.info("✅ Vosk ASR engine: %s", "ready" if state.vosk_ready else "offline")
    except Exception as exc:
        logger.warning("⚠️  Vosk init error: %s", exc)

    # ── 3. Start telemetry broadcast loop ─────────────────────────────────
    from backend.services.telemetry_service import telemetry_broadcast_loop
    telemetry_task = asyncio.create_task(telemetry_broadcast_loop())
    logger.info("✅ Telemetry broadcast loop started (10 Hz)")

    logger.info("🚀 Server ready — API: http://0.0.0.0:8000/api/health")
    logger.info("=" * 60)

    yield  # ── Application runs ──────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────
    telemetry_task.cancel()
    try:
        await telemetry_task
    except asyncio.CancelledError:
        pass
    logger.info("🛑 MAITRI 2.0 shutdown complete")


# ── FastAPI Application ───────────────────────────────────────────────────────
app = FastAPI(
    title="MAITRI 2.0 API",
    description="Offline Multimodal Astronaut Telemetry & Real-Time Intelligence",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS (dev mode: allow all origins for Vite dev server on port 5173) ──────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tightened after production build
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register REST API routers ─────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(logs_router)
app.include_router(psych_router)
app.include_router(mission_router)
app.include_router(watchdog_router)
app.include_router(settings_router)
app.include_router(clinical_router)

# ── Register WebSocket routers ────────────────────────────────────────────────
app.include_router(telemetry_ws_router)
app.include_router(audio_ws_router)
app.include_router(video_ws_router)

# ── Static file serving for the React production build ───────────────────────
_FRONTEND_DIST = _STATIC_ROOT / "frontend" / "dist"
_FRONTEND_ASSETS = _FRONTEND_DIST / "assets"
_FRONTEND_WASM = _FRONTEND_DIST / "wasm"

if _FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_ASSETS)), name="assets")
    logger.info("📦 Serving React assets from %s", _FRONTEND_ASSETS)

if _FRONTEND_WASM.exists():
    app.mount("/wasm", StaticFiles(directory=str(_FRONTEND_WASM)), name="wasm")
    logger.info("📦 Serving MediaPipe WASM from %s", _FRONTEND_WASM)


# ── SPA Fallback: serve index.html or root static assets ─────────────────────
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str, request: Request):
    """
    Catch-all route: serves static assets in dist/ or falls back to index.html for SPA routes.
    """
    # API and WebSocket paths should never reach here (registered first)
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    # If specific file in dist requested (e.g. face_landmarker.task, audio-processor.js)
    if full_path:
        candidate_file = _FRONTEND_DIST / full_path
        if candidate_file.is_file():
            return FileResponse(str(candidate_file))

    index_html = _FRONTEND_DIST / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))

    # Frontend not built yet — return helpful dev message
    return JSONResponse(
        {
            "message": "🛰️ MAITRI 2.0 Backend is running!",
            "status": "frontend not built",
            "instructions": "Run 'npm run build' in the frontend/ directory, then refresh.",
            "api_docs": "/api/docs",
            "health": "/api/health",
            "websockets": ["/ws/telemetry", "/ws/audio", "/ws/video-crop"],
        }
    )


# ── Entry point (direct execution) ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
