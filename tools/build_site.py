"""Build the song pages and the home-page song list.

Run from anywhere:  python3 tools/build_site.py

Reads
  reader/reader.html           the master reader (also the private Claude preview, with the conductor)
  songs.json                   one entry per song, in the order they appear on the home page
  songs/<slug>/<slug>.xml      each song's score (copied in from the Music Arrangements folder)

Writes
  songs/<slug>/index.html      the reader for that song
  index.html                   only the song cards between <!-- songs:start --> and <!-- songs:end -->,
                               and the app script between <!-- app:start --> and <!-- app:end -->
  sw.js                        the offline copy (from tools/sw_template.js): every page and file the site
                               needs, each with a fingerprint, so a change reaches copies already on phones

The app layer (offline copy, install button, iPhone sound) lives in app/app.js and sw.js, apart from
the reader. The home-screen app file is manifest.webmanifest, with its icons in assets/.

Key, time signature, bar count and the written tempo are read from the score (key, time and
bars can be given in songs.json too; if one disagrees with the score, the build stops so a bad
scan or a stale entry gets noticed). The build also stops if the score's parts aren't one of the two
layouts the reader knows, in BUILD-SPEC order, and says which one it read:
  six tiers, 24 parts (songs built before 2026-10-16): level by level, violin-viola-cello-bass in each
  levels and voices, 34 parts: level by level; Melody, Inner, Bass Line in each; then violin-viola-cello-bass
  (Inner on violin and viola only)

songs.json fields
  slug        folder and file name, lowercase-with-dashes ("holy-holy-holy")
  title       shown on the page and the home card
  category    small label on the home card ("Christmas", "Hymn")
  collection  small label in the song's About box ("Christmas Collection")
  source      one line on where the tune comes from ("Traditional English carol")
  pdf_url     Payhip (or other) link for the printable parts; "" = no Buy button
  key, time, bars   optional overrides; normally left out
"""
import hashlib, html, json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READER = ROOT / 'reader' / 'reader.html'
SW_TEMPLATE = ROOT / 'tools' / 'sw_template.js'
MANIFEST = ROOT / 'manifest.webmanifest'
FONT = 'assets/font/Bravura.woff2'
SOUNDFONT = 'assets/soundfont/strings-generaluser-sf2.b64.txt'
ALPHATAB = 'https://cdn.jsdelivr.net/npm/@coderline/alphatab@1.8.4/dist/alphaTab.min.js'
# Kept offline besides the pages, scores, font, sounds and reader: the small files the pages ask for.
APP_FILES = ['app/app.js', 'manifest.webmanifest', 'assets/icon.svg', 'assets/apple-touch-icon.png',
             'assets/icon-192.png', 'assets/icon-512.png', 'assets/icon-maskable-512.png']

# The reader is written for The First Noel (that is what the Claude preview plays).
# These are the song-specific strings in it; each must appear exactly the stated number of times.
TEMPLATE = {
    'title': 'The First Noel',
    'collection': 'Christmas Collection',
    'source': 'Traditional English carol',
    'key': 'D major', 'time': '3/4', 'bars': '25 bars',
    'lede': 'Six levels for violin, viola, cello and bass.',  # About box; a 34-part song says what it has instead
    'score': 'scores/the-first-noel.xml',
    'storage': 'first-noel-reader',
    'tempo': 'const BASE_TEMPO = 100; // Andante, from bar 1 of the score',
    'tempo_percent': 'const TEMPO_PERCENT = false;',
}

