// Class settings (the teacher locks settings for everyone): the reader as the Claude preview has it, with the fake
// room (tests/mockroom.js), a teacher and two students. Run: node tests/class_locks.js
// Where jsdelivr is blocked, ALPHATAB_JS=<path to alphaTab.min.js> (see CLAUDE.md).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const AT = process.env.ALPHATAB_JS;
const HEAD = '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>body{margin:0;padding:0}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>';
let fails = 0;
const ck = (ok, what) => { console.log((ok ? '  ok    ' : '  FAIL  ') + what); if (!ok) fails++; };
(async () => {
  const html = HEAD + fs.readFileSync(ROOT + '/reader/reader.html', 'utf8') + '\n</body></html>';
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 860 } });
  await ctx.addInitScript({ path: ROOT + '/tests/mockroom.js' });
  if (AT) await ctx.route('https://cdn.jsdelivr.net/npm/@coderline/**', r => r.fulfill({ path: AT, contentType: 'application/javascript', headers: { 'Access-Control-Allow-Origin': '*' } }));
  await ctx.route('http://local.test/**', r => {
    const u = r.request().url();
    if (u.includes('__preview')) return r.fulfill({ body: html, contentType: 'text/html' });
    if (u.includes('/scores/')) return r.fulfill({ path: ROOT + '/songs/the-first-noel/the-first-noel.xml' });
    const f = u.split('?')[0].split('/').pop();
    if (u.includes('/font/')) return r.fulfill({ path: ROOT + '/assets/font/' + f });
    if (u.includes('/soundfont/')) return r.fulfill({ path: ROOT + '/assets/soundfont/' + f });
    return r.fulfill({ status: 404, body: '' });
  });
  const errs = [];
  const open = async (q, name) => {
    const pg = await ctx.newPage();
    pg.on('pageerror', e => errs.push(name + ': ' + e));
    await pg.goto('http://local.test/reader/__preview.html' + q);
    await pg.waitForFunction("!document.getElementById('play').disabled", null, { timeout: 90000 });
    await pg.waitForTimeout(1200);
    return pg;
  };
  const T = await open('', 'teacher'), A = await open('?student', 'student A'), B = await open('?student&b', 'student B');
  const look = (pg) => pg.evaluate(() => document.querySelector('#g-look .now .word').textContent);
  const ball = (pg) => pg.getAttribute('#g-point', 'title');
  const seen = (pg) => pg.evaluate(() => reader.seen().map(i => reader.partKey(i)));
  // Students set looks of their own first.
  await A.click('#g-look'); await A.waitForTimeout(1200); // Fingers to the left -> Note names and fingers
  const aOwnLook = await look(A), aOwnParts = await seen(A);
  await T.click('#g-together'); await T.waitForTimeout(1000);
  ck(!(await T.isHidden('#g-class')), 'the lock button shows on the conducting device');
  ck(await A.isHidden('#g-class'), 'and not on a student’s');
  await A.click('#g-follow'); await B.click('#g-follow'); await A.waitForTimeout(2500);
  // Parts: everyone sees the teacher's.
  await T.evaluate(() => reader.parts({ seen: [reader.seen().length && [...Array(60).keys()].find(i => reader.partKey(i) === 'Viola — Melody')] }));
  await T.waitForTimeout(1500);
  await T.click('#g-class'); await T.waitForTimeout(300);
  await T.check('input[name="cl-parts"][value="all"]'); await A.waitForTimeout(2500);
  const tParts = await seen(T);
  ck(JSON.stringify(await seen(A)) === JSON.stringify(tParts) && JSON.stringify(await seen(B)) === JSON.stringify(tParts), `parts locked: both students see the teacher's (${tParts})`);
  await A.click('#g-parts'); await A.waitForTimeout(400);
  const before = await seen(A);
  await A.click('#mixParts .tog.see:not(.none) >> nth=0'); await A.waitForTimeout(500);
  ck(JSON.stringify(await seen(A)) === JSON.stringify(before), 'a student can’t change a locked part');
  ck((await A.textContent('#toast')).includes('teacher'), `and the toast says why ("${await A.textContent('#toast')}")`);
  await A.click('#g-parts'); await A.waitForTimeout(300);
  // What's on the notes.
  await T.check('#cl-notes'); await T.waitForTimeout(200);
  await T.click('#h-class'); // keep the card open
  await T.evaluate(() => document.getElementById('g-look').click()); await T.waitForTimeout(1500);
  await T.evaluate(() => document.getElementById('g-look').click()); await T.waitForTimeout(2500);
  const tLook = await look(T);
  ck((await look(A)) === tLook && (await look(B)) === tLook, `notes locked: the students' look follows the teacher's ("${tLook}"; A "${await look(A)}", B "${await look(B)}")`);
  ck(await A.evaluate(() => document.getElementById('g-look').hasAttribute('data-class-lock')), 'the student’s On the note button is greyed out');
  await A.click('#g-look'); await A.waitForTimeout(800);
  ck((await look(A)) === tLook, 'and a tap there changes nothing');
  // Bouncing ball.
  await T.check('#cl-ball'); await T.waitForTimeout(200);
  await T.evaluate(() => document.getElementById('g-point').click()); await T.waitForTimeout(2500);
  const tBall = await ball(T);
  ck((await ball(A)) === tBall, `ball locked: the student's ball follows ("${tBall}")`);
  // By seat.
  await T.check('input[name="cl-parts"][value="seats"]'); await A.waitForTimeout(2000);
  ck(!(await A.isHidden('#seatCard')), 'by seat: a student with no seat is asked for it');
  await A.fill('#seatIn', '3'); await A.click('#seatCard button'); await A.waitForTimeout(2000);
  await T.evaluate(() => document.getElementById('g-class').click()); await T.waitForTimeout(200);
  await T.evaluate(() => document.getElementById('g-class').click()); await T.waitForTimeout(400);
  const seats = await T.evaluate(() => [...document.querySelectorAll('#pop-class select[data-seat]')].map(s => s.dataset.seat));
  ck(seats.includes('3'), `the teacher's card lists seat 3 (${seats})`);
  const cello = 'Cello — Bass Line';
  await T.selectOption('#pop-class select[data-seat="3"]', cello); await A.waitForTimeout(2500);
  ck(JSON.stringify(await seen(A)) === JSON.stringify([cello]), `seat 3 gets its part (${await seen(A)})`);
  ck((await A.textContent('#g-follow')).includes('Seat 3'), `the student's Follow button says the seat ("${await A.textContent('#g-follow')}")`);
  // Unlock everything: the students' own settings come back.
  await T.check('input[name="cl-parts"][value="own"]'); await T.uncheck('#cl-notes'); await T.uncheck('#cl-ball'); await A.waitForTimeout(2500);
  ck((await look(A)) === aOwnLook && JSON.stringify(await seen(A)) === JSON.stringify(aOwnParts), `unlocked: student A has its own look and parts again ("${await look(A)}", ${await seen(A)})`);
  ck(!(await A.evaluate(() => document.getElementById('g-look').hasAttribute('data-class-lock'))), 'and its buttons work again');
  // Lock the look again, then the student stops following: own look back.
  await T.check('#cl-notes'); await A.waitForTimeout(2000);
  await A.click('#g-follow'); await A.waitForTimeout(1500);
  ck((await look(A)) === aOwnLook, `stopped following: its own look again ("${await look(A)}")`);
  ck(!errs.length, 'no script errors' + (errs.length ? ': ' + errs.slice(0, 3).join(' | ') : ''));
  console.log(fails ? fails + ' failed' : 'all passed');
  await browser.close();
  process.exitCode = fails ? 1 : 0;
})();
