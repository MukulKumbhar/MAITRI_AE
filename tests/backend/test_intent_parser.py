"""
MAITRI 2.0 — Intent Parser Tests (Phase 1 stubs, Phase 3 full implementation)
Tests fuzzy intent matching and synonym expansion.
This module tests the IntentParser class that will be used in Phase 3.
We define the parser here now so it's ready for Phase 3 integration.
"""

import sys
from pathlib import Path
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.services.intent_parser import (
    parse_intent,
    words_to_number,
    levenshtein,
    SafetyConfirmationGate,
    INTENT_PATTERNS,
    WAKE_WORDS,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWakeWordDetection:
    def test_exact_wake_word(self):
        result = parse_intent("maitri show me the vitals")
        assert result["has_wake_word"] is True

    def test_fuzzy_wake_word_matri(self):
        result = parse_intent("matri show vitals")
        assert result["has_wake_word"] is True

    def test_no_wake_word(self):
        result = parse_intent("show me vitals")
        assert result["has_wake_word"] is False

    def test_wake_word_maytri(self):
        result = parse_intent("maytri open live feed")
        assert result["has_wake_word"] is True


class TestNavigationIntents:
    def test_navigate_live_exact(self):
        result = parse_intent("maitri open live feed")
        assert result["intent"] == "navigate_live"
        assert result["confidence"] >= 0.9

    def test_navigate_logs_exact(self):
        result = parse_intent("maitri show logs")
        assert result["intent"] == "navigate_logs"

    def test_navigate_mission_exact(self):
        result = parse_intent("maitri mission control")
        assert result["intent"] == "navigate_mission"

    def test_navigate_support_exact(self):
        result = parse_intent("maitri psychological support")
        assert result["intent"] == "navigate_support"

    def test_tab_number_navigation(self):
        result = parse_intent("maitri tab 2")
        assert result["intent"] == "navigate_logs"

    def test_navigate_live_synonym(self):
        result = parse_intent("maitri go to dashboard")
        assert result["intent"] == "navigate_live"


class TestTelemetryIntents:
    def test_read_vitals_exact(self):
        result = parse_intent("maitri read vitals")
        assert result["intent"] == "read_vitals"
        assert result["confidence"] >= 0.9

    def test_read_vitals_question(self):
        result = parse_intent("what are my vitals")
        assert result["intent"] == "read_vitals"

    def test_read_stress(self):
        result = parse_intent("maitri what is my stress level")
        assert result["intent"] == "read_stress"

    def test_log_reading(self):
        result = parse_intent("maitri log reading")
        assert result["intent"] == "log_reading"

    def test_log_to_database(self):
        result = parse_intent("log to database")
        assert result["intent"] == "log_reading"


class TestInterventionIntents:
    def test_breathing_exercise(self):
        result = parse_intent("maitri start breathing exercise")
        assert result["intent"] == "start_breathing"

    def test_box_breathing(self):
        result = parse_intent("box breathing")
        assert result["intent"] == "start_breathing"

    def test_grounding(self):
        result = parse_intent("maitri grounding")
        assert result["intent"] == "start_breathing"

    def test_four_seven_eight(self):
        result = parse_intent("maitri four seven eight breathing")
        assert result["intent"] == "start_breathing"


class TestEntityExtraction:
    def test_set_heart_rate_value(self):
        result = parse_intent("maitri set heart rate to 85")
        assert result["intent"] == "set_heart_rate"
        assert result["entities"].get("value") == 85.0

    def test_set_oxygen_value(self):
        result = parse_intent("set oxygen to 96")
        assert result["intent"] == "set_oxygen"
        assert result["entities"].get("value") == 96.0


class TestWatchdogIntents:
    def test_acknowledge_watchdog(self):
        result = parse_intent("maitri i am here")
        assert result["intent"] == "watchdog_ack"

    def test_check_in(self):
        result = parse_intent("check in")
        assert result["intent"] == "watchdog_ack"

    def test_i_am_okay(self):
        result = parse_intent("maitri i am okay")
        assert result["intent"] == "watchdog_ack"


class TestFuzzyMatching:
    def test_levenshtein_identity(self):
        assert levenshtein("maitri", "maitri") == 0

    def test_levenshtein_one_edit(self):
        assert levenshtein("matri", "maitri") == 1

    def test_levenshtein_substitution(self):
        assert levenshtein("cat", "bat") == 1

    def test_low_confidence_on_nonsense(self):
        result = parse_intent("xyz qrs foo bar baz", confidence_threshold=0.6)
        assert result["intent"] is None
        assert result["confidence"] < 0.6

    def test_high_confidence_exact_match(self):
        result = parse_intent("open logs")
        assert result["confidence"] == 1.0

    def test_fuzzy_typo_tolerance(self):
        # 'vitls' → 'vitals' (1 char diff) should still match
        result = parse_intent("read vitls status")
        # Should match read_vitals with fuzzy score
        assert result["intent"] == "read_vitals"

    def test_show_vitals_canonical(self):
        result = parse_intent("maitri show vitals")
        assert result["intent"] == "read_vitals"
        assert result["has_wake_word"] is True

    def test_show_stress_canonical(self):
        result = parse_intent("show stress")
        assert result["intent"] == "read_stress"

    def test_switch_navigation(self):
        assert parse_intent("switch to logs")["intent"] == "navigate_logs"
        assert parse_intent("switch to mission")["intent"] == "navigate_mission"
        assert parse_intent("switch to live")["intent"] == "navigate_live"

    def test_spoken_number_words_extraction(self):
        res1 = parse_intent("set heart rate to eighty five")
        assert res1["intent"] == "set_heart_rate"
        assert res1["entities"]["value"] == 85.0

        res2 = parse_intent("set oxygen to ninety eight")
        assert res2["intent"] == "set_oxygen"
        assert res2["entities"]["value"] == 98.0

    def test_words_to_number_helper(self):
        assert words_to_number("seventy") == 70.0
        assert words_to_number("one hundred twenty") == 120.0
        assert words_to_number("forty two") == 42.0

    def test_critical_intent_requires_confirmation(self):
        res = parse_intent("override incapacitation")
        assert res["intent"] == "critical_override"
        assert res["requires_confirmation"] is True
