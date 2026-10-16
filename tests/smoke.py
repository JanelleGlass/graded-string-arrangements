"""Smoke test for the website and the reader. Run before every push.

    python3 tests/smoke.py

Needs Playwright for Python and its Chromium, once per computer:
    python3 -m pip install playwright
    python3 -m playwright install chromium

What it checks
  1. Home page: a card for every song in songs.json, the home-screen app file and icons load,
     no script errors.
  2. Every song page, at laptop and phone-landscape size: the score loads with all parts,
     notes are drawn, Play moves the music forward, nothing scrolls sideways, no script errors.
     Laptop: the Full screen button goes in and out of full screen. Phone (acting like an iPhone,
     which doesn't allow it): no Full screen button.
     The Parts panel: a tab at the right edge pulls it out with the music moved over beside it, each part's eye
     puts it on the page, the parts on the page play until "Hear the parts I see" is unticked and a
     speaker for each part chooses, and choices survive a reload.
  3. The Claude preview version (reader/reader.html) with a fake two-person room:
     the teacher conducts, a student follows, and the student's music keeps up with the teacher's.
  4. The app layer: the browser can install the site, every file is saved after one visit, every song
     opens and plays with the server stopped and the network off, and an update reaches the saved
     copy without downloading the unchanged files (the string sounds) again.

Offline options (only needed where the internet is filtered):
  ALPHATAB_JS=/path/to/alphaTab.min.js   serve alphaTab from a local copy instead of jsdelivr
  NO_WEBFONTS=1                           skip Google Fonts
"""
import asyncio, json, os, re, sys, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
SONGS = json.loads((ROOT / 'songs.json').read_text(encoding='utf-8'))
PREVIEW_HEAD = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">'
                '<style>body{margin:0;padding:0}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style>'
                '</head><body>\n')
failures = []


def check(ok, what):
    print(('  ok    ' if ok else '  FAIL  ') + what)
    if not ok:
        failures.append(what)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.server.asked.append(self.path)
        if self.path.split('?')[0] == '/sw.js' and self.server.sw is not None:
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript')
            self.send_header('Content-Length', str(len(self.server.sw)))
            self.end_headers()
            self.wfile.write(self.server.sw)
            return
        super().do_GET()


class Server(ThreadingHTTPServer):
    asked = None  # paths asked for, in order
    sw = None     # bytes served as /sw.js in place of the built one (to act out a new version)

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):  # a test window closed mid-download
            super().handle_error(request, client_address)


def serve(keep=False):
    httpd = Server(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    httpd.asked = []
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{httpd.server_address[1]}'
    return (base, httpd) if keep else base


async def setup(ctx):
    if os.environ.get('ALPHATAB_JS'):
        await ctx.route('https://cdn.jsdelivr.net/**', lambda r: r.fulfill(
            path=os.environ['ALPHATAB_JS'], content_type='application/javascript', headers={'Access-Control-Allow-Origin': '*'}))
    if os.environ.get('NO_WEBFONTS'):
        await ctx.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))


async def open_reader(ctx, url, errors, name, w=1366, h=860):
    pg = await ctx.new_page()
    await pg.set_viewport_size({'width': w, 'height': h})
    pg.on('pageerror', lambda e: errors.append(f'{name}: {e}'))
    await pg.goto(url)
    await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
    await pg.wait_for_timeout(1000)
    return pg


