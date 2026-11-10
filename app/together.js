// Play together on the website: the teacher's device conducts, students' devices follow (start, stop, tempo, bars,
// loop and count-in come from the teacher; the sound plays on the teacher's device only).
//
// The reader's conductor was written for the Claude preview's shared "room". This file gives the website the same
// kind of room, through Supabase Realtime (Janelle's violin-studio project), as window.playTogether; the reader uses
// it wherever window.claude doesn't exist. Song pages load it; it does nothing until someone opens Play together, or
// has a class code or a teacher sign-in saved, so a page that never uses it never downloads Supabase.
//
// How a class meets: the teacher signs in (her violin-studio email and password) and has a class code
// (public.conduct_classes). Students type the code once; it is saved on their device. Everyone on the same song page
// with the same code is in one room, made of two channels:
//   conduct:<CODE>:<song>     only the code's teacher may send (the database's rules on realtime.messages check it)
//   conduct-in:<CODE>:<song>  anyone may send: who is here (presence) and the students' clock pings
// So a student can't take over the class: only messages on the teacher's channel ever move a student's music.
(() => {
  const song = (location.pathname.match(/\/songs\/([^/]+)/) || [])[1];
  if (!song || window.claude) return;

  const SUPABASE_URL = 'https://wjzzdiuenlisxueaxqjq.supabase.co';
  const SUPABASE_KEY = 'sb_publishable_M4bWNkME8l7LTKIrQ_iCfw_JgsRZQlL'; // public by design: the database's rules guard everything
  const LIB = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.118.0/dist/umd/supabase.js';
  const CODE_KEY = 'gsa-class-code';
  const AUTH_KEY = 'gsa-teacher';
  const BEAT_MS = 2000;       // a conducting teacher says so this often, so a student who arrives late finds her
  const HOST_GONE_MS = 7000;  // a teacher not heard from for this long has stopped conducting

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} },
  };
  const cleanCode = (s) => String(s || '').toUpperCase().replace(/[^A-Z]/g, '');
  const hadTeacher = () => !!store.get(AUTH_KEY);

  let sb = null, libLoading = null;
  let teacher = null;                 // { code } once signed in with a class
  let signedInNoClass = false;        // signed in, but this account has no class code
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
    teacher = null; signedInNoClass = false;
    const { data } = await sb.auth.getSession();
    if (!data || !data.session) return;
    const { data: rows, error } = await sb.from('conduct_classes').select('code').limit(1);
    if (error) throw error;
    if (rows && rows[0]) teacher = { code: rows[0].code };
    else signedInNoClass = true;
  }

  // ---- The room, shaped like the Claude preview's: emit / on / presence / onPeers / onConnection ----
  async function openRoom(code, lead) {
    await sb.realtime.setAuth();
    const me = 'p' + Math.random().toString(36).slice(2, 10);
    const main = sb.channel(`conduct:${code}:${song}`, { config: { private: true, broadcast: { self: false } } });
    const inn = sb.channel(`conduct-in:${code}:${song}`, { config: { private: true, broadcast: { self: false }, presence: { key: me } } });
    const handlers = new Map(), peerCbs = [], connCbs = [];
    const hosts = new Map();    // peer -> when last heard on the teacher's channel
    let here = new Map();       // peer -> presence on the students' channel
    const pings = new Map();    // peer -> a ping waiting to be answered
    let mine = {}, tracked = null, beatTimer = 0, gcTimer = 0, last = new Map(), closed = false;

    function peers() {
      const ids = new Set([me, ...here.keys(), ...hosts.keys()]);
      return [...ids].map((peer) => {
        const presence = { ...(peer === me ? mine : here.get(peer) || {}) };
        delete presence.conducting;
        if (peer === me ? mine.conducting : hosts.has(peer)) presence.conducting = true;
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
      for (const cb of peerCbs) { try { cb({ peers: list, joined, updated, left }); } catch {} }
    }
    const connected = () => connCbs.forEach((cb) => { try { cb(); } catch {} });
    function sawHost(peer, off) {
      const had = hosts.has(peer);
      if (off) hosts.delete(peer); else hosts.set(peer, Date.now());
      if (had !== hosts.has(peer)) fire();
    }

    main.on('broadcast', { event: 'beat' }, ({ payload }) => payload && sawHost(payload.from, payload.off));
    main.on('broadcast', { event: '*' }, ({ event, payload }) => {
      if (!payload || event === 'beat') return;
      if (!hosts.has(payload.from)) sawHost(payload.from, false); else hosts.set(payload.from, Date.now());
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
      const old = [...hosts].filter(([, t]) => Date.now() - t > HOST_GONE_MS).map(([p]) => p);
      if (old.length) { old.forEach((p) => hosts.delete(p)); fire(); }
    }, 1000);

    const joinOk = (ch) => new Promise((resolve, reject) => {
      ch.subscribe((status) => {
        if (status === 'SUBSCRIBED') { resolve(); connected(); }
        else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') { reject(new Error(status)); connected(); }
        else if (status === 'CLOSED') connected();
      });
    });
    await Promise.all([joinOk(main), joinOk(inn)]);

    function track() {
      const want = JSON.stringify({ following: !!mine.following, lead: !!lead });
      if (want === tracked) return Promise.resolve();
      tracked = want;
      return inn.track(JSON.parse(want));
    }
    const sendMain = (event, data) => main.send({ type: 'broadcast', event, payload: { from: me, data } });
    function beat(off) { return main.send({ type: 'broadcast', event: 'beat', payload: { from: me, off: !!off } }); }
    const bye = () => { if (mine.conducting) beat(true); };
    addEventListener('pagehide', bye);
    await track();

    const room = {
      code, lead,
      emit(event, data) {
        if (!lead) return Promise.reject(new Error('Only the teacher conducts'));
        return sendMain(event, data).then((r) => { if (r !== 'ok') throw new Error(String(r)); });
      },
      on(event, cb) { if (!handlers.has(event)) handlers.set(event, []); handlers.get(event).push(cb); },
      presence(obj) {
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
  async function room() {
    if (current) { current.leave(); current = null; }
    const code = teacher ? teacher.code : cleanCode(store.get(CODE_KEY));
    if (!teacher && !code && !hadTeacher()) return null;
    await client();
    if (!teacher && hadTeacher()) await loadTeacher().catch(() => {});
    const useCode = teacher ? teacher.code : code;
    if (!useCode) return null;
    current = await openRoom(useCode, !!teacher);
    return current;
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
.pt-box input.pt-code { text-transform: uppercase; letter-spacing: 0.25em; font-weight: 700; font-size: 1.3rem; text-align: center; }
.pt-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.pt-btn { flex: 1 1 auto; padding: 10px 14px; border: 1px solid var(--line, #C9D2CE); border-radius: 999px; background: var(--paper, #fff);
  color: var(--paper-ink, #121614); font: inherit; font-weight: 600; cursor: pointer; }
.pt-btn.main { background: var(--accent, #1D5B72); border-color: var(--accent, #1D5B72); color: var(--accent-ink, #fff); }
.pt-btn:disabled { opacity: 0.55; cursor: default; }
.pt-link { display: inline-block; margin-top: 14px; padding: 0; border: 0; background: none; color: var(--accent, #1D5B72); font: inherit; font-size: 0.9rem; font-weight: 600; cursor: pointer; text-decoration: underline; }
.pt-big { margin: 4px 0 12px; font-size: 2.4rem; font-weight: 700; letter-spacing: 0.2em; text-align: center; color: var(--ink, #17201C); }
.pt-msg { min-height: 1.2em; margin: 2px 0 8px; font-size: 0.88rem; font-weight: 600; color: #B42318; }
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

    function studentView() {
      const saved = cleanCode(store.get(CODE_KEY));
      if (saved) {
        return show(...head('Play together'),
          el('p', {}, 'You’re in class ', el('strong', {}, saved), '. When your teacher conducts this piece, a “Follow the conductor” button appears at the bottom of the screen. Your teacher’s device plays the sound.'),
          el('div', { class: 'pt-row' },
            el('button', { class: 'pt-btn main', type: 'button', on: close }, 'OK'),
            el('button', { class: 'pt-btn', type: 'button', on: () => { store.set(CODE_KEY, null); changed(); studentView(); } }, 'Leave the class')),
          el('button', { class: 'pt-link', type: 'button', on: teacherView }, 'Teacher? Sign in to conduct'));
      }
      const input = el('input', { class: 'pt-code', id: 'pt-code', inputmode: 'text', autocomplete: 'off', autocapitalize: 'characters', spellcheck: 'false', maxlength: '8' });
      const go = el('button', { class: 'pt-btn main', type: 'submit' }, 'Join');
      const form = el('form', {}, el('label', { for: 'pt-code' }, 'Class code'), input, msg, el('div', { class: 'pt-row' }, go));
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const code = cleanCode(input.value);
        if (code.length < 4) { msg.textContent = 'Type the four letters your teacher gives you.'; return; }
        store.set(CODE_KEY, code); changed(); studentView();
      });
      show(...head('Play together'),
        el('p', {}, 'Follow your teacher: the music starts, stops and keeps time on every screen at once. Everyone opens this same piece; the sound plays on the teacher’s device.'),
        form,
        el('button', { class: 'pt-link', type: 'button', on: teacherView }, 'Teacher? Sign in to conduct'));
    }

    function teacherView() {
      if (teacher) {
        return show(...head('Play together'),
          el('p', {}, 'Your class code. Students open this piece, tap Play together and type it:'),
          el('div', { class: 'pt-big' }, teacher.code),
          el('div', { class: 'pt-row' },
            opts.conducting ? el('button', { class: 'pt-btn main', type: 'button', on: close }, 'OK')
              : el('button', { class: 'pt-btn main', type: 'button', on: () => { close(); if (opts.conduct) opts.conduct(); } }, 'Start conducting'),
            el('button', { class: 'pt-btn', type: 'button', on: (e) => busy(e.currentTarget, async () => { await sb.auth.signOut(); teacher = null; signedInNoClass = false; changed(); close(); }) }, 'Sign out')));
      }
      if (signedInNoClass) {
        return show(...head('Play together'),
          el('p', {}, 'This account isn’t set up to conduct. Students follow with a class code instead.'),
          el('div', { class: 'pt-row' }, el('button', { class: 'pt-btn', type: 'button', on: (e) => busy(e.currentTarget, async () => { await sb.auth.signOut(); signedInNoClass = false; changed(); studentView(); }) }, 'Sign out')));
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
        el('p', {}, 'Sign in with your studio account (the same email and password).'),
        form,
        el('button', { class: 'pt-link', type: 'button', on: studentView }, 'I’m a student'));
    }

    if (hadTeacher() && !teacher && !signedInNoClass) {
      show(...head('Play together'), el('p', {}, 'One moment…'));
      try { await client(); await loadTeacher(); } catch {}
      if (box !== back) return;
    }
    if (teacher || signedInNoClass) teacherView(); else studentView();
  }

  window.playTogether = {
    room,
    canLead: () => !!teacher,
    code: () => (teacher ? teacher.code : cleanCode(store.get(CODE_KEY))),
    open,
    onChange(cb) { changeCbs.push(cb); },
  };
})();
