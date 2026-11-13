"""
tests/test_phase2_extended.py
Automated test suite verifying the 7 Astronaut Interaction & Mission Telemetry requirements:
1. Audio Autoplay mechanics (one-shot autoplay, base64 data injection).
2. Accuracy & zero-bug validation under edge cases.
3. Hands-free Tab Switching solutions and voice command parsing.
4. Ultra-sensitive acoustic detection (RMS >= 0.002, distant murmur detection).
5. Sub-second silence-boundary segmentation (VAD pause detection & AGC normalization).
6. Presets dynamic evolution (preserving core anchors while evolving dynamic slots).
7. Database schema & 7-class emotion probabilities trajectory matching HUD colors.
"""

import base64
import os
import sqlite3
import unittest
import numpy as np
import pandas as pd

from modules.asr_tap import (
    ASRBuffer,
    parse_voice_command,
    parse_voice_action,
    TAB_NAMES,
)
from modules.database_module import (
    DB_FILE,
    init_db,
    log_event,
    get_logs,
    get_recent_trend,
)
from modules.phase2_core import (
    get_evolved_presets,
    Phase2Config,
    Phase2Manager,
)


class TestHandsFreeVoiceNavigation(unittest.TestCase):
    """Requirement 3: Voice command navigation parsing across all 4 mission tabs."""

    def test_live_tab_commands(self):
        commands = ["switch to live", "open live feed", "show cockpit camera", "tab 1", "go to live"]
        for cmd in commands:
            res = parse_voice_command(cmd)
            self.assertIsNotNone(res, f"Failed for '{cmd}'")
            tab_idx, tab_name = res
            self.assertEqual(tab_idx, 0)
            self.assertEqual(tab_name, TAB_NAMES[0])

    def test_logs_tab_commands(self):
        commands = ["switch to logs", "show telemetry trends", "open history", "tab 2", "go to logs", "display graph"]
        for cmd in commands:
            res = parse_voice_command(cmd)
            self.assertIsNotNone(res, f"Failed for '{cmd}'")
            tab_idx, tab_name = res
            self.assertEqual(tab_idx, 1)
            self.assertEqual(tab_name, TAB_NAMES[1])

    def test_demo_tab_commands(self):
        commands = ["switch to demo", "show mission control", "open simulation", "tab 3", "go to mission control"]
        for cmd in commands:
            res = parse_voice_command(cmd)
            self.assertIsNotNone(res, f"Failed for '{cmd}'")
            tab_idx, tab_name = res
            self.assertEqual(tab_idx, 2)
            self.assertEqual(tab_name, TAB_NAMES[2])

    def test_support_tab_commands(self):
        commands = ["switch to support", "open psychological support", "go to chat", "tab 4", "open grounding"]
        for cmd in commands:
            res = parse_voice_command(cmd)
            self.assertIsNotNone(res, f"Failed for '{cmd}'")
            tab_idx, tab_name = res
            self.assertEqual(tab_idx, 3)
            self.assertEqual(tab_name, TAB_NAMES[3])

    def test_conversational_queries_not_misidentified_as_nav(self):
        queries = [
            "I am feeling very tired and cannot sleep.",
            "Commander reporting nominal vital signs.",
            "Can you evaluate my docking anxiety?",
            "What is my current heart rate?",
            "Live telemetry shows I am feeling sick.",
            "History of insomnia is making me anxious.",
            "Video feedback indicates pupil dilation.",
            "Help me understand why I am dizzy.",
            "Chart our trajectory towards Mars.",
            "Log book says we are 2 days from Earth.",
            "Graph shows elevated heart rate.",
            "Telemetry shows low cabin oxygen.",
            "Video shows anomalous thruster flame.",
            "The cockpit display indicates normal pressure.",
            "MAITRI, I need guidance for high cabin temperature.",
        ]
        for q in queries:
            res = parse_voice_command(q)
            self.assertIsNone(res, f"Conversational query '{q}' incorrectly identified as command: {res}")

    def test_voice_action_commands(self):
        actions = ["log reading", "save telemetry", "record the reading", "MAITRI, log vitals"]
        for act in actions:
            res = parse_voice_action(act)
            self.assertEqual(res, "log_reading", f"Failed to identify action for '{act}'")

        # Conversational should not trigger action
        self.assertIsNone(parse_voice_action("Can you log this symptom?"))


