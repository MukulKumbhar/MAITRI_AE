"""
MAITRI 2.0 — Intent Parser & Safety Confirmation Engine
Offline Voice Command Intent Detection for Astronaut Cockpit
"""

import re
from typing import Any, Dict, List, Optional, Tuple

INTENT_PATTERNS: Dict[str, List[str]] = {
    "navigate_live": [
        "open live feed", "open live", "show live", "live feed", "live seed", "live cockpit",
        "go to live", "switch to live", "switch to live feed", "tab one", "tab 1", "tab won",
        "monitoring", "dashboard", "open monitoring", "open cockpit", "show cockpit",
        "switch to cockpit", "go to cockpit", "cockpit", "camera", "webcam", "astronaut feed",
        "live stream", "live view", "first tab", "open first tab", "switch to first tab",
        "switch tab 1", "switch to tab 1", "switch tab one", "switch to tab one",
        "tab live", "open tab live", "take me to live", "take me to cockpit",
        "show live tab", "live tab", "open feed", "feed", "seed", "live",
    ],
    "navigate_logs": [
        "open logs", "show logs", "mission logs", "go to logs", "switch to logs",
        "tab two", "tab 2", "tab to", "tab too", "telemetry history", "log view", "show telemetry", "view logs",
        "second tab", "open second tab", "switch to second tab", "switch tab 2", "switch to tab 2",
        "switch tab two", "switch to tab two", "telemetry logs", "telemetry", "trends", "charts",
        "analytics", "history", "tab logs", "open tab logs", "take me to logs",
        "show logs tab", "logs tab", "database", "view telemetry", "show trends",
        "logs", "log", "locks",
    ],
    "navigate_mission": [
        "open mission", "show mission", "mission control", "go to mission",
        "switch to mission", "switch to mission control", "tab three", "tab 3",
        "demo scenarios", "control panel", "demo", "run demo", "third tab",
        "open third tab", "switch to third tab", "switch tab 3", "switch to tab 3",
        "switch tab three", "switch to tab three", "dtn", "outbox", "dossier", "simulation",
        "tab demo", "open tab demo", "take me to demo", "show demo", "switch to demo",
        "tab mission", "open tab mission", "scenarios", "mission",
    ],
    "navigate_support": [
        "open support", "psychological support", "ai support", "go to support",
        "switch to support", "tab four", "tab 4", "tab for", "tab fore", "mental health", "counselor",
        "psych support", "open ai support", "fourth tab", "open fourth tab", "switch to fourth tab",
        "switch tab 4", "switch to tab 4", "switch tab four", "switch to tab four",
        "chat", "open chat", "doctor", "clinical", "talk to maitri", "tab support",
        "open tab support", "take me to support", "show support", "clinical ai",
        "support engine", "psychological", "support",
    ],
    "set_heart_rate": [
        "set heart rate to", "change heart rate to", "heart rate to", "set heart rate",
        "that heart rate to", "make heart rate", "pulse to", "set pulse to", "heart rate",
    ],
    "set_oxygen": [
        "set oxygen to", "blood oxygen to", "set spo2 to", "oxygen to", "set oxygen",
        "set spo2", "that oxygen to", "spo2 to", "blood oxygen",
    ],
    "read_vitals": [
        "show vitals", "read vitals", "display vitals", "what are my vitals",
        "vitals status", "check vitals", "check my vitals", "how am i doing",
        "my readings", "tell me my vitals", "my vitals", "the vitals", "vitals",
        "vital", "read my vitals", "status of vitals",
    ],
    "read_stress": [
        "show stress", "what is my stress level", "what is my stress",
        "how stressed am i", "stress status", "stress level", "my stress",
        "check stress", "psychological status", "the stress", "stress",
        "read stress", "how am i feeling",
    ],
    "log_reading": [
        "log reading to mission database", "log reading to database", "log reading",
        "save reading", "log current reading", "log current", "record reading",
        "log to database", "save to database", "log now", "record telemetry",
    ],
    "start_breathing": [
        "start breathing exercise", "start breathing", "breathing exercise",
        "box breathing", "four seven eight breathing", "four seven eight", "4 7 8",
        "initiate grounding", "grounding", "relax", "calm down", "help me breathe",
        "fox breathing",
    ],
    "watchdog_ack": [
        "acknowledge watchdog", "i am here", "check in", "acknowledge",
        "i am okay", "i'm here", "i'm okay", "confirm presence",
        "check-in", "at knowledge",
    ],
    "critical_override": [
        "override incapacitation", "cancel emergency", "dismiss critical alarm",
        "reset emergency", "override system",
    ],
    "confirm_critical": [
        "confirm override", "confirm emergency reset", "yes confirm", "confirm reset",
    ],
}

WAKE_WORDS = ["maitri", "matri", "maytri", "maitre", "matrix", "may tree", "my tree", "nightly", "mighty"]

# Phonetic corrections for common Vosk acoustic misrecognitions of spaceflight terms
PHONETIC_REPLACEMENTS = [
    (r"\blive seed\b", "live feed"),
    (r"\bseed\b", "feed"),
    (r"\bfox breathing\b", "box breathing"),
    (r"\bs p o two\b", "spo2"),
    (r"\bsp o2\b", "spo2"),
    (r"\bs p o 2\b", "spo2"),
    (r"\bsp o two\b", "spo2"),
    (r"\bfor seven eight\b", "four seven eight"),
    (r"\bat knowledge\b", "acknowledge"),
    (r"\b(her three|hurt rate|part rate|hard rate)\b", "heart rate"),
    (r"\bthat her\b", "set heart"),
    (r"\bthat heart rate\b", "set heart rate"),
]

