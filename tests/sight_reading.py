"""Test of the sight-reading generator: every book page, violin and viola, 1,000 exercise numbers each.

    python3 tests/sight_reading.py

About a minute. Uses the same Playwright and Chromium as tests/smoke.py (the generator runs in the browser, as on the
page), and ALPHATAB_JS=<path> in the same way when jsdelivr is out of reach.

The exercises are read back from their MusicXML and checked here, apart from the generator's own code:
  - only the page's notes, each with its string color and Janelle's finger number (arrows only where a finger moves)
  - only the page's rhythms, and every bar adds up
  - no leap bigger than the page allows, and no string crossing to or from an eighth note unless the page allows it
  - each of the page's new notes or rhythms at least twice
  - it starts on a note of the home chord and ends on the home note, long, on beat 1
  - viola in alto clef, a fifth below the violin (or as the page says), violin in treble clef
  - alphaTab reads every one, with the same bars and notes
  - the same page and number always give the same music
Flash a bar's patterns (pattern mode), every page, both instruments, every length (half a bar, a bar, two bars), with
and without repeated notes, 300 numbers each: the page's notes (colors and finger numbers too) and rhythms but never a
whole note, starting with a note, every bar adding up (half a bar in 2/4), no leap past the page's limit and no crossing
on an eighth, the right length, no note twice in a row when asked, and the shape it says: a run all steps one way, a turn
of steps that changes direction once, steps with one skip, or a repeated rhythm; alphaTab reads each one.
Besides the book pages in sight-reading/pages.json, a few made-up pages here try what those don't use yet: eighth
notes, dotted quarters, half rests, 2/4 and 3/4, 6 and 8 bars, low 2, few and free crossings, a viola page of its own.
"""
import asyncio, json, os, sys, threading, time
import xml.etree.ElementTree as ET
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = json.loads((ROOT / 'sight-reading' / 'pages.json').read_text(encoding='utf-8'))
COUNT = int(os.environ.get('SIGHT_COUNT', '1000'))  # exercise numbers per page and instrument
sys.stdout.reconfigure(encoding='utf-8')

TRY_PAGES = [
    {'id': 'test-eighths', 'title': 'Eighths in 3/4, 2/4 and 4/4, eight bars', 'notes': ['D0', 'D1', 'D2', 'D3', 'A0', 'A1', 'A2', 'A3', 'E0', 'E1'],
     'new': ['8 8', 'q. 8'], 'pattern': {'D': 'high2', 'A': 'high2', 'E': 'low2'}, 'key': 'D major', 'time': ['3/4', '2/4', '4/4'],
     'rhythms': ['h.', 'h', 'q', '8 8', 'q. 8', 'qr', 'hr', 'w'], 'bars': 8, 'maxLeap': 4, 'crossings': 'few', 'tempo': [72, 100]},
    {'id': 'test-low2', 'title': 'Low 2 in G major, six bars, free crossings', 'notes': ['G0', 'G1', 'G2', 'G3', 'D0', 'D1', 'D2', 'D3', 'A0', 'A1', 'A2', 'A3'],
     'new': ['A2', 'D2'], 'pattern': {'G': 'high2', 'D': 'high2', 'A': 'low2'}, 'key': 'G major', 'time': ['4/4'],
     'rhythms': ['h', 'q', '8 8', 'hr'], 'bars': 6, 'maxLeap': 5, 'crossings': 'free', 'tempo': [60, 80]},
    {'id': 'test-viola-own', 'title': 'Its own viola notes', 'notes': ['A0', 'A1', 'A2', 'A3', 'E0'], 'new': ['A3'],
     'pattern': {'A': 'high2'}, 'key': 'A major', 'time': ['4/4'], 'rhythms': ['w', 'h', 'q'], 'bars': 4, 'maxLeap': 3,
     'viola': {'notes': ['C0', 'C1', 'C2', 'C3', 'G0', 'G1', 'G2', 'G3'], 'new': ['C3'], 'pattern': {'C': 'high2', 'G': 'high2'}, 'key': 'C major'}},
]

