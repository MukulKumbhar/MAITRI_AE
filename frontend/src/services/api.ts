import {
  LogRecord,
  MissionStatus,
  PsychLogRecord,
  AlarmRecord,
  AlarmSummary,
  SensorAdapterStatus,
  BaselineStatus,
  PVTSessionStatus,
  PVTHistoryRecord,
  SleepStatus,
  SleepHistoryRecord,
  OrbitalCycleInfo,
  ScreenerResult,
  ScreenerHistoryRecord,
  ThirdQuarterAnalysis,
  CabinTelemetry,
  Law2014Hazard,
  MedicalArticle,
  EmergencyChecklist,
  BistReport,
} from "../types";

const API_BASE = "";

// ── General & Pre-existing Endpoints ──────────────────────────────────────────

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export async function fetchLogs(limit = 100, offset = 0): Promise<{ total: number; records: LogRecord[] }> {
  const res = await fetch(`${API_BASE}/api/logs?limit=${limit}&offset=${offset}`);
  return res.json();
}

export async function postLog(entry: Partial<LogRecord>): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/logs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  return res.json();
}

export async function fetchLogTrends(n = 60): Promise<{ count: number; records: any[] }> {
  const res = await fetch(`${API_BASE}/api/logs/trends?n=${n}`);
  return res.json();
}

export async function fetchPsychLogs(limit = 50): Promise<{ count: number; records: PsychLogRecord[] }> {
  const res = await fetch(`${API_BASE}/api/psych/logs?limit=${limit}`);
  return res.json();
}

export async function postPsychChat(query: string, channel = "text"): Promise<{ reply: string; audio_base64?: string }> {
  const res = await fetch(`${API_BASE}/api/psych/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, channel }),
  });
  return res.json();
}

export async function postPsychGrounding(crew = "Astronaut", stress = 70.0): Promise<{ script: string; audio_base64?: string }> {
  const res = await fetch(`${API_BASE}/api/psych/grounding`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ crew, stress }),
  });
  return res.json();
}

export async function fetchPsychPresets(): Promise<{ presets: [string, string][] }> {
  const res = await fetch(`${API_BASE}/api/psych/presets`);
  return res.json();
}

export async function postPsychInit(): Promise<{ success: boolean; message: string; is_loaded: boolean }> {
  const res = await fetch(`${API_BASE}/api/psych/init`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return res.json();
}

export async function fetchPsychStatus(): Promise<{ is_loaded: boolean; error?: string }> {
  const res = await fetch(`${API_BASE}/api/psych/status`);
  return res.json();
}

export async function fetchMissionStatus(): Promise<MissionStatus> {
  const res = await fetch(`${API_BASE}/api/mission/status`);
  return res.json();
}

export async function updateMissionProfile(mission: string, crew: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/mission/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mission, crew }),
  });
  return res.json();
}

export async function compileDossier(): Promise<{ markdown: string; download_url: string }> {
  const res = await fetch(`${API_BASE}/api/mission/dossier`, {
    method: "POST",
  });
  return res.json();
}

export async function acknowledgeWatchdog(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/watchdog/ack`, { method: "POST" });
  return res.json();
}

export async function simulateWatchdog(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/watchdog/simulate`, { method: "POST" });
  return res.json();
}

export async function fetchSettings(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings`);
  return res.json();
}

export async function updateSettings(settings: any): Promise<any> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  return res.json();
}

// ── IEC 60601-1-8 Alarms ───────────────────────────────────────────────────────

export async function fetchAlarms(): Promise<{
  summary: AlarmSummary;
  active: AlarmRecord[];
  is_audio_paused: boolean;
  remaining_pause_sec: number;
}> {
  const res = await fetch(`${API_BASE}/api/clinical/alarms`);
  return res.json();
}

export async function acknowledgeAlarm(code_or_id: string, ack_by = "crew"): Promise<{ status: string; alarm_id?: string; code?: string }> {
  const res = await fetch(`${API_BASE}/api/clinical/alarms/ack`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_or_id, ack_by }),
  });
  return res.json();
}

