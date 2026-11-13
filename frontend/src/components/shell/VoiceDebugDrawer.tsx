import React, { useState } from "react";
import { VoiceDebugInfo } from "../../types";
import { X, Mic, Volume2, Shield, Sliders, Check, AlertCircle } from "lucide-react";
import { audioService } from "../../services/audioSocket";

interface VoiceDebugDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  debugState: VoiceDebugInfo;
  isCapturing: boolean;
  onToggleMic: () => void;
}

export const VoiceDebugDrawer: React.FC<VoiceDebugDrawerProps> = ({
  isOpen,
  onClose,
  debugState,
  isCapturing,
  onToggleMic,
}) => {
  if (!isOpen) return null;

  const [gain, setGain] = useState<number>(debugState.gain || 1.0);
  const [threshold, setThreshold] = useState<number>(debugState.threshold || 0.03);

  const handleGainChange = (newGain: number) => {
    setGain(newGain);
    audioService.sendControl({ type: "set_gain", gain: newGain });
  };

  const handleThresholdChange = (newThresh: number) => {
    setThreshold(newThresh);
    audioService.sendControl({ type: "set_threshold", threshold: newThresh });
  };

  // VU meter percentage from dB (-60 dB to 0 dB)
  const clampedDb = Math.max(-60, Math.min(0, debugState.db));
  const vuPct = Math.round(((clampedDb + 60) / 60) * 100);

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-space-900 border-l border-space-700 shadow-2xl flex flex-col font-sans">
      {/* Header */}
      <div className="p-4 border-b border-space-700 bg-space-850 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mic className={`w-5 h-5 ${debugState.is_speaking ? "text-emerald-400 animate-pulse" : "text-space-400"}`} />
          <h3 className="font-bold text-xs uppercase tracking-wider text-space-100">
            Acoustic & Voice Control HUD
          </h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-space-400 hover:text-space-100 hover:bg-space-800 rounded transition-all"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body */}
      <div className="p-4 flex-1 overflow-y-auto space-y-4 text-xs">
        {/* Hardware Status Strip */}
        <div className="p-3 rounded bg-space-850 border border-space-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-space-400">Microphone Stream</span>
            <button
              onClick={onToggleMic}
              className={`px-2.5 py-1 rounded text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all ${
                isCapturing
                  ? "bg-emerald-600 text-white shadow-glow-nominal"
                  : "bg-space-800 text-space-300 hover:bg-space-700"
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              {isCapturing ? "Capturing (16kHz)" : "Start Mic"}
            </button>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-space-400">Offline Vosk Model</span>
            <span
              className={`font-mono px-2 py-0.5 rounded text-[10px] ${
                debugState.vosk_ready
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
              }`}
            >
              {debugState.vosk_ready ? "KALDI 40MB LOADED" : "OFFLINE / READY"}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-space-400">VAD State</span>
            <span
              className={`font-mono px-2 py-0.5 rounded text-[10px] ${
                debugState.is_speaking
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  : "bg-space-800 text-space-400"
              }`}
            >
              {debugState.is_speaking ? "🔊 SPEECH ACTIVE" : "🔇 SILENT / STANDBY"}
            </span>
          </div>
        </div>

        {/* Hardware Ballistic VU Meter */}
        <div className="p-3 rounded bg-space-850 border border-space-800 space-y-1.5">
          <div className="flex justify-between items-center text-space-400 font-mono text-[11px]">
            <span className="flex items-center gap-1">
              <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
              Ballistic VU Meter
            </span>
            <span className="text-cyan-300">
              {debugState.db.toFixed(1)} dB ({vuPct}%)
            </span>
          </div>
          <div className="h-2.5 bg-space-950 rounded-full overflow-hidden border border-space-700 p-0.5">
            <div
              className={`h-full rounded-full transition-all duration-75 ${
                vuPct > 80
                  ? "bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500"
                  : vuPct > 50
                  ? "bg-gradient-to-r from-emerald-500 to-amber-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${vuPct}%` }}
            />
          </div>
          <div className="flex justify-between font-mono text-[9px] text-space-400">
            <span>-60 dB</span>
            <span>-30 dB</span>
            <span>0 dB</span>
          </div>
        </div>

        {/* Real-Time ASR Transcript & Hypothesis */}
        <div className="p-3 rounded bg-space-850 border border-space-800 space-y-2">
          <span className="font-semibold text-space-300 text-[11px] uppercase tracking-wide block">
            Speech Recognition Stream
          </span>

          <div className="p-2 rounded bg-space-950 border border-space-700 font-mono text-xs min-h-[48px] space-y-1">
            {debugState.last_interim && (
              <p className="text-cyan-400/80 italic">
                &gt; {debugState.last_interim} <span className="animate-pulse">...</span>
              </p>
            )}
            {debugState.last_transcript ? (
              <p className="text-emerald-300 font-bold">
                &gt; "{debugState.last_transcript}"
              </p>
            ) : !debugState.last_interim ? (
              <p className="text-space-400 italic">Awaiting speech utterance...</p>
            ) : null}
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-space-400">
            <span>ASR Latency:</span>
            <span className="text-cyan-400">{debugState.last_latency_ms.toFixed(1)} ms</span>
          </div>
        </div>

        {/* Intent & Entity Matching */}
        <div className="p-3 rounded bg-space-850 border border-space-800 space-y-2">
          <span className="font-semibold text-space-300 text-[11px] uppercase tracking-wide block">
            Fuzzy Intent & Safety Classifier
          </span>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div className="p-2 rounded bg-space-950 border border-space-700">
              <span className="text-space-400 block text-[10px]">INTENT ID</span>
              <span className="text-cyan-300 font-bold">
                {debugState.last_intent || "NONE"}
              </span>
            </div>
            <div className="p-2 rounded bg-space-950 border border-space-700">
              <span className="text-space-400 block text-[10px]">CONFIDENCE</span>
              <span className="text-emerald-400 font-bold">
                {Math.round(debugState.last_confidence * 100)}%
              </span>
            </div>
          </div>

          {/* Safety Confirmation Gate Alert if active */}
          {debugState.safety_awaiting && (
            <div className="p-2.5 rounded bg-amber-950/80 border border-amber-500 text-amber-200 text-xs space-y-1 animate-pulse">
              <div className="flex items-center gap-1.5 font-bold">
                <Shield className="w-4 h-4 text-amber-400" />
                SAFETY GATE CHALLENGE ACTIVE
              </div>
              <p className="text-[11px]">
                Say <code className="text-amber-100 font-bold">"Confirm override"</code> to commit emergency reset.
              </p>
            </div>
          )}
        </div>

        {/* Calibration & Sensitivity Sliders */}
        <div className="p-3 rounded bg-space-850 border border-space-800 space-y-3">
          <div className="flex items-center gap-1.5 font-semibold text-space-300 text-[11px] uppercase tracking-wide">
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            Acoustic Calibration
          </div>

          <div className="space-y-1">
            <div className="flex justify-between font-mono text-[11px]">
              <span className="text-space-400">Digital Pre-Gain</span>
              <span className="text-cyan-300">{gain.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={gain}
              onChange={(e) => handleGainChange(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-space-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
          </div>

          <div className="space-y-1">
            <div className="flex justify-between font-mono text-[11px]">
              <span className="text-space-400">Silence Gate Cutoff</span>
              <span className="text-cyan-300">{threshold.toFixed(3)} RMS</span>
            </div>
            <input
              type="range"
              min="0.005"
              max="0.080"
              step="0.005"
              value={threshold}
              onChange={(e) => handleThresholdChange(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-space-950 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
