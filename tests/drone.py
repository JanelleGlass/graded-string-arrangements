"""Test of the drone (drone/drone.js): the tuning, the circle of fifths, and the sound it makes.

    python3 tests/drone.py

About half a minute. Uses the same Playwright and Chromium as tests/smoke.py: the drone runs in a blank browser page with
no site around it, and its sound is made with an OfflineAudioContext (as fast as the computer can, no speaker).

The tuning, worked out here on its own and compared with drone.js for every key, both tunings, every Notes, Octave and
Voicing, and A = 438 to 445:
  - at A = 440 the D root is 293.66 Hz (D4; D3 in the middle octave, 146.83)
  - the root is equal-tempered from A, so it agrees with a tuner and the site's playback
  - Pure: the fifth exactly 3:2 over the root, a major third 5:4, a minor third 6:5 (an octave up in Open voicing)
  - Piano: every note equal-tempered
  - changing A moves every note by the same proportion
  - each note spelled from the key (the third of G♯ minor is B, of E♭ minor G♭)
The circle: C, A minor, G, E minor ... F, D minor; Next and Previous step in that order and wrap round both ways.
The sound, rendered:
  - the notes heard are the notes worked out (each within a quarter of a hertz)
  - it fades in on Start and out on Stop to silence, and a new key crossfades in about a quarter of a second
  - no clicks: from start to stop, through key changes (quick ones too, one on top of another), setting changes and the
    volume, no step from one sample to the next is bigger than the steady sound's own (on the soft sound, where a click
    would stand out; a copy of drone.js with a 0.5 ms crossfade fails it)
  - in Pure the drone's notes don't beat (its loudness holds steady); in Piano a triad does, which shows the check works
  - every gain only ever ramps: set once to the value it already has, then one ramp, never cancelled; the volume glides
  - nothing clips, in any key, sound, octave or voicing at full volume, or with key changes coming fast
"""
import asyncio, math, sys
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding='utf-8')
failures = []


def check(ok, what):
    print(('  ok    ' if ok else '  FAIL  ') + what)
    if not ok:
        failures.append(what)


# ---- What the tuning should be, worked out here on its own ----
LETTERS = 'CDEFGAB'
NATURAL = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
CIRCLE = ['C', 'Am', 'G', 'Em', 'D', 'Bm', 'A', 'F#m', 'E', 'C#m', 'B', 'G#m', 'Gb', 'Ebm', 'Db', 'Bbm', 'Ab', 'Fm', 'Eb', 'Cm',
          'Bb', 'Gm', 'F', 'Dm']
BASE = {'low': 36, 'middle': 48, 'high': 60}  # C2, C3, C4


def pc(name):
    return (NATURAL[name[0]] + name.count('#') - name[1:].count('b')) % 12


def plain(name):
    """A spelled name back in letters: "F♯" -> "F#", "B♭" -> "Bb"."""
    return name.replace('♯', '#').replace('♭', 'b').replace('\U0001D12A', '##').replace('\U0001D12B', 'bb')


def expected(key, notes, tuning, a, octave, voicing):
    tonic, minor = key.rstrip('m'), key.endswith('m')
    root = BASE[octave] + pc(tonic)
    et = lambda m: a * 2 ** ((m - 69) / 12)
    third = (3, 6 / 5) if minor else (4, 5 / 4)
    ivs = [(0, 0, 1)]  # letters up, semitones up, pure ratio
    if notes == 'fifth':
        ivs.append((4, 7, 3 / 2))
    elif notes == 'triad':
        ivs += [(4, 7, 3 / 2), (2, third[0] + 12, third[1] * 2)] if voicing == 'open' else [(2, *third), (4, 7, 3 / 2)]
    out = []
    for letters, semis, ratio in ivs:
        hz = et(root) * ratio if tuning == 'pure' else et(root + semis)
        out.append((LETTERS[(LETTERS.index(tonic[0]) + letters) % 7], (pc(tonic) + semis) % 12, root + semis, hz))
    return out


TUNING_JS = '''() => {
  const out = [];
  for (const k of Drone.CIRCLE) for (const notes of ['tonic', 'fifth', 'triad']) for (const tuning of ['pure', 'piano'])
    for (const octave of ['low', 'middle', 'high']) for (const voicing of ['open', 'close']) for (let a = 438; a <= 445; a++)
      out.push([k.id, notes, tuning, a, octave, voicing, Drone.notes(k.id, { notes, tuning, a, octave, voicing })]);
  return out;
}'''

