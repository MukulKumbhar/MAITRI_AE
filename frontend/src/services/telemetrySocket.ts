import { TelemetryPayload } from "../types";

export type TelemetryCallback = (data: TelemetryPayload) => void;

class TelemetrySocketService {
  private ws: WebSocket | null = null;
  private listeners: Set<TelemetryCallback> = new Set();
  private isConnected: boolean = false;
  private lastPayload: TelemetryPayload | null = null;

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/telemetry`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        console.log("⚡ Telemetry WS connected");
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as TelemetryPayload;
          this.lastPayload = payload;
          this.listeners.forEach((listener) => {
            try {
              listener(payload);
            } catch (e) {
              console.error(e);
            }
          });
        } catch (e) {
          console.error("Telemetry JSON parse error", e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        setTimeout(() => this.connect(), 2000);
      };

      this.ws.onerror = (err) => {
        console.error("Telemetry WS error", err);
      };
    } catch (e) {
      console.error("Telemetry WS connect failed", e);
    }
  }

  public subscribe(cb: TelemetryCallback): () => void {
    this.listeners.add(cb);
    if (this.lastPayload) {
      cb(this.lastPayload);
    }
    return () => this.listeners.delete(cb);
  }

  public sendVitalsUpdate(heart_rate: number, temperature: number, spo2: number): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: "update_vitals",
        heart_rate,
        temperature,
        spo2,
      }));
    }
  }

  public sendWatchdogAck(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "watchdog_ack" }));
    }
  }

  public getLastPayload(): TelemetryPayload | null {
    return this.lastPayload;
  }
}

export const telemetrySocketService = new TelemetrySocketService();
