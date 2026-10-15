(() => {
  const bc = new BroadcastChannel('mockroom');
  const me = 'p' + Math.random().toString(36).slice(2, 8);
  const handlers = {}; const peerHandlers = []; const peers = new Map(); let myPresence = {};
  const lat = () => 60 + Math.random() * 80;   // one-way network delay 60–140 ms
  const deliver = (fn) => setTimeout(fn, lat());
  const self = () => ({ peer: me, isMe: true, sameTab: true, presence: myPresence, by: null, kind: 'viewer', guest: false, updatedAt: 0 });
  const snapshot = () => [self(), ...peers.values()];
  const firePeers = (c) => { const ps = snapshot(); peerHandlers.forEach(h => h({ peers: ps, joined: c.joined || [], left: c.left || [], updated: c.updated || [] })); };
  bc.onmessage = (ev) => { const m = ev.data; deliver(() => {
    if (m.kind === 'evt') (handlers[m.topic] || []).forEach(h => h({ topic: m.topic, data: m.data, peer: m.peer, isMe: false, sameTab: false, by: null, kind: 'viewer', guest: false }));
    if (m.kind === 'pres') {
      const was = peers.has(m.peer);
      const p = { peer: m.peer, isMe: false, sameTab: false, presence: m.presence, by: null, kind: 'viewer', guest: false, updatedAt: Date.now() };
      peers.set(m.peer, p); firePeers(was ? { updated: [p] } : { joined: [p] });
      if (!was) bc.postMessage({ kind: 'pres', peer: me, presence: myPresence });
    }
  }); };
  const room = {
    emit: async (topic, data) => { bc.postMessage({ kind: 'evt', topic, data: JSON.parse(JSON.stringify(data)), peer: me }); (handlers[topic] || []).forEach(h => setTimeout(() => h({ topic, data, peer: me, isMe: true, sameTab: true }), 0)); },
    on: (topic, fn) => { (handlers[topic] = handlers[topic] || []).push(fn); return () => {}; },
    presence: async (patch) => { const n = { ...myPresence }; for (const [k, v] of Object.entries(patch)) { if (v === null) delete n[k]; else n[k] = v; } myPresence = n; bc.postMessage({ kind: 'pres', peer: me, presence: myPresence }); firePeers({}); },
    peers: () => snapshot(),
    onPeers: (fn) => { peerHandlers.push(fn); setTimeout(() => fn({ peers: snapshot(), joined: snapshot(), left: [], updated: [] }), 0); return () => {}; },
    connected: () => true,
    onConnection: (fn) => { setTimeout(() => fn(true), 0); return () => {}; },
  };
  const student = location.search.includes('student');
  const user = { canEdit: async () => !student, isOwner: async () => !student };
  window.claude = { use: async (name) => name === 'room' ? room : name === 'user' ? user : null };
  setTimeout(() => bc.postMessage({ kind: 'pres', peer: me, presence: myPresence }), 100);
})();
