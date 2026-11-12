// A stand-in for supabase-js, for tests/together_sim.js: Realtime channels carried by the test through
// window.__netSend / window.__netRecv, so the test can give each device its own network (delay, freezes, drops).
// Auth: a tab whose first address has ?teacher is a teacher who may conduct; every other tab is a student.
(() => {
  let role = sessionStorage.getItem('fake-role');
  if (!role) { role = location.search.includes('teacher') ? 'teacher' : 'student'; sessionStorage.setItem('fake-role', role); }
  const chans = new Map();
  window.__netRecv = (m) => { const ch = chans.get(m.ch); if (ch) ch._recv(m); };
  const send = (o) => window.__netSend(JSON.stringify(o));
  function createClient() {
    return {
      auth: {
        onAuthStateChange() {},
        async getSession() { return { data: { session: role === 'teacher' ? { user: { id: 'T' } } : null } }; },
        async signInWithPassword() { return { error: null }; },
        async signOut() {},
      },
      from() { return { select() { return { async limit() { return { data: role === 'teacher' ? [{ teacher_id: 'T' }] : [], error: null }; } }; } }; },
      realtime: { async setAuth() {} },
      channel(name, opts) {
        const cfg = (opts && opts.config) || {};
        const key = (cfg.presence && cfg.presence.key) || 'k' + Math.random().toString(36).slice(2, 8);
        const bc = [], pc = [];
        let state = {}, statusCb = null, gone = false;
        const ch = {
          _name: name,
          on(kind, filter, cb) { (kind === 'broadcast' ? bc : pc).push([filter.event, cb]); return ch; },
          subscribe(cb) { statusCb = cb; chans.set(name, ch); send({ op: 'join', ch: name }); return ch; },
          send(m) { if (!gone) send({ op: 'bcast', ch: name, event: m.event, payload: m.payload }); return Promise.resolve('ok'); },
          track(p) { if (!gone) send({ op: 'track', ch: name, key, meta: p }); return Promise.resolve('ok'); },
          presenceState() { return state; },
          _recv(m) {
            if (gone) return;
            if (m.op === 'joined') { if (statusCb) statusCb('SUBSCRIBED'); return; }
            if (m.op === 'bcast') { for (const [ev, cb] of bc) if (ev === '*' || ev === m.event) cb({ event: m.event, payload: m.payload }); return; }
            if (m.op === 'sync') { state = m.state; for (const [ev, cb] of pc) if (ev === 'sync') cb(); }
          },
          _gone() { gone = true; },
        };
        return ch;
      },
      removeChannel(ch) { ch._gone(); if (chans.get(ch._name) === ch) chans.delete(ch._name); send({ op: 'leave', ch: ch._name }); },
    };
  }
  window.supabase = { createClient };
})();
