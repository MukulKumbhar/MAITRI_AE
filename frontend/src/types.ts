export type TabId =
  | "overview"
  | "cardio"
  | "neuro"
  | "cabin"
  | "medical"
  | "logs"
  | "live"
  | "mission"
  | "support";

export type StressLevel = "NOMINAL" | "MILD" | "ELEVATED" | "CRITICAL";

export interface EmotionProbs {
  angry: number;
  disgust: number;
  fear: number;
  happy: number;
  neutral: number;
  sad: number;
  surprise: number;
}

export interface FaceTelemetry {
  emotion: string;
  confidence: number;
  quality: number;
  is_blurry: boolean;
  blur_score: number;
  probs?: EmotionProbs;
}

export interface EyeTelemetry {
  ear: number;
  blink_rate: number;
  fatigue_label: string;
  fatigue_strain: number;
  frame_count?: number;
  eye_available?: boolean;
}

export interface VoiceTelemetry {
  emotion: string;
  confidence: number;
  is_speaking: boolean;
  rms: number;
  db: number;
  probs: EmotionProbs;
}

export interface VitalsTelemetry {
  heart_rate: number;
  temperature: number;
  spo2: number;
  hr_strain: number;
  temp_strain: number;
  spo2_strain: number;
  composite_strain: number;
  status: string;
  respiratory_rate?: number;
  rmssd?: number;
  sdnn?: number;
  baevsky_index?: number;
  hrv_strain?: number;
}

export interface ExplainableWeights {
  face: number;
  voice: number;
  vitals: number;
  eye: number;
}

export interface ExplainableBreakdown {
  face_strain?: number;
  vitals_strain?: number;
  fatigue_strain?: number;
  voice_strain?: number;
  dominant_contributor?: string;
  baseline_z_score?: number;
  cusum_drift_detected?: boolean;
  rationale?: string;
  [key: string]: any;
}

export interface FusionTelemetry {
  stress_pct: number;
  stress_level: StressLevel;
  dominant_emotion: string;
  weights: ExplainableWeights;
  fused_probs: EmotionProbs;
  is_speaking?: boolean;
  manual_override?: boolean;
  manual_face_ratio?: number;
  explainable_breakdown?: ExplainableBreakdown;
}

export interface AlertTelemetry {
  level: StressLevel;
  icon: string;
  color: string;
  header: string;
  body: string;
  technique: string | null;
}

export interface WatchdogTelemetry {
  state: "NORMAL" | "CHECK_IN" | "INCAPACITATED";
  countdown: number;
  message: string;
}

// ── IEC 60601-1-8 Alarms ───────────────────────────────────────────────────────
export interface AlarmRecord {
  alarm_id: string;
  code: string;
  priority: "HIGH" | "MEDIUM" | "LOW" | "INFO";
  message: string;
  source: string;
  created_at: string;
  acknowledged: boolean;
  ack_by?: string;
  escalated: boolean;
  occurrence_count: number;
}

export interface AlarmSummary {
  total_active: number;
  unacknowledged_count: number;
  audio_paused: boolean;
  audio_pause_remaining_sec: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  active_alarms: AlarmRecord[];
}

// ── Cabin Environmental Atmosphere & Law 2014 Hazard ──────────────────────────
export interface Law2014Hazard {
  co2_mmhg: number;
  odds_ratio: number;
  headache_probability_pct: number;
  risk_category: "NOMINAL" | "MILD_ELEVATION" | "HIGH_RISK" | "CRITICAL_HAZARD";
  reference: string;
  recommendation: string;
}

export interface CabinTelemetry {
  co2_mmhg: number;
  o2_percent: number;
  pressure_kpa: number;
  ambient_temp_c: number;
  noise_dba: number;
  co2_headache_hazard?: Law2014Hazard;
}

// ── Sensor Adapter Controls ───────────────────────────────────────────────────
export interface SensorAdapterStatus {
  mode: "live" | "manual" | "replay";
  scenario?: string;
  replay_speed?: number;
  channels?: Record<string, any>;
  active_scenario?: {
    name: string;
    duration_sec: number;
    events: any[];
  };
}

