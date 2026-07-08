/* ============================================================================
   auth.js — client-side MOCK authentication + session for the prototype.

   ⚠️ This SIMULATES a backend so the flow is fully clickable without a server:
     • "Database"           = localStorage  (key: afc_users)
     • "Session"            = sessionStorage (key: afc_session, 60-min TTL)
     • "Server-side checks" = validation run inside these async calls, with latency
   Passwords are stored in PLAIN TEXT for the demo ONLY. A real backend MUST hash
   them and enforce these same rules server-side. See HANDOFF.md.

   Seeded demo user (so "existing user login" works out of the box):
     email: priya@example.com   password: priya123
   ============================================================================ */
(function () {
  'use strict';

  var USERS_KEY = 'afc_users';
  var SESSION_KEY = 'afc_session';
  var SESSION_TTL_MS = 60 * 60 * 1000; // 60 minutes
  var LATENCY = 550;                   // simulated server round-trip
  var MIN_PW = 8;
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var LOGIN_PAGE = '01.2-login.html';
  var HOME_PAGE = '01.3-statement-upload.html';

  function readUsers() { try { return JSON.parse(localStorage.getItem(USERS_KEY) || '[]'); } catch (e) { return []; } }
  function writeUsers(u) { localStorage.setItem(USERS_KEY, JSON.stringify(u)); }
  function norm(email) { return (email || '').trim().toLowerCase(); }
  function findUser(email) { var e = norm(email); return readUsers().filter(function (u) { return u.email === e; })[0] || null; }

  // Seed a demo existing user once.
  (function seed() {
    var users = readUsers();
    if (!users.some(function (u) { return u.email === 'priya@example.com'; })) {
      users.push({ email: 'priya@example.com', password: 'priya123', name: 'Priya', createdAt: Date.now() });
      writeUsers(users);
    }
  })();

  function delay(ms) { return new Promise(function (r) { setTimeout(r, ms == null ? LATENCY : ms); }); }

  /* ---- Registration (server-side validation + unique email) ---- */
  function register(data) {
    return delay().then(function () {
      var email = norm(data.email), pw = data.password || '';
      if (!email) throw { field: 'email', message: 'Email is required' };
      if (!EMAIL_RE.test(email)) throw { field: 'email', message: 'Enter a valid email address' };
      if (!pw) throw { field: 'password', message: 'Password is required' };
      if (pw.length < MIN_PW) throw { field: 'password', message: 'Password must be at least ' + MIN_PW + ' characters' };
      if (findUser(email)) throw { field: 'email', message: 'This email is already registered' };
      var users = readUsers();
      users.push({ email: email, password: pw, name: email.split('@')[0], createdAt: Date.now() });
      writeUsers(users);
      return { email: email };
    });
  }

  /* ---- Login (validate credentials, create session) ---- */
  function login(data) {
    return delay().then(function () {
      var email = norm(data.email), pw = data.password || '';
      if (!email || !pw) throw { message: 'Enter your email and password' };
      var user = findUser(email);
      if (!user || user.password !== pw) throw { message: 'Incorrect email or password' };
      var session = { email: user.email, name: user.name, loginAt: Date.now(), exp: Date.now() + SESSION_TTL_MS };
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
      return { email: user.email, name: user.name };
    });
  }

  /* ---- Password reset (simulated; production would email a signed link) ---- */
  function resetPassword(data) {
    return delay().then(function () {
      var email = norm(data.email), pw = data.newPassword || '';
      if (!EMAIL_RE.test(email)) throw { field: 'email', message: 'Enter a valid email address' };
      var users = readUsers(), idx = users.map(function (u) { return u.email; }).indexOf(email);
      if (idx === -1) throw { field: 'email', message: 'No account found with that email' };
      if (pw.length < MIN_PW) throw { field: 'newPassword', message: 'Password must be at least ' + MIN_PW + ' characters' };
      users[idx].password = pw; writeUsers(users);
      return { email: email };
    });
  }

  function emailExists(email) { return !!findUser(email); }

  /* ---- Session ---- */
  function getSession() {
    try {
      var s = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null');
      if (!s || !s.email) return null;
      if (s.exp && Date.now() > s.exp) { sessionStorage.removeItem(SESSION_KEY); return null; }
      return s;
    } catch (e) { return null; }
  }
  function currentUser() { var s = getSession(); return s ? { email: s.email, name: s.name } : null; }

  function logout(redirect) {
    sessionStorage.removeItem(SESSION_KEY);
    if (redirect !== false) window.location.replace(LOGIN_PAGE);
  }

  /* ---- Route guards ---- */
  function requireAuth() {
    if (!getSession()) { window.location.replace(LOGIN_PAGE); return false; }
    return true;
  }
  function redirectIfAuthed(to) {
    if (getSession()) { window.location.replace(to || HOME_PAGE); return true; }
    return false;
  }

  window.Auth = {
    register: register, login: login, resetPassword: resetPassword, emailExists: emailExists,
    getSession: getSession, currentUser: currentUser, logout: logout,
    requireAuth: requireAuth, redirectIfAuthed: redirectIfAuthed,
    LOGIN_PAGE: LOGIN_PAGE, HOME_PAGE: HOME_PAGE, MIN_PW: MIN_PW, EMAIL_RE: EMAIL_RE
  };
})();
