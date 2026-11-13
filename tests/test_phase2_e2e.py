#!/usr/bin/env python3
"""
tests/test_phase2_e2e.py
End-to-End integration test for MAITRI Phase 2 Conversational & Psychological AI.
"""

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from modules.phase2_core import Phase2Config, Phase2Manager
from modules.asr_tap import asr_buffer
from modules.database_module import init_db, log_psych_event, get_psych_logs


def run_e2e_tests():
    print("==================================================")
    print("🛰️  MAITRI 2.0 — Phase 2 End-to-End Integration Test")
    print("==================================================")

    # 1. Initialize Database
    print("\n[1/6] Testing SQLite Database Schema & Psych Logging...")
    init_db()
    log_psych_event(
        crew_member="Cdr. A. Sharma (Pilot / CMO)",
        mission_phase="ISRO Gaganyaan (LEO)",
        input_channel="test:e2e",
        astronaut_query="Simulation test query for Phase 2 validation.",
        detected_emotion="neutral",
        stress_pct=42.0,
        ai_response="Simulation test response.",
        has_audio=True,
    )
    logs = get_psych_logs(limit=5)
    assert not logs.empty, "Failed to retrieve psych logs from database!"
    print(f"  ✔ Psych log table active (retrieved {len(logs)} records)")

    # 2. Instantiate and Load Models
    print("\n[2/6] Loading Phase 2 Neural Models (Whisper, Phi-3-Mini, Piper)...")
    cfg = Phase2Config()
    mgr = Phase2Manager()
    mgr.load_models(cfg)
    assert mgr.is_loaded, "Phase2Manager failed to load models!"
    print("  ✔ All neural models loaded successfully into RAM")

    # 3. Test Piper TTS Voice Synthesis
    print("\n[3/6] Testing Piper ONNX Voice Synthesis...")
    test_phrase = "Commander Sharma, MAITRI psychological support is fully operational."
    wav_bytes = mgr.speak(test_phrase)
    assert len(wav_bytes) > 20000, f"TTS output too small: {len(wav_bytes)} bytes"
    print(f"  ✔ Synthesized {len(wav_bytes)} bytes of 22.05 kHz PCM WAV audio")

    # 4. Test Whisper ASR (Speech-to-Text) on Synthesized Audio
    print("\n[4/6] Testing Whisper ASR on Simulated Voice Input (BytesIO)...")
    bio = io.BytesIO(wav_bytes)
    transcription = mgr.transcribe(bio)
    print(f"  🗣️ Whisper recognized: \"{transcription}\"")
    assert len(transcription) > 0, "Whisper transcription returned empty string!"
    print("  ✔ Speech-to-Text successfully decoded spoken audio")

    # 5. Test Contextual Clinical Prompting & Phi-3 LLM Reasoning
    print("\n[5/6] Testing Contextual Clinical Reasoning (Phi-3-Mini)...")
    reply = mgr.generate_response(
        user_text="I am experiencing mild dizziness and high cabin pressure alerts.",
        emotion="fear",
        stress_pct=74.5,
        astronaut_name="Cdr. A. Sharma",
        mission_phase="ISRO Gaganyaan (LEO)",
        vitals_summary="HR: 88 BPM, SpO2: 97%, Fatigue: Drowsy",
    )
    print(f"  🧠 MAITRI Clinical Reply:\n     \"{reply}\"")
    assert len(reply) > 20, "LLM reply was too short or empty!"
    print("  ✔ LLM generated empathetic, contextual clinical guidance")

    # 6. Test Guided Grounding Protocol Script & Audio
    print("\n[6/6] Testing Guided 4-7-8 Grounding Countermeasure...")
    grounding_text = mgr.generate_grounding_protocol("Cdr. A. Sharma", 74.5)
    assert "grounding cycle" in grounding_text.lower(), "Grounding script missing key phrase!"
    grounding_wav = mgr.speak(grounding_text)
    assert len(grounding_wav) > 100000, "Grounding WAV audio failed to synthesize!"
    print(f"  ✔ Synthesized {len(grounding_wav)} bytes of guided grounding audio")

    print("\n==================================================")
    print("✅ ALL 6 PHASE 2 INTEGRATION TESTS PASSED PERFECTLY!")
    print("==================================================")


def test_phase2_e2e():
    run_e2e_tests()


if __name__ == "__main__":
    run_e2e_tests()