MAJOR = {-7: 'C-flat', -6: 'G-flat', -5: 'D-flat', -4: 'A-flat', -3: 'E-flat', -2: 'B-flat', -1: 'F',
         0: 'C', 1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F-sharp', 7: 'C-sharp'}
MINOR = {-7: 'A-flat', -6: 'E-flat', -5: 'B-flat', -4: 'F', -3: 'C', -2: 'G', -1: 'D',
         0: 'A', 1: 'E', 2: 'B', 3: 'F-sharp', 4: 'C-sharp', 5: 'G-sharp', 6: 'D-sharp', 7: 'A-sharp'}

HEAD = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#E6EAE8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0F1513" media="(prefers-color-scheme: dark)">
<link rel="icon" href="../../assets/icon.svg" type="image/svg+xml">
<link rel="manifest" href="../../manifest.webmanifest">
<link rel="apple-touch-icon" href="../../assets/apple-touch-icon.png">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Graded Strings">
<style>body{margin:0;padding:0}img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}</style>
'''
HOME_LINK_CSS = ('.home-link { display: inline-block; margin: 0 0 6px; color: var(--muted); font-size: 0.86rem; '
                 'font-weight: 600; text-decoration: none; }\n.home-link:hover { color: var(--accent); }\n')


def fail(msg):
    sys.exit(f'build_site: {msg}')


def fingerprint(data):
    """A short fingerprint of a file's contents: it changes whenever the file does."""
    if isinstance(data, Path):
        data = data.read_bytes()
    elif isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()[:10]


def app_script(up, app_rev):
    """The tag that starts the app layer (offline copy, iPhone sound). up: the way to the site root."""
    return f'<script src="{up}app/app.js?v={app_rev}"></script>\n'


def read_score(path):
    """Key, time signature and bar count as the reader's About box shows them.

    A score that changes key or time partway through lists each one once, in the order it first
    appears ("E minor, A minor"; "4/4, 6/8, 3/4")."""
    root = ET.parse(path).getroot()
    part = root.find('part')
    if part is None:
        fail(f'{path} has no parts')
    measures = part.findall('measure')
    first = measures[0]
    if first.findtext('attributes/key/fifths') is None or first.findtext('attributes/time/beats') is None:
        fail(f'{path}: no key or time signature in the first bar')
    keys, times, mode = [], [], 'major'
    for m in measures:
        fifths = m.findtext('attributes/key/fifths')
        if fifths is not None:
            mode = (m.findtext('attributes/key/mode') or mode).strip()
            names = MINOR if mode == 'minor' else MAJOR
            k = f"{names[int(fifths)]} {'minor' if mode == 'minor' else 'major'}"
            if k not in keys:
                keys.append(k)
        beats = m.findtext('attributes/time/beats')
        if beats is not None:
            t = f"{beats}/{m.findtext('attributes/time/beat-type')}"
            if t not in times:
                times.append(t)
    key = ', '.join(keys)
    # Written tempo (quarter notes per minute) from the first tempo mark; alphaTab plays 120 when there is none.
    marks = [round(float(x.get('tempo'))) for x in part.iter('sound') if x.get('tempo')]
    tempo = marks[0] if marks else 120
    names_found = [sp.findtext('part-name') or '' for sp in root.find('part-list').findall('score-part')]
    return {'key': key, 'time': ', '.join(times), 'bars': len(measures), 'tempo': tempo,
            'tempo_marked': bool(marks), 'tempos': marks, 'parts': len(root.findall('part')),
            'part_names': names_found}


# The reader picks parts by position, so a score's parts must be in one of its two layouts (BUILD-SPEC section 3),
# each part named "<instrument> — <level or level and voice>". A score built to BUILD-SPEC comes out this way.
INSTRUMENTS = ['Violin', 'Viola', 'Cello', 'Bass']
TIERS = ['Open Strings', 'Easy', 'Melody', 'Harmony', 'Advanced Melody', 'Obbligato']
VOICES = [(inst, 'Open Strings') for inst in INSTRUMENTS]
for level in ['Easy ', '', 'Advanced ']:  # the Intermediate level has no word in the part names
    VOICES += [(inst, level + 'Melody') for inst in INSTRUMENTS]
    VOICES += [(inst, level + 'Inner') for inst in INSTRUMENTS[:2]]  # cello and bass take the bass line instead
    VOICES += [(inst, level + 'Bass Line') for inst in INSTRUMENTS]
LAYOUTS = {
    'six tiers': [(inst, tier) for tier in TIERS for inst in INSTRUMENTS],  # songs built before 2026-10-16
    'levels and voices': VOICES,
}
PART_NAME = re.compile(r'(Violin|Viola|Cello|Bass)\s*[—–-]\s*(.*?)(?:\s*\(pizz\.\))?$')


def part_layout(slug, names):
    """Which of the reader's layouts the score's parts are in. Stops the build if they're in neither."""
    for layout, want in LAYOUTS.items():
        if len(names) == len(want):
            break
    else:
        fail(f'{slug}: {len(names)} parts; the reader needs 24 (six tiers, songs built before 2026-10-16) '
             'or 34 (levels and voices)')
    for i, (name, (inst, label)) in enumerate(zip(names, want)):
        m = PART_NAME.match(name.strip())
        if not m or m.groups() != (inst, label):
            fail(f'{slug}: part {i + 1} is named {name!r}; the reader expects {inst} — {label} there '
                 f'({len(want)} parts: {layout})')
    return layout


def replace(text, old, new, count=1):
    n = text.count(old)
    if n != count:
        fail(f'reader.html: expected {count} of {old!r}, found {n}. '
             'The reader changed; update TEMPLATE / the replacements in tools/build_site.py.')
    return text.replace(old, new)


def song_page(reader, song, facts, app, revs):
    e = html.escape
    cut = reader.index('</style>') + len('</style>')
    head, body = reader[:cut], reader[cut:]
    t = TEMPLATE
    head = replace(head, f"<title>{t['title']}</title>", f"<title>{e(song['title'])}</title>")
    levels = 'six levels' if facts['layout'] == 'six tiers' else 'four levels'
    head = replace(head, f"play along with {t['title']} in six levels", f"play along with {e(song['title'])} in {levels}")
    head = replace(head, '</style>', HOME_LINK_CSS + '</style>')

    b = body
    b = replace(b, t['lede'], t['lede'] if facts['layout'] == 'six tiers' else
                'Four levels for violin, viola, cello and bass, each with a melody, an inner part and a bass line.')
    b = replace(b, f">{t['title']}<span class=\"info-i\"", f">{e(song['title'])}<span class=\"info-i\"")
    b = replace(b, f"<p class=\"info-title\">{t['title']}</p>", f"<p class=\"info-title\">{e(song['title'])}</p>")
    b = replace(b, f"<p class=\"eyebrow\">{t['collection']}</p>", f"<p class=\"eyebrow\">{e(song.get('collection', ''))}</p>")
    b = replace(b, f"<p class=\"info-src\">{t['source']}</p>", f"<p class=\"info-src\">{e(song.get('source', ''))}</p>")
    b = replace(b, f"<dt>Key</dt><dd>{t['key']}</dd>", f"<dt>Key</dt><dd>{e(facts['key'])}</dd>")
    b = replace(b, f"<dt>Time</dt><dd>{t['time']}</dd>", f"<dt>Time</dt><dd>{e(facts['time'])}</dd>")
    b = replace(b, f"<dt>Length</dt><dd>{t['bars']}</dd>", f"<dt>Length</dt><dd>{facts['bars']} bars</dd>")
    slug = song['slug']
    b = replace(b, t['tempo'], f"const BASE_TEMPO = {facts['tempo']}; // written tempo, from bar 1 of the score")
    # A score that changes tempo: the tempo control reads as a percentage of the written tempos.
    b = replace(b, t['tempo_percent'], f"const TEMPO_PERCENT = {'true' if len(set(facts['tempos'])) > 1 else 'false'};")
    # Each file address carries its fingerprint, so a page never gets an older or newer copy than it was built with.
    b = replace(b, f"const SCORE_URL = '{t['score']}';", f"const SCORE_URL = '{slug}.xml?v={revs['score']}';")
    b = replace(b, "const FONT_URL = 'font/Bravura.woff2';", f"const FONT_URL = '../../{FONT}?v={revs['font']}';")
    b = replace(b, "const SOUNDFONT_URL = 'soundfont/strings-generaluser-sf2.b64.txt';",
                f"const SOUNDFONT_URL = '../../{SOUNDFONT}?v={revs['soundfont']}';")
    pdf = song.get('pdf_url', '')
    if "'" in pdf or '\\' in pdf:
        fail(f"{slug}: pdf_url can't contain quotes or backslashes")
    b = replace(b, "const PDF_URL = '';", f"const PDF_URL = '{pdf}';")
    # Saved settings (instrument, level, zoom...) are kept per song.
    b = replace(b, f"'{t['storage']}'", f"'{slug}-reader'", count=2)
    # No store link yet: no Buy button at all rather than a greyed-out one.
    b = replace(b, "  else { $('buyNote').textContent = 'PDF store link coming soon. Free to read and play along here.'; }",
                "  else { $('buyPending').hidden = true; $('buyNote').textContent = 'Free to read and play along.'; }")
    # A way back to the song list.
    b = replace(b, '    <div class="title-wrap">\n', '    <div class="title-wrap">\n      <a class="home-link" href="../../">← All songs</a>\n')
    return HEAD + app + head + '\n</head>\n<body>\n' + b.lstrip('\n') + '\n</body>\n</html>\n'


def home_cards(songs, facts):
    e = html.escape
    out = []
    for s in songs:
        f = facts[s['slug']]
        line = ' · '.join(x for x in [s.get('source', ''), f['key'], f['time']] if x)
        out.append(
            f'      <a class="song" href="songs/{s["slug"]}/">\n'
            f'        <span class="eyebrow">{e(s.get("category", ""))}</span>\n'
            f'        <h3>{e(s["title"])}</h3>\n'
            f'        <p>{e(line)}</p>\n'
            f'        <span class="go">Open and play along →</span>\n'
            f'      </a>\n')
    return ''.join(out)


def main():
    reader = READER.read_text(encoding='utf-8')
    songs = json.loads((ROOT / 'songs.json').read_text(encoding='utf-8'))
    for need in [FONT, SOUNDFONT, 'tools/sw_template.js', *APP_FILES]:
        if not (ROOT / need).exists():
            fail(f'missing {need}')
    try:
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    except ValueError as e:
        fail(f'manifest.webmanifest is not valid JSON: {e}')
    for icon in manifest.get('icons', []):
        if icon['src'] not in APP_FILES:
            fail(f"manifest.webmanifest lists {icon['src']}; add it to APP_FILES in tools/build_site.py")
    if reader.count(ALPHATAB) != 1:
        fail(f'reader.html no longer loads {ALPHATAB}; update ALPHATAB in tools/build_site.py')
    shared = {'font': fingerprint(ROOT / FONT), 'soundfont': fingerprint(ROOT / SOUNDFONT)}
    app_rev = fingerprint(ROOT / 'app/app.js')
    offline = {f: fingerprint(ROOT / f) for f in APP_FILES}
    offline[f"{FONT}?v={shared['font']}"] = shared['font']
    offline[f"{SOUNDFONT}?v={shared['soundfont']}"] = shared['soundfont']
    offline[ALPHATAB] = '1.8.4'
    seen, facts = set(), {}
    for s in songs:
        slug = s.get('slug', '')
        if not slug or slug != slug.lower() or ' ' in slug or slug in seen:
            fail(f'bad or repeated slug {slug!r}')
        seen.add(slug)
        if not s.get('title'):
            fail(f'{slug}: no title')
        score = ROOT / 'songs' / slug / f'{slug}.xml'
        if not score.exists():
            fail(f'{slug}: score not found at {score.relative_to(ROOT)}')
        got = read_score(score)
        got['layout'] = part_layout(slug, got['part_names'])
        for k in ('key', 'time', 'bars'):
            if k in s and str(s[k]) != str(got[k]):
                fail(f'{slug}: songs.json says {k} = {s[k]!r} but the score says {got[k]!r}')
        facts[slug] = {**got, **{k: s[k] for k in ('key', 'time', 'bars') if k in s}}
        score_rev = fingerprint(score)
        page = song_page(reader, s, facts[slug], app_script('../../', app_rev), {**shared, 'score': score_rev})
        (ROOT / 'songs' / slug / 'index.html').write_text(page, encoding='utf-8', newline='\n')
        offline[f'songs/{slug}/'] = fingerprint(page)
        offline[f'songs/{slug}/{slug}.xml?v={score_rev}'] = score_rev
        print(f"  {slug}: {facts[slug]['key']}, {facts[slug]['time']}, {facts[slug]['bars']} bars, "
              f"quarter = {got['tempo']}, {got['parts']} parts ({got['layout']}){', Buy link' if s.get('pdf_url') else ''}")
        if not got['tempo_marked']:
            print(f'  note: {slug} has no tempo mark in the score, so it plays at quarter = 120')
        if len(set(got['tempos'])) > 1:
            print(f"  tempo changes: {' -> '.join(map(str, got['tempos']))} (tempo control shows a percentage)")

    home = (ROOT / 'index.html').read_text(encoding='utf-8')
    a, z = '<!-- songs:start', '      <!-- songs:end -->'
    if home.count(a) != 1 or home.count(z) != 1:
        fail('index.html: song list markers missing')
    i = home.index('\n', home.index(a)) + 1
    j = home.index(z)
    home = home[:i] + home_cards(songs, facts) + home[j:]
    a, z = '<!-- app:start', '<!-- app:end -->'
    if home.count(a) != 1 or home.count(z) != 1:
        fail('index.html: app script markers missing from <head>')
    i = home.index('\n', home.index(a)) + 1
    j = home.index(z)
    home = home[:i] + app_script('', app_rev) + home[j:]
    (ROOT / 'index.html').write_text(home, encoding='utf-8', newline='\n')
    offline['./'] = fingerprint(home)

    # The offline copy: every file above with its fingerprint, and the Google Fonts lettering the pages use.
    fonts = sorted(set(re.findall(r'href="(https://fonts\.googleapis\.com/css2\?[^"]+)"', reader + home)))
    files = dict(sorted(offline.items()))
    sw = SW_TEMPLATE.read_text(encoding='utf-8')
    version = fingerprint(sw + json.dumps(files) + json.dumps(fonts))
    sw = sw.replace('// sw.js is written by tools/build_site.py from tools/sw_template.js: edit the template, never sw.js.',
                    '// Written by tools/build_site.py from tools/sw_template.js. Do not edit by hand.')
    for old, new in [('__VERSION__', version), ('__FILES__', json.dumps(files)), ('__FONT_CSS__', json.dumps(fonts))]:
        if sw.count(old) != 1:
            fail(f'tools/sw_template.js: expected one {old}')
        sw = sw.replace(old, new)
    (ROOT / 'sw.js').write_text(sw, encoding='utf-8', newline='\n')
    size = sum((ROOT / f.split('?')[0]).stat().st_size for f in files if not f.startswith('http') and not f.endswith('/'))
    print(f'built {len(songs)} song page(s) and the home page list')
    print(f'offline copy {version}: {len(files)} files, {size / 1e6:.1f} MB (plus the pages and the music reader)')


if __name__ == '__main__':
    main()