# ---- What the rules allow, worked out here on its own ----
LETTERS = 'CDEFGAB'
NATURAL = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
OPEN = {'violin': {'E': 76, 'A': 69, 'D': 62, 'G': 55}, 'viola': {'A': 69, 'D': 62, 'G': 55, 'C': 48}}
FIFTH_DOWN = {'E': 'A', 'A': 'D', 'D': 'G', 'G': 'C'}
COLOR = {'E': '#F0B000', 'A': '#DC2626', 'D': '#1D4ED8', 'G': '#15803D', 'C': '#7C3AED'}
PATTERN = {'high2': [0, 2, 4, 5, 7], 'low2': [0, 2, 3, 5, 7], 'low1': [0, 1, 3, 5, 7], 'high3': [0, 2, 4, 6, 7]}
USUAL = [0, 2, 4, 5, 7]
MAJOR = {'C': 0, 'G': 1, 'D': 2, 'A': 3, 'E': 4, 'B': 5, 'F': -1, 'Bb': -2, 'Eb': -3}
TYPE_LEN = {'whole': 8, 'half': 4, 'quarter': 2, 'eighth': 1}


def rules(page, inst):
    names, pattern, key, new = page['notes'], page.get('pattern', {}), page['key'].split()[0], page.get('new', [])
    if inst == 'viola':
        v = page.get('viola', {})
        move = lambda n: FIFTH_DOWN[n[0]] + n[1] if len(n) == 2 and n[0] in FIFTH_DOWN and n[1].isdigit() else n
        names = v.get('notes') or [move(n) for n in names]
        pattern = v.get('pattern') or {FIFTH_DOWN[s]: p for s, p in pattern.items()}
        key = v['key'].split()[0] if v.get('key') else {'A': 'D', 'D': 'G', 'G': 'C', 'E': 'A', 'C': 'F'}[key]
        new = v.get('new') or [move(n) for n in new]
    allowed = {}
    for n in names:
        s, f = n[0], int(n[1])
        semis = PATTERN[pattern.get(s, 'high2')][f]
        midi = OPEN[inst][s] + semis
        letter = LETTERS[(LETTERS.index(s) + f) % 7]
        octave = midi // 12 - 1
        natural = 12 * (octave + 1) + NATURAL[letter]
        if natural - midi > 6: octave -= 1; natural -= 12
        elif midi - natural > 6: octave += 1; natural += 12
        label = '0' if f == 0 else (('↓' if semis < USUAL[f] else '↑') + str(f) if semis != USUAL[f] else str(f))
        allowed[(letter, midi - natural, octave)] = {'name': n, 'string': s, 'color': COLOR[s], 'label': label}
    return {'allowed': allowed, 'tonic': key[0], 'fifths': MAJOR[key], 'new': new}


