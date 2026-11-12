"""Smoke test for the website and the reader. Run before every push.

    python3 tests/smoke.py

It takes about twelve minutes, a little more with each song, and says how long at the end. Run it with no time limit:
a limit that stops it part-way closes its browser, and Playwright then reports "Page crashed" or "Target crashed"
in whatever step was running (the reader didn't crash; 2026-10-23).

Needs Playwright for Python and its Chromium, once per computer:
    python3 -m pip install playwright
    python3 -m playwright install chromium

What it checks
  1. Home page: a card for every song in songs.json, each under its section's heading (Christmas, Hymns, Solos,
     Other, in that order); the tabs over them (All songs, then one per section) each show only their section, a
     link with #hymns opens on that tab; the home-screen app file and icons load, no script errors.
  2. Every song page, at laptop and phone-landscape size: the score loads with all parts,
     notes are drawn, Play moves the music forward, nothing scrolls sideways, no script errors.
     The page settings are separate buttons in the strip; On the note steps through its five looks,
     each drawn as it says; on a laptop the music button switches between pages and one long line.
     On pages every line names its parts, and scrolled down the size buttons stay at the top of the
     window. Along one long line, each part's name, clef and key signature (the key in force there,
     after every change of key) stay pinned at the left edge.
     On pages every count sits under its own staff, clear of the music; with Counting off the lines of music sit
     closer together, and switched on again they make room for the counts. At the smallest size (0.15x) the counts
     shrink with the music and still sit clear of it. The bouncing ball's button (at the top) hides and shows the ball above the part.
     Laptop: the Full screen button goes in and out of full screen. Phone (acting like an iPhone,
     which doesn't allow it): no Full screen button, and pinching the music makes it bigger and smaller.
     The Parts panel: the music runs a little under a tab at the right edge, which pulls the panel out over it, each part's eye
     puts it on the page, the parts on the page play until "Hear the parts I see" is unticked and a
     speaker for each part chooses, and choices survive a reload.
     Songs in levels and voices (40 parts): a row for each level and voice, an eye for every part
     (cello and bass Inner too), the group rule over the table, the size buttons and Line or Pages
     moved over beside the open panel (not under it), and choices saved with the six levels or with
     34 parts moving to their match. Songs built on 2026-10-16 (34 parts): the cello and bass Inner
     cells greyed out in place (a tap says why). Run on the first 34-part song in songs.json, or on
     the first 40-part song's score cut to 34 parts when there is none. Songs with parts for the strongest
     players after the 40 (a Countermelody and/or Concert parts, 42 or 44 parts): a row for each at the bottom,
     an eye for violin and viola, cello and bass greyed out in place (a tap says why), the chosen parts shown,
     played and labelled, every Concert part with notes and no string colours (a Countermelody with them), the
     About box naming them, note names on every note of a Concert part's double stops in pitch order, a finger
     look saying Concert parts have none, and a Concert part's tune in its second voice counted. Run on every such
     song. Tapping a note rings that note: where a Concert part's two voices start a note together (alone and with a
     part shown above it), and where a note sits over the other voice's rest. Choices are saved as the graded 40
     ('voices40', which a reader from before the extra rows knows) with the full layout beside it, and a second
     visit shows the same parts. Songs with a Piano part last (Silent Night): a Piano row at the bottom with one eye
     across the instrument columns, the piano shown and played on its own, two staves named "Pno" inside the music's
     left edge, no string colours (String colors says so), the piano sound loaded with the strings, the About box
     naming it, and the choices saved with the full layout. A piece with no levels (one line on some or all instruments, such as Twinkle
     Harmony): a first visit shows the first part, one row named for the line under a Part heading, any instrument it
     isn't for greyed out in place (a tap says why), no group rule, the About box saying who it is for, a part taken
     off the page staying off after a reload, and (Twinkle Harmony) a choice saved when it was for viola and cello
     only moving to the same part.
     Print (the first song, laptop and phone sizes): the button sits at the top beside the size buttons and the strip
     keeps one row; it makes a copy for paper, a line of music at a time with its counts, under the parts, title and
     Strings key, finger numbers to the left of the notes, every one clear of the note before, and only that prints, each line whole; the music on the screen comes back just as it was (line or
     pages, size, place); Ctrl+P does the same; the browser's own Print menu prints the music as it is now on pages and
     not a stale copy in one long line; and where the print window doesn't open by itself, a card offers a Print button.
     Joy to the World's violin melody, which used to leave one line on a second sheet, prints on one sheet.
     Download PDF saves the same sheet as a PDF file, named for the song and its parts, without a print window.
  2b. The sight-reading page (unlisted), at laptop and phone-landscape sizes: an exercise from the book page and number
     in the address, its row (book page, Violin / Viola, exercise number, New exercise) in sight over the music,
     the page's starting look (string colors, plain notes) and tempo, Play moving the music; New exercise changing the
     music and the number in the address; a typed number bringing an exercise back, the same after a reload; Viola in
     alto clef with the viola's strings, kept after a reload; another book page starting with its own look again.
     (The generator's music rules are checked by tests/sight_reading.py.)
     Look ahead (laptop in one long line and on pages, phone): turning it on brings a count-in and the page's tempo;
     at its three levels (½ beat, 1 beat, 1 bar), at 60 and 120, while it plays, every note due within that time of what is
     heard is covered and no other is (checked against each note's place on the screen, during a count-in too), the
     staff lines and bar lines are drawn over the cover, and every note comes back when the music stops.
     Flash a bar (laptop, iPad upright, phone both ways round): the pattern drawn inside its card; a round goes look,
     hide, count in, play, check, with Start, Got it and Not yet each usable only when they apply; Got it counts the
     streak and three in a row move up a level; the level, streak and best are still there after a reload; Not yet
     starts the streak again; − and + change the level; Violin / Viola is kept with the sight-reading page's. The
     sight-reading page's Flash a bar button opens it on the same book page.
     Listen (Flash a bar, laptop): with no microphone it says so and stays off; with a made-up microphone
     (tests/listen_takes.js) it asks for the timing check first and keeps its answer, marks a round played as written
     with a tick on every note and "Every note right", marks a wrong note with a cross and a late one "late", and is
     still on after a reload.
  3. The Claude preview version (reader/reader.html) with a fake two-person room:
     the teacher conducts, a student follows, and the student's music keeps up with the teacher's.
  4. The app layer: the browser can install the site, every file is saved after one visit, every song (and the
     sight-reading page, New exercise too) opens and plays with the server stopped and the network off, and an update reaches the saved
     copy without downloading the unchanged files (the string sounds) again.

Offline options (only needed where the internet is filtered):
  ALPHATAB_JS=/path/to/alphaTab.min.js   serve alphaTab from a local copy instead of jsdelivr
  NO_WEBFONTS=1                           skip Google Fonts
"""
import asyncio, json, os, re, sys, threading, time
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
SONGS = json.loads((ROOT / 'songs.json').read_text(encoding='utf-8'))
PARTS = {s['slug']: (ROOT / 'songs' / s['slug'] / f"{s['slug']}.xml").read_text(encoding='utf-8').count('<score-part ') for s in SONGS}
sys.path.insert(0, str(ROOT / 'tools'))
from build_site import SECTIONS, section_id  # the home page's sections, in page order, and their short names
PREVIEW_HEAD = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1">'
                '<style>body{margin:0;padding:0}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style>'
                '</head><body>\n')