// ── Personal Baseline & CUSUM ─────────────────────────────────────────────────
export interface BaselineStatus {
  crew_id: string;
  is_calibrated: boolean;
  sample_count: number;
  calibration_target: number;
  means: {
    negative_affect: number;
    vitals_strain: number;
    ear: number;
    face_strain: number;
  };
  sigmas: {
    negative_affect: number;
    vitals_strain: number;
    ear: number;
    face_strain: number;
  };
  cusum_drift: Record<string, number>;
  cusum_sh: Record<string, number>;
}

// ── PVT-B Reaction Self-Test ──────────────────────────────────────────────────
export interface PVTTrial {
  trial_index: number;
  isi_delay_s: number;
  stimulus_time: number;
  response_time?: number;
  rt_ms: number;
  is_false_start: boolean;
  is_lapse: boolean;
  is_timeout: boolean;
}

export interface PVTMetrics {
  total_stimuli: number;
  valid_hits: number;
  lapses: number;
  false_starts: number;
  mean_rt_ms: number;
  median_rt_ms: number;
  fastest_10pct_rt_ms: number;
  slowest_10pct_rt_ms: number;
  mean_speed: number;
  fatigue_risk_score: number;
  performance_category: string;
}

export interface PVTSessionStatus {
  session_id: string;
  crew_member: string;
  status: "IDLE" | "AWAITING_STIMULUS" | "STIMULUS_ACTIVE" | "COMPLETED" | "ABORTED";
  elapsed_s: number;
  duration_s: number;
  remaining_s: number;
  active_stimulus_start: number;
  responses_count: number;
  metrics: PVTMetrics;
  current_trial?: PVTTrial;
}

export interface PVTHistoryRecord {
  id: number;
  timestamp: string;
  session_id: string;
  crew_member: string;
  duration_s: number;
  total_stimuli: number;
  valid_hits: number;
  lapses: number;
  false_starts: number;
  mean_rt_ms: number;
  median_rt_ms: number;
  fatigue_risk_score: number;
  performance_category: string;
  raw_rts?: number[];
  record_hash: string;
  prev_hash: string;
}

// ── Sleep & Circadian Dynamics ────────────────────────────────────────────────
export interface SleepDebtInfo {
  actual_sleep_hours: number;
  target_sleep_hours: number;
  daily_delta_hours: number;
  cumulative_debt_hours: number;
  chronic_fatigue_risk_index: number;
  clinical_status: string;
  recommendation: string;
}

export interface CircadianPhaseInfo {
  current_hour: number;
  phase_angle_deg: number;
  phase_label: string;
  core_temp_nadir_offset_hours: number;
}

export interface MelatoninInfo {
  light_lux: number;
  melatonin_suppression_pct: number;
  risk_level: string;
  recommendation: string;
}

export interface OrbitalCycleInfo {
  orbital_period_min: number;
  current_phase: "DAYLIGHT" | "NIGHT_ECLIPSE";
  cycle_elapsed_min: number;
  cycle_remaining_min: number;
  sunlight_intensity_lux: number;
  recommendation: string;
}

export interface SleepStatus {
  sleep_debt: SleepDebtInfo;
  circadian_phase: CircadianPhaseInfo;
  melatonin_suppression: MelatoninInfo;
  orbital_cycle: OrbitalCycleInfo;
  decision_support_notice: string;
}

export interface SleepHistoryRecord {
  id: number;
  timestamp: string;
  sleep_date: string;
  crew_member: string;
  sleep_duration_hours: number;
  target_sleep_hours: number;
  sleep_debt_hours: number;
  cumulative_debt_hours: number;
  chronic_fatigue_risk: number;
  melatonin_suppression_pct: number;
  light_exposure_lux: number;
  clinical_status: string;
  notes?: string;
  record_hash: string;
  prev_hash: string;
}

// ── Clinical Screeners & Third-Quarter Effect ────────────────────────────────
export type ScreenerType = "PHQ-9" | "GAD-7" | "PSS-4";

export interface ScreenerResult {
  screener_type: ScreenerType;
  total_score: number;
  max_possible_score: number;
  severity: string;
  clinical_interpretation: string;
  item_responses: number[];
  safety_alert: boolean;
  safety_message?: string;
  action_recommendation: string;
  timestamp?: string;
}

export interface ThirdQuarterAnalysis {
  mission_elapsed_days: number;
  mission_total_days: number;
  mission_fraction: number;
  is_third_quarter_window: boolean;
  vulnerability_index: number;
  vulnerability_tier: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  alert_message: string;
  clinical_recommendation: string;
}

