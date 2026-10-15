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
  3. The Claude preview version (reader/reader.html) with a fake two-person room:
     the teacher conducts, a student follows, and the student's music keeps up with the teacher's.

Offline options (only needed where the internet is filtered):
  ALPHATAB_JS=/path/to/alphaTab.min.js   serve alphaTab from a local copy instead of jsdelivr
  NO_WEBFONTS=1                           skip Google Fonts
"""
import asyncio, json, os, sys, threading
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


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{httpd.server_address[1]}'


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


async def main():
    base = serve()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        await home_checks(browser, base)
        await song_checks(browser, base)
        await preview_checks(browser, base)
        await browser.close()
    print()
    if failures:
        print(f'{len(failures)} check(s) failed:')
        for f in failures:
            print('  - ' + f)
        sys.exit(1)
    print('All checks passed.')


asyncio.run(main())
