// Made-up takes for the listening tests (tests/listening.py): a bowed string sound (a sawtooth's harmonics, a little
// vibrato, a soft attack and a little noise) for each note of a Flash a bar pattern, with the count-in clicks before it
// and whatever mistakes a case asks for. Runs in the browser beside sight-reading/listen.js, or in Node.
(function (root, make) {
  if (typeof module === 'object' && module.exports) module.exports = make();
  else root.ListenTakes = make();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  function rand(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  // notes: [{ midi, t, dur, cents }] in seconds; clicks: times; lead: seconds of quiet first.
  function take({ notes, clicks = [], sr = 48000, length, seed = 1, loud = 0.25, noise = 0.004, gapEach = 0.03 }) {
    const r = rand(seed), n = Math.ceil(length * sr), x = new Float32Array(n);
    for (let i = 0; i < n; i++) x[i] = (r() * 2 - 1) * noise;
    for (const c of clicks) { // the speaker's clicks, heard by the microphone
      const s = Math.round(c.t * sr), f = c.strong ? 1600 : 1100;
      for (let k = 0; k < sr * 0.06 && s + k < n; k++) if (s + k >= 0) x[s + k] += 0.05 * Math.sin(2 * Math.PI * f * k / sr) * Math.exp(-k / (sr * 0.015));
    }
    for (const nt of notes) {
      const f0 = 440 * Math.pow(2, (nt.midi - 69 + (nt.cents || 0) / 100) / 12), s0 = Math.round(nt.t * sr), len = Math.round((nt.dur - gapEach) * sr);
      const phases = Array.from({ length: 12 }, () => r() * Math.PI * 2);
      let ph = 0;
      for (let k = 0; k < len && s0 + k < n; k++) {
        const t = k / sr, vib = t > 0.15 ? 0.12 * Math.sin(2 * Math.PI * 5.5 * t) : 0;
        const f = f0 * Math.pow(2, vib / 12);
        ph += 2 * Math.PI * f / sr;
        const env = Math.min(1, t / 0.04) * Math.min(1, (len - k) / (sr * 0.03));
        let v = 0;
        for (let h = 1; h <= 12; h++) if (f * h < sr / 2) v += Math.sin(ph * h + phases[h - 1]) / h;
        if (s0 + k >= 0) x[s0 + k] += loud * env * v * 0.6;
      }
    }
    return x;
  }
  return { take };
});