async def song_checks(browser, base):
    for song in SONGS:
        slug = song['slug']
        print(f'Song page: {slug}')
        for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
            ctx = await browser.new_context(device_scale_factor=1)
            await setup(ctx)
            if label == 'phone landscape':
                # Like an iPhone: the browser won't let a page go full screen.
                await ctx.add_init_script("for (const k of ['fullscreenEnabled', 'webkitFullscreenEnabled']) Object.defineProperty(Document.prototype, k, { get: () => false });")
            errors = []
            try:
                pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, slug, w, h)
            except Exception as e:
                check(False, f'{label}: page loads ({e.__class__.__name__})')
                await ctx.close()
                continue
            title = (await pg.evaluate("() => document.getElementById('infoBtn').firstChild.textContent")).strip()
            check(title == song['title'], f'{label}: title reads "{song["title"]}" (got "{title}")')
            tracks = await pg.evaluate('() => reader.api.score ? reader.api.score.tracks.length : 0')
            check(tracks > 0, f'{label}: score has parts ({tracks})')
            drawn = await pg.evaluate("() => document.querySelectorAll('#sheet .at-surface > *').length")
            check(drawn > 0, f'{label}: notes are drawn')
            wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
            check(wide <= 1, f'{label}: no sideways scrolling ({wide}px extra)')
            shown = await pg.evaluate("() => !!document.getElementById('fullBtn').offsetParent")
            if label == 'phone landscape':
                check(not shown, f'{label}: no Full screen button where the browser does not allow it')
            else:
                check(shown, f'{label}: Full screen button shows')
                await pg.click('#fullBtn')
                await pg.wait_for_timeout(500)
                on = await pg.evaluate("() => [!!document.fullscreenElement, document.getElementById('fullBtn').getAttribute('aria-label')]")
                await pg.click('#fullBtn')
                await pg.wait_for_timeout(500)
                off = await pg.evaluate("() => [!!document.fullscreenElement, document.getElementById('fullBtn').getAttribute('aria-label')]")
                check(on == [True, 'Leave full screen'] and off == [False, 'Full screen'],
                      f'{label}: Full screen button goes in and out of full screen ({on}, {off})')
            await pg.click('#play')
            await pg.wait_for_timeout(3500)
            tick = await pg.evaluate('() => reader.at()')
            check(tick > 0, f'{label}: Play moves the music forward (tick {round(tick)})')
            await pg.click('#play')
            check(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()


# Listen in on what the reader tells the player to mute. Every change sends all 24 parts, muted or not.
SPY_JS = '''() => {
  window.__muted = new Set();
  const api = reader.api, orig = api.changeTrackMute.bind(api);
  api.changeTrackMute = (tracks, m) => { tracks.forEach(t => m ? __muted.add(t.index) : __muted.delete(t.index)); return orig(tracks, m); };
}'''
PLAYING_JS = '() => [...Array(24).keys()].filter(i => !__muted.has(i))'
SHOWN_JS = '() => reader.api.tracks.map(t => t.index)'


async def parts_checks(browser, base):
    """The Parts panel: each part on the page or not, and playing or not, on its own."""
    slug = SONGS[0]['slug']
    print(f'Parts panel: {slug}')
    ctx = await browser.new_context(device_scale_factor=1)
    await setup(ctx)
    errors = []
    pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, 'parts')
    await pg.evaluate(SPY_JS)
    speakers = "() => [...document.querySelectorAll('#mixParts .tog.hear')].filter(b => b.offsetParent).length"
    # Parts are numbered level by level (Open Strings 0-3, Easy 4-7, Melody 8-11, Harmony 12-15...), violin to bass.
    check(await pg.is_visible('#g-parts') and not await pg.is_visible('#fabRow #g-parts'), 'Parts is a tab at the right edge, not a button in the strip')
    await pg.click('#g-parts')
    check(await pg.is_visible('#pop-parts'), 'the Parts tab opens the panel')
    await pg.wait_for_timeout(600)
    clear = await pg.evaluate('''() => document.getElementById('sheet').getBoundingClientRect().right
      <= Math.min(document.getElementById('pop-parts').getBoundingClientRect().left, document.getElementById('g-parts').getBoundingClientRect().left) + 1''')
    check(clear, 'the panel and its tab open at the right edge, with the music moved over beside them, uncovered')
    check(await pg.evaluate(SHOWN_JS) == [8], 'a first visit shows Violin, Melody')
    check(await pg.evaluate(speakers) == 0 and await pg.is_checked('#hearSame'), '"Hear the parts I see" starts ticked: eyes only')
    # A violin at Open Strings reading along with a cello at Advanced Melody: those two parts and no others.
    await pg.click('#see-4-2'); await pg.click('#see-0-0'); await pg.click('#see-2-0'); await pg.wait_for_timeout(1500)
    check(await pg.evaluate(SHOWN_JS) == [0, 18], 'eyes on Violin Open Strings and Cello Advanced Melody show just those two, in score order')
    check(await pg.evaluate(PLAYING_JS) == [0, 18], 'ticked, the parts on the page are the parts that play')
    check(await pg.evaluate("() => document.querySelectorAll('#mixParts .tog.see').length") == 24, 'one eye for every part')
    label = await pg.get_attribute('#g-parts', 'title')
    check(label == 'Parts: 2 parts', f'the Parts tab counts the parts on the page ("{label}")')
    await pg.click('#hearSame')
    check(await pg.evaluate(speakers) == 24, 'unticking it shows a Hear speaker for every part')
    check(await pg.evaluate(PLAYING_JS) == [0, 18], 'the speakers start from what was playing')
    await pg.click('#hear-2-0'); await pg.click('#hear-0-0')
    check(await pg.evaluate(PLAYING_JS) == [8, 18], 'its speakers choose what plays: the tune on violin, my own part left out')
    await pg.click('#see-3-1'); await pg.wait_for_timeout(1500)
    check(await pg.evaluate(PLAYING_JS) == [8, 18], 'unticked, a new part on the page stays quiet until its speaker is on')
    await pg.click('#see-3-1'); await pg.wait_for_timeout(1500)
    await pg.click('#hearSame')
    check(await pg.evaluate(PLAYING_JS) == [0, 18] and await pg.evaluate(speakers) == 0, 'ticking it again plays the parts on the page, and the speakers fold away')
    await pg.click('#hearSame')
    check(await pg.evaluate(PLAYING_JS) == [8, 18], "unticking it again brings back the speakers' mix")
    await pg.click('#see-0-0'); await pg.click('#see-4-2'); await pg.wait_for_timeout(1500)
    check(await pg.evaluate(SHOWN_JS) == [18], 'the last part on the page stays on')
    label = await pg.get_attribute('#g-parts', 'title')
    check(label == 'Parts: Cello · Advanced Melody', f'the Parts tab names a single part ("{label}")')
    await pg.click('#partsX'); await pg.wait_for_timeout(600)
    wide = await pg.evaluate("() => document.getElementById('sheet').getBoundingClientRect().right > innerWidth - 60")
    check(wide and not await pg.is_visible('#pop-parts'), 'closing the panel gives the music the whole width again')
    check(await pg.evaluate(PLAYING_JS) == [8, 18], "and the speakers' mix keeps playing with the panel closed")
    await pg.reload()
    await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
    await pg.evaluate(SPY_JS)
    await pg.click('#g-parts'); await pg.click('#hear-0-0'); await pg.click('#hear-0-0')
    check(await pg.evaluate(SHOWN_JS) == [18] and await pg.evaluate(PLAYING_JS) == [8, 18] and await pg.evaluate(speakers) == 24,
          'the choices, and the box unticked, are still there after a reload')
    key = f'{slug}-reader'
    # Settings saved when the eyes went by instrument and by level: violin and cello, Melody and Harmony.
    await pg.evaluate(f"localStorage.setItem('{key}', JSON.stringify({{ seeInst: [0, 2], seeTier: [2, 3], heard: [8, 12] }}))")
    await pg.reload()
    await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
    await pg.evaluate(SPY_JS)
    await pg.click('#g-parts'); await pg.click('#hear-0-0'); await pg.click('#hear-0-0')
    check(await pg.evaluate(SHOWN_JS) == [8, 10, 12, 14] and await pg.evaluate(PLAYING_JS) == [8, 12], 'settings from the instrument and level eyes carry over, with their mix')
    # Settings saved by the reader before the Parts panel: cello, Harmony, with the tune above; play along with
    # Melody, leaving my part out.
    await pg.evaluate(f"localStorage.setItem('{key}', JSON.stringify({{ inst: 2, tier: 3, show: 'tune', hear: [2], muteMine: true }}))")
    await pg.reload()
    await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
    await pg.evaluate(SPY_JS)
    await pg.click('#g-parts'); await pg.click('#hear-0-0'); await pg.click('#hear-0-0')
    check(await pg.evaluate(SHOWN_JS) == [10, 14] and await pg.evaluate(PLAYING_JS) == [8, 9, 10, 11], 'older saved settings carry over')
    check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
    await ctx.close()


