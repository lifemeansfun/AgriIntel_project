/**
 * Web Audio Synthesizer Engine
 * Zero external audio assets required. All atmospheric frequencies and micro-haptics
 * are synthesized in real-time via the Web Audio API with defensive autoplay handling.
 */

let audioCtx = null;
let ambientGain = null;
let ambientOsc1 = null;
let ambientOsc2 = null;
let isAudioActive = false;

function getAudioContext() {
  if (typeof window === 'undefined') return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

export function playTactileClick() {
  try {
    const ctx = getAudioContext();
    if (!ctx || !isAudioActive) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(620, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(140, ctx.currentTime + 0.04);

    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.04);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.045);
  } catch (_) {
    // Non-critical audio fallback
  }
}

export function playCrystalChime() {
  try {
    const ctx = getAudioContext();
    if (!ctx || !isAudioActive) return;

    const frequencies = [528, 792, 1056]; // Solfeggio Love/Transformation chord
    frequencies.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.03);

      gain.gain.setValueAtTime(0.03, ctx.currentTime + idx * 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35 + idx * 0.03);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime + idx * 0.03);
      osc.stop(ctx.currentTime + 0.4 + idx * 0.03);
    });
  } catch (_) {
    // Non-critical audio fallback
  }
}

export function toggleAmbientSoundscape(enable) {
  try {
    const ctx = getAudioContext();
    if (!ctx) return false;

    if (enable) {
      isAudioActive = true;
      if (!ambientGain) {
        ambientGain = ctx.createGain();
        ambientGain.gain.setValueAtTime(0.0001, ctx.currentTime);
        ambientGain.gain.exponentialRampToValueAtTime(0.025, ctx.currentTime + 1.5);

        // Low binaural breeze frequency
        ambientOsc1 = ctx.createOscillator();
        ambientOsc1.type = 'sine';
        ambientOsc1.frequency.setValueAtTime(108, ctx.currentTime);

        ambientOsc2 = ctx.createOscillator();
        ambientOsc2.type = 'sine';
        ambientOsc2.frequency.setValueAtTime(114, ctx.currentTime); // 6Hz gentle binaural beat

        const filter = ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(260, ctx.currentTime);

        ambientOsc1.connect(filter);
        ambientOsc2.connect(filter);
        filter.connect(ambientGain);
        ambientGain.connect(ctx.destination);

        ambientOsc1.start();
        ambientOsc2.start();
      } else {
        ambientGain.gain.exponentialRampToValueAtTime(0.025, ctx.currentTime + 0.5);
      }
      playCrystalChime();
      return true;
    } else {
      isAudioActive = false;
      if (ambientGain) {
        ambientGain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.5);
      }
      return false;
    }
  } catch (_) {
    return false;
  }
}
