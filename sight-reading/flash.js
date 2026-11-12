// Flash a bar (sight-reading, round 3): a short pattern flashes, hides, and the student plays it from that glance.
//
// One round: the pattern shows (3 seconds to start, once or twice), hides, one bar of clicks counts in, the student plays
// while the beat flashes on the screen (no clicks), the pattern comes back, and the student taps Got it or Not yet.
// It gets harder level by level (3 s, then 2 s, then 1 s; two looks, then one; then longer patterns): three Got its in a
// row move up a level, and − / + choose one. The level, the streak and the best streak stay on the device, per book page.
// A lighter page than the reader (Janelle's brief: Flash a bar wants a much simpler screen), with the same music drawing
// (alphaTab), string colors and fonts. The patterns come from the generator (generator.js, pattern mode).
// Listen (round 4): with it on, the microphone hears the round and each note is marked: right or wrong, early or late,
// with one kind sentence (listen.js works it out in the browser). The sound is kept in memory for that one round only,
// never saved or uploaded. The microphone is asked for on a tap, without the echo, noise and loudness filtering that
// mangle a violin's sound. The first time, a timing check (open A on four clicks) measures how late this device hears
// the student, kept on the device; patterns then never have the same note twice in a row (a smooth bow change can sound
// like one long note).
(() => {
  const PAGES = window.SIGHT_READING_PAGES || [], SR = window.SightReading;
  const $ = (id) => document.getElementById(id);
  const load = (k) => { try { return JSON.parse(localStorage.getItem(k) || '{}') || {}; } catch { return {}; } };
  const keep = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  // The tests run every wait ten times faster (tests/smoke.py sets this).
  const FAST = (() => { try { return localStorage.getItem('gsa-flash-fast') === '1'; } catch { return false; } })();
  const ms = (x) => (FAST ? x / 10 : x);

  const params = new URLSearchParams(location.search);
  const mine = load('sight-reading'); // shared with the sight-reading page: the instrument and the last book page
  const page = PAGES.find(p => p.id === params.get('page')) || PAGES.find(p => p.id === mine.page) || PAGES[0];
  let inst = mine.inst === 'viola' ? 'viola' : 'violin';
  try { history.replaceState(history.state, '', '?page=' + encodeURIComponent(page.id)); } catch {}
  keep('sight-reading', { ...mine, page: page.id, inst });
  const tempo = SR.startTempo(page), colorsOn = !(page.help && page.help.colors === false);

  // The levels: each length, short to long, and at each, 3 s with two looks, then 3 s, 2 s and 1 s with one.
  const LEN_WORD = { half: 'half a bar', bar: 'one bar', two: 'two bars' };
  const LADDER = SR.flashLengths(page).flatMap(length => [[3, 2], [3, 1], [2, 1], [1, 1]].map(([secs, looks]) => ({ length, secs, looks })));
  const STORE = 'sight-reading-flash';
  const saved = load(STORE);
  const mineOf = (k, d) => (saved[k] && Number.isFinite(saved[k][page.id]) ? saved[k][page.id] : d);
  let level = Math.max(0, Math.min(LADDER.length - 1, mineOf('level', 0)));
  let streak = mineOf('streak', 0), best = mineOf('best', 0), run = 0; // run: Got its in a row at this level
  const save = () => {
    const s = load(STORE);
    for (const [k, v] of [['level', level], ['streak', streak], ['best', best]]) s[k] = { ...(s[k] || {}), [page.id]: v };
    keep(STORE, s);
  };

  // ---- The page around the music ----
  $('back').href = '../?page=' + encodeURIComponent(page.id);
  const sel = $('flPage');
  for (const p of PAGES) { const o = document.createElement('option'); o.value = p.id; o.textContent = p.title + (p.placeholder ? ' (placeholder)' : ''); sel.append(o); }
  sel.value = page.id;
  sel.addEventListener('change', () => location.assign('?page=' + encodeURIComponent(sel.value)));
  const showInst = () => { $('flViolin').setAttribute('aria-pressed', String(inst === 'violin')); $('flViola').setAttribute('aria-pressed', String(inst === 'viola')); };
  for (const [id, which] of [['flViolin', 'violin'], ['flViola', 'viola']]) $(id).addEventListener('click', () => {
    if (inst === which || phase !== 'ready') return;
    inst = which; showInst(); keep('sight-reading', { ...load('sight-reading'), page: page.id, inst });
    next();
  });
  showInst();
  function toast(text, t = 2200) { const el = $('toast'); el.textContent = text; el.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { el.hidden = true; }, t); }
  function showStatus() {
    $('streak').textContent = streak; $('best').textContent = best;
    const L = LADDER[level];
    $('level').textContent = 'Level ' + (level + 1) + ' of ' + LADDER.length;
    $('levelSay').textContent = (L.secs === 1 ? '1 second' : L.secs + ' seconds') + ' \u00B7 ' + (L.looks === 2 ? 'two looks' : 'one look') + ' \u00B7 ' + LEN_WORD[L.length];
    $('lvDown').disabled = level === 0 || phase !== 'ready'; $('lvUp').disabled = level === LADDER.length - 1 || phase !== 'ready';
  }
  $('lvDown').addEventListener('click', () => { if (phase === 'ready' && level > 0) { level--; run = 0; save(); next(); } });
  $('lvUp').addEventListener('click', () => { if (phase === 'ready' && level < LADDER.length - 1) { level++; run = 0; save(); next(); } });

  // ---- Listen ----
  const MIC = 'sight-reading-mic'; // on this device: Listen on or off, and the timing check's answer (seconds)
  const micSaved = load(MIC);
  let listen = !!micSaved.listen, offset = Number.isFinite(micSaved.offset) ? micSaved.offset : null;
  let mic = null, rec = null, round = null;
  const saveMic = () => keep(MIC, { ...load(MIC), listen, offset });
  const timingDue = () => listen && offset == null;
  function showListen() {
    $('listen').setAttribute('aria-pressed', String(listen));
    $('listenLbl').textContent = listen ? 'Listening' : 'Listen';
    $('recheck').disabled = !listen || phase !== 'ready';
  }
  // The microphone, from a tap (Listen, or Start with Listen on). Tests hand in their own sound (window.flashMicStub).
  async function openMic() {
    if (window.flashMicStub) return true;
    if (mic) return true;
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      if (audio.state !== 'running') await audio.resume();
      // iPhone and iPad: playing and recording at once (the clicks stay on the speaker).
      try { if (navigator.audioSession) navigator.audioSession.type = 'play-and-record'; } catch {}
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
      const src = audio.createMediaStreamSource(stream), node = audio.createScriptProcessor(4096, 1, 1), sink = audio.createGain();
      sink.gain.value = 0;
      node.onaudioprocess = (e) => {
        if (!rec) return;
        // When this stretch of sound reached the microphone, on the clock the clicks are timed by.
        rec.chunks.push({ t: e.playbackTime - e.inputBuffer.duration, data: new Float32Array(e.inputBuffer.getChannelData(0)) });
      };
      src.connect(node); node.connect(sink); sink.connect(audio.destination);
      mic = { stream, src, node, sink };
      return true;
    } catch (e) {
      console.warn(e);
      return false;
    }
  }
  function closeMic() {
    if (!mic) return;
    try { mic.stream.getTracks().forEach(t => t.stop()); mic.node.disconnect(); mic.src.disconnect(); } catch {}
    mic = null; rec = null;
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch {}
  }
  addEventListener('pagehide', closeMic);
  $('listen').addEventListener('click', async () => {
    if (phase !== 'ready') return;
    if (!listen) {
      if (!(await openMic())) { toast('The microphone is not allowed here. Allow it in the browser to use Listen.', 3200); return; }
      listen = true; saveMic(); showListen();
      toast(offset == null ? 'Listen on. First, a quick timing check.' : 'Listen on: I\u2019ll mark each note.', 2200);
    } else {
      listen = false; saveMic(); closeMic(); showListen();
      toast('Listen off', 1400);
    }
    next();
  });
  $('recheck').addEventListener('click', () => { if (phase === 'ready' && listen) { offset = null; saveMic(); next(); } });
  // The sound of the round, from rec, as one stretch with the time its first sample was heard.
  function takeSound() {
    if (window.flashMicStub) return window.flashMicStub(round);
    const chunks = rec ? rec.chunks : [];
    rec = null;
    if (!chunks.length) return null;
    const n = chunks.reduce((k, c) => k + c.data.length, 0), x = new Float32Array(n);
    let k = 0;
    for (const c of chunks) { x.set(c.data, k); k += c.data.length; }
    return { samples: x, sampleRate: audio.sampleRate, start: chunks[0].t };
  }
  // Marks on the notes after a round: a tick or a cross over each, "early" or "late" under it.
  function clearMarks() { const m = $('score').querySelector('.fl-marks'); if (m) m.remove(); $('heard').hidden = true; }
  function markNotes(res) {
    clearMarks();
    const look = api && api.boundsLookup, sys = look && look.staffSystems;
    if (!sys) return;
    const layer = document.createElement('div'); layer.className = 'fl-marks';
    const beats = [];
    for (const s of sys) for (const mb of s.bars) for (const be of mb.bars[0].beats) if (!be.beat.isRest) beats.push(be);
    const staff = sys[0].bars[0].bars[0].visualBounds, space = staff.h / 4;
    beats.forEach((be, i) => {
      const r = res.results[i];
      if (!r) return;
      const x = be.visualBounds.x + be.visualBounds.w / 2;
      const top = document.createElement('span');
      top.className = 'fl-mark ' + (!r.heard ? 'unheard' : r.right ? 'right' : 'wrong');
      top.textContent = !r.heard ? '?' : r.right ? '\u2713' : '\u2717';
      top.title = !r.heard ? 'Not heard' : r.right ? 'Right note' + (r.inTune ? '' : ' (' + (r.cents > 0 ? 'a little sharp' : 'a little flat') + ')') : 'Not this note';
      Object.assign(top.style, { left: x + 'px', top: (staff.y - space * 3.2) + 'px', fontSize: (space * 1.6) + 'px' });
      layer.append(top);
      if (r.heard && r.timing !== 'on time') {
        const when = document.createElement('span');
        when.className = 'fl-when'; when.textContent = r.timing;
        Object.assign(when.style, { left: x + 'px', top: (staff.y + staff.h + space * 2.6) + 'px', fontSize: (space * 1.05) + 'px' });
        layer.append(when);
      }
    });
    $('score').append(layer);
    $('heard').textContent = res.say; $('heard').hidden = false;
  }

  // ---- The music: alphaTab, drawn once per pattern, scaled to fit the card ----
  let api = null, current = null, drawn = false;
  const toDataUrl = (blob) => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(blob); });
  async function setup() {
    if (typeof alphaTab === 'undefined') { say('The music could not load. Check your connection and reload the page.'); return; }
    let font;
    try { const r = await fetch(window.FLASH_FONT); font = await toDataUrl(new Blob([await r.arrayBuffer()], { type: 'font/woff2' })); }
    catch { say('The music could not load. Reload the page to try again.'); return; }
    const s = new alphaTab.Settings();
    s.core.useWorkers = false; s.core.fontDirectory = null; s.core.enableLazyLoading = false;
    s.core.smuflFontSources = new Map([[alphaTab.FontFileFormat.Woff2, font]]);
    s.core.logLevel = alphaTab.LogLevel.Warning;
    s.display.staveProfile = alphaTab.StaveProfile.Score;
    s.display.layoutMode = alphaTab.LayoutMode.Horizontal;
    s.display.scale = 1.5;
    s.display.padding = [12, 8];
    s.display.resources.barNumberColor = alphaTab.model.Color.fromJson('#FFFFFF00');
    const N = alphaTab.NotationElement;
    for (const el of [N.ScoreTitle, N.ScoreSubTitle, N.ScoreArtist, N.ScoreAlbum, N.ScoreWords, N.ScoreMusic, N.ScoreWordsAndMusic, N.ScoreCopyright, N.EffectTempo, N.TrackNames]) if (el !== undefined) s.notation.elements.set(el, false);
    s.player.playerMode = alphaTab.PlayerMode.Disabled;
    api = new alphaTab.AlphaTabApi($('score'), s);
    api.renderFinished.on(() => { setTimeout(fit, 30); });
    api.postRenderFinished.on(() => { fit(); drawn = true; if (phase === 'ready') { say(roundWord()); setButtons(); } });
    next();
  }
  // The music as large as the card allows (never larger than about twice its drawn size), in the middle.
  function fit() {
    const surf = $('score').querySelector('.at-surface'), box = $('music');
    if (!surf) return;
    // alphaTab signs its drawing "rendered by alphaTab" in a strip of its own (the site credits it in words instead),
    // and its own box can be narrower than the music: measure the music itself.
    for (const c of surf.children) if (/rendered by alphaTab/.test(c.textContent || '')) c.style.display = 'none';
    const kids = [...surf.children].filter(c => c.style.display !== 'none' && c.querySelector('svg'));
    if (!kids.length) return;
    surf.style.overflow = 'visible';
    const w = Math.max(...kids.map(c => c.offsetLeft + c.offsetWidth)), h = Math.max(...kids.map(c => c.offsetTop + c.offsetHeight));
    const bw = box.clientWidth - 16, bh = box.clientHeight - 8;
    if (!w || !h) return;
    const k = Math.min(bw / w, bh / h, 2.2);
    Object.assign($('score').style, { width: w + 'px', height: h + 'px', transform: `translate(${((bw + 16 - w * k) / 2).toFixed(1)}px, ${((bh + 8 - h * k) / 2).toFixed(1)}px) scale(${k.toFixed(3)})` });
  }
  addEventListener('resize', () => setTimeout(fit, 60));
  function draw(pat) {
    // Plain notes, with string colors: no finger numbers (alphaTab would draw the score's own above the notes).
    const xml = pat.xml.replace(/<notations>[\s\S]*?<\/notations>/g, '');
    const score = alphaTab.importer.ScoreLoader.loadScoreFromBytes(new TextEncoder().encode(xml), api.settings);
    score.stylesheet.singleTrackTrackNamePolicy = alphaTab.model.TrackNamePolicy ? alphaTab.model.TrackNamePolicy.Hidden : 0;
    let k = 0;
    for (const bar of score.tracks[0].staves[0].bars) for (const beat of bar.voices[0].beats) {
      if (beat.isRest) continue;
      for (const note of beat.notes) {
        const c = pat.colors[k++];
        if (!colorsOn || !c) continue;
        const st = new alphaTab.model.NoteStyle(), col = alphaTab.model.Color.fromJson(c);
        st.colors.set(alphaTab.model.NoteSubElement.StandardNotationNoteHead, col);
        st.colors.set(alphaTab.model.NoteSubElement.StandardNotationAccidentals, col);
        note.style = st;
      }
    }
    drawn = false;
    // alphaTab skips a box with no width: give it the card's width while it draws (fit then scales the drawing).
    Object.assign($('score').style, { width: Math.max(300, $('music').clientWidth) + 'px', height: '', transform: '' });
    api.renderScore(score, [0]);
  }

  // ---- A round ----
  let phase = 'loading', timers = [], audio = null;
  const later = (fn, t) => timers.push(setTimeout(fn, t));
  function say(text) { $('say').textContent = text; }
  const roundWord = () => timingDue() ? 'Timing check: after four clicks, play open A on each of the next four.'
    : streak ? 'Ready for the next one?' : 'Ready? Tap Start.';
  function setButtons() {
    const ready = phase === 'ready' && drawn, check = phase === 'check';
    $('start').disabled = !ready; $('gotIt').disabled = !check; $('notYet').disabled = !check;
    $('startLbl').textContent = timingDue() ? 'Check' : streak || run ? 'Next' : 'Start';
    $('listen').disabled = phase !== 'ready' && phase !== 'loading';
    showListen();
    sel.disabled = phase !== 'ready' && phase !== 'loading';
    document.body.dataset.phase = phase;
    showStatus();
  }
  function cover(on) { $('card').classList.toggle('covered', on); }
  function next() {
    timers.forEach(clearTimeout); timers = [];
    phase = 'ready'; cover(true); $('beat').hidden = true; $('timer').classList.remove('run'); clearMarks();
    const L = LADDER[level];
    let n = 1 + Math.floor(Math.random() * 9999);
    try { current = SR.pattern(page, inst, n, { length: L.length, noRepeats: listen }); }
    catch (e) { console.error(e); say('This page has no patterns yet.'); return; }
    say('Setting out the music\u2026');
    setButtons();
    if (api) draw(current);
  }
  // The pattern shows for the level's time (a bar across the card runs down), once or twice.
  function timerRun(t) {
    const bar = $('timerBar'), el = $('timer');
    el.classList.remove('run'); bar.style.transitionDuration = '0ms'; bar.style.transform = 'scaleX(1)';
    void bar.offsetWidth;
    el.classList.add('run'); bar.style.transitionDuration = t + 'ms'; bar.style.transform = 'scaleX(0)';
  }
  async function start() {
    if (phase !== 'ready' || !drawn) return;
    // Sound starts from a tap (iPhone).
    try { audio = audio || new (window.AudioContext || window.webkitAudioContext)(); if (audio.state !== 'running') await audio.resume(); } catch { audio = null; }
    if (listen && !(await openMic())) { listen = false; saveMic(); showListen(); toast('The microphone is not allowed here, so Listen is off.', 3000); next(); return; }
    if (timingDue()) { timingCheck(); return; }
    const L = LADDER[level], look = ms(L.secs * 1000), gap = ms(700);
    phase = 'flash'; setButtons();
    let t = 0;
    for (let k = 0; k < L.looks; k++) {
      later(() => { cover(false); timerRun(look); }, t);
      t += look;
      later(() => { cover(true); $('timer').classList.remove('run'); say(k + 1 < L.looks ? 'Once more\u2026' : 'Get ready to play'); }, t);
      t += k + 1 < L.looks ? gap : ms(500);
    }
    later(countIn, t);
  }
  // One bar of clicks (the first one higher), the count big on the card; then the student plays while the beat flashes,
  // with no clicks, for as long as the pattern lasts; then the pattern comes back.
  function click(at, strong) {
    if (!audio) return;
    const o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = strong ? 1600 : 1100;
    g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(0.5, at + 0.002); g.gain.exponentialRampToValueAtTime(0.0001, at + 0.06);
    o.connect(g); g.connect(audio.destination); o.start(at); o.stop(at + 0.08);
  }
  function countIn() {
    phase = 'count'; setButtons();
    const beat = ms(60000 / tempo), clicks = Math.round(current.countIn), playBeats = Math.ceil(current.beats - 1e-6);
    // Each click is heard a moment after it is made: the numbers wait for it (the speaker's own delay too, where told).
    const lag = audio ? ((audio.outputLatency || 0) + (audio.baseLatency || 0)) * 1000 : 0;
    const t0 = audio ? audio.currentTime + 0.12 : 0;
    round = { kind: 'round', t0, beat: beat / 1000, clicks: Array.from({ length: clicks }, (_, i) => t0 + i * beat / 1000),
      T0: t0 + clicks * beat / 1000, pattern: current, offset, inst };
    if (listen) rec = { chunks: [] };
    for (let i = 0; i < clicks; i++) {
      click(t0 + i * beat / 1000, i === 0);
      later(() => flashBeat(i + 1, 'count', i === clicks - 1 ? 'Ready\u2026' : 'Listen\u2026'), 120 + lag + i * beat);
    }
    for (let i = 0; i < playBeats; i++) later(() => { phase = 'play'; flashBeat(i + 1, 'play', 'Play!'); }, 120 + lag + (clicks + i) * beat);
    // Listening: a little longer, for the last note's end (and the microphone's delay).
    later(reveal, 120 + lag + (clicks + playBeats) * beat + (listen ? Math.max(250, beat * 0.5) + (offset || 0) * 1000 : 0));
  }
  function flashBeat(num, kind, text) {
    const b = $('beat'), n = $('beatNum');
    b.hidden = false; b.className = 'fl-beat ' + kind;
    n.textContent = String(num);
    say(text);
    n.animate([{ transform: 'scale(1.35)', opacity: 1 }, { transform: 'scale(1)', opacity: 1 }], { duration: Math.min(260, ms(60000 / tempo) * 0.8), easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'forwards' });
    document.body.dataset.phase = phase;
  }
  function reveal() {
    phase = 'check'; $('beat').hidden = true; cover(false); say('');
    $('card').classList.add('check');
    if (listen) {
      const snd = takeSound();
      try { if (snd) markNotes(hear(snd)); } catch (e) { console.error(e); }
    }
    setButtons();
  }
  // What was played in this round, against the pattern, on the clicks' clock less the timing check's delay.
  function hear(snd) {
    const beatS = round.beat, from = round.T0 - snd.start;
    const played = Listen.notes(Listen.track(snd.samples, snd.sampleRate, inst))
      .map(n => ({ ...n, t0: n.t0 - from - (offset || 0), t1: n.t1 - from - (offset || 0) }))
      .filter(n => n.t1 > -0.45 * beatS);
    const expected = current.midis.map((m, i) => ({ midi: m, t: current.starts[i] * beatS }));
    return Listen.judge(expected, played, beatS);
  }
  // The timing check: four clicks to listen, then four more with open A on each; how late the microphone hears it.
  function timingCheck() {
    phase = 'count'; setButtons(); cover(true);
    const beat = ms(60000 / tempo), lag = audio ? ((audio.outputLatency || 0) + (audio.baseLatency || 0)) * 1000 : 0;
    const t0 = audio ? audio.currentTime + 0.12 : 0, all = Array.from({ length: 8 }, (_, i) => t0 + i * beat / 1000);
    round = { kind: 'timing', t0, beat: beat / 1000, clicks: all, playOn: all.slice(4), inst };
    rec = { chunks: [] };
    all.forEach((at, i) => {
      click(at, i % 4 === 0);
      later(() => { phase = i < 4 ? 'count' : 'play'; flashBeat((i % 4) + 1, i < 4 ? 'count' : 'play', i < 3 ? 'Listen\u2026' : i === 3 ? 'Ready\u2026' : 'Open A!'); }, 120 + lag + i * beat);
    });
    later(() => {
      const snd = takeSound();
      let res = null;
      try { res = snd && Listen.timing(snd.samples, snd.sampleRate, inst, round.playOn.map(c => c - snd.start), round.beat); } catch (e) { console.error(e); }
      if (res && res.offset > -0.1 && res.offset < 0.8) {
        offset = res.offset; saveMic();
        toast('Timing set. Now Flash a bar listens to every round.', 2600);
      } else toast('I couldn\u2019t hear four A\u2019s. Try again, a little louder.', 3000);
      next();
    }, 120 + lag + 8 * beat + Math.max(300, beat * 0.6));
  }
  function answer(got) {
    if (phase !== 'check') return;
    $('card').classList.remove('check');
    clearMarks();
    if (got) {
      streak++; run++;
      if (streak > best) best = streak;
      $('streakBox').animate([{ transform: 'scale(1.18)' }, { transform: 'scale(1)' }], { duration: 380, easing: 'cubic-bezier(.2,.7,.3,1)' });
      if (run >= 3 && level < LADDER.length - 1) {
        level++; run = 0;
        const L = LADDER[level];
        toast('Level up! Level ' + (level + 1) + ': ' + (L.secs === 1 ? '1 second' : L.secs + ' seconds') + ', ' + (L.looks === 2 ? 'two looks' : 'one look') + ', ' + LEN_WORD[L.length]);
      } else toast(streak > 1 ? streak + ' in a row!' : 'Got it!', 1400);
    } else {
      streak = 0; run = 0;
      toast('Keep going: the next one is new.', 1600);
    }
    save();
    next();
  }
  $('start').addEventListener('click', start);
  $('gotIt').addEventListener('click', () => answer(true));
  $('notYet').addEventListener('click', () => answer(false));
  // For the tests: where a round is.
  window.flash = { state: () => ({ phase, level, streak, best, run, drawn, listen, offset, covered: $('card').classList.contains('covered'),
    heard: $('heard').hidden ? null : $('heard').textContent, marks: [...$('score').querySelectorAll('.fl-mark, .fl-when')].map(m => m.className.replace('fl-', '') + ':' + m.textContent),
    pattern: current && { notes: current.notes, midis: current.midis, starts: current.starts, length: current.length, shape: current.shape, beats: current.beats } }) };
  showStatus();
  setup();
})();
