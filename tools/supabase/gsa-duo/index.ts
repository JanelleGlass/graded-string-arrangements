// Duo practice logins for the Graded String Arrangements website (Supabase project violin-studio, function gsa-duo).
// Deployed by hand (Supabase dashboard or a Claude session); this copy in the repo is the source. No secrets in it.
//
// A duo login is not a studio account: it is a row in public.gsa_duos with a username, a PBKDF2 hash of its password
// and a secret room name. Nobody can read that table except this function (service role). Actions:
//   login  {username, password}          anyone: the room for that username, if the password matches
//   list   (teacher)                      the duos this teacher made: username, created, last used
//   create {username, password} (teacher) a new duo, with a new room
//   reset  {username, password} (teacher) a new password and a new room (the old tablets are signed out)
//   remove {username} (teacher)
// "Teacher" means the caller's Supabase session belongs to someone in public.conduct_classes (who may conduct).
// Everything comes back as 200 with ok: false and a message, because supabase-js drops the body of an error.
import { createClient } from 'npm:@supabase/supabase-js@2';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
const no = (error: string) => json({ ok: false, error });

const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });

const ITERATIONS = 150000;
const hex = (b: ArrayBuffer | Uint8Array) => [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
const random = (n: number) => hex(crypto.getRandomValues(new Uint8Array(n)));
async function hash(password: string, salt: string) {
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: new TextEncoder().encode(salt), iterations: ITERATIONS }, key, 256);
  return hex(bits);
}
function same(a: string, b: string) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}
const cleanName = (u: unknown) => String(u ?? '').trim().toLowerCase();
const NAME_OK = /^[a-z0-9][a-z0-9._-]{2,39}$/;
const PASS_OK = (p: string) => p.length >= 6 && p.length <= 100;

async function teacherOf(req: Request) {
  const token = (req.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '');
  if (!token) return null;
  const { data, error } = await admin.auth.getUser(token);
  if (error || !data?.user) return null;
  const { data: rows } = await admin.from('conduct_classes').select('teacher_id').eq('teacher_id', data.user.id).limit(1);
  return rows && rows.length ? data.user.id : null;
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  if (req.method !== 'POST') return json({ ok: false, error: 'Method not allowed' }, 405);
  const body = await req.json().catch(() => ({}));
  const action = String(body.action || '');
  const username = cleanName(body.username);
  const password = String(body.password ?? '');

  if (action === 'login') {
    if (!username || !password) return no('Type the username and password.');
    const { data: duo, error } = await admin.from('gsa_duos').select('id, username, pass_salt, pass_hash, room').eq('username', username).maybeSingle();
    if (error) return no('Couldn’t check that just now. Try again.');
    // The same work and the same answer whether or not the username exists.
    const h = await hash(password, duo ? duo.pass_salt : 'no-such-duo');
    if (!duo || !same(h, duo.pass_hash)) return no('That username and password don’t match.');
    await admin.from('gsa_duos').update({ last_login_at: new Date().toISOString() }).eq('id', duo.id);
    return json({ ok: true, username: duo.username, room: duo.room });
  }

  const teacher = await teacherOf(req);
  if (!teacher) return no('Sign in as the teacher first.');

  if (action === 'list') {
    const { data, error } = await admin.from('gsa_duos').select('username, created_at, last_login_at').eq('created_by', teacher).order('username');
    return error ? no('Couldn’t load the duos.') : json({ ok: true, duos: data });
  }
  if (action === 'create' || action === 'reset') {
    if (!NAME_OK.test(username)) return no('A username is 3 to 40 letters, numbers, dots, dashes or underscores, starting with a letter or number.');
    if (!PASS_OK(password)) return no('A password needs at least 6 characters.');
    const salt = random(16), pass_hash = await hash(password, salt), room = random(16);
    if (action === 'create') {
      const { error } = await admin.from('gsa_duos').insert({ username, pass_salt: salt, pass_hash, room, created_by: teacher });
      if (error) return no(/duplicate|unique/i.test(error.message) ? 'That username is taken. Choose another.' : 'Couldn’t make the duo.');
      return json({ ok: true, username });
    }
    const { data, error } = await admin.from('gsa_duos').update({ pass_salt: salt, pass_hash, room }).eq('username', username).eq('created_by', teacher).select('username');
    if (error || !data?.length) return no('No duo with that username.');
    return json({ ok: true, username });
  }
  if (action === 'remove') {
    const { data, error } = await admin.from('gsa_duos').delete().eq('username', username).eq('created_by', teacher).select('username');
    if (error || !data?.length) return no('No duo with that username.');
    return json({ ok: true });
  }
  return no('Unknown action.');
});
