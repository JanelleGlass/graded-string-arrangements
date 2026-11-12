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
Duets (round 5), every page and pairing (violin and violin, violin and viola, viola and violin, viola and viola), 1,000
numbers with Part 2 on the same page and 250 for each other level (open strings, harder, each earlier book page), read back
from the score apart from the generator's own code: Part 1 is the exercise with that number; Part 2 in Part 1's key and its
own clef, only its level's notes (with their colors and finger numbers) and rhythms, no leap past its limit, starting
with a note and ending on the home note or its third; the two parts never cross and are never more than an octave apart,
a unison, third, fifth, sixth or octave on every strong beat and wherever both start a note, any other interval a second,
fourth or seventh with the note that moves stepping on one side, and no fifths or octaves in a row with both moving; over
each page, the parts move the same way under 30% of the time and share a bar's rhythm in under 20% of bars.
Besides the book pages in sight-reading/pages.json, a few made-up pages here try what those don't use yet: eighth
notes, dotted quarters, half rests, 2/4 and 3/4, 6 and 8 bars, low 2, few and free crossings, a viola page of its own.
"""
import asyncio, json, os, re, sys, threading, time
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


# ---- Duets (round 5) ----
SCALE_STEP = {'violin': 'GDAE', 'viola': 'CGDA'}


def key_alter(fifths, letter):
    sharps, flats = 'FCGDAEB', 'BEADGCF'
    return (1 if sharps.index(letter) < fifths else 0) if fifths > 0 else (-1 if flats.index(letter) < -fifths else 0) if fifths < 0 else 0


def first_position(inst, fifths, most):
    """Every note in first position in a key, fingers 0 to most, as {(letter, alter, octave): [(string, color, label)]}:
    each finger one step of the scale up a string whose open note is in the key."""
    out = {}
    for s in SCALE_STEP[inst]:
        if key_alter(fifths, s):
            continue
        for f in range(most + 1):
            letter = LETTERS[(LETTERS.index(s) + f) % 7]
            semis = (NATURAL[letter] - NATURAL[s]) % 12 + key_alter(fifths, letter)
            midi = OPEN[inst][s] + semis
            alter = key_alter(fifths, letter)
            octave = (midi - alter - NATURAL[letter]) // 12 - 1
            label = '0' if f == 0 else (('↓' if semis < USUAL[f] else '↑') + str(f) if semis != USUAL[f] else str(f))
            out.setdefault((letter, alter, octave), []).append((s, COLOR[s], label))
    return out


def page_notes(page, inst, fifths, tonic):
    """A page's notes for one instrument, in another key: the ones that key's signature has (not a minor key's 7th)."""
    out = {}
    for k, a in rules(page, inst)['allowed'].items():
        if k[1] == key_alter(fifths, k[0]):
            out.setdefault(k, []).append((a['string'], a['color'], a['label']))
    return out


def read_part(part, div):
    """One part of a score: its bars' rhythm tokens and its notes and rests, with where each starts (in divisions)."""
    events, bars, t = [], [], 0
    for m in part.findall('measure'):
        items, pos = [], 0
        for el in m.findall('note'):
            d = int(el.findtext('duration'))
            typ, dot, rest = el.findtext('type'), el.find('dot') is not None, el.find('rest') is not None
            items.append((typ + ('.' if dot else ''), rest, el.findtext('beam')))
            ev = {'t': t, 'pos': pos, 'len': d, 'rest': rest, 'bar': len(bars)}
            if not rest:
                p = el.find('pitch')
                k = (p.findtext('step'), int(p.findtext('alter') or 0), int(p.findtext('octave')))
                ev.update(key=k, midi=12 * (k[2] + 1) + NATURAL[k[0]] + k[1], dia=k[2] * 7 + LETTERS.index(k[0]),
                          color=el.get('color'), label=el.findtext('notations/technical/fingering'))
            events.append(ev)
            pos += d; t += d
        toks, i = [], 0
        while i < len(items):
            typ, rest, beam = items[i]
            nxt = items[i + 1] if i + 1 < len(items) else None
            if rest:
                tok = {'quarter': 'qr', 'half': 'hr', 'half.': 'h.r', 'whole': 'wr'}.get(typ, typ + 'r')
            elif typ == 'eighth' and beam == 'begin' and nxt and nxt[0] == 'eighth' and nxt[2] == 'end':
                tok, i = '8 8', i + 1
            elif typ == 'quarter.' and nxt and nxt[0] == 'eighth' and not nxt[1]:
                tok, i = 'q. 8', i + 1
            else:
                tok = {'whole': 'w', 'half.': 'h.', 'half': 'h', 'quarter': 'q'}.get(typ, typ)
            toks.append(tok); i += 1
        bars.append((toks, pos))
    return events, bars


CONSONANT, PASSING = {0, 3, 4, 7, 8, 9}, {2, 5, 10}


def check_duet(page, inst1, inst2, level, ex, pages):
    """Problems with one duet, in words; and its motion and rhythm counts for the totals."""
    out, stats = [], {'contrary': 0, 'similar': 0, 'oblique': 0, 'same_rhythm': 0, 'bars': 0}
    root = ET.fromstring(ex['xml'])
    names = [e.text for e in root.findall('part-list/score-part/part-name')]
    if names != [f'{inst1.capitalize()} — Part 1', f'{inst2.capitalize()} — Part 2']:
        out.append(f'parts named {names}')
    # Part 1 is the exercise with that number, note for note.
    solo_part = ex['solo'].split('<part id="P1">')[1].split('</part>')[0]
    if ex['xml'].split('<part id="P1">')[1].split('</part>')[0] != solo_part:
        out.append('Part 1 is not the exercise with that number')
    p1el, p2el = root.findall('part')
    a1, a2 = p1el.find('measure/attributes'), p2el.find('measure/attributes')
    div = int(a1.findtext('divisions'))
    fifths = int(a1.findtext('key/fifths'))
    if int(a2.findtext('key/fifths')) != fifths:
        out.append("Part 2 is not in Part 1's key")
    clef = (a2.findtext('clef/sign'), a2.findtext('clef/line'))
    if clef != (('G', '2') if inst2 == 'violin' else ('C', '3')):
        out.append(f'Part 2 in clef {clef}')
    beats, beat_type = int(a1.findtext('time/beats')), int(a1.findtext('time/beat-type'))
    bar_len = beats * 4 * div // beat_type
    strong_every = bar_len // 2 if bar_len == 8 else bar_len  # beats 1 and 3 in 4/4; beat 1 in 2/4 and 3/4
    e1, bars1 = read_part(p1el, div)
    e2, bars2 = read_part(p2el, div)
    if len(bars1) != len(bars2) or any(pos != bar_len for _, pos in bars2):
        out.append(f'Part 2 has {len(bars2)} bars adding up to {[pos for _, pos in bars2]}')
    # Part 2's notes and rhythms, by its level (a few open strings and first fingers, or more, where the page's own notes
    # can't make a part with this Part 1: widened 1 or 4).
    tonic = {'A': 'A', 'D': 'D', 'G': 'G', 'C': 'C', 'E': 'E', 'B': 'B', 'F': 'F'}[[k for k, v in MAJOR.items() if v == fifths][0][0]]
    earlier = next((p for p in pages if p['id'] == level), None)
    if level == 'open':
        allowed, toks, leap = first_position(inst2, fifths, 1), {'w', 'h.', 'h', 'q'}, 8
    elif level == 'harder':
        allowed, toks, leap = first_position(inst2, fifths, 4), {'w', 'h.', 'h', 'q', '8 8', 'q. 8', 'qr'} | set(page['rhythms']), 6
    else:
        src = earlier or page
        allowed, toks, leap = page_notes(src, inst2, fifths, tonic), set(src['rhythms']), max(5, src.get('maxLeap', 3))
        if len(allowed) < 3:  # too few notes for a part: open strings and first fingers too
            allowed = {**first_position(inst2, fifths, 1), **allowed}
    if ex['widened']:
        allowed = {**first_position(inst2, fifths, min(4, ex['widened'])), **allowed}
    if ex['widened'] >= 4:  # and quarter and half rests, then (5) a bar's rest now and then
        toks |= {'qr', 'hr'} | ({'wr', 'h.r'} if ex['widened'] == 5 else set())
    notes2 = [e for e in e2 if not e['rest']]
    for e in notes2:
        ways = allowed.get(e['key'])
        if not ways:
            out.append(f"Part 2 plays {e['key']}, not one of its notes ({level})")
        elif not any(c == e['color'] and lab == e['label'] for _, c, lab in ways):
            out.append(f"Part 2's {e['key']} marked {e['color']}/{e['label']}, not {ways}")
    for toks2, _ in bars2:
        for t in toks2:
            if t not in toks:
                out.append(f'Part 2 has rhythm {t!r} ({level})')
    for a, b in zip(notes2, notes2[1:]):
        if abs(a['dia'] - b['dia']) + 1 > leap:
            out.append(f"Part 2 leaps a {abs(a['dia'] - b['dia']) + 1} ({level})")
    # It starts with a note on beat 1, and ends on the home note or its third (or its fifth, over Part 1), on beat 1 of
    # the last bar.
    deg = lambda e: (LETTERS.index(e['key'][0]) - LETTERS.index(tonic)) % 7
    if not e2 or e2[0]['rest']:
        out.append('Part 2 starts with a rest')
    last = notes2[-1] if notes2 else None
    upper2 = ex['upper'] == 2
    if not last or last['bar'] != len(bars2) - 1 or last['pos'] != 0 or deg(last) not in ((0, 2, 4) if upper2 else (0, 2)):
        out.append(f"Part 2 ends on {last and last['key']} (bar {last and last['bar'] + 1}, at {last and last['pos']})")
    # The two parts together, at every moment either starts a note.
    def at(evs, t):
        for e in evs:
            if e['t'] <= t < e['t'] + e['len']:
                return e
    def steps_one_side(evs, e):
        notes = [x for x in evs if not x['rest']]
        i = notes.index(e)
        side = [abs(notes[j]['dia'] - e['dia']) == 1 for j in (i - 1, i + 1) if 0 <= j < len(notes)]
        return any(side)
    times = sorted({e['t'] for e in e1 + e2})
    signs, prev = set(), None
    for t in times:
        x, y = at(e1, t), at(e2, t)
        if not x or not y or x['rest'] or y['rest']:
            prev = None
            continue
        d = x['midi'] - y['midi']
        signs.add((d > 0) - (d < 0))
        gap = abs(d)
        if gap > 12:
            out.append(f'the parts are {gap} semitones apart at {t}')
        m = gap % 12
        both = x['t'] == t and y['t'] == t
        if (t % strong_every == 0 or both) and m not in CONSONANT:
            out.append(f"{'a strong beat' if t % strong_every == 0 else 'both starting'} at {t} is {gap} semitones apart")
        elif m not in CONSONANT:
            if m not in PASSING:
                out.append(f'{gap} semitones apart at {t}')
            moved = x if x['t'] == t else y
            if not steps_one_side(e1 if moved is x else e2, moved):
                out.append(f'a {gap}-semitone clash at {t} that does not pass by step')
        if prev:
            m1, m2 = x['midi'] - prev[0], y['midi'] - prev[1]
            if m1 and m2:
                if (m1 > 0) != (m2 > 0):
                    stats['contrary'] += 1
                else:
                    stats['similar'] += 1
                if prev[2] % 12 == m and m in (0, 7):
                    out.append(f"{'octaves' if m == 0 else 'fifths'} in a row at {t}")
            elif m1 or m2:
                stats['oblique'] += 1
        prev = (x['midi'], y['midi'], gap)
    if 1 in signs and -1 in signs:
        out.append('the parts cross')
    if (ex['upper'] == 1 and -1 in signs) or (ex['upper'] == 2 and 1 in signs):
        out.append(f"Part {ex['upper']} is not on top")
    for (t1, _), (t2, _) in list(zip(bars1, bars2))[:-1]:
        stats['bars'] += 1
        stats['same_rhythm'] += t1 == t2
    if ex['at'] != [[len(bars1), len([e for e in e1 if not e['rest']])], [len(bars2), len(notes2)]]:
        out.append(f"alphaTab read {ex['at']}")
    return out, stats


DUET_JS = '''async ({ page, earlier, inst1, inst2, level, from, to }) => {
  const out = [];
  for (let n = from; n <= to; n++) {
    let d = null, at = null, error = null, again = null, solo = null;
    try {
      d = SightReading.duet(page, inst1, inst2, n, earlier || level);
      again = SightReading.duet(page, inst1, inst2, n, earlier || level).xml === d.xml;
      solo = SightReading.exercise(page, inst1, n).xml;
      const score = alphaTab.importer.ScoreLoader.loadScoreFromBytes(new TextEncoder().encode(d.xml), new alphaTab.Settings());
      at = score.tracks.map(t => [t.staves[0].bars.length, t.staves[0].bars.reduce((k, b) => k + b.voices[0].beats.filter(x => !x.isRest).length, 0)]);
    } catch (e) { error = String(e && e.message || e); }
    out.push(d ? { xml: d.xml, solo, widened: d.widened, upper: d.upper, at, again, error, n } : { error, n });
  }
  return out;
}'''
DUET_COUNT = int(os.environ.get('DUET_COUNT', '1000'))  # numbers per page and pairing, Part 2 on the same page
DUET_OTHER = int(os.environ.get('DUET_OTHER', '250'))  # and for each other level
PAIRS = [('violin', 'violin'), ('violin', 'viola'), ('viola', 'violin'), ('viola', 'viola')]


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
        # The first exercises of every page, made now and again at the end: making duets or patterns in between must not
        # change them (nothing left behind from one piece of music to the next).
        SAME_JS = '(pages) => pages.flatMap(p => ["violin", "viola"].flatMap(i => Array.from({ length: 40 }, (_, k) => SightReading.exercise(p, i, k + 1).xml)))'
        first_made = await pg.evaluate(SAME_JS, pages)
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
        # Duets: every page and pairing, Part 2 on the same page (DUET_COUNT numbers), open strings, harder and each
        # earlier page (DUET_OTHER numbers each).
        for page in pages:
            k = pages.index(page)
            levels = [('same', DUET_COUNT), ('open', DUET_OTHER), ('harder', DUET_OTHER)] + [(p['id'], DUET_OTHER) for p in PAGES[:k] if page in PAGES]
            bad, made, widened = {}, 0, 0
            totals = {'contrary': 0, 'similar': 0, 'oblique': 0, 'same_rhythm': 0, 'bars': 0}
            for inst1, inst2 in PAIRS:
                for level, count in levels:
                    earlier = next((p for p in PAGES if p['id'] == level), None)
                    for start in range(1, count + 1, 250):
                        got = await pg.evaluate(DUET_JS, {'page': page, 'earlier': earlier, 'inst1': inst1, 'inst2': inst2, 'level': level, 'from': start, 'to': min(count, start + 249)})
                        for ex in got:
                            where = f"{page['id']} {inst1}+{inst2} {level} #{ex['n']}"
                            if ex['error']:
                                bad.setdefault('could not be made or read: ' + ex['error'], []).append(where); continue
                            made += 1
                            widened += bool(ex['widened'])
                            if not ex['again']:
                                bad.setdefault('the same number gave a different duet', []).append(where)
                            problems, stats = check_duet(page, inst1, inst2, level, ex, PAGES)
                            for key in totals:
                                totals[key] += stats[key]
                            for problem in problems:
                                bad.setdefault(re.sub(r' at \d+$', '', problem), []).append(where)
            moves = totals['contrary'] + totals['similar'] + totals['oblique']
            similar = totals['similar'] / max(1, moves)
            same_rhythm = totals['same_rhythm'] / max(1, totals['bars'])
            if similar > 0.3:
                bad.setdefault(f'the parts move the same way {round(100 * similar)}% of the time (want mostly against each other or one holding)', []).append(page['id'])
            if same_rhythm > 0.2:
                bad.setdefault(f'{round(100 * same_rhythm)}% of bars have the same rhythm in both parts (want the parts to take turns)', []).append(page['id'])
            tag = '[book page]' if page in PAGES else '[made-up page]'
            if bad:
                for what, where in list(bad.items())[:8]:
                    failures.append(f"{page['id']} duets: {what} ({len(where)}, e.g. {', '.join(where[:3])})")
                print(f"  FAIL  {page['id']} {tag}: duets, {sum(len(w) for w in bad.values())} problem(s)")
            else:
                print(f"  ok    {page['id']} {tag}: {made} duets follow the rules (4 pairings; moving against each other "
                      f"{round(100 * totals['contrary'] / max(1, moves))}%, one holding {round(100 * totals['oblique'] / max(1, moves))}%, "
                      f"the same way {round(100 * similar)}%; bars with the same rhythm {round(100 * same_rhythm)}%; "
                      f"with a few notes from outside Part 2's page {round(100 * widened / max(1, made))}%)")
            done += made
        again = await pg.evaluate(SAME_JS, pages)
        kept = again == first_made
        print(('  ok    ' if kept else '  FAIL  ') + 'after all the duets and patterns, every exercise number still gives the same music')
        if not kept:
            failures.append(f'exercises changed after making duets and patterns ({sum(a != b for a, b in zip(again, first_made))} of {len(again)})')
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
