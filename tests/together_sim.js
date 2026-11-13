// Play together on a patchy connection: a teacher and two students in the browser, through app/together.js, with
// tests/fakesupabase.js in place of Supabase, so each device's messages can be delayed, bunched up behind a freeze, or
// lost when its connection drops (2026-11-12: Janelle found following "very glitchy" on her phone's hotspot).
// The teacher plays, pauses, speeds up, a second student starts following, and the teacher loops two bars. It reports,
// for each student, how often its music was stopped or more than a beat off while the teacher's played.
//
//   python -m http.server 8000           (in this folder, in another window)
//   node tests/together_sim.js http://localhost:8000 hotspot
//
// Connections: wifi, hotspot (slow and uneven, with freezes of up to 1.5 s), bad (also drops of 3 to 9 s, after which
// what was sent meanwhile is lost). SEED=2 gives other freezes; SONG=<slug> another song (default the-first-noel).
// ALPHATAB_JS=<file> serves alphaTab from a local copy (see CLAUDE.md); TRACE=<file> writes every sample there.
// SCENARIO=two: the teacher signed in on two iPads instead (see twoTeachers below).
// On good Wi-Fi and the hotspot a student keeps within a quarter of a beat, apart from the second or two it takes to
// join; on the bad connection a student whose own connection dropped catches up within about a second of it coming back.
const { chromium } = require('playwright');
const path = require('path');
const BASE = (process.argv[2] || 'http://localhost:8000').replace(/\/$/, '');
const PROFILE = process.argv[3] || 'hotspot';
const SONG = process.env.SONG || 'the-first-noel';
const ALPHATAB = process.env.ALPHATAB_JS;
const FAKE = path.join(__dirname, 'fakesupabase.js');
let seed = Number(process.env.SEED || 1);
const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };

// One-way delays (ms) through a device's link. A phone hotspot: cellular, so slow and uneven, with the odd spike
// (bufferbloat, the radio waking up) during which everything queues up behind (TCP keeps order). "Drops" are longer
// freezes after which the connection is made again: what was sent meanwhile is lost.
const PROFILES = {
  wifi: { up: [15, 30], down: [15, 30], spikeEvery: 0, spike: [0, 0], dropEvery: 0, drop: [0, 0] },
  hotspot: { up: [60, 220], down: [40, 160], spikeEvery: 6000, spike: [400, 1500], dropEvery: 0, drop: [0, 0] },
  bad: { up: [80, 300], down: [60, 200], spikeEvery: 5000, spike: [600, 2500], dropEvery: 25000, drop: [3000, 9000] },
};
const P = PROFILES[PROFILE];
const between = ([a, b]) => a + rnd() * (b - a);
const t0 = Date.now();
const now = () => Date.now() - t0;