async def home_checks(browser, base):
    print('Home page')
    ctx = await browser.new_context()
    await setup(ctx)
    errors = []
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errors.append(str(e)))
    await pg.goto(base + '/')
    links = await pg.evaluate("() => [...document.querySelectorAll('a.song')].map(a => a.getAttribute('href'))")
    for s in SONGS:
        check(f"songs/{s['slug']}/" in links, f"card for {s['title']}")
    check(len(links) == len(SONGS), f'{len(links)} cards for {len(SONGS)} songs')
    # Added to a phone's home screen, the site opens like an app (no address bar): the app file and its icons load.
    app = await pg.evaluate("""async () => {
      const link = document.querySelector('link[rel=manifest]'), touch = document.querySelector('link[rel=apple-touch-icon]');
      if (!link || !touch) return 'missing link';
      const m = await (await fetch(link.href)).json();
      for (const src of [...m.icons.map(i => new URL(i.src, link.href).href), touch.href])
        if (!(await fetch(src)).ok) return 'missing ' + src;
      return m.display;
    }""")
    check(app == 'standalone', f'home-screen app file and icons load ({app})')
    check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
    await ctx.close()


async def preview_checks(browser, base):
    """The Claude preview: reader.html as published, with the conductor, against a fake room."""
    print('Claude preview (reader/reader.html) with the conductor')
    first = SONGS[0]['slug'] if SONGS else 'the-first-noel'
    page_html = PREVIEW_HEAD + (ROOT / 'reader' / 'reader.html').read_text(encoding='utf-8') + '\n</body></html>'
    ctx = await browser.new_context(device_scale_factor=1)
    await setup(ctx)
    await ctx.add_init_script(path=str(ROOT / 'tests' / 'mockroom.js'))
    await ctx.route('**/reader/__preview.html*', lambda r: r.fulfill(body=page_html, content_type='text/html'))
    await ctx.route('**/reader/scores/*', lambda r: r.fulfill(path=str(ROOT / 'songs' / 'the-first-noel' / 'the-first-noel.xml')))
    await ctx.route('**/reader/font/*', lambda r: r.fulfill(path=str(ROOT / 'assets' / 'font' / r.request.url.rsplit('/', 1)[1])))
    await ctx.route('**/reader/soundfont/*', lambda r: r.fulfill(path=str(ROOT / 'assets' / 'soundfont' / r.request.url.rsplit('/', 1)[1])))
    errors = []
    teacher = await open_reader(ctx, f'{base}/reader/__preview.html', errors, 'teacher')
    student = await open_reader(ctx, f'{base}/reader/__preview.html?student', errors, 'student')
    await teacher.click('#g-together'); await teacher.wait_for_timeout(1000)
    await student.click('#g-together'); await student.wait_for_timeout(2500)
    following = await student.evaluate("() => document.body.classList.contains('following')")
    check(following, 'student joins the teacher')
    await teacher.click('#play'); await teacher.wait_for_timeout(4000)
    gaps = []
    for _ in range(6):
        a, b = await asyncio.gather(teacher.evaluate('() => reader.at()'), student.evaluate('() => reader.at()'))
        gaps.append(abs(a - b))
        await asyncio.sleep(0.3)
    gaps.sort()
    # 960 ticks = one quarter note. A working conductor keeps students within a small fraction of a beat.
    check(gaps[len(gaps) // 2] < 240, f'student keeps up with the teacher (typical gap {round(gaps[len(gaps) // 2])} ticks)')
    await teacher.click('#play')
    check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
    await ctx.close()


# Which of the files listed in sw.js are not saved yet (run in a page of the site).
MISSING_JS = r'''async () => {
  const text = await (await fetch('sw.js', { cache: 'no-store' })).text();
  const files = JSON.parse(text.match(/const FILES = (\{.*\});/)[1]);
  const keys = new Set((await (await caches.open('gsa-files')).keys()).map((r) => r.url));
  const root = new URL('sw.js', location).href.replace(/sw\.js$/, '');
  return Object.entries(files).filter(([u, rev]) => {
    const url = new URL(u, root).href;
    return !keys.has(url + (url.includes('?') ? '&' : '?') + '__rev=' + rev);
  }).map(([u]) => u);
}'''

# Ask the browser to look for a new sw.js, and wait until it has taken over (or say why not).
UPDATE_JS = '''async () => {
  const reg = await navigator.serviceWorker.getRegistration();
  await reg.update();
  const next = reg.installing || reg.waiting;
  if (!next) return 'no new version found';
  return new Promise((done) => {
    const look = () => { if (next.state === 'activated') done('ok'); if (next.state === 'redundant') done('the new version failed to install'); };
    next.addEventListener('statechange', look); look();
  });
}'''

LETTERING_JS = '''() => document.fonts.check('600 16px Figtree') && document.fonts.check('600 16px "EB Garamond"')'''


async def app_checks(browser):
    """The installable, offline site: what a student gets from "Add to Home Screen"."""
    print('App: install, offline, updates')
    base, httpd = serve(keep=True)
    ctx = await browser.new_context(device_scale_factor=1)
    await setup(ctx)
    errors = []
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errors.append(str(e)))
    await pg.goto(base + '/')
    try:
        await pg.wait_for_function('() => !!navigator.serviceWorker.controller', timeout=120000)
        saved = True
    except Exception:
        saved = False
    check(saved, 'the offline copy is saved after one visit')
    cdp = await ctx.new_cdp_session(pg)
    blockers = (await cdp.send('Page.getInstallabilityErrors')).get('installabilityErrors', [])
    check(not blockers, 'the browser offers to install it' + (f': {blockers}' if blockers else ''))
    if saved:
        missing = await pg.evaluate(MISSING_JS)
        check(not missing, 'every file in sw.js is saved' + (f' (missing {missing})' if missing else ''))

        # A new version where one song page changed: only that page is fetched again, the string sounds stay.
        sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
        files = json.loads(re.search(r'const FILES = (\{.*\});', sw).group(1))
        first = f"songs/{SONGS[0]['slug']}/"
        files[first] = 'new-build'
        httpd.sw = re.sub(r'const FILES = \{.*\};', lambda m: 'const FILES = ' + json.dumps(files) + ';', sw).encode('utf-8')
        httpd.asked.clear()
        result = await pg.evaluate(UPDATE_JS)
        check(result == 'ok', f'a new version takes over the saved copy ({result})')
        again = [a for a in httpd.asked if a.split('?')[0] != '/sw.js']
        check(again == [f'/{first}'], f'only the changed file is fetched again (fetched {again})')
        missing = await pg.evaluate(MISSING_JS)
        check(not missing, 'the new version has every file saved' + (f' (missing {missing})' if missing else ''))

    # Network off, server gone.
    httpd.shutdown()
    httpd.server_close()
    await ctx.set_offline(True)
    home = await ctx.new_page()
    home.on('pageerror', lambda e: errors.append(str(e)))
    try:
        await home.goto(base + '/')
        cards = await home.evaluate("() => document.querySelectorAll('a.song').length")
    except Exception as e:
        cards = e.__class__.__name__
    check(cards == len(SONGS), f'offline: home page shows {len(SONGS)} cards (got {cards})')
    for song in SONGS:
        slug = song['slug']
        try:
            sp = await open_reader(ctx, f'{base}/songs/{slug}/', errors, slug, 844, 390)
        except Exception as e:
            check(False, f'offline: {slug} opens ({e.__class__.__name__})')
            continue
        drawn = await sp.evaluate("() => document.querySelectorAll('#sheet .at-surface > *').length")
        check(drawn > 0, f'offline: {slug} draws its notes')
        await sp.click('#play')
        await sp.wait_for_timeout(2500)
        tick = await sp.evaluate('() => reader.at()')
        check(tick > 0, f'offline: {slug} plays (tick {round(tick)})')
        await sp.click('#play')
        if not os.environ.get('NO_WEBFONTS'):
            check(await sp.evaluate(LETTERING_JS), f'offline: {slug} has its lettering')
        await sp.close()
    stray = await ctx.new_page()
    try:
        await stray.goto(base + '/songs/not-saved/')
        cards = await stray.evaluate("() => document.querySelectorAll('a.song').length")
    except Exception as e:
        cards = e.__class__.__name__
    check(cards == len(SONGS), f'offline: a page that was never saved shows the home page (got {cards})')
    check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
    await ctx.close()


async def main():
    base = serve()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        await home_checks(browser, base)
        await song_checks(browser, base)
        await parts_checks(browser, base)
        await preview_checks(browser, base)
        await app_checks(browser)
        await browser.close()
    print()
    if failures:
        print(f'{len(failures)} check(s) failed:')
        for f in failures:
            print('  - ' + f)
        sys.exit(1)
    print('All checks passed.')


asyncio.run(main())