# A window's power at one frequency (Hann window), the loudness of short stretches, and the biggest step between samples.
TOOLS_JS = '''
window.T = {
  power(x, from, n, f, sr) { let re = 0, im = 0; for (let i = 0; i < n; i++) { const w = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (n - 1)), ph = 2 * Math.PI * f * i / sr; re += x[from + i] * w * Math.cos(ph); im -= x[from + i] * w * Math.sin(ph); } return re * re + im * im; },
  rms(x, from, n) { let s = 0; for (let i = from; i < from + n; i++) s += x[i] * x[i]; return Math.sqrt(s / n); },
  step(x, from, to) { let m = 0; for (let i = Math.max(1, from); i < to; i++) m = Math.max(m, Math.abs(x[i] - x[i - 1])); return m; },
  peak(x) { let m = 0; for (const v of x) m = Math.max(m, Math.abs(v)); return m; },
  async render(secs, plan, sr = 48000) {
    const ctx = new OfflineAudioContext(1, Math.round(sr * secs), sr), d = Drone.createDrone(ctx);
    for (const [t, fn] of plan) if (t > 0) ctx.suspend(t).then(() => { fn(d, ctx); ctx.resume(); });
    for (const [t, fn] of plan) if (t === 0) fn(d, ctx);
    return (await ctx.startRendering()).getChannelData(0);
  },
};'''

# Start in C major, cross to A minor at 1.5 s, quick changes at 2.0, 2.08 and 2.12 s (each before the last has finished
# fading), the notes and the tuning changed at 2.6 and 2.9 s, the volume halved at 3.2 s, stop at 3.6 s.
SCENARIO_JS = '''async (sound) => {
  const sr = 48000, Q = 128 / sr; // the context changes things at the start of a 128-sample block
  const at = (t) => Math.round(t / Q) * Q;
  const x = await T.render(4.4, [
    [0, (d) => { d.set({ key: 'C', notes: 'triad', tuning: 'pure', octave: 'low', sound, volume: 1 }); d.start(); }],
    [at(1.5), (d) => d.set({ key: 'Am' })],
    [at(2.0), (d) => d.set({ key: 'G' })], [at(2.08), (d) => d.set({ key: 'Em' })], [at(2.12), (d) => d.set({ key: 'D' })],
    [at(2.6), (d) => d.set({ notes: 'fifth' })], [at(2.9), (d) => d.set({ tuning: 'piano', notes: 'triad' })],
    [at(3.2), (d) => d.set({ volume: 0.5 })], [at(3.6), (d) => d.stop()],
  ], sr);
  const s = (t) => Math.round(t * sr);
  const steady = Math.max(T.step(x, s(0.6), s(1.5)), T.step(x, s(1.9), s(2.0)), T.step(x, s(2.5), s(2.6)));
  const notes = (key, o) => Drone.notes(key, { notes: 'triad', tuning: 'pure', octave: 'low', ...o }).map(n => n.hz);
  // Power at each note heard, and a quarter and a half hertz away: the note itself must be the loudest of the three.
  const tuned = (from, secs, hzs) => hzs.every(f => { const n = s(secs), p = T.power(x, s(from), n, f, sr);
    return p > T.power(x, s(from), n, f - 0.5, sr) && p > T.power(x, s(from), n, f + 0.5, sr) && p > T.power(x, s(from), n, f - 0.25, sr) && p > T.power(x, s(from), n, f + 0.25, sr); });
  const gone = (from, secs, f) => { const n = s(secs); return T.power(x, s(from), n, f, sr) < 1e-6 * T.power(x, s(0.5), n, notes('C')[0], sr); };
  const env = []; for (let t = 0; t < 4.4; t += 0.01) env.push(T.rms(x, s(t), s(0.01)));
  return {
    steady, whole: T.step(x, 1, x.length), fadeIn: [env[1], env[20], env[38], env[45]], peak: T.peak(x),
    cTuned: tuned(0.45, 1, notes('C')), amTuned: tuned(1.8, 0.2, notes('Am')), cGoneAfterCross: gone(1.8, 0.2, notes('C')[0]),
    halfVol: [T.rms(x, s(3.0), s(0.15)), T.rms(x, s(3.4), s(0.15))],
    tail: T.peak(x.subarray(s(4.1))), fadeOut: [env[361], env[380], env[398]], afterStop: T.rms(x, s(3.62), s(0.02)),
  };
}'''