const devices = new Map(); // page -> device
const channels = new Map(); // name -> Map(device -> Map(key -> meta))
const log = [];
const at = () => (now() / 1000).toFixed(1) + 's';
function mkLink(name) {
  const l = { upFree: 0, downFree: 0, holds: [], drops: [] };
  if (P.spikeEvery) for (let t = 0; t < 600000;) { t += P.spikeEvery * (0.5 + rnd()); l.holds.push([t, t + between(P.spike)]); }
  if (P.dropEvery) for (let t = 15000; t < 600000;) { t += P.dropEvery * (0.6 + 0.8 * rnd()); const d = [t, t + between(P.drop)]; l.drops.push(d); log.push(`${(d[0] / 1000).toFixed(1)}s ${name}'s connection drops for ${((d[1] - d[0]) / 1000).toFixed(1)}s`); }
  return l;
}
const dropped = (link, t) => link.drops.some(([a, b]) => t >= a && t < b);
function through(link, t, dir) {
  t += between(P[dir]);
  for (const [a, b] of link.holds) if (t >= a && t < b) t = b + between(P[dir]) * 0.3;
  const free = dir === 'up' ? 'upFree' : 'downFree';
  t = Math.max(t, link[free] + 1);
  link[free] = t;
  return t;
}
function deliver(dev, msg, serverAt) {
  if (dropped(dev.link, serverAt)) return;
  const t = through(dev.link, serverAt, 'down');
  if (dropped(dev.link, t)) return;
  setTimeout(() => {
    dev.chain = dev.chain.then(() => dev.page.evaluate((m) => window.__netRecv && window.__netRecv(m), msg).catch(() => {}));
  }, Math.max(0, t - now()));
}
function syncState(name) {
  const st = {};
  for (const [, keys] of channels.get(name) || []) for (const [k, meta] of keys) st[k] = [{ ...meta, presence_ref: 'r' }];
  return st;
}
function server(dev, m) {
  const sAt = now();
  const members = channels.get(m.ch) || new Map();
  channels.set(m.ch, members);
  if (m.op === 'join') { members.set(dev, members.get(dev) || new Map()); deliver(dev, { op: 'joined', ch: m.ch }, sAt); deliver(dev, { op: 'sync', ch: m.ch, state: syncState(m.ch) }, sAt); }
  else if (m.op === 'leave') { members.delete(dev); for (const [d] of members) deliver(d, { op: 'sync', ch: m.ch, state: syncState(m.ch) }, sAt); }
  else if (m.op === 'track') { if (!members.has(dev)) return; members.get(dev).set(m.key, m.meta); for (const [d] of members) deliver(d, { op: 'sync', ch: m.ch, state: syncState(m.ch) }, sAt); }
  else if (m.op === 'bcast') { if (!members.has(dev)) return; for (const [d] of members) if (d !== dev) deliver(d, { op: 'bcast', ch: m.ch, event: m.event, payload: m.payload }, sAt); }
}

async function device(browser, name, teacher, init) {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 860 } });
  if (init) await ctx.addInitScript(init);
  await ctx.addInitScript(() => { try { localStorage.setItem('gsa-together-test', '1'); } catch (e) {} });
  if (teacher) await ctx.addInitScript(() => { try { localStorage.setItem('gsa-teacher', '{}'); } catch (e) {} });
  if (ALPHATAB) await ctx.route('https://cdn.jsdelivr.net/npm/@coderline/**', (r) => r.fulfill({ path: ALPHATAB, contentType: 'application/javascript', headers: { 'Access-Control-Allow-Origin': '*' } }));
  await ctx.route('https://cdn.jsdelivr.net/npm/@supabase/**', (r) => r.fulfill({ path: FAKE, contentType: 'application/javascript' }));
  if (process.env.NO_WEBFONTS) await ctx.route('https://fonts.googleapis.com/**', (r) => r.fulfill({ body: '', contentType: 'text/css' }));
  const dev = { name, link: mkLink(name), chain: Promise.resolve() };
  await ctx.exposeBinding('__netSend', (src, s) => {
    const m = JSON.parse(s);
    const d = devices.get(src.page); if (!d) return;
    if (dropped(d.link, now())) return;
    const t = through(d.link, now(), 'up');
    if (dropped(d.link, t)) return;
    setTimeout(() => server(d, m), Math.max(0, t - now()));
  });
  const page = await ctx.newPage();
  dev.page = page; devices.set(page, dev);
  // After a drop the connection is made again: the server forgot this device's presence, and the channels rejoin
  // (supabase-js does that by itself, but does not track presence again).
  for (const [, end] of dev.link.drops) setTimeout(() => {
    for (const [name, members] of channels) if (members.has(dev)) {
      members.set(dev, new Map());
      for (const [d] of members) if (d !== dev) deliver(d, { op: 'sync', ch: name, state: syncState(name) }, now());
      deliver(dev, { op: 'joined', ch: name }, now()); deliver(dev, { op: 'sync', ch: name, state: syncState(name) }, now());
    }
  }, end + 50);
  page.on('pageerror', (e) => log.push(`${at()} ${name} error: ${e.message}`));
  await page.goto(`${BASE}/songs/${SONG}/${teacher ? '?teacher' : ''}`);
  await page.waitForFunction(() => !document.getElementById('play').disabled, null, { timeout: 120000 });
  await page.waitForTimeout(500);
  return dev;
}

