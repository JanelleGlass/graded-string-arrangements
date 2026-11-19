// The app layer: keeps the site on the device so it works without the internet (with sw.js), offers an
// "Install the app" button on the home page, lets iPhones play the music with the ringer switch off, and keeps the
// screen on while music plays or a class plays together (window.gsaKeepAwake).
// Every page loads it in its <head>. It is kept apart from the reader so the reader stays the same
// everywhere it runs (the website, the Claude preview, a future app-store version).
(() => {
  // iPhone and iPad (iOS 17 and later): Safari mutes web audio when the ringer switch is off, unless the
  // page says it plays music. Set before any sound starts. Other browsers don't have this and skip it.
  try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch {}

  // Keep the screen on (Janelle, 2026-11-19: students' screens went dark in group class). The reader asks while
  // music plays, while this device conducts and while it follows the teacher; the home page while it conducts or
  // waits for the teacher's song (app/together.js). window.gsaKeepAwake(why, on): the screen stays on while any
  // "why" is on. Screen Wake Lock: Chrome and Android 84+, Safari 16.4+ (in the home-screen app only from iOS 18.4;
  // older ones skip it and sleep as before). The browser lets go whenever the page is hidden, so it is asked again
  // when the page shows, and on the next tap where a browser wants one first.
  const awake = { why: new Set(), lock: null, asking: false };
  async function holdScreen() {
    if (!('wakeLock' in navigator) || !awake.why.size || awake.lock || awake.asking || document.visibilityState !== 'visible') return;
    awake.asking = true;
    try {
      const lock = await navigator.wakeLock.request('screen');
      if (!awake.why.size) lock.release().catch(() => {}); // no longer wanted by the time it came
      else {
        awake.lock = lock;
        lock.addEventListener('release', () => { if (awake.lock === lock) awake.lock = null; });
      }
    } catch {} finally { awake.asking = false; }
  }
  window.gsaKeepAwake = (why, on) => {
    if (on) awake.why.add(why); else awake.why.delete(why);
    if (awake.why.size) { holdScreen(); return; }
    const lock = awake.lock;
    awake.lock = null;
    if (lock) lock.release().catch(() => {});
  };
  document.addEventListener('visibilitychange', holdScreen);
  addEventListener('pointerdown', holdScreen, true);

  const root = new URL('../', document.currentScript.src); // this file is app/app.js, one folder below the site root
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

  // Offline copy. Not inside an app-store wrapper (Capacitor), which carries its own files.
  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol) && !window.Capacitor) {
    addEventListener('load', () => {
      navigator.serviceWorker.register(new URL('sw.js', root).href, { scope: root.href }).catch(() => {});
    });
    // Once added to the home screen, ask the browser not to clear the saved music when space runs low.
    // (Not in Firefox, which asks the player about it.)
    if (standalone && navigator.storage && navigator.storage.persist && !/Firefox\//.test(navigator.userAgent)) {
      navigator.storage.persist().catch(() => {});
    }
  }

  // Home page: an "Install the app" button, shown only where the browser can install it in one tap
  // (Chrome, Edge, Android). iPhones and iPads have no such button; the tip next to it says how.
  let offer = null;
  const button = () => document.getElementById('install');
  const show = () => { const b = button(); if (b) b.hidden = !offer; };
  addEventListener('beforeinstallprompt', (e) => {
    if (!document.getElementById('install') && document.readyState !== 'loading') return; // not the home page
    e.preventDefault();
    offer = e;
    show();
  });
  addEventListener('appinstalled', () => { offer = null; show(); });
  document.addEventListener('DOMContentLoaded', () => {
    const b = button();
    if (!b) return;
    show();
    b.addEventListener('click', async () => {
      if (!offer) return;
      offer.prompt();
      await offer.userChoice.catch(() => {});
      offer = null;
      show();
    });
  });
})();
