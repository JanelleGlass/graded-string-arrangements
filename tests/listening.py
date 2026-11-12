"""Test of Flash a bar's listening (sight-reading/listen.js): made-up takes, and Janelle's recorded ones.

    python3 tests/listening.py

About three minutes. Uses the same Playwright and Chromium as tests/smoke.py, and ALPHATAB_JS in the same way (not needed
here, but harmless). The listening runs in the browser, as on the page.

Made-up takes (tests/listen_takes.js: a bowed string's sound, a little vibrato and noise, the count-in clicks heard by
the microphone, and the device's delay) for Flash a bar patterns on every book page, violin and viola, at 60 and 100:
  - played as written: every note right and on time
  - a note a semitone or a whole tone off: that note wrong, the others right
  - a note a third of a beat late or a quarter early: that note late or early; a tenth of a beat off is still on time
  - 10 cents off: right and in tune; 30 cents: right but not in tune; 70 cents: wrong
  - a note left out: not heard; nothing played, or only noise: nothing heard
  - quieter playing and a noisier room: still right
  - the timing check (open A on four clicks) finds the device's delay, and rounds judged with it are on time
Recorded takes: every take listed in tests/audio/takes.json (WAV files beside it, Janelle's own playing; public, her
choice, 2026-11-12), checked against what each one says was played.
"""
import asyncio, json, os, sys, threading, time, wave
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = json.loads((ROOT / 'sight-reading' / 'pages.json').read_text(encoding='utf-8'))
AUDIO = ROOT / 'tests' / 'audio'
sys.stdout.reconfigure(encoding='utf-8')