export async function pauseAlarmAudio(duration_sec = 120.0): Promise<{
  status: string;
  duration_sec: number;
  paused_until: number;
  remaining_sec: number;
}> {
  const res = await fetch(`${API_BASE}/api/clinical/alarms/pause`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ duration_sec }),
  });
  return res.json();
}

export async function resolveAlarm(code_or_id: string): Promise<{ status: string; alarm_id?: string; code?: string }> {
  const res = await fetch(`${API_BASE}/api/clinical/alarms/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_or_id }),
  });
  return res.json();
}

// ── Hardware Sensor Adapter Control ──────────────────────────────────────────

export async function fetchSensors(): Promise<SensorAdapterStatus> {
  const res = await fetch(`${API_BASE}/api/clinical/sensors`);
  return res.json();
}

export async function setSensorMode(mode: "live" | "manual" | "replay"): Promise<{ status: string; mode: string }> {
  const res = await fetch(`${API_BASE}/api/clinical/sensors/mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  return res.json();
}

export async function setSensorScenario(scenario: string, replay_speed?: number): Promise<{
  status: string;
  scenario: string;
  replay_speed?: number;
}> {
  const res = await fetch(`${API_BASE}/api/clinical/sensors/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, replay_speed }),
  });
  return res.json();
}

// ── Personal Baseline & CUSUM ─────────────────────────────────────────────────

export async function fetchBaselineStatus(): Promise<BaselineStatus> {
  const res = await fetch(`${API_BASE}/api/clinical/baseline/status`);
  return res.json();
}

export async function calibrateBaseline(sample: {
  face_probs?: Record<string, number>;
  vitals_strain?: number;
  ear?: number;
  fatigue_strain?: number;
}): Promise<{ status: string; sample_count: number; is_calibrated: boolean }> {
  const res = await fetch(`${API_BASE}/api/clinical/baseline/calibrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sample),
  });
  return res.json();
}

// ── PVT-B Reaction Self-Test (Basner & Dinges 2011) ──────────────────────────

