"""Build the song pages and the home-page song list.

Run from anywhere:  python3 tools/build_site.py

Reads
  reader/reader.html           the master reader (also the private Claude preview, with the conductor)
  songs.json                   one entry per song, in the order they appear on the home page
  songs/<slug>/<slug>.xml      each song's score (copied in from the Music Arrangements folder)

Writes
  songs/<slug>/index.html      the reader for that song
  index.html                   only the song cards between <!-- songs:start --> and <!-- songs:end -->

Key, time signature, bar count and the written tempo are read from the score (key, time and
bars can be given in songs.json too; if one disagrees with the score, the build stops so a bad
scan or a stale entry gets noticed). The build also stops if the score doesn't have the 24 parts
in the order the reader expects: level by level, violin-viola-cello-bass within each level.

songs.json fields
  slug        folder and file name, lowercase-with-dashes ("holy-holy-holy")
  title       shown on the page and the home card
  category    small label on the home card ("Christmas", "Hymn")
  collection  small label in the song's About box ("Christmas Collection")
  source      one line on where the tune comes from ("Traditional English carol")
  pdf_url     Payhip (or other) link for the printable parts; "" = no Buy button
  key, time, bars   optional overrides; normally left out
"""
import html, json, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READER = ROOT / 'reader' / 'reader.html'

