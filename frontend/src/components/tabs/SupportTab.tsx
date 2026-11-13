import React, { useEffect, useState, useRef } from "react";
import { TelemetryPayload, ChatMessage } from "../../types";
import {
  postPsychInit,
  fetchPsychStatus,
  postPsychChat,
  postPsychGrounding,
  fetchPsychPresets,
} from "../../services/api";
import { audioService } from "../../services/audioSocket";
import {
  Brain,
  Zap,
  Mic,
  Send,
  Trash2,
  Volume2,
  AlertTriangle,
  Play,
  RotateCcw,
  Sparkles,
  Bot,
  User,
  CheckCircle,
} from "lucide-react";

interface SupportTabProps {
  telemetry: TelemetryPayload | null;
}

export const SupportTab: React.FC<SupportTabProps> = ({ telemetry }) => {
  const [isEngineLoaded, setIsEngineLoaded] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState<boolean>(false);
  const [initMessage, setInitMessage] = useState<string>("");

  // Chat conversation
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial",
      role: "assistant",
      text: "Namaste Commander Sharma. I am MAITRI, your autonomous mission well-being companion. All telemetry streams are nominal. How are you feeling today?",
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [inputText, setInputText] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Dynamic presets
  const [presets, setPresets] = useState<[string, string][]>([
    ["🧘 4-7-8 Grounding", "Please guide me through the 4-7-8 acute breathing grounding sequence."],
    ["📊 Full Telemetry Check", "What is my current multimodal physiological stress status?"],
    ["🫁 Box Breathing", "Guide me through a four-stage box breathing routine."],
    ["🛰️ Docking Anxiety", "I am feeling pressure during the upcoming orbital rendezvous maneuver."],
    ["💤 Sleep Reset", "I am struggling with circadian sleep onset in the zero-g sleep pod."],
    ["⚓ Cold Anchor", "Provide a cognitive grounding exercise to restore spatial focus."],
  ]);

  // Voice stream tap state (S-12, S-13, S-14)
  const [continuousTap, setContinuousTap] = useState<boolean>(false);
  const [queuedBufferSec, setQueuedBufferSec] = useState<number>(0.0);
  const [latestVoiceToast, setLatestVoiceToast] = useState<string>("");

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // Scroll to bottom on new message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load status and presets on mount
  useEffect(() => {
    fetchPsychStatus().then((res) => {
      setIsEngineLoaded(res.is_loaded);
    });

    fetchPsychPresets().then((res) => {
      if (res.presets && res.presets.length > 0) {
        const normalized: [string, string][] = (res.presets as any[]).map((item: any) => {
          if (Array.isArray(item)) return [item[0] || "", item[1] || ""];
          if (item && typeof item === "object") return [item.label || "", item.prompt || ""];
          return ["", ""];
        });
        setPresets(normalized);
      }
    });

    // Listen to voice events
    const unsub = audioService.addEventListener((event) => {
      if (event.type === "asr_final_transcript" && event.transcript) {
        setLatestVoiceToast(event.transcript);
        if (continuousTap) {
          handleSendMessage(event.transcript, "voice");
        }
      }
    });

    return () => unsub();
  }, [continuousTap]);

  // Initialize Support Engine (S-04)
  const handleInitEngine = async () => {
    setIsInitializing(true);
    setInitMessage("Initializing Whisper ASR, Phi-3-Mini 3.8B & Piper TTS...");
    try {
      const res = await postPsychInit();
      setIsEngineLoaded(res.is_loaded);
      setInitMessage(res.message);
    } catch (e: any) {
      setInitMessage(`Initialization error: ${e.message}`);
    } finally {
      setIsInitializing(false);
    }
  };

  // Submit chat query (S-15)
  const handleSendMessage = async (textToSend?: string, channel = "text") => {
    const q = textToSend || inputText;
    if (!q.trim() || isSubmitting) return;

    const userMsg: ChatMessage = {
      id: String(Date.now()),
      role: "user",
      text: q.trim(),
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputText("");
    setIsSubmitting(true);

    try {
      const res = await postPsychChat(q, channel);
      const assistantMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: "assistant",
        text: res.reply,
        timestamp: new Date().toLocaleTimeString(),
        audioBase64: res.audio_base64,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Broadcast speech to Cabin Audio Player & Autoplay (S-18)
      if (res.audio_base64) {
        audioService.broadcast({
          type: "tts_audio_response",
          text: res.reply,
          audio_base64: res.audio_base64,
        });
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: String(Date.now() + 1),
        role: "assistant",
        text: "I am currently running in offline contingency mode. Let's take a slow breath together.",
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Immediate 4-7-8 Guided Grounding Audio (S-07)
  const handleImmediateGrounding = async () => {
    setIsSubmitting(true);
    try {
      const res = await postPsychGrounding(
        "Cdr. A. Sharma",
        telemetry?.fusion?.stress_pct || 70.0
      );
      const assistantMsg: ChatMessage = {
        id: String(Date.now()),
        role: "assistant",
        text: res.script,
        timestamp: new Date().toLocaleTimeString(),
        audioBase64: res.audio_base64,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (res.audio_base64) {
        audioService.broadcast({
          type: "tts_audio_response",
          text: res.script,
          audio_base64: res.audio_base64,
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Clear dialogue history (S-16)
  const handleClearHistory = () => {
    setMessages([]);
  };

  const stressPct = telemetry?.fusion?.stress_pct ?? 22.4;
  const isHighDistress = stressPct >= 65.0 || telemetry?.fusion?.dominant_emotion === "fear";

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12 font-sans">
      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Engine Status & Header (S-01, S-02, S-03, S-04)                          */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-space-800 pb-4">
        <div>
          {/* S-01: Header */}
          <h2 className="text-base font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
            <Brain className="w-5 h-5 text-cyan-400" />
            🧠 Autonomous In-Flight Psychological Support
          </h2>
          {/* S-02: Model Specs Caption */}
          <p className="text-xs text-space-400 mt-0.5">
            Offline Multimodal Conversational Intervention: Phi-3-Mini (3.8B), Whisper ASR, Piper ONNX TTS.
          </p>
        </div>

        {/* S-03 & S-04: Engine Status Callout & Init Button */}
        <div className="flex items-center gap-3">
          <span
            className={`font-mono text-xs px-3 py-1 rounded-full font-bold flex items-center gap-1.5 ${
              isEngineLoaded
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                : "bg-space-850 text-space-400 border border-space-700"
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${isEngineLoaded ? "bg-emerald-400 animate-pulse" : "bg-space-400"}`} />
            {isEngineLoaded ? "🟢 Online" : "💤 Idle (conserving CPU/RAM)"}
          </span>

          {!isEngineLoaded && (
            <button
              onClick={handleInitEngine}
              disabled={isInitializing}
              className="px-4 py-1.5 rounded-lg bg-cyan-700 hover:bg-cyan-600 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 shadow-md transition-all"
            >
              <Zap className="w-3.5 h-3.5" />
              {isInitializing ? "Initializing..." : "⚡ Initialize Support Engine"}
            </button>
          )}
        </div>
      </div>

      {initMessage && (
        <div className="p-3 rounded-lg bg-space-850 border border-space-700 font-mono text-xs text-cyan-300">
          {initMessage}
        </div>
      )}

      {/* S-05: Affective Context Telemetry Pill */}
      <div className="p-3 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-space-400">
          <span className="text-cyan-400 font-bold uppercase">Clinical Injected Context:</span>
          <span>Affect: <strong className="text-amber-300 uppercase">{telemetry?.fusion?.dominant_emotion || "HAPPY"}</strong></span>
          <span>|</span>
          <span>Stress: <strong className="text-cyan-300">{(telemetry?.fusion?.stress_pct || 22.4).toFixed(1)}%</strong></span>
          <span>|</span>
          <span>Astronaut: <strong className="text-space-200">Cdr. A. Sharma (Pilot)</strong></span>
          <span>|</span>
          <span>Mission: <strong className="text-space-200">ISRO Gaganyaan (LEO)</strong></span>
        </div>

        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px]">
          REAL-TIME TELEMETRY STREAM ACTIVE
        </span>
      </div>

      {/* S-06: Elevated Stress Alert Banner (Conditional) */}
      {isHighDistress && (
        <div className="p-4 rounded-xl bg-amber-950/80 border border-amber-500 text-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-pulse shadow-glow-mild">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0" />
            <div>
              <h4 className="font-bold text-xs uppercase tracking-wider">
                ⚠️ Acute Psychological Distress Detected ({stressPct.toFixed(1)}%)
              </h4>
              <p className="text-xs text-amber-300/90 mt-0.5">
                Elevated cognitive strain index. Autonomous protocol recommends immediate grounded breathing pacing.
              </p>
            </div>
          </div>

          {/* S-07: Immediate Grounding Audio Button */}
          <button
            onClick={handleImmediateGrounding}
            className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-space-950 font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg transition-all shrink-0"
          >
            <Play className="w-4 h-4 fill-space-950" />
            🧘 Launch Immediate 4-7-8 Guided Grounding
          </button>
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Astronaut Voice Channel (Primary) (S-08 to S-14)                         */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-space-800 pb-3">
          {/* S-08: Voice Channel Header & Caption */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
              <Mic className="w-4 h-4 text-cyan-400" />
              🎙️ Astronaut Voice Channel (Primary)
            </h3>
            <p className="text-[11px] text-space-400 mt-0.5">
              Hands-free speech recognition continuously monitors ambient speech; auto-dispatches query upon silence.
            </p>
          </div>

          {/* S-10: Acoustic Sensitivity & VAD Telemetry Strip */}
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span className="px-2 py-0.5 rounded bg-space-850 border border-space-700 text-space-300">
              Sensitivity: HIGH
            </span>
            <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              VAD: ACTIVE
            </span>
          </div>
        </div>

        {/* S-09: Autonomous Live Voice Toast/Banner if voice captured */}
        {latestVoiceToast && (
          <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-600/60 text-emerald-200 text-xs flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <strong>🗣️ Autonomous Live Voice:</strong> "{latestVoiceToast}"
            </span>
            <span className="text-[10px] font-mono opacity-80">Captured Hands-Free</span>
          </div>
        )}

        {/* Audio Buffer & Controls (S-11, S-12, S-13, S-14) */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-4">
            {/* S-12: Continuous Stream Tap Checkbox */}
            <label className="flex items-center gap-2 cursor-pointer text-space-300">
              <input
                type="checkbox"
                checked={continuousTap}
                onChange={(e) => setContinuousTap(e.target.checked)}
                className="rounded bg-space-800 border-space-700 text-cyan-500 focus:ring-0 cursor-pointer"
              />
              <span>🎙️ Enable Continuous Stream Tap (Auto-routes Live Audio to Support)</span>
            </label>

            {/* S-13: Queued Buffer Status Readout */}
            <span className="font-mono text-space-400 text-[11px]">
              Queued Buffer: <strong className="text-cyan-300">{queuedBufferSec.toFixed(1)}s</strong>
            </span>
          </div>

          {/* S-14: Transcribe Buffer Manual Button */}
          <button
            onClick={() => handleSendMessage("Manual buffer dispatch", "voice")}
            className="px-3 py-1.5 rounded bg-space-850 hover:bg-space-800 text-space-200 border border-space-700 text-xs font-mono flex items-center gap-1.5"
          >
            <Mic className="w-3.5 h-3.5 text-cyan-400" />
            🗣️ Transcribe Live Mic Buffer (Manual Override)
          </button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Dynamic Clinical Guidance Presets (S-19)                                 */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-space-200 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          Dynamic Contextual Guidance Presets
        </h3>
        <p className="text-[11px] text-space-400">
          Clinical intervention chips dynamically evolve based on prevailing biometric strain and mission phase:
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
          {presets.map(([label, prompt], idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              className="p-3 rounded-lg bg-space-850 hover:bg-space-800 border border-space-700 hover:border-cyan-500/50 text-left transition-all group flex flex-col justify-between"
            >
              <span className="font-bold text-xs text-space-100 group-hover:text-cyan-300 transition-colors">
                {label}
              </span>
              <span className="text-[10px] text-space-400 line-clamp-2 mt-1 leading-snug">
                {prompt}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────────── */}
      {/* Clinical Dialogue Stream & Input (S-15, S-16, S-17, S-18)                */}
      {/* ──────────────────────────────────────────────────────────────────────── */}
      <div className="p-5 rounded-xl bg-space-900 border border-space-700 shadow-glass-panel space-y-4">
        {/* S-16: Header & Clear Button */}
        <div className="flex items-center justify-between border-b border-space-800 pb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-space-100 flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400" />
            In-Flight Dialogue Transcript
          </h3>

          <button
            onClick={handleClearHistory}
            className="px-2.5 py-1 rounded bg-space-850 hover:bg-space-800 text-space-400 hover:text-red-400 border border-space-700 text-xs font-mono flex items-center gap-1.5 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear History
          </button>
        </div>

        {/* S-17: Chat Message Stream */}
        <div className="space-y-3.5 max-h-96 overflow-y-auto p-2">
          {messages.map((m) => {
            const isUser = m.role === "user";
            return (
              <div
                key={m.id}
                className={`flex gap-3 text-xs leading-relaxed ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="w-7 h-7 rounded-lg bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`p-3.5 rounded-xl max-w-lg space-y-1.5 shadow-sm ${
                    isUser
                      ? "bg-cyan-900/40 border border-cyan-600/50 text-cyan-100 rounded-br-none"
                      : "bg-space-850 border border-space-700 text-space-200 rounded-bl-none"
                  }`}
                >
                  <div className="flex justify-between items-center gap-3 text-[10px] text-space-400 font-mono">
                    <span className="font-bold">{isUser ? "Astronaut" : "MAITRI Clinical AI"}</span>
                    <span>{m.timestamp}</span>
                  </div>

                  <p className="whitespace-pre-wrap">{m.text}</p>

                  {/* S-18: Attached Speech Audio Player */}
                  {m.audioBase64 && (
                    <div className="pt-2 border-t border-space-700 flex items-center gap-2">
                      <audio
                        controls
                        src={`data:audio/wav;base64,${m.audioBase64}`}
                        className="h-7 w-full max-w-xs"
                      />
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-7 h-7 rounded-lg bg-space-800 border border-space-700 flex items-center justify-center text-space-300 shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}
          <div ref={chatEndRef} />
        </div>

        {/* S-15: Text Chat Input Box */}
        <div className="pt-2 border-t border-space-800 flex items-center gap-2">
          <input
            type="text"
            placeholder="💬 Or type your message to MAITRI..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
            className="flex-1 p-3 rounded-lg bg-space-850 border border-space-700 text-xs text-space-100 placeholder-space-400 focus:outline-none focus:border-cyan-500 font-sans"
          />

          <button
            onClick={() => handleSendMessage()}
            disabled={isSubmitting || !inputText.trim()}
            className="px-5 py-3 rounded-lg bg-cyan-700 hover:bg-cyan-600 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg transition-all"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  );
};