# Critical intents that require a two-step confirmation safety gate
CRITICAL_SAFETY_INTENTS = {"critical_override"}


def words_to_number(text: str) -> Optional[float]:
    """Convert spoken English number phrases to numeric values (e.g. 'eighty five' -> 85.0)."""
    units = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17, "eighteen": 18, "nineteen": 19,
    }
    tens = {
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
        "seventy": 70, "eighty": 80, "ninety": 90,
    }
    tokens = text.lower().replace("-", " ").split()
    total = 0
    current = 0
    found = False

    for tok in tokens:
        if tok in units:
            current += units[tok]
            found = True
        elif tok in tens:
            current += tens[tok]
            found = True
        elif tok in ("hundred", "hundreds"):
            current = (current if current > 0 else 1) * 100
            found = True
        else:
            if found:
                total += current
                current = 0

    total += current
    return float(total) if found else None


def levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,       # deletion
                curr[j] + 1,           # insertion
                prev[j] + (ca != cb),  # substitution
            ))
        prev = curr
    return prev[-1]


class SafetyConfirmationGate:
    """
    Guards safety-critical actions.
    When a critical intent is requested, transitions to AWAITING_CONFIRMATION for 10s.
    Only executes the critical action if confirmed within window.
    """
    def __init__(self, timeout_sec: float = 10.0):
        self.timeout_sec = timeout_sec
        self.pending_intent: Optional[str] = None
        self.pending_time: float = 0.0

    def request_critical_action(self, intent: str, current_time: float) -> str:
        self.pending_intent = intent
        self.pending_time = current_time
        return (
            "Safety confirmation required. Say 'Confirm override' or press the console button."
        )

    def is_awaiting_confirmation(self, current_time: float) -> bool:
        if self.pending_intent and (current_time - self.pending_time <= self.timeout_sec):
            return True
        self.pending_intent = None
        return False

    def confirm_action(self, current_time: float) -> Optional[str]:
        if self.is_awaiting_confirmation(current_time):
            action = self.pending_intent
            self.pending_intent = None
            return action
        return None

    def cancel(self) -> None:
        self.pending_intent = None


def parse_intent(transcript: str, confidence_threshold: float = 0.6) -> Dict[str, Any]:
    """
    Parse a voice transcript into an intent with fuzzy matching and entity extraction.
    """
    text = transcript.lower().strip()
    # Apply phonetic corrections for common acoustic misrecognitions
    for pattern_rx, replacement in PHONETIC_REPLACEMENTS:
        text = re.sub(pattern_rx, replacement, text)

    # Remove punctuation except numbers and periods
    text_clean = re.sub(r"[^\w\s\.]", " ", text)
    tokens = text_clean.split()

    # Check for wake word
    has_wake_word = any(
        any(levenshtein(tok, wake) <= 1 for wake in WAKE_WORDS)
        for tok in tokens
    )

    # Candidate strings to evaluate: full text and wake-word stripped text
    tokens_no_wake = [
        t for t in tokens if not any(levenshtein(t, w) <= 1 for w in WAKE_WORDS)
    ]
    candidate_texts = [text_clean]
    if tokens_no_wake and len(tokens_no_wake) < len(tokens):
        candidate_texts.append(" ".join(tokens_no_wake))

    best_intent = None
    best_score = 0.0
    best_pattern = ""

    for cand_text in candidate_texts:
        cand_tokens = cand_text.split()
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                # Exact match or substring match (highest confidence)
                if pattern == cand_text:
                    score = 1.0
                elif pattern in cand_text:
                    score = 0.95
                else:
                    pattern_tokens = pattern.split()
                    max_window_score = 0.0
                    for i in range(max(1, len(cand_tokens) - len(pattern_tokens) + 1)):
                        window = cand_tokens[i:i + len(pattern_tokens)]
                        if not window:
                            continue
                        matched = sum(
                            1 for pt, tt in zip(pattern_tokens, window)
                            if (pt == tt or (len(pt) > 4 and levenshtein(pt, tt) <= 1))
                        )
                        window_score = matched / len(pattern_tokens)
                        max_window_score = max(max_window_score, window_score)
                    score = max_window_score * 0.9

                # Longer patterns break ties to prioritize specific commands over generic ones
                if score > best_score or (score == best_score and len(pattern) > len(best_pattern)):
                    best_score = score
                    best_intent = intent
                    best_pattern = pattern

    # Extract entities (numeric values for sliders / vitals)
    entities: Dict[str, Any] = {}
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", text)
    if numbers:
        entities["value"] = float(numbers[0])
    else:
        word_num = words_to_number(text)
        if word_num is not None:
            entities["value"] = word_num

    # Check if this requires safety confirmation
    requires_confirmation = (best_intent in CRITICAL_SAFETY_INTENTS) if best_intent else False

    return {
        "intent": best_intent if best_score >= confidence_threshold else None,
        "confidence": round(best_score, 3),
        "matched_pattern": best_pattern,
        "has_wake_word": has_wake_word,
        "requires_confirmation": requires_confirmation,
        "entities": entities,
        "transcript": transcript,
    }
