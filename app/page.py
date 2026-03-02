"""Embedded HTML/CSS/JS single-page admin UI."""

PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Company &amp; User Management</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; min-height: 100vh; padding: 24px 16px; }
  .container { max-width: 1400px; margin: 0 auto; }
  h1 { color: #1a1a2e; margin-bottom: 4px; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  .logout { color: #e74c3c; text-decoration: none; font-weight: 600; cursor: pointer; }
  .logout:hover { text-decoration: underline; }

  /* tabs */
  .tabs { display: flex; gap: 4px; margin-bottom: 16px; }
  .tab { padding: 8px 18px; border: none; border-radius: 6px 6px 0 0; background: #ddd; color: #555; font-size: 14px; font-weight: 600; cursor: pointer; }
  .tab.active { background: #fff; color: #0f3460; box-shadow: 0 -2px 6px rgba(0,0,0,.08); }
  .tab:hover:not(.active) { background: #ccc; }
  .panel { display: none; background: #fff; border-radius: 0 10px 10px 10px; box-shadow: 0 2px 8px rgba(0,0,0,.08); padding: 24px; }
  .panel.active { display: block; }

  /* hierarchy tree */
  .tree-box { background: #f7f9fc; border: 1px solid #e0e4ea; border-radius: 8px; padding: 14px 18px; margin-bottom: 18px; overflow: hidden; }
  .tree-box h3 { font-size: 14px; color: #555; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .5px; }
  .tree-node { padding: 4px 0 4px 0; font-size: 14px; color: #1a1a2e; }
  .tree-node .indent { display: inline-block; width: 20px; }
  .tree-node .connector { color: #aaa; margin-right: 4px; }
  .tree-node .badge { display: inline-block; background: #0f3460; color: #fff; border-radius: 10px; padding: 1px 8px; font-size: 11px; margin-left: 6px; }
  .tree-hidden { display: none; }

  /* cards / forms */
  .card { margin-bottom: 20px; }
  .card h2 { font-size: 16px; color: #16213e; margin-bottom: 12px; }
  .form-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-end; }
  .form-row input, .form-row select, .form-row textarea { padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; }
  .form-row input:focus, .form-row select:focus, .form-row textarea:focus { outline: none; border-color: #0f3460; box-shadow: 0 0 0 2px rgba(15,52,96,.2); }
  .form-row input { flex: 1; min-width: 100px; }
  .form-row textarea { flex: 1; min-width: 200px; resize: vertical; max-height: 60px; }
  .form-row select { min-width: 140px; }
  .btn { padding: 8px 16px; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }
  .btn-primary { background: #0f3460; color: #fff; }
  .btn-primary:hover { background: #16213e; }
  .btn-danger { background: #e74c3c; color: #fff; font-size: 12px; padding: 5px 10px; }
  .btn-danger:hover { background: #c0392b; }
  .btn-edit { background: #0f3460; color: #fff; font-size: 12px; padding: 5px 10px; }
  .btn-edit:hover { background: #16213e; }

  /* multi-select checkboxes */
  .checks { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .checks label { font-size: 13px; color: #444; display: flex; align-items: center; gap: 4px; }

  /* table */
  table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  th { text-align: left; padding: 8px 10px; border-bottom: 2px solid #eee; color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }
  td { padding: 10px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  .empty { color: #999; font-style: italic; }
  .tag { display: inline-block; background: #eef2f7; color: #0f3460; border-radius: 4px; padding: 2px 7px; font-size: 11px; margin: 1px 2px; }
  .tag-admin { background: #0f3460; color: #fff; }
  .tag-superadmin { background: #d63031; color: #fff; }
  .error { color: #e74c3c; margin-top: 6px; font-size: 12px; display: none; }
  .error.visible { display: block; }

  /* me-card */
  .me-card { background: #eef2f7; border: 1px solid #dce3ec; border-radius: 8px; padding: 14px 18px; margin-bottom: 18px; }
  .me-card .me-label { font-size: 12px; color: #555; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
  .me-card .me-row { font-size: 14px; margin-bottom: 3px; color: #1a1a2e; }
  .me-card .me-row strong { color: #0f3460; }
  .me-unlinked { color: #888; font-style: italic; }
  .me-sub { font-size: 11px; color: #888; font-family: monospace; margin-top: 4px; word-break: break-all; }

  /* ── folder tree (companies panel) ─────────────────────────────────── */
  .ftree { font-size: 13px; user-select: none; }
  .ftree-node + .ftree-node { margin-top: 1px; }
  .ftree-row { display: flex; align-items: center; gap: 6px; padding: 5px 6px 5px 0; border-radius: 5px; }
  .ftree-row:hover { background: #f5f7fa; }
  .ftree-toggle { background: none; border: none; cursor: pointer; font-size: 11px; color: #aaa; width: 16px; min-width: 16px; padding: 0; line-height: 1; text-align: center; }
  .ftree-toggle:hover { color: #0f3460; }
  .ftree-spacer { width: 16px; min-width: 16px; }
  .ftree-icon { font-size: 15px; min-width: 18px; text-align: center; }
  .ftree-label { font-weight: 500; color: #1a1a2e; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ftree-badges { display: flex; gap: 3px; flex-wrap: wrap; }
  .ftree-hier { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; font-size: 10px; }
  .ftree-actions { margin-left: 8px; flex-shrink: 0; }
  .ftree-children { border-left: 2px solid #e8edf3; margin-left: 15px; padding-left: 6px; }
  .ftree-children.collapsed { display: none; }
  .ftree-empty { color: #999; font-style: italic; padding: 8px 0; }

  /* ── access tree — interactive company picker (users panel) ─────────── */
  .at-tree { font-size: 13px; user-select: none; }
  .at-node + .at-node { margin-top: 1px; }
  .at-row { display: flex; align-items: center; gap: 6px; padding: 5px 6px 5px 0; border-radius: 6px; flex-wrap: wrap; transition: background .1s; cursor: default; }
  .at-row:hover { background: #f5f7fa; }
  .at-name { font-weight: 500; color: #1a1a2e; min-width: 80px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
  .at-flags { display: flex; gap: 5px; align-items: center; flex-shrink: 0; }
  .at-flag { font-size: 11px; display: inline-flex; align-items: center; gap: 3px; cursor: pointer; white-space: nowrap; padding: 2px 8px; border-radius: 10px; border: 1px solid #dde; transition: border-color .1s; }
  .at-flag:hover { border-color: #0f3460; }
  .at-flag-allowed { color: #2e7d32; border-color: #c8e6c9; }
  .at-flag-blocked { color: #c62828; border-color: #ffcdd2; }
  .at-flag input[type=checkbox] { cursor: pointer; margin: 0; }
  .at-flag-allowed input[type=checkbox]:checked { accent-color: #2e7d32; }
  .at-flag-blocked input[type=checkbox]:checked { accent-color: #c62828; }
  .at-meta { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
  .at-role-tag  { background: #e8f4f8; color: #0a7ea4; border-radius: 10px; padding: 1px 8px; font-size: 10px; }
  .at-perm-plus { background: #e8f5e9; color: #2e7d32; border-radius: 10px; padding: 1px 8px; font-size: 10px; }
  .at-row-allowed { background: rgba(46,125,50,.07) !important; }
  .at-row-blocked { background: rgba(198,40,40,.07) !important; }

  /* company details modal */
  .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center; }
  .modal-overlay.visible { display: flex; }
  .modal-box { background: #fff; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); padding: 24px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto; }
  .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .modal-header h2 { font-size: 18px; color: #0f3460; margin: 0; }
  .modal-close { background: none; border: none; font-size: 24px; color: #999; cursor: pointer; padding: 0; line-height: 1; }
  .modal-close:hover { color: #e74c3c; }
  .modal-section { margin-bottom: 16px; }
  .modal-section h3 { font-size: 14px; color: #555; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .5px; }
  .modal-list { display: flex; flex-wrap: wrap; gap: 6px; }

  /* auth overlay */
  .token-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,52,96,0.95); z-index: 2000; align-items: center; justify-content: center; }
  .token-overlay.visible { display: flex; }
  .token-box { background: #fff; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); padding: 36px; max-width: 420px; width: 90%; }
  .token-box h2 { color: #0f3460; margin-bottom: 6px; font-size: 22px; }
  .token-box .auth-subtitle { font-size: 13px; color: #777; margin-bottom: 22px; }
  .token-box input[type="text"],
  .token-box input[type="password"] { width: 100%; padding: 10px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; margin-bottom: 12px; display: block; }
  .token-box input:focus { outline: none; border-color: #0f3460; box-shadow: 0 0 0 2px rgba(15,52,96,.15); }
  .token-box .btn-primary { width: 100%; padding: 11px; font-size: 14px; margin-top: 4px; }
  .auth-error { color: #e74c3c; font-size: 13px; margin-bottom: 10px; min-height: 18px; }
  .auth-switch { text-align: center; margin-top: 16px; font-size: 12px; color: #999; }
  .auth-switch a { color: #0f3460; cursor: pointer; text-decoration: underline; }
  .token-box textarea { width: 100%; height: 80px; padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 11px; font-family: monospace; resize: none; margin-bottom: 12px; display: block; }
  .token-box textarea:focus { outline: none; border-color: #0f3460; }
</style>
</head>
<body>

<!-- Auth overlay — username/password (default) or raw token (advanced) -->
<div class="token-overlay" id="tokenOverlay">
  <div class="token-box">

    <!-- ── Login form (shown by default) ── -->
    <div id="authLoginPanel">
      <h2>Sign In</h2>
      <p class="auth-subtitle">Sign in with your Cognito account.</p>
      <div class="auth-error" id="loginError"></div>
      <input type="text"     id="loginUsername" placeholder="Username" autocomplete="username"
             onkeydown="if(event.key==='Enter') doLogin()" />
      <input type="password" id="loginPassword" placeholder="Password" autocomplete="current-password"
             onkeydown="if(event.key==='Enter') doLogin()" />
      <button class="btn btn-primary" id="loginBtn" onclick="doLogin()">Sign In</button>
      <div class="auth-switch">
        <a onclick="switchToTokenPanel()">Paste access token instead</a>
      </div>
    </div>

    <!-- ── Raw-token panel (advanced / fallback) ── -->
    <div id="authTokenPanel" style="display:none;">
      <h2>Paste Token</h2>
      <p class="auth-subtitle">Paste a Cognito <strong>access token</strong> obtained via the AWS CLI or Hosted UI.</p>
      <div class="auth-error" id="tokenError"></div>
      <textarea id="tokenInput" placeholder="eyJraWQiOiJ…"></textarea>
      <button class="btn btn-primary" onclick="saveToken()">Authenticate</button>
      <div class="auth-switch">
        <a onclick="switchToLoginPanel()">Back to sign in</a>
      </div>
    </div>

  </div>
</div>

<div class="container">
  <div class="header">
    <h1>Company &amp; User Management</h1>
    <a class="logout" onclick="clearToken(); return false;" href="#">Logout (clear token)</a>
  </div>

  <!-- me-card: filled by JS on load -->
  <div class="me-card" id="meCard"></div>

  <!-- tabs -->
  <div class="tabs">
    <button class="tab active" onclick="switchTab('users')">Users</button>
    <button class="tab"        onclick="switchTab('companies')">Companies</button>
    <button class="tab"        onclick="switchTab('roles')">Roles</button>
    <button class="tab"        onclick="switchTab('access')">Try Access</button>
  </div>

  <!-- ===== USERS PANEL ===== -->
  <div class="panel active" id="panel-users">

    <div class="card" id="addUserCard">
      <h2 id="addUserTitle">Add User</h2>
      <div class="form-row" style="margin-top:8px;">
        <input id="u-username" placeholder="Username (required)" />
        <input id="u-name" placeholder="Full name" />
        <input id="u-email" placeholder="Email" />
      </div>
      <div class="form-row" style="margin-top:6px;">
        <input id="u-cognito-sub" placeholder="Cognito sub UUID (required)" style="font-family:monospace;font-size:12px;" />
      </div>

      <!-- ── interactive company access tree ── -->
      <div style="margin-top:14px;">
        <strong style="font-size:13px;color:#444;">Company Access</strong>
        <span style="font-size:11px;color:#888;margin-left:8px;">
          ✅ Allowed &nbsp;|&nbsp; 🚫 Blocked — checking a parent propagates to children
        </span>
        <div style="margin-top:8px;border:1px solid #e0e4ea;border-radius:8px;padding:10px 14px;max-height:420px;overflow-y:auto;background:#fafbfc;">
          <div id="accessTreeContainer"><div class="ftree-empty">Loading…</div></div>
        </div>
      </div>
      <div style="margin-top:10px;">
        <strong style="font-size:13px;color:#444;">Notes:</strong>
        <textarea id="u-notes" placeholder="Notes…" style="margin-left:8px;width:calc(100% - 80px);"></textarea>
      </div>
      <div style="margin-top:10px;" class="checks">
        <label><input type="checkbox" id="u-is-admin" /> Grant admin</label>
        <label><input type="checkbox" id="u-is-superadmin" /> Grant superadmin</label>
      </div>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center;">
        <button class="btn btn-primary" id="addUserBtn" onclick="addUser()">Add User</button>
        <button class="btn" id="cancelEditBtn" style="display:none;background:#eee;color:#333;" onclick="cancelEditUser()">Cancel</button>
      </div>
      <div class="error" id="u-error"></div>
    </div>

    <div class="card">
      <h2>Users</h2>
      <table>
        <thead><tr><th>Name</th><th>User</th><th>Company (role + permissions)</th><th>Blocked</th><th>Notes</th><th></th></tr></thead>
        <tbody id="userTable"><tr><td class="empty" colspan="8">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- ===== COMPANIES PANEL ===== -->
  <div class="panel" id="panel-companies">
    <div class="card">
      <h2>Add Company</h2>
      <div class="form-row">
        <input id="c-name" placeholder="Company name" />
        <select id="c-parent"><option value="">— no parent —</option></select>
        <label style="font-size:13px;display:flex;align-items:center;gap:4px;"><input type="checkbox" id="c-hierarchical"/> Hierarchical</label>
      </div>
      <div style="margin-top:10px;"><button class="btn btn-primary" onclick="addCompany()">Add Company</button></div>
      <div class="error" id="c-error"></div>
    </div>

    <div class="card">
      <h2>Companies</h2>
      <div id="companyTree" class="ftree"><div class="ftree-empty">Loading…</div></div>
    </div>
  </div>

  <!-- ===== ROLES PANEL ===== -->
  <div class="panel" id="panel-roles">
    <div class="card">
      <h2>Add Role</h2>
      <div class="form-row">
        <input id="r-name" placeholder="Role name" />
        <input id="r-desc" placeholder="Description (optional)" />
      </div>
      <div style="margin-top:10px;">
        <strong style="font-size:13px;color:#444;">Permissions:</strong>
        <div class="checks" id="r-perm-checks"></div>
      </div>
      <div style="margin-top:10px;"><button class="btn btn-primary" onclick="addRole()">Add Role</button></div>
      <div class="error" id="r-error"></div>
    </div>

    <div class="card">
      <h2>Roles</h2>
      <table>
        <thead><tr><th>Name</th><th>Description</th><th>Permissions</th><th></th></tr></thead>
        <tbody id="roleTable"><tr><td class="empty" colspan="4">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- ===== TRY ACCESS PANEL ===== -->
  <div class="panel" id="panel-access">
    <div class="card" style="max-width:560px;">
      <h2>Try User Access</h2>
      <p style="font-size:13px;color:#666;margin-bottom:16px;">
        Check whether a user can perform an operation on a company based on their assigned permissions.
      </p>

      <div class="form-row" style="flex-direction:column;gap:12px;">

        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:12px;font-weight:600;color:#444;">User (username)</label>
          <select id="ac-user" style="padding:7px 10px;border:1px solid #ccc;border-radius:6px;font-size:13px;">
            <option value="">— select user —</option>
          </select>
        </div>

        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:12px;font-weight:600;color:#444;">Company</label>
          <select id="ac-company" style="padding:7px 10px;border:1px solid #ccc;border-radius:6px;font-size:13px;">
            <option value="">— select company —</option>
          </select>
        </div>

        <div style="display:flex;flex-direction:column;gap:4px;">
          <label style="font-size:12px;font-weight:600;color:#444;">Operation</label>
          <select id="ac-operation" style="padding:7px 10px;border:1px solid #ccc;border-radius:6px;font-size:13px;">
            <option value="get">Get (requires: read)</option>
            <option value="update">Update (requires: edit)</option>
            <option value="create">Create (requires: edit)</option>
            <option value="delete">Delete (requires: delete)</option>
          </select>
        </div>

      </div>

      <div style="margin-top:16px;">
        <button class="btn btn-primary" onclick="runAccessCheck()">Check Access</button>
      </div>
      <div class="error" id="ac-error"></div>
    </div>

    <div class="card" id="ac-result-card" style="display:none;max-width:560px;">
      <div id="ac-result-body"></div>
    </div>
  </div>

</div>

<!-- Company details modal -->
<div class="modal-overlay" id="companyModal" onclick="if(event.target===this) closeCompanyModal()">
  <div class="modal-box">
    <div class="modal-header">
      <h2 id="modalCompanyName">Company Details</h2>
      <button class="modal-close" onclick="closeCompanyModal()">&times;</button>
    </div>
    <div class="modal-section">
      <h3>Users</h3>
      <div class="modal-list" id="modalUsers">—</div>
    </div>
    <div class="modal-section">
      <h3>Roles</h3>
      <div class="modal-list" id="modalRoles">—</div>
    </div>
    <div class="modal-section">
      <h3>Permissions</h3>
      <div class="modal-list" id="modalPermissions">—</div>
    </div>
  </div>
</div>

<script>
// ---------------------------------------------------------------------------
// Global data cache
// ---------------------------------------------------------------------------
let DATA = { permissions: [], roles: [], companies: [], users: [] };
let ACTIVE_COMPANY_IDS = new Set();

// ---------------------------------------------------------------------------
// Token management (Cognito bearer auth)
// ---------------------------------------------------------------------------
function getToken() { return localStorage.getItem('cognito_access_token') || ''; }

function _storeAndClose(accessToken) {
  localStorage.setItem('cognito_access_token', accessToken);
  document.getElementById('tokenOverlay').classList.remove('visible');
  renderMe();
  refreshPanel('users');
}

function showTokenOverlay() {
  switchToLoginPanel();
  document.getElementById('tokenOverlay').classList.add('visible');
}

function clearToken() {
  localStorage.removeItem('cognito_access_token');
  document.getElementById('meCard').innerHTML = '';
  showTokenOverlay();
}

// ── Panel switching ──────────────────────────────────────────────────────────
function switchToLoginPanel() {
  document.getElementById('authLoginPanel').style.display = '';
  document.getElementById('authTokenPanel').style.display = 'none';
  document.getElementById('loginError').textContent = '';
  document.getElementById('loginUsername').focus();
}
function switchToTokenPanel() {
  document.getElementById('authLoginPanel').style.display = 'none';
  document.getElementById('authTokenPanel').style.display = '';
  document.getElementById('tokenError').textContent = '';
  document.getElementById('tokenInput').focus();
}

// ── Username / password login ────────────────────────────────────────────────
async function doLogin() {
  const btn      = document.getElementById('loginBtn');
  const errEl    = document.getElementById('loginError');
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  errEl.textContent = '';
  if (!username || !password) { errEl.textContent = 'Username and password are required.'; return; }

  btn.disabled = true;
  btn.textContent = 'Signing in…';
  try {
    const res = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Login failed.'; return; }
    document.getElementById('loginPassword').value = '';
    _storeAndClose(data.access_token);
  } catch (e) {
    errEl.textContent = 'Network error — is the server reachable?';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
}

// ── Raw-token paste (advanced) ───────────────────────────────────────────────
function saveToken() {
  const t = document.getElementById('tokenInput').value.trim();
  if (!t) { document.getElementById('tokenError').textContent = 'Paste a token first.'; return; }
  _storeAndClose(t);
}

// ---------------------------------------------------------------------------
// Generic API helper — injects Bearer token on every request
// ---------------------------------------------------------------------------
async function api(method, url, body) {
  const token = getToken();
  if (!token) { showTokenOverlay(); return []; }
  const headers = { 'Authorization': 'Bearer ' + token };
  if (body) headers['Content-Type'] = 'application/json';
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (res.status === 401) { showTokenOverlay(); return []; }
  if (!res.ok) throw new Error(await res.text() || res.statusText);
  return res.json();
}

function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function showErr(id, msg) { const el = document.getElementById(id); el.textContent = msg; el.className = 'error visible'; }
function clearErr(id)     { document.getElementById(id).className = 'error'; }

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
const _TAB_NAMES    = ['users','companies','roles','access'];
const _PANEL_NAMES  = ['panel-users','panel-companies','panel-roles','panel-access'];

function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', _TAB_NAMES[i] === name));
  document.querySelectorAll('.panel').forEach((p,i) => p.classList.toggle('active', _PANEL_NAMES[i] === 'panel-'+name));
  refreshPanel(name);
}

async function refreshPanel(name) {
  DATA.permissions = await api('GET','/api/permissions');
  if (name === 'users')     { DATA.companies = await api('GET','/api/companies'); DATA.roles = await api('GET','/api/roles'); DATA.users = await api('GET','/api/users'); renderUsers(); }
  if (name === 'companies') { DATA.companies = await api('GET','/api/companies'); DATA.roles = await api('GET','/api/roles'); renderCompanies(); }
  if (name === 'roles')     { DATA.roles = await api('GET','/api/roles'); renderRoles(); }
  if (name === 'access')    { DATA.companies = await api('GET','/api/companies'); DATA.users = await api('GET','/api/users'); renderAccessCheck(); }
}

// ---------------------------------------------------------------------------
// Company details modal
// ---------------------------------------------------------------------------
function showCompanyModal(companyId) {
  const company = DATA.companies.find(c => c.id === companyId);
  if (!company) return;

  document.getElementById('modalCompanyName').textContent = company.name;

  const companyUsers = DATA.users.filter(u => u.company_ids && u.company_ids.includes(companyId));
  let usersHtml = companyUsers.map(u => `<span class="tag">${esc(u.name || u.username || 'Unknown')}</span>`).join('');
  document.getElementById('modalUsers').innerHTML = usersHtml || '—';

  // Roles: direct first, then walk up to first ancestor with roles
  let rolesHtml = '';
  if (company.role_ids.length > 0) {
    rolesHtml = company.role_ids.map(id => { const r = DATA.roles.find(x=>x.id===id); return r ? `<span class="tag">${esc(r.name)}</span>` : ''; }).join('');
  } else {
    let cur = company;
    while (cur && cur.parent_id) {
      const parent = DATA.companies.find(c => c.id === cur.parent_id);
      if (!parent) break;
      if (parent.role_ids.length > 0) {
        rolesHtml = parent.role_ids.map(id => { const r = DATA.roles.find(x=>x.id===id); return r ? `<span class="tag" style="background:#e8f4f8;color:#0a7ea4;" title="Inherited from ${esc(parent.name)}">${esc(r.name)} ↑</span>` : ''; }).join('');
        break;
      }
      cur = parent;
    }
  }
  document.getElementById('modalRoles').innerHTML = rolesHtml || '—';

  // Permissions: same pattern
  let permsHtml = '';
  if (company.permission_ids.length > 0) {
    permsHtml = company.permission_ids.map(id => { const p = DATA.permissions.find(x=>x.id===id); return p ? `<span class="tag">${esc(p.name)}</span>` : ''; }).join('');
  } else {
    let cur = company;
    while (cur && cur.parent_id) {
      const parent = DATA.companies.find(c => c.id === cur.parent_id);
      if (!parent) break;
      if (parent.permission_ids.length > 0) {
        permsHtml = parent.permission_ids.map(id => { const p = DATA.permissions.find(x=>x.id===id); return p ? `<span class="tag" style="background:#e8f4f8;color:#0a7ea4;" title="Inherited from ${esc(parent.name)}">${esc(p.name)} ↑</span>` : ''; }).join('');
        break;
      }
      cur = parent;
    }
  }
  document.getElementById('modalPermissions').innerHTML = permsHtml || '—';

  document.getElementById('companyModal').classList.add('visible');
}

function closeCompanyModal() {
  document.getElementById('companyModal').classList.remove('visible');
}

// ---------------------------------------------------------------------------
// /api/me banner
// ---------------------------------------------------------------------------
function getDescendants(companyId, companies) {
  const result = [];
  const children = companies.filter(c => c.parent_id === companyId);
  for (const ch of children) {
    result.push(ch.id);
    result.push(...getDescendants(ch.id, companies));
  }
  return result;
}

async function renderMe() {
  let me;
  try { me = await api('GET', '/api/me'); } catch(e) { return; }
  if (!me || !me.sub) return;
  const el = document.getElementById('meCard');
  if (!me.user_info) {
    el.innerHTML =
      '<div class="me-label">Authenticated via Cognito</div>' +
      '<div class="me-row"><strong>' + esc(me.username || me.sub) + '</strong> <span class="me-unlinked">(not yet linked to a local user record)</span></div>' +
      '<div class="me-sub">sub: ' + esc(me.sub) + '</div>';
    return;
  }
  const info = me.user_info;
  const tag  = (txt, style) => `<span class="tag" style="${style||''}">${esc(txt)}</span>`;
  const adminBadge = info.is_superadmin
    ? tag('superadmin', 'background:#6a1b9a;color:#fff;')
    : info.is_admin
      ? tag('admin', 'background:#1565c0;color:#fff;')
      : tag('user', '');

  // Per-company rows
  const companyRows = (info.companies || []).map(c => {
    const chain = (c.chain || []).map(x => esc(x.name)).join(' &rsaquo; ');
    const roleTag  = c.role ? tag(c.role, 'background:#e8eaf6;color:#283593;') : '';
    const permTags = (c.permissions || []).map(p => tag(p, 'background:#e8f5e9;color:#2e7d32;')).join(' ');
    return `<div style="margin-bottom:4px;line-height:1.6;">
      <span style="font-size:12px;color:#555;">${chain}</span>
      ${roleTag} ${permTags}
    </div>`;
  }).join('') || '—';

  // Blocked companies
  const blockedRow = (info.blocked_companies || []).length
    ? (info.blocked_companies || []).map(c => tag(c.name, 'background:#fee;color:#c33;')).join(' ')
    : '';

  el.innerHTML =
    '<div class="me-label">Logged in as</div>' +
    `<div class="me-row"><strong>${esc(me.username || me.sub)}</strong> &nbsp; ${adminBadge}</div>` +
    `<div class="me-row"><strong>Companies:</strong><br>${companyRows}</div>` +
    (blockedRow ? `<div class="me-row"><strong>Blocked:</strong> ${blockedRow}</div>` : '');
}

async function computeActiveCompanies() {
  let me;
  try { me = await api('GET', '/api/me'); } catch(e) { ACTIVE_COMPANY_IDS.clear(); return; }
  if (!me || !me.user_info) { ACTIVE_COMPANY_IDS.clear(); return; }
  const info = me.user_info;
  ACTIVE_COMPANY_IDS = new Set();
  if (info.companies) {
    for (const company of info.companies) {
      ACTIVE_COMPANY_IDS.add(company.id);
      getDescendants(company.id, DATA.companies).forEach(id => ACTIVE_COMPANY_IDS.add(id));
    }
  }
  if (info.blocked_companies) {
    for (const bc of info.blocked_companies) {
      ACTIVE_COMPANY_IDS.delete(bc.id);
      getDescendants(bc.id, DATA.companies).forEach(id => ACTIVE_COMPANY_IDS.delete(id));
    }
  }
}

// ---------------------------------------------------------------------------
// Render checkboxes
// ---------------------------------------------------------------------------
function renderChecks(containerId, items, prefix) {
  document.getElementById(containerId).innerHTML = items.map(it =>
    `<label><input type="checkbox" class="${prefix}-check" data-id="${it.id}"/> ${esc(it.name)}</label>`
  ).join('');
}
function getCheckedIds(cssClass) {
  return [...document.querySelectorAll('.'+cssClass+':checked')].map(el => +el.dataset.id);
}

// ---------------------------------------------------------------------------
// ROLES
// ---------------------------------------------------------------------------
function renderRoles() {
  renderChecks('r-perm-checks', DATA.permissions, 'rp');
  const tb = document.getElementById('roleTable');
  tb.innerHTML = DATA.roles.length === 0
    ? '<tr><td class="empty" colspan="4">No roles yet.</td></tr>'
    : DATA.roles.map(r => {
        const permNames = r.permission_ids.map(id => { const p = DATA.permissions.find(x=>x.id===id); return p ? `<span class="tag">${esc(p.name)}</span>` : ''; }).join('');
        return `<tr><td>${esc(r.name)}</td><td>${esc(r.description)}</td><td>${permNames || '—'}</td><td><button class="btn btn-danger" onclick="delRole(${r.id})">Delete</button></td></tr>`;
      }).join('');
}
async function addRole() {
  clearErr('r-error');
  const name = document.getElementById('r-name').value.trim();
  if (!name) { showErr('r-error','Name is required'); return; }
  try {
    await api('POST','/api/roles',{ name, description: document.getElementById('r-desc').value.trim() || null, permission_ids: getCheckedIds('rp-check') });
    document.getElementById('r-name').value=''; document.getElementById('r-desc').value='';
    document.querySelectorAll('.rp-check').forEach(c=>c.checked=false);
    await refreshPanel('roles');
  } catch(e) { showErr('r-error', e.message); }
}
async function delRole(id) {
  if (!confirm('Delete this role?')) return;
  await api('DELETE','/api/roles/'+id);
  await refreshPanel('roles');
}

// ---------------------------------------------------------------------------
// COMPANIES
// ---------------------------------------------------------------------------
function renderCompanies() {
  // Populate "parent" select
  const pSel = document.getElementById('c-parent');
  pSel.innerHTML = '<option value="">— no parent —</option>' +
    DATA.companies.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');

  const container = document.getElementById('companyTree');
  if (DATA.companies.length === 0) {
    container.innerHTML = '<div class="ftree-empty">No companies yet.</div>';
    return;
  }

  // Build lookup map and find root nodes
  const idSet = new Set(DATA.companies.map(c => c.id));
  const roots = DATA.companies.filter(c => c.parent_id === null || !idSet.has(c.parent_id));

  // Recursively build HTML for one node + its subtree
  function nodeHtml(c, depth) {
    const children  = DATA.companies.filter(x => x.parent_id === c.id);
    const hasKids   = children.length > 0;
    const indent    = depth * 20;
    const icon      = hasKids ? '📁' : '📄';
    const toggleBtn = hasKids
      ? `<button class="ftree-toggle" onclick="ftToggle(${c.id})" title="Toggle">▼</button>`
      : `<span class="ftree-spacer"></span>`;

    let html = `<div class="ftree-node" id="ftnode-${c.id}">`;
    html += `<div class="ftree-row" style="padding-left:${indent}px">`;
    html += toggleBtn;
    html += `<span class="ftree-icon">${icon}</span>`;
    html += `<span class="ftree-label" title="${esc(c.name)}">${esc(c.name)}</span>`;
    if (c.is_hierarchical) html += `<span class="tag ftree-hier">hier</span>`;
    html += `<span class="ftree-actions"><button class="btn btn-danger" onclick="delCompany(${c.id})">Delete</button></span>`;
    html += `</div>`;

    if (hasKids) {
      html += `<div class="ftree-children" id="ftchildren-${c.id}">`;
      for (const ch of children) html += nodeHtml(ch, depth + 1);
      html += `</div>`;
    }

    html += `</div>`;
    return html;
  }

  container.innerHTML = roots.map(r => nodeHtml(r, 0)).join('');
}

function ftToggle(id) {
  const kids   = document.getElementById(`ftchildren-${id}`);
  const btn    = document.querySelector(`#ftnode-${id} > .ftree-row > .ftree-toggle`);
  if (!kids || !btn) return;
  const closing = !kids.classList.contains('collapsed');
  kids.classList.toggle('collapsed', closing);
  btn.textContent = closing ? '▶' : '▼';
  // Update folder icon
  const icon = document.querySelector(`#ftnode-${id} > .ftree-row > .ftree-icon`);
  if (icon) icon.textContent = closing ? '📁' : '📂';
}
async function addCompany() {
  clearErr('c-error');
  const name = document.getElementById('c-name').value.trim();
  if (!name) { showErr('c-error','Name is required'); return; }
  const parentVal = document.getElementById('c-parent').value;
  try {
    await api('POST','/api/companies',{
      name,
      parent_id: parentVal ? +parentVal : null,
      is_hierarchical: document.getElementById('c-hierarchical').checked,
      role_ids: [],
      permission_ids: [],
    });
    document.getElementById('c-name').value='';
    document.getElementById('c-parent').value='';
    document.getElementById('c-hierarchical').checked=false;
    await refreshPanel('companies');
  } catch(e) { showErr('c-error', e.message); }
}
async function delCompany(id) {
  if (!confirm('Delete this company? Users in it will also be deleted.')) return;
  await api('DELETE','/api/companies/'+id);
  await refreshPanel('companies');
}


// ---------------------------------------------------------------------------
// Access-tree state  (company picker in the Add/Edit User form)
// ---------------------------------------------------------------------------
// { [companyId]: { allowed: bool, blocked: bool, role_id, permission_ids } }
let AT_STATE = {};
let EDIT_USER_ID = null;  // null → Add mode; number → Edit mode

function atInit(companies, user) {
  // user: full user object from DATA.users (may be null for a blank add form)
  AT_STATE = {};
  const allowedSet = new Set(user ? (user.company_ids         || []) : []);
  const blockedSet = new Set(user ? (user.blocked_company_ids || []) : []);
  const asgMap     = {};
  if (user && user.company_assignments) {
    user.company_assignments.forEach(a => { asgMap[a.company_id] = a; });
  }
  companies.forEach(c => {
    const a = asgMap[c.id] || {};
    AT_STATE[c.id] = {
      allowed:        allowedSet.has(c.id),
      blocked:        blockedSet.has(c.id),
      role_id:        a.role_id        || null,
      permission_ids: a.permission_ids ? [...a.permission_ids] : [],
    };
  });
}

function atDescendants(cid) {
  const result = [];
  (function walk(id) {
    DATA.companies.filter(c => c.parent_id === id).forEach(c => { result.push(c.id); walk(c.id); });
  })(cid);
  return result;
}

function atToggle(cid, flag) {
  const s = AT_STATE[cid];
  if (!s) return;
  const newVal = !s[flag];
  s[flag] = newVal;

  const desc = atDescendants(cid);

  if (flag === 'allowed') {
    if (newVal) s.blocked = false;                      // mutual exclusivity on this node
    desc.forEach(did => {
      const ds = AT_STATE[did]; if (!ds) return;
      ds.allowed = newVal;
      if (newVal) ds.blocked = false;
    });
  } else if (flag === 'blocked') {
    if (newVal) s.allowed = false;
    desc.forEach(did => {
      const ds = AT_STATE[did]; if (!ds) return;
      ds.blocked = newVal;
      if (newVal) ds.allowed = false;
    });
  }

  atUpdateDom();
}

function atUpdateDom() {
  Object.keys(AT_STATE).forEach(cid => {
    const s  = AT_STATE[+cid];
    const el = document.getElementById(`at-node-${cid}`);
    if (!el) return;

    // Flags
    const acb = el.querySelector('.at-allowed-cb'); if (acb) acb.checked = s.allowed;
    const bcb = el.querySelector('.at-blocked-cb'); if (bcb) bcb.checked = s.blocked;

    // Row highlight
    const row = el.querySelector(':scope > .at-row');
    if (row) {
      row.classList.toggle('at-row-allowed', s.allowed);
      row.classList.toggle('at-row-blocked', s.blocked && !s.allowed);
    }

    // Detail row: show/hide + sync controls
    const detail = document.getElementById(`at-detail-${cid}`);
    if (detail) {
      detail.style.display = s.allowed ? 'flex' : 'none';

      // Sync role select
      const rSel = detail.querySelector('.at-role-sel');
      if (rSel) rSel.value = s.role_id ? String(s.role_id) : '';

      // Sync permission checkboxes
      DATA.permissions.forEach(p => {
        const cb = detail.querySelector(`.at-perm-${+cid}[data-pid="${p.id}"]`);
        if (cb) cb.checked = !!(s.permission_ids && s.permission_ids.includes(p.id));
      });
    }
  });
}

function atFtToggle(id) {
  const kids = document.getElementById(`at-children-${id}`);
  const btn  = document.querySelector(`#at-node-${id} > .at-row > .ftree-toggle`);
  if (!kids || !btn) return;
  const closing = !kids.classList.contains('collapsed');
  kids.classList.toggle('collapsed', closing);
  btn.textContent = closing ? '▶' : '▼';
  const icon = document.querySelector(`#at-node-${id} > .at-row > .ftree-icon`);
  if (icon) icon.textContent = closing ? '📁' : '📂';
}

// Role selected → prepopulate permissions from that role, propagate both down the tree
function atSetRole(cid, roleId) {
  if (!AT_STATE[cid]) return;
  const rid  = roleId ? +roleId : null;
  const role = rid ? DATA.roles.find(r => r.id === rid) : null;
  const perms = role ? (role.permission_ids || []) : [];

  // Apply to this node
  AT_STATE[cid].role_id        = rid;
  AT_STATE[cid].permission_ids = [...perms];

  // Propagate role + permissions to ALL descendants
  atDescendants(cid).forEach(did => {
    if (!AT_STATE[did]) return;
    AT_STATE[did].role_id        = rid;
    AT_STATE[did].permission_ids = [...perms];
  });

  atUpdateDom();
}

// Permission checkbox changed → update only this node (no propagation)
function atSetPerms(cid) {
  if (!AT_STATE[cid]) return;
  AT_STATE[cid].permission_ids = [...document.querySelectorAll(`.at-perm-${cid}:checked`)].map(e => +e.dataset.pid);
  // No atUpdateDom() needed — checkbox state is already correct in the DOM
}

function renderAccessTree(initUser = null) {
  const container = document.getElementById('accessTreeContainer');
  if (!container) return;

  atInit(DATA.companies, initUser);  // null → blank add form; user object → pre-populate edit

  if (DATA.companies.length === 0) {
    container.innerHTML = '<div class="ftree-empty">No companies available.</div>';
    return;
  }

  const idSet = new Set(DATA.companies.map(c => c.id));
  const roots = DATA.companies.filter(c => c.parent_id === null || !idSet.has(c.parent_id));

  function nodeHtml(c, depth) {
    const children  = DATA.companies.filter(x => x.parent_id === c.id);
    const hasKids   = children.length > 0;
    const indent    = depth * 20;
    const s         = AT_STATE[c.id] || {};
    const toggleBtn = hasKids
      ? `<button class="ftree-toggle" onclick="atFtToggle(${c.id})" title="Expand / collapse">▼</button>`
      : `<span class="ftree-spacer"></span>`;
    const icon = hasKids ? '📁' : '📄';

    let html = `<div class="at-node ftree-node" id="at-node-${c.id}">`;

    // ── Main flag row ────────────────────────────────────────────────────
    html += `<div class="at-row${s.allowed ? ' at-row-allowed' : s.blocked ? ' at-row-blocked' : ''}" style="padding-left:${indent}px">`;
    html += toggleBtn;
    html += `<span class="ftree-icon">${icon}</span>`;
    html += `<span class="at-name" title="${esc(c.name)}">${esc(c.name)}</span>`;
    html += `<span class="at-flags">`;
    html += `<label class="at-flag at-flag-allowed" title="Grant access (propagates to children)">`;
    html += `<input type="checkbox" class="at-allowed-cb"${s.allowed ? ' checked' : ''} onchange="atToggle(${c.id},'allowed')"> ✅ Allowed</label>`;
    html += `<label class="at-flag at-flag-blocked" title="Block access including all descendants">`;
    html += `<input type="checkbox" class="at-blocked-cb"${s.blocked ? ' checked' : ''} onchange="atToggle(${c.id},'blocked')"> 🚫 Blocked</label>`;
    html += `</span>`;
    html += `</div>`;

    // ── Per-company role + permission detail row (visible only when Allowed) ──
    const detailDisplay = s.allowed ? 'flex' : 'none';
    html += `<div class="at-detail" id="at-detail-${c.id}" style="display:${detailDisplay};padding-left:${indent + 38}px;gap:12px;flex-wrap:wrap;align-items:flex-start;padding-bottom:8px;padding-top:2px;background:#f8fbff;border-left:2px solid #c5d8f5;margin-bottom:2px;">`;

    // Role dropdown
    html += `<div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">`;
    html += `<label style="font-size:12px;color:#555;white-space:nowrap;">Role:</label>`;
    html += `<select class="at-role-sel" style="font-size:12px;padding:2px 6px;border:1px solid #ccc;border-radius:4px;" onchange="atSetRole(${c.id},this.value)">`;
    html += `<option value="">— none —</option>`;
    DATA.roles.forEach(r => {
      const sel = (s.role_id == r.id) ? ' selected' : '';
      html += `<option value="${r.id}"${sel}>${esc(r.name)}</option>`;
    });
    html += `</select></div>`;

    // Permission checkboxes (prepopulated from role; user can edit freely)
    if (DATA.permissions.length > 0) {
      html += `<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">`;
      html += `<span style="font-size:12px;color:#444;white-space:nowrap;font-weight:600;">Permissions:</span>`;
      DATA.permissions.forEach(p => {
        const chk = s.permission_ids && s.permission_ids.includes(p.id) ? ' checked' : '';
        html += `<label style="font-size:12px;display:inline-flex;align-items:center;gap:3px;white-space:nowrap;">`;
        html += `<input type="checkbox" class="at-perm-${c.id}" data-pid="${p.id}"${chk} onchange="atSetPerms(${c.id})"> ${esc(p.name)}`;
        html += `</label>`;
      });
      html += `</div>`;
    }

    html += `</div>`;

    if (hasKids) {
      html += `<div class="ftree-children" id="at-children-${c.id}">`;
      children.forEach(ch => { html += nodeHtml(ch, depth + 1); });
      html += `</div>`;
    }
    html += `</div>`;
    return html;
  }

  container.innerHTML = `<div class="at-tree">${roots.map(r => nodeHtml(r, 0)).join('')}</div>`;
}

// ---------------------------------------------------------------------------
// USERS
// ---------------------------------------------------------------------------
async function renderUsers() {
  renderAccessTree(null);

  const tb = document.getElementById('userTable');
  tb.innerHTML = DATA.users.length === 0
    ? '<tr><td class="empty" colspan="8">No users yet.</td></tr>'
    : DATA.users.map(u => {
        const adminBadge = u.is_superadmin
          ? '<span class="tag tag-superadmin">superadmin</span>'
          : u.is_admin
            ? '<span class="tag tag-admin">admin</span>'
            : '';
        // Per-company assignment display
        const companyHtml = (u.company_assignments || []).map(a => {
          const roleName = a.role_id ? (DATA.roles.find(r => r.id === a.role_id)?.name || '') : '';
          const permTags = (a.permission_ids || []).map(id => { const p = DATA.permissions.find(x=>x.id===id); return p ? `<span class="tag" style="font-size:11px;">${esc(p.name)}</span>` : ''; }).join('');
          let cell = `<div style="margin-bottom:2px;"><strong style="font-size:12px;">${esc(a.company_name)}</strong>`;
          if (roleName) cell += ` <span class="tag" style="font-size:11px;background:#e8eaf6;color:#283593;">${esc(roleName)}</span>`;
          if (permTags) cell += ` ${permTags}`;
          cell += `</div>`;
          return cell;
        }).join('') || '—';
        const blockedTags = (u.blocked_company_names || []).map(name => `<span class="tag" style="background:#fee;color:#c33;">${esc(name)}</span>`).join(' ');
        return `<tr>
          <td>${esc(u.name) || '—'}</td>
          <td>${esc(u.username) || '—'} ${adminBadge}</td>
          <td>${companyHtml}</td>
          <td>${blockedTags || '—'}</td>
          <td>${esc(u.notes) || '—'}</td>
          <td style="white-space:nowrap;">
            <button class="btn btn-edit" onclick="openEditUser(${u.id})" style="margin-right:4px;">Edit</button>
            <button class="btn btn-danger" onclick="delUser(${u.id})">Delete</button>
          </td>
        </tr>`;
      }).join('');
}


// Open the Add User form in "edit" mode pre-populated with an existing user's data
function openEditUser(userId) {
  const u = DATA.users.find(x => x.id === userId);
  if (!u) return;

  EDIT_USER_ID = userId;

  // Pre-fill scalar fields
  document.getElementById('u-username').value    = u.username    || '';
  document.getElementById('u-name').value        = u.name        || '';
  document.getElementById('u-email').value       = '';            // not stored locally
  document.getElementById('u-cognito-sub').value = u.cognito_sub || '';
  document.getElementById('u-notes').value       = u.notes       || '';
  document.getElementById('u-is-admin').checked     = !!u.is_admin;
  document.getElementById('u-is-superadmin').checked = !!u.is_superadmin;

  // Rebuild the access tree pre-populated with this user's assignments
  renderAccessTree(u);

  // Update form title + button labels
  document.getElementById('addUserTitle').textContent   = `Edit User: ${u.name || u.username}`;
  document.getElementById('addUserBtn').textContent     = 'Save Changes';
  document.getElementById('cancelEditBtn').style.display = '';

  // Scroll the panel to the top so the form is visible
  const panel = document.getElementById('panel-users');
  panel.scrollTo({ top: 0, behavior: 'smooth' });
  document.getElementById('addUserCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Cancel editing — reset the form to "Add User" mode
function cancelEditUser() {
  EDIT_USER_ID = null;
  ['u-username','u-name','u-email','u-cognito-sub','u-notes'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('u-is-admin').checked     = false;
  document.getElementById('u-is-superadmin').checked = false;
  document.getElementById('addUserTitle').textContent   = 'Add User';
  document.getElementById('addUserBtn').textContent     = 'Add User';
  document.getElementById('cancelEditBtn').style.display = 'none';
  renderAccessTree(null);
}

async function addUser() {
  clearErr('u-error');
  // Build per-company assignments from AT_STATE
  const company_assignments = Object.keys(AT_STATE)
    .filter(id => AT_STATE[+id] && AT_STATE[+id].allowed)
    .map(id => {
      const s = AT_STATE[+id];
      return {
        company_id:     +id,
        role_id:        s.role_id || null,
        permission_ids: s.permission_ids || [],
      };
    });
  const blockedIds = Object.keys(AT_STATE).filter(id => AT_STATE[+id] && AT_STATE[+id].blocked).map(Number);

  if (company_assignments.length === 0) { showErr('u-error', 'Mark at least one company as ✅ Allowed'); return; }
  const username = document.getElementById('u-username').value.trim();
  if (!username) { showErr('u-error', 'Username is required'); return; }
  const cognitoSub = document.getElementById('u-cognito-sub').value.trim();
  if (!cognitoSub) { showErr('u-error', 'Cognito sub UUID is required'); return; }
  const payload = {
    cognito_sub:         cognitoSub,
    username,
    name:                document.getElementById('u-name').value.trim()  || null,
    email:               document.getElementById('u-email').value.trim() || null,
    company_assignments,
    blocked_company_ids: blockedIds,
    notes:               document.getElementById('u-notes').value.trim() || null,
    is_admin:            document.getElementById('u-is-admin').checked,
    is_superadmin:       document.getElementById('u-is-superadmin').checked,
  };
  try {
    if (EDIT_USER_ID !== null) {
      await api('PUT', '/api/users/' + EDIT_USER_ID, payload);
    } else {
      await api('POST', '/api/users', payload);
    }
    // Reset form to add mode
    EDIT_USER_ID = null;
    ['u-username', 'u-name', 'u-email', 'u-cognito-sub', 'u-notes'].forEach(id => { document.getElementById(id).value = ''; });
    document.getElementById('u-is-admin').checked     = false;
    document.getElementById('u-is-superadmin').checked = false;
    document.getElementById('addUserTitle').textContent   = 'Add User';
    document.getElementById('addUserBtn').textContent     = 'Add User';
    document.getElementById('cancelEditBtn').style.display = 'none';
    await refreshPanel('users');   // re-renders tree (resets AT_STATE)
  } catch(e) { showErr('u-error', e.message); }
}

async function delUser(id) {
  if (!confirm('Delete this user?')) return;
  await api('DELETE','/api/users/'+id);
  await refreshPanel('users');
}

// ---------------------------------------------------------------------------
// Try Access panel
// ---------------------------------------------------------------------------
function renderAccessCheck() {
  // Populate user dropdown
  const uSel = document.getElementById('ac-user');
  const prevUser = uSel.value;
  uSel.innerHTML = '<option value="">— select user —</option>' +
    DATA.users.map(u => {
      const label = u.name ? `${esc(u.name)} (${esc(u.username)})` : esc(u.username);
      return `<option value="${esc(u.username)}"${u.username===prevUser?' selected':''}>${label}</option>`;
    }).join('');

  // Populate company dropdown — show breadcrumb path
  const cSel = document.getElementById('ac-company');
  const prevComp = cSel.value;

  // Build breadcrumb for every company
  function breadcrumb(cid) {
    const parts = [];
    let cur = DATA.companies.find(x => x.id === cid);
    while (cur) {
      parts.unshift(cur.name);
      cur = cur.parent_id ? DATA.companies.find(x => x.id === cur.parent_id) : null;
    }
    return parts.join(' › ');
  }

  cSel.innerHTML = '<option value="">— select company —</option>' +
    DATA.companies
      .slice()
      .sort((a, b) => breadcrumb(a.id).localeCompare(breadcrumb(b.id)))
      .map(c => {
        const label = breadcrumb(c.id);
        return `<option value="${esc(c.name)}"${c.name===prevComp?' selected':''}>${esc(label)}</option>`;
      }).join('');

  // Hide any stale result
  document.getElementById('ac-result-card').style.display = 'none';
}

async function runAccessCheck() {
  clearErr('ac-error');
  const username  = document.getElementById('ac-user').value;
  const compName  = document.getElementById('ac-company').value;
  const operation = document.getElementById('ac-operation').value;
  if (!username)  { showErr('ac-error', 'Please select a user');    return; }
  if (!compName)  { showErr('ac-error', 'Please select a company'); return; }

  let result;
  try {
    result = await api('POST', '/api/access-check', { username, company_name: compName, operation });
  } catch(e) { showErr('ac-error', e.message); return; }

  const card = document.getElementById('ac-result-card');
  const body = document.getElementById('ac-result-body');
  card.style.display = '';

  const opLabels = { get:'Get', update:'Update', create:'Create', delete:'Delete' };
  const permTag  = p => `<span class="tag" style="background:#e8f5e9;color:#2e7d32;font-size:12px;">${esc(p)}</span>`;
  const grantedPerms = (result.user_permissions || []).map(permTag).join(' ') || '<em style="color:#999;">none</em>';

  if (result.allowed) {
    body.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <span style="font-size:36px;">✅</span>
        <div>
          <div style="font-size:18px;font-weight:700;color:#2e7d32;">Access Allowed</div>
          <div style="font-size:13px;color:#555;margin-top:2px;">${esc(result.reason)}</div>
        </div>
      </div>
      <table style="font-size:13px;border-collapse:collapse;width:100%;">
        <tr><td style="padding:4px 8px;color:#777;width:140px;">User</td><td style="padding:4px 8px;"><strong>${esc(result.user)}</strong></td></tr>
        <tr><td style="padding:4px 8px;color:#777;">Company</td><td style="padding:4px 8px;"><strong>${esc(result.company)}</strong></td></tr>
        ${result.covering_company !== result.company ? `<tr><td style="padding:4px 8px;color:#777;">Assigned via</td><td style="padding:4px 8px;">${esc(result.covering_company)}</td></tr>` : ''}
        <tr><td style="padding:4px 8px;color:#777;">Operation</td><td style="padding:4px 8px;">${esc(opLabels[result.operation] || result.operation)}</td></tr>
        <tr><td style="padding:4px 8px;color:#777;">Required perm.</td><td style="padding:4px 8px;">${permTag(result.required_permission)}</td></tr>
        <tr><td style="padding:4px 8px;color:#777;">User permissions</td><td style="padding:4px 8px;">${grantedPerms}</td></tr>
      </table>`;
  } else {
    body.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <span style="font-size:36px;">❌</span>
        <div>
          <div style="font-size:18px;font-weight:700;color:#c62828;">Access Denied</div>
          <div style="font-size:13px;color:#555;margin-top:2px;">${esc(result.reason)}</div>
        </div>
      </div>
      <table style="font-size:13px;border-collapse:collapse;width:100%;">
        <tr><td style="padding:4px 8px;color:#777;width:140px;">User</td><td style="padding:4px 8px;"><strong>${esc(result.user)}</strong></td></tr>
        <tr><td style="padding:4px 8px;color:#777;">Company</td><td style="padding:4px 8px;"><strong>${esc(result.company)}</strong></td></tr>
        ${result.covering_company ? `<tr><td style="padding:4px 8px;color:#777;">Assigned via</td><td style="padding:4px 8px;">${esc(result.covering_company)}</td></tr>` : ''}
        <tr><td style="padding:4px 8px;color:#777;">Operation</td><td style="padding:4px 8px;">${esc(opLabels[result.operation] || result.operation)}</td></tr>
        <tr><td style="padding:4px 8px;color:#777;">Required perm.</td><td style="padding:4px 8px;">${permTag(result.required_permission)}</td></tr>
        <tr><td style="padding:4px 8px;color:#777;">User permissions</td><td style="padding:4px 8px;">${grantedPerms}</td></tr>
      </table>`;
  }
}

// ---------------------------------------------------------------------------
// Boot — check for token, then load
// ---------------------------------------------------------------------------
if (!getToken()) {
  showTokenOverlay();
} else {
  renderMe();
  refreshPanel('users');
}
</script>
</body>
</html>"""
