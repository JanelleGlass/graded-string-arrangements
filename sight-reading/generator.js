// Sight-reading: a book page's rules in, a new exercise out, written as MusicXML for the reader.
//
// No page code here: the sight-reading page (practice.js) and the tests (tests/sight_reading.py) run it the same way.
// The same page and exercise number always make the same music, on every device: the random choices come from a
// seeded generator, and nothing here works differently from one browser to another. So a teacher can put one exercise
// on every stand in group class. Violin and viola with the same number get the same exercise a fifth apart.
//
// A book page is a small set of rules (sight-reading/pages.json):
//   id, title     "v1-02", "Page 2: A string 1, 2, 3"
//   notes         what the student has learned so far, in violin string names: "A3" is third finger on A, "E0" open E
//   new           the notes (or rhythms) the page brings in: every exercise has each of them at least twice
//   pattern       each string's finger pattern: high2 (C♯ on the A string), low2 (C), low1, high3; high2 if not given
//   key           "A major" (the viola's key is a fifth lower, worked out here)
//   time          ["4/4"]: 2/4, 3/4 and 4/4 so far (with more than one, each exercise takes one of them)
//   rhythms       what may be used: w, h., h, q, "8 8" (two beamed eighths), "q. 8", and the rests qr, hr
//   bars          how long an exercise is
//   maxLeap       the biggest leap, as an interval: 2 a step, 3 a third, 4 a fourth, 5 a fifth
//   crossings     "few" (one a bar at most), "some" (any number, never to or from an eighth note), "free"
//   tempo         [slowest, fastest]: an exercise starts at the slowest
//   help          what shows on the notes at first: { "colors": true, "look": "plain" } (looks: plain, fingers,
//                 fingers-left, names, names-fingers)
//   viola         only what is different for viola ({ "notes", "pattern", "key", "new" }), in viola string names.
//                 Without it the viola plays the same fingers a fifth lower, as in the Suzuki viola books (A3 is D3).
//   placeholder   true for a made-up page, until Janelle writes the real ones
//
// How an exercise is made: the rhythm of each bar first (the second phrase starts with the first phrase's rhythm, and
// the last bar is the home note, long, on beat 1), then a chord for each bar or half bar (I, IV and V, only the ones the
// page's notes can outline; the first phrase ends on V, the last goes V to I), then the notes: chord notes on the strong
// beats, mostly steps between, any other note moving by step on at least one side, a leap of a fourth or more followed
// by a turn the other way, never past maxLeap, crossings as the page allows, and the page's new notes at least twice each.
// Half the time the second phrase also starts with the first phrase's notes and chords.
(function (root, make) {
  if (typeof module === 'object' && module.exports) module.exports = make();
  else root.SightReading = make();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const LETTERS = 'CDEFGAB';
  const NATURAL = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  // The open strings, as MIDI note numbers (middle C is 60).
  const OPEN = { violin: { E: 76, A: 69, D: 62, G: 55 }, viola: { A: 69, D: 62, G: 55, C: 48 } };
  const VIOLA_STRING = { E: 'A', A: 'D', D: 'G', G: 'C' }; // the same fingers a fifth lower
  // Janelle's string colors (BUILD-SPEC), on the note and its head as in her scores.
  const COLORS = { E: '#F0B000', A: '#DC2626', D: '#1D4ED8', G: '#15803D', C: '#7C3AED' };
  // How many semitones above the open string each finger (0 to 4) sits.
  const PATTERNS = { high2: [0, 2, 4, 5, 7], low2: [0, 2, 3, 5, 7], low1: [0, 1, 3, 5, 7], high3: [0, 2, 4, 6, 7] };
  // Finger numbers as Janelle's scores write them: a plain number where the finger usually sits in first position
  // (1 a whole step above the open string, 2 a major third, 3 a fourth, 4 a fifth), an arrow where it moves (↓1 low 1,
  // ↓2 low 2, ↑3 high 3, ↓4 / ↑4).
  const USUAL = PATTERNS.high2;
  const SHARPS = 'FCGDAEB', FLATS = 'BEADGCF';
  const MAJOR = ['Cb', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#']; // by fifths, -7 to 7
  const MINOR = ['Ab', 'Eb', 'Bb', 'F', 'C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#'];
  const NOTE = /^([EADGC])([0-4])$/;

  // Rhythm tokens: their notes (in eighths) and whether they are rests.
  const TOKENS = {
    'w': { parts: [8] }, 'h.': { parts: [6] }, 'h': { parts: [4] }, 'q': { parts: [2] },
    '8 8': { parts: [1, 1] }, 'q. 8': { parts: [3, 1] },
    'qr': { parts: [2], rest: true }, 'hr': { parts: [4], rest: true },
    'h.r': { parts: [6], rest: true }, 'wr': { parts: [8], rest: true }, // a bar's rest (a duet's Part 2, as a last resort)
  };
  for (const t of Object.values(TOKENS)) t.len = t.parts.reduce((a, b) => a + b, 0);
  const BAR = { '2/4': 4, '3/4': 6, '4/4': 8 }; // a bar's length in eighths
  // The last bar: the home note on beat 1, as long as the page's rhythms allow, then rests if it needs them.
  const ENDINGS = { 8: [['w'], ['h.', 'qr'], ['h', 'hr'], ['h', 'qr', 'qr']], 6: [['h.'], ['h', 'qr']], 4: [['h'], ['q', 'qr']] };
  // How often each token comes up, before the page's new ones are favoured.
  const TOKEN_WEIGHT = { 'w': 0.5, 'h.': 1.1, 'h': 2, 'q': 3, '8 8': 1.6, 'q. 8': 1.1, 'qr': 1, 'hr': 0.6, 'h.r': 0.5, 'wr': 0.5 };
  // Chords by the scale degree of their root (0 is I, 3 is IV, 4 is V), and how likely each one is to follow another.
  // V never goes to IV.
  const NAMES = { 0: 'I', 3: 'IV', 4: 'V' };
  const MOVE = { 0: { 0: 3, 3: 2, 4: 2 }, 3: { 3: 1.5, 4: 2, 0: 1 }, 4: { 4: 1.5, 0: 2, 3: 0 } };
  // What shows on the notes, by the page's help.look, in the reader's own words for its settings.
  const LOOKS = {
    'plain': { fingerMode: 'off', letters: 'off' },
    'fingers': { fingerMode: 'all', fingers: 'inside', letters: 'off' },
    'fingers-left': { fingerMode: 'all', fingers: 'left', letters: 'off' },
    'names': { fingerMode: 'off', letters: 'all' },
    'names-fingers': { fingerMode: 'all', letters: 'all' },
  };

  // ---- Random numbers: the same from the same seed everywhere ----
  function hash(text) {
    let h = 2166136261;
    for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function seeded(text) {
    let a = hash(text);
    return () => {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function pick(items, weights, rng) {
    let total = 0;
    for (const w of weights) total += w;
    let r = rng() * total;
    for (let k = 0; k < items.length; k++) { if (r < weights[k]) return items[k]; r -= weights[k]; }
    return items[items.length - 1];
  }
  // Every item, in a random order where heavier ones tend to come first.
  function shuffle(items, weights, rng) {
    items = items.slice(); weights = weights.slice();
    const out = [];
    while (items.length) {
      let total = 0;
      for (const w of weights) total += w;
      let r = rng() * total, k = 0;
      while (k < items.length - 1 && r >= weights[k]) { r -= weights[k]; k++; }
      out.push(items[k]); items.splice(k, 1); weights.splice(k, 1);
    }
    return out;
  }

  // ---- Keys and notes ----
  function parseKey(text) {
    const m = /^\s*([A-G])\s*(#|\u266F|b|\u266D)?\s*(major|minor)\s*$/i.exec(text || '');
    if (!m) throw new Error('key "' + text + '": write it like "A major" or "D minor"');
    const mode = m[3].toLowerCase(), acc = m[2] ? (/#|\u266F/.test(m[2]) ? '#' : 'b') : '';
    const fifths = (mode === 'minor' ? MINOR : MAJOR).indexOf(m[1].toUpperCase() + acc) - 7;
    if (fifths < -7) throw new Error('key "' + text + '" has more than seven sharps or flats');
    return keyOf(m[1].toUpperCase(), acc, mode, fifths);
  }
  function keyOf(tonic, acc, mode, fifths) {
    return { tonic, mode, fifths, name: tonic + (acc === '#' ? '\u266F' : acc === 'b' ? '\u266D' : '') + ' ' + mode };
  }
  function fifthLower(key) {
    const fifths = key.fifths - 1;
    if (fifths < -7) throw new Error('the viola key a fifth below ' + key.name + ' has too many flats: give the page a viola key');
    const name = (key.mode === 'minor' ? MINOR : MAJOR)[fifths + 7];
    return keyOf(name[0], name.slice(1), key.mode, fifths);
  }
  // The sharp or flat the key signature puts on a letter.
  const keyAlter = (fifths, letter) => fifths > 0 ? (SHARPS.indexOf(letter) < fifths ? 1 : 0) : fifths < 0 ? (FLATS.indexOf(letter) < -fifths ? -1 : 0) : 0;
  const fingerLabel = (finger, semis) => !finger ? '0' : semis < USUAL[finger] ? '\u2193' + finger : semis > USUAL[finger] ? '\u2191' + finger : String(finger);

  function makeNote(name, inst, patterns, key) {
    const m = NOTE.exec(name);
    if (!m) throw new Error('note "' + name + '": write a string and a finger, like A3');
    const string = m[1], finger = Number(m[2]), open = OPEN[inst][string];
    if (open === undefined) throw new Error('note "' + name + '": the ' + inst + ' has no ' + string + ' string');
    const pattern = Array.isArray(patterns[string]) ? patterns[string] : PATTERNS[patterns[string] || 'high2']; // or each finger's semitones
    if (!pattern) throw new Error('finger pattern "' + patterns[string] + '" on the ' + string + ' string: use ' + Object.keys(PATTERNS).join(', '));
    const semis = pattern[finger], midi = open + semis;
    // In first position each finger is the next letter up the string (A string: A, B, C, D, E).
    const letter = LETTERS[(LETTERS.indexOf(string) + finger) % 7];
    let octave = Math.floor(midi / 12) - 1, natural = 12 * (octave + 1) + NATURAL[letter];
    if (natural - midi > 6) { octave--; natural -= 12; } else if (midi - natural > 6) { octave++; natural += 12; }
    return {
      name, string, finger, midi, letter, octave, alter: midi - natural,
      dia: octave * 7 + LETTERS.indexOf(letter), // steps up the staff: tells a step from a skip
      degree: (LETTERS.indexOf(letter) - LETTERS.indexOf(key.tonic) + 7) % 7, // 0 is the home note
      color: COLORS[string], label: fingerLabel(finger, semis),
    };
  }

  // The page's rules for one instrument.
  function rulesFor(page, inst) {
    if (!OPEN[inst]) throw new Error('instrument "' + inst + '": violin or viola');
    let names = page.notes || [], patterns = page.pattern || {}, key = parseKey(page.key), fresh = page.new || [];
    if (inst === 'viola') {
      const v = page.viola || {}, move = (n) => NOTE.test(n) && VIOLA_STRING[n[0]] ? VIOLA_STRING[n[0]] + n[1] : n;
      names = v.notes || names.map(move);
      patterns = v.pattern || Object.fromEntries(Object.entries(patterns).map(([s, p]) => [VIOLA_STRING[s] || s, p]));
      key = v.key ? parseKey(v.key) : fifthLower(key);
      fresh = v.new || fresh.map(move);
    }
    const notes = names.map(n => makeNote(n, inst, patterns, key));
    const rhythms = page.rhythms || [];
    for (const t of rhythms) if (!TOKENS[t]) throw new Error('rhythm "' + t + '": use ' + Object.keys(TOKENS).join(', '));
    const times = page.time && page.time.length ? page.time : ['4/4'];
    for (const t of times) if (!BAR[t]) throw new Error('time "' + t + '": use ' + Object.keys(BAR).join(', '));
    const newNotes = fresh.filter(x => NOTE.test(x)), newRhythms = fresh.filter(x => TOKENS[x]);
    for (const x of fresh) if (!newNotes.includes(x) && !newRhythms.includes(x)) throw new Error('new "' + x + '" is neither a note nor a rhythm');
    for (const x of newNotes) if (!names.includes(x)) throw new Error('new note ' + x + ' is not in the notes');
    for (const x of newRhythms) if (!rhythms.includes(x)) throw new Error('new rhythm ' + x + ' is not in the rhythms');
    if (!notes.some(n => n.degree === 0)) throw new Error('none of the notes is the home note of ' + key.name);
    const chords = [0, 3, 4].filter(r => canOutline(notes, r));
    return {
      inst, key, notes, rhythms, times, chords, newNotes, newRhythms,
      bars: Math.max(1, Math.round(page.bars || 4)),
      maxLeap: Math.max(2, page.maxLeap || 3),
      crossings: ['few', 'some', 'free'].includes(page.crossings) ? page.crossings : 'some',
    };
  }
  const chordTones = (root) => [root, (root + 2) % 7, (root + 4) % 7];
  // A chord the notes can outline: they have its root, or two of its notes.
  function canOutline(notes, root) {
    const have = new Set(notes.map(n => n.degree));
    return have.has(root) || chordTones(root).filter(d => have.has(d)).length >= 2;
  }

  // ---- Rhythm ----
  // Every token starts on a beat. In 4/4 nothing longer than a beat runs over the middle of the bar unless it starts on
  // beat 1 (no half note on beat 2), the way beginners' music is written.
  function fits(t, pos, len) {
    const L = TOKENS[t].len;
    if (pos % 2 || pos + L > len) return false;
    return !(len === 8 && pos > 0 && pos < 4 && pos + L > 4);
  }
  const fillCache = new Map();
  // Every way to fill a bar with the page's rhythms: at most one rest, and at least one note.
  function fillings(tokens, len) {
    const id = tokens.join('|') + '/' + len;
    if (fillCache.has(id)) return fillCache.get(id);
    const out = [];
    const walk = (pos, seq) => {
      if (pos === len) { out.push(seq); return; }
      for (const t of tokens) if (fits(t, pos, len)) walk(pos + TOKENS[t].len, seq.concat([t]));
    };
    walk(0, []);
    const ok = out.filter(seq => seq.filter(t => TOKENS[t].rest).length <= 1 && seq.some(t => !TOKENS[t].rest));
    fillCache.set(id, ok);
    return ok;
  }
  // The exercise in phrases of 2 bars (4 from 8 bars up); a single bar left over joins the phrase before.
  function phrases(bars) {
    const P = bars >= 8 ? 4 : 2, out = [];
    for (let b = 0; b < bars; b += P) out.push([b, Math.min(bars, b + P)]);
    if (out.length > 1 && out[out.length - 1][1] - out[out.length - 1][0] === 1) { const last = out.pop(); out[out.length - 1][1] = last[1]; }
    return out;
  }
  function planRhythm(R, time, rng) {
    const len = BAR[time], B = R.bars, ph = phrases(B);
    const ending = ENDINGS[len].find(e => e.every(t => R.rhythms.includes(t)));
    if (!ending) throw new Error('the last bar needs a long note: add ' + ENDINGS[len][0][0] + ' (or a long note and rests) to the rhythms');
    const options = fillings(R.rhythms.filter(t => t !== 'w' || len === 8), len);
    if (!options.length) throw new Error('the rhythms cannot fill a bar of ' + time);
    const isNew = (t) => R.newRhythms.includes(t);
    const weight = (seq, role, before) => {
      let w = 1;
      for (const t of seq) w *= TOKEN_WEIGHT[t] * (isNew(t) ? 3 : 1);
      w = Math.pow(w, 1 / seq.length); // the tokens' average, so busy bars and quiet ones both come up
      if (role === 'first' && TOKENS[seq[0]].rest) return 0; // the music starts with a note
      if (role === 'cadence') { const last = seq[seq.length - 1]; w *= TOKENS[last].len >= 4 ? 3 : TOKENS[last].rest ? 1.5 : 1; } // a breath at the end of a phrase
      if (before && before.join() === seq.join()) w *= 0.5;
      if (seq.length === 1 && seq[0] === 'w' && role !== 'cadence') w *= 0.4;
      return w;
    };
    const bars = [];
    for (let b = 0; b < B; b++) {
      const k = ph.findIndex(([s, e]) => b >= s && b < e), [start, end] = ph[k];
      if (b === B - 1) bars.push(ending);
      else if (k > 0 && b === start) bars.push(bars[ph[0][0]]); // the next phrase answers the first: the same rhythm
      else {
        const role = b === 0 ? 'first' : b === end - 1 ? 'cadence' : 'plain';
        bars.push(pick(options, options.map(o => weight(o, role, bars[b - 1])), rng));
      }
    }
    for (const t of R.newRhythms) if (bars.flat().filter(x => x === t).length < 2) return null;
    return { time, len, bars, events: eventsOf(bars), phrases: ph, slots: len === 8 ? 2 : 1 };
  }
  // The notes and rests of a run of bars, in order.
  function eventsOf(bars) {
    const events = [];
    bars.forEach((seq, b) => {
      let pos = 0;
      for (const t of seq) TOKENS[t].parts.forEach((L, k) => {
        events.push({ bar: b, pos, len: L, rest: !!TOKENS[t].rest, token: t, fast: L === 1,
          beam: t === '8 8' ? (k ? 'end' : 'begin') : null });
        pos += L;
      });
    });
    return events;
  }

  // ---- Chords: one for each bar, or each half bar in 4/4 ----
  function planChords(R, plan, echoing, rng) {
    const S = plan.slots, B = R.bars, total = B * S, ch = new Array(total).fill(null);
    const home = 0, dominant = R.chords.includes(4) ? 4 : R.chords.includes(3) ? 3 : 0;
    for (let s = (B - 1) * S; s < total; s++) ch[s] = home; // the last bar is home
    ch[0] = home;
    if (B > 1) ch[(B - 1) * S - 1] = dominant; // V to I at the end
    for (const [, end] of plan.phrases.slice(0, -1)) ch[end * S - 1] = R.chords.includes(4) ? 4 : home; // the first phrase ends on V
    const echo = new Map(); // the next phrase starts on the first phrase's chords, when it starts with its notes too
    if (echoing) for (const [start] of plan.phrases.slice(1)) for (let k = 0; k < S; k++) echo.set(start * S + k, plan.phrases[0][0] * S + k);
    for (let s = 1; s < total; s++) {
      if (ch[s] !== null) continue;
      const prev = ch[s - 1], next = ch[s + 1];
      if (echo.has(s) && (next === null || next === undefined || MOVE[ch[echo.get(s)]][next] > 0) && MOVE[prev][ch[echo.get(s)]] > 0) { ch[s] = ch[echo.get(s)]; continue; }
      const can = R.chords.filter(c => MOVE[prev][c] > 0 && (next === null || next === undefined || MOVE[c][next] > 0));
      if (!can.length) { ch[s] = home; continue; }
      ch[s] = pick(can, can.map(c => MOVE[prev][c] * (S === 2 && s % 2 && c === prev ? 2.5 : 1)), rng);
    }
    return ch;
  }

  // ---- The notes ----
  const interval = (a, b) => Math.abs(a.dia - b.dia) + 1; // 1 the same note, 2 a step, 3 a third...
  const direction = (a, b) => Math.sign(b.dia - a.dia);
  function planMelody(R, plan, chords, echoing, rng) {
    const ev = plan.events, at = [];
    ev.forEach((e, i) => { if (!e.rest) at.push(i); });
    const N = at.length, slotLen = plan.len / plan.slots;
    const slotOf = (e) => e.bar * plan.slots + Math.floor(e.pos / slotLen);
    const strong = (e) => e.pos % slotLen === 0;
    // The next phrase may also start with the first phrase's notes (up to three of them).
    const echo = new Map();
    if (echoing) {
      const first = at.filter(i => ev[i].bar === plan.phrases[0][0]);
      for (const [start] of plan.phrases.slice(1)) {
        const here = at.filter(i => ev[i].bar === start);
        here.slice(0, Math.min(3, first.length)).forEach((i, k) => echo.set(at.indexOf(i), at.indexOf(first[k])));
      }
    }
    const fresh = R.newNotes, need = () => fresh.reduce((s, n) => s + Math.max(0, 2 - (counts.get(n) || 0)), 0);
    const picks = [], counts = new Map(), pending = [], crossed = [];
    let budget = 2500;
    const tonesAt = (i) => chordTones(chords[slotOf(ev[at[i]])]);
    const nct = (i, c) => !tonesAt(i).includes(c.degree); // not a note of the chord: a passing or neighbour note
    const joined = (i) => i > 0 && !!ev[at[i] - 1] && !ev[at[i] - 1].rest; // no rest between this note and the one before

    function allowed(i, c) {
      const e = ev[at[i]], before = ev[at[i] - 1], p = picks[i - 1], touching = joined(i);
      if (strong(e) && nct(i, c)) return false;
      if (i === N - 1 && c.degree !== 0) return false; // the last note is the home note
      if (p) {
        const iv = interval(p, c), dir = direction(p, c);
        if (iv > R.maxLeap) return false;
        if (pending[i - 1] && dir === pending[i - 1]) return false; // after a leap of a fourth or more, turn back
        // A leap of a fourth or more never follows another leap the same way.
        const pp = picks[i - 2];
        if (pp && iv >= 4 && interval(pp, p) >= 3 && direction(pp, p) === dir) return false;
        if (iv >= 3 && pp && interval(pp, p) >= 4 && direction(pp, p) === dir) return false;
        // A note outside the chord comes straight after another note (no rest), on a weak beat, and moves by step on
        // at least one side: reached by a leap, it steps on; reached by step, it may skip on by a third the other way
        // (B C♯ A at a cadence).
        if (nct(i, c) && !touching) return false;
        if (nct(i - 1, p)) {
          const pp = picks[i - 2], stepIn = joined(i - 1) && interval(pp, p) === 2;
          if (iv !== 2 && (!stepIn || iv > 3 || dir === direction(pp, p) || nct(i, c))) return false;
        }
        if (touching && c.string !== p.string) {
          if (R.crossings !== 'free' && (e.fast || before.fast)) return false; // no crossings on fast notes
          if (R.crossings === 'few' && crossed.some(([k, bar]) => bar === e.bar && k < i)) return false;
        }
      } else if (nct(i, c)) return false;
      if (nct(i, c)) { const after = ev[at[i] + 1]; if (!after || after.rest) return false; } // and a note follows it
      return true;
    }
    function weight(i, c) {
      const e = ev[at[i]], before = ev[at[i] - 1], p = picks[i - 1];
      let w = 1;
      if (p) {
        const iv = interval(p, c);
        w *= [0, 1, 4, 1.6, 0.8, 0.5, 0.4, 0.3, 0.3][Math.min(iv, 8)];
        if (iv === 1) { let run = 1; for (let k = i - 1; k > 0 && picks[k - 1].midi === picks[k].midi; k--) run++; w *= run >= 3 ? 0.1 : run === 2 ? 0.35 : 1; }
        const pp = picks[i - 2];
        if (pp && interval(pp, p) >= 3 && direction(pp, p) === -direction(p, c) && iv === 2) w *= 2.5; // after a skip, step back
        if (e.fast || (before && before.fast)) w *= iv <= 2 ? 1.5 : 0.4;
        if (c.string === p.string) w *= 1.3;
      } else if (c.degree === 0) w *= 2;
      if (fresh.includes(c.name)) w *= (counts.get(c.name) || 0) < 2 ? 2.5 : 1.2;
      if (echo.has(i) && picks[echo.get(i)]) w *= picks[echo.get(i)] === c ? 25 : 1;
      if (i === N - 2 && R.notes.some(f => f.degree === 0 && interval(c, f) === 2)) w *= 2; // lead into the home note by step
      return w;
    }
    function walk(i) {
      if (i === N) return true;
      if (--budget < 0) return false;
      const can = R.notes.filter(c => allowed(i, c));
      for (const c of shuffle(can, can.map(c => weight(i, c)), rng)) {
        const p = picks[i - 1], before = ev[at[i] - 1];
        picks[i] = c;
        counts.set(c.name, (counts.get(c.name) || 0) + 1);
        const dir = p ? direction(p, c) : 0;
        pending[i] = p && interval(p, c) >= 4 ? dir : pending[i - 1] && dir !== -pending[i - 1] ? pending[i - 1] : 0;
        const crossing = p && before && !before.rest && c.string !== p.string;
        if (crossing) crossed.push([i, ev[at[i]].bar]);
        if (need() <= N - 1 - i && walk(i + 1)) return true;
        if (crossing) crossed.pop();
        counts.set(c.name, counts.get(c.name) - 1);
      }
      picks.length = i;
      return false;
    }
    return walk(0) ? picks.slice() : null;
  }

  // ---- MusicXML ----
  const TYPE = { 8: ['whole', false], 6: ['half', true], 4: ['half', false], 3: ['quarter', true], 2: ['quarter', false], 1: ['eighth', false] };
  const ACCIDENTAL = { '-1': 'flat', '0': 'natural', '1': 'sharp' };
  const PART = { violin: { name: 'Violin', abbr: 'Vln.', program: 41, clef: ['G', 2] }, viola: { name: 'Viola', abbr: 'Vla.', program: 42, clef: ['C', 3] } };
  // parts: one or two of { inst, key, plan, notes, label }; the part is named "Violin \u2014 <label>". The tempo mark goes
  // over the first part only.
  const solo = (R, plan, notes) => [{ inst: R.inst, key: R.key, plan, notes, label: 'Sight-reading' }];
  function toXml(parts, tempo) {
    const [beats, beatType] = parts[0].plan.time.split('/'), out = [];
    out.push('<?xml version="1.0" encoding="UTF-8"?>',
      '<score-partwise version="4.0">',
      '  <work><work-title>Sight-reading</work-title></work>',
      '  <part-list>');
    parts.forEach((part, p) => {
      const P = PART[part.inst], id = 'P' + (p + 1);
      out.push(`    <score-part id="${id}">`,
        `      <part-name>${P.name} \u2014 ${part.label}</part-name>`,
        `      <part-abbreviation>${P.abbr}</part-abbreviation>`,
        `      <score-instrument id="${id}-I1"><instrument-name>${P.name}</instrument-name></score-instrument>`,
        `      <midi-instrument id="${id}-I1"><midi-channel>${p + 1}</midi-channel><midi-program>${P.program}</midi-program><volume>80</volume><pan>0</pan></midi-instrument>`,
        '    </score-part>');
    });
    out.push('  </part-list>');
    parts.forEach(({ inst, key, plan, notes }, p) => {
      const P = PART[inst];
      out.push(`  <part id="P${p + 1}">`);
      let k = 0;
      plan.bars.forEach((_, b) => {
        out.push(`    <measure number="${b + 1}">`);
        if (b === 0) {
          out.push('      <attributes>',
            '        <divisions>2</divisions>',
            `        <key><fifths>${key.fifths}</fifths><mode>${key.mode}</mode></key>`,
            `        <time><beats>${beats}</beats><beat-type>${beatType}</beat-type></time>`,
            `        <clef><sign>${P.clef[0]}</sign><line>${P.clef[1]}</line></clef>`,
            '      </attributes>');
          if (!p) out.push(`      <direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>${tempo}</per-minute></metronome></direction-type><sound tempo="${tempo}"/></direction>`);
        }
        const shown = new Map(); // sharps, flats and naturals already written in this bar
        for (const e of plan.events.filter(x => x.bar === b)) {
          const [type, dot] = TYPE[e.len];
          if (e.rest) {
            out.push(`      <note><rest/><duration>${e.len}</duration><voice>1</voice><type>${type}</type>${dot ? '<dot/>' : ''}</note>`);
            continue;
          }
          const n = notes[k++], spot = n.letter + n.octave;
          const now = shown.has(spot) ? shown.get(spot) : keyAlter(key.fifths, n.letter);
          shown.set(spot, n.alter);
          out.push(`      <note color="${n.color}">`,
            `        <pitch><step>${n.letter}</step>${n.alter ? `<alter>${n.alter}</alter>` : ''}<octave>${n.octave}</octave></pitch>`,
            `        <duration>${e.len}</duration>`,
            '        <voice>1</voice>',
            `        <type>${type}</type>${dot ? '<dot/>' : ''}${n.alter !== now ? `<accidental>${ACCIDENTAL[n.alter]}</accidental>` : ''}`,
            `        <notehead color="${n.color}">normal</notehead>${e.beam ? `<beam number="1">${e.beam}</beam>` : ''}`,
            `        <notations><technical><fingering>${n.label}</fingering></technical></notations>`,
            '      </note>');
        }
        if (b === plan.bars.length - 1) out.push('      <barline location="right"><bar-style>light-heavy</bar-style></barline>');
        out.push('    </measure>');
      });
      out.push('  </part>');
    });
    out.push('</score-partwise>', '');
    return out.join('\n');
  }

  // ---- The exercise ----
  const startTempo = (page) => (page.tempo && page.tempo[0]) || 72;
  // Page rules, instrument ("violin" or "viola"), exercise number: the exercise. Throws, saying why, on rules that
  // can't make music.
  function exercise(page, inst, n) {
    const { R, plan, chords, notes, tempo, time } = compose(page, inst, n);
    return {
      xml: toXml(solo(R, plan, notes), tempo), page: page.id, inst, n, tempo, time, bars: R.bars, key: R.key.name,
      chords: chords.map(c => NAMES[c]), rhythm: plan.bars.map(b => b.join(' ')), notes: notes.map(x => x.name),
    };
  }
  // The exercise's makings: its rules, rhythm plan, chords and notes (a duet's Part 2 is built on them).
  function compose(page, inst, n) {
    const R = rulesFor(page, inst);
    const rng = seeded(page.id + '|' + n); // not the instrument: violin and viola get the same exercise
    const time = R.times.length > 1 ? R.times[Math.floor(rng() * R.times.length)] : R.times[0];
    for (let tries = 0; tries < 80; tries++) {
      const plan = planRhythm(R, time, rng);
      if (!plan) continue;
      const echoing = plan.phrases.length > 1 && rng() < 0.5; // the next phrase starts with the first one's notes
      const chords = planChords(R, plan, echoing, rng);
      const notes = planMelody(R, plan, chords, echoing, rng);
      if (!notes) continue;
      return { R, plan, chords, notes, tempo: startTempo(page), time };
    }
    throw new Error('could not make exercise ' + n + ' of ' + page.id + ' for ' + inst + ': the rules may be too tight');
  }

  // ---- Duets (round 5): a second part to play with the exercise ----
  // Part 1 is the exercise with that number, note for note. Part 2 is built on its chords, in its key, under it (over it
  // when a violin plays with a viola's Part 1), as the brief asks: never crossing it and never more than an octave from
  // it; a unison, third, fifth, sixth or octave on every strong beat and wherever the two start a note together; a second,
  // fourth or seventh only on a weak beat, where one part passes by step against the other's chord note; no fifths or
  // octaves in a row with both parts moving; moving against Part 1 more than with it; and often holding while Part 1
  // moves, or moving while it holds. Its own line follows Part 1's rules (chord notes on strong beats, a note outside the
  // chord reached and left by step, a turn back after a leap of a fourth or more) and ends on the home note or its third.
  // Part 2's level (part2):
  //   'same'    the page's notes and rhythms (a viola with a violin's Part 1: the viola's notes for the page, those in the
  //             key, so the same fingers it has learned; the same the other way round)
  //   'open'    open strings, in long notes (a first finger now and then, where a chord has no open string), for a parent
  //             or a younger brother or sister
  //   a page    an earlier book page's notes and rhythms (its rules object), for a student a few pages behind
  //   'harder'  every note in first position in the key, with eighths and dotted rhythms: a part for the teacher
  // The pairs: violin and violin, violin and viola, viola and violin, viola and viola.
  const PART2 = ['same', 'open', 'harder'];
  // Every note a hand reaches in first position in a key, fingers 0 to most: each finger one step of the scale up a
  // string whose open note is in the key (a string whose open note isn't, like the C string in A major, is left out).
  function firstPosition(inst, key, most) {
    const out = [];
    for (const string of Object.keys(OPEN[inst])) {
      if (keyAlter(key.fifths, string)) continue;
      const semis = [0];
      for (let f = 1; f <= 4; f++) {
        const letter = LETTERS[(LETTERS.indexOf(string) + f) % 7];
        semis.push((NATURAL[letter] - NATURAL[string] + 12) % 12 + keyAlter(key.fifths, letter));
      }
      for (let f = 0; f <= most; f++) out.push(makeNote(string + f, inst, { [string]: semis }, key));
    }
    return out;
  }
  // Part 2's rules: its notes (in Part 1's key), rhythms, biggest leap and string crossings.
  function partnerRules(page, R1, inst2, level, earlier) {
    const key = R1.key;
    // A page's notes for this instrument, in the duet's key: the ones its key signature has (in a minor key, not the
    // seventh note, whose sharp depends on the chord).
    const inKey = (list) => list.map(n => ({ ...n, degree: (LETTERS.indexOf(n.letter) - LETTERS.indexOf(key.tonic) + 7) % 7 }))
      .filter(n => n.alter === keyAlter(key.fifths, n.letter) && !(key.mode === 'minor' && n.degree === 6));
    let R;
    if (level === 'open') R = { notes: inKey(firstPosition(inst2, key, 1)), rhythms: ['w', 'h.', 'h', 'q'], maxLeap: 8, crossings: 'free' };
    else if (level === 'harder') {
      R = { notes: inKey(firstPosition(inst2, key, 4)), maxLeap: 6, crossings: 'free',
        rhythms: [...new Set(['w', 'h.', 'h', 'q', '8 8', 'q. 8', 'qr', ...R1.rhythms])] };
    } else {
      const P = level === 'page' ? rulesFor(earlier, inst2) : inst2 === R1.inst ? R1 : rulesFor(page, inst2);
      // A leap of a fourth or fifth between chord notes, as a lower part goes from V to I, even where the page's own
      // tunes move only by step and third.
      R = { notes: P === R1 ? R1.notes : inKey(P.notes), rhythms: P.rhythms, maxLeap: Math.max(5, P.maxLeap), crossings: P.crossings };
    }
    // Too few notes for the chords (a viola's page notes in a violin's key, say): open strings and first fingers too.
    if (R.notes.length < 3 || [0, 3, 4].some(c => R1.chords.includes(c) && !R.notes.some(n => chordTones(c).includes(n.degree)))) R = widen(R, inKey, inst2, key, 1);
    return { ...R, inst: inst2, key, level, inKey };
  }
  // More for Part 2, when its own notes can't make a part with this Part 1: open strings and first fingers (step 1), then
  // every note in first position and quarter and half rests, to rest while Part 1 runs further than an octave (step 4),
  // then a whole bar's rest now and then (step 5: a viola low on its C string, say, that a violin can't stay within an
  // octave of). Marked, so the page can say so.
  function widen(R, inKey, inst2, key, step) {
    if (step === 5) return { ...R, widened: 5 };
    const have = new Set(R.notes.map(n => n.midi));
    const more = inKey(firstPosition(inst2, key, step)).filter(n => !have.has(n.midi));
    const rests = step === 4 ? ['qr', 'hr'].filter(t => !R.rhythms.includes(t)) : [];
    return more.length || rests.length ? { ...R, notes: R.notes.concat(more), rhythms: R.rhythms.concat(rests), widened: step } : R;
  }
  // Part 2's rhythm, bar by bar: its own (the last bar Part 1's ending, a phrase that starts again starting with Part 2's
  // own first bar), chosen so that one part often holds while the other moves; Part 1's own rhythm only now and then.
  const OPEN_WEIGHT = { 'w': 2, 'h.': 1.6, 'h': 3, 'q': 0.6, 'qr': 0.8, 'hr': 0.6, 'h.r': 0.5, 'wr': 0.5 };
  function partnerRhythm(R2, plan1, rng) {
    const len = plan1.len, B = plan1.bars.length, ph = plan1.phrases, last = plan1.bars[B - 1];
    const ending = last.every(t => R2.rhythms.includes(t)) ? last : ENDINGS[len].find(e => e.every(t => R2.rhythms.includes(t)));
    const options = fillings(R2.rhythms.filter(t => t !== 'w' || len === 8), len);
    if (!ending || !options.length) throw new Error('Part 2\u2019s rhythms cannot fill a bar of ' + plan1.time);
    if (R2.widened === 5) options.push([{ 8: 'wr', 6: 'h.r', 4: 'hr' }[len]]); // a bar's rest, as a last resort
    const attacks = (seq) => eventsOf([seq]).filter(e => !e.rest).map(e => e.pos);
    const weight = (seq, b, role, before) => {
      let w = 1;
      for (const t of seq) w *= (R2.level === 'open' ? OPEN_WEIGHT : TOKEN_WEIGHT)[t];
      w = Math.pow(w, 1 / seq.length);
      if (role === 'first' && TOKENS[seq[0]].rest) return 0;
      if (role === 'cadence') { const t = seq[seq.length - 1]; w *= TOKENS[t].len >= 4 ? 3 : TOKENS[t].rest ? 1.5 : 1; }
      if (before && before.join() === seq.join()) w *= 0.6;
      const one = attacks(plan1.bars[b]), two = attacks(seq), both = two.filter(x => one.includes(x)).length;
      w *= 1 + 0.5 * (one.length + two.length - 2 * both); // a note in one part while the other holds
      if (seq.join() === plan1.bars[b].join()) w *= 0.3;
      return w;
    };
    const bars = [];
    for (let b = 0; b < B; b++) {
      const k = ph.findIndex(([s, e]) => b >= s && b < e), [start, end] = ph[k];
      if (b === B - 1) bars.push(ending);
      else if (k > 0 && b === start && R2.widened !== 5) bars.push(bars[ph[0][0]]); // (as a last resort, its own)
      else bars.push(pick(options, options.map(o => weight(o, b, b === 0 ? 'first' : b === end - 1 ? 'cadence' : 'plain', bars[b - 1])), rng));
    }
    return { time: plan1.time, len, bars, events: eventsOf(bars), phrases: ph, slots: plan1.slots };
  }
  const CONSONANT = [0, 3, 4, 7, 8, 9]; // a unison or octave, a third, fifth or sixth (in semitones, within the octave)
  const PASSING = [2, 5, 10]; // a second, fourth or seventh: on a weak beat, one part passing against the other's chord note
  function planPartner(one, R2, plan2, upper, rng) {
    const plan1 = one.plan, chords = one.chords, T = plan1.bars.length * plan1.len, slotLen = plan1.len / plan1.slots;
    // Part 1, eighth by eighth: the note sounding and where it began.
    const p1 = new Array(T).fill(null);
    let k = 0;
    for (const e of plan1.events) {
      const start = e.bar * plan1.len + e.pos, note = e.rest ? null : one.notes[k++];
      for (let t = start; t < start + e.len; t++) p1[t] = note && { note, start };
    }
    const strongAt = (t) => t % slotLen === 0;
    const chordAt = (n, t) => chordTones(chords[Math.floor(t / slotLen)]).includes(n.degree);
    const gap = (a, b) => upper === 1 ? a.midi - b.midi : b.midi - a.midi; // Part 1's note a, Part 2's b: the upper one's height over the lower
    const ev = plan2.events, at = [];
    ev.forEach((e, i) => { if (!e.rest) at.push(i); });
    const N = at.length, startOf = at.map(i => ev[i].bar * plan2.len + ev[i].pos);
    const joined = (i) => i > 0 && !!ev[at[i] - 1] && !ev[at[i] - 1].rest;
    // The moments each Part 2 note sounds against Part 1: its start, and each Part 1 note that starts while it sounds.
    const moments = at.map((ei, i) => {
      const s = startOf[i], out = [];
      for (let t = s; t < s + ev[ei].len; t++) if (p1[t] && (t === s || p1[t].start === t)) out.push(t);
      return out;
    });
    const picks = [], pending = [], passing = [], crossed = [];
    let budget = 3000;
    const sweet = (i, c) => moments[i].length && moments[i][0] === startOf[i] && moments[i].every(t => { const d = gap(p1[t].note, c); return d >= 0 && d <= 12 && CONSONANT.includes(d % 12); });
    // false, or what kind of note c is at i: a chord note, a pedal, a free note (outside the chord, but sweet with Part 1
    // all through, on a weak beat), or a passing or neighbour note (which moves on by step).
    function allowed(i, c) {
      const s = startOf[i], e = ev[at[i]], before = ev[at[i] - 1], p = picks[i - 1], touching = joined(i);
      // It ends on the home note or its third (or, over Part 1, its fifth).
      if (i === N - 1 && c.degree !== 0 && c.degree !== 2 && !(upper === 2 && c.degree === 4)) return false;
      let kind = 'chord';
      if (!chordAt(c, s)) {
        // The home note or the fifth may stay on (a pedal) through another chord: the same note again.
        if (p && touching && p.midi === c.midi && (c.degree === 0 || c.degree === 4) && !passing[i - 1]) kind = 'pedal';
        else if (strongAt(s)) return false;
        else if (sweet(i, c)) kind = 'free';
        else {
          if (!p || !touching || interval(p, c) !== 2) return false; // a passing or neighbour note: reached by step,
          const after = ev[at[i] + 1];
          if (!after || after.rest) return false; // and left by step
          kind = 'passing';
        }
      }
      if (p) {
        const iv = interval(p, c), dir = direction(p, c), pp = picks[i - 2];
        if (iv > R2.maxLeap) return false;
        if (passing[i - 1] && iv !== 2) return false;
        if (pending[i - 1] && dir === pending[i - 1]) return false; // after a leap of a fourth or more, turn back
        if (pp && iv >= 4 && interval(pp, p) >= 3 && direction(pp, p) === dir) return false;
        if (iv >= 3 && pp && interval(pp, p) >= 4 && direction(pp, p) === dir) return false;
        if (touching && c.string !== p.string) {
          if (R2.crossings !== 'free' && (e.fast || before.fast)) return false;
          if (R2.crossings === 'few' && crossed.some(([j, bar]) => bar === e.bar && j < i)) return false;
        }
      }
      for (const t of moments[i]) {
        const q = p1[t].note, d = gap(q, c);
        if (d < 0 || d > 12) return false; // never crossing, never more than an octave apart
        const m = d % 12;
        if (CONSONANT.includes(m)) continue;
        if (strongAt(t) || (t === s && p1[t].start === t) || !PASSING.includes(m)) return false;
        const moved = t === s ? c : q, held = t === s ? q : c;
        if (chordAt(moved, t) || !chordAt(held, t)) return false;
      }
      // No fifths or octaves in a row with both parts moving.
      if (p && touching && p1[s] && p1[s].start === s && p1[s - 1] && c.midi !== p.midi && p1[s].note.midi !== p1[s - 1].note.midi) {
        const was = gap(p1[s - 1].note, p) % 12, now = gap(p1[s].note, c) % 12;
        if (was === now && (now === 0 || now === 7)) return false;
      }
      return kind;
    }
    function weight(i, c) {
      const s = startOf[i], p = picks[i - 1], q = p1[s];
      let w = 1;
      if (p) {
        const iv = interval(p, c);
        w *= [0, 1, 3, 2, 1.2, 1, 0.5, 0.35, 0.4][Math.min(iv, 8)];
        if (iv === 1) { let run = 1; for (let j = i - 1; j > 0 && picks[j - 1].midi === picks[j].midi; j--) run++; w *= run >= 3 ? 0.12 : run === 2 ? 0.45 : 1; }
        const pp = picks[i - 2];
        if (pp && interval(pp, p) >= 3 && direction(pp, p) === -direction(p, c) && iv === 2) w *= 2;
        if (c.string === p.string) w *= 1.2;
        // Against Part 1: moving the other way is best, moving while it holds next, moving the same way least.
        if (q && joined(i) && p1[s - 1] && q.start === s && q.note.midi !== p1[s - 1].note.midi && c.midi !== p.midi) {
          w *= Math.sign(q.note.midi - p1[s - 1].note.midi) === -Math.sign(c.midi - p.midi) ? 2.5 : 0.55;
        } else if (q && q.start !== s && c.midi !== p.midi) w *= 1.4;
      } else if (c.degree === 0) w *= 2;
      if (q) { const d = gap(q.note, c), m = d % 12; w *= [3, 4, 8, 9].includes(m) ? 2 : d === 0 ? 0.35 : m === 0 ? 0.8 : 1; } // thirds and sixths sound fullest
      if (R2.level === 'open' && c.finger) w *= 0.03;
      if (c.finger === 4 && R2.notes.some(x => x.finger === 0 && x.midi === c.midi)) w *= 0.25; // the open string, where it is the same note
      if (i === N - 1) w *= c.degree === 0 ? 3 : c.degree === 2 ? 2 : 0.3; // the home note or its third sounds finished
      return w;
    }
    function walk(i) {
      if (i === N) return true;
      if (--budget < 0) return false;
      const kinds = new Map(), can = R2.notes.filter(c => { const k = allowed(i, c); if (k) kinds.set(c, k); return !!k; });
      for (const c of shuffle(can, can.map(c => weight(i, c)), rng)) {
        const p = picks[i - 1], before = ev[at[i] - 1];
        picks[i] = c;
        const dir = p ? direction(p, c) : 0;
        pending[i] = p && interval(p, c) >= 4 ? dir : pending[i - 1] && dir !== -pending[i - 1] ? pending[i - 1] : 0;
        passing[i] = kinds.get(c) === 'passing';
        const crossing = p && before && !before.rest && c.string !== p.string;
        if (crossing) crossed.push([i, ev[at[i]].bar]);
        if (walk(i + 1)) return true;
        if (crossing) crossed.pop();
      }
      picks.length = i;
      return false;
    }
    return walk(0) ? picks.slice() : null;
  }
  // Page rules, the two instruments, the exercise number and Part 2's level ('same', 'open', 'harder' or an earlier
  // page's rules): the duet, as one score of two parts named "Violin — Part 1" and "Viola — Part 2".
  function duet(page, inst1, inst2, n, part2) {
    if (!OPEN[inst2]) throw new Error('instrument "' + inst2 + '": violin or viola');
    const one = compose(page, inst1, n);
    const earlier = part2 && typeof part2 === 'object' ? part2 : null, level = earlier ? 'page' : PART2.includes(part2) ? part2 : 'same';
    const R2 = partnerRules(page, one.R, inst2, level, earlier);
    // Which part is on top (upper: 1 or 2): the viola under a violin; with two of the same instrument, Part 2 goes where
    // its notes have more room (over a Part 1 that sits low, under one that sits high), else the other side.
    const mid = one.notes.reduce((a, x) => a + x.midi, 0) / one.notes.length;
    const room = (up) => up === 2 ? Math.max(...R2.notes.map(x => x.midi)) - mid : mid - Math.min(...R2.notes.map(x => x.midi));
    const sides = inst1 !== inst2 ? [inst1 === 'viola' ? 2 : 1] : room(2) > room(1) ? [2, 1] : [1, 2];
    const rng = seeded(page.id + '|duet|' + inst1 + '|' + inst2 + '|' + (earlier ? earlier.id : level) + '|' + n);
    let R = R2;
    for (let tries = 0; tries < 200; tries++) {
      if (tries === 40 || tries === 80 || tries === 160) R = widen(R, R2.inKey, inst2, R2.key, tries === 40 ? 1 : tries === 80 ? 4 : 5);
      const upper = sides[Math.floor(tries / 20) % sides.length];
      const plan2 = partnerRhythm(R, one.plan, rng);
      const notes2 = planPartner(one, R, plan2, upper, rng);
      if (!notes2) continue;
      const parts = [{ inst: inst1, key: one.R.key, plan: one.plan, notes: one.notes, label: 'Part 1' },
        { inst: inst2, key: one.R.key, plan: plan2, notes: notes2, label: 'Part 2' }];
      return {
        xml: toXml(parts, one.tempo), page: page.id, inst1, inst2, n, part2: earlier ? earlier.id : level, upper, widened: R.widened || 0,
        tempo: one.tempo, time: one.time, bars: one.R.bars, key: one.R.key.name, chords: one.chords.map(c => NAMES[c]),
        rhythm: [one.plan, plan2].map(pl => pl.bars.map(b => b.join(' '))), notes: [one.notes, notes2].map(l => l.map(x => x.name)),
      };
    }
    throw new Error('could not make a Part 2 for exercise ' + n + ' of ' + page.id + ' (' + inst1 + ' with ' + inst2 + ', ' + (earlier ? earlier.id : level) + ')');
  }
  // ---- Flash a bar (round 3): short patterns the eye takes in at once ----
  // Half a bar to two bars from the page's notes and rhythms, no chord plan: a run of steps up or down, a scale fragment
  // that turns once, mostly steps with one skip (and a step back after it), or a repeated rhythm. Each has one of the
  // page's new notes when it can. noRepeats: never the same note twice in a row (a smooth bow change can sound like one
  // long note, so round 4's listening will want it). Lengths: 'half' (2 beats, shown in 2/4; only in 4/4), 'bar', 'two'.
  const flashLengths = (page) => ((page.time && page.time[0]) || '4/4') === '4/4' ? ['half', 'bar', 'two'] : ['bar', 'two'];
  const SHAPES = ['run', 'turn', 'skip', 'cell'];
  function pattern(page, inst, n, opts = {}) {
    const R = rulesFor(page, inst);
    const length = flashLengths(page).includes(opts.length) ? opts.length : 'bar';
    const rng = seeded(page.id + '|flash|' + length + (opts.noRepeats ? '|norepeat' : '') + '|' + n);
    const pageTime = R.times[0], half = length === 'half';
    const time = half ? '2/4' : pageTime, len = BAR[time], bars = length === 'two' ? 2 : 1;
    const tokens = R.rhythms.filter(t => t !== 'w' && (t !== 'h.' || len === 6));
    const options = fillings(tokens, len).filter(seq => !TOKENS[seq[0]].rest);
    if (!options.length) throw new Error('the rhythms cannot fill a bar of ' + time);
    const least = { half: 2, bar: len >= 6 ? 3 : 2, two: 5 }[length];
    const hasSteps = R.notes.some(a => R.notes.some(b => interval(a, b) === 2));
    for (let tries = 0; tries < 120; tries++) {
      const shape = SHAPES[Math.floor(rng() * SHAPES.length)];
      // The rhythm: a repeated cell for 'cell' (a beat in a half bar, half a bar in 4/4, else a bar), else bar by bar.
      let barSeqs;
      if (shape === 'cell') {
        const cellLen = half || len !== 8 ? (bars === 2 ? len : 2) : 4;
        const cells = fillings(tokens, cellLen).filter(seq => !TOKENS[seq[0]].rest && seq.some(t => !TOKENS[t].rest));
        if (!cells.length) continue;
        const cell = cells[Math.floor(rng() * cells.length)];
        barSeqs = Array.from({ length: bars }, () => Array.from({ length: len / cellLen }, () => cell).flat());
      } else {
        barSeqs = Array.from({ length: bars }, (_, b) => {
          const list = b === 0 ? options : fillings(tokens, len);
          return list[Math.floor(rng() * list.length)];
        });
      }
      const events = [];
      barSeqs.forEach((seq, b) => {
        let pos = 0;
        for (const t of seq) TOKENS[t].parts.forEach((L, k) => {
          events.push({ bar: b, pos, len: L, rest: !!TOKENS[t].rest, token: t, fast: L === 1, beam: t === '8 8' ? (k ? 'end' : 'begin') : null });
          pos += L;
        });
      });
      const at = events.map((e, i) => (e.rest ? -1 : i)).filter(i => i >= 0), N = at.length;
      if (N < least || (shape !== 'cell' && N < 2)) continue;
      if (R.newRhythms.length && !barSeqs.flat().some(t => R.newRhythms.includes(t)) && tries < 60) continue;
      const wantNew = R.newNotes.length && tries < 80;
      // The notes, by the shape.
      const d = rng() < 0.5 ? 1 : -1, pivot = 1 + Math.floor(rng() * Math.max(1, N - 2)), skipAt = 1 + Math.floor(rng() * Math.max(1, N - 1));
      const picks = [], crossed = [];
      let budget = 600;
      const allowed = (i, c) => {
        const p = picks[i - 1];
        if (!p) return true;
        const e = events[at[i]], before = events[at[i] - 1], touching = !!before && !before.rest;
        const iv = interval(p, c), dir = direction(p, c);
        if (iv > R.maxLeap) return false;
        if (opts.noRepeats && iv === 1) return false;
        if (touching && c.string !== p.string) {
          if (R.crossings !== 'free' && (e.fast || before.fast)) return false;
          if (R.crossings === 'few' && crossed.some(([k, bar]) => bar === e.bar && k < i)) return false;
        }
        if (shape === 'run') return iv === 2 && dir === d;
        if (shape === 'turn') return iv === 2 && dir === (i <= pivot ? d : -d);
        if (shape === 'skip') {
          if (i === skipAt) return iv >= 3;
          if (i === skipAt + 1) return iv === 2 && dir === -direction(picks[i - 2], p);
          return iv === 2 || (iv === 1 && !opts.noRepeats && rng() < 0.2);
        }
        return hasSteps ? iv <= 3 : true; // cell: steps, skips and repeats (only leaps with no steps to take, as on open strings)
      };
      const walk = (i) => {
        if (i === N) return !wantNew || picks.some(c => R.newNotes.includes(c.name));
        if (--budget < 0) return false;
        const can = R.notes.filter(c => allowed(i, c));
        const w = can.map(c => (R.newNotes.includes(c.name) ? 2.5 : 1) * (picks[i - 1] && c.string === picks[i - 1].string ? 1.3 : 1));
        for (const c of shuffle(can, w, rng)) {
          const p = picks[i - 1], before = events[at[i] - 1];
          picks[i] = c;
          const crossing = p && before && !before.rest && c.string !== p.string;
          if (crossing) crossed.push([i, events[at[i]].bar]);
          if (walk(i + 1)) return true;
          if (crossing) crossed.pop();
        }
        picks.length = i;
        return false;
      };
      if (!walk(0)) continue;
      const plan = { time, len, bars: barSeqs, events };
      const tempo = startTempo(page), [beats, beatType] = pageTime.split('/').map(Number);
      return {
        xml: toXml(solo(R, plan, picks), tempo), page: page.id, inst, n, shape, length, time, bars, tempo, key: R.key.name,
        notes: picks.map(x => x.name), colors: picks.map(x => x.color), rhythm: barSeqs.map(b => b.join(' ')),
        midis: picks.map(x => x.midi), // what each note sounds, for listening (round 4)
        starts: at.map(i => (events[i].bar * len + events[i].pos) / 2), // when each note starts, in quarter notes
        beats: bars * len / 2, // the pattern's length, in quarter notes
        countIn: beats * 4 / beatType, // one bar of the page's time, in quarter notes
      };
    }
    throw new Error('could not make a ' + length + ' pattern ' + n + ' of ' + page.id + ' for ' + inst);
  }

  // What is wrong with a page's rules, in words ([] when nothing is).
  function problems(page) {
    const out = [];
    for (const inst of ['violin', 'viola']) {
      try { const R = rulesFor(page, inst); planRhythm(R, R.times[0], seeded('check')); } catch (e) { out.push(inst + ': ' + e.message); }
    }
    return out;
  }
  return { exercise, duet, pattern, flashLengths, problems, startTempo, LOOKS, TOKENS, PATTERNS, COLORS, PART2 };
});
