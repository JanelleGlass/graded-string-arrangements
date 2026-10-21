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
     The page settings are separate buttons in the strip; On the note steps through its five looks,
     each drawn as it says; on a laptop the music button switches between pages and one long line.
     On pages every line names its parts, and scrolled down the size buttons stay at the top of the
     window. Along one long line, each part's name, clef and key signature (the key in force there,
     after every change of key) stay pinned at the left edge.
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
     visit shows the same parts. A piece with no levels (one line on some instruments, such as Twinkle Harmony for
     viola and cello): a first visit shows and plays the first part, one row named for the line under a Part heading,
     the other instruments greyed out in place (a tap says why), no group rule, the About box saying who it is for,
     and a part taken off the page staying off after a reload.
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
PARTS = {s['slug']: (ROOT / 'songs' / s['slug'] / f"{s['slug']}.xml").read_text(encoding='utf-8').count('<score-part ') for s in SONGS}
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


# Pages: a part name beside every staff on every line (names drawn, and lines times parts on the page).
NAMED_LINES_JS = '''() => {
  const names = new Set(reader.api.tracks.map(t => t.name));
  const drawn = [...document.querySelectorAll('#sheet svg text')].filter(t => names.has(t.textContent)).length;
  const lines = new Set(reader.api.boundsLookup.staffSystems.map(s => Math.round(s.visualBounds.y))).size;
  return [drawn, lines * reader.api.tracks.length];
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
            # on note names with finger numbers to the right. Each look draws what it says, at the same size.
            look_js = '''() => { const fin = [...document.querySelectorAll('#sheet text.fin')].map(t => t.textContent);
              return { look: document.querySelector('#g-look .now .word').textContent, head: document.querySelector('#g-look .now ellipse').getAttribute('fill'),
                       off: (r => (r.left + r.right) / 2)(document.querySelector('#g-look .now').getBoundingClientRect()) - (r => (r.left + r.right) / 2)(document.getElementById('g-look').getBoundingClientRect()), names: fin.some(x => /^[A-G]/.test(x)),
                       fingers: fin.some(x => /^[0-4]/.test(x)), size: reader.api.settings.display.scale }; }'''
            seen = [await pg.evaluate(look_js)]
            for _ in range(5):
                await pg.click('#g-look'); await pg.wait_for_timeout(2200)
                seen.append(await pg.evaluate(look_js))
            order = ['Fingers inside', 'Fingers to the right', 'Note names and fingers', 'Note names', 'Plain notes']
            first = 0 if label == 'laptop' else 2
            want_looks = [order[(first + k) % 5] for k in range(6)]
            check([x['look'] for x in seen] == want_looks, f'{label}: the On the note button steps through the five looks ({[x["look"] for x in seen]})')
            drawn = {x['look']: (x['names'], x['fingers']) for x in seen}
            check(drawn == {'Fingers inside': (False, True), 'Fingers to the right': (False, True), 'Note names and fingers': (True, True),
                            'Note names': (True, False), 'Plain notes': (False, False)}, f'{label}: each look draws what it says ({drawn})')
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
            await pg.click('#g-count')
            on = await pg.evaluate("() => !document.getElementById('sheet').classList.contains('counts-off')")
            check(off and on, f'{label}: the Counting button in the strip hides and shows the counts')
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
                await pg.evaluate('() => window.scrollTo(0, document.documentElement.scrollHeight)'); await pg.wait_for_timeout(400)
                held = await pg.evaluate(TOOLS_HELD_JS)
                check(held[0] > 300 and held[1], f'{label}: scrolled down the pages, the size buttons and Line or Pages stay at the top of the window, ready to tap ({held})')
                await pg.evaluate('() => window.scrollTo(0, 0)')
                await pg.click('#g-layout'); await pg.wait_for_timeout(1500)
                lined = await pg.evaluate("() => document.getElementById('sheet').classList.contains('line') && document.getElementById('g-layout').title")
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
    """The Parts panel for a piece with no levels: one line on some of the instruments (Twinkle Harmony: viola and cello)."""
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
        check(await pg.evaluate(SHOWN_JS) == [0] and await pg.evaluate(PLAYING_JS) == [0],
              f'{label}: a first visit shows and plays the first instrument\'s part ({insts[0]})')
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
            check(same == 'viola & cello have the same notes', f'the line under the row says viola and cello have the same notes ("{same}")')
        lede = await pg.evaluate("() => document.querySelector('#infoPop .lede').textContent")
        check(lede.startswith(f'One line, for {who}.'), f'the About box says who the piece is for ("{lede[:40]}")')
        none = next(i for i in range(4) if i not in cols)
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


async def main():
    base = serve()
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
        await home_checks(browser, base)
        await song_checks(browser, base)
        await parts_checks(browser, base)
        await voices40_checks(browser, base)
        await voices_checks(browser, base)
        await one_line_checks(browser, base)
        await extras_checks(browser, base)
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
