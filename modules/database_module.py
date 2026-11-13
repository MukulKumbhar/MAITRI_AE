"""
MAITRI 2.0 — M6: Database Module
SQLite-backed telemetry logging with graceful schema migration.
"""

import datetime
import sqlite3

import pandas as pd

DB_FILE = "maitri_logs.db"

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
    prob_surprise   REAL DEFAULT 0.0
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
"""

# Columns added after initial schema — migrated gracefully
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
]


def init_db() -> None:
    """Create tables and apply any pending column migrations."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.executescript(_SCHEMA)

    # Graceful migrations — skip if column already exists
    c.execute("PRAGMA table_info(stress_logs)")
    existing = {row[1] for row in c.fetchall()}
    for col_name, col_def in _MIGRATIONS:
        if col_name not in existing:
            c.execute(f"ALTER TABLE stress_logs ADD COLUMN {col_name} {col_def}")

    conn.commit()
    conn.close()


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
) -> None:
    """Insert one telemetry record including 7-class emotion confidence distribution."""
    # Resolve 7 emotion probabilities
    probs = emotion_probs or {}
    dom = (fused_emotion or face_emotion or "neutral").lower()

    p_angry    = float(probs.get("angry", 1.0 if dom == "angry" else 0.0))
    p_disgust  = float(probs.get("disgust", 1.0 if dom == "disgust" else 0.0))
    p_fear     = float(probs.get("fear", 1.0 if dom == "fear" else 0.0))
    p_happy    = float(probs.get("happy", 1.0 if dom == "happy" else 0.0))
    p_neutral  = float(probs.get("neutral", 1.0 if dom in ("neutral", "nominal") else 0.0))
    p_sad      = float(probs.get("sad", 1.0 if dom == "sad" else 0.0))
    p_surprise = float(probs.get("surprise", 1.0 if dom == "surprise" else 0.0))

    # Fallback if all zero
    if p_angry + p_disgust + p_fear + p_happy + p_neutral + p_sad + p_surprise == 0:
        p_neutral = 1.0

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """INSERT INTO stress_logs
           (timestamp, face_emotion, fused_emotion, voice_state,
            heart_rate, temperature, spo2, blink_rate, fatigue_label,
            stress_score, stress_level, alert_triggered, response_msg,
            prob_angry, prob_disgust, prob_fear, prob_happy, prob_neutral, prob_sad, prob_surprise)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        ),
    )
    conn.commit()
    conn.close()


def get_logs() -> pd.DataFrame:
    """Return all logs, newest first."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT * FROM stress_logs ORDER BY id DESC", conn
    )
    conn.close()
    return df


def get_recent_trend(n: int = 60) -> pd.DataFrame:
    """Return the last n records with all 7 emotion probabilities for trend charts."""
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(
            f"""SELECT timestamp, stress_score, stress_level, fused_emotion,
                       prob_angry, prob_disgust, prob_fear, prob_happy,
                       prob_neutral, prob_sad, prob_surprise
                FROM stress_logs ORDER BY id DESC LIMIT {n}""",
            conn,
        )
    except Exception:
        # Fallback if columns not migrated yet
        df = pd.read_sql_query(
            f"SELECT timestamp, stress_score, stress_level, fused_emotion FROM stress_logs ORDER BY id DESC LIMIT {n}",
            conn,
        )
    conn.close()

    df = df.iloc[::-1].reset_index(drop=True)  # chronological order

    # Backfill missing probabilities if necessary
    emo_cols = ["prob_angry", "prob_disgust", "prob_fear", "prob_happy", "prob_neutral", "prob_sad", "prob_surprise"]
    for col in emo_cols:
        if col not in df.columns:
            df[col] = 0.0

    # Ensure nonzero probability distribution for rows logged before this update
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
) -> None:
    """Log an AI psychological support dialogue turn."""
    conn = sqlite3.connect(DB_FILE)
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


def get_psych_logs(limit: int = 50) -> pd.DataFrame:
    """Return recent psychological support logs, newest first."""
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(
            f"SELECT * FROM psych_support_logs ORDER BY id DESC LIMIT {limit}", conn
        )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

