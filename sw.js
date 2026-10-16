// Offline copy of the site. Keeps the home page, every song (page and score), the music font, the string
// sounds and the music reader (alphaTab) on the device, so everything works without the internet after
// one visit, in the browser or as an app on the home screen.
//
// Written by tools/build_site.py from tools/sw_template.js. Do not edit by hand.
const VERSION = '476a8be6b0';
// Every file kept offline, with a fingerprint of its contents. When a fingerprint changes (a new song, a
// fixed note, a reader change) only that file is fetched again; the rest stay, so adding a song doesn't
// make every student download the 4 MB of string sounds again.
const FILES = {"./": "fff572708d", "app/app.js": "3a19f0d83d", "assets/apple-touch-icon.png": "77db2738c9", "assets/font/Bravura.woff2?v=181e0e7c48": "181e0e7c48", "assets/icon-192.png": "f5d3d0f1da", "assets/icon-512.png": "4c288bcc63", "assets/icon-maskable-512.png": "9e90ad9613", "assets/icon.svg": "071a925436", "assets/soundfont/strings-generaluser-sf2.b64.txt?v=bcdca70e5f": "bcdca70e5f", "https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/alphaTab.min.js": "1.8.4", "manifest.webmanifest": "c2642a3839", "songs/the-first-noel/": "b9e244b55b", "songs/the-first-noel/the-first-noel.xml?v=0c94bf8fea": "0c94bf8fea", "songs/what-child-is-this-epic/": "3bfc36d6d5", "songs/what-child-is-this-epic/what-child-is-this-epic.xml?v=cd68be468c": "cd68be468c"};
// The page lettering from Google Fonts. Kept as well (Latin letters only), but the site still works
// without it: the pages fall back to the device's own fonts.
const FONT_CSS = ["https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,500;0,600;1,500&family=Figtree:wght@400;500;600;700&display=swap"];

const CACHE = 'gsa-files';
const FONTS = 'gsa-fonts';
const PAGE_WAIT_MS = 3500; // how long a page waits for the network before using the saved copy

const root = new URL('./', self.location).href;
const want = new Map(Object.entries(FILES).map(([u, rev]) => [new URL(u, root).href, rev]));
const keyFor = (url, rev) => url + (url.includes('?') ? '&' : '?') + '__rev=' + rev;

async function inTurn(items, lanes, fn) {
  const queue = [...items];
  await Promise.all(Array.from({ length: lanes }, async () => { while (queue.length) await fn(queue.shift()); }));
}

// A stored page must not remember the redirect it came through, or the browser refuses to show it.
const plain = (res) => (res.redirected ? new Response(res.body, { status: res.status, statusText: res.statusText, headers: res.headers }) : res);

async function saveFonts() {
  const cache = await caches.open(FONTS);
  for (const href of FONT_CSS) {
    const res = await fetch(href, { mode: 'cors', credentials: 'omit' });
    if (!res.ok) continue;
    const css = await res.clone().text();
    await cache.put(href, res);
    const urls = [];
    for (const block of css.split('/*').slice(1)) {
      const [name, rules = ''] = block.split('*/');
      if (name.trim() === 'latin') for (const m of rules.matchAll(/url\((https:[^)]+)\)/g)) urls.push(m[1]);
    }
    await inTurn(urls, 4, async (u) => {
      if (await cache.match(u)) return;
      const r = await fetch(u, { mode: 'cors', credentials: 'omit' });
      if (r.ok) await cache.put(u, r);
    });
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const have = new Set((await cache.keys()).map((r) => r.url));
    // Anything missing fails the install, and the browser tries again on the next visit (keeping what it got).
    // 'no-cache': always check with the server, so a changed file is never taken from an old browser copy.
    await inTurn([...want].filter(([u, rev]) => !have.has(keyFor(u, rev))), 4, async ([u, rev]) => {
      const res = await fetch(u, { mode: 'cors', credentials: 'same-origin', cache: 'no-cache' });
      if (!res.ok) throw new Error(`${u}: ${res.status}`);
      await cache.put(keyFor(u, rev), plain(res));
    });
    await saveFonts().catch(() => {});
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = new Set([...want].map(([u, rev]) => keyFor(u, rev)));
    const cache = await caches.open(CACHE);
    for (const req of await cache.keys()) if (!keep.has(req.url)) await cache.delete(req);
    for (const name of await caches.keys()) if (name.startsWith('gsa-') && name !== CACHE && name !== FONTS) await caches.delete(name);
    await self.clients.claim();
  })());
});

const saved = (u) => (want.has(u) ? caches.match(keyFor(u, want.get(u)), { cacheName: CACHE }) : Promise.resolve(undefined));

// Pages: fresh from the network when it answers quickly (so a new song shows up straight away), the saved
// copy when offline or the connection is poor. A page that was never saved falls back to the home page.
async function page(req, u) {
  const net = fetch(req);
  try {
    const res = await Promise.race([net, new Promise((r) => setTimeout(r, PAGE_WAIT_MS))]);
    if (res && (res.ok || !want.has(u))) return res;
  } catch {}
  const hit = await saved(u);
  if (hit) return hit;
  try { return await net; } catch {}
  return (await saved(root)) || Response.error();
}

// Everything else on the list (scores, sounds, font, reader): the saved copy, or the network if it is missing.
async function file(req, u) {
  const hit = await saved(u);
  if (hit) return hit;
  return fetch(req);
}

async function font(req) {
  const cache = await caches.open(FONTS);
  const hit = await cache.match(req.url);
  if (hit) return hit;
  try {
    const res = await fetch(req.url, { mode: 'cors', credentials: 'omit' });
    if (res.ok) await cache.put(req.url, res.clone());
    return res;
  } catch { return Response.error(); }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate' && url.origin === self.location.origin) {
    url.search = ''; url.hash = '';
    let u = url.href.replace(/\/index\.html$/, '/');
    if (!want.has(u) && want.has(u + '/')) u += '/'; // songs/holy-holy-holy -> songs/holy-holy-holy/
    return event.respondWith(page(req, u));
  }
  if (want.has(req.url)) return event.respondWith(file(req, req.url));
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') return event.respondWith(font(req));
});
