# -*- coding: utf-8 -*-
"""
BalkanHDplus — Trial & Paid Admin (Standalone v7.2.0)
- Settings page: paste JSON to update config.json (live reload; PORT needs restart)
- Safe JS (no leaked script outside strings)
- Working WU/Crypto "Generiši" with copy-ready text
- Trials/Clients dashboards with search + CSV export
- CSV exports use csv.writer (no quoting bugs)
- Hardened panel user-id extraction & form defaults
"""

import os, time, json, re, secrets, string, requests, sqlite3, io, csv
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

APP_DIR  = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(APP_DIR, "config.json")
DB_PATH  = os.path.join(APP_DIR, "admin.db")

# ---------------- Config ----------------
def load_cfg() -> dict:
    defaults = {
        "PORT": 8088,
        "BRAND": "BalkanHDplus",
        "ADMIN_TOKEN": "ADMIN",
        "PANEL_BASE": "",
        "PANEL_USER": "",
        "PANEL_PASS": "",
        "PANEL_PIN": "",
        "PANEL_MEMBER_ID": "",
        "PANEL_TIMEZONE": "Europe/Vienna",
        "BOUQUETS": [],
        "PKG_TRIAL": "2",
        "PKG_1M_TEST": "3",
        "PKG_1M": "3",
        "PKG_12M": "7",
        "PRICE_1M_TEST": 6,
        "PRICE_1M": 10,
        "PRICE_12M": 100,
        "TUTORIALS_URL": "https://www.balkanhdplus.com/rs/tutoriali",
        "WU_DEFAULT_COUNTRY": "Macedonia",
        "BANK_NAME": "BalkanHDplus",
        "BANK_IBAN": "LT893250046691800418",
        "STREAM_HOST": "http://balkanhdplus1.com:8080",
        "TRIAL_HOURS": 48
    }
    if not os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "w", encoding="utf-8") as f:
                json.dump(defaults, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return dict(defaults)
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        merged = dict(defaults); merged.update(loaded or {})
        return merged
    except Exception:
        return dict(defaults)

def _normalize_panel_base(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip()
    return s if s.endswith("/") else (s + "/")

CFG = load_cfg()

# ---- globals bound from CFG (reloaded live) ----
BRAND          = CFG.get('BRAND', 'BalkanHDplus')
ADMIN_TOKEN    = str(CFG.get('ADMIN_TOKEN', 'ADMIN'))
PANEL_BASE     = _normalize_panel_base(CFG.get('PANEL_BASE', ''))
PANEL_USER     = CFG.get('PANEL_USER', '')
PANEL_PASS     = CFG.get('PANEL_PASS', '')
PANEL_PIN      = CFG.get('PANEL_PIN', '')
PANEL_MEMBER_ID= CFG.get('PANEL_MEMBER_ID', '')
PANEL_TIMEZONE = CFG.get('PANEL_TIMEZONE', 'Europe/Vienna')
BOUQUETS       = CFG.get('BOUQUETS', [])

PKG_TRIAL    = str(CFG.get('PKG_TRIAL', '2'))
PKG_1M_TEST  = str(CFG.get('PKG_1M_TEST', CFG.get('PKG_1M', '3')))
PKG_1M       = str(CFG.get('PKG_1M', '3'))
PKG_12M      = str(CFG.get('PKG_12M', '7'))

PRICE_1M_TEST = float(CFG.get('PRICE_1M_TEST', 6))
PRICE_1M      = float(CFG.get('PRICE_1M', 10))
PRICE_12M     = float(CFG.get('PRICE_12M', 100))

TUTORIALS_URL      = CFG.get('TUTORIALS_URL', "https://www.balkanhdplus.com/rs/tutoriali")
STREAM_HOST        = CFG.get('STREAM_HOST', "http://balkanhdplus1.com:8080")
TRIAL_HOURS        = int(CFG.get('TRIAL_HOURS', 48))
WU_DEFAULT_COUNTRY = CFG.get("WU_DEFAULT_COUNTRY", "Macedonia")
BANK_NAME          = CFG.get("BANK_NAME", "BalkanHDplus")
BANK_IBAN          = CFG.get("BANK_IBAN", "LT893250046691800418")
PORT               = int(CFG.get('PORT', 8088))

def _apply_cfg_to_globals(cfg: dict):
    global BRAND, ADMIN_TOKEN, PANEL_BASE, PANEL_USER, PANEL_PASS, PANEL_PIN, PANEL_MEMBER_ID
    global PANEL_TIMEZONE, BOUQUETS, PKG_TRIAL, PKG_1M_TEST, PKG_1M, PKG_12M
    global PRICE_1M_TEST, PRICE_1M, PRICE_12M
    global TUTORIALS_URL, STREAM_HOST, TRIAL_HOURS, WU_DEFAULT_COUNTRY, BANK_NAME, BANK_IBAN

    BRAND           = cfg.get('BRAND', BRAND)
    ADMIN_TOKEN     = str(cfg.get('ADMIN_TOKEN', ADMIN_TOKEN))
    PANEL_BASE      = _normalize_panel_base(cfg.get('PANEL_BASE', PANEL_BASE))
    PANEL_USER      = cfg.get('PANEL_USER', PANEL_USER)
    PANEL_PASS      = cfg.get('PANEL_PASS', PANEL_PASS)
    PANEL_PIN       = cfg.get('PANEL_PIN', PANEL_PIN)
    PANEL_MEMBER_ID = cfg.get('PANEL_MEMBER_ID', PANEL_MEMBER_ID)
    PANEL_TIMEZONE  = cfg.get('PANEL_TIMEZONE', PANEL_TIMEZONE)
    BOUQUETS        = cfg.get('BOUQUETS', BOUQUETS) or []
    PKG_TRIAL       = str(cfg.get('PKG_TRIAL', PKG_TRIAL))
    PKG_1M_TEST     = str(cfg.get('PKG_1M_TEST', PKG_1M_TEST))
    PKG_1M          = str(cfg.get('PKG_1M', PKG_1M))
    PKG_12M         = str(cfg.get('PKG_12M', PKG_12M))
    PRICE_1M_TEST   = float(cfg.get('PRICE_1M_TEST', PRICE_1M_TEST))
    PRICE_1M        = float(cfg.get('PRICE_1M', PRICE_1M))
    PRICE_12M       = float(cfg.get('PRICE_12M', PRICE_12M))
    TUTORIALS_URL   = cfg.get('TUTORIALS_URL', TUTORIALS_URL)
    STREAM_HOST     = cfg.get('STREAM_HOST', STREAM_HOST)
    TRIAL_HOURS     = int(cfg.get('TRIAL_HOURS', TRIAL_HOURS))
    WU_DEFAULT_COUNTRY = cfg.get('WU_DEFAULT_COUNTRY', WU_DEFAULT_COUNTRY)
    BANK_NAME       = cfg.get('BANK_NAME', BANK_NAME)
    BANK_IBAN       = cfg.get('BANK_IBAN', BANK_IBAN)

def _validate_cfg_payload(data: dict) -> tuple[bool, str]:
    # Block obvious issues that cause "missing user id" later
    if not data.get("PANEL_BASE"):
        return False, "PANEL_BASE is required"
    if not data.get("PANEL_USER"):
        return False, "PANEL_USER is required"
    if not data.get("PANEL_PASS"):
        return False, "PANEL_PASS is required"
    if not data.get("PANEL_MEMBER_ID"):
        return False, "PANEL_MEMBER_ID is required"
    if "BOUQUETS" in data and not isinstance(data["BOUQUETS"], list):
        return False, "BOUQUETS must be a list of IDs"
    return True, "ok"

# ---------------- DB ----------------
def db_init():
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trials (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      country TEXT,
      name TEXT,
      phone TEXT,
      username TEXT,
      password TEXT,
      m3u TEXT,
      expires_at INTEGER,
      notes TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      plan TEXT,
      price REAL,
      country TEXT,
      name TEXT,
      phone TEXT,
      username TEXT,
      password TEXT,
      m3u TEXT,
      expires_at INTEGER,
      notes TEXT
    )""")
    con.commit(); con.close()

def db_exec(sql, params=()):
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    cur = con.cursor(); cur.execute(sql, params); con.commit()
    lid = cur.lastrowid; con.close(); return lid

def db_all(sql, params=()):
    con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
    cur = con.cursor(); cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    con.close(); return rows

db_init()

# ---------------- UI helpers ----------------
def _css() -> str:
    return """
    <style>
      :root { --bg:#0f1115; --panel:#111827; --card:#0b1220; --muted:#9aa6b2; --text:#e6e9ef; --accent:#e30613; --border:#1f2937; }
      *{ box-sizing:border-box; } body{ margin:0; font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); }
      a{ color:var(--text); text-decoration:none; } .wrap{ max-width:1100px; margin:24px auto; padding:0 16px; }
      .topbar{ background:var(--panel); border-bottom:1px solid var(--border); }
      .topbar .inner{ max-width:1100px; margin:0 auto; padding:12px 16px; display:flex; align-items:center; gap:12px; justify-content:space-between; }
      .brand{ font-weight:800; letter-spacing:.2px; }
      .navlinks a{ padding:8px 12px; border:1px solid var(--border); border-radius:10px; color:#cbd5e1; }
      .grid{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:16px; }
      .card{ background:var(--card); border:1px solid var(--border); border-radius:16px; padding:18px; box-shadow:0 6px 18px rgba(0,0,0,.25); }
      h1,h2,h3{ margin:8px 0 12px; } .muted{ color:var(--muted); }
      .row{ display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end; } .col{ flex:1 1 260px; min-width:240px; }
      label{ display:block; font-size:12px; color:#9aa6b2; margin-bottom:6px;} .input{ width:100%; background:#0f1117; border:1px solid #1f2433; color:#e6e9ef; padding:10px 12px; border-radius:12px; outline:none; }
      select.input{ appearance:none; } .btn{ background:var(--accent); color:#fff; border:none; padding:10px 16px; border-radius:12px; cursor:pointer; font-weight:700; }
      .btn.ghost{ background:transparent; border:1px solid var(--border); color:#e6e9ef; } .msg{ background:#0f1117; border:1px dashed #2a3142; border-radius:12px; padding:12px; margin:12px 0; }
      textarea.input{ height:220px; white-space:pre; } .error{ background:#2a1111; border:1px solid #512222; color:#ffb4b4; padding:12px; border-radius:12px; }
      @media (max-width:780px){ .grid{ grid-template-columns:1fr; } }
    </style>
    """

def topbar(active: str="") -> str:
    return f"""
    <div class="topbar"><div class="inner">
      <div class="brand">{BRAND} • Admin</div>
      <div class="navlinks">
        <a href="/" {'style="background:#0e1625"' if active=='home' else ''}>Dashboard</a>
        <a href="/manual-trial" {'style="background:#0e1625"' if active=='trial' else ''}>Kreiraj Test</a>
        <a href="/manual-paid" {'style="background:#0e1625"' if active=='paid' else ''}>Kreiraj Plaćeni</a>
        <a href="/payments" {'style="background:#0e1625"' if active=='payments' else ''}>Uplate</a>
        <a href="/trials" {'style="background:#0e1625"' if active=='trials' else ''}>Lista Testova</a>
        <a href="/clients" {'style="background:#0e1625"' if active=='clients' else ''}>Plaćeni Kupci</a>
        <a href="/settings" {'style="background:#0e1625"' if active=='settings' else ''}>Settings</a>
      </div>
    </div></div>
    """

def rand(n=10) -> str:
    import random
    return "".join(random.choice(string.ascii_letters+string.digits) for _ in range(n))

def _normalize_cc(s: Optional[str]) -> Optional[str]:
    if not s: return None
    t = (s or "").strip().upper()
    if len(t)==2 and t.isalpha(): return t
    MAP = { "DEUTSCHLAND":"DE","GERMANY":"DE","ÖSTERREICH":"AT","AUSTRIA":"AT","SCHWEIZ":"CH","SWITZERLAND":"CH" }
    return MAP.get(t)

def _m3u(username: str, password: str) -> str:
    base = urlparse(STREAM_HOST)
    host = base.hostname or "balkanhdplus1.com"
    scheme = base.scheme or "http"
    return f"{scheme}://{host}:8080/get.php?username={username}&password={password}&type=m3u_plus&output=mpegts"

def _fmt_local_ts(ts: int) -> str:
    tz_name = PANEL_TIMEZONE or "Europe/Vienna"
    try:
        dt = datetime.fromtimestamp(ts, ZoneInfo(tz_name))
    except Exception:
        dt = datetime.fromtimestamp(ts)
    return dt.strftime("%d.%m.%Y %H:%M")

def _plan_catalog() -> dict:
    return {
        "1m_test": {"package": PKG_1M_TEST, "days": 30, "price": PRICE_1M_TEST, "label": "1 mesec TEST (€6)"},
        "1m": {"package": PKG_1M, "days": 30, "price": PRICE_1M, "label": "1 mesec Regular (€10)"},
        "12m": {"package": PKG_12M, "days": 365, "price": PRICE_12M, "label": "12 meseci (€100)"},
    }

# ---------------- Panel client ----------------
class Panel:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0"})
        self.logged = False
        self.debug_dump = True

    def _base_norm(self) -> str:
        b = self.cfg.get("PANEL_BASE", PANEL_BASE)
        return b if b.endswith("/") else b + "/"

    def login(self) -> bool:
        if self.logged: return True
        try:
            self.s.get(urljoin(self._base_norm(), 'login.php'), timeout=30)
        except Exception:
            pass
        r = self.s.post(urljoin(self._base_norm(), 'login.php'),
                        data={'username': self.cfg.get("PANEL_USER", PANEL_USER),
                              'password': self.cfg.get("PANEL_PASS", PANEL_PASS)},
                        allow_redirects=True, timeout=45)
        ok = (r.status_code in (200, 302)) and not any(x in (r.text or '').lower() for x in ('invalid','error','failed'))
        if ok:
            self.logged = True
            return True
        raise RuntimeError("panel_login_failed")

    def _ensure(self) -> bool:
        try:
            r = self.s.get(urljoin(self._base_norm(), 'reseller.php'), timeout=25, allow_redirects=False)
            if r.status_code in (301,302) or 'login' in (r.headers.get('Location','') or '').lower():
                return self.login()
            return True
        except Exception:
            return self.login()

    def _extract_uid_any(self, r) -> Optional[str]:
        # Check redirect chain locations first
        chain = [r] + list(getattr(r, 'history', []))
        for resp in chain:
            loc = resp.headers.get('Location') or resp.headers.get('location') or ''
            m = re.search(r'[\?&](?:id|user_id|uid)=(\d+)', loc, re.I)
            if m: return m.group(1)
        # Fallback: search in HTML
        txt = (r.text or '')
        m = re.search(r'user_reseller\.php\?(?:[^"\']*?)(?:id|user_id|uid)=(\d+)', txt, re.I)
        if m: return m.group(1)
        m = re.search(r'[\?&](?:id|user_id|uid)=(\d+)', txt, re.I)
        return m.group(1) if m else None

    def _parse_creds_from_edit_html(self, html_text: str) -> Optional[Dict[str,str]]:
        soup = BeautifulSoup(html_text, 'lxml')
        u=''; p=''
        for u_name in ('username','user','line_username','user_name'):
            el = soup.find('input', attrs={'name': u_name})
            if el and el.get('value'): u = el.get('value'); break
        for p_name in ('password','pass','line_password','pass_word'):
            el = soup.find('input', attrs={'name': p_name})
            if el and el.get('value'): p = el.get('value'); break
        if u and p: return {'username': u, 'password': p}
        m = re.search(r'get\.php\?[^\s\"\']*username=([^&\"\']+)&password=([^&\"\']+)', html_text, re.I)
        if m: return {'username': m.group(1), 'password': m.group(2)}
        return None

    def _fetch_create_form(self, trial: bool) -> Dict[str, Any]:
        url = urljoin(self._base_norm(), 'user_reseller.php?trial' if trial else 'user_reseller.php')
        r = self.s.get(url, timeout=30, allow_redirects=True)
        soup = BeautifulSoup(r.text or '', 'lxml')
        form = {}
        for inp in soup.find_all('input'):
            name = inp.get('name')
            if not name: continue
            t = (inp.get('type') or '').lower()
            if t in ('hidden','text','password','email','number','tel','checkbox','radio','submit'):
                val = inp.get('value') or ''
                if t in ('checkbox','radio'):
                    if inp.has_attr('checked'): form.setdefault(name, val if val!='' else 'on')
                    else: continue
                else:
                    form[name] = val
        for sel in soup.find_all('select'):
            name = sel.get('name')
            if not name: continue
            opt = sel.find('option', selected=True) or sel.find('option')
            if opt: form[name] = opt.get('value') or ''
        return form

    def _merge_form(self, base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base)
        for k,v in extra.items():
            if k == 'bouquet[]':
                existing = merged.get(k, [])
                if not isinstance(existing, list):
                    existing = [existing] if existing else []
                if isinstance(v, list): existing.extend(v)
                else: existing.append(v)
                merged[k] = [str(x) for x in existing]
            else:
                merged[k] = v
        return merged

    def _finish_and_fetch_creds(self, r) -> Dict[str, Any]:
        uid = self._extract_uid_any(r)
        if not uid:
            try:
                rr = self.s.get(urljoin(self._base_norm(), 'reseller.php'), timeout=25)
                uid = self._extract_uid_any(rr)
            except Exception:
                uid = None
        if not uid:
            if self.debug_dump:
                try: open('panel_debug_last.html','w',encoding='utf-8').write(r.text or '')
                except Exception: pass
            raise RuntimeError("missing user id after POST")
        r2 = self.s.get(urljoin(self._base_norm(), f'user_reseller.php?id={uid}'), timeout=30)
        creds = self._parse_creds_from_edit_html(r2.text)
        if not creds:
            if self.debug_dump:
                try: open('panel_debug_last_edit.html','w',encoding='utf-8').write(r2.text or '')
                except Exception: pass
            raise RuntimeError("parse_creds_failed")
        return {"user_id": uid, "username": creds['username'], "password": creds['password']}

    def common_form(self, forced_country: Optional[str], notes: str) -> Dict[str, Any]:
        # Prefer numeric member/owner if present; some panels require this
        owner_val = self.cfg.get("PANEL_MEMBER_ID", PANEL_MEMBER_ID) or self.cfg.get("PANEL_USER", PANEL_USER)
        form = {
            'user_timezone': self.cfg.get("PANEL_TIMEZONE", PANEL_TIMEZONE),
            'max_connections': '1',
            'reseller_notes': notes or '',
            'bouquets_selected': json.dumps(self.cfg.get("BOUQUETS", BOUQUETS) or []),
            'owner': owner_val,
            'twobro_pin': self.cfg.get("PANEL_PIN", PANEL_PIN),
            'member_id': self.cfg.get("PANEL_MEMBER_ID", PANEL_MEMBER_ID),
        }
        # Explicit bouquets list
        form['bouquet[]'] = [str(b) for b in (self.cfg.get("BOUQUETS", BOUQUETS) or [])]
        return form

    def create_trial(self, forced_country: Optional[str], notes: str) -> Dict[str, Any]:
        self._ensure()
        base = self._fetch_create_form(trial=True)
        extra = self.common_form(forced_country, notes)
        extra.update({'trial': '1', 'package': self.cfg.get("PKG_TRIAL", PKG_TRIAL), 'package_id': self.cfg.get("PKG_TRIAL", PKG_TRIAL)})
        form = self._merge_form(base, extra)
        form.setdefault('submit_user', 'Save')
        url = urljoin(self._base_norm(), 'user_reseller.php?trial')
        r = self.s.post(url, data=form, timeout=60, allow_redirects=True)
        return self._finish_and_fetch_creds(r)

    def create_paid(self, package_id: str, forced_country: Optional[str], notes: str) -> Dict[str, Any]:
        self._ensure()
        base = self._fetch_create_form(trial=False)
        extra = self.common_form(forced_country, notes)
        extra.update({'package': package_id, 'package_id': package_id})
        form = self._merge_form(base, extra)
        form.setdefault('submit_user', 'Save')
        url = urljoin(self._base_norm(), 'user_reseller.php')
        r = self.s.post(url, data=form, timeout=60, allow_redirects=True)
        return self._finish_and_fetch_creds(r)

panel = Panel(CFG)
app = FastAPI(title=f"{BRAND} Trial & Paid Admin (v7.2.0)")

# ---------------- auth ----------------
def admin_ok(req: Request) -> bool:
    return (req.cookies.get("admin_token") or req.query_params.get("token")) == ADMIN_TOKEN

def set_cookie(resp, name, value):
    resp.set_cookie(name, value, max_age=7*24*3600, httponly=False, samesite="lax")

# ---------------- pages ----------------
@app.get("/", response_class=HTMLResponse)
def root(req: Request):
    if not admin_ok(req):
        return HTMLResponse(f"""
        <!doctype html><meta charset="utf-8"><title>Login • {BRAND}</title>{_css()}
        <div class="topbar"><div class="inner"><div class="brand">{BRAND} • Admin</div></div></div>
        <div class="wrap"><div class="card">
            <h2>Admin Login</h2>
            <p class="muted">Unesi <strong>ADMIN_TOKEN</strong> za pristup.</p>
            <form method="post" action="/login" class="row">
              <div class="col"><label>Token</label><input class="input" name="token" placeholder="ADMIN_TOKEN"></div>
              <div class="col"><button class="btn">Prijava</button></div>
            </form>
        </div></div>
        """)
    return HTMLResponse(f"""
    <!doctype html><meta charset="utf-8"><title>Admin • {BRAND}</title>{_css()}
    {topbar("home")}
    <div class="wrap">
      <div class="grid">
        <div class="card">
          <h2>⚡ Ručno kreiranje testa</h2>
          <p class="muted">Kreiraj probni nalog i kopiraj poruku za WhatsApp.</p>
          <a class="btn" href="/manual-trial">Kreni</a>
        </div>
        <div class="card">
          <h2>💳 Kreiraj plaćeni nalog</h2>
          <p class="muted">Direktno aktiviraj 1/3/12 meseci i kopiraj poruku za klijenta.</p>
          <a class="btn" href="/manual-paid">Kreni</a>
        </div>
        <div class="card">
          <h2>💸 Uplate</h2>
          <p class="muted">Generiši tekst sa instrukcijama i kopiraj jednim klikom.</p>
          <a class="btn" href="/payments">Otvori</a>
        </div>
        <div class="card">
          <h2>⚙️ Settings</h2>
          <p class="muted">Ažuriraj config.json (PANEL, PIN, BOuquets...).</p>
          <a class="btn" href="/settings">Otvori</a>
        </div>
      </div>
    </div>
    """)

@app.post("/login")
def login(req: Request, token: str = Form(...)):
    if token != ADMIN_TOKEN: raise HTTPException(401, "Pogrešan token")
    resp = RedirectResponse("/", status_code=302); set_cookie(resp, "admin_token", ADMIN_TOKEN); return resp

# ---- JS snippets
SCRIPT_TRIAL = """
<script>
const el = (id)=>document.getElementById(id);
el('go').addEventListener('click', async () => {
  const fd = new URLSearchParams();
  const _c = el('country').value.trim();
  const _n = el('name').value.trim();
  const _p = el('phone').value.trim();
  fd.set('country', _c ? _c : 'AT');
  fd.set('name',    _n ? _n : '');
  fd.set('phone',   _p ? _p : '');
  const r = await fetch('/manual-trial/new', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: fd.toString() });
  const out = el('out'); out.style.display = 'block';
  const err = el('err');
  if (!r.ok) { err.style.display = 'block'; err.textContent = 'Greška: ' + await r.text(); return; } else { err.style.display='none'; err.textContent=''; }
  const j = await r.json();
  el('u').textContent = j.username;
  el('p').textContent = j.password;
  el('m').textContent = j.m3u; el('m').href = j.m3u;
  el('e').textContent = j.expires_at_human;
  el('msg').value = j.whatsapp_message;
});
function copyText(s){ navigator.clipboard.writeText(s).then(()=>{ alert('Kopirano!'); }); }
el('copyCreds').addEventListener('click', () => { copyText(el('u').textContent + ':' + el('p').textContent); });
el('copyAll').addEventListener('click', () => { copyText(el('msg').value); });
</script>
"""

SCRIPT_PAID = """
<script>
const ep = (id)=>document.getElementById(id);
ep('goPaid').addEventListener('click', async () => {
  const fd = new URLSearchParams();
  const _plan = ep('plan').value;
  const _c = ep('country').value.trim();
  const _n = ep('name').value.trim();
  const _p = ep('phone').value.trim();
  fd.set('plan',   _plan);
  fd.set('country', _c ? _c : 'AT');
  fd.set('name',    _n ? _n : '');
  fd.set('phone',   _p ? _p : '');
  const r = await fetch('/manual-paid/new', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: fd.toString() });
  const out = ep('out'); out.style.display = 'block';
  const err = ep('err');
  if (!r.ok) { err.style.display = 'block'; err.textContent = 'Greška: ' + await r.text(); return; } else { err.style.display='none'; err.textContent=''; }
  const j = await r.json();
  ep('plan_lbl').textContent = j.plan_human;
  ep('u').textContent = j.username;
  ep('p1').textContent = j.password;
  ep('m').textContent = j.m3u; ep('m').href = j.m3u;
  ep('e').textContent = j.expires_at_human;
  ep('msg').value = j.whatsapp_message;
});
function copyText(s){ navigator.clipboard.writeText(s).then(()=>{ alert('Kopirano!'); }); }
ep('copyCreds').addEventListener('click', () => { copyText(ep('u').textContent + ':' + ep('p1').textContent); });
ep('copyAll').addEventListener('click', () => { copyText(ep('msg').value); });
</script>
"""

def script_payments() -> str:
    plans = _plan_catalog()
    return f"""
<script>
(function(){{
  const PLAN_INFO = {json.dumps(plans)};
  const $ = (id)=>document.getElementById(id);

  function syncAmount(){{
    const plan = $('pay_plan')?.value;
    const info = PLAN_INFO[plan];
    if (!info) return;
    const amount = info.price.toFixed(0);
    const amountEl = $('pay_amount');
    if (amountEl) amountEl.value = amount;
  }}

  function syncMethodFields(){{
    const method = $('pay_method')?.value;
    const wuBox = $('wu_fields');
    const bankBox = $('bank_fields');
    if (wuBox) wuBox.style.display = method === 'wu' ? 'flex' : 'none';
    if (bankBox) bankBox.style.display = method === 'bank' ? 'block' : 'none';
  }}

  function planLabel(key){{
    return (PLAN_INFO[key] && PLAN_INFO[key].label) ? PLAN_INFO[key].label : key;
  }}

  document.addEventListener('DOMContentLoaded', () => {{
    $('pay_plan')?.addEventListener('change', syncAmount);
    $('pay_method')?.addEventListener('change', syncMethodFields);
    syncAmount();
    syncMethodFields();

    $('pay_go')?.addEventListener('click', () => {{
      const method = $('pay_method').value;
      const plan = $('pay_plan').value;
      const amount = ($('pay_amount').value || '').trim();
      let txt = '';

      if (method === 'wu') {{
        const receiver = ($('wu_name').value || '').trim();
        const country = ($('wu_country').value || '').trim() || {json.dumps(WU_DEFAULT_COUNTRY)};
        if (!receiver) {{ alert('Unesite ime primaoca.'); return; }}
        txt = `💸 Western Union podaci:
Vrsta linije: ${{planLabel(plan)}}
Iznos: €${{amount}}
Ime primaoca: ${{receiver}}
Država: ${{country}}

Nakon uplate pošaljite MTCN (10 cifara) i screenshot potvrde.
Kada proverimo uplatu, aktiviraćemo pretplatu i dobićete informacije.`;
      }} else if (method === 'bank') {{
        txt = `🏦 Bank transfer podaci:
Vrsta linije: ${{planLabel(plan)}}
Iznos: €${{amount}}
Name: {BANK_NAME}
IBAN: {BANK_IBAN}

Uplatu pošaljite kao fast transfer.
Nakon uplate pošaljite screenshot potvrde.
Kada proverimo uplatu, aktiviraćemo pretplatu i dobićete informacije.`;
      }} else if (method === 'psc') {{
        txt = `💳 Paysafecard uplata:
Vrsta linije: ${{planLabel(plan)}}
Iznos: €${{amount}}

Pošaljite paysafecard kod i screenshot potvrde.
Kada proverimo uplatu, aktiviraćemo pretplatu i dobićete informacije.`;
      }}

      $('pay_out').style.display = 'block';
      $('pay_msg').value = txt;
    }});

    $('pay_copy')?.addEventListener('click', () => {{
      navigator.clipboard.writeText($('pay_msg').value || '').then(() => alert('Kopirano!'));
    }});
  }});
}})();
</script>
"""


# ---------------- Trial UI ----------------
@app.get("/manual-trial", response_class=HTMLResponse)
def manual_trial_ui(req: Request):
    if not admin_ok(req): return RedirectResponse("/", status_code=302)
    return HTMLResponse(f"""
    <!doctype html><meta charset="utf-8"><title>Kreiraj Test • {BRAND}</title>{_css()}
    {topbar("trial")}
    <div class="wrap"><div class="card">
        <h2>⚡ Ručno kreiranje testa</h2>
        <p class="muted">Popuni polja i klikni „Kreiraj Test”.</p>
        <form id="f" onsubmit="return false;" class="row">
          <div class="col"><label>Država (npr. AT, DE, CH)</label><input class="input" id="country" value="AT"></div>
          <div class="col"><label>Ime i prezime (opciono)</label><input class="input" id="name" placeholder="Ime"></div>
          <div class="col"><label>Telefon</label><input class="input" id="phone" placeholder="+43..."></div>
          <div class="col"><button class="btn" id="go">Kreiraj Test</button></div>
        </form>
        <div id="out" style="margin-top:16px;display:none">
          <div class="msg">
            <div><strong>Korisničko ime:</strong> <span id="u"></span></div>
            <div><strong>Lozinka:</strong> <span id="p"></span></div>
            <div><strong>M3U:</strong> <a id="m" target="_blank"></a></div>
            <div><strong>Ističe:</strong> <span id="e"></span></div>
          </div>
          <div id="err" class="error" style="display:none"></div>
          <div class="row">
            <button class="btn ghost" id="copyCreds">Kopiraj (user:pass)</button>
            <button class="btn" id="copyAll">Kopiraj kompletnu poruku</button>
          </div>
          <textarea id="msg" class="input" style="margin-top:12px;"></textarea>
        </div>
    </div></div>
    {SCRIPT_TRIAL}
    """)

@app.post("/manual-trial/new")
def manual_trial_new(country: str = Form("AT"), name: str = Form(""), phone: str = Form("")):
    cc = _normalize_cc(country) or "AT"
    notes = f"TRIAL | name={name}; phone={phone}".strip()
    try:
        res = panel.create_trial(cc, notes)
    except Exception as e:
        raise HTTPException(502, f"Panel error: {e}")
    username, password = res["username"], res["password"]
    exp = int(time.time()) + TRIAL_HOURS * 3600
    exp_human = _fmt_local_ts(exp)

    m3u = _m3u(username, password)
    url8000 = "http://balkanhdplus1.com:8000"
    url8080 = "http://balkanhdplus1.com:8080"
    wa = (
        f"✅ Test aktiviran\n\n"
        f"• Username: {username}\n"
        f"• Password: {password}\n"
        f"• M3U: {m3u}\n"
        f"• URL (Smarters/TV): {url8000}\n"
        f"• URL: {url8080}\n\n"
        f"Uputstva: {TUTORIALS_URL}"
    )
    try:
        db_exec("""INSERT INTO trials(ts,country,name,phone,username,password,m3u,expires_at,notes)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (int(time.time()), cc, name, phone, username, password, m3u, exp, f"TRIAL | name={name}; phone={phone}"))
    except Exception:
        pass
    return {"username": username, "password": password, "m3u": m3u, "expires_at": exp, "expires_at_human": exp_human, "whatsapp_message": wa}

# ---------------- Paid UI ----------------
@app.get("/manual-paid", response_class=HTMLResponse)
def manual_paid_ui(req: Request):
    if not admin_ok(req): return RedirectResponse("/", status_code=302)
    return HTMLResponse(f"""
    <!doctype html><meta charset="utf-8"><title>Kreiraj Plaćeni • {BRAND}</title>{_css()}
    {topbar("paid")}
    <div class="wrap"><div class="card">
        <h2>💳 Kreiraj plaćeni nalog</h2>
        <p class="muted">Izaberi plan i popuni podatke. Nalog se odmah kreira na panelu.</p>
        <form id="p" onsubmit="return false;" class="row">
          <div class="col"><label>Plan</label>
            <select class="input" id="plan">
              <option value="1m_test">1 mesec - TEST MESEC (€{PRICE_1M_TEST:.0f})</option>
              <option value="1m">1 mesec - Regular (€{PRICE_1M:.0f})</option>
              <option value="12m">12 meseci (€{PRICE_12M:.0f})</option>
            </select>
          </div>
          <div class="col"><label>Država (npr. AT, DE, CH)</label><input class="input" id="country" value="AT"></div>
          <div class="col"><label>Ime i prezime</label><input class="input" id="name" placeholder="Ime"></div>
          <div class="col"><label>Telefon</label><input class="input" id="phone" placeholder="+43..."></div>
          <div class="col"><button class="btn" id="goPaid">Kreiraj plaćeni</button></div>
        </form>
        <div id="out" style="margin-top:16px;display:none">
          <div class="msg">
            <div><strong>Plan:</strong> <span id="plan_lbl"></span></div>
            <div><strong>Korisničko ime:</strong> <span id="u"></span></div>
            <div><strong>Lozinka:</strong> <span id="p1"></span></div>
            <div><strong>M3U:</strong> <a id="m" target="_blank"></a></div>
            <div><strong>Ističe:</strong> <span id="e"></span></div>
          </div>
          <div id="err" class="error" style="display:none"></div>
          <div class="row">
            <button class="btn ghost" id="copyCreds">Kopiraj (user:pass)</button>
            <button class="btn" id="copyAll">Kopiraj kompletnu poruku</button>
          </div>
          <textarea id="msg" class="input" style="margin-top:12px;"></textarea>
        </div>
    </div></div>
    {SCRIPT_PAID}
    """)

@app.post("/manual-paid/new")
def manual_paid_new(plan: str = Form("1m"), country: str = Form("AT"), name: str = Form(""), phone: str = Form("")):
    plans = _plan_catalog()
    if plan not in plans:
        raise HTTPException(400, "Pogrešan plan")

    meta = plans[plan]
    cc = _normalize_cc(country) or "AT"
    notes = f"PAID_MANUAL | plan={plan}; name={name}; phone={phone}".strip()
    try:
        res = panel.create_paid(meta["package"], cc, notes)
    except Exception as e:
        raise HTTPException(502, f"Panel error: {e}")

    username, password = res["username"], res["password"]
    days = int(meta["days"])
    exp = int(time.time()) + days * 86400
    exp_human = _fmt_local_ts(exp)

    m3u = _m3u(username, password)
    url8000 = "http://balkanhdplus1.com:8000"
    url8080 = "http://balkanhdplus1.com:8080"
    price = float(meta["price"])
    plan_human = meta["label"]

    msg = (
        f"✅ Pretplata aktivirana\n\n"
        f"• Plan: {plan_human}\n"
        f"• Username: {username}\n"
        f"• Password: {password}\n"
        f"• M3U: {m3u}\n"
        f"• URL (Smarters/TV): {url8000}\n"
        f"• URL: {url8080}\n\n"
        f"Važi do: {exp_human}\n"
        f"Uputstva: {TUTORIALS_URL}"
    )
    try:
        db_exec("""INSERT INTO clients(ts,plan,price,country,name,phone,username,password,m3u,expires_at,notes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (int(time.time()), plan, float(price), cc, name, phone, username, password, m3u, exp, f"PAID | plan={plan}; name={name}; phone={phone}"))
    except Exception:
        pass
    return { "plan": plan, "plan_human": plan_human, "price": price,
             "username": username, "password": password, "m3u": m3u,
             "expires_at": exp, "expires_at_human": exp_human,
             "whatsapp_message": msg }

# ---------------- Payments (WU/Crypto) ----------------
@app.get("/payments", response_class=HTMLResponse)
def payments_ui(req: Request):
    if not admin_ok(req): return RedirectResponse("/", status_code=302)
    return HTMLResponse(f"""
    <!doctype html><meta charset="utf-8"><title>Uplate • {BRAND}</title>{_css()}
    {topbar("payments")}
    <div class="wrap">
      <div class="card">
        <h2>💳 Uplate</h2>
        <p class="muted">Sve je sada na jednom mestu: prvo izaberi vrstu linije, zatim način plaćanja, unesi potrebne podatke i generiši gotov tekst za klijenta.</p>

        <form id="pay" onsubmit="return false;" class="row">
          <div class="col">
            <label>Vrsta linije</label>
            <select id="pay_plan" class="input">
              <option value="1m_test">1 mesec - TEST MESEC (€{PRICE_1M_TEST:.0f})</option>
              <option value="1m">1 mesec - Regular (€{PRICE_1M:.0f})</option>
              <option value="12m">12 meseci (€{PRICE_12M:.0f})</option>
            </select>
          </div>

          <div class="col">
            <label>Način plaćanja</label>
            <select id="pay_method" class="input">
              <option value="wu">Western Union</option>
              <option value="bank">Bank transfer</option>
              <option value="psc">Paysafecard</option>
            </select>
          </div>

          <div class="col">
            <label>Iznos (€)</label>
            <input id="pay_amount" class="input">
          </div>
        </form>

        <div id="wu_fields" class="row" style="margin-top:12px;">
          <div class="col">
            <label>Ime primaoca</label>
            <input id="wu_name" class="input" placeholder="npr. Hristijan Vlaoski">
          </div>
          <div class="col">
            <label>Država</label>
            <input id="wu_country" class="input" value="{WU_DEFAULT_COUNTRY}">
          </div>
        </div>

        <div id="bank_fields" style="display:none; margin-top:12px;">
          <div class="msg"><strong>Name:</strong> {BANK_NAME}<br><strong>IBAN:</strong> {BANK_IBAN}</div>
        </div>

        <div class="row" style="margin-top:12px;">
          <button class="btn" id="pay_go">Generiši tekst</button>
          <button class="btn ghost" id="pay_copy" type="button">Kopiraj tekst</button>
        </div>

        <div id="pay_out" style="display:none; margin-top:12px;">
          <textarea id="pay_msg" class="input" style="height:220px;"></textarea>
        </div>
      </div>
    </div>
    """ + script_payments())

# ---------------- Trials/Clients dashboards + CSV ----------------
@app.get('/trials', response_class=HTMLResponse)
def list_trials(req: Request, q: str = '', limit: int = 500):
    if not admin_ok(req): return RedirectResponse('/', status_code=302)
    sql = "SELECT id,ts,country,name,phone,username,password,m3u,expires_at,notes FROM trials"
    params=[]
    if q:
        sql += " WHERE (COALESCE(country,'')||' '||COALESCE(name,'')||' '||COALESCE(phone,'')||' '||COALESCE(username,'')) LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id DESC LIMIT ?"; params.append(int(limit))
    rows = db_all(sql, params)
    def fmt_ts(x): return time.strftime('%d.%m.%Y %H:%M', time.localtime(x)) if x else ''
    trs=''.join([f"<tr><td>{r['id']}</td><td>{fmt_ts(r['ts'])}</td><td>{r.get('country','')}</td><td>{r.get('name','')}</td><td>{r.get('phone','')}</td><td>{r['username']}</td><td>{r['password']}</td><td><a href='{r['m3u']}' target='_blank'>m3u</a></td><td>{fmt_ts(r['expires_at'])}</td><td><span class='muted'>{r.get('notes','')}</span></td></tr>" for r in rows]) or "<tr><td colspan=10 class='muted'>Nema zapisa</td></tr>"
    html=f"""
    <!doctype html><meta charset='utf-8'><title>Lista Testova • {BRAND}</title>{_css()}
    {topbar('trials')}
    <div class='wrap'>
      <div class='card'>
        <h2>Lista Testova</h2>
        <form class='row' method='get'>
          <div class='col'><label>Pretraga</label><input class='input' name='q' value='{q}' placeholder='ime / telefon / username / država'></div>
          <div class='col'><label>Limit</label><input class='input' name='limit' value='{limit}'></div>
          <div class='col'><button class='btn'>Traži</button></div>
          <div class='col'><a class='btn ghost' href='/trials.csv?q={q}&limit={limit}'>⭳ CSV export</a></div>
        </form>
        <div style='overflow:auto'>
          <table>
            <thead><tr><th>ID</th><th>Kreiran</th><th>DR</th><th>Ime</th><th>Telefon</th><th>User</th><th>Pass</th><th>M3U</th><th>Ističe</th><th>Beleška</th></tr></thead>
            <tbody>{trs}</tbody>
          </table>
        </div>
      </div>
    </div>
    """
    return HTMLResponse(html)

@app.get('/trials.csv')
def trials_csv(req: Request, q: str = '', limit: int = 500):
    if not admin_ok(req): return RedirectResponse('/', status_code=302)
    sql = "SELECT id,ts,country,name,phone,username,password,m3u,expires_at,notes FROM trials"
    params=[]
    if q:
        sql += " WHERE (COALESCE(country,'')||' '||COALESCE(name,'')||' '||COALESCE(phone,'')||' '||COALESCE(username,'')) LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id DESC LIMIT ?"; params.append(int(limit))
    rows = db_all(sql, params)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["id","ts","country","name","phone","username","password","m3u","expires_at","notes"])
    for r in rows:
        w.writerow([r.get('id',''), r.get('ts',''), r.get('country',''), r.get('name',''),
                    r.get('phone',''), r.get('username',''), r.get('password',''), r.get('m3u',''),
                    r.get('expires_at',''), r.get('notes','')])
    return Response(buf.getvalue(), media_type='text/csv')

@app.get('/clients', response_class=HTMLResponse)
def list_clients(req: Request, q: str = '', limit: int = 500):
    if not admin_ok(req): return RedirectResponse('/', status_code=302)
    sql = "SELECT id,ts,plan,price,country,name,phone,username,password,m3u,expires_at,notes FROM clients"
    params=[]
    if q:
        sql += " WHERE (COALESCE(plan,'')||' '||COALESCE(country,'')||' '||COALESCE(name,'')||' '||COALESCE(phone,'')||' '||COALESCE(username,'')) LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id DESC LIMIT ?"; params.append(int(limit))
    rows = db_all(sql, params)
    def fmt_ts(x): return time.strftime('%d.%m.%Y %H:%M', time.localtime(x)) if x else ''
    trs=''.join([f"<tr><td>{r['id']}</td><td>{fmt_ts(r['ts'])}</td><td>{r.get('plan','')}</td><td>€{r.get('price',0):.0f}</td><td>{r.get('country','')}</td><td>{r.get('name','')}</td><td>{r.get('phone','')}</td><td>{r['username']}</td><td>{r['password']}</td><td><a href='{r['m3u']}' target='_blank'>m3u</a></td><td>{fmt_ts(r['expires_at'])}</td><td><span class='muted'>{r.get('notes','')}</span></td></tr>" for r in rows]) or "<tr><td colspan=12 class='muted'>Nema zapisa</td></tr>"
    html=f"""
    <!doctype html><meta charset='utf-8'><title>Plaćeni Kupci • {BRAND}</title>{_css()}
    {topbar('clients')}
    <div class='wrap'>
      <div class='card'>
        <h2>Plaćeni Kupci</h2>
        <form class='row' method='get'>
          <div class='col'><label>Pretraga</label><input class='input' name='q' value='{q}' placeholder='plan / ime / telefon / username / država'></div>
          <div class='col'><label>Limit</label><input class='input' name='limit' value='{limit}'></div>
          <div class='col'><button class='btn'>Traži</button></div>
          <div class='col'><a class='btn ghost' href='/clients.csv?q={q}&limit={limit}'>⭳ CSV export</a></div>
        </form>
        <div style='overflow:auto'>
          <table>
            <thead><tr><th>ID</th><th>Kreiran</th><th>Plan</th><th>Cena</th><th>DR</th><th>Ime</th><th>Telefon</th><th>User</th><th>Pass</th><th>M3U</th><th>Vredi do</th><th>Beleška</th></tr></thead>
            <tbody>{trs}</tbody>
          </table>
        </div>
      </div>
    </div>
    """
    return HTMLResponse(html)

@app.get('/clients.csv')
def clients_csv(req: Request, q: str = '', limit: int = 500):
    if not admin_ok(req): return RedirectResponse('/', status_code=302)
    sql = "SELECT id,ts,plan,price,country,name,phone,username,password,m3u,expires_at,notes FROM clients"
    params=[]
    if q:
        sql += " WHERE (COALESCE(plan,'')||' '||COALESCE(country,'')||' '||COALESCE(name,'')||' '||COALESCE(phone,'')||' '||COALESCE(username,'')) LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id DESC LIMIT ?"; params.append(int(limit))
    rows = db_all(sql, params)
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["id","ts","plan","price","country","name","phone","username","password","m3u","expires_at","notes"])
    for r in rows:
        w.writerow([r.get('id',''), r.get('ts',''), r.get('plan',''), r.get('price',''), r.get('country',''),
                    r.get('name',''), r.get('phone',''), r.get('username',''), r.get('password',''),
                    r.get('m3u',''), r.get('expires_at',''), r.get('notes','')])
    return Response(buf.getvalue(), media_type='text/csv')

# ---------------- Settings (UPDATE JSON) ----------------
@app.get("/settings", response_class=HTMLResponse)
def settings_ui(req: Request):
    if not admin_ok(req): return RedirectResponse("/", status_code=302)
    pretty = json.dumps(CFG, indent=2, ensure_ascii=False)
    return HTMLResponse(f"""
    <!doctype html><meta charset="utf-8"><title>Settings • {BRAND}</title>{_css()}
    {topbar("settings")}
    <div class="wrap">
      <div class="card">
        <h2>⚙️ UPDATE JSON (config.json)</h2>
        <p class="muted">Nalepi ceo JSON i klikni <strong>Sačuvaj</strong>. Promene (osim PORT) važe odmah.</p>
        <textarea id="cfg" class="input" style="height:420px;">{pretty}</textarea>
        <div class="row" style="margin-top:12px">
          <button class="btn" id="save">Sačuvaj</button>
          <a class="btn ghost" href="/">Nazad</a>
        </div>
        <div id="status" class="msg" style="display:none"></div>
        <div id="err" class="error" style="display:none"></div>
      </div>
    </div>
    <script>
      const saveBtn = document.getElementById('save');
      const ta = document.getElementById('cfg');
      const ok = document.getElementById('status');
      const err = document.getElementById('err');
      saveBtn.addEventListener('click', async () => {{
        ok.style.display='none'; err.style.display='none';
        let payload;
        try {{
          payload = JSON.parse(ta.value);
        }} catch(e) {{
          err.style.display='block'; err.textContent = 'JSON greška: ' + e.message;
          return;
        }}
        const r = await fetch('/settings/update', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        const txt = await r.text();
        if (!r.ok) {{
          err.style.display='block'; err.textContent = 'Greška: ' + txt;
        }} else {{
          ok.style.display='block'; ok.textContent = txt || 'Sačuvano.';
        }}
      }});
    </script>
    """)

@app.post("/settings/update")
async def settings_update(req: Request):
    if not admin_ok(req):
        raise HTTPException(401, "Unauthorized")

    try:
        data = await req.json()
        if not isinstance(data, dict):
            raise ValueError("Payload must be a JSON object")
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    # Normalize + basic validation
    if "PANEL_BASE" in data:
        data["PANEL_BASE"] = _normalize_panel_base(data["PANEL_BASE"])
    ok, msg = _validate_cfg_payload(data)
    if not ok:
        raise HTTPException(400, msg)

    # Merge into current CFG (preserve anything not provided)
    new_cfg = dict(CFG)
    new_cfg.update(data)

    # Write backup then save pretty JSON
    try:
        if os.path.exists(CFG_PATH):
            ts = time.strftime("%Y%m%d-%H%M%S")
            bk = CFG_PATH + f".bak-{ts}"
            with open(bk, "w", encoding="utf-8") as f:
                json.dump(CFG, f, indent=2, ensure_ascii=False)
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(500, f"Failed to write config: {e}")

    # Apply live (no restart)
    CFG.update(new_cfg)
    _apply_cfg_to_globals(CFG)

    # Also update the Panel client to use the fresh cfg
    try:
        panel.cfg = CFG
        panel.logged = False  # force re-login on next use
    except Exception:
        pass

    return Response("Config updated. (Note: PORT changes require restart.)", media_type="text/plain")

# ---------------- health ----------------
@app.get('/healthz')
def healthz():
    return JSONResponse({"status": "ok", "ts": int(time.time())})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("trial_admin_app:app", host="127.0.0.1", port=PORT, reload=True)