def check(page, inst, n, xml, at):
    """Problems with one exercise, in words ([] if none). at: what alphaTab read (bars, notes)."""
    R, out = rules(page, inst), []
    root = ET.fromstring(xml)
    name = root.findtext('part-list/score-part/part-name')
    if name != f"{inst.capitalize()} — Sight-reading":
        out.append(f'part named {name!r}')
    part = root.find('part')
    first = part.find('measure/attributes')
    clef = (first.findtext('clef/sign'), first.findtext('clef/line'))
    if clef != (('G', '2') if inst == 'violin' else ('C', '3')):
        out.append(f'clef {clef}')
    if int(first.findtext('key/fifths')) != R['fifths']:
        out.append(f"key signature {first.findtext('key/fifths')}")
    div = int(first.findtext('divisions'))
    beats, beat_type = int(first.findtext('time/beats')), int(first.findtext('time/beat-type'))
    if f'{beats}/{beat_type}' not in page.get('time', ['4/4']):
        out.append(f'time {beats}/{beat_type}')
    bar_len = beats * 4 * div // beat_type
    measures = part.findall('measure')
    if len(measures) != page.get('bars', 4):
        out.append(f'{len(measures)} bars')
    notes, tokens, prev = [], [], None
    for bi, m in enumerate(measures):
        pos, items = 0, []
        for el in m.findall('note'):
            d = int(el.findtext('duration'))
            typ, dot, rest = el.findtext('type'), el.find('dot') is not None, el.find('rest') is not None
            if TYPE_LEN[typ] * (1.5 if dot else 1) * div / 2 != d:
                out.append(f'bar {bi + 1}: a {typ} lasting {d}')
            items.append((typ + ('.' if dot else ''), rest, el.findtext('beam')))
            if not rest:
                p = el.find('pitch')
                k = (p.findtext('step'), int(p.findtext('alter') or 0), int(p.findtext('octave')))
                a = R['allowed'].get(k)
                if not a:
                    out.append(f'bar {bi + 1}: {k} is not one of the page\'s notes')
                else:
                    color, head = el.get('color'), el.find('notehead').get('color')
                    label = el.findtext('notations/technical/fingering')
                    if color != a['color'] or head != a['color'] or label != a['label']:
                        out.append(f"bar {bi + 1}: {a['name']} marked {color}/{head}/{label}, not {a['color']}/{a['label']}")
                    notes.append({'bar': bi, 'pos': pos, 'len': d, 'dia': k[2] * 7 + LETTERS.index(k[0]), 'letter': k[0],
                                  'name': a['name'], 'string': a['string'], 'after_rest': prev == 'rest'})
            prev = 'rest' if rest else 'note'
            pos += d
        if pos != bar_len:
            out.append(f'bar {bi + 1} adds up to {pos}, not {bar_len}')
        # The bar's rhythm tokens.
        i = 0
        while i < len(items):
            typ, rest, beam = items[i]
            nxt = items[i + 1] if i + 1 < len(items) else None
            if rest:
                tok = {'quarter': 'qr', 'half': 'hr', 'whole': 'wr'}.get(typ, typ + 'r')
            elif typ == 'eighth' and beam == 'begin' and nxt and nxt[0] == 'eighth' and nxt[2] == 'end':
                tok, i = '8 8', i + 1
            elif typ == 'quarter.' and nxt and nxt[0] == 'eighth' and not nxt[1]:
                tok, i = 'q. 8', i + 1
            else:
                tok = {'whole': 'w', 'half.': 'h.', 'half': 'h', 'quarter': 'q'}.get(typ, typ)
            tokens.append(tok)
            i += 1
    for t in set(tokens):
        if t not in page['rhythms']:
            out.append(f'rhythm {t!r} is not one of the page\'s')
    # Leaps and crossings.
    crossings = page.get('crossings', 'some')
    per_bar = {}
    for a, b in zip(notes, notes[1:]):
        if abs(a['dia'] - b['dia']) + 1 > page.get('maxLeap', 3):
            out.append(f"bar {b['bar'] + 1}: a leap of a {abs(a['dia'] - b['dia']) + 1} from {a['name']} to {b['name']}")
        if a['string'] != b['string'] and not b['after_rest']:
            if crossings != 'free' and (a['len'] == 1 or b['len'] == 1):
                out.append(f"bar {b['bar'] + 1}: a string crossing on an eighth note ({a['name']} to {b['name']})")
            per_bar[b['bar']] = per_bar.get(b['bar'], 0) + 1
    if crossings == 'few' and any(v > 1 for v in per_bar.values()):
        out.append(f'more than one string crossing in a bar ({per_bar})')
    # The new notes and rhythms, at least twice each.
    for x in R['new']:
        got = sum(1 for nt in notes if nt['name'] == x) + sum(1 for t in tokens if t == x)
        if got < 2:
            out.append(f'new {x!r} only {got} time(s)')
    # Home: it starts on a note of the home chord, and ends on the home note, long, on beat 1.
    deg = lambda nt: (LETTERS.index(nt['letter']) - LETTERS.index(R['tonic'])) % 7
    if notes and deg(notes[0]) not in (0, 2, 4):
        out.append(f"starts on {notes[0]['name']}, not a note of the home chord")
    last = notes[-1] if notes else None
    if not last or deg(last) != 0 or last['bar'] != len(measures) - 1 or last['pos'] != 0 or last['len'] < min(bar_len, 2 * div):
        out.append(f"ends on {last and last['name']} (bar {last and last['bar'] + 1}, at {last and last['pos']}, lasting {last and last['len']}), not the home note held on beat 1")
    if at != [len(measures), len(notes)]:
        out.append(f'alphaTab read {at}, the file has {[len(measures), len(notes)]}')
    return out


