// The sight-reading page: choose a book page and an instrument, and read exercise after exercise, alone or as a duet.
//
// Runs before the reader (tools/build_site.py puts it in the page's <head>): it reads the address
// (/sight-reading/?page=v1-02&n=4821), makes the exercise with the generator (generator.js) and hands it to the reader
// through window.readerScore, the way a song page hands over its score file. New exercise, Violin / Viola and the Duet
// choices change the music in place (reader.newScore), so the sounds don't load again; another book page opens as a new
// address, so Back returns to the page before.
//
// A duet (round 5): the address also says the two instruments and Part 2's level (&duet=violin-viola&part2=same), so
// another device opening it, or opening the same page and number with the same choices, gets the same music. Which part
// this device plays (for Look ahead, which hides only that part) is kept on the device.
(() => {
  const PAGES = window.SIGHT_READING_PAGES || [];
  const SR = window.SightReading;
  const MINE = 'sight-reading'; // this device: its instrument, the last book page opened, its duet choices and part
  const READER = 'sight-reading-reader'; // the reader's own saved settings for this page
  const load = (k) => { try { return JSON.parse(localStorage.getItem(k) || '{}') || {}; } catch { return {}; } };
  const keep = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };
  const MAX = 9999;
  const number = (v) => { const x = Number(String(v || '').trim()); return Number.isInteger(x) && x >= 1 && x <= MAX ? x : 0; };
  const fresh = (not) => { let x; do { x = 1 + Math.floor(Math.random() * MAX); } while (x === not); return x; };
  const INSTS = ['violin', 'viola'];

  const mine = load(MINE);
  const params = new URLSearchParams(location.search);
  const page = PAGES.find(p => p.id === params.get('page')) || PAGES.find(p => p.id === mine.page) || PAGES[0];
  let inst = mine.inst === 'viola' ? 'viola' : 'violin';
  let n = number(params.get('n')) || fresh();
  // The duet: its two instruments (null when playing alone) and Part 2's level: 'same', 'open', 'harder' or an earlier
  // book page's id. The book pages before this one, for that list.
  const before = (p) => PAGES.slice(0, Math.max(0, PAGES.indexOf(p)));
  const levelFor = (v, p) => SR.PART2.includes(v) || before(p).some(x => x.id === v) ? v : 'same';
  const pairOf = (v) => { const m = /^(violin|viola)-(violin|viola)$/.exec(v || ''); return m ? [m[1], m[2]] : null; };
  let duet = pairOf(params.get('duet'));
  let part2 = levelFor(params.get('part2') || (mine.duet && mine.duet.part2), page);
  let myPart = mine.part === 2 ? 2 : 1;
  const duetQuery = (p) => duet ? '&duet=' + duet.join('-') + '&part2=' + encodeURIComponent(levelFor(part2, p)) : '';
  const address = () => '?page=' + encodeURIComponent(page.id) + '&n=' + n + duetQuery(page);
  const putAddress = () => { try { history.replaceState(history.state, '', address() + location.hash); } catch {} };
  putAddress();

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
  const remember = () => keep(MINE, { ...load(MINE), page: page.id, inst, part: myPart, duet: duet ? { pair: duet.join('-'), part2 } : (load(MINE).duet || null) });
  remember();

  // The reader reads its written tempo from here (the page's slowest tempo), and asks for the music. own: the part
  // (0 or 1) Look ahead hides in a duet.
  // A duet that can't be made (rare: the generator tries its rules, then more notes, rests, then a bar's rest) comes as
  // the exercise alone, and says so.
  let made = null, notice = '';
  const make = () => {
    if (duet) {
      try { made = SR.duet(page, duet[0], duet[1], n, SR.PART2.includes(part2) ? part2 : PAGES.find(p => p.id === part2)); }
      catch (e) {
        console.error(e);
        notice = 'Exercise ' + n + ' could not be made as a duet, so here it is alone. Try another number.';
        inst = duet[0]; duet = null; putAddress(); remember();
      }
    }
    if (!duet) made = SR.exercise(page, inst, n);
    window.sightReading.own = duet ? myPart - 1 : undefined;
    return new TextEncoder().encode(made.xml).buffer;
  };
  window.sightReading = { page, tempo: SR.startTempo(page) };
  window.readerScore = async () => make();

  const $ = (id) => document.getElementById(id);
  const toast = (text) => {
    const el = $('toast');
    if (!el) return;
    el.textContent = text; el.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => { el.hidden = true; }, 2600);
  };
  // In words: "two violins", "violin and viola"; Part 2's level.
  const pairWords = (d) => d[0] === d[1] ? 'two ' + d[0] + 's' : d[0] + ' and ' + d[1];
  const levelWords = (v) => v === 'same' ? 'on this page' : v === 'open' ? 'on open strings' : v === 'harder' ? 'harder' : 'on ' + ((PAGES.find(p => p.id === v) || {}).title || v).replace(/:.*/, '');
  // The details card (the title button) says which page and exercise, the key, time and length; that line under the title
  // also heads a printed copy, so a teacher can bring the same exercise back.
  function facts() {
    if (!made) return;
    if (notice) { show(); toast(notice); notice = ''; }
    $('srSource').textContent = page.title + ' · Exercise ' + made.n
      + (made.inst1 ? ' · Duet for ' + pairWords([made.inst1, made.inst2]) + ', Part 2 ' + levelWords(made.part2)
        + (made.widened === 1 ? ' (with a few open strings and first fingers)' : made.widened ? ' (with a few notes and rests from beyond the page)' : '') : '')
      + (page.placeholder ? ' (a placeholder page)' : '');
    $('srKey').textContent = made.key;
    $('srTime').textContent = made.time;
    $('srLength').textContent = made.bars + ' bars';
  }
  function show() {
    for (const [id, which] of [['srViolin', 'violin'], ['srViola', 'viola']]) $(id).setAttribute('aria-pressed', String(!duet && inst === which));
    $('srInst').classList.toggle('off', !!duet); // a duet: each part has its own instrument, in the Duet card
    $('srDuet').setAttribute('aria-pressed', String(!!duet));
    $('srSolo').setAttribute('aria-pressed', String(!duet));
    $('srDuetOn').setAttribute('aria-pressed', String(!!duet));
    const d = duet || [inst, inst];
    for (const k of [0, 1]) for (const w of INSTS) $('srP' + (k + 1) + w).setAttribute('aria-pressed', String(d[k] === w));
    $('srLevel').value = levelFor(part2, page);
    for (const k of [1, 2]) $('srMine' + k).setAttribute('aria-pressed', String(myPart === k));
    const rows = $('srDuetRows');
    rows.classList.toggle('off', !duet);
    for (const el of rows.querySelectorAll('button, select')) el.disabled = !duet;
    $('srCopy').textContent = duet ? 'Copy the link' : 'Copy the link to this exercise';
  }
  // New music in place (the reader keeps its settings and sounds).
  function swap() {
    if (!window.reader || !window.reader.newScore) return;
    let buf;
    try { buf = make(); } catch (e) { console.error(e); toast('This exercise could not be made. Try another number.'); return; }
    window.reader.newScore(buf);
    facts();
  }
  function go(to) {
    n = to;
    $('srNum').value = String(n);
    putAddress();
    swap();
  }
  // A duet choice changed: new music, the address and this device's choices follow.
  function changed() {
    putAddress(); remember(); show(); swap();
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
    sel.addEventListener('change', () => {
      const to = PAGES.find(p => p.id === sel.value) || page;
      location.assign('?page=' + encodeURIComponent(to.id) + '&n=' + fresh() + duetQuery(to));
    });
    $('srFlash').href = 'flash/?page=' + encodeURIComponent(page.id); // Flash a bar, on the same book page
    // Part 2 on an earlier book page: one choice for each page before this one.
    const lv = $('srLevel'), harder = lv.querySelector('option[value="harder"]');
    for (const p of before(page)) {
      const o = document.createElement('option');
      o.value = p.id; o.textContent = 'On ' + p.title.replace(/:/, ' (') + ')';
      lv.insertBefore(o, harder);
    }
    show();
    for (const [id, which] of [['srViolin', 'violin'], ['srViola', 'viola']]) {
      $(id).addEventListener('click', () => {
        if (duet) { openPop(true); toast('In a duet, each part has its own instrument: choose them here'); return; }
        if (inst === which || !window.reader || !window.reader.newScore) return;
        inst = which; remember(); show();
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

    // The Duet card: opens under its button, closes with ×, Escape or a tap outside it.
    const pop = $('srDuetPop'), btn = $('srDuet');
    function openPop(open) {
      pop.hidden = !open; btn.setAttribute('aria-expanded', String(open));
      if (!open) return;
      const bar = $('srBar').getBoundingClientRect(), b = btn.getBoundingClientRect(), w = pop.offsetWidth;
      pop.style.left = Math.max(8 - bar.left, Math.min(b.left - bar.left, innerWidth - 8 - w - bar.left)) + 'px';
    }
    btn.addEventListener('click', () => openPop(pop.hidden));
    $('srDuetX').addEventListener('click', () => { openPop(false); btn.focus(); });
    document.addEventListener('pointerdown', (e) => { if (!pop.hidden && !pop.contains(e.target) && !btn.contains(e.target) && !$('srInst').contains(e.target)) openPop(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !pop.hidden) { openPop(false); btn.focus(); } });
    addEventListener('resize', () => { if (!pop.hidden) openPop(true); });
    const ready = () => window.reader && window.reader.newScore;
    $('srSolo').addEventListener('click', () => { if (!duet || !ready()) return; duet = null; changed(); });
    $('srDuetOn').addEventListener('click', () => {
      if (duet || !ready()) return;
      const was = load(MINE).duet;
      duet = (was && pairOf(was.pair)) || [inst, inst];
      part2 = levelFor(was && was.part2, page);
      changed();
    });
    for (const k of [0, 1]) for (const w of INSTS) {
      $('srP' + (k + 1) + w).addEventListener('click', () => {
        if (!duet || duet[k] === w || !ready()) return;
        duet = k ? [duet[0], w] : [w, duet[1]];
        changed();
      });
    }
    lv.addEventListener('change', () => { if (!duet || !ready()) return; part2 = levelFor(lv.value, page); changed(); });
    for (const k of [1, 2]) {
      $('srMine' + k).addEventListener('click', () => {
        if (!duet || myPart === k) return;
        myPart = k; remember(); show();
        window.sightReading.own = myPart - 1;
        // This part on the page now (the other one keeps playing); Look ahead hides it.
        if (window.reader && window.reader.parts) window.reader.parts({ seen: [myPart - 1], heard: [0, 1], hearOpen: true });
      });
    }
    // The link to this exercise (and duet), to open on another device.
    $('srCopy').addEventListener('click', async () => {
      const link = location.origin + location.pathname + address();
      try { await navigator.clipboard.writeText(link); toast('Link copied: open it on the other device'); }
      catch { window.prompt('Copy this link:', link); }
    });

    // Phones turned sideways: the row starts just right of "All songs", which floats at the top left.
    const room = () => {
      const home = $('homeBtn'), bar = $('srBar');
      if (!home || home.hidden || (window.visualViewport && Math.abs(visualViewport.scale - 1) > 0.01)) return;
      document.documentElement.style.setProperty('--sr-home', Math.max(0, Math.ceil(home.getBoundingClientRect().right + 8 - bar.getBoundingClientRect().left)) + 'px');
    };
    room(); addEventListener('resize', room); addEventListener('load', room);
    // New exercise works once the reader has its music on the page.
    const wait = setInterval(() => {
      if (!ready()) return;
      clearInterval(wait);
      $('srNew').disabled = false;
      facts();
    }, 150);
  });
})();