const STATE = `(() => { const c = reader.conductor; return { at: reader.at(), playing: reader.api.playerState === 1,
  following: c.following, synced: c.synced, host: !!c.hostPeer, hosting: c.hosting, fixes: c.fixes || 0, followers: c.followers, speed: reader.api.playbackSpeed,
  keen: !!(c.site && c.site.wantsFollow()), ver: c.seenVer, sent: c.sentVer, origin: performance.timeOrigin, offx: c.offset, loop: !!reader.api.playbackRange, off: Math.round(c.offset), rtt: Math.round(c.bestRtt) }; })()`;

async function follow(S) {
  await S.page.waitForSelector('#g-follow:not([hidden])', { timeout: 30000 });
  await S.page.click('#g-follow');
  await S.page.waitForFunction(() => reader.conductor.synced, null, { timeout: 30000 }).catch(() => log.push(`${at()} ${S.name} never synced`));
  log.push(`${at()} ${S.name} following`);
}
async function dragBars(page, from, to) {
  const pt = (i) => page.evaluate((i) => {
    const s = document.querySelector('#sheet .at-surface').getBoundingClientRect();
    const b = reader.api.boundsLookup.staffSystems.flatMap((y) => y.bars).find((m) => m.index === i).visualBounds;
    return { x: s.left + b.x + b.w / 2, y: s.top + b.y + b.h / 2 };
  }, i);
  const a = await pt(from), b = await pt(to);
  await page.mouse.move(a.x, a.y); await page.mouse.down();
  for (let k = 1; k <= 8; k++) await page.mouse.move(a.x + (b.x - a.x) * k / 8, a.y + (b.y - a.y) * k / 8);
  await page.mouse.up();
}