def check_pattern(page, inst, length, no_repeats, ex):
    """Problems with one Flash a bar pattern, in words."""
    R, out = rules(page, inst), []
    root = ET.fromstring(ex['xml'])
    part = root.find('part')
    first = part.find('measure/attributes')
    div = int(first.findtext('divisions'))
    beats, beat_type = int(first.findtext('time/beats')), int(first.findtext('time/beat-type'))
    page_time = page.get('time', ['4/4'])[0]
    want_time = '2/4' if length == 'half' else page_time
    if f'{beats}/{beat_type}' != want_time:
        out.append(f'time {beats}/{beat_type}, not {want_time}')
    bar_len = beats * 4 * div // beat_type
    measures = part.findall('measure')
    if len(measures) != (2 if length == 'two' else 1):
        out.append(f'{len(measures)} bars')
    notes, kinds, prev_rest = [], [], None  # a rest at the end of a bar comes before the next bar's first note
    for bi, m in enumerate(measures):
        pos = 0
        for el in m.findall('note'):
            d = int(el.findtext('duration'))
            rest = el.find('rest') is not None
            kinds.append((el.findtext('type'), el.find('dot') is not None, rest))
            if bi == 0 and pos == 0 and rest:
                out.append('starts with a rest')
            if not rest:
                p = el.find('pitch')
                k = (p.findtext('step'), int(p.findtext('alter') or 0), int(p.findtext('octave')))
                a = R['allowed'].get(k)
                if not a:
                    out.append(f'{k} is not one of the page\'s notes')
                elif el.get('color') != a['color'] or el.findtext('notations/technical/fingering') != a['label']:
                    out.append(f"{a['name']} marked wrongly")
                else:
                    notes.append({'dia': k[2] * 7 + LETTERS.index(k[0]), 'name': a['name'], 'string': a['string'], 'len': d, 'after_rest': prev_rest, 'bar': bi})
            prev_rest = rest
            pos += d
        if pos != bar_len:
            out.append(f'bar {bi + 1} adds up to {pos}, not {bar_len}')
    if any(t == 'whole' for t, _, r in kinds if not r):
        out.append('a whole note')
    allowed_types = {'w': ('whole', False), 'h.': ('half', True), 'h': ('half', False), 'q': ('quarter', False), 'qr': ('quarter', False), 'hr': ('half', False)}
    for t, dot, rest in kinds:
        ok = (t == 'eighth' and ('8 8' in page['rhythms'] or 'q. 8' in page['rhythms'])) or \
             (t == 'quarter' and dot and 'q. 8' in page['rhythms']) or \
             any(allowed_types.get(tok) == (t, dot) and (tok.endswith('r') == rest) for tok in page['rhythms'])
        if not ok:
            out.append(f"rhythm {t}{'.' if dot else ''}{' rest' if rest else ''} is not one of the page's")
    steps = [(b['dia'] - a['dia']) for a, b in zip(notes, notes[1:])]
    for a, b in zip(notes, notes[1:]):
        if abs(a['dia'] - b['dia']) + 1 > page.get('maxLeap', 3):
            out.append(f"a leap from {a['name']} to {b['name']}")
        if no_repeats and a['dia'] == b['dia'] and a['name'] == b['name']:
            out.append(f"{a['name']} twice in a row")
        if a['string'] != b['string'] and not b['after_rest'] and page.get('crossings', 'some') != 'free' and (a['len'] == 1 or b['len'] == 1):
            out.append(f"a crossing on an eighth ({a['name']} to {b['name']})")
    shape = ex['shape']
    if shape == 'run' and not (steps and all(x == steps[0] and abs(x) == 1 for x in steps)):
        out.append(f'a run that is not all steps one way ({steps})')
    if shape == 'turn' and not (steps and all(abs(x) == 1 for x in steps) and sum(1 for x, y in zip(steps, steps[1:]) if x != y) <= 1):
        out.append(f'a turn that is not steps turning once ({steps})')
    if shape == 'skip' and sum(1 for x in steps if abs(x) >= 2) != 1:
        out.append(f'a skip pattern without exactly one skip ({steps})')
    if shape == 'cell':
        bars_rhythm = ex['rhythm']
        if len(set(bars_rhythm)) != 1 and length == 'two':
            out.append(f'a repeated rhythm whose bars differ ({bars_rhythm})')
    beats_want = {'half': 2, 'bar': bar_len / div, 'two': 2 * bar_len / div}[length]
    if abs(ex['beats'] - beats_want) > 1e-9:
        out.append(f"length {ex['beats']} beats, not {beats_want}")
    if ex['at'] != [len(measures), len(notes)]:
        out.append(f"alphaTab read {ex['at']}, the file has {[len(measures), len(notes)]}")
    return out