# Runs every made-up case in the browser and returns what the listening made of each.
CASES_JS = r'''async ({ pages, perPage }) => {
  const out = [];
  const make = (pat, tempo, inst, opts = {}) => {
    const beat = 60 / tempo, lat = opts.lat ?? 0.14, sr = 48000, T0 = 0.4 + 4 * beat;
    const clicks = [0, 1, 2, 3].map(i => ({ t: 0.4 + i * beat + lat, strong: !i }));
    const notes = [];
    pat.midis.forEach((m, i) => {
      if (opts.drop === i) return;
      const shift = (opts.shift && opts.shift[i] || 0) * beat;
      const end = ((pat.starts[i + 1] ?? pat.beats)) * beat;
      notes.push({ midi: m + (opts.wrong && opts.wrong[i] || 0), cents: opts.cents && opts.cents[i] || 0, t: T0 + pat.starts[i] * beat + shift + lat, dur: end - pat.starts[i] * beat - Math.max(0, shift) });
    });
    // One string, one note at a time: a note stops where the next one starts.
    for (let i = 0; i + 1 < notes.length; i++) notes[i].dur = Math.min(notes[i].dur, notes[i + 1].t - notes[i].t);
    if (opts.silent) notes.length = 0;
    const x = ListenTakes.take({ notes, clicks, length: T0 + pat.beats * beat + 0.8, seed: opts.seed || 1, loud: opts.loud ?? 0.25, noise: opts.noise ?? 0.004 });
    const played = Listen.notes(Listen.track(x, sr, inst)).map(n => ({ ...n, t0: n.t0 - T0 - (opts.offset ?? lat + 0.03), t1: n.t1 - T0 - (opts.offset ?? lat + 0.03) })).filter(n => n.t1 > -0.45 * beat);
    const res = Listen.judge(pat.midis.map((m, i) => ({ midi: m, t: pat.starts[i] * beat })), played, beat);
    return res.results.map(r => r.heard ? (r.right ? 'R' : 'W') + (r.timing === 'early' ? 'e' : r.timing === 'late' ? 'l' : '') + (r.inTune ? '' : '~') : '-').join(' ');
  };
  for (const page of pages) for (const inst of ['violin', 'viola']) for (const tempo of [60, 100]) for (let n = 1; n <= perPage; n++) {
    const length = n % 3 === 0 ? 'two' : 'bar';
    let pat;
    try { pat = SightReading.pattern(page, inst, n, { length, noRepeats: true }); } catch (e) { continue; }
    const N = pat.midis.length, k = n % N, base = { page: page.id, inst, tempo, n, notes: pat.notes.join(' '), count: N };
    out.push({ ...base, case: 'as written', got: make(pat, tempo, inst, { seed: n }) });
    out.push({ ...base, case: 'wrong', k, got: make(pat, tempo, inst, { seed: n + 1, wrong: { [k]: n % 2 ? 1 : -2 } }) });
    if (k > 0) out.push({ ...base, case: 'late', k, got: make(pat, tempo, inst, { seed: n + 2, shift: { [k]: 0.33 } }) });
    if (k > 0 && pat.starts[k] - pat.starts[k - 1] >= 1) out.push({ ...base, case: 'early', k, got: make(pat, tempo, inst, { seed: n + 3, shift: { [k]: -0.25 } }) });
    out.push({ ...base, case: 'nearly on time', k, got: make(pat, tempo, inst, { seed: n + 4, shift: { [k]: 0.1 } }) });
    out.push({ ...base, case: '10 cents', k, got: make(pat, tempo, inst, { seed: n + 5, cents: { [k]: 10 } }) });
    out.push({ ...base, case: '30 cents', k, got: make(pat, tempo, inst, { seed: n + 6, cents: { [k]: -30 } }) });
    out.push({ ...base, case: '70 cents', k, got: make(pat, tempo, inst, { seed: n + 7, cents: { [k]: 70 } }) });
    out.push({ ...base, case: 'left out', k, got: make(pat, tempo, inst, { seed: n + 8, drop: k }) });
    if (n === 1) {
      out.push({ ...base, case: 'nothing', got: make(pat, tempo, inst, { silent: true }) });
      out.push({ ...base, case: 'noise only', got: make(pat, tempo, inst, { silent: true, noise: 0.05 }) });
      out.push({ ...base, case: 'quiet and noisy', got: make(pat, tempo, inst, { seed: n + 9, loud: 0.05, noise: 0.01 }) });
    }
  }
  // The timing check: open A on four clicks, at three delays; then a round judged with what it found.
  for (const lat of [0.05, 0.14, 0.32]) {
    const beat = 1, clicks = Array.from({ length: 8 }, (_, i) => 0.4 + i * beat);
    const x = ListenTakes.take({ notes: clicks.slice(4).map((c, i) => ({ midi: 69, t: c + lat + (i % 2 ? 0.015 : -0.015), dur: 0.7 })), clicks: clicks.map((c, i) => ({ t: c + lat, strong: i % 4 === 0 })), length: 9.5, seed: 7 });
    const res = Listen.timing(x, 48000, 'violin', clicks.slice(4), beat);
    const pat = SightReading.pattern(pages[1], 'violin', 3, { length: 'bar', noRepeats: true });
    out.push({ case: 'timing check', lat, offset: res && res.offset, round: res ? make(pat, 60, 'violin', { lat, offset: res.offset, seed: 11 }) : null, count: pat.midis.length });
  }
  return out;
}'''

RECORDED_JS = r'''async ({ samples, sampleRate, take }) => {
  const x = new Float32Array(samples), beat = 60 / take.tempo;
  if (take.kind === 'timing') {
    const res = Listen.timing(x, sampleRate, take.inst, take.clicks, beat);
    return { offset: res && res.offset };
  }
  const played = Listen.notes(Listen.track(x, sampleRate, take.inst)).map(n => ({ ...n, t0: n.t0 - take.firstBeat - (take.offset || 0), t1: n.t1 - take.firstBeat - (take.offset || 0) })).filter(n => n.t1 > -0.45 * beat);
  const res = Listen.judge(take.midis.map((m, i) => ({ midi: m, t: take.starts[i] * beat })), played, beat);
  return { got: res.results.map(r => r.heard ? (r.right ? 'R' : 'W') + (r.timing === 'early' ? 'e' : r.timing === 'late' ? 'l' : '') + (r.inTune ? '' : '~') : '-').join(' '), say: res.say };
}'''


