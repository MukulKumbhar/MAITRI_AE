import { VoiceDebugInfo } from "../types";

export type AudioEventHandler = (event: any) => void;

class AudioService {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private eventListeners: Set<AudioEventHandler> = new Set();
  private isCapturing: boolean = false;
  private isConnected: boolean = false;

  public debugState: VoiceDebugInfo = {
    rms: 0.0,
    db: -90.0,
    is_speaking: false,
    vosk_ready: false,
    gain: 1.0,
    threshold: 0.03,
    last_transcript: "",
    last_interim: "",
    last_intent: null,
    last_confidence: 0.0,
    last_latency_ms: 0.0,
    safety_awaiting: false,
    last_status: "IDLE",
  };

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/audio`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.binaryType = "arraybuffer";

      this.ws.onopen = () => {
        this.isConnected = true;
        console.log("🎙️ Audio WS connected");
      };

      this.ws.onmessage = (event) => {
        if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            this.handleServerEvent(data);
          } catch (e) {
            console.error("Audio WS message error", e);
          }
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        setTimeout(() => this.connect(), 3000);
      };

      this.ws.onerror = (err) => {
        console.error("Audio WS error", err);
      };
    } catch (e) {
      console.error("Audio WS connect failed", e);
    }
  }

  public addEventListener(listener: AudioEventHandler): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  private handleServerEvent(event: any): void {
    if (event.type === "audio_level") {
      this.debugState.rms = event.rms;
      this.debugState.db = event.db;
      this.debugState.is_speaking = event.is_speaking;
      if (event.debug) {
        this.debugState.gain = event.debug.gain ?? this.debugState.gain;
        this.debugState.threshold = event.debug.threshold ?? this.debugState.threshold;
        this.debugState.vosk_ready = event.debug.vosk_ready ?? this.debugState.vosk_ready;
        this.debugState.last_intent = event.debug.last_intent;
        this.debugState.last_confidence = event.debug.last_confidence ?? 0;
        this.debugState.safety_awaiting = !!event.debug.safety_awaiting;
      }
    } else if (event.type === "asr_interim_transcript") {
      this.debugState.last_interim = event.transcript;
    } else if (event.type === "asr_final_transcript") {
      this.debugState.last_transcript = event.transcript;
      this.debugState.last_latency_ms = event.latency_ms ?? 0;
      this.debugState.last_status = "TRANSCRIPT";
    } else if (event.type === "voice_action_dispatched") {
      this.debugState.last_status = `ACTION: ${event.action}`;
    }

    // Broadcast event to all listeners
    this.eventListeners.forEach((listener) => {
      try {
        listener(event);
      } catch (e) {
        console.error(e);
      }
    });
  }

  public broadcast(event: any): void {
    this.handleServerEvent(event);
  }

  public async startMicrophoneCapture(): Promise<boolean> {
    if (this.isCapturing) return true;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: false,
      });

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      try {
        this.audioContext = new AudioContextClass({ sampleRate: 16000 });
      } catch (e) {
        this.audioContext = new AudioContextClass();
      }
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      await this.audioContext.audioWorklet.addModule("/audio-processor.js");
      this.workletNode = new AudioWorkletNode(this.audioContext, "maitri-audio-processor");

      this.workletNode.port.onmessage = (event) => {
        const pcmBuffer = event.data as ArrayBuffer;
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(pcmBuffer);
        }
      };

      source.connect(this.workletNode);
      // Connect to destination via zero gain so audio is processed without feedback
      const gainNode = this.audioContext.createGain();
      gainNode.gain.value = 0;
      this.workletNode.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      this.isCapturing = true;
      console.log("🎙️ Microphone capture started via AudioWorklet");
      return true;
    } catch (err) {
      console.warn("⚠️ AudioWorklet initialization fallback:", err);
      return false;
    }
  }

  public stopMicrophoneCapture(): void {
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.isCapturing = false;
  }

  public getIsCapturing(): boolean {
    return this.isCapturing;
  }

  public sendControl(msg: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }
}

export const audioService = new AudioService();