PATTERN_JS = '''async ({ page, inst, length, noRepeats, from, to }) => {
  const out = [];
  for (let n = from; n <= to; n++) {
    let ex = null, at = null, error = null, again = null;
    try {
      ex = SightReading.pattern(page, inst, n, { length, noRepeats });
      again = SightReading.pattern(page, inst, n, { length, noRepeats }).xml === ex.xml;
      const score = alphaTab.importer.ScoreLoader.loadScoreFromBytes(new TextEncoder().encode(ex.xml), new alphaTab.Settings());
      const bars = score.tracks[0].staves[0].bars;
      at = [bars.length, bars.reduce((k, b) => k + b.voices[0].beats.filter(x => !x.isRest).length, 0)];
    } catch (e) { error = String(e && e.message || e); }
    out.push(ex ? { xml: ex.xml, shape: ex.shape, rhythm: ex.rhythm, beats: ex.beats, at, again, error, n } : { error, n });
  }
  return out;
}'''
FLASH_COUNT = int(os.environ.get('FLASH_COUNT', '300'))


# ---- Running the generator in the browser ----
MAKE_JS = '''async ({ pages, from, to }) => {
  const out = [];
  for (const page of pages) for (const inst of ['violin', 'viola']) for (let n = from; n <= to; n++) {
    let xml = null, at = null, again = null, error = null;
    try {
      xml = SightReading.exercise(page, inst, n).xml;
      again = SightReading.exercise(page, inst, n).xml === xml;
      const s = new alphaTab.Settings();
      const score = alphaTab.importer.ScoreLoader.loadScoreFromBytes(new TextEncoder().encode(xml), s);
      const bars = score.tracks[0].staves[0].bars;
      at = [bars.length, bars.reduce((k, b) => k + b.voices[0].beats.filter(x => !x.isRest).length, 0)];
    } catch (e) { error = String(e && e.message || e); }
    out.push({ page: page.id, inst, n, xml, at, again, error });
  }
  return out;
}'''


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


