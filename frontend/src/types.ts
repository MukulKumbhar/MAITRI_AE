export type TabId = "live" | "logs" | "mission" | "support";

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
}

export interface FusionTelemetry {
  stress_pct: number;
  stress_level: StressLevel;
  dominant_emotion: string;
  weights: {
    face: number;
    voice: number;
    vitals: number;
    eye: number;
  };
  fused_probs: EmotionProbs;
  is_speaking?: boolean;
  manual_override?: boolean;
  manual_face_ratio?: number;
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
}