# The crossfade, heard: C major (high) to A minor at 1.5 s. G (392 Hz) is only in C major: its level, in short windows,
# should fall away over about a quarter of a second, not all at once.
XFADE_JS = '''async () => {
  const sr = 48000, Q = 128 / sr, t0 = Math.round(1.5 / Q) * Q;
  const x = await T.render(2.2, [[0, (d) => { d.set({ key: 'C', octave: 'high', sound: 'soft', volume: 1 }); d.start(); }], [t0, (d) => d.set({ key: 'Am' })]], sr);
  const g = Drone.notes('C', { octave: 'high' })[1].hz, n = Math.round(0.06 * sr), lv = [];
  for (let t = t0 - 0.2; t < t0 + 0.5; t += 0.005) lv.push([t - t0, Math.sqrt(T.power(x, Math.round((t - 0.03) * sr), n, g, sr))]);
  const full = lv[0][1], when = (f) => lv.find(([, v]) => v < f * full)[0];
  return { from: when(0.9), to: when(0.1) };
}'''

# Loudness, measured over windows a whole number of the chord's common periods long, so Pure reads exactly steady.
BEATS_JS = '''async ([tuning, voicing]) => {
  const sr = 48000, x = await T.render(7, [[0, (d) => { d.set({ key: 'C', notes: 'triad', tuning, voicing, octave: 'middle', sound: 'organ', volume: 1 }); d.start(); }]], sr);
  const root = Drone.notes('C', { octave: 'middle' })[0].hz, win = Math.round(16 * 4 / root * sr); // C major repeats every 4/root
  const out = []; for (let i = Math.round(0.6 * sr); i + win < x.length; i += win) out.push(T.rms(x, i, win));
  const mean = out.reduce((a, b) => a + b) / out.length;
  return (Math.max(...out) - Math.min(...out)) / mean;
}'''

# Records every call on every gain: which param, what call, the value it was given and the value it had then.
SPY_JS = '''() => {
  const ids = new WeakMap(); let next = 0; window.calls = [];
  const id = (p) => { if (!ids.has(p)) ids.set(p, ++next); return ids.get(p); };
  for (const m of ['setValueAtTime', 'linearRampToValueAtTime', 'exponentialRampToValueAtTime', 'setTargetAtTime', 'setValueCurveAtTime', 'cancelScheduledValues', 'cancelAndHoldAtTime']) {
    const orig = AudioParam.prototype[m]; if (!orig) continue;
    AudioParam.prototype[m] = function (...args) { calls.push({ p: id(this), m, v: args[0], t: args[1], had: this.value, gain: this.maxValue > 1e30 && this.minValue < -1e30 }); return orig.apply(this, args); };
  }
}'''

SPY_RUN_JS = '''async () => {
  calls.length = 0;
  const sr = 48000, Q = 128 / sr, at = (t) => Math.round(t / Q) * Q;
  await T.render(3, [
    [0, (d) => { d.set({ key: 'C', volume: 0.6 }); d.start(); }],
    [at(0.1), (d) => d.set({ key: 'Am' })], [at(0.15), (d) => d.set({ key: 'G', sound: 'organ' })],
    [at(0.6), (d) => d.set({ volume: 0.9 })], [at(0.7), (d) => d.set({ a: 442, octave: 'high' })], [at(0.72), (d) => d.set({ volume: 0.3 })],
    [at(1.0), (d) => d.stop()], [at(1.1), (d) => d.start()], [at(1.12), (d) => d.set({ key: 'F' })], [at(1.2), (d) => d.stop()],
  ]);
  return calls;
}'''

CLIP_JS = '''async () => {
  let worst = 0, where = '';
  for (const key of Drone.CIRCLE.map(k => k.id)) for (const sound of ['bowed', 'organ', 'soft']) for (const octave of ['low', 'middle', 'high'])
    for (const [notes, voicing] of [['triad', 'open'], ['triad', 'close'], ['fifth', 'open']]) {
      const x = await T.render(0.7, [[0, (d) => { d.set({ key, sound, octave, notes, voicing, tuning: 'pure', volume: 1 }); d.start(); }]]);
      const p = T.peak(x); if (p > worst) { worst = p; where = `${key} ${sound} ${octave} ${notes} ${voicing}`; }
    }
  // Key changes every 0.08 s, so three or four chords fade over each other at once.
  const keys = Drone.CIRCLE.map(k => k.id), plan = [[0, (d) => { d.set({ key: 'C', volume: 1, octave: 'low' }); d.start(); }]];
  keys.forEach((k, i) => plan.push([Math.round((0.5 + i * 0.08) / (128 / 48000)) * (128 / 48000), (d) => d.set({ key: k })]));
  const fast = T.peak(await T.render(3, plan));
  return { worst, where, fast };
}'''


