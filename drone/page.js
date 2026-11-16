// The Drone page (/drone/): twelve keys round the circle of fifths, each with its relative minor, a big Start / Stop,
// Previous and Next (also the arrow keys and Page Up / Page Down, so a Bluetooth page-turn pedal steps through the keys,
// and the space bar starts and stops), and the drone's settings, all visible, each a tap-to-change button like the
// reader's strip. A setting that doesn't apply is greyed out in its place, and a tap says why. The sound is drone.js.
// Settings stay on the device (localStorage 'drone'); whether it is playing doesn't. The screen is kept awake while it
// plays (Screen Wake Lock, where the browser has it), since a phone that locks may stop the sound.
(() => {
  const D = window.Drone;
  const $ = (id) => document.getElementById(id);
  const load = () => { try { return JSON.parse(localStorage.getItem('drone') || '{}') || {}; } catch { return {}; } };
  const keep = (s) => { try { localStorage.setItem('drone', JSON.stringify(s)); } catch {} };

  const drone = D.createDrone();
  drone.set(load());

  function toast(text, t = 2200) {
    const el = $('toast');
    el.textContent = text;
    el.hidden = false;
    clearTimeout(toast.t);
    toast.t = setTimeout(() => { el.hidden = true; }, t);
  }

  // ---- Keeping the screen awake while it plays ----
  let lock = null;
  async function wake(on) {
    try {
      if (on && !lock && navigator.wakeLock && document.visibilityState === 'visible') {
        lock = await navigator.wakeLock.request('screen');
        lock.addEventListener('release', () => { lock = null; });
      } else if (!on && lock) {
        const l = lock;
        lock = null;
        await l.release();
      }
    } catch { lock = null; }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && drone.state().playing) wake(true);
  });

  // ---- Start / Stop, the keys, Previous and Next ----
  function start() { drone.start(); wake(true); }
  function stop() { drone.stop(); wake(false); }
  const toggle = () => (drone.state().playing ? stop() : start());
  $('start').addEventListener('click', toggle);

  function choose(id, play) {
    drone.set({ key: id });
    if (play && !drone.state().playing) start();
  }
  const stepKey = (by) => choose(D.step(drone.state().key, by).id, false);
  $('prev').addEventListener('click', () => stepKey(-1));
  $('next').addEventListener('click', () => stepKey(1));

  // The keys: one column for each place round the circle, the major over its relative minor.
  const keyButtons = [];
  for (let i = 0; i < D.CIRCLE.length; i += 2) {
    const pair = document.createElement('div');
    pair.className = 'dr-pair';
    for (const k of [D.CIRCLE[i], D.CIRCLE[i + 1]]) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'dr-key ' + k.mode;
      b.dataset.key = k.id;
      b.setAttribute('aria-pressed', 'false');
      b.setAttribute('aria-label', k.name + (k.also ? ` (${k.also} ${k.mode})` : ''));
      b.innerHTML = `<b>${k.label}</b><small>${k.mode}</small>` + (k.also ? `<i aria-hidden="true">${k.also}</i>` : '');
      b.addEventListener('click', () => choose(k.id, true));
      pair.append(b);
      keyButtons.push(b);
    }
    $('keys').append(pair);
  }

  // ---- The settings: each a button that steps through its choices ----
  const SAY = {
    notes: { tonic: 'Tonic: the home note alone', fifth: 'Tonic + 5th', triad: 'Triad: the key’s chord' },
    voicing: { open: 'Open: root, 5th, and the 3rd an octave up', close: 'Close: root, 3rd and 5th together' },
    tuning: { pure: 'Pure: the 5th and 3rd tuned pure over the root', piano: 'Piano: every note equal-tempered' },
    octave: { low: 'Low octave (best on a speaker: a phone can’t play that low)', middle: 'Middle octave', high: 'High octave' },
    sound: { bowed: 'Sound: Bowed', organ: 'Sound: Organ', soft: 'Sound: Soft' },
  };
  // A setting that does nothing with the notes chosen is greyed out in its place; a tap says why.
  function why(k, s) {
    if (k === 'tuning' && s.notes === 'tonic') return 'With one note, Pure and Piano sound the same';
    if (k === 'voicing' && s.notes !== 'triad') return 'Voicing is for the triad (Notes: Triad)';
    return '';
  }
  const opts = [...document.querySelectorAll('.dr-opt[data-set]')];
  for (const b of opts) {
    const k = b.dataset.set;
    // Every choice is in the button, only the current one showing, so the button keeps the width of its longest.
    b.querySelector('.dr-swap').innerHTML = D.CHOICES[k].map(([v, label]) => `<span data-v="${v}">${label}</span>`).join('');
    b.addEventListener('click', () => {
      const s = drone.settings();
      const no = why(k, s);
      if (no) { toast(no); return; }
      const list = D.CHOICES[k];
      const v = list[(list.findIndex(([x]) => x === s[k]) + 1) % list.length][0];
      drone.set({ [k]: v });
      toast(SAY[k][v]);
    });
  }
  function moveA(by) {
    const a = drone.settings().a + by;
    if (a < D.A_MIN || a > D.A_MAX) { toast(by < 0 ? `A = ${D.A_MIN} is the lowest` : `A = ${D.A_MAX} is the highest`); return; }
    drone.set({ a });
    toast(`A = ${a}`, 1200);
  }
  $('aDown').addEventListener('click', () => moveA(-1));
  $('aUp').addEventListener('click', () => moveA(1));
  const vol = $('vol');
  vol.addEventListener('input', () => drone.set({ volume: Number(vol.value) / 100 }));
  // Let go of the slider once it is set, so a pedal's arrow keys go back to changing the key.
  vol.addEventListener('change', () => vol.blur());

  // ---- A pedal or a keyboard ----
  const typing = (el) => !!el && (el.isContentEditable || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT'
    || (el.tagName === 'INPUT' && !['range', 'button', 'checkbox', 'radio'].includes(el.type)));
  const NEXT = ['ArrowRight', 'ArrowDown', 'PageDown'], PREV = ['ArrowLeft', 'ArrowUp', 'PageUp'];
  addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || typing(document.activeElement)) return;
    const space = e.key === ' ' || e.key === 'Spacebar';
    if (!space && !NEXT.includes(e.key) && !PREV.includes(e.key)) return;
    e.preventDefault(); // no scrolling, no slider moving, no button pressed by the space bar as well
    if (e.repeat) return; // a pedal held down steps once
    if (space) toggle();
    else stepKey(NEXT.includes(e.key) ? 1 : -1);
  }, true);
  addEventListener('keyup', (e) => {
    if ((e.key === ' ' || e.key === 'Spacebar') && !typing(document.activeElement)) e.preventDefault();
  }, true);

  // ---- Showing it ----
  function render() {
    const st = drone.state(), s = st.settings, k = D.keyById(st.key);
    $('keyName').textContent = k.name;
    $('keyAlso').textContent = k.also ? `${k.also} ${k.mode}` : '';
    $('keyNotes').textContent = st.notes.map((n) => n.name).join(' · ');
    $('start').setAttribute('aria-pressed', String(st.playing));
    $('start').classList.toggle('on', st.playing);
    for (const b of keyButtons) {
      const here = b.dataset.key === st.key;
      b.setAttribute('aria-pressed', String(here && st.playing));
      b.classList.toggle('sel', here);
    }
    for (const b of opts) {
      const key = b.dataset.set;
      for (const sp of b.querySelectorAll('.dr-swap span')) sp.classList.toggle('on', sp.dataset.v === s[key]);
      const no = why(key, s);
      b.classList.toggle('off', !!no);
      b.setAttribute('aria-disabled', String(!!no));
      b.title = no;
    }
    $('aVal').textContent = s.a;
    $('aDown').setAttribute('aria-disabled', String(s.a <= D.A_MIN));
    $('aUp').setAttribute('aria-disabled', String(s.a >= D.A_MAX));
    if (document.activeElement !== vol) vol.value = Math.round(s.volume * 100);
  }
  drone.onchange((what) => {
    if (what === 'set') keep(drone.settings());
    if (what === 'interrupted') { wake(false); toast('The sound was stopped. Tap Start to play again.', 3000); }
    render();
  });
  render();

  // For the tests (tests/smoke.py).
  window.drone = { state: () => ({ ...drone.state(), wake: !!lock }), drone };
})();
