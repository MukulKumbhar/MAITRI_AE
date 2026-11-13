import React from "react";
import { X, Mic, Zap, Monitor, Eye, Footprints } from "lucide-react";

interface HandsFreeStudyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HandsFreeStudyModal: React.FC<HandsFreeStudyModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-space-900 border border-space-700 rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-space-700 bg-space-850">
          <div className="flex items-center gap-2">
            <span className="text-xl">🛰️</span>
            <h3 className="font-bold text-space-100 text-sm uppercase tracking-wider">
              Astronaut Hands-Free Navigation: Solutions Study & Voice Director
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-space-400 hover:text-space-100 hover:bg-space-800 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs text-space-200 leading-relaxed font-sans">
          <div className="p-3.5 rounded bg-space-850 border border-space-700 text-space-300">
            <h4 className="font-semibold text-cyan-400 mb-1 uppercase tracking-wide">
              👨‍🚀 Spaceflight Hands-Free Ergonomic Analysis
            </h4>
            In microgravity operations, astronauts' hands are frequently engaged (gripping handrails during high-g thrust, handling fragile payload experiments, operating physical manual levers, or wearing bulky pressurized EVA gloves). Traditional GUI cursor manipulation causes severe motor and cognitive distraction. MAITRI 2.0 implements five defense-in-depth ergonomic solutions:
          </div>

          <div className="space-y-3">
            <div className="p-3.5 rounded bg-space-850/60 border border-space-800 hover:border-space-700 transition-all flex gap-3">
              <Mic className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <h5 className="font-bold text-space-100">1. Primary: Autonomous Voice Navigation ("Voice Cockpit Director")</h5>
                <p className="mt-1 text-space-400">
                  Sub-50ms offline Vosk Kaldi STT continuously parses incoming speech for navigation triggers. Phrases like <code className="text-cyan-300">"switch to logs"</code>, <code className="text-cyan-300">"open live feed"</code>, or <code className="text-cyan-300">"tab 1..4"</code> transition views immediately with zero physical contact.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded bg-space-850/60 border border-space-800 hover:border-space-700 transition-all flex gap-3">
              <Zap className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h5 className="font-bold text-space-100">2. Secondary: Autonomous Telemetry-Driven View Focusing (Priority Override)</h5>
                <p className="mt-1 text-space-400">
                  When acute distress is detected (Stress Index &gt; 65% or persistent panic state), MAITRI automatically focuses the AI Psychological Support console and initializes guided 4-7-8 breathing countermeasures without waiting for astronaut manual input.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded bg-space-850/60 border border-space-800 hover:border-space-700 transition-all flex gap-3">
              <Monitor className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <h5 className="font-bold text-space-100">3. Tertiary: Single-Pane "Heads-Up Cockpit" Mode</h5>
                <p className="mt-1 text-space-400">
                  Consolidates live webcam FER, eye-tracking PERCLOS, instant acoustic telemetry, and mission vitals into a single high-density cockpit layout to eliminate the cognitive overhead of paginated navigation during emergency tasks.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded bg-space-850/60 border border-space-800 hover:border-space-700 transition-all flex gap-3">
              <Eye className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
              <div>
                <h5 className="font-bold text-space-100">4. Quaternary: Ocular Gaze-Dwell & Intentional Blink Tracking</h5>
                <p className="mt-1 text-space-400">
                  Leverages MediaPipe iris mesh geometry. Detects rising-edge blink hysteresis over rolling 60s windows for silent operational telemetry during acoustic communication blackouts.
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded bg-space-850/60 border border-space-800 hover:border-space-700 transition-all flex gap-3">
              <Footprints className="w-5 h-5 text-orange-400 shrink-0 mt-0.5" />
              <div>
                <h5 className="font-bold text-space-100">5. Quinary: Foot-Pedal & 1-Key Tactile Hotkeys</h5>
                <p className="mt-1 text-space-400">
                  Instantaneous single-touch tactile bindings mapped to physical keys <code className="text-cyan-300">1</code>, <code className="text-cyan-300">2</code>, <code className="text-cyan-300">3</code>, and <code className="text-cyan-300">4</code> via direct DOM keyboard event listeners. Compatible with spacecraft foot-pedal switches or gloved tactile input.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-space-700 bg-space-850 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-space-800 hover:bg-space-700 text-space-100 text-xs font-medium border border-space-700"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
