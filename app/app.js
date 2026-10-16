// The app layer: keeps the site on the device so it works without the internet (with sw.js), offers an
// "Install the app" button on the home page, and lets iPhones play the music with the ringer switch off.
// Every page loads it in its <head>. It is kept apart from the reader so the reader stays the same
// everywhere it runs (the website, the Claude preview, a future app-store version).
(() => {
  // iPhone and iPad (iOS 17 and later): Safari mutes web audio when the ringer switch is off, unless the
  // page says it plays music. Set before any sound starts. Other browsers don't have this and skip it.
  try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch {}

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
