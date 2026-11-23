const tune = [523.25, 392, 349.23, 440, 293.66];

export class FilmSound {
  constructor() {
    this.context = null;
    this.pending = [];
    this.enabled = false;
  }

  async enable() {
    const Audio = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!Audio) return false;
    if (!this.context) {
      this.context = new Audio();
      this.captureBus = this.context.createMediaStreamDestination();
      this.bus = this.context.createGain();
      this.bus.gain.value = 2.05;
      this.bus.connect(this.context.destination);
      this.bus.connect(this.captureBus);
    }
    await this.context.resume();
    this.enabled = this.context.state === "running";
    return this.enabled;
  }

  stop() {
    if (this.context) {
      for (const source of this.pending) {
        try { source.stop(); } catch { /* Ended sources may already be gone. */ }
      }
    }
    this.pending = [];
  }

  output() {
    return this.enabled && this.captureBus ? this.captureBus.stream.getAudioTracks() : [];
  }

  play(shot, speed) {
    if (!this.enabled || !this.context) return;
    this.stop();
    const audio = this.context;
    const start = audio.currentTime;
    const hold = shot.duration_ms / (1000 * speed);
    const tone = (onset, seconds, pitch, volume) => {
      const envelope = audio.createGain();
      envelope.connect(this.bus);
      envelope.gain.setValueAtTime(.001, start + onset);
      envelope.gain.linearRampToValueAtTime(volume, start + onset + .014);
      envelope.gain.exponentialRampToValueAtTime(.001, start + onset + seconds);
      for (const [multiple, amplitude] of [[1, 1], [2.003, .22], [3.011, .075]]) {
        const oscillator = audio.createOscillator();
        const gain = audio.createGain();
        oscillator.frequency.value = pitch * multiple;
        gain.gain.value = amplitude;
        oscillator.connect(gain).connect(envelope);
        oscillator.start(start + onset);
        oscillator.stop(start + onset + seconds);
        this.pending.push(oscillator);
      }
    };
    const noise = (onset, seconds, volume, roughness) => {
      const buffer = audio.createBuffer(1, Math.round(seconds * audio.sampleRate), audio.sampleRate);
      const data = buffer.getChannelData(0);
      let last = 0;
      let seed = 21979 * (shot.event_index + 1);
      for (let i = 0; i < data.length; i++) {
        seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
        last = last * (1 - roughness) + (2 * seed / 4294967296 - 1) * roughness;
        data[i] = last * volume * Math.min(1, i * 80 / audio.sampleRate) * Math.exp(-3.6 * i / data.length);
      }
      const source = audio.createBufferSource();
      source.buffer = buffer;
      source.connect(this.bus);
      source.start(start + onset);
      this.pending.push(source);
    };
    const cue = shot.sound;
    if (cue === "radio" || cue === "tomorrow") {
      noise(hold * .21, .5, .19, .67);
      tune.forEach((pitch, index) => tone(hold * .24 + index * .16 / speed, .56, pitch * (cue === "tomorrow" ? 1.25 : 1), .12));
    } else if (cue === "splash") {
      noise(hold * .37, .64, .21, .35);
      tone(hold * .39, .16, 179, .09);
    } else if (cue === "wind") {
      noise(0, hold, .33, .047);
    } else if (cue === "snap") {
      noise(hold * .27, .19, .23, .95);
    } else if (cue === "bell") {
      tone(hold * .14, 1.8, 293.66, .14);
    } else if (cue === "piano" || cue === "practice") {
      const pitches = cue === "practice" ? tune.slice(2) : [...tune, 349.23, 493.88, 587.33, 392];
      const spacing = cue === "practice" ? .18 : .073;
      pitches.forEach((pitch, index) => tone(hold * (.15 + spacing * index), .73, pitch, .12));
    } else if (cue === "steps") {
      [.18, .39, .60, .83].forEach(offset => noise(hold * offset, .12, .085, .27));
    }
    const root = [130.81, 146.83, 110, 130.81][shot.loop % 4];
    tone(0, Math.min(hold + .28, 4.4), root, .018);
    tone(.035, Math.min(hold, 4.1), root * 1.5, .014);
  }
}

const castDelivery = {
  phil: [.80, .98, 0], rita: [1.12, 1.00, 1], larry: [.86, .91, 2], ned: [1.19, 1.11, 3],
};

export class CastSpeech {
  constructor(onChange) {
    this.engine = globalThis.speechSynthesis;
    this.enabled = false;
    this.voices = [];
    const refresh = () => {
      if (!this.engine || !globalThis.SpeechSynthesisUtterance) return;
      this.voices = this.engine.getVoices().filter(voice => voice.localService && /^en(?:-|$)/i.test(voice.lang))
        .sort((left, right) => left.name.localeCompare(right.name));
      onChange(this.voices.length > 0);
    };
    this.engine?.addEventListener("voiceschanged", refresh);
    refresh();
  }

  stop() {
    if (this.active) this.engine?.cancel();
    this.active = null;
  }

  speak(shot, speed) {
    this.stop();
    if (!this.enabled || !this.voices.length || !shot.speaker || !shot.caption) return;
    const [pitch, pace, voiceIndex] = castDelivery[shot.actor] || [1, 1, 0];
    const speech = new SpeechSynthesisUtterance(shot.caption);
    speech.voice = this.voices[voiceIndex % this.voices.length];
    speech.pitch = pitch;
    speech.rate = Math.min(1.85, speed * Math.max(pace, shot.caption.split(/\s+/).length * 310 / shot.duration_ms));
    speech.volume = .82;
    this.active = speech;
    this.engine.speak(speech);
  }
}
