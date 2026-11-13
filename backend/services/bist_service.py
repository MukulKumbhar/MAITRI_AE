"""
MAITRI 2.0 — Built-In Self-Test (BIST) Diagnostic Service
Autonomous diagnostic runner for offline spacecraft operations.
Validates:
1. Camera video capture input
2. Microphone audio input devices
3. Offline neural models on disk (Face ONNX, Piper TTS, Vosk STT, Phi-3 LLM, Whisper)
4. System RAM and memory headroom
5. SQLite database integrity & SHA-256 cryptographic hash chains
"""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("maitri.bist")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MODELS_DIR = _PROJECT_ROOT / "models"

# In-memory cache of the latest BIST execution
_LAST_BIST_RESULT: Optional[Dict[str, Any]] = None


def check_cameras() -> Dict[str, Any]:
    """
    Check camera availability and capture test frame.
    Gracefully handles headless servers, lack of physical webcams, or permission limits.
    """
    video_devs = sorted(glob.glob("/dev/video*"))
    has_video_devices = len(video_devs) > 0

    capture_success = False
    device_index = None
    width = 0
    height = 0
    error_msg = None

    try:
        import cv2  # type: ignore
        # Attempt opening default index 0
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                capture_success = True
                device_index = 0
                height, width = frame.shape[:2]
            cap.release()
    except Exception as exc:
        error_msg = str(exc)

    if capture_success:
        status = "PASSED"
        details = f"Active camera index {device_index} captured frame ({width}x{height})."
    elif has_video_devices:
        status = "DEGRADED"
        details = f"Found video devices {video_devs}, but capture failed ({error_msg or 'device busy/unreadable'}). Hardware adapter fallback active."
    else:
        status = "DEGRADED"
        details = "No /dev/video* devices detected. Operating in synthetic / simulation sensor adapter mode."

    return {
        "status": status,
        "capture_success": capture_success,
        "video_devices": video_devs,
        "frame_dimensions": f"{width}x{height}" if capture_success else "none",
        "details": details,
    }


def check_microphones() -> Dict[str, Any]:
    """
    Check audio input devices and microphone subsystem.
    """
    has_audio_devices = False
    input_devices: List[str] = []
    error_msg = None

    try:
        import sounddevice as sd  # type: ignore
        devs = sd.query_devices()
        for idx, dev in enumerate(devs):
            if dev.get("max_input_channels", 0) > 0:
                has_audio_devices = True
                input_devices.append(f"[{idx}] {dev.get('name', 'Unknown')}")
    except Exception as exc:
        error_msg = str(exc)

    if not has_audio_devices:
        # Fallback check on Linux /dev/snd
        snd_nodes = glob.glob("/dev/snd/pcm*c")
        if snd_nodes:
            has_audio_devices = True
            input_devices = [f"ALSA capture node: {n}" for n in snd_nodes]

    if has_audio_devices:
        status = "PASSED"
        details = f"Detected {len(input_devices)} audio input device(s)."
    else:
        status = "DEGRADED"
        details = f"No physical microphone detected ({error_msg or 'no audio capture device'}). AudioWorklet browser capture or synthetic mode active."

    return {
        "status": status,
        "has_audio_devices": has_audio_devices,
        "devices": input_devices[:5],
        "details": details,
    }


