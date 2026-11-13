"""
MAITRI 2.0 — M6: Database Module
SQLite-backed telemetry logging with graceful schema migration,
cryptographic SHA-256 hash chaining, and IEC 60601-1-8 alarm events ledger.
"""

import datetime
import hashlib
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

DB_FILE = "maitri_logs.db"
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stress_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT,
    face_emotion    TEXT,
    fused_emotion   TEXT,
    voice_state     TEXT,
    heart_rate      REAL,
    temperature     REAL,
    spo2            REAL,
    blink_rate      REAL,
    fatigue_label   TEXT,
    stress_score    REAL,
    stress_level    TEXT,
    alert_triggered TEXT,
    response_msg    TEXT,
    prob_angry      REAL DEFAULT 0.0,
    prob_disgust    REAL DEFAULT 0.0,
    prob_fear       REAL DEFAULT 0.0,
    prob_happy      REAL DEFAULT 0.0,
    prob_neutral    REAL DEFAULT 0.0,
    prob_sad        REAL DEFAULT 0.0,
    prob_surprise   REAL DEFAULT 0.0,
    rmssd           REAL DEFAULT 42.0,
    sdnn            REAL DEFAULT 55.0,
    baevsky_index   REAL DEFAULT 95.0,
    respiratory_rate REAL DEFAULT 14.0,
    co2_mmhg        REAL DEFAULT 3.0,
    o2_percent      REAL DEFAULT 20.9,
    pressure_kpa    REAL DEFAULT 101.3,
    ambient_temp_c  REAL DEFAULT 22.0,
    noise_dba       REAL DEFAULT 58.0,
    prev_hash       TEXT DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
    record_hash     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS psych_support_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT,
    crew_member     TEXT,
    mission_phase   TEXT,
    input_channel   TEXT,
    astronaut_query TEXT,
    detected_emotion TEXT,
    stress_pct      REAL,
    ai_response     TEXT,
    has_audio       INTEGER
);