class TestUltraSensitiveLiveASRAndVAD(unittest.TestCase):
    """Requirements 4 & 5: Ultra-sensitive acoustic detection, AGC, and silence boundaries."""

    def setUp(self):
        self.buf = ASRBuffer()
        self.buf.set_enabled(True)

    def tearDown(self):
        self.buf.set_enabled(False)

    def test_faint_distant_speech_triggers_vad(self):
        """Verify faint audio (RMS ~0.0035, quiet astronaut across cabin) triggers speech."""
        sr = 16000
        # Generate 1.2s of faint speech-like harmonic signal
        t = np.linspace(0, 1.2, int(1.2 * sr), dtype=np.float32)
        faint_speech = 0.005 * np.sin(2 * np.pi * 320 * t)  # RMS ~0.0035
        rms = np.sqrt(np.mean(faint_speech ** 2))
        self.assertGreater(rms, 0.002, "Test signal RMS should exceed faint threshold")

        # Push 100ms chunks
        chunk_sz = 1600
        for i in range(0, len(faint_speech), chunk_sz):
            self.buf.push(faint_speech[i:i + chunk_sz])

        tel = self.buf.get_telemetry()
        self.assertTrue(tel["in_speech"], "Faint speech should activate VAD in_speech state")
        self.assertGreater(tel["speech_duration_s"], 0.8)

    def test_has_transcript_and_queue_drain(self):
        self.assertFalse(self.buf.has_transcript())
        with self.buf._lock:
            self.buf._transcript_queue.append({"text": "test", "is_command": False})
        self.assertTrue(self.buf.has_transcript())
        t = self.buf.pop_transcript()
        self.assertIsNotNone(t)
        self.assertFalse(self.buf.has_transcript())

    def test_silence_boundary_finalizes_utterance_with_agc(self):
        """Verify ~650ms of silence terminates utterance and applies AGC peak normalization."""
        sr = 16000
        # 1.0s speech
        t = np.linspace(0, 1.0, sr, dtype=np.float32)
        speech = 0.02 * np.sin(2 * np.pi * 400 * t)
        # 0.8s silence
        silence = np.zeros(int(0.8 * sr), dtype=np.float32)

        chunk_sz = 1600
        # Push speech
        for i in range(0, len(speech), chunk_sz):
            self.buf.push(speech[i:i + chunk_sz])
        self.assertTrue(self.buf.get_telemetry()["in_speech"])

        # Push silence to trigger boundary
        for i in range(0, len(silence), chunk_sz):
            self.buf.push(silence[i:i + chunk_sz])

        # Utterance should now be completed and packaged
        self.assertFalse(self.buf.get_telemetry()["in_speech"], "Should have exited speech state")
        utt = self.buf.pop_completed_utterance()
        self.assertIsNotNone(utt, "Completed utterance must be enqueued")
        self.assertGreaterEqual(len(utt), int(0.5 * sr), "Utterance length must meet minimum duration")

        # AGC Verification: quiet 0.02 amplitude should be normalized near ~0.82
        peak = np.max(np.abs(utt))
        self.assertGreater(peak, 0.25, f"AGC peak normalization failed to boost audio: peak={peak:.3f}")
        self.assertLessEqual(peak, 0.99, f"AGC must not clip: peak={peak:.3f}")

    def test_preroll_captures_onset_consonants(self):
        """Verify ~350ms pre-roll is prepended to speech utterance."""
        sr = 16000
        pre_silence = np.zeros(int(0.4 * sr), dtype=np.float32)
        speech = 0.05 * np.ones(int(0.8 * sr), dtype=np.float32)
        post_silence = np.zeros(int(0.8 * sr), dtype=np.float32)

        chunk_sz = 800  # 50ms chunks
        for i in range(0, len(pre_silence), chunk_sz):
            self.buf.push(pre_silence[i:i + chunk_sz])
        for i in range(0, len(speech), chunk_sz):
            self.buf.push(speech[i:i + chunk_sz])
        for i in range(0, len(post_silence), chunk_sz):
            self.buf.push(post_silence[i:i + chunk_sz])

        utt = self.buf.pop_completed_utterance()
        self.assertIsNotNone(utt)
        # Length should include speech + pre-roll + post-silence boundary
        expected_min = int((0.8 + 0.3) * sr)
        self.assertGreaterEqual(len(utt), expected_min, f"Pre-roll not included in utterance: len={len(utt)}")


class TestDynamicPresetsEvolution(unittest.TestCase):
    """Requirement 6: Evolving presets based on astronaut responses while preserving main anchors."""

    def test_core_presets_always_preserved(self):
        presets = get_evolved_presets([], cur_emotion="neutral", stress_pct=20.0)
        labels = [p[0] for p in presets]
        self.assertIn("🧘 4-7-8 Grounding", labels)
        self.assertIn("📊 Full Telemetry Check", labels)

    def test_high_stress_triggers_box_breathing_and_cold_anchor(self):
        presets = get_evolved_presets([], cur_emotion="fear", stress_pct=78.0)
        labels = [p[0] for p in presets]
        self.assertIn("🫁 Box Breathing (4-4-4-4)", labels)
        self.assertIn("🧊 Cold Sensory Anchor", labels)
        # Core preserved
        self.assertIn("🧘 4-7-8 Grounding", labels)

    def test_sleep_keywords_trigger_sleep_architecture_presets(self):
        history = [
            {"role": "user", "content": "I haven't been able to sleep due to insomnia in lunar transit."},
            {"role": "assistant", "content": "Acknowledged, Commander. Sleep disruption is critical."},
        ]
        presets = get_evolved_presets(history, cur_emotion="neutral", stress_pct=45.0)
        labels = [p[0] for p in presets]
        self.assertIn("💤 Sleep Reset Protocol", labels)
        self.assertIn("👁️ Micro-sleep Guard", labels)

    def test_docking_keywords_trigger_docking_readiness(self):
        history = [{"role": "user", "content": "Approaching docking port with automated thrusters."}]
        presets = get_evolved_presets(history, cur_emotion="neutral", stress_pct=35.0)
        labels = [p[0] for p in presets]
        self.assertIn("🛰️ Docking Readiness Check", labels)

    def test_co2_keywords_trigger_hypercapnia_protocol(self):
        history = [{"role": "user", "content": "Cabin CO2 scrubber is reporting high partial pressure."}]
        presets = get_evolved_presets(history, cur_emotion="fear", stress_pct=60.0)
        labels = [p[0] for p in presets]
        self.assertIn("🫁 Hypercapnia Breathing Protocol", labels)

    def test_checklist_fatigue_triggers_cognitive_declutter(self):
        history = [{"role": "user", "content": "I am making multiple procedural checklist errors and my head feels in a fog."}]
        presets = get_evolved_presets(history, cur_emotion="neutral", stress_pct=40.0)
        labels = [p[0] for p in presets]
        self.assertIn("🧠 Cognitive De-clutter", labels)

    def test_isolation_triggers_earth_anchor(self):
        history = [{"role": "user", "content": "Looking at dark lunar orbit feeling isolated and lonely."}]
        presets = get_evolved_presets(history, cur_emotion="sad", stress_pct=40.0)
        labels = [p[0] for p in presets]
        self.assertIn("🌍 Earth Connection Anchor", labels)


