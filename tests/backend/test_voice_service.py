"""
MAITRI 2.0 — Tests for VoiceService, Vosk, Safety Confirmation Gate
"""

import time
import pytest
from backend.services.intent_parser import SafetyConfirmationGate, parse_intent
from backend.services.voice_service import VoiceService, _compute_rms_int16


class TestSafetyConfirmationGate:
    def test_critical_action_transition(self):
        gate = SafetyConfirmationGate(timeout_sec=5.0)
        t0 = time.time()
        msg = gate.request_critical_action("critical_override", t0)
        assert "Safety confirmation required" in msg
        assert gate.is_awaiting_confirmation(t0 + 1.0) is True

    def test_critical_action_timeout(self):
        gate = SafetyConfirmationGate(timeout_sec=2.0)
        t0 = time.time()
        gate.request_critical_action("critical_override", t0)
        # Check after timeout
        assert gate.is_awaiting_confirmation(t0 + 3.0) is False

    def test_confirm_action_success(self):
        gate = SafetyConfirmationGate(timeout_sec=5.0)
        t0 = time.time()
        gate.request_critical_action("critical_override", t0)
        confirmed = gate.confirm_action(t0 + 1.0)
        assert confirmed == "critical_override"
        # Subsequent check should be False since action was consumed
        assert gate.is_awaiting_confirmation(t0 + 2.0) is False

    def test_confirm_action_after_timeout(self):
        gate = SafetyConfirmationGate(timeout_sec=1.0)
        t0 = time.time()
        gate.request_critical_action("critical_override", t0)
        confirmed = gate.confirm_action(t0 + 2.0)
        assert confirmed is None


class TestVoiceServiceVosk:
    def test_init_vosk_loads_model(self):
        svc = VoiceService()
        assert svc.is_vosk_ready() is False
        success = svc.init_vosk()
        assert success is True
        assert svc.is_vosk_ready() is True

    def test_push_audio_chunk_rms_and_level(self):
        svc = VoiceService()
        events = []

        async def cb(evt):
            events.append(evt)

        svc.set_event_callback(cb)

        from backend.state import AppState
        state = AppState()

        # Feed 100ms of 16kHz silence
        import asyncio
        silence = bytes(3200)
        asyncio.run(svc.push_audio_chunk(silence, state))

        # Check emitted level
        assert any(e.get("type") == "audio_level" for e in events)
