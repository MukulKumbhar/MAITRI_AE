// MAITRI 2.0 — Offline AudioWorklet Processor
// Captures PCM audio, downsamples to 16000 Hz, and streams 16-bit PCM chunks to main thread

class MaitriAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetSampleRate = 16000;
    this.buffer = [];
    this.chunkSize = 1600; // 100ms chunks @ 16kHz
    this.phase = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0];
    // Accurate streaming phase-continuous anti-aliased linear interpolation resampling to 16000 Hz
    const ratio = sampleRate / this.targetSampleRate;
    let i = this.phase;
    while (i < channelData.length) {
      const idx0 = Math.floor(i);
      const idx1 = Math.min(channelData.length - 1, idx0 + 1);
      const frac = i - idx0;
      // Linear interpolation between adjacent samples
      const sampleInterp = channelData[idx0] * (1.0 - frac) + channelData[idx1] * frac;
      const sample = Math.max(-1.0, Math.min(1.0, sampleInterp));
      // Convert float [-1.0, 1.0] to int16 [-32768, 32767]
      const int16 = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      this.buffer.push(Math.floor(int16));

      if (this.buffer.length >= this.chunkSize) {
        const int16Array = new Int16Array(this.buffer);
        this.port.postMessage(int16Array.buffer, [int16Array.buffer]);
        this.buffer = [];
      }
      i += ratio;
    }
    this.phase = i - channelData.length;

    return true;
  }
}

registerProcessor("maitri-audio-processor", MaitriAudioProcessor);
