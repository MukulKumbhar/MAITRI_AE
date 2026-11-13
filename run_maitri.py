#!/usr/bin/env python3
"""
🛰️ Project MAITRI 2.0 — Offline Astronaut Well-Being Monitor
One-Command Master Runner

Usage:
    ./venv311/bin/python run_maitri.py
    python run_maitri.py [--port 8000] [--host 0.0.0.0] [--no-browser]
"""

import argparse
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_FRONTEND_DIST = _ROOT / "frontend" / "dist"
_INDEX_HTML = _FRONTEND_DIST / "index.html"


def ensure_frontend_built() -> None:
    """Check if frontend/dist exists; if not, compile via npm run build."""
    if not _INDEX_HTML.exists():
        print("📦 Frontend not built. Running 'npm run build' in frontend/...")
        try:
            subprocess.run(
                ["npm", "run", "build"],
                cwd=str(_ROOT / "frontend"),
                check=True,
            )
            print("✅ Frontend build completed.")
        except Exception as exc:
            print(f"⚠️  Frontend build failed: {exc}")
            print("   FastAPI backend will still start in headless / API mode.")


def main() -> None:
    parser = argparse.ArgumentParser(description="MAITRI 2.0 Master Runner")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn hot-reload (dev mode)")
    args = parser.parse_args()

    print("=" * 65)
    print("🛰️  MAITRI 2.0 — Multimodal Astronaut Well-Being Monitor")
    print("    100% Offline Air-Gapped Aerospace Cockpit")
    print("=" * 65)

    ensure_frontend_built()

    import uvicorn

    url = f"http://localhost:{args.port}"
    print(f"🚀 Launching Cockpit UI at: {url}")
    print(f"📋 REST API Docs available at: {url}/api/docs")
    print("=" * 65)

    if not args.no_browser and not os.environ.get("CI"):
        try:
            # Short delay to give uvicorn time to bind
            import threading
            threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        except Exception:
            pass

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