export interface ScreenerHistoryRecord {
  id: number;
  timestamp: string;
  crew_member: string;
  screener_type: string;
  total_score: number;
  max_possible_score: number;
  severity: string;
  item_responses: string | number[];
  safety_alert: number | boolean;
  safety_message?: string;
  third_quarter_risk_index: number;
  clinical_interpretation: string;
  action_recommendation: string;
  record_hash: string;
  prev_hash: string;
}

// ── Medical Knowledge Base & Emergency Checklists ─────────────────────────────
export interface MedicalArticle {
  id: string;
  title: string;
  category: string;
  keywords: string[];
  citations: string[];
  summary: string;
  clinical_management: string;
}

export interface ChecklistStep {
  step_number: number;
  action: string;
  instruction: string;
  critical: boolean;
}

export interface EmergencyChecklist {
  id: string;
  title: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  source: string;
  steps: ChecklistStep[];
}

// ── Built-In Self-Test (BIST) ─────────────────────────────────────────────────
export interface BistSubsystemResult {
  status: "PASSED" | "DEGRADED" | "FAILED";
  details: string;
  [key: string]: any;
}

export interface BistReport {
  timestamp_iso: string;
  overall_status: "PASSED" | "DEGRADED" | "FAILED";
  duration_ms: number;
  subsystems: {
    camera: BistSubsystemResult;
    microphone: BistSubsystemResult;
    models_on_disk: BistSubsystemResult;
    memory_ram: BistSubsystemResult;
    database_cryptography: BistSubsystemResult;
  };
}

// ── Telemetry Payload ─────────────────────────────────────────────────────────
export interface TelemetryPayload {
  type: string;
  timestamp: number;
  face: FaceTelemetry;
  eye: EyeTelemetry;
  voice: VoiceTelemetry;
  vitals: VitalsTelemetry;
  fusion: FusionTelemetry;
  alert: AlertTelemetry;
  watchdog: WatchdogTelemetry;
  cabin?: CabinTelemetry;
  alarms?: AlarmSummary;
  sensor_adapter?: SensorAdapterStatus;
  security?: {
    audit_hash: string;
    entry_count: number;
  };
  settings?: {
    mic_gain: number;
    silence_threshold: number;
  };
}

export interface LogRecord {
  id?: number;
  timestamp: string;
  face_emotion: string;
  fused_emotion: string;
  voice_state: string;
  heart_rate: number;
  temperature: number;
  spo2: number;
  blink_rate: number;
  fatigue_label: string;
  stress_score: number;
  stress_level: string;
  alert_triggered: string;
  response_msg: string;
  prob_angry?: number;
  prob_disgust?: number;
  prob_fear?: number;
  prob_happy?: number;
  prob_neutral?: number;
  prob_sad?: number;
  prob_surprise?: number;
  emotion_probs?: EmotionProbs;
  respiratory_rate?: number;
  rmssd?: number;
  sdnn?: number;
  baevsky_index?: number;
  co2_mmhg?: number;
}

export interface PsychLogRecord {
  id?: number;
  timestamp: string;
  crew_member: string;
  mission_phase: string;
  input_channel: string;
  astronaut_query: string;
  detected_emotion: string;
  stress_pct: number;
  ai_response: string;
  has_audio: number;
}

export interface DTNPacket {
  packet_id: string;
  created_at: number;
  priority: string;
  status: string;
  summary: string;
}

export interface MissionStatus {
  mission: string;
  crew: string;
  mission_catalog: Record<string, number>;
  crew_list: string[];
  dtn: {
    latency_sec: number;
    latency_formatted: string;
    queued_packets: number;
    packets: DTNPacket[];
  };
  dossier_compiled: boolean;
}

export interface VoiceDebugInfo {
  rms: number;
  db: number;
  is_speaking: boolean;
  vosk_ready: boolean;
  gain: number;
  threshold: number;
  last_transcript: string;
  last_interim: string;
  last_intent: string | null;
  last_confidence: number;
  last_latency_ms: number;
  safety_awaiting: boolean;
  last_status: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: string;
  audioBase64?: string;
  citations?: string[];
  refusal?: boolean;
}