def expect(case):
    """What the made-up case should come out as, note by note: R right on time (~ not in tune), W wrong, e early,
    l late, - not heard."""
    n, k = case['count'], case.get('k', 0)
    want = ['R'] * n
    c = case['case']
    if c == 'wrong': want[k] = 'W~'
    elif c == 'late': want[k] = 'Rl'
    elif c == 'early': want[k] = 'Re'
    elif c == '30 cents': want[k] = 'R~'
    elif c == '70 cents': want[k] = 'W~'
    elif c == 'left out': want[k] = '-'
    elif c in ('nothing', 'noise only'): want = ['-'] * n
    return ' '.join(want)


def read_wav(path):
    """A WAV file's first channel as floats from -1 to 1, and its sample rate."""
    with wave.open(str(path), 'rb') as w:
        sr, ch, width, frames = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(frames)
    if width != 2:
        raise ValueError(f'{path.name}: 16-bit WAV please (convert with ffmpeg -i take.m4a -ac 1 -ar 48000 -sample_fmt s16 take.wav)')
    import array
    a = array.array('h', raw)
    return [a[i] / 32768 for i in range(0, len(a), ch)], sr


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


async def main():
    began = time.monotonic()
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{httpd.server_address[1]}'
    failures = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        pg = await browser.new_page()
        await pg.goto(f'{base}/sight-reading/flash.css')  # any page of the site, so the scripts load from it
        for f in ('sight-reading/generator.js', 'sight-reading/listen.js', 'tests/listen_takes.js'):
            await pg.add_script_tag(url=f'{base}/{f}')
        got = await pg.evaluate(CASES_JS, {'pages': PAGES, 'perPage': int(os.environ.get('LISTEN_COUNT', '6'))})
        by_case = {}
        for c in got:
            if c['case'] == 'timing check':
                continue
            ok = c['got'] == expect(c)
            by_case.setdefault(c['case'], [0, 0, []])
            by_case[c['case']][0] += ok
            by_case[c['case']][1] += 1
            if not ok:
                by_case[c['case']][2].append(f"{c['page']} {c['inst']} {c['tempo']} #{c['n']} ({c['notes']}): {c['got']!r}, not {expect(c)!r}")
        for name, (ok, total, bad) in by_case.items():
            print(('  ok    ' if not bad else '  FAIL  ') + f'{name}: {ok} of {total} takes heard as they were played')
            for b in bad[:4]:
                failures.append(f'{name}: {b}')
        for c in [c for c in got if c['case'] == 'timing check']:
            # The check reads the delay plus the listening's own (about 0.03 s), the same in every round.
            ok = c['offset'] is not None and abs(c['offset'] - c['lat'] - 0.03) < 0.03 and c['round'] == ' '.join(['R'] * c['count'])
            print(('  ok    ' if ok else '  FAIL  ') + f"timing check at a {c['lat']} s delay: reads {c['offset'] and round(c['offset'], 3)} s, and a round judged with it is {c['round']!r}")
            if not ok:
                failures.append(f"timing check at {c['lat']} s: {c}")
        # Janelle's recorded takes, when there are some.
        listed = AUDIO / 'takes.json'
        if listed.exists():
            takes = json.loads(listed.read_text(encoding='utf-8'))
            for take in takes:
                samples, sr = read_wav(AUDIO / take['file'])
                res = await pg.evaluate(RECORDED_JS, {'samples': samples, 'sampleRate': sr, 'take': take})
                if take.get('kind') == 'timing':
                    ok = res['offset'] is not None
                    what = f"timing check reads {res['offset']}"
                else:
                    ok = res['got'] == take['expect']
                    what = f"{res['got']!r} (expected {take['expect']!r}): {res['say']}"
                print(('  ok    ' if ok else '  FAIL  ') + f"recorded {take['file']}: {what}")
                if not ok:
                    failures.append(f"recorded {take['file']}: {what}")
        else:
            print('  (no recorded takes yet: tests/audio/takes.json)')
        await browser.close()
    httpd.shutdown()
    took = round(time.monotonic() - began)
    print(f'\nTook {took // 60} min {took % 60} s.')
    if failures:
        print(f'{len(failures)} problem(s):')
        for f in failures[:30]:
            print('  - ' + f)
        sys.exit(1)
    print('All checks passed.')


asyncio.run(main())
