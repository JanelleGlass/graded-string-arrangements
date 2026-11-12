// Listening (sight-reading, round 4): what a student played, worked out from the microphone's sound in the browser.
//
// No page code here, like the generator: Flash a bar (flash.js) hands it the sound of one round, kept in memory for that
// round only (never saved or uploaded), and the tests (tests/listening.py) hand it made-up and recorded takes.
//   track(samples, sampleRate, range)   the pitch and loudness every 10 ms (the McLeod pitch method)
//   notes(track)                         the notes in it: when each starts and ends, and its pitch
//   judge(expected, played, beat)        each expected note: heard or not, right note or not (within half a
//                                        semitone), in tune or not (within 20 cents), early, on time or late
//                                        (a window that grows with the beat), and one kind sentence
//   timing(samples, sampleRate, ...)     the timing check: open A on four clicks, and how late the microphone hears it
(function (root, make) {
  if (typeof module === 'object' && module.exports) module.exports = make();
  else root.Listen = make();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  // The instruments' ranges, in MIDI numbers, a little past first position each way; anything else is ignored.
  const RANGE = { violin: [53, 100], viola: [46, 93] };
  const midiOf = (f) => 69 + 12 * Math.log2(f / 440);

  // Half the samples at 44.1 or 48 kHz: plenty for a violin or viola, and four times less work.
  function halve(x, sr) {
    if (sr < 32000) return { x, sr };
    const n = x.length >> 1, y = new Float32Array(n);
    for (let i = 0; i < n; i++) y[i] = 0.5 * (x[2 * i] + x[2 * i + 1]);
    return { x: y, sr: sr / 2 };
  }

  // ---- Pitch: the McLeod pitch method (normalized square difference, first strong peak) ----
  function mpm(x, start, W, sr, minF, maxF) {
    const tauMax = Math.min(W >> 1, Math.ceil(sr / minF)), tauMin = Math.max(2, Math.floor(sr / maxF));
    const n = new Float32Array(tauMax + 2);
    let m = 0;
    for (let j = 0; j < W; j++) { const v = x[start + j]; m += v * v; }
    m *= 2;
    for (let tau = 0; tau <= tauMax + 1; tau++) {
      if (tau > 0) { const a = x[start + tau - 1], b = x[start + W - tau]; m -= a * a + b * b; }
      let r = 0;
      for (let j = 0, end = W - tau; j < end; j++) r += x[start + j] * x[start + j + tau];
      n[tau] = m > 1e-9 ? (2 * r) / m : 0;
    }
    // The highest point of each positive stretch after the first, then the first of those near the very highest.
    const peaks = [];
    let tau = 1;
    while (tau <= tauMax && n[tau] > 0) tau++;
    while (tau <= tauMax) {
      while (tau <= tauMax && n[tau] <= 0) tau++;
      let best = -1, at = -1;
      while (tau <= tauMax && n[tau] > 0) { if (n[tau] > best) { best = n[tau]; at = tau; } tau++; }
      if (at > 0) peaks.push([at, best]);
    }
    if (!peaks.length) return null;
    const top = Math.max(...peaks.map(p => p[1]));
    const pick = peaks.find(([t, v]) => v >= 0.88 * top && t >= tauMin);
    if (!pick) return null;
    const [t0, v0] = pick, a = n[t0 - 1], b = n[t0], c = n[t0 + 1];
    const d = a - 2 * b + c, shift = d ? (0.5 * (a - c)) / d : 0;
    return { freq: sr / (t0 + shift), clarity: v0 };
  }

  // Every 10 ms: the time (the middle of the window), the loudness, and the pitch as a MIDI number (or null).
  function track(samples, sampleRate, inst) {
    const { x, sr } = halve(samples, sampleRate);
    const W = sr > 16000 ? 1024 : 512, hop = Math.round(sr * 0.01);
    const [lo, hi] = RANGE[inst] || RANGE.violin;
    const minF = 440 * Math.pow(2, (lo - 1 - 69) / 12), maxF = 440 * Math.pow(2, (hi + 1 - 69) / 12);
    const frames = [];
    for (let i = 0; i + W <= x.length; i += hop) {
      let e = 0;
      for (let j = i + (W >> 2); j < i + W - (W >> 2); j++) e += x[j] * x[j];
      frames.push({ t: (i + W / 2) / sr, rms: Math.sqrt(e / (W >> 1)), i });
    }
    // Quiet is anything near the quietest tenth of the take (the count-in bar, before the student plays).
    const sorted = frames.map(f => f.rms).sort((a, b) => a - b);
    const floor = sorted[Math.floor(sorted.length * 0.1)] || 0;
    const gate = Math.max(0.0025, floor * 4);
    for (const f of frames) {
      f.midi = null;
      if (f.rms < gate) continue;
      const p = mpm(x, f.i, W, sr, minF, maxF);
      if (!p || p.clarity < 0.75) continue;
      const m = midiOf(p.freq);
      if (m >= lo - 0.5 && m <= hi + 0.5) f.midi = m;
    }
    return { frames, hop: hop / sr, gate };
  }

  const median = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[s.length >> 1] : NaN; };
  // The notes: a run of steady pitch; a new one where the pitch moves by more than half a semitone and stays there
  // (30 ms), where the bow starts again on the same pitch (loudness dips, then jumps), or after a silence (40 ms).
  function notes(tr) {
    const out = [], fr = tr.frames;
    let cur = null, pend = [], gap = 0;
    const close = (end) => {
      if (cur && end - cur.t0 >= 0.07) out.push({ t0: cur.t0, t1: end, midi: median(cur.m) });
      cur = null;
    };
    for (let k = 0; k < fr.length; k++) {
      const f = fr[k];
      if (f.midi == null) {
        gap++;
        if (cur && gap * tr.hop >= 0.04) { close(f.t - gap * tr.hop); pend = []; }
        continue;
      }
      gap = 0;
      if (!cur) { cur = { t0: f.t, m: [f.midi], peak: f.rms, low: f.rms }; continue; }
      const here = median(cur.m.slice(-8));
      // A bow change on the same note: the sound dips to under half and comes back.
      if (Math.abs(f.midi - here) <= 0.5 && cur.low < cur.peak * 0.45 && f.rms > cur.low * 2.2 && f.t - cur.t0 > 0.12) {
        close(f.t); cur = { t0: f.t, m: [f.midi], peak: f.rms, low: f.rms }; continue;
      }
      if (Math.abs(f.midi - here) <= 0.6) {
        cur.m.push(f.midi); pend = [];
        if (f.rms > cur.peak) { cur.peak = f.rms; cur.low = f.rms; } else cur.low = Math.min(cur.low, f.rms);
        continue;
      }
      pend.push(f);
      if (pend.length > 3) pend.shift(); // the last three readings: one stray reading doesn't hold the next note back
      if (pend.length >= 3 && Math.max(...pend.map(p => p.midi)) - Math.min(...pend.map(p => p.midi)) <= 0.6) {
        close(pend[0].t);
        cur = { t0: pend[0].t, m: pend.map(p => p.midi), peak: Math.max(...pend.map(p => p.rms)), low: f.rms };
        pend = [];
      }
    }
    if (cur) close(fr.length ? fr[fr.length - 1].t : 0);
    return out;
  }

  // Line up what was played with what was written (fewest mistakes, in order) and say how each note went.
  // expected: [{ midi, t }] (seconds from the first beat); played: notes(), on the same clock; beat: seconds a beat.
  function judge(expected, played, beat) {
    const E = expected.length, P = played.length, SKIP_E = 2.4, SKIP_P = 1.1;
    const cost = (e, p) => {
      const d = Math.abs(p.midi - e.midi), dt = Math.abs(p.t0 - e.t) / beat;
      if (dt > 0.75) return Infinity; // too far from its beat to be this note
      return (d <= 0.5 ? 0 : d <= 1.5 ? 1 : 1.6) + dt * 1.6;
    };
    const D = Array.from({ length: E + 1 }, () => new Float64Array(P + 1).fill(Infinity)), how = Array.from({ length: E + 1 }, () => new Int8Array(P + 1));
    D[0][0] = 0;
    for (let i = 0; i <= E; i++) for (let j = 0; j <= P; j++) {
      if (i && D[i - 1][j] + SKIP_E < D[i][j]) { D[i][j] = D[i - 1][j] + SKIP_E; how[i][j] = 1; }
      if (j && D[i][j - 1] + SKIP_P < D[i][j]) { D[i][j] = D[i][j - 1] + SKIP_P; how[i][j] = 2; }
      if (i && j) { const c = D[i - 1][j - 1] + cost(expected[i - 1], played[j - 1]); if (c < D[i][j]) { D[i][j] = c; how[i][j] = 3; } }
    }
    const match = new Array(E).fill(null);
    for (let i = E, j = P; i || j;) {
      const h = how[i][j];
      if (h === 3) { match[i - 1] = played[j - 1]; i--; j--; } else if (h === 1) i--; else j--;
    }
    const win = Math.min(0.15, Math.max(0.06, beat * 0.15)); // on time: within this either side
    const results = expected.map((e, i) => {
      const p = match[i];
      if (!p) return { heard: false };
      const cents = Math.round((p.midi - e.midi) * 100), dt = p.t0 - e.t;
      return { heard: true, right: Math.abs(cents) <= 50, inTune: Math.abs(cents) <= 20, cents, ms: Math.round(dt * 1000),
        timing: dt < -win ? 'early' : dt > win ? 'late' : 'on time' };
    });
    return { results, extra: P - results.filter(r => r.heard).length, say: sentence(results) };
  }

  const NUMBER = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
  const num = (k) => NUMBER[k] || String(k);
  function sentence(results) {
    const n = results.length, heard = results.filter(r => r.heard).length, right = results.filter(r => r.heard && r.right).length;
    const early = results.filter(r => r.heard && r.right && r.timing === 'early').length, late = results.filter(r => r.heard && r.right && r.timing === 'late').length;
    if (!heard) return "I didn't hear the notes. Play a little louder, or come closer to the device.";
    if (heard < n / 2) return 'I heard only ' + num(heard) + ' of the ' + num(n) + ' notes. Play a little louder, or come closer to the device.';
    if (right === n && !early && !late) return n === 1 ? 'Right note, right on time!' : 'Every note right, and right on time!';
    if (right === n) {
      const when = early && late ? 'a little early or late' : early ? 'a little early' : 'a little late';
      return 'Every note right! ' + (early + late === 1 ? 'One was ' : (early + late === n ? 'They were ' : num(early + late).replace(/^./, c => c.toUpperCase()) + ' were ')) + when + '.';
    }
    return (right ? num(right).replace(/^./, c => c.toUpperCase()) + ' of ' + num(n) + ' notes right.' : 'Not quite this time.') + ' Look again at the ones marked.';
  }

  // The timing check (Janelle's brief: play open A on four clicks): how long after a click the microphone hears a note
  // played with it, from the speaker's own delay, the microphone's, and the listening's. The A's are found by their
  // pitch, so the clicks (which the microphone hears too) never count. clicks: when each was made (seconds, the take's
  // clock); beat: seconds. Null unless three of the four are heard.
  function timing(samples, sampleRate, inst, clicks, beat, midi = 69) {
    const found = notes(track(samples, sampleRate, inst)).filter(n => Math.abs(n.midi - midi) < 0.8);
    const diffs = [];
    for (const c of clicks) {
      const near = found.filter(n => n.t0 > c - 0.3 * beat && n.t0 < c + 0.6 * beat).sort((a, b) => Math.abs(a.t0 - c) - Math.abs(b.t0 - c))[0];
      if (near) diffs.push(near.t0 - c);
    }
    if (diffs.length < 3) return null;
    return { offset: median(diffs), heard: diffs.length, spread: Math.max(...diffs) - Math.min(...diffs) };
  }
  return { track, notes, judge, timing, sentence, RANGE, midiOf };
});