CREATE TABLE IF NOT EXISTS alarm_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_id        TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    priority        TEXT NOT NULL,
    code            TEXT NOT NULL,
    message         TEXT NOT NULL,
    source          TEXT DEFAULT 'clinical',
    status          TEXT NOT NULL,
    acknowledged_at TEXT,
    resolved_at     TEXT,
    escalated_from  TEXT,
    occurrence_count INTEGER DEFAULT 1,
    prev_hash       TEXT DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
    record_hash     TEXT DEFAULT ''
);
"""

_MIGRATIONS = [
    ("fused_emotion",   "TEXT DEFAULT 'Neutral'"),
    ("spo2",            "REAL DEFAULT 98.0"),
    ("blink_rate",      "REAL DEFAULT 0.0"),
    ("fatigue_label",   "TEXT DEFAULT 'Normal'"),
    ("stress_level",    "TEXT DEFAULT 'NOMINAL'"),
    ("prob_angry",      "REAL DEFAULT 0.0"),
    ("prob_disgust",    "REAL DEFAULT 0.0"),
    ("prob_fear",       "REAL DEFAULT 0.0"),
    ("prob_happy",      "REAL DEFAULT 0.0"),
    ("prob_neutral",    "REAL DEFAULT 0.0"),
    ("prob_sad",        "REAL DEFAULT 0.0"),
    ("prob_surprise",   "REAL DEFAULT 0.0"),
    ("rmssd",           "REAL DEFAULT 42.0"),
    ("sdnn",            "REAL DEFAULT 55.0"),
    ("baevsky_index",   "REAL DEFAULT 95.0"),
    ("respiratory_rate","REAL DEFAULT 14.0"),
    ("co2_mmhg",        "REAL DEFAULT 3.0"),
    ("o2_percent",      "REAL DEFAULT 20.9"),
    ("pressure_kpa",    "REAL DEFAULT 101.3"),
    ("ambient_temp_c",  "REAL DEFAULT 22.0"),
    ("noise_dba",       "REAL DEFAULT 58.0"),
    ("prev_hash",       "TEXT DEFAULT '0000000000000000000000000000000000000000000000000000000000000000'"),
    ("record_hash",     "TEXT DEFAULT ''"),
]


def init_db(db_path: Optional[str] = None) -> None:
    """Create tables and apply any pending column migrations."""
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript(_SCHEMA)

    c.execute("PRAGMA table_info(stress_logs)")
    existing = {row[1] for row in c.fetchall()}
    for col_name, col_def in _MIGRATIONS:
        if col_name not in existing:
            c.execute(f"ALTER TABLE stress_logs ADD COLUMN {col_name} {col_def}")

    conn.commit()
    conn.close()


def compute_telemetry_hash(prev_hash: str, payload_str: str) -> str:
    """Computes SHA-256 hash chaining prev_hash and payload string."""
    raw = f"{prev_hash}|{payload_str}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def log_event(
    face_emotion: str,
    fused_emotion: str,
    voice_state: str,
    heart_rate: float,
    temperature: float,
    spo2: float,
    blink_rate: float,
    fatigue_label: str,
    stress_score: float,
    stress_level: str,
    alert_triggered: str,
    response_msg: str,
    emotion_probs: dict = None,
    rmssd: float = 42.0,
    sdnn: float = 55.0,
    baevsky_index: float = 95.0,
    respiratory_rate: float = 14.0,
    co2_mmhg: float = 3.0,
    o2_percent: float = 20.9,
    pressure_kpa: float = 101.3,
    ambient_temp_c: float = 22.0,
    noise_dba: float = 58.0,
    db_path: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Insert one telemetry record with full cardio-respiratory, environmental metrics,
    and cryptographic SHA-256 hash chaining.
    Returns (prev_hash, record_hash).
    """
    path = db_path or DB_FILE
    init_db(path)

    probs = emotion_probs or {}
    dom = (fused_emotion or face_emotion or "neutral").lower()

    p_angry    = float(probs.get("angry", 1.0 if dom == "angry" else 0.0))
    p_disgust  = float(probs.get("disgust", 1.0 if dom == "disgust" else 0.0))
    p_fear     = float(probs.get("fear", 1.0 if dom == "fear" else 0.0))
    p_happy    = float(probs.get("happy", 1.0 if dom == "happy" else 0.0))
    p_neutral  = float(probs.get("neutral", 1.0 if dom in ("neutral", "nominal") else 0.0))
    p_sad      = float(probs.get("sad", 1.0 if dom == "sad" else 0.0))
    p_surprise = float(probs.get("surprise", 1.0 if dom == "surprise" else 0.0))

    if p_angry + p_disgust + p_fear + p_happy + p_neutral + p_sad + p_surprise == 0:
        p_neutral = 1.0

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute("SELECT record_hash FROM stress_logs WHERE record_hash IS NOT NULL AND record_hash != '' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    prev_hash = row[0] if (row and row[0]) else GENESIS_HASH

    canonical_payload = (
        f"{timestamp}|{face_emotion}|{fused_emotion}|{voice_state}|"
        f"{heart_rate:.1f}|{temperature:.2f}|{spo2:.1f}|{blink_rate:.1f}|{fatigue_label}|"
        f"{stress_score:.1f}|{stress_level}|{rmssd:.1f}|{sdnn:.1f}|{baevsky_index:.1f}|"
        f"{respiratory_rate:.1f}|{co2_mmhg:.2f}|{o2_percent:.2f}|{pressure_kpa:.1f}|"
        f"{ambient_temp_c:.1f}|{noise_dba:.1f}"
    )
    record_hash = compute_telemetry_hash(prev_hash, canonical_payload)

    c.execute(
        """INSERT INTO stress_logs
           (timestamp, face_emotion, fused_emotion, voice_state,
            heart_rate, temperature, spo2, blink_rate, fatigue_label,
            stress_score, stress_level, alert_triggered, response_msg,
            prob_angry, prob_disgust, prob_fear, prob_happy, prob_neutral, prob_sad, prob_surprise,
            rmssd, sdnn, baevsky_index, respiratory_rate,
            co2_mmhg, o2_percent, pressure_kpa, ambient_temp_c, noise_dba,
            prev_hash, record_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            timestamp,
            face_emotion,
            fused_emotion,
            voice_state,
            heart_rate,
            temperature,
            spo2,
            blink_rate,
            fatigue_label,
            stress_score,
            stress_level,
            alert_triggered,
            response_msg,
            p_angry,
            p_disgust,
            p_fear,
            p_happy,
            p_neutral,
            p_sad,
            p_surprise,
            rmssd,
            sdnn,
            baevsky_index,
            respiratory_rate,
            co2_mmhg,
            o2_percent,
            pressure_kpa,
            ambient_temp_c,
            noise_dba,
            prev_hash,
            record_hash,
        ),
    )
    conn.commit()
    conn.close()
    return prev_hash, record_hash


def verify_stress_logs_hash_chain(db_path: Optional[str] = None) -> Tuple[bool, Optional[int]]:
    """
    Verifies that stress_logs forms an unbroken cryptographic SHA-256 hash chain.
    Returns (is_valid, failing_record_id).
    """
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        """SELECT id, prev_hash, record_hash, timestamp, face_emotion, fused_emotion,
                  voice_state, heart_rate, temperature, spo2, blink_rate, fatigue_label,
                  stress_score, stress_level, rmssd, sdnn, baevsky_index, respiratory_rate,
                  co2_mmhg, o2_percent, pressure_kpa, ambient_temp_c, noise_dba
           FROM stress_logs ORDER BY id ASC"""
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        return True, None

    expected_prev = rows[0][1] or GENESIS_HASH
    for r in rows:
        rec_id = r[0]
        actual_prev = r[1]
        actual_hash = r[2]

        if not actual_hash:
            continue

        if actual_prev != expected_prev:
            return False, rec_id

        canonical_payload = (
            f"{r[3]}|{r[4]}|{r[5]}|{r[6]}|"
            f"{float(r[7]):.1f}|{float(r[8]):.2f}|{float(r[9]):.1f}|{float(r[10]):.1f}|{r[11]}|"
            f"{float(r[12]):.1f}|{r[13]}|{float(r[14]):.1f}|{float(r[15]):.1f}|{float(r[16]):.1f}|"
            f"{float(r[17]):.1f}|{float(r[18]):.2f}|{float(r[19]):.2f}|{float(r[20]):.1f}|"
            f"{float(r[21]):.1f}|{float(r[22]):.1f}"
        )
        computed = compute_telemetry_hash(actual_prev, canonical_payload)
        if computed != actual_hash:
            return False, rec_id

        expected_prev = actual_hash

    return True, None


def log_alarm_event(
    alarm_id: str,
    priority: str,
    code: str,
    message: str,
    source: str = "clinical",
    status: str = "ACTIVE",
    acknowledged_at: Optional[str] = None,
    resolved_at: Optional[str] = None,
    escalated_from: Optional[str] = None,
    occurrence_count: int = 1,
    db_path: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Log an IEC 60601-1-8 alarm event to the tamper-evident cryptographic alarm ledger.
    Returns (prev_hash, record_hash).
    """
    path = db_path or DB_FILE
    init_db(path)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(path)
    c = conn.cursor()

    c.execute("SELECT record_hash FROM alarm_events WHERE record_hash IS NOT NULL AND record_hash != '' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    prev_hash = row[0] if (row and row[0]) else GENESIS_HASH

    canonical = f"{timestamp}|{alarm_id}|{priority}|{code}|{message}|{source}|{status}|{occurrence_count}"
    record_hash = compute_telemetry_hash(prev_hash, canonical)

    c.execute(
        """INSERT INTO alarm_events
           (alarm_id, timestamp, priority, code, message, source, status,
            acknowledged_at, resolved_at, escalated_from, occurrence_count, prev_hash, record_hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            alarm_id,
            timestamp,
            priority,
            code,
            message,
            source,
            status,
            acknowledged_at,
            resolved_at,
            escalated_from,
            occurrence_count,
            prev_hash,
            record_hash,
        ),
    )
    conn.commit()
    conn.close()
    return prev_hash, record_hash


def verify_alarm_events_hash_chain(db_path: Optional[str] = None) -> Tuple[bool, Optional[int]]:
    """
    Verifies that alarm_events forms an unbroken cryptographic SHA-256 hash chain.
    Returns (is_valid, failing_record_id).
    """
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        """SELECT id, prev_hash, record_hash, timestamp, alarm_id, priority, code,
                  message, source, status, occurrence_count
           FROM alarm_events ORDER BY id ASC"""
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        return True, None

    expected_prev = rows[0][1] or GENESIS_HASH
    for r in rows:
        rec_id = r[0]
        actual_prev = r[1]
        actual_hash = r[2]

        if not actual_hash:
            continue

        if actual_prev != expected_prev:
            return False, rec_id

        canonical = f"{r[3]}|{r[4]}|{r[5]}|{r[6]}|{r[7]}|{r[8]}|{r[9]}|{r[10]}"
        computed = compute_telemetry_hash(actual_prev, canonical)
        if computed != actual_hash:
            return False, rec_id

        expected_prev = actual_hash

    return True, None


def get_alarm_events(limit: int = 100, db_path: Optional[str] = None) -> pd.DataFrame:
    """Return recent alarm events ledger records, newest first."""
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            f"SELECT * FROM alarm_events ORDER BY id DESC LIMIT {limit}", conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def get_logs(db_path: Optional[str] = None) -> pd.DataFrame:
    """Return all logs, newest first."""
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    df = pd.read_sql_query(
        "SELECT * FROM stress_logs ORDER BY id DESC", conn
    )
    conn.close()
    return df


def get_recent_trend(n: int = 60, db_path: Optional[str] = None) -> pd.DataFrame:
    """Return the last n records with all 7 emotion probabilities for trend charts."""
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            f"""SELECT timestamp, stress_score, stress_level, fused_emotion,
                       prob_angry, prob_disgust, prob_fear, prob_happy,
                       prob_neutral, prob_sad, prob_surprise
                FROM stress_logs ORDER BY id DESC LIMIT {n}""",
            conn,
        )
    except Exception:
        df = pd.read_sql_query(
            f"SELECT timestamp, stress_score, stress_level, fused_emotion FROM stress_logs ORDER BY id DESC LIMIT {n}",
            conn,
        )
    conn.close()

    df = df.iloc[::-1].reset_index(drop=True)

    emo_cols = ["prob_angry", "prob_disgust", "prob_fear", "prob_happy", "prob_neutral", "prob_sad", "prob_surprise"]
    for col in emo_cols:
        if col not in df.columns:
            df[col] = 0.0

    for idx, row in df.iterrows():
        total_p = sum(float(row[c]) for c in emo_cols)
        if total_p < 0.01:
            dom = str(row.get("fused_emotion", "neutral")).lower()
            for c in emo_cols:
                df.at[idx, c] = 0.05
            target_col = f"prob_{dom}" if f"prob_{dom}" in emo_cols else "prob_neutral"
            df.at[idx, target_col] = 0.70

    return df


def log_psych_event(
    crew_member: str,
    mission_phase: str,
    input_channel: str,
    astronaut_query: str,
    detected_emotion: str,
    stress_pct: float,
    ai_response: str,
    has_audio: bool = False,
    db_path: Optional[str] = None,
) -> None:
    """Log an AI psychological support dialogue turn."""
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO psych_support_logs (
            timestamp, crew_member, mission_phase, input_channel,
            astronaut_query, detected_emotion, stress_pct, ai_response, has_audio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            crew_member,
            mission_phase,
            input_channel,
            astronaut_query,
            detected_emotion,
            round(stress_pct, 1),
            ai_response,
            1 if has_audio else 0,
        ),
    )
    conn.commit()
    conn.close()


def get_psych_logs(limit: int = 50, db_path: Optional[str] = None) -> pd.DataFrame:
    """Return recent psychological support logs, newest first."""
    path = db_path or DB_FILE
    init_db(path)
    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            f"SELECT * FROM psych_support_logs ORDER BY id DESC LIMIT {limit}", conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df
