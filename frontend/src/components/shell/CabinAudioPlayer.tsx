import React, { useEffect, useState, useRef } from "react";
import { Volume2, Play, RotateCcw, X, Radio } from "lucide-react";
import { audioService } from "../../services/audioSocket";

interface TalkbackMessage {
  text: string;
  audioBase64: string;
  timestamp: string;
}

export const CabinAudioPlayer: React.FC = () => {
  const [currentMessage, setCurrentMessage] = useState<TalkbackMessage | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [autoplayBlocked, setAutoplayBlocked] = useState<boolean>(false);
  const audioInstanceRef = useRef<HTMLAudioElement | null>(null);
  const timeoutRef = useRef<any>(null);

  const playAudio = (base64Audio: string) => {
    try {
      if (audioInstanceRef.current) {
        audioInstanceRef.current.pause();
        audioInstanceRef.current = null;
      }

      const snd = new Audio(`data:audio/wav;base64,${base64Audio}`);
      audioInstanceRef.current = snd;

      snd.onplay = () => {
        setIsPlaying(true);
        setAutoplayBlocked(false);
      };

      snd.onended = () => {
        setIsPlaying(false);
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => {
          setCurrentMessage(null);
        }, 8000);
      };

      snd.onerror = () => {
        setIsPlaying(false);
      };

      snd.play().catch((err) => {
        console.warn("Audio autoplay blocked by browser policy:", err);
        setAutoplayBlocked(true);
        setIsPlaying(false);
      });
    } catch (e) {
      console.error("Audio playback error:", e);
      setIsPlaying(false);
    }
  };

  useEffect(() => {
    const unsub = audioService.addEventListener((event) => {
      if (event.type === "tts_audio_response" && event.audio_base64) {
        const msg: TalkbackMessage = {
          text: event.text || "Spoken response",
          audioBase64: event.audio_base64,
          timestamp: new Date().toLocaleTimeString(),
        };
        setCurrentMessage(msg);
        playAudio(event.audio_base64);
      }
    });

    return () => {
      unsub();
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (audioInstanceRef.current) audioInstanceRef.current.pause();
    };
  }, []);

  if (!currentMessage) return null;

  return (
    <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 max-w-xl w-full px-4 animate-in fade-in slide-in-from-top-4 duration-300">
      <div className="bg-space-900/95 border border-cyan-500/50 rounded-xl p-3 shadow-2xl backdrop-blur-md flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-500/40 flex items-center justify-center shrink-0">
            <Volume2 className={`w-4 h-4 text-cyan-400 ${isPlaying ? "animate-pulse" : ""}`} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] tracking-wider uppercase text-cyan-400 font-bold flex items-center gap-1">
                <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
                AI Talkback
              </span>
              <span className="text-space-400 text-[10px] font-mono">{currentMessage.timestamp}</span>
              {isPlaying && (
                <div className="flex items-center gap-0.5 h-3">
                  <span className="w-1 bg-cyan-400 rounded-full animate-bounce h-2" style={{ animationDelay: "0ms" }} />
                  <span className="w-1 bg-cyan-400 rounded-full animate-bounce h-3" style={{ animationDelay: "150ms" }} />
                  <span className="w-1 bg-cyan-400 rounded-full animate-bounce h-1.5" style={{ animationDelay: "300ms" }} />
                </div>
              )}
            </div>
            <p className="text-space-100 font-mono text-xs truncate mt-0.5">
              "{currentMessage.text}"
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {autoplayBlocked ? (
            <button
              onClick={() => playAudio(currentMessage.audioBase64)}
              className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 font-mono text-[11px] flex items-center gap-1 transition-colors"
            >
              <Play className="w-3 h-3 fill-amber-300" /> Click to Hear
            </button>
          ) : (
            <button
              onClick={() => playAudio(currentMessage.audioBase64)}
              title="Replay Talkback"
              className="p-1.5 rounded hover:bg-space-800 text-space-400 hover:text-cyan-300 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            onClick={() => setCurrentMessage(null)}
            title="Dismiss"
            className="p-1.5 rounded hover:bg-space-800 text-space-400 hover:text-rose-400 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