# The reader is written for The First Noel (that is what the Claude preview plays).
# These are the song-specific strings in it; each must appear exactly the stated number of times.
TEMPLATE = {
    'title': 'The First Noel',
    'collection': 'Christmas Collection',
    'source': 'Traditional English carol',
    'key': 'D major', 'time': '3/4', 'bars': '25 bars',
    'score': 'scores/the-first-noel.xml',
    'storage': 'first-noel-reader',
    'tempo': 'const BASE_TEMPO = 100; // Andante, from bar 1 of the score',
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


def read_score(path):
    """Key, time signature and bar count as the reader's About box shows them."""
    root = ET.parse(path).getroot()
    part = root.find('part')
    if part is None:
        fail(f'{path} has no parts')
    measures = part.findall('measure')
    first = measures[0]
    fifths = first.findtext('attributes/key/fifths')
    mode = (first.findtext('attributes/key/mode') or 'major').strip()
    beats = first.findtext('attributes/time/beats')
    beat_type = first.findtext('attributes/time/beat-type')
    if fifths is None or beats is None:
        fail(f'{path}: no key or time signature in the first bar')
    names = MINOR if mode == 'minor' else MAJOR
    key = f"{names[int(fifths)]} {'minor' if mode == 'minor' else 'major'}"
    # Written tempo (quarter notes per minute) from the first tempo mark; alphaTab plays 120 when there is none.
    sound = next((x for x in root.iter('sound') if x.get('tempo')), None)
    tempo = round(float(sound.get('tempo'))) if sound is not None else 120
    names_found = [sp.findtext('part-name') or '' for sp in root.find('part-list').findall('score-part')]
    return {'key': key, 'time': f'{beats}/{beat_type}', 'bars': len(measures), 'tempo': tempo,
            'tempo_marked': sound is not None, 'parts': len(root.findall('part')), 'part_names': names_found}


# The reader picks parts by position: level by level (in this order), and within each level
# violin, viola, cello, bass. A score built to BUILD-SPEC comes out this way.
LEVELS = ['Open Strings', 'Easy', 'Melody', 'Harmony', 'Advanced Melody', 'Obbligato']
INSTRUMENTS = ['Violin', 'Viola', 'Cello', 'Bass']


def check_part_order(slug, names):
    if len(names) != 24:
        fail(f'{slug}: {len(names)} parts; the reader needs 24 (6 levels x 4 instruments)')
    for i, name in enumerate(names):
        inst, level = INSTRUMENTS[i % 4], LEVELS[i // 4]
        if not name.startswith(inst) or level not in name:
            fail(f'{slug}: part {i + 1} is named {name!r}; the reader expects {inst}, {level} there')
        if level == 'Melody' and 'Advanced' in name:
            fail(f'{slug}: part {i + 1} is named {name!r}; the reader expects {inst}, Melody there')


def replace(text, old, new, count=1):
    n = text.count(old)
    if n != count:
        fail(f'reader.html: expected {count} of {old!r}, found {n}. '
             'The reader changed; update TEMPLATE / the replacements in tools/build_site.py.')
    return text.replace(old, new)


def song_page(reader, song, facts):
    e = html.escape
    cut = reader.index('</style>') + len('</style>')
    head, body = reader[:cut], reader[cut:]
    t = TEMPLATE
    head = replace(head, f"<title>{t['title']}</title>", f"<title>{e(song['title'])}</title>")
    head = replace(head, f"play along with {t['title']} in six levels", f"play along with {e(song['title'])} in six levels")
    head = replace(head, '</style>', HOME_LINK_CSS + '</style>')

    b = body
    b = replace(b, f">{t['title']}<span class=\"info-i\"", f">{e(song['title'])}<span class=\"info-i\"")
    b = replace(b, f"<p class=\"info-title\">{t['title']}</p>", f"<p class=\"info-title\">{e(song['title'])}</p>")
    b = replace(b, f"<p class=\"eyebrow\">{t['collection']}</p>", f"<p class=\"eyebrow\">{e(song.get('collection', ''))}</p>")
    b = replace(b, f"<p class=\"info-src\">{t['source']}</p>", f"<p class=\"info-src\">{e(song.get('source', ''))}</p>")
    b = replace(b, f"<dt>Key</dt><dd>{t['key']}</dd>", f"<dt>Key</dt><dd>{e(facts['key'])}</dd>")
    b = replace(b, f"<dt>Time</dt><dd>{t['time']}</dd>", f"<dt>Time</dt><dd>{e(facts['time'])}</dd>")
    b = replace(b, f"<dt>Length</dt><dd>{t['bars']}</dd>", f"<dt>Length</dt><dd>{facts['bars']} bars</dd>")
    slug = song['slug']
    b = replace(b, t['tempo'], f"const BASE_TEMPO = {facts['tempo']}; // written tempo, from bar 1 of the score")
    b = replace(b, f"const SCORE_URL = '{t['score']}';", f"const SCORE_URL = '{slug}.xml';")
    b = replace(b, "const FONT_URL = 'font/Bravura.woff2';", "const FONT_URL = '../../assets/font/Bravura.woff2';")
    b = replace(b, "const SOUNDFONT_URL = 'soundfont/strings-generaluser-sf2.b64.txt';",
                "const SOUNDFONT_URL = '../../assets/soundfont/strings-generaluser-sf2.b64.txt';")
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
    return HEAD + head + '\n</head>\n<body>\n' + b.lstrip('\n') + '\n</body>\n</html>\n'


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
    for need in ['assets/font/Bravura.woff2', 'assets/soundfont/strings-generaluser-sf2.b64.txt', 'assets/icon.svg',
                 'assets/apple-touch-icon.png', 'manifest.webmanifest']:
        if not (ROOT / need).exists():
            fail(f'missing {need}')
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
        check_part_order(slug, got['part_names'])
        for k in ('key', 'time', 'bars'):
            if k in s and str(s[k]) != str(got[k]):
                fail(f'{slug}: songs.json says {k} = {s[k]!r} but the score says {got[k]!r}')
        facts[slug] = {**got, **{k: s[k] for k in ('key', 'time', 'bars') if k in s}}
        page = song_page(reader, s, facts[slug])
        (ROOT / 'songs' / slug / 'index.html').write_text(page, encoding='utf-8', newline='\n')
        print(f"  {slug}: {facts[slug]['key']}, {facts[slug]['time']}, {facts[slug]['bars']} bars, "
              f"quarter = {got['tempo']}, {got['parts']} parts{', Buy link' if s.get('pdf_url') else ''}")
        if not got['tempo_marked']:
            print(f'  note: {slug} has no tempo mark in the score, so it plays at quarter = 120')

    home = (ROOT / 'index.html').read_text(encoding='utf-8')
    a, z = '<!-- songs:start', '      <!-- songs:end -->'
    if home.count(a) != 1 or home.count(z) != 1:
        fail('index.html: song list markers missing')
    i = home.index('\n', home.index(a)) + 1
    j = home.index(z)
    home = home[:i] + home_cards(songs, facts) + home[j:]
    (ROOT / 'index.html').write_text(home, encoding='utf-8', newline='\n')
    print(f'built {len(songs)} song page(s) and the home page list')


if __name__ == '__main__':
    main()