async def main():
    began = time.monotonic()
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{httpd.server_address[1]}'
    failures, done = [], 0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        pg = await browser.new_page()
        await pg.goto(f'{base}/sight-reading/practice.css')  # any page of the site, so the scripts load from it
        await pg.add_script_tag(url=f'{base}/sight-reading/generator.js')
        if os.environ.get('ALPHATAB_JS'):
            await pg.add_script_tag(path=os.environ['ALPHATAB_JS'])
        else:
            await pg.add_script_tag(url='https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/alphaTab.min.js')
        # The book pages' rules make sense (the made-up pages too).
        for page in PAGES + TRY_PAGES:
            said = await pg.evaluate('(p) => SightReading.problems(p)', page)
            if said:
                failures.append(f"{page['id']}: {said}")
        pages = PAGES + TRY_PAGES
        for page in pages:
            bad = {}
            for start in range(1, COUNT + 1, 250):
                got = await pg.evaluate(MAKE_JS, {'pages': [page], 'from': start, 'to': min(COUNT, start + 249)})
                for ex in got:
                    done += 1
                    where = f"{ex['page']} {ex['inst']} #{ex['n']}"
                    if ex['error']:
                        bad.setdefault('could not be made or read: ' + ex['error'], []).append(where)
                        continue
                    if not ex['again']:
                        bad.setdefault('the same number gave different music', []).append(where)
                    for problem in check(page, ex['inst'], ex['n'], ex['xml'], ex['at']):
                        bad.setdefault(problem.split(':')[-1].strip() if problem.startswith('bar ') else problem, []).append(where)
            tag = '[book page]' if page in PAGES else '[made-up page]'
            if bad:
                for what, where in list(bad.items())[:8]:
                    failures.append(f"{page['id']}: {what} ({len(where)} exercise(s), e.g. {', '.join(where[:3])})")
                print(f"  FAIL  {page['id']} {tag}: {sum(len(w) for w in bad.values())} problem(s)")
            else:
                print(f"  ok    {page['id']} {tag}: {2 * COUNT} exercises (violin and viola) follow the rules")
        # Flash a bar's patterns.
        for page in pages:
            bad, made, shapes = {}, 0, {}
            lengths = await pg.evaluate('(p) => SightReading.flashLengths(p)', page)
            for inst in ('violin', 'viola'):
                for length in lengths:
                    for no_rep in (False, True):
                        got = await pg.evaluate(PATTERN_JS, {'page': page, 'inst': inst, 'length': length, 'noRepeats': no_rep, 'from': 1, 'to': FLASH_COUNT})
                        for ex in got:
                            where = f"{page['id']} {inst} {length}{' no repeats' if no_rep else ''} #{ex['n']}"
                            if ex['error']:
                                bad.setdefault('could not be made or read: ' + ex['error'], []).append(where); continue
                            made += 1
                            shapes[ex['shape']] = shapes.get(ex['shape'], 0) + 1
                            if not ex['again']:
                                bad.setdefault('the same number gave a different pattern', []).append(where)
                            for problem in check_pattern(page, inst, length, no_rep, ex):
                                bad.setdefault(problem, []).append(where)
            tag = '[book page]' if page in PAGES else '[made-up page]'
            if bad:
                for what, where in list(bad.items())[:8]:
                    failures.append(f"{page['id']} patterns: {what} ({len(where)}, e.g. {', '.join(where[:3])})")
                print(f"  FAIL  {page['id']} {tag}: Flash a bar patterns, {sum(len(w) for w in bad.values())} problem(s)")
            else:
                print(f"  ok    {page['id']} {tag}: {made} Flash a bar patterns follow the rules ({', '.join(f'{k} {v}' for k, v in sorted(shapes.items()))})")
            done += made
        # Violin and viola with one number: the same exercise, a fifth apart (when the page has no viola notes of its own).
        same = await pg.evaluate('''(page) => { const v = SightReading.exercise(page, 'violin', 42), a = SightReading.exercise(page, 'viola', 42);
          return v.rhythm.join() === a.rhythm.join() && v.notes.length === a.notes.length; }''', PAGES[0])
        print(('  ok    ' if same else '  FAIL  ') + 'violin and viola get the same exercise for the same number')
        if not same:
            failures.append('violin and viola differ for the same number')
        await browser.close()
    httpd.shutdown()
    took = round(time.monotonic() - began)
    print(f'\n{done} exercises checked in {took // 60} min {took % 60} s.')
    if failures:
        print(f'{len(failures)} problem(s):')
        for f in failures:
            print('  - ' + f)
        sys.exit(1)
    print('All checks passed.')


asyncio.run(main())
