import React from "react";
import { TabId, AlarmSummary } from "../../types";
import {
  LayoutDashboard,
  HeartPulse,
  Brain,
  Gauge,
  Stethoscope,
  Terminal,
  ShieldAlert,
  Cpu,
  HelpCircle,
  Mic,
  VolumeX,
  Volume2,
  Lock,
  Moon,
  Sun,
  AlertTriangle,
  Radio,
} from "lucide-react";

interface HeaderProps {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  isCircadianNight: boolean;
  onToggleCircadianNight: () => void;
  onOpenBist: () => void;
  alarms?: AlarmSummary;
  onPauseAlarmAudio?: () => void;
  onOpenStudy: () => void;
  onOpenVoiceDebug: () => void;
  isVoiceSpeaking: boolean;
  isVoskReady: boolean;
  isMicCapturing?: boolean;
  onToggleMic?: () => void;
  auditHash?: string;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  isCircadianNight,
  onToggleCircadianNight,
  onOpenBist,
  alarms,
  onPauseAlarmAudio,
  onOpenStudy,
  onOpenVoiceDebug,
  isVoiceSpeaking,
  isVoskReady,
  isMicCapturing = false,
  onToggleMic,
  auditHash,
}) => {
  const highCount = alarms?.high_count ?? 0;
  const medCount = alarms?.medium_count ?? 0;
  const isAudioPaused = alarms?.audio_paused ?? false;
  const pauseRemaining = alarms?.audio_pause_remaining_sec ?? 0;

  return (
    <header className="border-b border-space-700 bg-space-900/90 backdrop-blur-md px-4 lg:px-6 py-3 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto flex flex-col xl:flex-row items-center justify-between gap-3">
        {/* Left: Mission Title & Status Badges */}
        <div className="flex items-center gap-3 w-full xl:w-auto justify-between xl:justify-start">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-xl shadow-glow-nominal">
              🛰️
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-wider text-space-100 uppercase">
                  Project MAITRI 2.0
                </h1>
                <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  OFFLINE AIR-GAPPED
                </span>
              </div>
              <p className="text-[11px] text-space-400 tracking-wide hidden sm:block">
                Multimodal Astronaut Health Cockpit & Decision Support
              </p>
            </div>
          </div>

          {/* Quick Actions (Mobile/Tablet view) */}
          <div className="flex xl:hidden items-center gap-1.5">
            <button
              onClick={onToggleCircadianNight}
              className={`p-1.5 rounded border text-xs font-mono transition-all ${
                isCircadianNight
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/50"
                  : "bg-space-850 text-space-300 border-space-700"
              }`}
              title="Circadian Night Shift Toggle"
            >
              {isCircadianNight ? <Moon className="w-4 h-4 text-amber-400" /> : <Sun className="w-4 h-4" />}
            </button>
            <button
              onClick={onOpenBist}
              className="p-1.5 rounded border border-space-700 bg-space-850 text-emerald-400 hover:border-space-600"
              title="BIST & Audit Ledger"
            >
              <Lock className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Center: 5-View Operational Cockpit Navigation (Hotkeys 1-5) */}
        <nav
          aria-label="Operational Cockpit Views"
          className="flex items-center flex-wrap justify-center gap-1 bg-space-950/80 p-1 rounded-lg border border-space-800"
        >
          {/* 1: Overview */}
          <button
            onClick={() => setActiveTab("overview")}
            aria-current={activeTab === "overview" ? "page" : undefined}
            className={`px-2.5 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "overview"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700 text-cyan-400">
              1
            </span>
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Overview</span>
          </button>

          {/* 2: Cardio */}
          <button
            onClick={() => setActiveTab("cardio")}
            aria-current={activeTab === "cardio" ? "page" : undefined}
            className={`px-2.5 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "cardio"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700 text-cyan-400">
              2
            </span>
            <HeartPulse className="w-3.5 h-3.5" />
            <span>Cardio</span>
          </button>

          {/* 3: Neuro */}
          <button
            onClick={() => setActiveTab("neuro")}
            aria-current={activeTab === "neuro" ? "page" : undefined}
            className={`px-2.5 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "neuro"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700 text-cyan-400">
              3
            </span>
            <Brain className="w-3.5 h-3.5" />
            <span>Neuro</span>
          </button>

          {/* 4: Cabin */}
          <button
            onClick={() => setActiveTab("cabin")}
            aria-current={activeTab === "cabin" ? "page" : undefined}
            className={`px-2.5 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "cabin"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700 text-cyan-400">
              4
            </span>
            <Gauge className="w-3.5 h-3.5" />
            <span>Cabin</span>
          </button>

          {/* 5: Medical */}
          <button
            onClick={() => setActiveTab("medical")}
            aria-current={activeTab === "medical" ? "page" : undefined}
            className={`px-2.5 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "medical"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700 text-cyan-400">
              5
            </span>
            <Stethoscope className="w-3.5 h-3.5" />
            <span>Medical</span>
          </button>

          <span className="w-px h-4 bg-space-800 mx-1 hidden md:block" />

          {/* Secondary Views: Logs, Mission, Support */}
          <button
            onClick={() => setActiveTab("logs")}
            className={`px-2 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeTab === "logs"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50"
                : "text-space-400 hover:text-space-200"
            }`}
            title="Mission Logs Ledger"
          >
            <Terminal className="w-3 h-3" />
            <span>Logs</span>
          </button>

          <button
            onClick={() => setActiveTab("mission")}
            className={`px-2 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeTab === "mission"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50"
                : "text-space-400 hover:text-space-200"
            }`}
            title="Mission Control & DTN Simulation"
          >
            <ShieldAlert className="w-3 h-3" />
            <span>DTN</span>
          </button>

          <button
            onClick={() => setActiveTab("support")}
            className={`px-2 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeTab === "support"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50"
                : "text-space-400 hover:text-space-200"
            }`}
            title="Psychological Support Agent"
          >
            <Cpu className="w-3 h-3" />
            <span>Psych</span>
          </button>

          <button
            onClick={() => setActiveTab("live")}
            className={`px-2 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeTab === "live"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50"
                : "text-space-400 hover:text-space-200"
            }`}
            title="Sensor Lab Video Telemetry HUD"
          >
            <Radio className="w-3 h-3" />
            <span>Sensors</span>
          </button>
        </nav>

        {/* Right: IEC Alarm status pill + 120s mute, Circadian Night toggle, BIST pill, Mic */}
        <div className="flex items-center flex-wrap gap-2 justify-end w-full xl:w-auto">
          {/* IEC 60601-1-8 Alarm Status Pill with 120s Audio Mute */}
          <div className="flex items-center bg-space-950/80 rounded-lg border border-space-800 p-0.5">
            <div
              className={`px-2 py-1 rounded text-[11px] font-mono flex items-center gap-1.5 transition-all ${
                highCount > 0
                  ? "bg-red-500/20 text-red-300 border border-red-500/50 animate-pulse"
                  : medCount > 0
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                  : "text-emerald-400"
              }`}
              title="IEC 60601-1-8 Tiered Alarm Status"
            >
              {highCount > 0 ? (
                <>
                  <AlertTriangle className="w-3 h-3 text-red-400" />
                  <span>{highCount} CRITICAL</span>
                </>
              ) : medCount > 0 ? (
                <>
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                  <span>{medCount} WARN</span>
                </>
              ) : (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[10px]">IEC OK</span>
                </>
              )}
            </div>

            {onPauseAlarmAudio && (
              <button
                onClick={onPauseAlarmAudio}
                className={`px-2 py-1 rounded text-[10px] font-mono flex items-center gap-1 transition-all ${
                  isAudioPaused
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold"
                    : "text-space-400 hover:text-space-200 hover:bg-space-850"
                }`}
                title="Pause Alarm Audio for 120s (IEC 60601-1-8 clause 6.8.4)"
              >
                {isAudioPaused ? (
                  <>
                    <VolumeX className="w-3 h-3 text-amber-400" />
                    <span>MUTED {pauseRemaining}s</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-3 h-3" />
                    <span>MUTE 120s</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Circadian Red / Night Shift Toggle */}
          <button
            onClick={onToggleCircadianNight}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-1.5 transition-all hidden xl:flex ${
              isCircadianNight
                ? "bg-amber-500/20 text-amber-300 border-amber-500/60 shadow-glow-mild"
                : "bg-space-850 text-space-300 border-space-700 hover:text-space-100 hover:border-space-600"
            }`}
            title="Toggle Circadian 620nm Low-Melatonin Suppression Night Mode"
          >
            {isCircadianNight ? (
              <>
                <Moon className="w-3.5 h-3.5 text-amber-400" />
                <span>🌙 NIGHT (620nm)</span>
              </>
            ) : (
              <>
                <Sun className="w-3.5 h-3.5 text-cyan-400" />
                <span>☀️ DAY (480nm)</span>
              </>
            )}
          </button>

          {/* BIST / Audit Ledger Pill */}
          <button
            onClick={onOpenBist}
            className="px-2.5 py-1.5 rounded-lg border border-space-700 bg-space-850 hover:bg-space-800 text-xs font-mono flex items-center gap-1.5 text-emerald-400 hover:border-emerald-500/50 transition-all hidden xl:flex"
            title="Inspect Built-In Self-Test (BIST) & Cryptographic SHA-256 Hash Chain"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>
              LEDGER:{" "}
              {auditHash ? `${auditHash.slice(0, 6)}…` : "SECURE"}
            </span>
          </button>

          {/* Mic Toggle */}
          {onToggleMic && (
            <button
              onClick={onToggleMic}
              className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-1.5 transition-all ${
                isMicCapturing
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500 shadow-glow-nominal animate-pulse"
                  : "bg-space-850 text-space-400 border-space-700 hover:text-space-200 hover:border-space-600"
              }`}
              title={
                isMicCapturing
                  ? "Mute Microphone Audio Stream"
                  : "Enable Acoustic Capture for Offline Voice Commands"
              }
            >
              <Mic
                className={`w-3.5 h-3.5 ${
                  isMicCapturing ? "text-emerald-400" : "text-space-400"
                }`}
              />
              <span className="hidden sm:inline">
                {isMicCapturing ? "MIC ON" : "MIC OFF"}
              </span>
            </button>
          )}

          {/* Voice HUD */}
          <button
            onClick={onOpenVoiceDebug}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono flex items-center gap-1.5 transition-all ${
              isVoiceSpeaking
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500 animate-pulse shadow-glow-nominal"
                : isVoskReady
                ? "bg-space-850 text-space-200 border-space-700 hover:border-space-600"
                : "bg-space-850 text-amber-400/80 border-space-700"
            }`}
            title="Open Offline Kaldi/Vosk Voice Diagnostics HUD"
          >
            <Radio className={`w-3.5 h-3.5 ${isVoiceSpeaking ? "text-emerald-400" : ""}`} />
            <span className="hidden sm:inline">VOICE</span>
          </button>

          {/* Spaceflight Ergonomics Study */}
          <button
            onClick={onOpenStudy}
            className="p-1.5 rounded-lg border border-space-700 bg-space-850 text-space-400 hover:text-space-200 hover:border-space-600 transition-all"
            title="Astronaut Hands-Free Navigation & Ergonomics Reference"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
