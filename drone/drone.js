// The drone: a held note or chord to tune scales to, made in the browser with Web Audio. No recordings, so it works
// offline and is exactly in tune. Used by the Drone page (drone/page.js) and, from round 2, the scale studies.
//
// No page code here: the Drone page and the tests (tests/drone.py) run it the same way, and the scale studies will too.
//
// Keys go round the circle of fifths, each major followed by its relative minor (Janelle, 2026-11-11): C, A minor, G,
// E minor, D, B minor ... F, D minor, then C again. Six flats as Hřímalý writes them, G♭ major and E♭ minor (F♯ and D♯
// shown beside them), then D♭ major and B♭ minor.
//
// Settings (the page keeps them on the device, localStorage 'drone'):
//   notes    'tonic', 'fifth' (tonic + 5th) or 'triad' (major or minor, from the key)
//   tuning   'pure': the root tuned from A in equal temperament, so it agrees with a tuner and the site's playback;
//            above it the fifth at exactly 3:2, a major third at 5:4, a minor third at 6:5, so nothing beats.
//            'piano': every note equal-tempered, like the site's playback or a piano.
//   a        the reference A, 438 to 445 (orchestras she plays with use 440 or 442)
//   octave   'low', 'middle' or 'high': where the root sits. Middle is the octave from the viola's C string up
//            (C3 to B3), low the cello's C-string octave (C2 to B2), high the octave from middle C (C4 to B4).
//   voicing  'open': the root, the fifth above it, and the third an octave above that (a 10th over the root), so the
//            chord rings rather than buzzes; 'close': root, third and fifth together. Janelle picks by ear.
//   sound    'bowed' (warm, like a cello), 'organ' or 'soft' (plain)
//   volume   0 to 1
//
// The sound: each note is an oscillator playing one cycle of a wave made of exact whole-number partials, so in Pure
// every partial of every note lands on a partial of the root's series: steady, no vibrato, no beating. A chord fades in
// (FADE_IN) when it starts and out (FADE_OUT) when it stops; a new key or setting crossfades (XFADE). Every fade is a
// ramp on a gain of its own that is ramped once and never cancelled (a chord's in-gain goes up, its out-gain goes down,
// the sound is their product), so a fade can start part-way through another without a jump: no clicks.
(function (root, make) {
  if (typeof module === 'object' && module.exports) module.exports = make();
  else root.Drone = make();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const LETTERS = 'CDEFGAB';
  const NATURAL = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  // "F#" -> "F♯", "Bb" -> "B♭" (no look-behind in the pattern: older iPads' Safari can't read one, and would lose the page)
  const pretty = (n) => n[0] + n.slice(1).replace('##', '\u{1D12A}').replace('#', '♯').replace('bb', '\u{1D12B}').replace('b', '♭');
  const pcOf = (n) => ((NATURAL[n[0]] + (n.slice(1).match(/#/g) || []).length - (n.slice(1).match(/b/g) || []).length) % 12 + 12) % 12;

  // ---- The circle of fifths ----
  const MAJORS = ['C', 'G', 'D', 'A', 'E', 'B', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F'];
  const MINORS = ['A', 'E', 'B', 'F#', 'C#', 'G#', 'Eb', 'Bb', 'F', 'C', 'G', 'D'];
  const ALSO = { Gb: 'F#', Ebm: 'D#' }; // the other name of the six-flat keys, shown small beside them
  const CIRCLE = [];
  MAJORS.forEach((tonic, i) => {
    for (const [t, mode] of [[tonic, 'major'], [MINORS[i], 'minor']]) {
      const id = t + (mode === 'minor' ? 'm' : '');
      CIRCLE.push({ id, tonic: t, mode, pos: i, pc: pcOf(t), label: pretty(t), name: `${pretty(t)} ${mode}`,
        also: ALSO[id] ? pretty(ALSO[id]) : '' });
    }
  });
  const index = (id) => Math.max(0, CIRCLE.findIndex((k) => k.id === id));
  const keyById = (id) => CIRCLE[index(id)];
  // Next (+1) and Previous (-1) around the circle, wrapping both ways.
  const step = (id, by) => CIRCLE[((index(id) + by) % CIRCLE.length + CIRCLE.length) % CIRCLE.length];

  // A note's name, spelled from the tonic: so many letters up, so many semitones up (the third of G♯ minor is B).
  function spell(tonic, letters, semis) {
    const letter = LETTERS[(LETTERS.indexOf(tonic[0]) + letters) % 7];
    const off = ((pcOf(tonic) + semis - NATURAL[letter]) % 12 + 18) % 12 - 6;
    return letter + (off > 0 ? '#'.repeat(off) : 'b'.repeat(-off));
  }

  // ---- The choices (in the order a tap steps through them) ----
  const CHOICES = {
    notes: [['tonic', 'Tonic'], ['fifth', 'Tonic + 5th'], ['triad', 'Triad']],
    tuning: [['pure', 'Pure'], ['piano', 'Piano']],
    octave: [['low', 'Low'], ['middle', 'Middle'], ['high', 'High']],
    voicing: [['open', 'Open'], ['close', 'Close']],
    sound: [['bowed', 'Bowed'], ['organ', 'Organ'], ['soft', 'Soft']],
  };
  const A_MIN = 438, A_MAX = 445;
  const DEFAULTS = { key: 'C', notes: 'triad', tuning: 'pure', a: 440, octave: 'middle', voicing: 'open', sound: 'bowed', volume: 0.8 };
  // Settings from anywhere (a saved copy, an address), made safe: anything unknown takes the default.
  function clean(s) {
    const out = { ...DEFAULTS };
    if (!s || typeof s !== 'object') return out;
    if (CIRCLE.some((k) => k.id === s.key)) out.key = s.key;
    for (const k of Object.keys(CHOICES)) if (CHOICES[k].some(([v]) => v === s[k])) out[k] = s[k];
    const a = Math.round(Number(s.a));
    if (a >= A_MIN && a <= A_MAX) out.a = a;
    const v = Number(s.volume);
    if (s.volume !== undefined && s.volume !== null && isFinite(v)) out.volume = Math.min(1, Math.max(0, v));
    return out;
  }

  // ---- Tuning ----
  const OCTAVE_BASE = { low: 36, middle: 48, high: 60 }; // MIDI note of C at the bottom of each octave band (C2, C3, C4)
  const equal = (midi, a) => a * Math.pow(2, (midi - 69) / 12);

  // The drone's notes for a key and settings, lowest first: [{ name, midi, hz }]. midi is the note's place on a piano.
  function notes(keyOrId, settings) {
    const key = typeof keyOrId === 'string' ? keyById(keyOrId) : keyOrId;
    const s = clean({ ...settings, key: key.id });
    const minor = key.mode === 'minor';
    const root = OCTAVE_BASE[s.octave] + key.pc;
    const rootHz = equal(root, s.a);
    // Each note above the root: letters and semitones up, and its pure ratio over the root.
    const fifth = { letters: 4, semis: 7, ratio: 3 / 2 };
    const third = minor ? { letters: 2, semis: 3, ratio: 6 / 5 } : { letters: 2, semis: 4, ratio: 5 / 4 };
    const up = (iv, octaves = 0) => ({ letters: iv.letters, semis: iv.semis + 12 * octaves, ratio: iv.ratio * Math.pow(2, octaves) });
    let above = [];
    if (s.notes === 'fifth') above = [fifth];
    else if (s.notes === 'triad') above = s.voicing === 'open' ? [fifth, up(third, 1)] : [third, fifth];
    return [{ letters: 0, semis: 0, ratio: 1 }, ...above].map((iv) => ({
      name: pretty(spell(key.tonic, iv.letters, iv.semis)),
      midi: root + iv.semis,
      hz: s.tuning === 'pure' ? rootHz * iv.ratio : equal(root + iv.semis, s.a),
    }));
  }

  // ---- The sounds: how strong each partial is (1 the note itself, 2 an octave up, 3 a twelfth up...) ----
  const SOUNDS = {
    // Warm and bowed, like a cello: every partial, falling away gently, darker above about 2 kHz.
    bowed: (hz) => {
      const amps = [0];
      for (let n = 1; n <= 40 && n * hz < 9000; n++) amps.push((1 / Math.pow(n, 0.9)) / Math.sqrt(1 + Math.pow(n * hz / 2200, 4)) * (n === 2 ? 1.15 : 1));
      return amps;
    },
    // An organ's flue pipes: the note, the octave, the twelfth, two octaves, and a little above.
    organ: () => [0, 1, 0.55, 0.32, 0.3, 0, 0.12, 0, 0.1],
    // Soft and plain: nearly a pure tone.
    soft: () => [0, 1, 0.12, 0.035],
  };
  // How loud each sound is against the others. Measured (2026-11-16): within 3 dB of each other, the brighter ones a
  // little quieter by the meter, which the ear hears as about even, so all are left at 1 until Janelle says otherwise.
  const TRIM = { bowed: 1, organ: 1, soft: 1 };
  // The chord's notes share the room, each at 1/√n, and the loudest at full volume: a triad's peaks reach √3 × 0.5 =
  // 0.87, and quick key changes, a few chords fading over each other, stay under 1 (tests/drone.py checks it), so the
  // sound never clips.
  const LOUDEST = 0.5;
  const loud = (v) => LOUDEST * v * v; // the slider's way from quiet to loud

  const FADE_IN = 0.4, FADE_OUT = 0.4, XFADE = 0.25; // seconds

  // ---- The drone itself ----
  // createDrone() makes its own audio when it first starts (on a tap: phones allow sound only then). Give it a context
  // (an OfflineAudioContext in the tests) to play into that instead.
  function createDrone(given) {
    let ctx = given || null, master = null, meter = null, ran = false, rest = 0;
    let chord = null, playing = false;
    let s = clean(DEFAULTS);
    const listeners = [];
    const offline = () => !!ctx && typeof ctx.startRendering === 'function';
    const emit = (why) => { for (const fn of listeners) { try { fn(why); } catch (e) { setTimeout(() => { throw e; }); } } };
    const waves = new Map();

    function wave(sound, hz) {
      const amps = SOUNDS[sound](hz);
      const k = sound + ':' + amps.length + ':' + (sound === 'bowed' ? Math.round(hz / 4) : 0);
      if (!waves.has(k)) {
        const imag = new Float32Array(amps), real = new Float32Array(amps.length);
        waves.set(k, ctx.createPeriodicWave(real, imag));
      }
      return waves.get(k);
    }

    function ensure() {
      if (!ctx) {
        // iPhone and iPad: play with the ringer switch off (app/app.js sets this for the page too).
        try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {}
        const AC = (typeof window !== 'undefined') && (window.AudioContext || window.webkitAudioContext);
        try { ctx = new AC({ latencyHint: 'playback' }); } catch (e) { ctx = new AC(); }
      }
      if (!master) {
        master = ctx.createGain();
        master.gain.value = loud(s.volume);
        meter = ctx.createAnalyser();
        meter.fftSize = 2048;
        master.connect(meter);
        meter.connect(ctx.destination);
        // A phone call, Siri or another app can stop the sound on a phone. Then the drone stops too, and Start
        // (one tap) brings it back, rather than it carrying on silently or coming back by itself with a jolt.
        ctx.addEventListener('statechange', () => {
          if (ctx.state === 'running') { ran = true; return; }
          if (!playing || !ran) return;
          playing = false; ran = false;
          if (chord) { for (const o of chord.oscs) { try { o.stop(); } catch (e) {} } try { chord.out.disconnect(); } catch (e) {} chord = null; }
          emit('interrupted');
        });
      }
    }

    // A chord, fading in from time t over `fade` seconds.
    function build(t, fade) {
      const list = notes(s.key, s);
      const inG = ctx.createGain(), out = ctx.createGain();
      inG.gain.value = 0;
      out.gain.value = 1;
      inG.connect(out);
      out.connect(master);
      inG.gain.setValueAtTime(0, t);
      inG.gain.linearRampToValueAtTime(1, t + fade);
      const each = TRIM[s.sound] / Math.sqrt(list.length);
      const oscs = list.map((n) => {
        const o = ctx.createOscillator();
        o.setPeriodicWave(wave(s.sound, n.hz));
        o.frequency.value = n.hz;
        const g = ctx.createGain();
        g.gain.value = each;
        o.connect(g);
        g.connect(inG);
        o.start(t);
        return o;
      });
      return { list, inG, out, oscs, gone: false };
    }

    // A chord fading out from time t, then stopped and let go.
    function retire(c, t, fade) {
      if (!c || c.gone) return;
      c.gone = true;
      c.out.gain.setValueAtTime(1, t);
      c.out.gain.linearRampToValueAtTime(0, t + fade);
      const end = t + fade + 0.05;
      c.oscs.forEach((o, i) => {
        if (i === 0) o.onended = () => { try { c.out.disconnect(); } catch (e) {} };
        o.stop(end);
      });
    }

    const now = () => ctx.currentTime;

    function start() {
      if (playing) return;
      ensure();
      clearTimeout(rest);
      if (!offline() && ctx.state !== 'running') { try { const p = ctx.resume(); if (p && p.catch) p.catch(() => {}); } catch (e) {} }
      ran = ctx.state === 'running';
      playing = true;
      chord = build(now(), FADE_IN);
      emit('start');
    }

    function stop() {
      if (!playing) return;
      playing = false;
      retire(chord, now(), FADE_OUT);
      chord = null;
      if (!offline()) {
        clearTimeout(rest);
        // Let the speaker rest once the fade is over (and the phone's battery).
        rest = setTimeout(() => { if (!playing && ctx.state === 'running') { try { ctx.suspend().catch(() => {}); } catch (e) {} } }, (FADE_OUT + 0.25) * 1000);
      }
      emit('stop');
    }

    // Change the key or any setting. While playing, the new chord crossfades in; the volume glides.
    function set(changes) {
      const next = clean({ ...s, ...changes });
      const sounding = ['key', 'notes', 'tuning', 'a', 'octave', 'voicing', 'sound'].some((k) => next[k] !== s[k]);
      const louder = next.volume !== s.volume;
      s = next;
      if (louder && master) master.gain.setTargetAtTime(loud(s.volume), now(), 0.03);
      if (sounding && playing) {
        const t = now(), old = chord;
        chord = build(t, XFADE);
        retire(old, t, XFADE);
      }
      if (sounding || louder) emit('set');
    }

    // How loud the drone is right now (0 when silent), from what goes to the speaker.
    function level() {
      if (!meter) return 0;
      const buf = new Float32Array(meter.fftSize);
      meter.getFloatTimeDomainData(buf);
      let sum = 0;
      for (const x of buf) sum += x * x;
      return Math.sqrt(sum / buf.length);
    }

    return {
      start, stop, set,
      toggle() { if (playing) stop(); else start(); },
      settings: () => ({ ...s }),
      state: () => ({ playing, key: s.key, settings: { ...s }, ctx: ctx ? ctx.state : 'none', notes: notes(s.key, s), level: level() }),
      onchange(fn) { listeners.push(fn); },
      get context() { return ctx; },
    };
  }

  return { CIRCLE, CHOICES, DEFAULTS, A_MIN, A_MAX, FADE_IN, FADE_OUT, XFADE, OCTAVE_BASE, LOUDEST,
    keyById, index, step, spell, notes, clean, pretty, createDrone, SOUNDS, TRIM };
});