// SCENARIO=two: the teacher signed in on two iPads (Janelle's class, 2026-11-13: students' music lurched back and forth
// and stopped). The second iPad opens the piece while the first conducts and plays; it had conducted earlier in its tab,
// so it takes up conducting again by itself. Then the teacher presses Conduct on the second iPad and plays there.
// A student follows throughout; it should stay with one teacher, and move over cleanly when Conduct is pressed.
async function twoTeachers(browser) {
  const T = await device(browser, 'teacher iPad 1', true);
  const S = await device(browser, 'student', false);
  await T.page.waitForFunction(() => reader.conductor.room, null, { timeout: 30000 });
  await T.page.waitForSelector('#g-together:not([hidden])', { timeout: 30000 }); await T.page.click('#g-together');
  await T.page.waitForFunction(() => reader.conductor.hosting, null, { timeout: 30000 });
  await follow(S);
  const samples = [];
  let stop = false, phase = '', T2 = null;
  const sampler = (async () => {
    while (!stop) {
      const r = await Promise.all([T, T2, S].map((d) => (d ? d.page.evaluate(STATE).catch(() => null) : null)));
      if (r[0] && r[2]) samples.push({ t: now(), phase, a: r[0], b: r[1], s: r[2] });
      await new Promise((res) => setTimeout(res, 100));
    }
  })();
  const step = async (what, fn, wait) => { phase = what; log.push(`${at()} ${what}`); await fn(); await new Promise((r) => setTimeout(r, wait)); };
  await step('iPad 1 plays', () => T.page.click('#play'), 6000);
  await step('iPad 2 opens the piece (it conducted earlier in its tab)', async () => {
    T2 = await device(browser, 'teacher iPad 2', true, () => { if (!sessionStorage.getItem('sim-once')) { sessionStorage.setItem('sim-once', '1'); sessionStorage.setItem('gsa-conduct', '1'); } });
  }, 4000);
  // Students coming and going (every arrival or departure changes who the student sees as conducting).
  await step('another student opens the piece, then closes it', async () => {
    const S2 = await device(browser, 'student 2', false);
    await new Promise((r) => setTimeout(r, 5000));
    await S2.page.context().close();
  }, 6000);
  await step('iPad 1 pauses', () => T.page.click('#play'), 3000);
  await step('Conduct pressed on iPad 2', async () => {
    if (!(await T2.page.evaluate(() => reader.conductor.hosting))) await T2.page.click('#g-together');
  }, 4000);
  await step('iPad 2 plays', () => T2.page.click('#play'), 12000);
  await step('iPad 2 pauses', () => T2.page.click('#play'), 3000);
  stop = true; await sampler;
  console.log(log.sort((x, y) => parseFloat(x) - parseFloat(y)).join('\n'));
  // Against whichever iPad the student follows: is the student with it, or off somewhere?
  const byPhase = {};
  let prev = null;
  for (const smp of samples) {
    const ph = (byPhase[smp.phase] = byPhase[smp.phase] || { n: 0, stuck: 0, far: 0, jumps: 0, moving: 0, hosts: new Set() });
    const lead = [smp.a, smp.b].filter((x) => x && x.hosting);
    ph.hosts.add(lead.length);
    // The iPad the student should be with: iPad 1 until Conduct is pressed on iPad 2.
    const a = /Conduct pressed|iPad 2 plays|iPad 2 pauses/.test(smp.phase) && smp.b ? smp.b : smp.a;
    ph.n++;
    if (a.playing) { ph.moving++; if (!smp.s.playing) ph.stuck++; else if (Math.abs(a.at - smp.s.at) > 960) ph.far++; }
    if (prev && smp.s.playing && prev.s.playing && Math.abs((smp.s.at - prev.s.at) - (smp.t - prev.t) * 1.6) > 480) ph.jumps++;
    prev = smp;
  }
  for (const [p, v] of Object.entries(byPhase)) console.log(`${p}: devices conducting ${[...v.hosts].join('/')}; teacher's music moving ${v.moving} of ${v.n} samples; student stopped ${v.stuck}, over a beat off ${v.far}, jumps ${v.jumps}`);
}