async def main():
    began = asyncio.get_event_loop().time()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        pg = await browser.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        await pg.evaluate(SPY_JS)
        await pg.add_script_tag(path=str(ROOT / 'drone' / 'drone.js'))
        await pg.add_script_tag(content=TOOLS_JS)

        print('Tuning')
        rows = await pg.evaluate(TUNING_JS)
        wrong = []
        for key, notes, tuning, a, octave, voicing, got in rows:
            want = expected(key, notes, tuning, a, octave, voicing)
            ok = len(got) == len(want)
            for g, (letter, npc, midi, hz) in zip(got, want):
                name = plain(g['name'])
                ok = ok and name[0] == letter and pc(name) == npc and g['midi'] == midi and abs(g['hz'] - hz) < 1e-9 * hz
            if not ok:
                wrong.append((key, notes, tuning, a, octave, voicing, got))
        check(not wrong, f'{len(rows)} keys and settings tuned and spelled as worked out here'
              + (f' (first wrong: {wrong[0][:6]}: {[(n["name"], round(n["hz"], 3)) for n in wrong[0][6]]})' if wrong else ''))
        d = {(r[0], r[1], r[2], r[3], r[4], r[5]): r[6] for r in rows}
        d4 = d[('D', 'tonic', 'pure', 440, 'high', 'open')][0]['hz']
        check(round(d4, 2) == 293.66, f'at A = 440 the D root is 293.66 Hz in the high octave (D4: {d4:.2f})')
        check(round(d[('D', 'tonic', 'pure', 440, 'middle', 'open')][0]['hz'], 2) == 146.83, 'and 146.83 Hz in the middle octave (D3)')
        ratio = lambda k, i, t='pure', v='close': d[(k, 'triad', t, 440, 'middle', v)][i]['hz'] / d[(k, 'triad', t, 440, 'middle', v)][0]['hz']
        check(abs(ratio('G', 2) - 1.5) < 1e-12 and abs(ratio('G', 1) - 1.25) < 1e-12 and abs(ratio('Em', 1) - 1.2) < 1e-12,
              'Pure: fifth exactly 3:2, major third 5:4, minor third 6:5 over the root')
        check(abs(ratio('G', 2, v='open') - 2.5) < 1e-12 and abs(ratio('Em', 2, v='open') - 2.4) < 1e-12,
              'Pure, Open voicing: the third an octave above (5:2, 12:5), over the fifth (3:2)')
        et = all(abs(12 * math.log2(n['hz'] / 440) - (n['midi'] - 69)) < 1e-9 for k, v in d.items() if k[2] == 'piano' and k[3] == 440 for n in v)
        check(et, 'Piano: every note equal-tempered from A = 440')
        moved = all(abs(d[(k[0], k[1], k[2], 442, k[4], k[5])][i]['hz'] / n['hz'] - 442 / 440) < 1e-12
                    for k, v in d.items() if k[3] == 440 for i, n in enumerate(v))
        check(moved, 'A = 442 moves every note up by 442:440, in both tunings')
        names = {k: ' '.join(plain(n['name']) for n in d[(k, 'triad', 'pure', 440, 'middle', 'close')]) for k in ['G#m', 'Ebm', 'Gb', 'Bbm', 'B']}
        check(names == {'G#m': 'G# B D#', 'Ebm': 'Eb Gb Bb', 'Gb': 'Gb Bb Db', 'Bbm': 'Bb Db F', 'B': 'B D# F#'},
              f'spelled from the key: {names}')

        print('The circle of fifths')
        ids = await pg.evaluate('() => Drone.CIRCLE.map(k => k.id)')
        check(ids == CIRCLE, 'C, A minor, G, E minor ... F, D minor, each major followed by its relative minor')
        steps = await pg.evaluate('() => Drone.CIRCLE.map(k => [Drone.step(k.id, 1).id, Drone.step(k.id, -1).id])')
        check(all(n == CIRCLE[(i + 1) % 24] and p_ == CIRCLE[i - 1] for i, (n, p_) in enumerate(steps)),
              'Next and Previous step in that order, and wrap round (D minor -> C, C -> D minor)')
        names = await pg.evaluate('() => [Drone.keyById("Gb"), Drone.keyById("Ebm")].map(k => k.name + " / " + k.also)')
        check(names == ['G♭ major / F♯', 'E♭ minor / D♯'], f'six flats as Hřímalý writes them, the sharps beside ({names})')

        print('The sound')
        for sound in ['soft', 'organ', 'bowed']:
            r = await pg.evaluate(SCENARIO_JS, sound)
            if sound == 'soft':
                check(r['cTuned'] and r['amTuned'], 'the notes heard are the notes worked out (C major, then A minor), each within a quarter of a hertz')
                check(r['cGoneAfterCross'], 'after the crossfade the old chord is gone')
                f = r['fadeIn']
                check(f[0] < 0.1 * f[3] and f[0] < f[1] < f[2] <= f[3] * 1.02, f'Start fades in over about 0.4 s ({[round(v, 3) for v in f]})')
                xf = await pg.evaluate(XFADE_JS)
                check(0.15 <= xf['to'] - xf['from'] <= 0.26, 'a new key crossfades: the old chord fades away over about a quarter of a second '
                      f"(from 90% to 10% in {xf['to'] - xf['from']:.2f} s)")
                h = r['halfVol']
                check(abs(h[1] / h[0] - 0.25) < 0.03, f'half the volume slider is a quarter of the level ({h[1] / h[0]:.3f})')
                fo = r['fadeOut']
                check(fo[0] > fo[1] > fo[2] and r['tail'] == 0, f'Stop fades out to silence ({[round(v, 3) for v in fo]}, then {r["tail"]})')
                check(r['afterStop'] > 0.5 * h[1], 'and starts fading where the sound was, without a drop')
            if sound == 'soft':  # a click stands out on the plain sound; the brighter ones' own steps are as big as a click
                check(r['whole'] <= 1.05 * r['steady'], 'no clicks: the biggest step between samples from start to stop, through every '
                      f'change, is no bigger than the steady sound\'s own ({r["whole"]:.4f} / {r["steady"]:.4f}; every sound uses the same fades)')
            check(r['peak'] < 1, f'{sound}: never clips ({r["peak"]:.3f})')
        pure_o, pure_c = await pg.evaluate(BEATS_JS, ['pure', 'open']), await pg.evaluate(BEATS_JS, ['pure', 'close'])
        piano_o, piano_c = await pg.evaluate(BEATS_JS, ['piano', 'open']), await pg.evaluate(BEATS_JS, ['piano', 'close'])
        check(pure_o < 0.002 and pure_c < 0.002, f'Pure: the triad does not beat (its loudness varies {pure_o:.2%} open, {pure_c:.2%} close)')
        check(piano_o > 0.01 and piano_c > 0.01, f'Piano: the triad does beat, as equal temperament does ({piano_o:.1%} open, {piano_c:.1%} close)')

        calls = await pg.evaluate(SPY_RUN_JS)
        by = {}
        for c in calls:
            by.setdefault(c['p'], []).append(c)
        banned = [c for c in calls if c['m'] in ('cancelScheduledValues', 'cancelAndHoldAtTime', 'setValueCurveAtTime', 'exponentialRampToValueAtTime')]
        check(not banned, 'no gain is cancelled part-way or jumps by a curve' + (f' ({banned[:2]})' if banned else ''))
        bad = []
        for p_, cs in by.items():
            ms = [c['m'] for c in cs]
            if 'setTargetAtTime' in ms:
                if set(ms) != {'setTargetAtTime'}:
                    bad.append(cs)
            elif ms != ['setValueAtTime', 'linearRampToValueAtTime'] or cs[0]['v'] != cs[0]['had'] or cs[1]['t'] <= cs[0]['t']:
                bad.append(cs)
        fades = [c for p_, cs in by.items() for c in cs if c['m'] == 'linearRampToValueAtTime']
        # Start (1 fade), three changes (2 each: one in, one out), Stop (1), Start (1), a change (2), Stop (1): 12 fades.
        check(len(fades) == 12 and not bad, f'every fade is one ramp from the value the gain already had, never cut short ({len(fades)} of 12 fades)'
              + (f'; wrong: {bad[:2]}' if bad else ''))
        vols = [c for c in calls if c['m'] == 'setTargetAtTime']
        # The first volume is set before there is any sound, so it needs no glide; the two changes while playing glide.
        check(len(vols) == 2, f'the volume glides to each new level ({len(vols)} of 2 glides)')

        clip = await pg.evaluate(CLIP_JS)
        check(clip['worst'] < 0.9 and clip['fast'] < 1,
              f"at full volume nothing clips: loudest {clip['worst']:.3f} ({clip['where']}); keys changing every 0.08 s {clip['fast']:.3f}")
        check(not errors, 'no script errors' + (f': {errors[:3]}' if errors else ''))
        await browser.close()
    took = round(asyncio.get_event_loop().time() - began)
    print(f'\nTook {took} s.')
    if failures:
        print(f'{len(failures)} check(s) failed:')
        for f in failures:
            print('  - ' + f)
        sys.exit(1)
    print('All checks passed.')


asyncio.run(main())