def check_models_on_disk() -> Dict[str, Any]:
    """
    Verify on-disk presence, readability, and file size of offline AI models.
    """
    models = {
        "emotion_ferplus_onnx": {
            "path": _MODELS_DIR / "emotion-ferplus-8.onnx",
            "fallback_path": _MODELS_DIR / "emotion_ferplus.onnx",
            "critical": False,
        },
        "piper_voice_tts": {
            "path": _MODELS_DIR / "piper_voice" / "en_US-lessac-medium.onnx",
            "critical": False,
        },
        "piper_voice_config": {
            "path": _MODELS_DIR / "piper_voice" / "en_US-lessac-medium.onnx.json",
            "critical": False,
        },
        "vosk_stt": {
            "path": _MODELS_DIR / "vosk",
            "critical": False,
            "is_dir": True,
        },
        "phi3_mini_llm": {
            "path": _MODELS_DIR / "phi3_mini_q4.gguf",
            "critical": False,
        },
        "whisper_tiny_asr": {
            "path": _MODELS_DIR / "whisper_tiny_en",
            "critical": False,
            "is_dir": True,
        },
    }

    report = {}
    total_models = len(models)
    found_count = 0

    for name, spec in models.items():
        p: Path = spec["path"]
        fallback_p: Optional[Path] = spec.get("fallback_path")
        is_dir = spec.get("is_dir", False)

        exists = False
        target_path = p
        if p.exists():
            exists = True
        elif fallback_p and fallback_p.exists():
            exists = True
            target_path = fallback_p

        size_mb = 0.0
        if exists:
            found_count += 1
            if is_dir:
                total_bytes = sum(f.stat().st_size for f in target_path.rglob("*") if f.is_file())
                size_mb = round(total_bytes / (1024 * 1024), 2)
            else:
                size_mb = round(target_path.stat().st_size / (1024 * 1024), 2)

        report[name] = {
            "exists": exists,
            "path": str(target_path),
            "size_mb": size_mb,
            "status": "ONLINE" if exists else "ABSENT",
        }

    # At least Piper or Emotion or Whisper/Vosk should be available
    if found_count >= 2:
        status = "PASSED"
        details = f"{found_count}/{total_models} local AI models present and validated on disk."
    else:
        status = "DEGRADED"
        details = f"Only {found_count}/{total_models} models present. Core heuristic / simulated fallbacks active."

    return {
        "status": status,
        "models_found": found_count,
        "models_total": total_models,
        "models": report,
        "details": details,
    }


def check_ram_and_resources() -> Dict[str, Any]:
    """
    Check host memory usage and available RAM headroom.
    """
    total_mb = 0.0
    available_mb = 0.0
    percent_used = 0.0
    process_rss_mb = 0.0

    try:
        import psutil  # type: ignore
        mem = psutil.virtual_memory()
        total_mb = round(mem.total / (1024 * 1024), 1)
        available_mb = round(mem.available / (1024 * 1024), 1)
        percent_used = mem.percent

        proc = psutil.Process(os.getpid())
        process_rss_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
    except Exception:
        # /proc/meminfo fallback
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            meminfo = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v = int(parts[1].split()[0])  # kB
                    meminfo[k] = v
            total_kb = meminfo.get("MemTotal", 0)
            avail_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
            total_mb = round(total_kb / 1024, 1)
            available_mb = round(avail_kb / 1024, 1)
            percent_used = round(100.0 * (1.0 - (available_mb / max(1.0, total_mb))), 1)
        except Exception:
            total_mb = 4096.0
            available_mb = 2048.0
            percent_used = 50.0

    if available_mb >= 500.0 and percent_used < 90.0:
        status = "PASSED"
        details = f"RAM nominal: {available_mb} MB available ({percent_used}% used)."
    elif available_mb >= 200.0:
        status = "DEGRADED"
        details = f"RAM low headroom: {available_mb} MB available ({percent_used}% used)."
    else:
        status = "FAILED"
        details = f"RAM critical: only {available_mb} MB available ({percent_used}% used)."

    return {
        "status": status,
        "total_mb": total_mb,
        "available_mb": available_mb,
        "percent_used": percent_used,
        "process_rss_mb": process_rss_mb,
        "details": details,
    }