(async () => {
  const browser = await chromium.launch();
  if (process.env.SCENARIO === 'two') { await twoTeachers(browser); await browser.close(); process.exit(0); }
  const T = await device(browser, 'teacher', true);
  const S1 = await device(browser, 'student1', false);
  const S2 = await device(browser, 'student2', false);
  log.push(`${at()} pages ready (profile ${PROFILE})`);
  await T.page.waitForFunction(() => reader.conductor.room, null, { timeout: 30000 });
  await T.page.waitForSelector('#g-together:not([hidden])', { timeout: 30000 }); await T.page.click('#g-together');
  await T.page.waitForFunction(() => reader.conductor.hosting, null, { timeout: 30000 });
  await follow(S1);

  const samples = [];
  let stop = false, phase = '';
  const sampler = (async () => {
    while (!stop) {
      const r = await Promise.all([T, S1, S2].map((d) => d.page.evaluate(STATE).catch(() => null)));
      if (r.every(Boolean)) samples.push({ t: now(), phase, a: r[0], s: [r[1], r[2]] });
      await new Promise((res) => setTimeout(res, 100));
    }
  })();
  const step = async (what, fn, wait) => { phase = what; log.push(`${at()} teacher: ${what}`); await fn(); await T.page.waitForTimeout(wait); };
  const isPlaying = () => T.page.evaluate(() => reader.api.playerState === 1 || /Starting/.test(document.getElementById('playText').textContent));
  const play = async () => { if (!(await isPlaying())) await T.page.click('#play'); };
  const pause = async () => { if (await isPlaying()) await T.page.click('#play'); };
  const toStart = async () => { await pause(); await T.page.waitForTimeout(300); await T.page.click('#restart'); };
  await step('Play', play, 12000);
  await step('Pause', pause, 3000);
  await step('Play', play, 6000);
  await step('Faster (+15)', () => T.page.evaluate(() => { for (let i = 0; i < 3; i++) document.getElementById('faster').click(); }), 4000);
  await step('student2 follows', () => follow(S2), 8000);
  await step('Pause', pause, 2000);
  await step('back to the start', toStart, 1500);
  await step('loop bars 2-3', () => dragBars(T.page, 1, 2), 1500);
  await step('Play (loop)', play, 20000);
  await step('Pause', pause, 2000);
  await step('tap bar 5 (loop off)', () => dragBars(T.page, 4, 4), 1500);
  await step('Play', play, 15000);
  await step('Pause', pause, 4000);
  stop = true; await sampler;

  if (process.env.TRACE) require('fs').writeFileSync(process.env.TRACE, samples.map((x) => [(x.t/1000).toFixed(1), x.phase, Math.round(x.a.at), x.a.playing ? 'P' : '-', x.a.sent, x.a.loop ? 'L' : '', '|', ...x.s.map((s) => [Math.round(s.at), s.playing ? 'P' : '-', s.following ? 'F' : '-', s.ver, s.loop ? 'L' : '', Math.round(s.at - x.a.at), 'offErr', Math.round(s.offx - (s.origin - x.a.origin))].join(' '))].join(' ')).join('\n'));
  // Report, per student: while the teacher's music moves, how far off is the student, and is it moving at all?
  console.log(log.sort((x, y) => parseFloat(x) - parseFloat(y)).join('\n'));
  for (const k of [0, 1]) {
    let moving = 0, stuck = 0, close = 0, far = 0, flaps = 0, lastFollow = null, jumps = 0, gaps = [], prev = null, wrongWhilePaused = 0, pausedN = 0;
    const byPhase = {};
    for (const smp of samples) {
      const s = smp.s[k], a = smp.a;
      if (s.following !== lastFollow) { if (lastFollow !== null) flaps++; lastFollow = s.following; }
      if (!s.following) { prev = null; continue; }
      const ph = (byPhase[smp.phase] = byPhase[smp.phase] || { n: 0, stuck: 0, far: 0 });
      if (a.playing) {
        moving++; ph.n++;
        if (!s.playing) { stuck++; ph.stuck++; }
        else { const g = Math.abs(a.at - s.at); gaps.push(g); if (g < 240) close++; if (g > 960) { far++; ph.far++; } }
      } else { pausedN++; if (s.playing) wrongWhilePaused++; }
      // A jump: the student's place changes by more than half a beat more than the teacher's did.
      if (prev && a.playing && prev.a.playing && s.playing && prev.s.playing && Math.abs((s.at - prev.s.at) - (a.at - prev.a.at)) > 480) jumps++;
      prev = { a, s };
    }
    gaps.sort((x, y) => x - y);
    const q = (p) => (gaps.length ? Math.round(gaps[Math.floor(p * (gaps.length - 1))]) : '-');
    console.log(`\nstudent${k + 1}: teacher playing ${moving} samples; student stopped ${stuck}, within 1/4 beat ${close}, over a beat off ${far}; ` +
      `teacher paused ${pausedN}, student still moving ${wrongWhilePaused}; jumps ${jumps}; follow on/off ${flaps}; ` +
      `gap ticks median ${q(0.5)} 90% ${q(0.9)} max ${q(1)}; clock off ${samples[samples.length - 1].s[k].off} rtt ${samples[samples.length - 1].s[k].rtt}`);
    for (const [p, v] of Object.entries(byPhase)) if (v.stuck || v.far) console.log(`   ${p}: of ${v.n} samples, stopped ${v.stuck}, over a beat off ${v.far}`);
  }
  await browser.close();
  process.exit(0);
})().catch((e) => { console.error(e); console.log(log.join('\n')); process.exit(1); });