failures = []
# Messages have signs like "−" that Windows can't write to a file in its own code page, so a run saved to a file
# stopped there. Write them in UTF-8.
sys.stdout.reconfigure(encoding='utf-8')


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
    # Play together on test channels of their own, so a test never meets a real class (app/together.js).
    await ctx.add_init_script("try { localStorage.setItem('gsa-together-test', '1'); } catch (e) {}")
    if os.environ.get('ALPHATAB_JS'):
        await ctx.route('https://cdn.jsdelivr.net/npm/@coderline/**', lambda r: r.fulfill(
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


# Counts the reader's drawings of the music, so a step can wait until the music is drawn (with any second drawing the
# reader starts itself, for room for the part names) instead of pausing a fixed time.
DRAWS_JS = '''() => { if (window.__draws) return; window.__draws = { started: 0, done: 0, at: 0 };
  reader.api.renderStarted.on(() => { __draws.started++; });
  reader.api.renderFinished.on(() => { __draws.done++; __draws.at = performance.now(); }); }'''


async def click_drawn(pg, sel):
    """Click something that draws the music again (after DRAWS_JS), and wait until it is drawn. False if it never was."""
    n = await pg.evaluate('() => __draws.done')
    await pg.click(sel)
    try:
        await pg.wait_for_function('(n) => __draws.done > n && __draws.done >= __draws.started && performance.now() - __draws.at > 250',
                                   arg=n, timeout=15000)
        return True
    except Exception:
        return False


# Pages: a part name beside every staff on every line (names drawn, and lines times parts on the page).
NAMED_LINES_JS = '''() => {
  const names = new Set(reader.api.tracks.map(t => t.name));
  const drawn = [...document.querySelectorAll('#sheet svg text')].filter(t => names.has(t.textContent)).length;
  const lines = new Set(reader.api.boundsLookup.staffSystems.map(s => Math.round(s.visualBounds.y))).size;
  return [drawn, lines * reader.api.tracks.length];
}'''
# Every count sits clear of the music: its numeral doesn't touch a staff line, note, stem, beam, bar number or word (a
# count pushed into the next line of music would). Also the music's height, to see the lines close up without counts.
COUNTS_CLEAR_JS = '''() => {
  const surf = document.querySelector('#sheet .at-surface'), base = surf.getBoundingClientRect();
  const ink = [];
  const add = (r, what) => { if (r.width || r.height) ink.push({ x: r.left - base.left, r: r.right - base.left, y: r.top - base.top, b: r.bottom - base.top, what }); };
  surf.querySelectorAll('svg rect, svg path, svg line, svg polygon').forEach(e => add(e.getBoundingClientRect(), e.tagName));
  surf.querySelectorAll('svg text').forEach(t => { const x = (t.textContent || '').trim(), c = x.codePointAt(0);
    if (!x || (c >= 0xE000 && c <= 0xF8FF) || t.parentElement.getAttribute('transform')?.includes('rotate')) return;
    const r = t.getBoundingClientRect(), h = r.height * 0.2; add(new DOMRect(r.left, r.top + h, r.width, r.height - 2 * h), 'text ' + x); });
  const hits = [];
  const counts = [...document.querySelectorAll('.beat-count')].filter(e => e.textContent);
  for (const el of counts) {
    const sz = parseFloat(el.style.width), cx = parseFloat(el.style.left), top = parseFloat(el.style.top);
    const g = { x: cx - sz * 0.22, r: cx + sz * 0.22, y: top + sz * 0.28, b: top + sz * 0.72 };
    const e = ink.find(e => g.x < e.r - 0.5 && g.r > e.x + 0.5 && g.y < e.b - 0.5 && g.b > e.y + 0.5);
    if (e) hits.push(`"${el.textContent}" at ${Math.round(cx)},${Math.round(top)} on ${e.what}`);
  }
  return { counts: counts.length, hits, h: Math.round(base.height) };
}'''
# How far the page is scrolled, and whether the size buttons and Line or Pages can still be tapped at the top.
TOOLS_HELD_JS = '''() => {
  const ids = ['zoomOut', 'zoomIn', 'g-layout'].filter(id => document.getElementById(id).offsetParent);
  const ok = ids.every(id => { const b = document.getElementById(id), r = b.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return r.top >= 0 && r.bottom < window.innerHeight * 0.25 && h && b.contains(h); });
  return [Math.round(window.scrollY), ok];
}'''
# One long line: scrolled along to the middle and to just after each change of key, the pinned start shows a clef for
# each part and the key signature in force there.
LINE_HEAD_JS = '''async () => {
  const sheet = document.getElementById('sheet'), head = document.querySelector('.line-head'), sc = reader.api.score;
  const bars = reader.api.boundsLookup.staffSystems[0].bars.map(b => b.visualBounds.x), staves = reader.api.tracks.length;
  const at = new Set([Math.floor(bars.length / 2)]);
  sc.masterBars.forEach((mb, i) => { if (i && mb.keySignature !== sc.masterBars[i - 1].keySignature) at.add(i); });
  const out = [];
  for (const b of at) {
    sheet.scrollLeft = bars[b];
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const g = [...head.querySelectorAll('text')].map(t => t.textContent.codePointAt(0));
    out.push({ bar: b + 1, on: head.classList.contains('on') && head.classList.contains('lifted'), staves,
      clefs: g.filter(c => c >= 0xE050 && c <= 0xE07F).length, keys: g.filter(c => c === 0xE260 || c === 0xE262).length,
      want: Math.abs(sc.masterBars[b].keySignature) * staves });
  }
  sheet.scrollLeft = 0;
  return out;
}'''


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
            # What's drawn on the page: one tap-to-change button per setting in the strip, no "On the page" panel.
            strip = await pg.evaluate('''() => ['g-colors', 'g-ltype', 'g-fnum', 'g-fpos', 'g-look', 'g-layout', 'g-count', 'g-page', 'countTog']
              .filter(id => { const e = document.getElementById(id); return e && e.offsetParent && e.closest('#fabRow'); })''')
            # The same buttons on every screen, always in the same place.
            want = ['g-colors', 'g-look', 'g-count']
            check(strip == want, f'{label}: the page settings are separate buttons in the strip ({strip})')
            # The size of the music, and on bigger screens Line or Pages, sit at the top right of the music.
            top = await pg.evaluate('''() => ['zoomOut', 'zoomIn', 'g-layout'].filter(id => { const e = document.getElementById(id); return e.offsetParent && e.closest('#topTools'); })''')
            above = await pg.evaluate("() => document.getElementById('topTools').getBoundingClientRect().bottom <= document.querySelector('#sheet .at-surface').getBoundingClientRect().top + 1")
            want_top = ['zoomOut', 'zoomIn', 'g-layout'] if label == 'laptop' else ['zoomOut', 'zoomIn']
            check(top == want_top and above, f'{label}: the size buttons{" and Line/Pages" if label == "laptop" else ""} sit at the top, above the music ({top})')
            # On the note: one button steps through five looks. Laptops start on finger numbers inside the notes, phones
            # on note names with finger numbers to the left. Each look draws what it says, at the same size, finger
            # numbers inside the notes or to their left.
            look_js = '''() => { const fin = [...document.querySelectorAll('#sheet text.fin')].map(t => t.textContent);
              return { look: document.querySelector('#g-look .now .word').textContent, head: document.querySelector('#g-look .now ellipse').getAttribute('fill'),
                       off: (r => (r.left + r.right) / 2)(document.querySelector('#g-look .now').getBoundingClientRect()) - (r => (r.left + r.right) / 2)(document.getElementById('g-look').getBoundingClientRect()), names: fin.some(x => /^[A-G]/.test(x)),
                       fingers: fin.some(x => /^[0-4]/.test(x)), size: reader.api.settings.display.scale,
                       sides: [...new Set([...document.querySelectorAll('#sheet text.fin')].filter(t => /^[0-4↑↓]/.test(t.textContent)).map(t => t.getAttribute('text-anchor')))].sort() }; }'''
            seen = [await pg.evaluate(look_js)]
            for _ in range(5):
                await pg.click('#g-look'); await pg.wait_for_timeout(2200)
                seen.append(await pg.evaluate(look_js))
            order = ['Fingers inside', 'Fingers to the left', 'Note names and fingers', 'Note names', 'Plain notes']
            first = 0 if label == 'laptop' else 2
            want_looks = [order[(first + k) % 5] for k in range(6)]
            check([x['look'] for x in seen] == want_looks, f'{label}: the On the note button steps through the five looks ({[x["look"] for x in seen]})')
            drawn = {x['look']: (x['names'], x['fingers']) for x in seen}
            check(drawn == {'Fingers inside': (False, True), 'Fingers to the left': (False, True),
                            'Note names and fingers': (True, True), 'Note names': (True, False), 'Plain notes': (False, False)}, f'{label}: each look draws what it says ({drawn})')
            sides = {x['look']: x['sides'] for x in seen if x['fingers']}
            check(sides == {'Fingers inside': ['middle'], 'Fingers to the left': ['end'], 'Note names and fingers': ['end']},
                  f'{label}: finger numbers sit inside the notes or to their left, as the look says ({sides})')
            heads = {x['look']: x['head'] for x in seen}
            check(all(h == ('#17201C' if k == 'Plain notes' else '#1D4ED8') for k, h in heads.items()), f'{label}: the note head on the button is black for Plain notes, blue otherwise ({heads})')
            offs = {x['look']: round(x['off'], 1) for x in seen}
            check(all(abs(o) <= 1 for o in offs.values()), f'{label}: each look sits in the middle of the On the note button ({offs})')
            sizes = {x['look']: x['size'] for x in seen}
            check(len(set(sizes.values())) == 1, f'{label}: the music stays the same size for all five looks ({sizes})')
            if label != 'laptop':
                for _ in range(3): await pg.click('#g-look')  # back to where a phone starts
                await pg.wait_for_timeout(1500)
            said = (await pg.text_content('#g-count .now')).strip()
            check(said == 'Counting: On', f'{label}: the Counting button says so in words ("{said}")')
            await pg.click('#g-count')
            off = await pg.evaluate("() => document.getElementById('sheet').classList.contains('counts-off')")
            await pg.wait_for_timeout(1500)
            await pg.click('#g-count')
            try:  # the counts come back once the music is drawn again with their room
                await pg.wait_for_function("() => !document.getElementById('sheet').classList.contains('counts-off')", timeout=10000)
                on = True
            except Exception:
                on = False
            check(off and on, f'{label}: the Counting button in the strip hides and shows the counts')
            await pg.wait_for_timeout(1000)
            # The bouncing ball: above the part, on at first, switched off and on again with its button in the strip.
            fingers = "() => document.querySelectorAll('#sheet .pointer').length"
            had = await pg.evaluate(fingers)
            await pg.click('#g-point'); await pg.wait_for_timeout(300)
            gone = await pg.evaluate(fingers)
            await pg.click('#g-point'); await pg.wait_for_timeout(300)
            back_on = await pg.evaluate(fingers)
            check(had > 0 and gone == 0 and back_on == had, f'{label}: the bouncing ball button hides and shows the ball ({had}, off {gone}, on {back_on})')
            # Nothing in the strip moves as labels change: each changing button keeps one width.
            widths = []
            for _ in range(5):
                widths.append(await pg.evaluate("() => [...document.querySelectorAll('#fabRow .fab-btn')].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().left))"))
                await pg.click('#g-look'); await pg.wait_for_timeout(600)
            check(all(w == widths[0] for w in widths), f'{label}: the buttons stay in the same place as On the note changes')
            if label == 'laptop':
                await pg.click('#g-layout'); await pg.wait_for_timeout(1500)
                paged = await pg.evaluate("() => !document.getElementById('sheet').classList.contains('line') && document.getElementById('g-layout').title")
                named = await pg.evaluate(NAMED_LINES_JS)
                check(named[0] > 1 and named[0] == named[1], f'{label}: on pages every line of music names its parts ({named[0]} names, {named[1]} wanted)')
                laid = await pg.evaluate(COUNTS_CLEAR_JS)
                check(laid['counts'] > 0 and not laid['hits'], f'{label}: on pages every count sits in its row under its own staff, clear of the music ({laid["hits"][:3]})')
                await pg.click('#g-count'); await pg.wait_for_timeout(1500)
                closer = await pg.evaluate(COUNTS_CLEAR_JS)
                await pg.click('#g-count')
                await pg.wait_for_function("() => !document.getElementById('sheet').classList.contains('counts-off')", timeout=10000)
                await pg.wait_for_timeout(1000)
                back = await pg.evaluate(COUNTS_CLEAR_JS)
                check(closer['h'] < laid['h'] * 0.95 and abs(back['h'] - laid['h']) <= 2 and not back['hits'],
                      f'{label}: with Counting off the lines of music sit closer together, and switched on again they make room for the counts ({laid["h"]}px, off {closer["h"]}px, on again {back["h"]}px)')
                await pg.evaluate('() => window.scrollTo(0, document.documentElement.scrollHeight)'); await pg.wait_for_timeout(400)
                held = await pg.evaluate(TOOLS_HELD_JS)
                check(held[0] > 300 and held[1], f'{label}: scrolled down the pages, the size buttons and Line or Pages stay at the top of the window, ready to tap ({held})')
                await pg.evaluate('() => window.scrollTo(0, 0)')
                # The smallest size (0.15x): the counts shrink with the music, still clear of it and of each other.
                size_js = "() => ({ scale: reader.api.settings.display.scale, count: parseFloat((document.querySelector('.beat-count') || {}).style?.width) || 0 })"
                normal = await pg.evaluate(size_js)
                await pg.evaluate(DRAWS_JS)    # each step waits for the music to be drawn (about 0.3s), not a fixed 1s
                steps, drawn = 0, True
                while steps < 20 and not await pg.evaluate("() => document.getElementById('zoomOut').disabled"):
                    drawn = await click_drawn(pg, '#zoomOut') and drawn; steps += 1
                least = await pg.evaluate(size_js)
                tiny = await pg.evaluate(COUNTS_CLEAR_JS)
                check(drawn and abs(least['scale'] / normal['scale'] - 0.15) < 0.01 and least['count'] < normal['count'] and tiny['counts'] > 0 and not tiny['hits'],
                      f'{label}: the − button goes down to 0.15x, the counts shrink with the music and stay clear of it '
                      f'(size {normal["scale"]:.2f} to {least["scale"]:.2f}, counts {normal["count"]:.0f}px to {least["count"]:.0f}px, {tiny["hits"][:2]}'
                      f'{"" if drawn else ", a step was never drawn"})')
                for _ in range(steps):
                    await click_drawn(pg, '#zoomIn')
                await pg.click('#g-layout'); await pg.wait_for_timeout(1500)
                lined =await pg.evaluate("() => document.getElementById('sheet').classList.contains('line') && document.getElementById('g-layout').title")
                check(paged == 'Music: pages' and lined == 'Music: one long line', f'{label}: the music button switches between pages and one long line')
            pinned = await pg.evaluate(LINE_HEAD_JS)
            check(pinned and all(p['on'] and p['clefs'] == p['staves'] and p['keys'] == p['want'] for p in pinned),
                  f'{label}: along the line, each part\'s name, clef and key signature (the key in force there) stay pinned at the left edge ({pinned})')
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
            if label == 'phone landscape':
                # Pinch to zoom: two fingers spread on the music make it bigger; pinched together, smaller.
                cdp = await ctx.new_cdp_session(pg)
                await cdp.send('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
                cx, cy = await pg.evaluate("() => { const r = document.getElementById('sheet').getBoundingClientRect(); return [r.left + r.width * 0.55, r.top + r.height * 0.45]; }")

                async def pinch_to(ratio, d0=80):
                    pts = lambda d: [{'x': cx - d / 2, 'y': cy, 'id': 0}, {'x': cx + d / 2, 'y': cy, 'id': 1}]
                    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': pts(d0)})
                    for k in range(1, 7):
                        await cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': pts(d0 * (1 + (ratio - 1) * k / 6))})
                    live = await pg.evaluate("() => document.querySelector('#sheet .at-surface').style.transform")
                    await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
                    await pg.wait_for_timeout(1800)
                    return live, await pg.evaluate('() => reader.api.settings.display.scale')

                before = await pg.evaluate('() => reader.api.settings.display.scale')
                live, bigger = await pinch_to(1.6)
                _, smaller = await pinch_to(0.5)
                check(live.startswith('scale(') and bigger > before and smaller < bigger,
                      f'{label}: pinching the music makes it bigger and smaller (size {before:.2f}, then {bigger:.2f}, then {smaller:.2f})')
            await pg.click('#play')
            await pg.wait_for_timeout(3500)
            tick = await pg.evaluate('() => reader.at()')
            check(tick > 0, f'{label}: Play moves the music forward (tick {round(tick)})')
            await pg.click('#play')
            check(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()


# Listen in on what the reader tells the player to mute. Every change sends all the parts, muted or not.
SPY_JS = '''() => {
  window.__muted = new Set();
  const api = reader.api, orig = api.changeTrackMute.bind(api);
  api.changeTrackMute = (tracks, m) => { tracks.forEach(t => m ? __muted.add(t.index) : __muted.delete(t.index)); return orig(tracks, m); };
}'''
PLAYING_JS = '() => [...Array(reader.api.score.tracks.length).keys()].filter(i => !__muted.has(i))'
SHOWN_JS = '() => reader.api.tracks.map(t => t.index)'


async def parts_checks(browser, base):
    """The Parts panel: each part on the page or not, and playing or not, on its own (a song in the six levels)."""
    slug = next((s['slug'] for s in SONGS if PARTS[s['slug']] == 24), None)
    if not slug:
        print('Parts panel: no 24-part song, skipped')
        return
    print(f'Parts panel: {slug}')
    ctx = await browser.new_context(device_scale_factor=1)
    await setup(ctx)
    errors = []
    pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, 'parts')
    await pg.evaluate(SPY_JS)
    speakers = "() => [...document.querySelectorAll('#mixParts .tog.hear')].filter(b => b.offsetParent).length"
    # Parts are numbered level by level (Open Strings 0-3, Easy 4-7, Melody 8-11, Harmony 12-15...), violin to bass.
    check(await pg.is_visible('#g-parts') and not await pg.is_visible('#fabRow #g-parts'), 'Parts is a tab at the right edge, not a button in the strip')
    music_right = "() => Math.round(document.getElementById('sheet').getBoundingClientRect().right)"
    closed_right = await pg.evaluate(music_right)
    tab_left, tab_right = await pg.evaluate("() => { const t = document.getElementById('g-parts').getBoundingClientRect(); return [Math.round(t.left), Math.round(t.right)]; }")
    check(tab_left < closed_right < tab_right, f'the music runs a little under the Parts tab (music ends at {closed_right}, tab {tab_left} to {tab_right})')
    await pg.click('#g-parts')
    check(await pg.is_visible('#pop-parts'), 'the Parts tab opens the panel')
    await pg.wait_for_timeout(600)
    over = await pg.evaluate("() => document.getElementById('pop-parts').getBoundingClientRect().left < document.getElementById('sheet').getBoundingClientRect().right")
    check(over and await pg.evaluate(music_right) == closed_right, 'the panel opens over the music, which stays where it is')
    check(await pg.evaluate(SHOWN_JS) == [8], 'a first visit shows Violin, Melody')
    check(await pg.evaluate(speakers) == 0 and await pg.is_checked('#hearSame'), '"Hear the parts I see" starts ticked: eyes only')
    # A violin at Open Strings reading along with a cello at Advanced Melody: those two parts and no others.
    await pg.click('#see-4-2'); await pg.click('#see-0-0'); await pg.click('#see-2-0'); await pg.wait_for_timeout(1500)
    check(await pg.evaluate(SHOWN_JS) == [0, 18], 'eyes on Violin Open Strings and Cello Advanced Melody show just those two, in score order')
    names = await pg.evaluate('() => reader.api.tracks.map(t => t.name)')
    check(names == ['Vln Open str.', 'C Adv. melody'], f'the staves are labelled with the same short names as the table ({names})')
    check(await pg.evaluate(PLAYING_JS) == [0, 18], 'ticked, the parts on the page are the parts that play')
    check(await pg.evaluate("() => document.querySelectorAll('#mixParts .tog.see').length") == 24, 'one eye for every part')
    # In The First Noel: Open Strings has violin with bass and viola with cello; Easy, Melody and Advanced Melody
    # have all four on the tune; Harmony and Obbligato give each instrument its own line.
    if slug == 'the-first-noel':
        same = await pg.evaluate("() => [0, 1, 2, 3, 4, 5].map(t => document.getElementById('same-' + t).textContent)")
        check(same == ['violin & bass have the same notes\nviola & cello have the same notes', 'all parts have the same notes',
                       'all parts have the same notes', '', 'all parts have the same notes', ''],
              f'a line under each level name says which parts play the same notes ({same})')
        said = await pg.get_attribute('#see-0-0', 'title')
        check(said.endswith('(same notes as Bass)'), f'pointing at a part names its match ("{said}")')
    check(not await pg.is_visible('#mixParts .group-rule') and await pg.evaluate("() => document.querySelectorAll('#mixParts .tog.none, #mixParts .mix-div').length") == 0,
          'the six levels: no group rule, no greyed-out cells, no lines between levels')
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
    check(not await pg.is_visible('#pop-parts') and await pg.evaluate(music_right) == closed_right, 'closing the panel leaves the music where it was')
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


VOICE_ROWS = ['Open Strings', 'Easy Melody', 'Easy Inner', 'Easy Bass Line', 'Melody', 'Inner', 'Bass Line',
              'Advanced Melody', 'Advanced Inner', 'Advanced Bass Line']
# The size buttons and Line or Pages (where shown) can be tapped, and don't sit on the Strings key.
TOOLS_CLEAR_JS = """() => {
  const tools = ['zoomOut', 'zoomIn', 'g-layout'].map(id => document.getElementById(id)).filter(b => b.offsetParent);
  const tapped = tools.every(b => { const r = b.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return h && b.contains(h); });
  const key = document.getElementById('legend');
  const keyClear = key.hidden || getComputedStyle(key).visibility === 'hidden' || key.getBoundingClientRect().right <= document.getElementById('topTools').getBoundingClientRect().left;
  return tapped && keyClear;
}"""


def without_low_inner(slug):
    """A 40-part score cut to the 34-part layout (no cello or bass Inner parts), as songs built on 2026-10-16 have."""
    text = (ROOT / 'songs' / slug / f'{slug}.xml').read_text(encoding='utf-8')
    for pid in re.findall(r'<score-part id="([^"]+)">\s*<part-name>(?:Cello|Bass) — (?:Easy |Advanced )?Inner</part-name>', text):
        text = re.sub(rf'<score-part id="{pid}">.*?</score-part>\s*', '', text, flags=re.S)
        text = re.sub(rf'<part id="{pid}">.*?</part>\s*', '', text, flags=re.S)
    return text.encode('utf-8')


async def voices40_checks(browser, base):
    """The Parts panel for a song in levels and voices with every voice on every instrument (40 parts)."""
    slug = next((s['slug'] for s in SONGS if PARTS[s['slug']] == 40), None)
    if not slug:
        print('Parts panel, levels and voices (40 parts): no 40-part song, skipped')
        return
    print(f'Parts panel, levels and voices (40 parts): {slug}')
    key = f'{slug}-reader'
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        errors = []
        pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, 'voices40', w, h)
        await pg.evaluate(SPY_JS)
        await pg.click('#g-parts'); await pg.wait_for_timeout(600)
        names = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .mix-name')].map(n => [...n.children].find(c => c.offsetParent && !c.classList.contains('lvl-same')).textContent)")
        if label == 'laptop':
            check(names == VOICE_ROWS, f'{label}: a row for each level and voice ({names})')
        else:
            check(len(names) == 10 and names[0] == 'Open str.' and names[-1] == 'Adv. bass line', f'{label}: short names on a phone ({names})')
        eyes = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .tog.see')].filter(b => b.offsetParent).map(b => b.classList.contains('none'))")
        check(len(eyes) == 40 and not any(eyes), f'{label}: an eye for every part, cello and bass Inner too, none greyed out')
        rule = (await pg.text_content('#mixParts .group-rule') or '').strip()
        check(await pg.is_visible('#mixParts .group-rule') and rule.startswith('One player on Melody'), f'{label}: the group rule shows over the table ("{rule}")')
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        check(wide <= 1, f'{label}: no sideways scrolling ({wide}px extra)')
        check(await pg.evaluate(TOOLS_CLEAR_JS), f'{label}: with the panel open, the size buttons and Line or Pages sit beside it, clear of the Strings key')
        same = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .lvl-same')].map(s => s.textContent)")
        hint = await pg.get_attribute('#see-0-0', 'title')
        check(same[0] == '' and 'same notes' not in hint and any(same[1:]),
              f'{label}: no same-notes line or hint for Open Strings, while other levels keep theirs ({same[:2]}, "{hint}")')
        if label != 'laptop':
            check(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()
            continue
        check(await pg.evaluate(SHOWN_JS) == [16] and await pg.get_attribute('#g-parts', 'title') == 'Parts: Violin · Melody', 'a first visit shows Violin, Melody')
        # A cello trio at Easy: Melody, Inner and Bass Line.
        await pg.click('#see-1-2'); await pg.click('#see-2-2'); await pg.click('#see-3-2'); await pg.click('#see-4-0'); await pg.wait_for_timeout(1500)
        check(await pg.evaluate(SHOWN_JS) == [6, 10, 14] and await pg.evaluate(PLAYING_JS) == [6, 10, 14], 'eyes on Cello Easy Melody, Easy Inner and Easy Bass Line show and play those three')
        staves = await pg.evaluate('() => reader.api.tracks.map(t => t.name)')
        check(staves == ['Easy melody', 'Easy inner', 'Easy bass line'], f'the staves are labelled with the short names ({staves})')
        await pg.click('#hearSame')
        speakers = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .tog.hear')].filter(b => b.offsetParent).map(b => b.classList.contains('none'))")
        check(len(speakers) == 40 and not any(speakers), 'unticking "Hear the parts I see" shows a speaker for every part')
        await pg.reload()
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        check(await pg.evaluate(SHOWN_JS) == [6, 10, 14], 'the choices are still there after a reload')
        # Saved with the six levels: violin Melody and cello Harmony on the page, violin Melody and Harmony playing.
        await pg.evaluate(f"localStorage.setItem('{key}', JSON.stringify({{ seen: [8, 14], heard: [8, 12], hearOpen: true }}))")
        await pg.reload()
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        await pg.evaluate(SPY_JS)
        await pg.click('#g-parts'); await pg.click('#hear-0-0'); await pg.click('#hear-0-0')
        check(await pg.evaluate(SHOWN_JS) == [16, 26] and await pg.evaluate(PLAYING_JS) == [16, 20],
              'choices saved with the six levels move over (cello Harmony to Bass Line, violin Harmony to Inner)')
        # Saved with 34 parts: Viola Easy Inner, Cello Easy Bass Line, Violin Bass Line keep their names.
        await pg.evaluate(f"localStorage.setItem('{key}', JSON.stringify({{ parts: 'voices', seen: [9, 12, 20] }}))")
        await pg.reload()
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        check(await pg.evaluate(SHOWN_JS) == [9, 14, 24], 'choices saved with 34 parts move to the same parts here')
        check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


async def voices_checks(browser, base):
    """The Parts panel for a song in levels and voices with no cello or bass Inner (34 parts, built 2026-10-16)."""
    slug = next((s['slug'] for s in SONGS if PARTS[s['slug']] == 34), None)
    stand_in = None
    if not slug:
        slug = next((s['slug'] for s in SONGS if PARTS[s['slug']] == 40), None)
        if not slug:
            print('Parts panel, levels and voices (34 parts): no 34- or 40-part song, skipped')
            return
        stand_in = without_low_inner(slug)
        print(f'Parts panel, levels and voices (34 parts): {slug} cut to 34 parts')
    else:
        print(f'Parts panel, levels and voices (34 parts): {slug}')
    key = f'{slug}-reader'
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
        # No offline copy here, so a stand-in score can't be answered from it.
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        if stand_in:
            await ctx.route(f'**/songs/{slug}/{slug}.xml*', lambda r: r.fulfill(body=stand_in, content_type='application/xml'))
        errors = []
        pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, 'voices', w, h)
        await pg.evaluate(SPY_JS)
        await pg.click('#g-parts'); await pg.wait_for_timeout(600)
        names = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .mix-name')].map(n => [...n.children].find(c => c.offsetParent && !c.classList.contains('lvl-same')).textContent)")
        if label == 'laptop':
            check(names == VOICE_ROWS, f'{label}: a row for each level and voice ({names})')
        else:
            check(len(names) == 10 and names[0] == 'Open str.' and names[-1] == 'Adv. bass line', f'{label}: short names on a phone ({names})')
        greyed = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .tog.see.none')].filter(b => b.offsetParent && b.getAttribute('aria-disabled') === 'true').map(b => b.id)")
        check(greyed == ['see-2-2', 'see-2-3', 'see-5-2', 'see-5-3', 'see-8-2', 'see-8-3'], f'{label}: cello and bass Inner cells greyed out in their places ({greyed})')
        check(await pg.evaluate("() => document.querySelectorAll('#mixParts .tog.see:not(.none)').length") == 34, f'{label}: one eye for every part')
        rule = (await pg.text_content('#mixParts .group-rule') or '').strip()
        check(await pg.is_visible('#mixParts .group-rule') and rule.startswith('One player on Melody'), f'{label}: the group rule shows over the table ("{rule}")')
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        check(wide <= 1, f'{label}: no sideways scrolling ({wide}px extra)')
        check(await pg.evaluate(TOOLS_CLEAR_JS), f'{label}: with the panel open, the size buttons and Line or Pages sit beside it, clear of the Strings key')
        if label != 'laptop':
            check(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()
            continue
        check(await pg.evaluate(SHOWN_JS) == [14] and await pg.get_attribute('#g-parts', 'title') == 'Parts: Violin · Melody', 'a first visit shows Violin, Melody')
        await pg.click('#see-5-2', force=True); await pg.wait_for_timeout(300)
        said = await pg.text_content('#toast')
        check(said.startswith('No Inner part for cello') and await pg.evaluate(SHOWN_JS) == [14], f'a tap on a greyed-out cell says why and changes nothing ("{said}")')
        # An Easy trio: the tune on violin, viola inside, cello on the bass.
        await pg.click('#see-1-0'); await pg.click('#see-2-1'); await pg.click('#see-3-2'); await pg.click('#see-4-0'); await pg.wait_for_timeout(1500)
        check(await pg.evaluate(SHOWN_JS) == [4, 9, 12] and await pg.evaluate(PLAYING_JS) == [4, 9, 12], 'eyes on Violin Easy Melody, Viola Easy Inner and Cello Easy Bass Line show and play those three')
        staves = await pg.evaluate('() => reader.api.tracks.map(t => t.name)')
        check(staves == ['Vln Easy melody', 'Vla Easy inner', 'C Easy bass line'], f'the staves are labelled with the short names ({staves})')
        await pg.click('#hearSame')
        speakers = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .tog.hear')].filter(b => b.offsetParent).map(b => b.classList.contains('none'))")
        check(speakers.count(False) == 34 and speakers.count(True) == 6, 'unticking "Hear the parts I see" shows a speaker for every part, greyed out where there is no part')
        await pg.wait_for_timeout(300)
        check(await pg.evaluate(TOOLS_CLEAR_JS), 'the wider panel (with the speakers) still leaves the size buttons and Line or Pages beside it')
        await pg.reload()
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        check(await pg.evaluate(SHOWN_JS) == [4, 9, 12], 'the choices are still there after a reload')
        # Saved with the six levels: violin Melody and cello Harmony on the page, violin Melody and Harmony playing.
        await pg.evaluate(f"localStorage.setItem('{key}', JSON.stringify({{ seen: [8, 14], heard: [8, 12], hearOpen: true }}))")
        await pg.reload()
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        await pg.evaluate(SPY_JS)
        await pg.click('#g-parts'); await pg.click('#hear-0-0'); await pg.click('#hear-0-0')
        check(await pg.evaluate(SHOWN_JS) == [14, 22] and await pg.evaluate(PLAYING_JS) == [14, 18],
              'choices saved with the six levels move over (cello Harmony to Bass Line, violin Harmony to Inner)')
        check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


ONE_LINE = re.compile(r'<part-name>(Violin|Viola|Cello|Bass) — ([^<]+)</part-name>')


def one_line_parts(slug):
    """The instruments and the line's name of a piece with no levels (one line, the same name on each part), or None."""
    found = ONE_LINE.findall((ROOT / 'songs' / slug / f'{slug}.xml').read_text(encoding='utf-8'))
    if not found or len(found) != PARTS[slug] or len({name for _, name in found}) != 1:
        return None
    return [inst for inst, _ in found], found[0][1]


async def one_line_checks(browser, base):
    """The Parts panel for a piece with no levels: one line on some or all of the instruments (Twinkle Harmony: all four)."""
    slug = next((s['slug'] for s in SONGS if PARTS[s['slug']] <= 4 and one_line_parts(s['slug'])), None)
    if not slug:
        print('Parts panel, one line: no such song, skipped')
        return
    insts, line = one_line_parts(slug)
    cols = [i for i, n in enumerate(['Violin', 'Viola', 'Cello', 'Bass']) if n in insts]
    who = ' and '.join([', '.join(i.lower() for i in insts[:-1]), insts[-1].lower()] if len(insts) > 1 else [insts[0].lower()])
    print(f'Parts panel, one line: {slug} ({who})')
    key = f'{slug}-reader'
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        errors = []
        pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, 'one line', w, h)
        await pg.evaluate(SPY_JS)
        check(await pg.evaluate(SHOWN_JS) == [0] and await pg.evaluate("() => document.getElementById('hearSame').checked"),
              f'{label}: a first visit shows the first instrument\'s part ({insts[0]}), with "Hear the parts I see" ticked')
        await pg.click('#g-parts'); await pg.wait_for_timeout(600)
        names = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .mix-name')].map(n => [...n.children].find(c => c.offsetParent && !c.classList.contains('lvl-same')).textContent)")
        heading = (await pg.text_content('#mixParts .mix-h.lvl')).strip()
        check(names == [line] and heading == 'Part', f'{label}: one row, named for the line, headed Part ({names}, "{heading}")')
        greyed = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .tog.see')].filter(b => b.offsetParent).map(b => b.classList.contains('none'))")
        check(greyed == [i not in cols for i in range(4)], f'{label}: an eye for each instrument it is for, the others greyed out in their places ({greyed})')
        check(not await pg.is_visible('#mixParts .group-rule'), f'{label}: no group rule (it is about levels and voices)')
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        check(wide <= 1, f'{label}: no sideways scrolling ({wide}px extra)')
        check(await pg.evaluate(TOOLS_CLEAR_JS), f'{label}: with the panel open, the size buttons and Line or Pages sit beside it, clear of the Strings key')
        if label != 'laptop':
            check(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()
            continue
        if slug == 'twinkle-harmony':
            same = await pg.text_content('#same-0')
            check(same == 'all parts have the same notes', f'the line under the row says all parts have the same notes ("{same}")')
        lede = await pg.evaluate("() => document.querySelector('#infoPop .lede').textContent")
        check(lede.startswith(f'One line, for {who}.'), f'the About box says who the piece is for ("{lede[:40]}")')
        none = next((i for i in range(4) if i not in cols), None)
        if none is not None:
            await pg.click(f'#see-0-{none}', force=True); await pg.wait_for_timeout(300)
            said = await pg.text_content('#toast')
            check(said.startswith(f'No {line} part for ') and said.endswith(f'this piece is for {who}') and await pg.evaluate(SHOWN_JS) == [0],
                  f'a tap on a greyed-out cell says why and changes nothing ("{said}")')
        if len(cols) > 1:
            # The second instrument joins the first, then the first leaves: the staves and the tab follow.
            short = {'Violin': 'Vln', 'Viola': 'Vla', 'Cello': 'C', 'Bass': 'B'}
            await pg.click(f'#see-0-{cols[1]}'); await pg.wait_for_timeout(1500)
            staves = await pg.evaluate('() => reader.api.tracks.map(t => t.name)')
            check(await pg.evaluate(SHOWN_JS) == [0, 1] and await pg.evaluate(PLAYING_JS) == [0, 1] and staves == [short[i] for i in insts[:2]],
                  f'its eye puts the {insts[1].lower()} part on the page too, playing, its staff labelled ({staves})')
            await pg.click(f'#see-0-{cols[0]}'); await pg.wait_for_timeout(1500)
            staves = await pg.evaluate('() => reader.api.tracks.map(t => t.name)')
            title = await pg.get_attribute('#g-parts', 'title')
            check(await pg.evaluate(SHOWN_JS) == [1] and await pg.evaluate(PLAYING_JS) == [1] and staves == [short[insts[1]]]
                  and title == f'Parts: {insts[1]} · {line}', f'and the {insts[0].lower()} part leaves ({staves}, "{title}")')
            await pg.reload()
            await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
            stored = await pg.evaluate(f"() => JSON.parse(localStorage.getItem('{key}') || '{{}}')")
            check(await pg.evaluate(SHOWN_JS) == [1] and stored.get('partsFull', '').startswith('one:'),
                  f"the choice is still there after a reload ({stored.get('partsFull')}, {stored.get('seen')})")
        if slug == 'twinkle-harmony':
            # Saved when Twinkle Harmony was for viola and cello only (2026-10-21): the cello part on the page.
            await pg.evaluate(f"localStorage.setItem('{key}', JSON.stringify({{ parts: 'one:12:Harmony', partsFull: 'one:12:Harmony', seen: [1] }}))")
            await pg.reload()
            await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
            shown = await pg.evaluate(SHOWN_JS)
            check(shown == [insts.index('Cello')], f'a choice saved when it was for viola and cello moves to the same part (cello: {shown})')
        check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


# Stands in for the browser's print window: counts the calls and fires the events a real one fires (or, with quiet,
# none, like a browser that won't print without a fresh tap).
PRINT_STUB_JS = '''(quiet) => { window.__prints = 0;
  window.print = () => { __prints++; if (!quiet) { dispatchEvent(new Event('beforeprint')); dispatchEvent(new Event('afterprint')); } }; }'''
PRINTED_JS = "(n) => __prints > n && document.getElementById('printCover').hidden"
# The copy made for paper, and whether it is what prints. Finger numbers: how many sit inside the note heads (centred
# on them) and how many to the right (starting just after them).
FINGERS_JS = '''(root) => { const f = [...root.querySelectorAll('text.fin')].filter(t => /^[0-4]/.test(t.textContent));
  return { inside: f.filter(t => t.getAttribute('text-anchor') === 'middle').length, right: f.filter(t => t.getAttribute('text-anchor') === 'start').length,
           left: f.filter(t => t.getAttribute('text-anchor') === 'end').length }; }'''
PAPER_JS = '''() => { const FINGERS = ''' + FINGERS_JS + '''; const out = document.getElementById('printOut'), t = (s) => (out.querySelector(s) || {}).textContent;
  return { lines: out.querySelectorAll('.pr-line > svg').length, music: out.querySelectorAll('.pr-line > svg > svg').length,
           counts: out.querySelectorAll('.pr-count').length, parts: t('.pr-parts'), title: t('.pr-title'), key: !!out.querySelector('.key'),
           ready: document.documentElement.classList.contains('print-ready'), fingers: FINGERS(out) }; }'''
# The screen as it is: how the music is laid out and drawn, and where it is scrolled to.
SCREEN_JS = '''() => { const s = document.getElementById('sheet');
  return { line: s.classList.contains('line'), size: reader.api.settings.display.scale, x: Math.round(s.scrollLeft), y: Math.round(window.scrollY) }; }'''
# On paper, every finger number beside a note is clear of the next note (to the right) or the note before (to the left):
# its head, stem, dot, flag, sharp or flat, a rest or a bar line (a corner just touching a note a step higher or lower
# doesn't count). Run with the copy for paper showing (print media); returns the numbers checked and those that touch
# something.
FINGERS_CLEAR_JS = '''() => { const touching = []; let checked = 0;
  for (const svg of document.querySelectorAll('#printOut .pr-line > svg > svg')) {
    const ink = [];
    for (const g of svg.querySelectorAll('g.at')) { const t = g.querySelector(':scope > text'), c = t ? t.textContent.codePointAt(0) : 0;
      const flag = c >= 0xE240 && c <= 0xE24F ? (c % 2 ? -3 : 3) : 0;
      const half = c >= 0xE0A0 && c <= 0xE0FF ? 0.42 : c >= 0xE260 && c <= 0xE26F ? 1.4 : c >= 0xE4E0 && c <= 0xE4FF ? 1 : c === 0xE1E7 ? 0.5 : 0;
      const m = (half || flag) && /translate\\(([-\\d.]+)[ ,]+([-\\d.]+)\\)/.exec(g.getAttribute('transform') || ''); if (!m) continue;
      const x = +m[1], y = +m[2], w = t.getBBox().width;
      ink.push(flag ? { x, r: x + w, t: Math.min(y, y + w * flag), b: Math.max(y, y + w * flag) } : { x, r: x + w, t: y - w * half, b: y + w * half }); }
    for (const r of svg.querySelectorAll('rect')) { const x = +r.getAttribute('x'), y = +r.getAttribute('y'), w = +r.getAttribute('width'), h = +r.getAttribute('height');
      if (w < h / 8) ink.push({ x, r: x + w, t: y, b: y + h }); }
    // Bar numbers, with a little paper after them, so a number beside a bar's first note doesn't read as part of one.
    for (const t of svg.querySelectorAll(':scope > text:not(.fin)')) { const n = t.textContent.trim(); if (!/^\\d+$/.test(n)) continue;
      const b = t.getBBox(); ink.push({ x: b.x, r: b.x + t.getSubStringLength(0, n.length) + b.height * 0.3, t: b.y, b: b.y + b.height }); }
    for (const f of svg.querySelectorAll('text.fin')) {
      const side = f.getAttribute('text-anchor');
      if ((side !== 'start' && side !== 'end') || !/[0-4]/.test(f.textContent)) continue;
      checked++;
      const fs = +f.getAttribute('font-size'), x = +f.getAttribute('x'), y = +f.getAttribute('y'), len = f.getComputedTextLength();
      const box = side === 'end' ? { x: x - len - fs * 0.11, r: x, t: y - fs * 0.72, b: y + fs * 0.05 } : { x, r: x + len + fs * 0.11, t: y - fs * 0.72, b: y + fs * 0.05 };
      if (ink.some(o => o.x < box.r - 0.3 && o.r > box.x + 0.3 && Math.min(o.b, box.b) - Math.max(o.t, box.t) > fs * 0.12)) touching.push(f.textContent);
    } }
  return { checked, touching }; }'''
# How many sheets of Letter paper the print takes (Chromium's own PDF of the print).
MUSIC_JS = """() => reader.score.tracks[0].staves[0].bars.map(b => b.voices[0].beats.map(x => x.isRest ? 'r' : x.notes.map(n => n.realValue).join('+') + ':' + x.duration).join(',')).join('|')"""


async def sight_reading_checks(browser, base):
    """The sight-reading page: the reader with music made on the page for a book page and an exercise number."""
    print('Sight-reading page')
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390), ('iPhone SE landscape', 667, 375)]:
        ctx = await browser.new_context(device_scale_factor=1)
        await setup(ctx)
        errors = []
        try:
            pg = await open_reader(ctx, f'{base}/sight-reading/?page=v1-02&n=7', errors, 'sight-reading', w, h)
        except Exception as e:
            check(False, f'{label}: sight-reading page loads ({e.__class__.__name__})')
            await ctx.close()
            continue
        ck = lambda ok, what: check(ok, f'{label}: {what}')
        title = (await pg.evaluate("() => document.getElementById('infoBtn').firstChild.textContent")).strip()
        ck(title == 'Sight-reading', f'title reads "Sight-reading" ("{title}")')
        got = await pg.evaluate("""() => ({ page: document.getElementById('srPage').value, n: document.getElementById('srNum').value,
          tracks: reader.score.tracks.length, bars: reader.score.masterBars.length, clef: reader.score.tracks[0].staves[0].bars[0].clef,
          look: document.querySelector('#g-look .now .word').textContent, colors: document.querySelector('#g-colors .now').textContent,
          tempo: document.getElementById('tempoChip').textContent, key: document.getElementById('srKey').textContent,
          strings: [...document.querySelectorAll('#legend .key-head')].map(e => e.textContent).join('') })""")
        ck(got['page'] == 'v1-02' and got['n'] == '7', f"book page and number from the address ({got['page']}, {got['n']})")
        ck(got['tracks'] == 1 and got['bars'] == 4, f"one part, four bars ({got['tracks']}, {got['bars']})")
        ck(got['look'] == 'Plain notes' and got['colors'] == 'All', f"starts with string colors and plain notes, as the page says ({got['colors']}, {got['look']})")
        ck(got['tempo'] == '60', f"starts at the page's slowest tempo ({got['tempo']})")
        ck(got['key'] == 'A major' and got['strings'] == 'EADG', f"violin in A major with its strings ({got['key']}, {got['strings']})")
        drawn = await pg.evaluate("() => document.querySelectorAll('#sheet .at-surface > *').length")
        ck(drawn > 0, 'notes are drawn')
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        ck(wide <= 1, f'no sideways scrolling ({wide}px extra)')
        # The row: every control on the screen, above the music, clear of All songs.
        row = await pg.evaluate("""() => { const r = (id) => document.getElementById(id).getBoundingClientRect();
          const ids = ['srPage', 'srViolin', 'srViola', 'srNum', 'srDuet', 'srFlash', 'srNew'], home = r('homeBtn'), surf = document.querySelector('#sheet .at-surface').getBoundingClientRect();
          return { inside: ids.every(id => { const b = r(id); return b.width > 0 && b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= innerHeight; }),
                   above: ids.every(id => r(id).bottom <= surf.top + 1), clear: ids.every(id => { const b = r(id); return b.left >= home.right || b.top >= home.bottom; }) }; }""")
        ck(row['inside'] and row['above'] and row['clear'], f'the row (book page, Violin / Viola, number, Duet, Flash a bar, New exercise) is on the screen over the music ({row})')
        href = await pg.get_attribute('#srFlash', 'href')
        ck(href == 'flash/?page=v1-02', f'Flash a bar opens on the same book page ({href})')
        await pg.click('#play'); await pg.wait_for_timeout(2500)
        tick = await pg.evaluate('() => reader.at()')
        ck(tick > 0, f'Play moves the music forward (tick {round(tick)})')
        await pg.click('#play')
        first = await pg.evaluate(MUSIC_JS)
        await pg.click('#srNew'); await pg.wait_for_timeout(1500)
        n2 = await pg.input_value('#srNum')
        second = await pg.evaluate(MUSIC_JS)
        ck(n2 != '7' and f'n={n2}' in pg.url and second != first, f'New exercise brings new music and its number, in the address too (#{n2}, {pg.url})')
        await pg.click('#play'); await pg.wait_for_timeout(2000)
        tick = await pg.evaluate('() => reader.at()')
        ck(tick > 0, f'the new exercise plays (tick {round(tick)})')
        await pg.click('#play')
        await pg.fill('#srNum', '7'); await pg.press('#srNum', 'Enter'); await pg.wait_for_timeout(1500)
        ck(await pg.evaluate(MUSIC_JS) == first and 'n=7' in pg.url, 'typing a number brings that exercise back')
        await pg.click('#srViola'); await pg.wait_for_timeout(1500)
        got = await pg.evaluate("""() => ({ clef: reader.score.tracks[0].staves[0].bars[0].clef, key: document.getElementById('srKey').textContent,
          strings: [...document.querySelectorAll('#legend .key-head')].map(e => e.textContent).join(''), pressed: document.getElementById('srViola').getAttribute('aria-pressed') })""")
        ck(got['clef'] == 1 and got['key'] == 'D major' and got['strings'] == 'ADGC' and got['pressed'] == 'true',
           f"Viola: alto clef, D major, the viola's strings ({got})")
        viola = await pg.evaluate(MUSIC_JS)
        await pg.reload()
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        await pg.wait_for_timeout(1000)
        again = await pg.evaluate(MUSIC_JS)
        pressed = await pg.get_attribute('#srViola', 'aria-pressed')
        ck(again == viola and pressed == 'true', 'after a reload: still viola, and the same number gives the same music')
        # Another book page starts with its own look again, after the student changed it.
        await pg.click('#g-look'); await pg.wait_for_timeout(1200)
        async with pg.expect_navigation():
            await pg.select_option('#srPage', 'v1-04')
        await pg.wait_for_function("!document.getElementById('play').disabled", timeout=90000)
        await pg.wait_for_timeout(1000)
        look = await pg.evaluate("() => document.querySelector('#g-look .now .word').textContent")
        ck('page=v1-04' in pg.url and look == 'Plain notes', f'another book page opens with its own look ({pg.url}, {look})')
        ck(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


# The whole score: each part's notes, bar by bar (both parts of a duet).
SCORE_JS = """() => reader.score.tracks.map(t => t.name.replace(/^.*?(Part \\d)$/, '$1') + '=' + t.staves[0].bars.map(b => b.voices[0].beats.map(x => x.isRest ? 'r' : x.notes.map(n => n.realValue).join('+') + ':' + x.duration).join(',')).join('|')).join(' / ')"""
# The parts on the page (drawn), and the duet's facts.
DUET_JS = """() => ({ drawn: reader.api.tracks.map(t => t.index), tracks: reader.score.tracks.length, labels: reader.api.tracks.map(t => t.name),
  rows: [...document.querySelectorAll('#mixParts .mix-name .lvl-long')].map(e => e.textContent),
  hear: [...document.querySelectorAll('#mixParts .tog.hear:not(.none)')].map(b => b.getAttribute('aria-pressed')),
  hearSame: document.getElementById('hearSame').checked, url: location.search, src: document.getElementById('srSource').textContent,
  clefs: reader.score.tracks.map(t => t.staves[0].bars[0].clef), fifths: reader.score.tracks.map(t => t.staves[0].bars[0].keySignature),
  duet: document.getElementById('srDuet').getAttribute('aria-pressed'), instOff: document.getElementById('srInst').classList.contains('off'),
  mine: [1, 2].map(k => document.getElementById('srMine' + k).getAttribute('aria-pressed')) })"""
# Look ahead with both parts of a duet on the page: which notes are covered, in which part.
DUET_LOOK_JS = """() => { const l = reader.look(); if (!l || l.t == null) return null;
  const surf = document.querySelector('#sheet .at-surface').getBoundingClientRect(), sc = reader.score, out = [];
  for (const t of reader.api.tracks) for (const bar of t.staves[0].bars) for (const b of bar.voices[0].beats) {
    const g = document.querySelector('g.b' + b.id); if (!g) continue;
    const r = g.getBoundingClientRect(), x = (r.left + r.right) / 2 - surf.left, y = (r.top + r.bottom) / 2 - surf.top;
    const band = l.bands.find(d => y >= d.top && y <= d.bottom);
    out.push({ part: t.index, tick: sc.masterBars[bar.index].start + b.playbackStart, covered: !!band && x < band.cut });
  }
  return { H: l.H, t: l.t, beats: out }; }"""


async def duet_checks(browser, base):
    """Duets on the sight-reading page (round 5): two devices with one exercise number read the same duet, each its own
    part; the Duet card; Look ahead hides only the part this device plays."""
    print('Sight-reading: duets')
    url = f'{base}/sight-reading/?page=v1-03&n=321&duet=violin-viola&part2=same'
    devices = []
    for label, w, h, part in [('teacher laptop', 1366, 860, 2), ('student phone landscape', 844, 390, 1)]:
        ctx = await browser.new_context(device_scale_factor=1)
        await setup(ctx)
        await ctx.add_init_script(f"try {{ if (!sessionStorage.getItem('set')) {{ sessionStorage.setItem('set', 1); localStorage.setItem('sight-reading', JSON.stringify({{ part: {part} }})); }} }} catch (e) {{}}")
        errors = []
        try:
            pg = await open_reader(ctx, url, errors, 'duet ' + label, w, h)
        except Exception as e:
            check(False, f'duet, {label}: page loads ({e.__class__.__name__})')
            await ctx.close()
            continue
        devices.append((label, ctx, pg, errors, part))
    if len(devices) < 2:
        for d in devices:
            await d[1].close()
        return
    music = [await pg.evaluate(SCORE_JS) for _, _, pg, _, _ in devices]
    check(music[0] == music[1] and 'Part 1=' in music[0] and 'Part 2=' in music[0],
          f'two devices with one exercise number and the same duet choices get the same duet ({len(music[0])} characters of music each)')
    for label, ctx, pg, errors, part in devices:
        ck = lambda ok, what: check(ok, f'duet, {label}: {what}')
        got = await pg.evaluate(DUET_JS)
        ck(got['tracks'] == 2 and got['clefs'] == [4, 1] and got['fifths'] == [3, 3],  # alphaTab's clefs: 4 treble (G2), 1 alto (C3)
           f"two parts, violin (treble clef) over viola (alto clef), both in Part 1's key ({got['tracks']}, {got['clefs']}, {got['fifths']})")
        ck(got['drawn'] == [part - 1] and got['mine'] == (['true', 'false'] if part == 1 else ['false', 'true']),
           f"the page shows the part this device plays, Part {part} ({got['drawn']}, I play {got['mine']})")
        ck(got['hear'] == ['true', 'true'] and not got['hearSame'], f"both parts play (Hear: {got['hear']}, Hear the parts I see: {got['hearSame']})")
        ck(got['rows'] == ['Part 1', 'Part 2'], f"the Parts table has Part 1 and Part 2 ({got['rows']})")
        ck(got['labels'] == [('Vln Part 1' if part == 1 else 'Vla Part 2')], f"the staff is labelled with its part ({got['labels']})")
        ck('Duet for violin and viola, Part 2 on this page' in got['src'] and got['duet'] == 'true' and got['instOff'],
           f"the details say it is a duet, the Duet button is on and Violin / Viola is greyed out ({got['src']})")
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        ck(wide <= 1, f'no sideways scrolling ({wide}px extra)')
        await pg.click('#play'); await pg.wait_for_timeout(2000)
        tick = await pg.evaluate('() => reader.at()')
        ck(tick > 0, f'the duet plays (tick {round(tick)})')
        await pg.click('#play')
    # The teacher's laptop: the Duet card, I play, Look ahead on my part only, Solo and back.
    label, ctx, pg, errors, _ = devices[0]
    ck = lambda ok, what: check(ok, f'duet, {label}: {what}')
    await pg.click('#srDuet'); await pg.wait_for_timeout(300)
    card = await pg.evaluate("""() => { const b = document.getElementById('srDuetPop').getBoundingClientRect();
      return { open: !document.getElementById('srDuetPop').hidden, inside: b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= innerHeight } }""")
    ck(card['open'] and card['inside'], f'the Duet card opens on the screen ({card})')
    await pg.click('#srMine1'); await pg.wait_for_timeout(1500)
    got = await pg.evaluate(DUET_JS)
    ck(got['drawn'] == [0] and got['hear'] == ['true', 'true'], f"I play Part 1: the page shows Part 1, both still play ({got['drawn']}, {got['hear']})")
    await pg.click('#srDuetX')
    # Both parts on the page, then Look ahead: only Part 1 (mine) vanishes.
    await pg.click('#g-parts'); await pg.wait_for_timeout(500)
    await pg.click('#see-1-1'); await pg.wait_for_timeout(1500)
    await pg.click('#g-parts'); await pg.wait_for_timeout(400)
    ck((await pg.evaluate(DUET_JS))['drawn'] == [0, 1], 'Parts puts the other part on the page too')
    await pg.evaluate("() => { const t = document.getElementById('tempo'); t.value = 90; t.dispatchEvent(new Event('input')); }")
    while 'level 3' not in (await pg.get_attribute('#g-ahead', 'aria-label') or ''):
        await pg.click('#g-ahead')
    while (await pg.text_content('#g-metro .now')) != 'Off':
        await pg.click('#g-metro')
    await pg.click('#restart'); await pg.click('#play')
    problems, samples = [], 0
    for ms in (1500, 1200, 1500):
        await pg.wait_for_timeout(ms)
        st = await pg.evaluate(DUET_LOOK_JS)
        if not st:
            problems.append('no cover'); continue
        samples += 1
        mine = [b for b in st['beats'] if b['part'] == 0 and abs(b['tick'] - st['H']) > 40]
        other = [b for b in st['beats'] if b['part'] == 1]
        if any(b['covered'] != (b['tick'] <= st['H']) for b in mine):
            problems.append(f"Part 1's notes covered wrongly at {round(st['t'])}")
        if any(b['covered'] for b in other):
            problems.append(f"Part 2's notes covered at {round(st['t'])}")
    await pg.click('#play')
    ck(not problems and samples == 3, f"Look ahead hides Part 1's notes as they come and never Part 2's ({samples} checks{': ' + '; '.join(problems) if problems else ''})")
    while (await pg.get_attribute('#g-ahead', 'aria-label') or '').find('Off') < 0 and 'level' in (await pg.get_attribute('#g-ahead', 'aria-label') or ''):
        await pg.click('#g-ahead')
    # The card's choices change the music and the address: Part 2 on viola to violin, Part 2 open strings.
    await pg.click('#srDuet'); await pg.wait_for_timeout(300)
    before = await pg.evaluate(SCORE_JS)
    await pg.click('#srP2violin'); await pg.wait_for_timeout(1500)
    got = await pg.evaluate(DUET_JS)
    ck('duet=violin-violin' in got['url'] and got['clefs'] == [4, 4] and 'two violins' in got['src'], f"Part 2 on violin: two violins, in the address too ({got['url']}, {got['clefs']})")
    await pg.select_option('#srLevel', 'open'); await pg.wait_for_timeout(1500)
    got = await pg.evaluate(DUET_JS)
    ck('part2=open' in got['url'] and 'Part 2 on open strings' in got['src'], f"Part 2 on open strings, in the address too ({got['url']})")
    first = (await pg.evaluate(SCORE_JS)).split(' / ')[0]
    ck(first == before.split(' / ')[0], 'Part 1 stays the same exercise whatever Part 2 is')
    levels = await pg.evaluate("() => [...document.getElementById('srLevel').options].map(o => o.value)")
    ck(levels == ['same', 'v1-01', 'v1-02', 'open', 'harder'] or levels == ['same', 'open', 'v1-01', 'v1-02', 'harder'],
       f'Part 2 can be on this page, an earlier page, open strings or harder ({levels})')
    await ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
    await pg.click('#srCopy'); await pg.wait_for_timeout(300)
    link = await pg.evaluate('() => navigator.clipboard.readText()')
    ck(link.endswith(got['url']) and '/sight-reading/' in link, f'Copy the link copies this duet ({link})')
    await pg.click('#srSolo'); await pg.wait_for_timeout(1500)
    got = await pg.evaluate(DUET_JS)
    ck(got['tracks'] == 1 and 'duet=' not in got['url'] and got['duet'] == 'false' and not got['instOff'],
       f"Solo: one part again, and the address drops the duet ({got['tracks']}, {got['url']})")
    await pg.click('#srDuetOn'); await pg.wait_for_timeout(1500)
    got = await pg.evaluate(DUET_JS)
    ck('duet=violin-violin' in got['url'] and 'part2=open' in got['url'], f"Duet again: the last duet choices come back ({got['url']})")
    for label, ctx, pg, errors, _ in devices:
        check(not errors, f'duet, {label}: no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()
    # An iPhone SE turned sideways: the row and the card fit.
    ctx = await browser.new_context(device_scale_factor=1)
    await setup(ctx)
    errors = []
    try:
        pg = await open_reader(ctx, url, errors, 'duet SE', 667, 375)
        await pg.click('#srDuet'); await pg.wait_for_timeout(300)
        fit = await pg.evaluate("""() => { const r = (id) => document.getElementById(id).getBoundingClientRect(), ids = ['srPage', 'srViolin', 'srViola', 'srNum', 'srDuet', 'srFlash', 'srNew', 'srCopy'];
          return { inside: ids.every(id => { const b = r(id); return b.width > 0 && b.left >= 0 && b.right <= innerWidth && b.top >= 0 && b.bottom <= innerHeight; }), page: r('srPage').width } }""")
        check(fit['inside'] and fit['page'] > 90, f'duet, iPhone SE landscape: the row and the Duet card fit on the screen ({fit})')
        check(not errors, 'duet, iPhone SE landscape: no script errors' + (f': {errors[:3]}' if errors else ''))
    except Exception as e:
        check(False, f'duet, iPhone SE landscape: page loads ({e.__class__.__name__})')
    await ctx.close()


LOOK_JS = """() => { const l = reader.look(); if (!l || l.t == null) return null;
  const surf = document.querySelector('#sheet .at-surface').getBoundingClientRect(), sc = reader.score, out = [];
  for (const bar of sc.tracks[0].staves[0].bars) for (const b of bar.voices[0].beats) {
    const g = document.querySelector('g.b' + b.id); if (!g) continue;
    const r = g.getBoundingClientRect(), x = (r.left + r.right) / 2 - surf.left, y = (r.top + r.bottom) / 2 - surf.top;
    const band = l.bands.find(d => y >= d.top && y <= d.bottom);
    out.push({ tick: sc.masterBars[bar.index].start + b.playbackStart, covered: !!band && x < band.cut });
  }
  return { H: l.H, t: l.t, at: reader.at(), beats: out, lines: document.querySelectorAll('.look-layer g > rect').length - l.bands.length,
           cuts: l.bands.map(b => b.cut - b.left), counting: !document.getElementById('count').hidden }; }"""
AHEAD_TICKS = {'Level 1': 480, 'Level 2': 960, 'Level 3': 3840}  # half a beat, a beat and a bar, in 4/4
AHEAD_SAY = {'Level 1': 'level 1: each note vanishes half a beat', 'Level 2': 'level 2: each note vanishes one beat',
             'Level 3': 'level 3: each note vanishes a bar'}  # its button's label


async def look_ahead_checks(browser, base):
    """Look ahead on the sight-reading page: notes vanish the chosen time before they are heard."""
    print('Sight-reading: Look ahead')
    for label, w, h, pages in [('laptop, one long line', 1366, 860, False), ('laptop, pages', 1366, 860, True), ('phone landscape', 844, 390, False)]:
        ctx = await browser.new_context(device_scale_factor=1)
        await setup(ctx)
        errors = []
        try:
            pg = await open_reader(ctx, f'{base}/sight-reading/?page=v1-03&n=40', errors, 'look ahead', w, h)
        except Exception as e:
            check(False, f'{label}: Look ahead page loads ({e.__class__.__name__})')
            await ctx.close()
            continue
        ck = lambda ok, what: check(ok, f'{label}: {what}')
        if pages:
            await pg.click('#g-layout'); await pg.wait_for_timeout(2000)
        await pg.evaluate("() => { const t = document.getElementById('tempo'); t.value = 90; t.dispatchEvent(new Event('input')); }")
        await pg.click('#g-ahead')
        got = await pg.evaluate("() => ({ label: document.getElementById('g-ahead').getAttribute('aria-label'), metro: document.querySelector('#g-metro .now').textContent, tempo: document.getElementById('tempoChip').textContent })")
        ck('level 1: each note vanishes half a beat' in got['label'] and got['metro'] == 'Count-in only' and got['tempo'] == '60',
           f"turning Look ahead on brings a count-in and the page's tempo ({got})")
        problems, samples = [], 0
        for setting in ['Level 1', 'Level 2', 'Level 3']:
            while AHEAD_SAY[setting] + ' ' not in await pg.get_attribute('#g-ahead', 'aria-label'):
                await pg.click('#g-ahead')
            for tempo in (60, 120):
                await pg.evaluate("(v) => { const t = document.getElementById('tempo'); t.value = v; t.dispatchEvent(new Event('input')); }", tempo)
                # The first run of each setting counts in (and is checked during the count-in); the others start at once.
                count_in = tempo == 60
                while (await pg.text_content('#g-metro .now')) != ('Count-in only' if count_in else 'Off'):
                    await pg.click('#g-metro')
                await pg.click('#restart')
                await pg.click('#play')
                beat_ms = 60000 / tempo
                waits = ([beat_ms * 2.6] if count_in else []) + [beat_ms * (5.3 if count_in else 1.3), beat_ms * 1.1, beat_ms * 1.7]
                for ms in waits:
                    await pg.wait_for_timeout(ms)
                    st = await pg.evaluate(LOOK_JS)
                    if not st:
                        problems.append(f'{setting} at {tempo}: no cover'); continue
                    samples += 1
                    want = AHEAD_TICKS[setting]
                    if abs(st['H'] - st['t'] - want) > 40:
                        problems.append(f"{setting} at {tempo}: notes vanish {round(st['H'] - st['t'])} ticks ahead, not {want}")
                    if not st['counting'] and abs(st['t'] - st['at']) > 0.06 * tempo * 16:
                        problems.append(f"{setting} at {tempo}: the cover's clock {round(st['t'])} is not the heard one {round(st['at'])}")
                    wrong = [b for b in st['beats'] if abs(b['tick'] - st['H']) > 40 and b['covered'] != (b['tick'] <= st['H'])]
                    if wrong:
                        problems.append(f"{setting} at {tempo}: {len(wrong)} note(s) covered wrongly at heard {round(st['t'])} (e.g. {wrong[0]})")
                    if any(st['cuts']) and st['lines'] < 5:
                        problems.append(f"{setting} at {tempo}: staff lines not drawn over the cover ({st['lines']})")
                await pg.click('#play')
                await pg.wait_for_timeout(400)
                back = await pg.evaluate('() => reader.look().bands.every(b => b.cut === b.left)')
                if not back:
                    problems.append(f'{setting} at {tempo}: the notes did not come back when the music stopped')
        ck(not problems and samples >= 18, f'at levels 1, 2 and 3 (½ beat, 1 beat, 1 bar), at 60 and 120, the right notes vanish while it plays, and come back when it stops ({samples} checks{": " + "; ".join(problems[:4]) if problems else ""})')
        ck(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


async def flash_round(pg, answer):
    """One round of Flash a bar, in the order it should go; returns the phases seen and whether each button was usable
    only when it applies."""
    seen, wrong = [], []
    await pg.click('#start')
    t0 = time.monotonic()
    while time.monotonic() - t0 < 15:
        st = await pg.evaluate("""() => ({ ...flash.state(), start: !document.getElementById('start').disabled,
          got: !document.getElementById('gotIt').disabled, no: !document.getElementById('notYet').disabled })""")
        tag = st['phase'] + ('/hidden' if st['covered'] else '/shown')
        if not seen or seen[-1] != tag:
            seen.append(tag)
        if st['start'] or (st['got'] != (st['phase'] == 'check')) or (st['no'] != (st['phase'] == 'check')):
            wrong.append(tag)
        if st['phase'] == 'check':
            break
        await pg.wait_for_timeout(15)
    await pg.click('#gotIt' if answer else '#notYet')
    await pg.wait_for_function("() => flash.state().phase === 'ready' && flash.state().drawn", timeout=15000)
    return seen, wrong


async def flash_checks(browser, base):
    """Flash a bar: a pattern shows, hides, and the student plays it from that glance."""
    print('Sight-reading: Flash a bar')
    for label, w, h in [('laptop', 1366, 860), ('iPad upright', 820, 1180), ('phone landscape', 844, 390), ('phone upright', 390, 844)]:
        ctx = await browser.new_context(device_scale_factor=1, viewport={'width': w, 'height': h})
        await setup(ctx)
        await ctx.add_init_script("try { localStorage.setItem('gsa-flash-fast', '1'); } catch (e) {}")  # every wait ten times shorter
        errors = []
        pg = await ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        ck = lambda ok, what: check(ok, f'Flash a bar, {label}: {what}')
        try:
            await pg.goto(f'{base}/sight-reading/flash/?page=v1-02')
            await pg.wait_for_function("() => window.flash && flash.state().phase === 'ready' && flash.state().drawn", timeout=60000)
        except Exception as e:
            ck(False, f'page loads ({e.__class__.__name__})')
            await ctx.close()
            continue
        fit = await pg.evaluate("""() => { const m = document.getElementById('music').getBoundingClientRect(), s = document.querySelector('#score .at-surface svg');
          const r = document.getElementById('score').getBoundingClientRect();
          return { svg: !!s, inside: r.left >= m.left - 1 && r.right <= m.right + 1 && r.top >= m.top - 1 && r.bottom <= m.bottom + 1, wide: document.documentElement.scrollWidth - innerWidth,
                   buttons: ['notYet', 'start', 'gotIt'].map(id => { const b = document.getElementById(id).getBoundingClientRect(); return b.bottom <= innerHeight + 1 && b.width > 60; }) }; }""")
        ck(fit['svg'] and fit['inside'] and fit['wide'] <= 1 and all(fit['buttons']), f'the pattern is drawn inside its card, and the three buttons are on the screen ({fit})')
        seen, wrong = await flash_round(pg, True)
        order = ['flash/shown', 'flash/hidden', 'count/hidden', 'play/hidden', 'check/shown']
        ck([x for x in seen if x in order] == order or [x for x in seen if x in order] == order[:2] + order[:2] + order[2:], f'a round goes look, hide, count in, play, check ({seen})')
        ck(not wrong, f'Start, Got it and Not yet are usable only when they apply ({wrong[:3]})')
        st = await pg.evaluate('() => flash.state()')
        ck(st['streak'] == 1 and st['best'] == 1, f"Got it counts the streak ({st['streak']}, best {st['best']})")
        if label == 'laptop':
            for _ in range(2):
                await flash_round(pg, True)
            st = await pg.evaluate("() => ({ ...flash.state(), toast: document.getElementById('toast').textContent, lv: document.getElementById('level').textContent })")
            ck(st['level'] == 1 and st['streak'] == 3 and 'Level up' in st['toast'] and st['lv'].startswith('Level 2'), f"three in a row move up a level ({st['lv']}, {st['toast']})")
            await pg.reload()
            await pg.wait_for_function("() => window.flash && flash.state().phase === 'ready' && flash.state().drawn", timeout=60000)
            st = await pg.evaluate('() => flash.state()')
            ck(st['level'] == 1 and st['streak'] == 3 and st['best'] == 3, f"the level, streak and best stay after a reload ({st['level']}, {st['streak']}, {st['best']})")
            await flash_round(pg, False)
            st = await pg.evaluate('() => flash.state()')
            ck(st['streak'] == 0 and st['best'] == 3, f"Not yet starts the streak again, the best stays ({st['streak']}, {st['best']})")
            await pg.click('#lvDown'); await pg.wait_for_timeout(300)
            down = await pg.evaluate('() => flash.state().level')
            await pg.click('#lvUp'); await pg.wait_for_timeout(300)
            up = await pg.evaluate('() => flash.state().level')
            ck(down == 0 and up == 1, f'− and + change the level ({down}, {up})')
            await pg.click('#flViola')
            await pg.wait_for_function("() => flash.state().phase === 'ready' && flash.state().drawn", timeout=15000)
            inst = await pg.evaluate("() => JSON.parse(localStorage.getItem('sight-reading') || '{}').inst")
            clef = await pg.evaluate("() => [...document.querySelectorAll('#score text')].some(t => t.textContent.codePointAt(0) === 0xE05C)")
            ck(inst == 'viola' and clef, f'Viola: kept with the sight-reading page, in alto clef ({inst}, alto clef {clef})')
        ck(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


MIC_STUB = """window.__mistakes = {};
window.flashMicStub = (round) => {
  const lat = 0.15, sr = 48000, start = round.t0 - 0.3, m = window.__mistakes;
  const clicks = round.clicks.map((t, i) => ({ t: t - start + lat, strong: i % 4 === 0 }));
  let notes;
  if (round.kind === 'timing') notes = round.playOn.map(t => ({ midi: 69, t: t - start + lat + 0.01, dur: round.beat * 0.7 }));
  else {
    const p = round.pattern;
    notes = p.midis.map((midi, i) => ({ midi: midi + (m.wrong === i ? 1 : 0), t: round.T0 + p.starts[i] * round.beat - start + lat + (m.late === i ? 0.35 * round.beat : 0),
      dur: ((p.starts[i + 1] ?? p.beats) - p.starts[i]) * round.beat - (m.late === i ? 0.35 * round.beat : 0) }));
  }
  const end = (round.kind === 'timing' ? round.clicks[7] : round.T0 + round.pattern.beats * round.beat) - start + 1;
  return { samples: ListenTakes.take({ notes, clicks, length: end, seed: 5 }), sampleRate: sr, start };
};"""


async def listen_checks(browser, base):
    """Flash a bar's Listen, with no microphone and with a made-up one."""
    print('Sight-reading: Flash a bar, Listen')
    ck = lambda ok, what: check(ok, f'Listen: {what}')
    ready = "() => window.flash && flash.state().phase === 'ready' && flash.state().drawn"
    # No microphone in this browser: Listen says so and stays off.
    ctx = await browser.new_context(device_scale_factor=1, viewport={'width': 1366, 'height': 860})
    await setup(ctx)
    pg = await ctx.new_page()
    await pg.goto(f'{base}/sight-reading/flash/?page=v1-02')
    await pg.wait_for_function(ready, timeout=60000)
    await pg.click('#listen')
    await pg.wait_for_timeout(1500)
    st = await pg.evaluate("() => ({ on: flash.state().listen, toast: document.getElementById('toast').textContent })")
    ck(not st['on'] and 'microphone' in st['toast'], f"with no microphone it says so and stays off ({st})")
    await ctx.close()
    # A made-up microphone (the round's own sound, made by tests/listen_takes.js).
    ctx = await browser.new_context(device_scale_factor=1, viewport={'width': 1366, 'height': 860})
    await setup(ctx)
    await ctx.add_init_script("localStorage.setItem('sight-reading-flash', JSON.stringify({ level: { 'v1-02': 3 } }));")  # 1 second, one look
    await ctx.add_init_script(MIC_STUB)
    errors = []
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errors.append(str(e)))
    await pg.goto(f'{base}/sight-reading/flash/?page=v1-02')
    await pg.add_script_tag(url=f'{base}/tests/listen_takes.js')
    await pg.wait_for_function(ready, timeout=60000)
    await pg.click('#listen')
    await pg.wait_for_function(ready, timeout=15000)
    st = await pg.evaluate("() => ({ say: document.getElementById('say').textContent, label: document.getElementById('startLbl').textContent, on: flash.state().listen })")
    ck(st['on'] and 'Timing check' in st['say'] and st['label'] == 'Check', f"turned on, it asks for the timing check first ({st})")
    await pg.click('#start')
    await pg.wait_for_function("() => flash.state().offset != null", timeout=40000)
    await pg.wait_for_function(ready, timeout=15000)
    off = await pg.evaluate('() => flash.state().offset')
    ck(0.1 < off < 0.3, f'the timing check finds the delay (made up as 0.15 s; read {round(off, 3)} s)')
    for mistakes, want in [({}, 'right'), ({'wrong': 1, 'late': 0}, 'mistakes')]:
        await pg.evaluate('(m) => { window.__mistakes = m; }', mistakes)
        await pg.click('#start')
        await pg.wait_for_function("() => flash.state().phase === 'check'", timeout=40000)
        await pg.wait_for_timeout(300)
        st = await pg.evaluate('() => flash.state()')
        n = len(st['pattern']['midis'])
        if want == 'right':
            ck(st['marks'] == ['mark right:✓'] * n and 'Every note right' in (st['heard'] or ''), f"a round played as written: a tick on every note ({st['marks']}, {st['heard']})")
        else:
            ck('mark wrong:✗' in st['marks'] and 'when:late' in st['marks'], f"a wrong note gets a cross, a late one 'late' ({st['marks']}, {st['heard']})")
        await pg.click('#gotIt')
        await pg.wait_for_function(ready, timeout=15000)
    await pg.reload()
    await pg.add_script_tag(url=f'{base}/tests/listen_takes.js')
    await pg.wait_for_function(ready, timeout=60000)
    st = await pg.evaluate("() => ({ on: flash.state().listen, offset: flash.state().offset, label: document.getElementById('listenLbl').textContent })")
    ck(st['on'] and st['offset'] == off and st['label'] == 'Listening', f'after a reload Listen is still on, with its timing ({st})')
    ck(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
    await ctx.close()


async def sheets_printed(pg):
    pdf = await pg.pdf(format='Letter', prefer_css_page_size=True, print_background=True)
    return len(re.findall(rb'/Type\s*/Page(?![a-zA-Z])', pdf))


# In print, only the copy for paper shows, a line of music never splits across two sheets, and it fits the paper.
PRINT_VIEW_JS = '''() => { const out = document.getElementById('printOut'), lines = [...out.querySelectorAll('.pr-line')];
  return { page: getComputedStyle(document.querySelector('.page')).display, out: getComputedStyle(out).display,
           whole: lines.every(l => getComputedStyle(l).breakInside === 'avoid' && l.offsetHeight > 20),
           fits: lines.every(l => l.getBoundingClientRect().right <= document.documentElement.clientWidth + 1) }; }'''


async def print_checks(browser, base):
    """Print: the music on the page drawn for paper, a line of music at a time, then the screen just as it was."""
    song = SONGS[0]
    slug = song['slug']
    print(f'Print: {slug}')
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390), ('small phone landscape', 667, 375)]:
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        if label != 'laptop':  # like an iPhone: no Full screen button
            await ctx.add_init_script("for (const k of ['fullscreenEnabled', 'webkitFullscreenEnabled']) Object.defineProperty(Document.prototype, k, { get: () => false });")
        errors = []
        pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, 'print', w, h)
        # Beside the size buttons at the top, so the strip at the bottom keeps its one row on a phone.
        where = await pg.evaluate("() => { const b = document.getElementById('printBtn'); return !!b.offsetParent && !!b.closest('#topTools'); }")
        rows = await pg.evaluate("() => new Set([...document.querySelectorAll('#fabRow .fab-btn, #fabRow .play')].filter(e => e.offsetParent).map(e => Math.round(e.getBoundingClientRect().top))).size")
        check(where and rows == 1, f'{label}: the Print button sits at the top beside the size buttons, and the strip stays one row ({rows} rows)')
        await pg.evaluate(PRINT_STUB_JS, False)
        # A small phone's line settles on its size at the next drawing after the first (as it always has): draw it again
        # first (string colors round to where they were), so the size compared is the settled one.
        await pg.evaluate(DRAWS_JS)
        for _ in range(3):
            await click_drawn(pg, '#g-colors')
        await pg.evaluate("() => { const s = document.getElementById('sheet'); s.scrollLeft = s.scrollWidth / 3; }")
        await pg.wait_for_timeout(300)
        before = await pg.evaluate(SCREEN_JS)
        await pg.click('#printBtn')
        try:
            await pg.wait_for_function(PRINTED_JS, arg=0, timeout=30000)
            printed = True
        except Exception:
            printed = False
        await pg.wait_for_timeout(300)
        paper = await pg.evaluate(PAPER_JS)
        check(printed and paper['ready'] and paper['lines'] > 1 and paper['music'] == paper['lines'] and paper['counts'] > 0
              and paper['parts'] == 'Violin — Melody' and paper['title'] == song['title'] and paper['key'],
              f'{label}: Print makes a copy for paper, a line of music at a time with its counts, under the parts, the title and the Strings key, and prints it ({paper})')
        after = await pg.evaluate(SCREEN_JS)
        check(after == before, f'{label}: then the music on the screen is just as it was (one long line, same size, same place: {before}, then {after})')
        if label == 'laptop':
            # A laptop starts on Fingers inside; on paper the finger numbers go beside the notes, to the left (Janelle,
            # 2026-10-30 and 2026-11-02).
            screen = await pg.evaluate('() => (' + FINGERS_JS + ")(document.getElementById('sheet'))")
            check(paper['fingers']['left'] > 0 and not paper['fingers']['inside'] and not paper['fingers']['right'] and screen['inside'] > 0,
                  f"on paper every finger number sits to the left of its note, while the screen keeps them inside (paper {paper['fingers']}, screen {screen})")
        await pg.emulate_media(media='print')
        view = await pg.evaluate(PRINT_VIEW_JS)
        clear = await pg.evaluate(FINGERS_CLEAR_JS)
        await pg.emulate_media(media='screen')
        check(view['page'] == 'none' and view['out'] == 'block' and view['whole'] and view['fits'],
              f'{label}: on paper only the music prints, each line of music whole and inside the paper ({view})')
        check(clear['checked'] > 0 and not clear['touching'],
              f"{label}: on paper every finger number is clear of the next note ({clear['checked']} checked, touching: {clear['touching'][:6]})")
        if label != 'laptop':
            check(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()
            continue
        await pg.keyboard.press('Control+p')
        try:
            await pg.wait_for_function(PRINTED_JS, arg=1, timeout=30000)
            keyed = True
        except Exception:
            keyed = False
        check(keyed, 'Ctrl+P prints the same way')
        # Pages, scrolled down: printing leaves the page where it was.
        await pg.click('#g-layout'); await pg.wait_for_timeout(1500)
        await pg.evaluate('() => window.scrollTo(0, 1500)'); await pg.wait_for_timeout(300)
        before = await pg.evaluate(SCREEN_JS)
        await pg.click('#printBtn')
        await pg.wait_for_function(PRINTED_JS, arg=2, timeout=30000)
        await pg.wait_for_timeout(300)
        after = await pg.evaluate(SCREEN_JS)
        check(after == before, f'on pages, printing leaves the music as it was, scrolled to the same place ({before}, then {after})')
        # The browser's own Print menu after a change (Counting off): on pages, a fresh copy of the music as it is.
        await pg.click('#g-count'); await pg.wait_for_timeout(1500)
        await pg.evaluate("() => dispatchEvent(new Event('beforeprint'))")
        menu = await pg.evaluate(PAPER_JS)
        check(menu['ready'] and menu['lines'] > 1 and menu['counts'] == 0, f"the browser's own Print menu on pages prints the music as it is now (no counts: {menu['counts']})")
        # In one long line it can't make one: the page prints as it is, not the copy made for other choices.
        await pg.click('#g-layout'); await pg.wait_for_timeout(1500)
        await pg.click('#g-count'); await pg.wait_for_timeout(1500)
        await pg.evaluate("() => dispatchEvent(new Event('beforeprint'))")
        check(not (await pg.evaluate(PAPER_JS))['ready'], "in one long line the browser's own Print menu doesn't print a copy made for other choices")
        # A browser that doesn't open its print window after the music is drawn for paper: a card offers a fresh tap.
        await pg.evaluate(PRINT_STUB_JS, True)
        await pg.click('#printBtn')
        await pg.wait_for_function("() => !document.getElementById('printActs').hidden", timeout=30000)
        said = await pg.text_content('#printMsg')
        await pg.click('#printGo')
        check(said == 'The music is ready to print.' and await pg.evaluate('() => __prints') == 2 and await pg.evaluate("() => document.getElementById('printCover').hidden"),
              f'where the print window doesn\'t open by itself, a card says the music is ready and its Print button prints ("{said}")')
        # Fingers to the left on the page: on paper too, every number clear of the note before (Janelle, 2026-11-02).
        await pg.evaluate(PRINT_STUB_JS, False)
        while (await pg.text_content('#g-look .now .word')).strip() != 'Fingers to the left':
            await pg.click('#g-look'); await pg.wait_for_timeout(1500)
        await pg.click('#printBtn')
        await pg.wait_for_function(PRINTED_JS, arg=0, timeout=30000)
        await pg.wait_for_timeout(300)
        paper = await pg.evaluate(PAPER_JS)
        await pg.emulate_media(media='print')
        clear = await pg.evaluate(FINGERS_CLEAR_JS)
        await pg.emulate_media(media='screen')
        check(paper['fingers']['left'] > 0 and not paper['fingers']['right'] and not paper['fingers']['inside'] and not clear['touching'],
              f"with Fingers to the left on the page, on paper every finger number sits to the left of its note, clear of the note before ({paper['fingers']}, touching: {clear['touching'][:6]})")
        check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()
    # Joy to the World's violin melody left one line of music on a second sheet, with finger numbers under the next notes
    # in its sixteenths (Janelle, 2026-11-02): now a little smaller, it fits on one sheet, every number clear.
    if any(s['slug'] == 'joy-to-the-world' for s in SONGS):
        print('Print: joy-to-the-world')
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        errors = []
        pg = await open_reader(ctx, f'{base}/songs/joy-to-the-world/', errors, 'print joy')
        await pg.evaluate(PRINT_STUB_JS, False)
        await pg.click('#printBtn')
        await pg.wait_for_function(PRINTED_JS, arg=0, timeout=30000)
        await pg.wait_for_timeout(300)
        paper = await pg.evaluate(PAPER_JS)
        await pg.emulate_media(media='print')
        clear = await pg.evaluate(FINGERS_CLEAR_JS)
        sheets = await sheets_printed(pg)
        await pg.emulate_media(media='screen')
        check(paper['parts'] == 'Violin — Melody' and sheets == 1 and clear['checked'] > 0 and not clear['touching'],
              f"the violin melody prints on one sheet of Letter paper ({sheets}), every finger number clear ({clear['checked']} checked, touching: {clear['touching'][:6]})")
        # Download PDF (Janelle, 2026-11-02): the same sheets saved as a file, no print window; the screen as it was.
        before = await pg.evaluate(SCREEN_JS)
        async with pg.expect_download(timeout=60000) as info:
            await pg.click('#pdfBtn')
        dl = await info.value
        pdf = Path(await dl.path()).read_bytes()
        await pg.wait_for_function("() => document.getElementById('printCover').hidden", timeout=30000)
        pages = len(re.findall(rb'/Type\s*/Page(?![a-zA-Z])', pdf))
        after = await pg.evaluate(SCREEN_JS)
        check(pdf.startswith(b'%PDF') and pages == 1 and dl.suggested_filename == 'Joy to the World - Violin - Melody.pdf' and after == before,
              f'Download PDF saves the music as a PDF of one sheet ("{dl.suggested_filename}", {pages} sheet(s), {len(pdf) // 1024} KB), and the screen is as it was')
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
    # The cards sit in sections (Christmas, Hymns, Solos, Other), each under its heading, in the build's order.
    under = await pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('a.song')].map(a =>
      [a.getAttribute('href'), a.closest('section')?.querySelector('h2')?.textContent || '']))""")
    wrong = [s['title'] for s in SONGS if under.get(f"songs/{s['slug']}/") != s.get('section')]
    check(not wrong, 'every card sits under its section heading' + (f': not {wrong}' if wrong else ''))
    heads = await pg.evaluate("() => [...document.querySelectorAll('section h2')].map(h => h.textContent)")
    want = [x for x in SECTIONS if any(s.get('section') == x for s in SONGS)]
    check(heads[:len(want)] == want, f'sections in order: {heads[:len(want)]}')
    # Tabs over the list (Janelle, 2026-11-02): All songs, then one for each section. A tab shows only its section's
    # cards and puts it in the address (#hymns), so a link opens on that tab; All songs shows every card again.
    tabs = await pg.evaluate("() => [...document.querySelectorAll('.tabs button')].map(b => b.textContent)")
    check(tabs == ['All songs', *want], f'tabs: {tabs}')
    state = """() => ({ shown: [...document.querySelectorAll('a.song')].filter(a => a.offsetParent).map(a => a.getAttribute('href')),
      on: [...document.querySelectorAll('.tabs [aria-pressed=true]')].map(b => b.textContent), hash: location.hash })"""
    for name in want:
        await pg.click(f'.tabs button:text-is("{name}")')
        got = await pg.evaluate(state)
        expect = [f"songs/{s['slug']}/" for s in SONGS if s.get('section') == name]
        check(got['shown'] == expect and got['on'] == [name] and got['hash'] == '#' + section_id(name),
              f"{name} tab shows only its {len(expect)} piece(s) ({len(got['shown'])} shown, {got['on']}, {got['hash']!r})")
    await pg.click('.tabs button:text-is("All songs")')
    got = await pg.evaluate(state)
    check(len(got['shown']) == len(SONGS) and got['on'] == ['All songs'] and got['hash'] == '',
          f"All songs shows all {len(SONGS)} again ({len(got['shown'])} shown, {got['hash']!r})")
    if len(want) > 1:
        linked = await ctx.new_page()
        await linked.goto(f'{base}/#{section_id(want[1])}')
        got = await linked.evaluate(state)
        check(got['on'] == [want[1]] and len(got['shown']) == sum(s.get('section') == want[1] for s in SONGS),
              f"a link to #{section_id(want[1])} opens on the {want[1]} tab ({got['on']}, {len(got['shown'])} shown)")
        await linked.close()
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
    await student.click('#g-follow'); await student.wait_for_timeout(2500)  # Follow sits at the top of the music
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
    try:
        sp = await open_reader(ctx, f'{base}/sight-reading/?page=v1-03&n=12', errors, 'sight-reading', 844, 390)
        drawn = await sp.evaluate("() => document.querySelectorAll('#sheet .at-surface > *').length")
        before = await sp.evaluate(MUSIC_JS)
        await sp.click('#srNew'); await sp.wait_for_timeout(1500)
        after = await sp.evaluate(MUSIC_JS)
        await sp.click('#play'); await sp.wait_for_timeout(2500)
        tick = await sp.evaluate('() => reader.at()')
        check(drawn > 0 and after != before and tick > 0, f'offline: the sight-reading page opens, New exercise works, and it plays (tick {round(tick)})')
        await sp.close()
    except Exception as e:
        check(False, f'offline: the sight-reading page opens ({e.__class__.__name__})')
    try:
        fp = await ctx.new_page()
        await fp.goto(f'{base}/sight-reading/flash/?page=v1-03')
        await fp.wait_for_function("() => window.flash && flash.state().phase === 'ready' && flash.state().drawn", timeout=60000)
        check(True, 'offline: Flash a bar opens and draws its pattern')
        await fp.close()
    except Exception as e:
        check(False, f'offline: Flash a bar opens ({e.__class__.__name__})')
    stray = await ctx.new_page()
    try:
        await stray.goto(base + '/songs/not-saved/')
        cards = await stray.evaluate("() => document.querySelectorAll('a.song').length")
    except Exception as e:
        cards = e.__class__.__name__
    check(cards == len(SONGS), f'offline: a page that was never saved shows the home page (got {cards})')
    check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
    await ctx.close()


async def extras_checks(browser, base):
    """Parts for the strongest players after the 40 (BUILD-SPEC section 3), on violin and viola only: a Countermelody
    and/or Concert parts (42 or 44 parts). The Concert parts have chords and a second voice, with no string colours
    or finger numbers."""
    import xml.etree.ElementTree as ET
    def extra_rows(slug):
        names = ET.parse(ROOT / 'songs' / slug / f'{slug}.xml').getroot().find('part-list').findall('score-part')
        rows = []
        for sp in names[40:]:
            row = re.split(r'\s*[—–-]\s*', sp.findtext('part-name').strip(), maxsplit=1)[1]
            if row not in rows: rows.append(row)
        return rows
    slugs = [s['slug'] for s in SONGS if PARTS[s['slug']] in (42, 44)]
    if not slugs:
        print('Parts panel, countermelody and concert parts: no such song, skipped')
    for slug in slugs:
        await extras_song_checks(browser, base, slug, extra_rows(slug))


async def extras_song_checks(browser, base, slug, extra):
    """One song's extra rows (Countermelody and/or Concert), from its part names."""
    ck = lambda ok, what: check(ok, f'{slug}: {what}')    # two songs run these checks: each message names its song
    n = PARTS[slug]
    print(f'Parts panel, countermelody and concert parts ({n} parts: {", ".join(extra)}): {slug}')
    row_of = {name: 10 + r for r, name in enumerate(extra)}
    track = lambda name, inst: 40 + 2 * extra.index(name) + inst          # violin 0, viola 1
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        errors = []
        pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, slug, w, h)
        await pg.evaluate(SPY_JS)
        await pg.click('#g-parts'); await pg.wait_for_timeout(600)
        names = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .mix-name')].map(n => [...n.children].find(c => c.offsetParent && !c.classList.contains('lvl-same')).textContent)")
        if label == 'laptop':
            ck(names == VOICE_ROWS + extra, f'{label}: the extra rows come after the ten levels and voices ({names[10:]})')
        else:
            ck(len(names) == 10 + len(extra) and names[10:] == extra, f'{label}: the extra rows on a phone ({names[10:]})')
        eyes = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .tog.see')].filter(b => b.offsetParent).map(b => [b.id, b.classList.contains('none'), b.title])")
        greyed = [i for i, none, t in eyes if none]
        want = [f'see-{10 + r}-{i}' for r in range(len(extra)) for i in (2, 3)]
        ck(len(eyes) == 40 + 4 * len(extra) and greyed == want,
              f'{label}: an eye for violin and viola on each extra row, cello and bass greyed out in place ({greyed})')
        why = [t for i, none, t in eyes if none]
        ck(all('written for violin and viola' in t for t in why), f'{label}: a greyed-out cell says why ("{why[0] if why else ""}")')
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        ck(wide <= 1, f'{label}: no sideways scrolling ({wide}px extra)')
        if label != 'laptop':
            ck(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()
            continue
        # Violin on the first extra row and viola on the last, without the first visit's Violin Melody.
        first, last = extra[0], extra[-1]
        await pg.click(f'#see-{row_of[first]}-0'); await pg.click(f'#see-{row_of[last]}-1'); await pg.click('#see-4-0'); await pg.wait_for_timeout(1500)
        want_idx = [track(first, 0), track(last, 1)]
        ck(await pg.evaluate(SHOWN_JS) == want_idx and await pg.evaluate(PLAYING_JS) == want_idx,
              f'eyes on Violin {first} and Viola {last} show and play those two ({await pg.evaluate(SHOWN_JS)})')
        # The reader names a staff by whatever tells the shown staves apart: both rows differ, or only the instrument.
        want_staves = [f'Vln {first}', f'Vla {last}'] if first != last else ['Vln', 'Vla']
        staves = await pg.evaluate('() => reader.api.tracks.map(t => t.name)')
        ck(staves == want_staves, f'the staves are labelled ({staves})')
        # Concert parts have notes and no string colours; a Countermelody has its colours.
        styled = await pg.evaluate("""() => reader.api.score.tracks.slice(40).map(t => { const ns = t.staves[0].bars.flatMap(b => b.voices.flatMap(v => v.beats.flatMap(be => be.notes)));
              return [ns.length, ns.filter(x => x.style).length] })""")
        for k, (count, coloured) in enumerate(styled):
            name = ['Violin', 'Viola'][k % 2] + ' ' + extra[k // 2]
            ok = count > 0 and (coloured == 0 if extra[k // 2] == 'Concert' else coloured > 0)
            ck(ok, f'{name}: {count} notes, {coloured} with string colours ({"none" if extra[k // 2] == "Concert" else "some"} expected)')
        about = (await pg.text_content('#infoPop')).lower()
        ck(all(w in about for w in (['countermelody'] if 'Countermelody' in extra else []) + (['concert part'] if 'Concert' in extra else [])),
              'the About box names the extra parts')
        if 'Concert' in extra:
            # Only Viola Concert on the page, with note names: each double stop has a name on every note, top to bottom
            # in pitch order (the bars on screen at the start).
            await pg.click(f'#see-{row_of[first]}-0')        # the violin part of the first extra row off: Viola Concert alone
            for _ in range(5):
                if (await pg.text_content('#g-look .now .word')) == 'Note names': break
                await pg.click('#g-look'); await pg.wait_for_timeout(400)
            await pg.wait_for_timeout(1500)
            chords = await pg.evaluate(f"""() => {{ const out = [];
              for (const bar of reader.api.score.tracks[{track('Concert', 1)}].staves[0].bars) for (const v of bar.voices) for (const be of v.beats) {{
                if (be.isRest || be.notes.length < 2) continue;
                const g = document.querySelector('#sheet g.b' + be.id); if (!g) continue;
                const fins = []; let el = g.nextElementSibling;
                while (el && el.classList && el.classList.contains('fin')) {{ fins.push([parseFloat(el.getAttribute('y')), el.firstChild.textContent]); el = el.nextElementSibling; }}
                const want = [...be.notes].sort((a, b) => b.realValue - a.realValue).map(x => (x.letter || '').charAt(0));
                out.push([fins.sort((a, b) => a[0] - b[0]).map(f => f[1]), want]);
              }}
              return out; }}""")
            good = [c for c in chords if c[0] == c[1]]
            ck(chords and len(good) == len(chords), f'note names on Viola Concert chords: one per note, top to bottom in pitch order ({len(good)} of {len(chords)}; e.g. {chords[:2]})')
            # Only Concert parts on the page: the Strings key steps aside, and a finger look or String colors says why.
            ck(await pg.evaluate("() => document.getElementById('legend').hidden"), 'with only a Concert part on the page the Strings key steps aside')
            for _ in range(5):
                await pg.click('#g-look'); await pg.wait_for_timeout(300)
                if (await pg.text_content('#g-look .now .word')) == 'Fingers inside': break
            told = await pg.text_content('#toast') or ''
            ck('Concert parts have no finger numbers' in told, f'a finger look says the Concert parts have none ("{told}")')
            for _ in range(3):
                await pg.click('#g-colors'); await pg.wait_for_timeout(300)
                told = await pg.text_content('#toast') or ''
                if not told.endswith('off'): break
            ck('Concert parts have no string colors' in told, f'String colors says the Concert parts have none ("{told}")')
            for _ in range(5):
                if (await pg.text_content('#g-look .now .word')) == 'Note names': break
                await pg.click('#g-look'); await pg.wait_for_timeout(300)
            # Violin Concert alone: its second voice (the Epic's tune under a drone, Joy's drone under the tune) gets note
            # names, and counts follow whichever voice has the most notes.
            await pg.click(f'#see-{row_of["Concert"]}-0'); await pg.click(f'#see-{row_of["Concert"]}-1'); await pg.wait_for_timeout(2000)
            v2 = await pg.evaluate(f"""() => {{ const t = reader.api.score.tracks[{track('Concert', 0)}]; let n = 0, named = 0;
              for (const bar of t.staves[0].bars) bar.voices.slice(1).forEach(v => v.beats.forEach(be => {{ if (be.isRest) return; n += be.notes.length;
                const g = document.querySelector('#sheet g.b' + be.id); let el = g && g.nextElementSibling, k = 0;
                while (el && el.classList && el.classList.contains('fin')) {{ k++; el = el.nextElementSibling; }}
                named += Math.min(k, be.notes.length); }}));
              return [n, named] }}""")
            if v2[0]:
                ck(v2[1] == v2[0], f'Violin Concert: every note of its second voice has a note name ({v2[1]} of {v2[0]})')
            else:
                print('  (Violin Concert has no second voice: second-voice names skipped)')
            # Counts follow the voice with the most notes: in a bar where that is a second voice with notes between the
            # beats, those notes are counted too.
            counts = await pg.evaluate("""() => { const tr = reader.api.score.tracks[reader.api.tracks[0].index], mbs = reader.api.score.masterBars;
              for (let k = 0; k < mbs.length; k++) {
                const vs = tr.staves[0].bars[k].voices; if (vs.length < 2) continue;
                const n = v => v.beats.filter(b => !b.isRest).length, best = vs.reduce((a, v) => n(v) > n(a) ? v : a, vs[0]);
                const beat = 3840 / mbs[k].timeSignatureDenominator;
                if (best === vs[0] || !best.beats.some(b => !b.isRest && b.playbackStart % beat !== 0)) continue;
                const mb = reader.api.boundsLookup.findMasterBarByIndex(k); if (!mb) continue;
                const r = mb.visualBounds;
                const got = [...document.querySelectorAll('.beat-count')].filter(e => { const x = parseFloat(e.style.left); return x >= r.x && x < r.x + r.w && e.textContent; }).map(e => e.textContent);
                return { bar: k + 1, beats: mbs[k].timeSignatureNumerator, got };
              }
              return null }""")
            if counts:
                ck(len(counts['got']) > counts['beats'], f"Violin Concert bar {counts['bar']}: counted from its second voice's tune ({counts['got']})")
            else:
                print('  (no bar where a Concert part counts from its second voice: skipped)')
            # Where the drone and the tune start a note together (either may be the second voice), tapping either note
            # rings that note, not the other.
            heads = r"""(ids) => ids.map(id => { const g = document.querySelector('#sheet svg g.b' + id);
              const a = g && [...g.querySelectorAll('g.at')].find(a => { const k = ((a.querySelector('text') || {}).textContent || '').charCodeAt(0); return k >= 0xE0A0 && k <= 0xE0FF; });
              const m = a && /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(a.getAttribute('transform')); if (!m) return null;
              const r = g.ownerSVGElement.getBoundingClientRect(); return { x: r.left + +m[1] + a.querySelector('text').getBoundingClientRect().width / 2, y: r.top + +m[2] }; })"""
            # In the one-line view the music slides sideways (as a swipe moves it); a page of music scrolls down.
            bring = """(id) => { const sh = document.getElementById('sheet'), g = document.querySelector('#sheet svg g.b' + id);
              if (!sh.classList.contains('line')) return g.scrollIntoView({ block: 'center' });
              sh.scrollIntoView({ block: 'center' }); const r = g.getBoundingClientRect(), s = sh.getBoundingClientRect();
              sh.scrollLeft += r.left - (s.left + s.width / 2);
              const q = g.getBoundingClientRect(); window.scrollBy(0, q.top + q.height / 2 - innerHeight / 2); }"""
            pair = await pg.evaluate('() => { const heads = ' + heads + """;
              const tr = reader.api.score.tracks[reader.api.tracks[0].index];
              for (const [k, bar] of tr.staves[0].bars.entries()) {
                const all = bar.voices.flatMap(v => v.beats).filter(b => !b.isRest && b.notes.length === 1);
                for (const b of all.filter(b => b.voice.index > 0)) {
                  const o = all.find(q => q.voice.index === 0 && Math.abs(q.playbackStart - b.playbackStart) <= 1); if (!o) continue;
                  const [hb, ho] = heads([b.id, o.id]);
                  if (hb && ho && Math.abs(hb.y - ho.y) > 40) return { bar: k + 1, ids: [b.id, o.id] };
                } }
              return null }""")
            if pair:
                # Alone, then under Viola Inner: alphaTab takes the upper staff's note where two staves start one together.
                for above in (None, 'see-5-1'):
                    if above:
                        await pg.evaluate('(id) => document.getElementById(id).click()', above); await pg.wait_for_timeout(2000)
                    with_what = ' with Viola Inner above it' if above else ''
                    for ids, what in ((pair['ids'], "the second voice's note"), (pair['ids'][::-1], "the first voice's note")):
                        await pg.evaluate(bring, ids[0])
                        await pg.wait_for_timeout(600)
                        pos = await pg.evaluate(heads, ids)
                        await pg.mouse.click(pos[0]['x'], pos[0]['y']); await pg.wait_for_timeout(600)
                        pos = await pg.evaluate(heads, ids)  # the one-line view slides to bring the tapped note to its place
                        rung = await pg.evaluate("""(ps) => { const rs = [...document.querySelectorAll('.start-mark')].map(e => e.getBoundingClientRect());
                          return ps.map(p => rs.some(r => p.x > r.left && p.x < r.right && p.y > r.top && p.y < r.bottom)) }""", pos)
                        ck(rung == [True, False], f"Violin Concert{with_what} bar {pair['bar']}: tapping {what} where the drone and the tune start together rings that note, not the other ({rung})")
                    if above:
                        await pg.evaluate('(id) => document.getElementById(id).click()', above); await pg.wait_for_timeout(2000)
            else:
                print('  (no bar where the drone and the tune start a note together: tap check skipped)')
            # Where one voice rests under the other's note (Joy's bar 15, where the drone stops), tapping the note rings
            # the note, not the rest.
            over = await pg.evaluate("""() => { const tr = reader.api.score.tracks[reader.api.tracks[0].index];
              for (const [k, bar] of tr.staves[0].bars.entries()) {
                const all = bar.voices.flatMap(v => v.beats);
                for (const b of all.filter(b => !b.isRest && b.notes.length === 1))
                  if (all.some(q => q.isRest && !q.isEmpty && q.voice !== b.voice && Math.abs(q.playbackStart - b.playbackStart) <= 1)) return { bar: k + 1, id: b.id };
              }
              return null }""")
            if over:
                await pg.evaluate(bring, over['id']); await pg.wait_for_timeout(600)
                pos = await pg.evaluate(heads, [over['id']])
                await pg.mouse.click(pos[0]['x'], pos[0]['y']); await pg.wait_for_timeout(600)
                pos = await pg.evaluate(heads, [over['id']])
                rung = await pg.evaluate("""([p]) => [...document.querySelectorAll('.start-mark')].map(e => e.getBoundingClientRect())
                  .some(r => p.x > r.left && p.x < r.right && p.y > r.top && p.y < r.bottom)""", pos)
                ck(rung, f"Violin Concert bar {over['bar']}: tapping a note over the other voice's rest rings the note, not the rest")
            else:
                print("  (no bar where a Concert note sits over the other voice's rest: tap check skipped)")
        # Saved choices: the layout is saved as the 40 graded parts ('voices40', which a reader from before the extra rows
        # knows), with the full id beside it; a second visit shows the same parts.
        stored = await pg.evaluate(f"() => JSON.parse(localStorage.getItem('{slug}-reader') || '{{}}')")
        full = 'voices40+' + '+'.join({'Countermelody': 'counter', 'Concert': 'concert'}[x] for x in extra)
        shown = await pg.evaluate(SHOWN_JS)
        ck(stored.get('parts') == 'voices40' and stored.get('partsFull') == full and stored.get('seen') == shown,
           f"choices are saved as the graded 40 plus the full layout ({stored.get('parts')}, {stored.get('partsFull')}, {stored.get('seen')})")
        again = await open_reader(ctx, f'{base}/songs/{slug}/', errors, slug)
        ck(await again.evaluate(SHOWN_JS) == shown, f'a second visit shows the same parts ({shown})')
        ck(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


async def piano_checks(browser, base):
    """A song whose last part is a Piano (the hymn on two staves; Silent Night, 2026-11-02): one row, one eye."""
    import xml.etree.ElementTree as ET
    def last_name(slug):
        return ET.parse(ROOT / 'songs' / slug / f'{slug}.xml').getroot().find('part-list').findall('score-part')[-1].findtext('part-name').strip()
    slug = next((s['slug'] for s in SONGS if last_name(s['slug']) == 'Piano'), None)
    if not slug:
        print('Parts panel, piano part: no such song, skipped')
        return
    n = PARTS[slug]
    ck = lambda ok, what: check(ok, f'{slug}: {what}')
    print(f'Parts panel, piano part ({n} parts): {slug}')
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        errors, sounds = [], []
        ctx.on('requestfinished', lambda r: sounds.append(r.url.split('/')[-1].split('?')[0]) if '/soundfont/' in r.url else None)
        pg = await open_reader(ctx, f'{base}/songs/{slug}/', errors, slug, w, h)
        pg.on('console', lambda m: errors.append(f'{slug}: {m.text}') if m.type == 'error' else None)
        await pg.evaluate(SPY_JS)
        await pg.click('#g-parts'); await pg.wait_for_timeout(600)
        names = await pg.evaluate("() => [...document.querySelectorAll('#mixParts .mix-name')].map(n => [...n.children].find(c => c.offsetParent && !c.classList.contains('lvl-same')).textContent)")
        ck(names[-1] == 'Piano' and names[:10] == (VOICE_ROWS if label == 'laptop' else names[:10]), f'{label}: the Piano row comes last ({names[10:]})')
        r = len(names) - 1
        eyes = await pg.evaluate(f"() => [...document.querySelectorAll('#mixParts .tog.see')].filter(b => b.offsetParent && b.id.startsWith('see-{r}-')).map(b => [b.id, b.className, b.title])")
        ck(len(eyes) == 1 and 'wide' in eyes[0][1] and 'none' not in eyes[0][1] and eyes[0][2] == 'See Piano',
           f'{label}: one eye for the Piano, across the instrument columns ({eyes})')
        wide = await pg.evaluate('() => document.documentElement.scrollWidth - window.innerWidth')
        ck(wide <= 1, f'{label}: no sideways scrolling ({wide}px extra)')
        ck('piano-generaluser-sf2.b64.txt' in sounds and 'strings-generaluser-sf2.b64.txt' in sounds, f'{label}: the piano sound loads with the strings ({sounds})')
        if label != 'laptop':
            ck(not errors, f'{label}: no script errors' + (f': {errors[:3]}' if errors else ''))
            await ctx.close()
            continue
        # The piano alone: shown and played, two staves named "Pno", no string colours.
        await pg.click(f'#see-{r}-0'); await pg.click('#see-4-0'); await pg.wait_for_timeout(2500)
        ck(await pg.evaluate(SHOWN_JS) == [n - 1] and await pg.evaluate(PLAYING_JS) == [n - 1],
           f'the eye shows and plays the Piano alone ({await pg.evaluate(SHOWN_JS)})')
        staff = await pg.evaluate('() => reader.api.tracks.map(t => [t.name, t.staves.length])')
        ck(staff == [['Pno', 2]], f'the piano is two staves named Pno ({staff})')
        coloured = await pg.evaluate(f"() => reader.api.score.tracks[{n - 1}].staves.flatMap(s => s.bars.flatMap(b => b.voices.flatMap(v => v.beats.flatMap(be => be.notes)))).filter(x => x.style).length")
        ck(coloured == 0, f'the piano has no string colours ({coloured} coloured notes)')
        inside = await pg.evaluate("""() => { const edge = document.getElementById('sheet').getBoundingClientRect().left;
          return [...document.querySelectorAll('#sheet .at-surface svg g[transform*="rotate"] > text')].filter(t => t.textContent === 'Pno').map(t => Math.round(t.getBoundingClientRect().left - edge)); }""")
        ck(inside and min(inside) >= 0, f'the name Pno starts inside the music ({inside} px from its left edge)')
        for _ in range(3):
            await pg.click('#g-colors'); await pg.wait_for_timeout(300)
            told = await pg.text_content('#toast') or ''
            if not told.endswith('off'): break
        ck('Piano parts have no string colors' in told, f'String colors says the Piano has none ("{told}")')
        about = await pg.evaluate("() => document.getElementById('infoPop').textContent")
        ck('a piano part' in about, 'the About box names the piano part')
        stored = await pg.evaluate(f"() => JSON.parse(localStorage.getItem('{slug}-reader') || '{{}}')")
        ck(stored.get('parts') == 'voices40' and str(stored.get('partsFull', '')).endswith('+piano') and stored.get('seen') == [n - 1],
           f"choices are saved with the full layout ({stored.get('parts')}, {stored.get('partsFull')}, {stored.get('seen')})")
        ck(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await ctx.close()


async def main():
    began = time.monotonic()
    base = serve()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        await home_checks(browser, base)
        await song_checks(browser, base)
        await parts_checks(browser, base)
        await voices40_checks(browser, base)
        await voices_checks(browser, base)
        await one_line_checks(browser, base)
        await sight_reading_checks(browser, base)
        await look_ahead_checks(browser, base)
        await duet_checks(browser, base)
        await flash_checks(browser, base)
        await listen_checks(browser, base)
        await print_checks(browser, base)
        await extras_checks(browser, base)
        await piano_checks(browser, base)
        await preview_checks(browser, base)
        await app_checks(browser)
        await browser.close()
    took = round(time.monotonic() - began)
    print(f'\nTook {took // 60} min {took % 60} s.')
    if failures:
        print(f'{len(failures)} check(s) failed:')
        for f in failures:
            print('  - ' + f)
        sys.exit(1)
    print('All checks passed.')


asyncio.run(main())