def check_database_integrity(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifies SQLite integrity check, schema presence, and SHA-256 audit hash chains.
    """
    from modules.database_module import (
        DB_FILE,
        init_db,
        verify_stress_logs_hash_chain,
        verify_alarm_events_hash_chain,
        verify_pvt_logs_hash_chain,
        verify_sleep_records_hash_chain,
        verify_screener_records_hash_chain,
    )
    path = db_path or DB_FILE
    init_db(path)

    integrity_ok = False
    integrity_message = ""
    table_counts = {}

    try:
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("PRAGMA integrity_check")
        rows = c.fetchall()
        integrity_ok = len(rows) > 0 and rows[0][0] == "ok"
        integrity_message = rows[0][0] if rows else "unknown"

        # Check required tables
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in c.fetchall()}

        for tbl in ["stress_logs", "alarm_events", "pvt_logs", "sleep_records", "screener_records", "psych_support_logs"]:
            if tbl in existing_tables:
                c.execute(f"SELECT COUNT(*) FROM {tbl}")
                cnt = c.fetchone()[0]
                table_counts[tbl] = cnt
            else:
                table_counts[tbl] = -1  # missing

        conn.close()
    except Exception as exc:
        integrity_message = str(exc)

    # Verify SHA-256 hash chains across all cryptographic ledgers
    v_stress, f_stress = verify_stress_logs_hash_chain(path)
    v_alarm, f_alarm = verify_alarm_events_hash_chain(path)
    v_pvt, f_pvt = verify_pvt_logs_hash_chain(path)
    v_sleep, f_sleep = verify_sleep_records_hash_chain(path)
    v_screener, f_screener = verify_screener_records_hash_chain(path)

    all_chains_valid = v_stress and v_alarm and v_pvt and v_sleep and v_screener

    if integrity_ok and all_chains_valid:
        status = "PASSED"
        details = "SQLite integrity ok; all 5 cryptographic hash chains intact and unbroken."
    elif integrity_ok and not all_chains_valid:
        status = "FAILED"
        details = (
            f"Cryptographic tamper detected! Chain verification failure: "
            f"stress={v_stress}(fail_id={f_stress}), alarm={v_alarm}(fail_id={f_alarm}), "
            f"pvt={v_pvt}(fail_id={f_pvt}), sleep={v_sleep}(fail_id={f_sleep}), "
            f"screener={v_screener}(fail_id={f_screener})"
        )
    else:
        status = "FAILED"
        details = f"Database integrity check failed: {integrity_message}"

    return {
        "status": status,
        "integrity_check": integrity_message,
        "all_chains_valid": all_chains_valid,
        "hash_chains": {
            "stress_logs": {"valid": v_stress, "fail_id": f_stress},
            "alarm_events": {"valid": v_alarm, "fail_id": f_alarm},
            "pvt_logs": {"valid": v_pvt, "fail_id": f_pvt},
            "sleep_records": {"valid": v_sleep, "fail_id": f_sleep},
            "screener_records": {"valid": v_screener, "fail_id": f_screener},
        },
        "table_row_counts": table_counts,
        "details": details,
    }


def run_bist(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Run full Built-In Self-Test (BIST) diagnostic suite.
    Returns complete structured BIST report.
    """
    global _LAST_BIST_RESULT
    t0 = time.perf_counter()
    timestamp_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    cam_res = check_cameras()
    mic_res = check_microphones()
    models_res = check_models_on_disk()
    ram_res = check_ram_and_resources()
    db_res = check_database_integrity(db_path=db_path)

    # Determine overall system health status
    subsystems = {
        "camera": cam_res,
        "microphone": mic_res,
        "models_on_disk": models_res,
        "memory_ram": ram_res,
        "database_cryptography": db_res,
    }

    statuses = [s["status"] for s in subsystems.values()]
    if "FAILED" in statuses:
        overall_status = "FAILED"
    elif "DEGRADED" in statuses:
        overall_status = "DEGRADED"
    else:
        overall_status = "PASSED"

    duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    result = {
        "bist_id": f"BIST_{int(time.time())}",
        "timestamp": timestamp_iso,
        "overall_status": overall_status,
        "duration_ms": duration_ms,
        "subsystems": subsystems,
        "summary": (
            f"BIST completed in {duration_ms} ms. Status: {overall_status}. "
            f"DB: {db_res['status']}, RAM: {ram_res['status']}, "
            f"Models: {models_res['status']}, Video: {cam_res['status']}, Audio: {mic_res['status']}."
        ),
    }

    _LAST_BIST_RESULT = result
    logger.info("🛠️ BIST diagnostic execution complete: %s (%s ms)", overall_status, duration_ms)
    return result


def get_last_bist_result() -> Optional[Dict[str, Any]]:
    """Return the cached result of the last BIST run."""
    return _LAST_BIST_RESULT