export async function startPVT(crew_member = "Astronaut", duration_s = 180.0): Promise<{
  status: string;
  session: PVTSessionStatus;
}> {
  const res = await fetch(`${API_BASE}/api/clinical/pvt/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ crew_member, duration_s }),
  });
  return res.json();
}

export async function recordPVTResponse(req: { rt_ms?: number; is_false_start?: boolean }): Promise<any> {
  const res = await fetch(`${API_BASE}/api/clinical/pvt/response`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return res.json();
}

export async function fetchPVTStatus(): Promise<{ status: string; session: PVTSessionStatus | null }> {
  const res = await fetch(`${API_BASE}/api/clinical/pvt/status`);
  return res.json();
}

export async function abortPVT(): Promise<{ status: string; session: any }> {
  const res = await fetch(`${API_BASE}/api/clinical/pvt/abort`, {
    method: "POST",
  });
  return res.json();
}

export async function fetchPVTHistory(limit = 20): Promise<{ records: PVTHistoryRecord[] }> {
  const res = await fetch(`${API_BASE}/api/clinical/pvt/history?limit=${limit}`);
  return res.json();
}

// ── Sleep & Circadian Rhythm Endpoints ────────────────────────────────────────

export async function fetchSleepStatus(
  actual_hours = 7.0,
  target_hours = 8.0,
  lux = 120.0
): Promise<SleepStatus> {
  const res = await fetch(
    `${API_BASE}/api/clinical/sleep?actual_hours=${actual_hours}&target_hours=${target_hours}&lux=${lux}`
  );
  return res.json();
}

export async function logSleep(entry: {
  sleep_date: string;
  sleep_duration_hours: number;
  target_sleep_hours?: number;
  light_exposure_lux?: number;
  notes?: string;
  crew_member?: string;
}): Promise<{
  status: string;
  record_hash: string;
  prev_hash: string;
  debt_analysis: any;
}> {
  const res = await fetch(`${API_BASE}/api/clinical/sleep/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  return res.json();
}

export async function fetchSleepHistory(limit = 30): Promise<{ records: SleepHistoryRecord[] }> {
  const res = await fetch(`${API_BASE}/api/clinical/sleep/history?limit=${limit}`);
  return res.json();
}

export async function fetchOrbitalCycle(): Promise<OrbitalCycleInfo> {
  const res = await fetch(`${API_BASE}/api/clinical/sleep/orbital-cycle`);
  return res.json();
}

// ── Clinical Screeners & Third-Quarter Effect ────────────────────────────────

export async function submitScreener(data: {
  screener_type: string;
  item_responses: number[];
  crew_member?: string;
  mission_elapsed_days?: number;
  mission_total_days?: number;
}): Promise<{
  status: string;
  result: ScreenerResult;
  third_quarter_effect: ThirdQuarterAnalysis;
  record_hash: string;
  prev_hash: string;
}> {
  const res = await fetch(`${API_BASE}/api/clinical/screener/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchScreenerHistory(limit = 30): Promise<{ records: ScreenerHistoryRecord[] }> {
  const res = await fetch(`${API_BASE}/api/clinical/screener/history?limit=${limit}`);
  return res.json();
}

export async function fetchThirdQuarter(
  mission_elapsed_days = 90.0,
  mission_total_days = 180.0
): Promise<ThirdQuarterAnalysis> {
  const res = await fetch(
    `${API_BASE}/api/clinical/screener/third-quarter?mission_elapsed_days=${mission_elapsed_days}&mission_total_days=${mission_total_days}`
  );
  return res.json();
}

// ── Cabin Environmental Telemetry & Law 2014 Hazard ──────────────────────────

export async function fetchCabinEnvironment(): Promise<CabinTelemetry> {
  const res = await fetch(`${API_BASE}/api/clinical/environment`);
  return res.json();
}

export async function updateCabinEnvironment(env: {
  cabin_co2?: number;
  cabin_o2?: number;
  cabin_pressure?: number;
  cabin_temp?: number;
  cabin_noise?: number;
}): Promise<CabinTelemetry> {
  const res = await fetch(`${API_BASE}/api/clinical/environment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(env),
  });
  return res.json();
}

export async function fetchCo2HazardModel(co2_mmhg = 3.0): Promise<Law2014Hazard> {
  const res = await fetch(`${API_BASE}/api/clinical/environment/hazard-model?co2_mmhg=${co2_mmhg}`);
  return res.json();
}

// ── Curated Medical Reference Library ────────────────────────────────────────

export async function fetchMedicalReferences(query?: string): Promise<{ references: MedicalArticle[]; total: number }> {
  const url = query
    ? `${API_BASE}/api/clinical/references?query=${encodeURIComponent(query)}`
    : `${API_BASE}/api/clinical/references`;
  const res = await fetch(url);
  return res.json();
}

export async function fetchMedicalReferenceById(ref_id: string): Promise<MedicalArticle> {
  const res = await fetch(`${API_BASE}/api/clinical/references/${encodeURIComponent(ref_id)}`);
  return res.json();
}

// ── Emergency Checklists ──────────────────────────────────────────────────────

export async function fetchEmergencyChecklists(): Promise<{ checklists: EmergencyChecklist[] }> {
  const res = await fetch(`${API_BASE}/api/clinical/checklists`);
  return res.json();
}

export async function fetchEmergencyChecklistById(checklist_id: string): Promise<EmergencyChecklist> {
  const res = await fetch(`${API_BASE}/api/clinical/checklists/${encodeURIComponent(checklist_id)}`);
  return res.json();
}

// ── Built-In Self-Test (BIST) ─────────────────────────────────────────────────

export async function runBistDiagnostic(): Promise<BistReport> {
  const res = await fetch(`${API_BASE}/api/clinical/bist/run`, { method: "POST" });
  return res.json();
}

export async function fetchBistStatus(): Promise<BistReport> {
  const res = await fetch(`${API_BASE}/api/clinical/bist/status`);
  return res.json();
}