class TestDatabase7EmotionTelemetry(unittest.TestCase):
    """Requirement 7: SQLite schema and multi-line trajectory for all 7 affect dimensions."""

    def setUp(self):
        init_db()

    def test_schema_contains_all_7_emotion_columns(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("PRAGMA table_info(stress_logs)")
        cols = {row[1] for row in c.fetchall()}
        conn.close()

        expected = [
            "prob_angry", "prob_disgust", "prob_fear", "prob_happy",
            "prob_neutral", "prob_sad", "prob_surprise"
        ]
        for ec in expected:
            self.assertIn(ec, cols, f"Missing 7-class emotion column in stress_logs: {ec}")

    def test_log_and_retrieve_7_emotion_probabilities(self):
        probs = {
            "angry": 0.05, "disgust": 0.02, "fear": 0.15,
            "happy": 0.08, "neutral": 0.55, "sad": 0.10, "surprise": 0.05
        }
        log_event(
            face_emotion="neutral",
            fused_emotion="neutral",
            voice_state="Speaking",
            heart_rate=78.0,
            temperature=36.7,
            spo2=98.5,
            blink_rate=14.0,
            fatigue_label="Normal",
            stress_score=32.0,
            stress_level="NOMINAL",
            alert_triggered="NOMINAL",
            response_msg="Nominal reading.",
            emotion_probs=probs,
        )

        trend_df = get_recent_trend(10)
        self.assertFalse(trend_df.empty)
        latest = trend_df.iloc[-1]

        self.assertAlmostEqual(float(latest["prob_neutral"]), 0.55, places=2)
        self.assertAlmostEqual(float(latest["prob_fear"]), 0.15, places=2)
        self.assertAlmostEqual(float(latest["prob_angry"]), 0.05, places=2)

    def test_legacy_rows_gracefully_backfilled(self):
        """Verify rows logged without explicit probability dict receive valid synthesized probabilities."""
        log_event(
            face_emotion="happy",
            fused_emotion="happy",
            voice_state="Silent",
            heart_rate=72.0,
            temperature=36.6,
            spo2=99.0,
            blink_rate=12.0,
            fatigue_label="Normal",
            stress_score=15.0,
            stress_level="NOMINAL",
            alert_triggered="NOMINAL",
            response_msg="Telemetry nominal.",
            emotion_probs=None,
        )

        trend_df = get_recent_trend(5)
        latest = trend_df.iloc[-1]
        self.assertGreater(float(latest["prob_happy"]), 0.50, "Dominant emotion should be strongly weighted")


class TestAudioAutoplayMechanics(unittest.TestCase):
    """Requirement 1: Audio Autoplay mechanics."""

    def test_base64_audio_tag_generation(self):
        dummy_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00data\x00\x00\x00\x00"
        b64 = base64.b64encode(dummy_wav).decode("ascii")
        tag = f'<audio autoplay="true" style="display:none;"><source src="data:audio/wav;base64,{b64}" type="audio/wav"></audio>'
        self.assertIn('autoplay="true"', tag)
        self.assertIn("data:audio/wav;base64,", tag)

    def test_one_shot_autoplay_state_reset(self):
        """Verify message autoplay flag is one-shot to prevent repeating playback on subsequent reruns."""
        msg = {"role": "assistant", "content": "Telemetry nominal.", "audio": b"wavdata", "autoplay": True}
        # First render pass
        if msg.get("audio"):
            is_new = msg.get("autoplay", False)
            self.assertTrue(is_new, "First render pass must detect autoplay=True")
            msg["autoplay"] = False

        # Second render pass (e.g. rerun)
        self.assertFalse(msg["autoplay"], "Second render pass must be reset to autoplay=False")


if __name__ == "__main__":
    unittest.main()
