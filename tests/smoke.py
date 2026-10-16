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
     Laptop: the Full screen button goes in and out of full screen. Phone (acting like an iPhone,
     which doesn't allow it): no Full screen button, and pinching the music makes it bigger and smaller.
     The Parts panel: the music runs a little under a tab at the right edge, which pulls the panel out over it, each part's eye
     puts it on the page, the parts on the page play until "Hear the parts I see" is unticked and a
     speaker for each part chooses, and choices survive a reload.
     Songs in levels and voices (34 parts): a row for each level and voice, the cello and bass Inner
     cells greyed out in place (a tap says why), the group rule over the table, and choices saved with
     the six levels moving to their match. Run on the first 34-part song in songs.json; until there is
     one, give a 34-part score to try it on in place of the first song's:
         VOICES_SCORE="../Christmas Collection/The First Noel/The-First-Noel.xml" python tests/smoke.py
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
                await pg.click('#g-layout'); await pg.wait_for_timeout(1500)
                lined = await pg.evaluate("() => document.getElementById('sheet').classList.contains('line') && document.getElementById('g-layout').title")
                check(paged == 'Music: pages' and lined == 'Music: one long line', f'{label}: the music button switches between pages and one long line')
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


async def voices_checks(browser, base):
    """The Parts panel for a song in levels and voices (34 parts)."""
    slug = next((s['slug'] for s in SONGS if PARTS[s['slug']] == 34), None)
    stand_in = os.environ.get('VOICES_SCORE')
    if not slug and not stand_in:
        print('Parts panel, levels and voices: no 34-part song, skipped (VOICES_SCORE=<34-part xml> tries one)')
        return
    if not slug:
        slug = SONGS[0]['slug']
        print(f'Parts panel, levels and voices: {Path(stand_in).name} in place of {slug}')
    else:
        print(f'Parts panel, levels and voices: {slug}')
    key = f'{slug}-reader'
    for label, w, h in [('laptop', 1366, 860), ('phone landscape', 844, 390)]:
        # No offline copy here, so a stand-in score can't be answered from it.
        ctx = await browser.new_context(device_scale_factor=1, service_workers='block')
        await setup(ctx)
        if stand_in and PARTS[slug] != 34:
            await ctx.route(f'**/songs/{slug}/{slug}.xml*', lambda r: r.fulfill(path=stand_in, content_type='application/xml'))
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
        await voices_checks(browser, base)
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
