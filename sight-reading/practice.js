// The sight-reading page: choose a book page and an instrument, and read exercise after exercise.
//
// Runs before the reader (tools/build_site.py puts it in the page's <head>): it reads the address
// (/sight-reading/?page=v1-02&n=4821), makes the exercise with the generator (generator.js) and hands it to the reader
// through window.readerScore, the way a song page hands over its score file. New exercise and Violin / Viola change the
// music in place (reader.newScore), so the sounds don't load again; another book page opens as a new address, so Back
// returns to the page before.
(() => {
  const PAGES = window.SIGHT_READING_PAGES || [];
  const SR = window.SightReading;
  const MINE = 'sight-reading'; // this device: its instrument and the last book page opened
  const READER = 'sight-reading-reader'; // the reader's own saved settings for this page
  const load = (k) => { try { return JSON.parse(localStorage.getItem(k) || '{}') || {}; } catch { return {}; } };
  const keep = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const MAX = 9999;
  const number = (v) => { const x = Number(String(v || '').trim()); return Number.isInteger(x) && x >= 1 && x <= MAX ? x : 0; };
  const fresh = (not) => { let x; do { x = 1 + Math.floor(Math.random() * MAX); } while (x === not); return x; };

  const mine = load(MINE);
  const params = new URLSearchParams(location.search);
  const page = PAGES.find(p => p.id === params.get('page')) || PAGES.find(p => p.id === mine.page) || PAGES[0];
  let inst = mine.inst === 'viola' ? 'viola' : 'violin';
  let n = number(params.get('n')) || fresh();
  const address = () => '?page=' + encodeURIComponent(page.id) + '&n=' + n;
  try { history.replaceState(history.state, '', address() + location.hash); } catch {}

  // Another book page than last time: it starts with its own look on the notes and its own tempo (Janelle, 2026-11-12:
  // string colors on, finger numbers and note names off, set by each page). The student can change them from there.
  if (mine.page !== page.id) {
    const r = load(READER), help = page.help || {}, look = SR.LOOKS[help.look] || SR.LOOKS.plain;
    r.colorMode = help.colors === false ? 'off' : 'all';
    r.fingerMode = look.fingerMode;
    if (look.fingers) r.fingers = look.fingers;
    r.letterMode = look.letters; r.lettersBig = look.letters;
    r.tempo = SR.startTempo(page);
    keep(READER, r);
  }
  keep(MINE, { ...mine, page: page.id, inst });

  // The reader reads its written tempo from here (the page's slowest tempo), and asks for the music.
  let made = null;
  const make = () => { made = SR.exercise(page, inst, n); return new TextEncoder().encode(made.xml).buffer; };
  window.sightReading = { page, tempo: SR.startTempo(page) };
  window.readerScore = async () => make();

  const $ = (id) => document.getElementById(id);
  // The details card (the title button) says which page and exercise, the key, time and length; that line under the title
  // also heads a printed copy, so a teacher can bring the same exercise back.
  function facts() {
    if (!made) return;
    $('srSource').textContent = page.title + ' \u00B7 Exercise ' + made.n + (page.placeholder ? ' (a placeholder page)' : '');
    $('srKey').textContent = made.key;
    $('srTime').textContent = made.time;
    $('srLength').textContent = made.bars + ' bars';
  }
  function showInst() {
    for (const [id, which] of [['srViolin', 'violin'], ['srViola', 'viola']]) $(id).setAttribute('aria-pressed', String(inst === which));
  }
  // New music in place (the reader keeps its settings and sounds).
  function swap() {
    if (!window.reader || !window.reader.newScore) return;
    let buf;
    try { buf = make(); } catch (e) { console.error(e); return; }
    window.reader.newScore(buf);
    facts();
  }
  function go(to) {
    n = to;
    $('srNum').value = String(n);
    try { history.replaceState(history.state, '', address() + location.hash); } catch {}
    swap();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const sel = $('srPage');
    for (const p of PAGES) {
      const o = document.createElement('option');
      o.value = p.id;
      o.textContent = p.title + (p.placeholder ? ' (placeholder)' : '');
      sel.append(o);
    }
    sel.value = page.id;
    sel.addEventListener('change', () => { location.assign('?page=' + encodeURIComponent(sel.value) + '&n=' + fresh()); });
    showInst();
    for (const [id, which] of [['srViolin', 'violin'], ['srViola', 'viola']]) {
      $(id).addEventListener('click', () => {
        if (inst === which || !window.reader || !window.reader.newScore) return;
        inst = which; showInst();
        keep(MINE, { ...load(MINE), page: page.id, inst });
        swap();
      });
    }
    const num = $('srNum');
    num.value = String(n);
    const typed = () => { const x = number(num.value); if (x && x !== n) go(x); else num.value = String(n); };
    num.addEventListener('change', typed);
    num.addEventListener('keydown', (e) => { if (e.key === 'Enter') { typed(); num.blur(); } });
    num.addEventListener('focus', () => num.select());
    $('srNew').addEventListener('click', () => go(fresh(n)));
    // Phones turned sideways: the row starts just right of "All songs", which floats at the top left.
    const room = () => {
      const home = $('homeBtn'), bar = $('srBar');
      if (!home || home.hidden || (window.visualViewport && Math.abs(visualViewport.scale - 1) > 0.01)) return;
      document.documentElement.style.setProperty('--sr-home', Math.max(0, Math.ceil(home.getBoundingClientRect().right + 8 - bar.getBoundingClientRect().left)) + 'px');
    };
    room(); addEventListener('resize', room); addEventListener('load', room);
    // New exercise works once the reader has its music on the page.
    const ready = setInterval(() => {
      if (!window.reader || !window.reader.newScore) return;
      clearInterval(ready);
      $('srNew').disabled = false;
      facts();
    }, 150);
  });
})();
