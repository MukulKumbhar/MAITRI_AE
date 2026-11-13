import { LogRecord, MissionStatus, PsychLogRecord } from "../types";

const API_BASE = "";

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
