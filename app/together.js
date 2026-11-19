// Play together on the website: the teacher's device conducts, students' devices follow (start, stop, tempo, bars,
// loop and count-in come from the teacher; the sound plays on the teacher's device only).
//
// The reader's conductor was written for the Claude preview's shared "room". This file gives the website the same
// kind of room, through Supabase Realtime (Janelle's violin-studio project), as window.playTogether; the reader uses
// it wherever window.claude doesn't exist.
//
// No class code (Janelle, 2026-11-10): every song page is one room, and any page that has it open watches for a
// teacher conducting it; the reader then shows a small "Follow" at the top. Nobody follows unless they tap it. The
// teacher signs in (her violin-studio email and password) from the About box. Each room is two channels:
//   conduct:<song>     only a teacher listed in public.conduct_classes may send (the database's rules on
//                      realtime.messages check it)
//   conduct-in:<song>  anyone may send: who is here (presence) and the students' clock pings
// So a student can't take over: only messages on the teacher's channel ever move a student's music.
//
// Changing songs (Janelle, 2026-11-10): the teacher's conducting carries on from page to page in her tab until she
// stops it, and she says on one site-wide channel, conduct:__site, which song she has open (or none, on the home
// page). A device that tapped Follow keeps following from page to page in its tab: when the teacher opens another
// song, it goes there too, from a song page or the home page. Stopping (her "Conducting", their "Following") ends it.
(() => {
  if (window.claude) return;
  const root = new URL('../', document.currentScript.src); // this file is app/together.js
  const song = (location.pathname.match(/\/songs\/([^/]+)/) || [])[1] || null;
  const home = !song && new URL('./', location.href).href === root.href;
  if (!song && !home) return;

  const SUPABASE_URL = 'https://wjzzdiuenlisxueaxqjq.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_M4bWNkME8l7LTKIrQ_iCfw_JgsRZQlL'; // public by design: the database's rules guard everything
  const LIB = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/dist/umd/supabase.js';
  const START_MS = 1500;      // connect this long after the page starts, so the music loads first
  const AUTH_KEY = 'gsa-teacher';
  const BEAT_MS = 2000;       // a conducting teacher says so this often, so a student who arrives late finds her
  const HOST_GONE_MS = 7000;  // a teacher not heard from for this long has stopped conducting
  // ...except on a device following her: a phone's connection (a hotspot, Janelle, 2026-11-12) can freeze for several
  // seconds, and the music keeps going on its own meanwhile, so it holds on longer. A teacher who stops says so.
  const FOLLOWED_GONE_MS = 25000;

  const SITE_GONE_MS = 10000; // the home page's Follow goes when the teacher hasn't been heard for this long,
  const SITE_FOLLOWED_GONE_MS = 30000; // and a following device stops following after this long
  const FOLLOW_KEY = 'gsa-follow', CONDUCT_KEY = 'gsa-conduct'; // in this tab only (sessionStorage)
  // One device conducts at a time (Janelle, 2026-11-13: signed in on two iPads and her iPhone, a device that had conducted
  // earlier took it up again by itself on each new piece, and students' music lurched between them). gsa-conduct holds
  // when this tab took the lead (Date.now()); where two devices conduct, the one where Conduct was pressed last leads and
  // the other stops by itself, quietly (no "stop" for the students).
  const conducting = () => { try { return !!sessionStorage.getItem(CONDUCT_KEY); } catch { return false; } };
  const conductSince = () => { try { return Number(sessionStorage.getItem(CONDUCT_KEY)) || 0; } catch { return 0; } };
  let tabId = '';
  try { tabId = sessionStorage.getItem('gsa-tab') || ''; if (!tabId) { tabId = Math.random().toString(36).slice(2, 10); sessionStorage.setItem('gsa-tab', tabId); } } catch { tabId = Math.random().toString(36).slice(2, 10); }
  const tab = {
    get(k) { try { return sessionStorage.getItem(k) === '1'; } catch { return false; } },
    set(k, on) { try { on ? sessionStorage.setItem(k, '1') : sessionStorage.removeItem(k); } catch {} },
  };
  // Tests run on channels of their own, so they never meet a real class (set by tests/smoke.py and Claude's checks).
  let TEST = ''; try { if (localStorage.getItem('gsa-together-test')) TEST = 'test-'; } catch {}
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };
  const hadTeacher = () => !!store.get(AUTH_KEY);

  // ---- Duo practice (Janelle, 2026-11-19: a couple practising at home on two tablets) ----
  // A duo login (a username and password Janelle makes for them; not a studio account) opens a room of their own,
  // duo:<room>, instead of each song's open room. One tablet leads (it conducts by itself on every song), the other
  // follows (by itself, from song to song). They can swap. The room name comes from the gsa-duo function after the
  // password check; the device keeps it (localStorage gsa-duo) so it opens connected from then on.
  const DUO_KEY = 'gsa-duo';
  let duo = null;
  try { const d = JSON.parse(store.get(DUO_KEY) || 'null'); if (d && /^[0-9a-f]{32}$/.test(d.room)) duo = { user: String(d.user || ''), room: d.room, role: d.role === 'follow' ? 'follow' : 'lead' }; } catch {}
  const saveDuo = () => store.set(DUO_KEY, duo ? JSON.stringify(duo) : null);
  const leader = () => (duo ? duo.role === 'lead' : teacher); // this device may conduct
  if (duo && song) {
    // The leader conducts every song it opens; the follower follows (both carry on from page to page anyway).
    try { if (duo.role === 'lead') { if (!sessionStorage.getItem(CONDUCT_KEY)) sessionStorage.setItem(CONDUCT_KEY, String(Date.now())); sessionStorage.removeItem(FOLLOW_KEY); }
      else { sessionStorage.setItem(FOLLOW_KEY, '1'); sessionStorage.removeItem(CONDUCT_KEY); } } catch {}
  } else if (duo && home) tab.set(FOLLOW_KEY, duo.role === 'follow');
  let duoConn = 'connecting', duoOthers = 0; // the room's state, for the duo bar

  let sb = null, libLoading = null;
  let teacher = false;                // signed in as a teacher who may conduct
  let signedInNoClass = false;        // signed in, but this account may not conduct
  let started = false;
  let current = null;                 // the room the reader holds
  const changeCbs = [];
  const changed = () => changeCbs.forEach((cb) => { try { cb(); } catch {} });

  function client() {
    if (sb) return Promise.resolve(sb);
    if (!libLoading) {
      libLoading = new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = LIB; s.async = true;
        s.onload = () => resolve();
        s.onerror = () => { libLoading = null; reject(new Error('offline')); };
        document.head.append(s);
      }).then(() => {
        sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY, {
          auth: { storageKey: AUTH_KEY, persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
          // The script holds a device to 10 messages a second unless told otherwise; a teacher answering several
          // students' clock pings at once (each sends 8 as they start following) needs more.
          realtime: { params: { eventsPerSecond: 60 } },
        });
        sb.auth.onAuthStateChange((event) => { if (event === 'TOKEN_REFRESHED') sb.realtime.setAuth().catch(() => {}); });
        return sb;
      });
    }
    return libLoading;
  }

  async function loadTeacher() {
    teacher = false; signedInNoClass = false;
    const { data } = await sb.auth.getSession();
    if (!data || !data.session) return;
    const { data: rows, error } = await sb.from('conduct_classes').select('teacher_id').limit(1);
    if (error) throw error;
    if (rows && rows[0]) teacher = true;
    else signedInNoClass = true;
  }

  // ---- The room, shaped like the Claude preview's: emit / on / presence / onPeers / onConnection ----
  async function openRoom(lead) {
    await sb.realtime.setAuth();
    const me = 'p' + Math.random().toString(36).slice(2, 10);
    const main = sb.channel(duo ? `duo:${duo.room}` : `conduct:${TEST}${song}`, { config: { private: true, broadcast: { self: false } } });
    const inn = sb.channel(duo ? `duo:${duo.room}:in` : `conduct-in:${TEST}${song}`, { config: { private: true, broadcast: { self: false }, presence: { key: me } } });
    const handlers = new Map(), peerCbs = [], connCbs = [];
    const hosts = new Map();    // peer -> { t: when last heard on the teacher's channel, since: when it took the lead }
    let here = new Map();       // peer -> presence on the students' channel
    const pings = new Map();    // peer -> a ping waiting to be answered
    let mine = {}, tracked = null, beatTimer = 0, gcTimer = 0, last = new Map(), closed = false;

    function peers() {
      const ids = new Set([me, ...here.keys(), ...hosts.keys(), ...pings.keys()]); // a ping can arrive before its sender's presence
      return [...ids].map((peer) => {
        const presence = { ...(peer === me ? mine : here.get(peer) || {}) };
        delete presence.conducting;
        if (peer === me ? mine.conducting : hosts.has(peer)) presence.conducting = true;
        if (peer !== me && hosts.has(peer)) presence.since = hosts.get(peer).since || 0;
        if (pings.has(peer)) Object.assign(presence, { following: true, ping: pings.get(peer) });
        return { peer, isMe: peer === me, sameTab: peer === me, presence };
      });
    }
    function fire() {
      if (closed) return;
      const list = peers(), now = new Map(list.map((p) => [p.peer, JSON.stringify(p.presence)]));
      const joined = list.filter((p) => !last.has(p.peer));
      const updated = list.filter((p) => last.has(p.peer) && last.get(p.peer) !== now.get(p.peer));
      const left = [...last.keys()].filter((p) => !now.has(p)).map((peer) => ({ peer }));
      last = now;
      pings.clear();
      if (duo) { duoOthers = here.size; duoUi(); }
      for (const cb of peerCbs) { try { cb({ peers: list, joined, updated, left }); } catch {} }
    }
    const connected = () => connCbs.forEach((cb) => { try { cb(); } catch {} });
    function sawHost(peer, off, since) {
      const had = hosts.get(peer);
      if (off) hosts.delete(peer); else hosts.set(peer, { t: Date.now(), since: since != null ? since : had ? had.since : 0 });
      if (!had !== !hosts.has(peer) || (had && hosts.has(peer) && had.since !== hosts.get(peer).since)) fire();
    }

    main.on('broadcast', { event: 'beat' }, ({ payload }) => payload && sawHost(payload.from, payload.off, payload.since));
    main.on('broadcast', { event: '*' }, ({ event, payload }) => {
      if (!payload || event === 'beat') return;
      if (!hosts.has(payload.from)) sawHost(payload.from, false); else hosts.get(payload.from).t = Date.now();
      for (const cb of handlers.get(event) || []) { try { cb({ data: payload.data, peer: payload.from, sameTab: false }); } catch {} }
    });
    inn.on('presence', { event: 'sync' }, () => {
      const next = new Map();
      for (const [peer, metas] of Object.entries(inn.presenceState())) if (peer !== me) next.set(peer, Object.assign({}, ...metas.map(({ presence_ref, ...m }) => m)));
      here = next;
      fire();
    });
    inn.on('broadcast', { event: 'ping' }, ({ payload }) => {
      if (!lead || !mine.conducting || !payload) return;
      pings.set(payload.from, payload.id);
      fire();
    });
    gcTimer = setInterval(() => {
      const gone = mine.following ? FOLLOWED_GONE_MS : HOST_GONE_MS;
      const old = [...hosts].filter(([, h]) => Date.now() - h.t > gone).map(([p]) => p);
      if (old.length) { old.forEach((p) => hosts.delete(p)); fire(); }
    }, 1000);

    let joined = false;
    const joinOk = (ch) => new Promise((resolve, reject) => {
      ch.subscribe((status) => {
        // Joined again after the connection dropped: the server has forgotten who this device is (supabase-js doesn't
        // say it again by itself), so say it again.
        if (status === 'SUBSCRIBED' && ch === inn && joined && !closed) { tracked = null; track().catch(() => {}); }
        if (duo && ch === main) { duoConn = status === 'SUBSCRIBED' ? 'ok' : status === 'CLOSED' && closed ? duoConn : 'lost'; duoUi(); }
        if (status === 'SUBSCRIBED') { resolve(); connected(); }
        else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') { reject(new Error(status)); connected(); }
        else if (status === 'CLOSED') connected();
      });
    });
    await Promise.all([joinOk(main), joinOk(inn)]);
    joined = true;

    function track() {
      // A student's seat (or stand) number, so the teacher can give a seat its part (the reader's class settings).
      const want = JSON.stringify({ following: !!mine.following, lead: !!lead, ...(mine.seat ? { seat: String(mine.seat).slice(0, 12) } : {}) });
      if (want === tracked) return Promise.resolve();
      tracked = want;
      return inn.track(JSON.parse(want));
    }
    const sendMain = (event, data) => main.send({ type: 'broadcast', event, payload: { from: me, data } });
    function beat(off) { return main.send({ type: 'broadcast', event: 'beat', payload: { from: me, off: !!off, since: mine.since || 0 } }); }
    const bye = () => { if (mine.conducting) beat(true); };
    addEventListener('pagehide', bye);
    await track();

    const room = {
      lead,
      emit(event, data) {
        if (closed) return Promise.reject(new Error('This room was closed'));
        if (!lead) return Promise.reject(new Error(duo ? 'Only the leader leads' : 'Only the teacher conducts'));
        return sendMain(event, data).then((r) => { if (r !== 'ok') throw new Error(String(r)); });
      },
      on(event, cb) { if (!handlers.has(event)) handlers.set(event, []); handlers.get(event).push(cb); },
      presence(obj) {
        if (closed) return Promise.resolve(); // a room that was replaced says nothing more (no stray "I'm conducting")
        const was = !!mine.conducting;
        for (const [k, v] of Object.entries(obj || {})) { if (v == null) delete mine[k]; else mine[k] = v; }
        if (obj && obj.ping != null) inn.send({ type: 'broadcast', event: 'ping', payload: { from: me, id: obj.ping } });
        if (lead && !!mine.conducting !== was) {
          clearInterval(beatTimer);
          if (mine.conducting) { beat(false); beatTimer = setInterval(() => beat(false), BEAT_MS); } else beat(true);
        }
        return track();
      },
      onPeers(cb) { peerCbs.push(cb); setTimeout(fire, 0); },
      onConnection(cb) { connCbs.push(cb); },
      leave() {
        if (closed) return;
        bye(); closed = true;
        clearInterval(beatTimer); clearInterval(gcTimer);
        removeEventListener('pagehide', bye);
        sb.removeChannel(main); sb.removeChannel(inn);
      },
    };
    return room;
  }

  // ---- What the reader asks for ----
  // Every song page joins its room by itself; offline it has none, and tries again when the internet comes back.
  async function room() {
    if (current) { current.leave(); current = null; }
    if (!started) { started = true; await new Promise((r) => setTimeout(r, START_MS)); }
    await client();
    if (!duo && !teacher && hadTeacher()) await loadTeacher().catch(() => {});
    current = await openRoom(leader());
    return current;
  }
  addEventListener('online', () => { if (!current) changed(); if (!site) startSite(); });

  // ---- Which song the teacher has open (conduct:__site) ----
  let site = null, siteHost = null, siteTimer = 0, siteSeen = 0;
  const siteCbs = [];
  const siteChanged = () => { siteCbs.forEach((cb) => { try { cb(); } catch {} }); if (home) homeUi(); };
  const songUrl = (slug) => new URL('songs/' + slug + '/', root).href;
  function goTo(slug) {
    if (!slug || slug === song) return;
    tab.set(FOLLOW_KEY, true);
    location.href = songUrl(slug);
  }
  function sayHere() {
    if (!site || !leader() || !conducting()) return;
    const title = song ? document.title : null;
    site.send({ type: 'broadcast', event: 'here', payload: { song, title, from: tabId, since: conductSince() } });
  }
  async function startSite() {
    if (site) return;
    try { await client(); } catch { return; }
    if (!duo && !teacher && hadTeacher()) await loadTeacher().catch(() => {});
    await sb.realtime.setAuth().catch(() => {});
    const ch = sb.channel(duo ? `duo:${duo.room}:site` : `conduct:${TEST}__site`, { config: { private: true, broadcast: { self: false } } });
    // A duo swapped who leads, from the other tablet: take the other role, and open the page afresh in it.
    ch.on('broadcast', { event: 'swap' }, ({ payload }) => { if (duo && payload && (payload.role === 'lead' || payload.role === 'follow')) setRole(payload.role, false); });
    ch.on('broadcast', { event: 'here' }, ({ payload }) => {
      if (!payload) return;
      const since = payload.since || 0;
      // Another device of the teacher's is conducting too: the one where Conduct was pressed last leads.
      if (leader() && conducting() && payload.from !== tabId) {
        if (since > conductSince()) giveWay(); else return;
      }
      // A student stays with the teacher it has while she is heard, whatever another (earlier) device says.
      if (siteHost && siteHost.from && payload.from !== siteHost.from && since < (siteHost.since || 0)
        && Date.now() - siteSeen < SITE_GONE_MS) return;
      const was = siteHost && siteHost.song;
      siteHost = { song: payload.song || null, title: payload.title || null, from: payload.from || '', since };
      siteSeen = Date.now();
      if (tab.get(FOLLOW_KEY) && siteHost.song && siteHost.song !== song) { goTo(siteHost.song); return; }
      if (was !== siteHost.song || !was) siteChanged();
    });
    ch.on('broadcast', { event: 'off' }, ({ payload }) => {
      if (payload && payload.from && siteHost && siteHost.from && payload.from !== siteHost.from) return; // not the teacher it follows
      siteHost = null; if (!duo) tab.set(FOLLOW_KEY, false); siteChanged(); // a duo's follower waits for its leader
    });
    ch.subscribe((status) => { if (status === 'SUBSCRIBED') sayHere(); });
    site = ch;
    clearInterval(siteTimer);
    siteTimer = setInterval(() => {
      sayHere();
      if (siteHost && Date.now() - siteSeen > (tab.get(FOLLOW_KEY) ? SITE_FOLLOWED_GONE_MS : SITE_GONE_MS)) {
        siteHost = null;
        if (!duo) tab.set(FOLLOW_KEY, false);
        siteChanged();
      }
    }, BEAT_MS);
    // A following tab that arrives with nobody conducting gives up after a while too.
    if (tab.get(FOLLOW_KEY)) siteSeen = Date.now(), siteHost = siteHost || { song: null, title: null, pending: true };
    if (home) homeUi();
  }
  // since: when the lead was taken (Conduct pressed); kept as it is when conducting carries on to the next page.
  function setConducting(on, since) {
    try { if (on) sessionStorage.setItem(CONDUCT_KEY, String(since || conductSince() || Date.now())); else sessionStorage.removeItem(CONDUCT_KEY); } catch {}
    if (on) sayHere();
    else if (site) site.send({ type: 'broadcast', event: 'off', payload: { from: tabId } });
    if (home) homeUi();
  }
  // Another device took the lead: stop conducting here without telling the students to stop.
  const giveWayCbs = [];
  function giveWay() {
    try { sessionStorage.removeItem(CONDUCT_KEY); } catch {}
    giveWayCbs.forEach((cb) => { try { cb(); } catch {} });
    if (home) homeUi();
  }
  function setFollow(on) {
    tab.set(FOLLOW_KEY, on);
    if (on && siteHost && siteHost.song && siteHost.song !== song) goTo(siteHost.song);
    siteChanged();
  }

  // ---- The home page: Follow, or the teacher's Conducting · Stop, at the top right ----
  let pill = null;
  function homeUi() {
    if (!home || !document.body) return;
    if (!pill) {
      if (!styled) { document.head.append(el('style', {}, CSS)); styled = true; }
      pill = el('div', { class: 'pt-pill', role: 'group', 'aria-label': 'Play together' });
      document.body.append(pill);
    }
    const kids = [];
    if (duo) { pill.hidden = true; duoUi(); return; } // a duo has its own bar
    if (teacher && conducting()) {
      kids.push(el('span', { class: 'pt-pill-txt' }, 'Conducting: open a song'),
        el('button', { class: 'pt-pill-btn', type: 'button', on: () => setConducting(false) }, 'Stop'));
    } else if (tab.get(FOLLOW_KEY) && siteHost) {
      kids.push(el('button', { class: 'pt-pill-btn on', type: 'button', title: 'Stop following', on: () => setFollow(false) }, 'Following'),
        el('span', { class: 'pt-pill-txt' }, 'waiting for the teacher to choose a song'));
    } else if (siteHost && !siteHost.pending) {
      kids.push(el('button', { class: 'pt-pill-btn', type: 'button', title: 'Follow the teacher: your screen goes to the song the teacher plays',
        on: () => setFollow(true) }, 'Follow'));
    }
    pill.replaceChildren(...kids);
    pill.hidden = !kids.length;
    // The screen stays on while the teacher conducts here or a student waits for her song (app/app.js).
    if (window.gsaKeepAwake) window.gsaKeepAwake('home', (teacher && conducting()) || (tab.get(FOLLOW_KEY) && !!siteHost));
  }
  if (home) setTimeout(startSite, START_MS); else if (song) setTimeout(() => { startSite(); }, START_MS);
  try { localStorage.removeItem('gsa-class-code'); } catch {} // from the first version, which had class codes

  // ---- Duo practice: the bar at the top, swapping, and the gsa-duo function ----
  // A big, plain bar at the top of every page while a duo is signed in: who this tablet is and whether the two are
  // connected ("Leading · the other tablet is following", "Following · waiting for the leader", "Not connected").
  // A tap opens the duo box (swap, sign out).
  let duoBar = null;
  function duoUi() {
    if (!duo || !document.body) return;
    if (!styled) { document.head.append(el('style', {}, CSS)); styled = true; }
    if (!duoBar) {
      duoBar = el('button', { class: 'pt-duo', type: 'button', title: 'Duo practice: swap who leads, or sign out', on: () => open() });
      document.body.append(duoBar);
    }
    const lead = duo.role === 'lead', heard = !!siteHost && !siteHost.pending;
    const ok = duoConn === 'ok' || (home && !!site);
    let state = !ok && duoConn !== 'connecting' ? 'off' : 'on', words;
    if (!ok && duoConn !== 'connecting') words = 'Not connected: check the internet';
    else if (lead) words = home ? 'Leading: open a song' : duoOthers ? 'Leading · the other tablet is following' : 'Leading · waiting for the other tablet';
    else words = home && heard && siteHost.song ? 'Following · going to the leader’s song' : heard || duoOthers ? 'Following the leader' : 'Following · waiting for the leader';
    if (words.startsWith('Leading ·') && !duoOthers) state = 'wait';
    if (words.includes('waiting')) state = 'wait';
    duoBar.dataset.state = state;
    duoBar.replaceChildren(el('span', { class: 'pt-duo-dot', 'aria-hidden': 'true' }), el('span', {}, 'Duo · ' + words));
    if (window.gsaKeepAwake) window.gsaKeepAwake('duo', true); // a duo practising: the screens stay on
  }
  // This tablet takes a role; told: the other tablet takes the other one.
  function setRole(role, tell = true) {
    if (!duo || duo.role === role) return;
    if (tell && site) site.send({ type: 'broadcast', event: 'swap', payload: { role: role === 'lead' ? 'follow' : 'lead' } });
    duo.role = role; saveDuo();
    try { sessionStorage.removeItem(CONDUCT_KEY); sessionStorage.removeItem(FOLLOW_KEY); } catch {}
    setTimeout(() => location.reload(), tell ? 400 : 0); // opened afresh in the new role (the message goes out first)
  }
  // The gsa-duo function (Supabase): login for anyone, the rest for a signed-in teacher.
  async function duoCall(body) {
    await client().catch(() => { throw new Error('No internet connection.'); });
    const { data, error } = await sb.functions.invoke('gsa-duo', { body });
    if (error || !data) throw new Error('That didn’t work. Check the internet and try again.');
    if (!data.ok) throw new Error(data.error || 'That didn’t work.');
    return data;
  }

  // ---- The Play together box ----
  const CSS = `
.pt-back { position: fixed; inset: 0; z-index: 1000; display: grid; place-items: center; padding: 16px; background: rgba(15, 21, 19, 0.45); }
.pt-box { width: min(380px, 100%); max-height: calc(100vh - 32px); overflow: auto; box-sizing: border-box; padding: 18px 20px 20px; border-radius: 14px;
  background: var(--panel, #F5F7F6); color: var(--ink, #17201C); font-family: var(--font-body, system-ui, sans-serif); box-shadow: 0 20px 50px -20px rgba(0,0,0,.55); }
.pt-box h2 { margin: 0 0 6px; font-family: var(--font-display, Georgia, serif); font-size: 1.45rem; font-weight: 600; }
.pt-box p { margin: 0 0 12px; font-size: 0.94rem; line-height: 1.4; color: var(--muted, #55615B); }
.pt-box label { display: block; margin: 0 0 4px; font-size: 0.86rem; font-weight: 600; }
.pt-box input { box-sizing: border-box; width: 100%; margin: 0 0 10px; padding: 9px 11px; border: 1px solid var(--line, #C9D2CE); border-radius: 8px;
  background: var(--paper, #fff); color: var(--paper-ink, #121614); font: inherit; font-size: 16px; }
.pt-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.pt-btn { flex: 1 1 auto; padding: 10px 14px; border: 1px solid var(--line, #C9D2CE); border-radius: 999px; background: var(--paper, #fff);
  color: var(--paper-ink, #121614); font: inherit; font-weight: 600; cursor: pointer; }
.pt-btn.main { background: var(--accent, #1D5B72); border-color: var(--accent, #1D5B72); color: var(--accent-ink, #fff); }
.pt-btn:disabled { opacity: 0.55; cursor: default; }
.pt-msg { min-height: 1.2em; margin: 2px 0 8px; font-size: 0.88rem; font-weight: 600; color: #B42318; }
.pt-pill { position: fixed; top: 12px; right: 12px; z-index: 900; display: flex; align-items: center; gap: 8px; padding: 4px; border-radius: 999px;
  background: var(--panel, #F5F7F6); border: 1px solid var(--line, #C9D2CE); box-shadow: 0 6px 18px -10px rgba(0,0,0,.4); font-family: var(--font-body, system-ui, sans-serif); }
.pt-pill[hidden] { display: none; }
.pt-pill-txt { padding: 0 8px 0 4px; font-size: 0.86rem; color: var(--muted, #55615B); }
.pt-pill-btn { padding: 6px 14px; border: 1px solid var(--line, #C9D2CE); border-radius: 999px; background: var(--paper, #fff); color: var(--ink, #17201C);
  font: inherit; font-size: 0.88rem; font-weight: 600; cursor: pointer; }
.pt-pill-btn.on { background: var(--accent, #1D5B72); border-color: var(--accent, #1D5B72); color: var(--accent-ink, #fff); }
.pt-duo { position: fixed; top: calc(8px + env(safe-area-inset-top, 0px)); left: 50%; transform: translateX(-50%); z-index: 950; display: flex; align-items: center; gap: 10px;
  max-width: calc(100vw - 24px); padding: 9px 18px; border-radius: 999px; border: 2px solid #1D5B72; background: #FFFFFF; color: #17201C; font: 700 1.05rem/1.2 var(--font-body, system-ui, sans-serif);
  box-shadow: 0 6px 18px -10px rgba(0,0,0,.45); cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pt-duo-dot { flex: none; width: 14px; height: 14px; border-radius: 50%; background: #1E8E5A; }
.pt-duo[data-state="wait"] .pt-duo-dot { background: #E0A100; }
.pt-duo[data-state="off"] { border-color: #B42318; color: #B42318; }
.pt-duo[data-state="off"] .pt-duo-dot { background: #B42318; }
.pt-list { margin: 0 0 12px; padding: 0; list-style: none; }
.pt-list li { display: flex; align-items: center; gap: 6px; padding: 6px 0; border-bottom: 1px solid var(--line, #C9D2CE); font-size: 0.92rem; }
.pt-list li b { flex: 1 1 auto; overflow-wrap: anywhere; }
.pt-list .pt-btn { flex: none; padding: 5px 10px; font-size: 0.82rem; }
.pt-roles { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0 0 12px; }
.pt-roles .pt-btn { padding: 16px 10px; font-size: 1.1rem; }
.pt-x { float: right; margin: -6px -8px 0 0; padding: 4px 10px; border: 0; background: none; color: var(--muted, #55615B); font-size: 1.5rem; line-height: 1; cursor: pointer; }`;
  let styled = false;
  function el(tag, attrs = {}, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) { if (k === 'on') e.addEventListener('click', v); else if (v != null) e.setAttribute(k, v); }
    e.append(...kids.filter((k) => k != null));
    return e;
  }

  let box = null;
  function close() { if (box) { box.remove(); box = null; } }
  // opts.conduct(): start conducting (shown to a signed-in teacher); opts.conducting: already conducting.
  async function open(opts = {}) {
    if (!styled) { document.head.append(el('style', {}, CSS)); styled = true; }
    close();
    const back = el('div', { class: 'pt-back' });
    const panel = el('div', { class: 'pt-box', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': 'pt-h' });
    back.append(panel);
    back.addEventListener('pointerdown', (e) => { if (e.target === back) close(); });
    back.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
    document.body.append(back);
    box = back;
    const head = (title) => [el('button', { class: 'pt-x', type: 'button', 'aria-label': 'Close', on: close }, '×'), el('h2', { id: 'pt-h' }, title)];
    const msg = el('div', { class: 'pt-msg', role: 'status' });
    const show = (...kids) => { panel.replaceChildren(...kids); const f = panel.querySelector('input, .pt-btn.main'); if (f) f.focus(); };
    const busy = async (btn, fn) => {
      btn.disabled = true; msg.textContent = '';
      try { await fn(); } catch (e) { msg.textContent = (e && e.message) || 'That didn’t work. Check the internet and try again.'; }
      btn.disabled = false;
    };

    // Duo practice: signed in, the two roles (a tap swaps) and Sign out; not yet, a username and password.
    function duoView() {
      if (duo) {
        const role = (r, label, sub) => el('button', { class: 'pt-btn' + (duo.role === r ? ' main' : ''), type: 'button', 'aria-pressed': String(duo.role === r),
          on: () => { if (duo.role !== r) { close(); setRole(r); } } }, label, el('br'), el('small', {}, sub));
        return show(...head('Duo practice'),
          el('p', {}, 'Signed in as ' + duo.user + '. The leader picks the song and presses Play; the other tablet follows, each with its own part.'),
          el('div', { class: 'pt-roles' }, role('lead', 'I lead', 'pick the song, Play'), role('follow', 'I follow', 'my tablet follows')),
          el('p', {}, 'Tap the other choice to swap: the other tablet swaps too.'),
          el('div', { class: 'pt-row' }, el('button', { class: 'pt-btn main', type: 'button', on: close }, 'OK'),
            el('button', { class: 'pt-btn', type: 'button', on: () => { duo = null; saveDuo(); try { sessionStorage.removeItem(CONDUCT_KEY); sessionStorage.removeItem(FOLLOW_KEY); } catch {} location.reload(); } }, 'Sign out')));
      }
      const user = el('input', { id: 'pt-duo-user', autocomplete: 'username', autocapitalize: 'off', spellcheck: 'false' });
      const pass = el('input', { id: 'pt-duo-pass', type: 'password', autocomplete: 'current-password' });
      const lead = el('input', { id: 'pt-duo-lead', type: 'checkbox', style: 'width:auto;margin:0 8px 0 0' });
      const go = el('button', { class: 'pt-btn main', type: 'submit' }, 'Sign in');
      const form = el('form', {}, el('label', { for: 'pt-duo-user' }, 'Username'), user, el('label', { for: 'pt-duo-pass' }, 'Password'), pass,
        el('label', { for: 'pt-duo-lead', style: 'display:flex;align-items:center;font-weight:600;margin:4px 0 12px' }, lead, 'This tablet leads'), msg, el('div', { class: 'pt-row' }, go));
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        busy(go, async () => {
          const d = await duoCall({ action: 'login', username: user.value, password: pass.value });
          duo = { user: d.username, room: d.room, role: lead.checked ? 'lead' : 'follow' }; saveDuo();
          try { sessionStorage.removeItem(CONDUCT_KEY); sessionStorage.removeItem(FOLLOW_KEY); } catch {}
          location.replace(location.pathname); // opened afresh, connected (and without ?duo)
        });
      });
      show(...head('Duo practice'), el('p', {}, 'Sign in with the username and password your teacher gave you. You only need to do this once on each tablet.'), form);
    }
    // The teacher's duo logins: make one (she chooses the username and password), give one a new password, or remove it.
    async function duoAdmin() {
      show(...head('Duo logins'), el('p', {}, 'One moment…'));
      let list = [];
      try { list = (await duoCall({ action: 'list' })).duos || []; } catch (e) { msg.textContent = e.message; }
      if (box !== back) return;
      const user = el('input', { id: 'pt-new-user', autocomplete: 'off', autocapitalize: 'off', spellcheck: 'false', placeholder: 'for example: practice-duo' });
      const pass = el('input', { id: 'pt-new-pass', autocomplete: 'off', placeholder: 'at least 6 characters' });
      const make = el('button', { class: 'pt-btn main', type: 'submit' }, 'Make duo login');
      const form = el('form', {}, el('label', { for: 'pt-new-user' }, 'Username'), user, el('label', { for: 'pt-new-pass' }, 'Password'), pass, msg, el('div', { class: 'pt-row' }, make,
        el('button', { class: 'pt-btn', type: 'button', on: () => teacherView() }, 'Back')));
      form.addEventListener('submit', (e) => { e.preventDefault(); busy(make, async () => { await duoCall({ action: 'create', username: user.value, password: pass.value }); await duoAdmin(); msg.textContent = ''; }); });
      const row = (d) => {
        const reset = el('button', { class: 'pt-btn', type: 'button', on: (e) => { const p = prompt('New password for ' + d.username + ' (at least 6 characters). Both tablets will need to sign in again.'); if (p) busy(e.currentTarget, async () => { await duoCall({ action: 'reset', username: d.username, password: p }); msg.textContent = 'New password set for ' + d.username + '.'; }); } }, 'New password');
        const remove = el('button', { class: 'pt-btn', type: 'button', on: (e) => { if (confirm('Remove the duo login ' + d.username + '? Its tablets stop connecting.')) busy(e.currentTarget, async () => { await duoCall({ action: 'remove', username: d.username }); await duoAdmin(); }); } }, 'Remove');
        return el('li', {}, el('b', {}, d.username), reset, remove);
      };
      show(...head('Duo logins'),
        el('p', {}, 'Make a username and password for two people practising together at home, and send it to them with this link: ' + new URL('?duo', root).href + ' . They sign in once on each tablet; one leads, one follows.'),
        list.length ? el('ul', { class: 'pt-list' }, ...list.map(row)) : el('p', {}, 'No duo logins yet.'),
        form);
    }

    function teacherView() {
      const signOut = (e) => busy(e.currentTarget, async () => { await sb.auth.signOut(); teacher = false; signedInNoClass = false; changed(); close(); });
      if (teacher) {
        return show(...head('Play together'),
          el('p', {}, 'You’re signed in as the teacher. Press Conduct (at the bottom) or Start conducting: students with this piece open see a small Follow button at the top, and tap it to follow you. The sound plays on your device.'),
          el('div', { class: 'pt-row' },
            opts.conducting ? el('button', { class: 'pt-btn main', type: 'button', on: close }, 'OK')
              : el('button', { class: 'pt-btn main', type: 'button', on: () => { close(); if (opts.conduct) opts.conduct(); } }, 'Start conducting'),
            el('button', { class: 'pt-btn', type: 'button', on: () => duoAdmin() }, 'Duo logins'),
            el('button', { class: 'pt-btn', type: 'button', on: signOut }, 'Sign out')));
      }
      if (signedInNoClass) {
        return show(...head('Play together'),
          el('p', {}, 'This account isn’t set up to conduct. Students don’t need to sign in: a Follow button appears at the top when the teacher conducts.'),
          el('div', { class: 'pt-row' }, el('button', { class: 'pt-btn', type: 'button', on: signOut }, 'Sign out')));
      }
      const email = el('input', { id: 'pt-email', type: 'email', autocomplete: 'username', autocapitalize: 'off' });
      const pass = el('input', { id: 'pt-pass', type: 'password', autocomplete: 'current-password' });
      const go = el('button', { class: 'pt-btn main', type: 'submit' }, 'Sign in');
      const form = el('form', {}, el('label', { for: 'pt-email' }, 'Email'), email, el('label', { for: 'pt-pass' }, 'Password'), pass, msg, el('div', { class: 'pt-row' }, go));
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        busy(go, async () => {
          await client().catch(() => { throw new Error('No internet connection.'); });
          const { error } = await sb.auth.signInWithPassword({ email: email.value.trim(), password: pass.value });
          if (error) throw new Error(/invalid/i.test(error.message) ? 'That email and password don’t match.' : error.message);
          await loadTeacher();
          changed();
          teacherView();
        });
      });
      show(...head('Conduct the class'),
        el('p', {}, 'Sign in with your studio account (the same email and password). Students don’t sign in: a Follow button appears at the top of their music while you conduct this piece.'),
        form, el('div', { class: 'pt-row' }, el('button', { class: 'pt-btn', type: 'button', on: () => duoView() }, 'Practising as a duo? Sign in here')));
    }

    if (duo || opts.duo) return duoView();
    if (hadTeacher() && !teacher && !signedInNoClass) {
      show(...head('Play together'), el('p', {}, 'One moment…'));
      try { await client(); await loadTeacher(); } catch {}
      if (box !== back) return;
    }
    teacherView();
  }

  window.playTogether = {
    wantsFollow: () => tab.get(FOLLOW_KEY),
    setFollow,
    wantsConduct: conducting,
    conductSince,
    onGiveWay(cb) { giveWayCbs.push(cb); },
    giveWay,
    setConducting,
    onSite(cb) { siteCbs.push(cb); },
    // The song the teacher is conducting somewhere on the site (null: on the home page), or undefined: nobody conducting.
    teacherAt: () => (siteHost && !siteHost.pending && !(teacher && conducting()) ? { song: siteHost.song, title: siteHost.title } : undefined),
    room,
    canLead: () => leader(),
    duo: () => (duo ? { role: duo.role } : null),
    open,
    onChange(cb) { changeCbs.push(cb); },
  };
  // Duo practice: its bar from the start (the home page has no room, only the site channel, so it counts as connected
  // once that is up).
  if (duo) {
    if (document.body) duoUi(); else addEventListener('DOMContentLoaded', duoUi);
    if (home) setTimeout(() => { if (site) duoConn = 'ok'; duoUi(); }, START_MS + 3000);
  }
  // A link Janelle sends: …/?duo opens the duo sign-in.
  if (/[?&]duo\b/.test(location.search)) addEventListener('load', () => open({ duo: true }));
})();
