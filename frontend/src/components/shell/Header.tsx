import React from "react";
import { TabId } from "../../types";
import { Activity, Terminal, ShieldAlert, Cpu, HelpCircle, Mic } from "lucide-react";

interface HeaderProps {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  onOpenStudy: () => void;
  onOpenVoiceDebug: () => void;
  isVoiceSpeaking: boolean;
  isVoskReady: boolean;
  isMicCapturing?: boolean;
  onToggleMic?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onOpenStudy,
  onOpenVoiceDebug,
  isVoiceSpeaking,
  isVoskReady,
  isMicCapturing = false,
  onToggleMic,
}) => {
  return (
    <header className="border-b border-space-700 bg-space-900/90 backdrop-blur-md px-6 py-4 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Left: Mission Title & Subtitle (G-01, G-02) */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-xl shadow-glow-nominal">
            🛰️
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-wider text-space-100 uppercase">
                Project MAITRI 2.0
              </h1>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                OFFLINE AIR-GAPPED
              </span>
            </div>
            <p className="text-xs text-space-400 tracking-wide">
              Live Multimodal AI Astronaut Telemetry & Psychological Monitoring
            </p>
          </div>
        </div>

        {/* Center: Quick Navigation Bar with Hotkey Badges (G-10, G-09) */}
        <div className="flex items-center gap-1.5 bg-space-950/80 p-1.5 rounded-lg border border-space-800">
          <button
            onClick={() => setActiveTab("live")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "live"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700">1</span>
            <Activity className="w-3.5 h-3.5" />
            Live Cockpit
          </button>

          <button
            onClick={() => setActiveTab("logs")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "logs"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700">2</span>
            <Terminal className="w-3.5 h-3.5" />
            Mission Logs
          </button>

          <button
            onClick={() => setActiveTab("mission")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "mission"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700">3</span>
            <ShieldAlert className="w-3.5 h-3.5" />
            Mission Control
          </button>

          <button
            onClick={() => setActiveTab("support")}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "support"
                ? "bg-cyan-600/30 text-cyan-300 border border-cyan-500/50 shadow-sm"
                : "text-space-400 hover:text-space-200 hover:bg-space-850"
            }`}
          >
            <span className="font-mono text-[10px] bg-space-800 px-1 py-0.2 rounded border border-space-700">4</span>
            <Cpu className="w-3.5 h-3.5" />
            AI Support
          </button>
        </div>

        {/* Right: Global Mic Toggle, Voice HUD button & Ergonomics study (G-08) */}
        <div className="flex items-center gap-2">
          {onToggleMic && (
            <button
              onClick={onToggleMic}
              className={`px-2.5 py-1.5 rounded border text-xs font-mono flex items-center gap-1.5 transition-all ${
                isMicCapturing
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500 shadow-glow-nominal animate-pulse"
                  : "bg-space-850 text-space-400 border-space-700 hover:text-space-200 hover:border-space-600"
              }`}
              title={isMicCapturing ? "Mute Microphone Stream" : "Enable Microphone Stream for Voice Commands"}
            >
              <Mic className={`w-3.5 h-3.5 ${isMicCapturing ? "text-emerald-400" : "text-space-400"}`} />
              <span>{isMicCapturing ? "MIC ON" : "MIC OFF"}</span>
            </button>
          )}

          <button
            onClick={onOpenVoiceDebug}
            className={`px-2.5 py-1.5 rounded border text-xs font-mono flex items-center gap-1.5 transition-all ${
              isVoiceSpeaking
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500 animate-pulse shadow-glow-nominal"
                : isVoskReady
                ? "bg-space-850 text-space-200 border-space-700 hover:border-space-600"
                : "bg-space-850 text-amber-400/80 border-space-700"
            }`}
            title="Open Voice Diagnostics & HUD"
          >
            <Mic className={`w-3.5 h-3.5 ${isVoiceSpeaking ? "text-emerald-400" : ""}`} />
            <span>VOICE HUD</span>
          </button>

          <button
            onClick={onOpenStudy}
            className="p-1.5 rounded border border-space-700 bg-space-850 text-space-400 hover:text-space-200 hover:border-space-600 transition-all"
            title="Astronaut Hands-Free Navigation & Spaceflight Ergonomics"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
