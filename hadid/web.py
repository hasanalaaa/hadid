"""Local web UI for browsing and searching the archive (stdlib only).

Security model: the server is intended for loopback use only. It validates
the Host header (mitigating DNS-rebinding), sends a strict Content-Security-
Policy, and never writes anything to disk besides the archive itself.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .db import DEFAULT_DB_PATH, Archive

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def host_is_allowed(host_header: str | None) -> bool:
    """Return True when the Host header refers to this machine (loopback).

    Handles bracketed IPv6 literals ([::1], [::1]:8642) as well as
    host:port forms. Anything else is rejected (anti DNS-rebinding).
    """
    host = (host_header or "").strip().lower()
    if host.startswith("["):
        host = host.split("]", 1)[0].lstrip("[")
    else:
        host = host.split(":", 1)[0]
    return host in _ALLOWED_HOSTS


_SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    (
        "Content-Security-Policy",
        "default-src 'none'; style-src 'unsafe-inline'; "
        "script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:",
    ),
)

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hadid \u2014 your AI conversations</title>
<style>
  :root{
    --bg:#07090f; --panel:rgba(255,255,255,.03); --panel2:rgba(255,255,255,.06);
    --border:rgba(255,255,255,.08); --text:#e8eaf2; --muted:#8a90a6;
    --a1:#6366f1; --a2:#a855f7; --bar:rgba(10,12,20,.6);
  }
  body.light{
    --bg:#f3f4fa; --panel:rgba(15,18,35,.03); --panel2:rgba(15,18,35,.06);
    --border:rgba(15,18,35,.12); --text:#181b27; --muted:#5d6375;
    --bar:rgba(255,255,255,.65);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0;color:var(--text);
    font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif;
    background:
      radial-gradient(900px 500px at 85% -10%,rgba(99,102,241,.16),transparent 60%),
      radial-gradient(700px 420px at -10% 110%,rgba(168,85,247,.10),transparent 60%),
      var(--bg);
    display:flex;flex-direction:column;overflow:hidden;
    transition:background .3s,color .3s
  }
  ::-webkit-scrollbar{width:10px}
  ::-webkit-scrollbar-thumb{background:rgba(128,132,150,.25);border-radius:8px}
  ::-webkit-scrollbar-track{background:transparent}
  header{
    display:flex;align-items:center;gap:20px;padding:14px 22px;
    border-bottom:1px solid var(--border);
    backdrop-filter:blur(12px);background:var(--bar)
  }
  .logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px;cursor:pointer}
  .searchwrap{position:relative;flex:1;max-width:560px}
  #q{
    width:100%;padding:10px 44px 10px 16px;border-radius:12px;font-size:14px;
    border:1px solid var(--border);background:var(--panel);color:var(--text);
    outline:none;transition:border-color .2s, box-shadow .2s
  }
  #q:focus{border-color:var(--a1);box-shadow:0 0 0 3px rgba(99,102,241,.2)}
  .kbd{
    position:absolute;right:10px;top:50%;transform:translateY(-50%);
    font-size:11px;color:var(--muted);border:1px solid var(--border);
    border-radius:5px;padding:1px 7px;background:var(--panel2)
  }
  #stats{margin-left:auto;display:flex;gap:8px}
  .pill{font-size:12px;color:var(--muted);border:1px solid var(--border);border-radius:20px;padding:5px 12px;background:var(--panel);white-space:nowrap}
  .pill b{color:var(--text);font-weight:600}
  main{display:flex;flex:1;min-height:0}
  aside{width:340px;min-width:280px;border-right:1px solid var(--border);display:flex;flex-direction:column}
  .chips{display:flex;gap:6px;flex-wrap:wrap;padding:12px 14px;border-bottom:1px solid var(--border)}
  .chip{
    font-size:12px;padding:5px 12px;border-radius:20px;cursor:pointer;user-select:none;
    border:1px solid var(--border);color:var(--muted);background:transparent;transition:all .15s
  }
  .chip:hover{color:var(--text)}
  .chip.active{color:#fff;border-color:transparent;background:linear-gradient(135deg,var(--a1),var(--a2))}
  #list{flex:1;overflow-y:auto}
  .item{padding:13px 16px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .12s}
  .item:hover{background:var(--panel)}
  .item.active{background:var(--panel2);box-shadow:inset 3px 0 0 var(--a1)}
  .item .t{font-size:13.5px;font-weight:500;margin-bottom:5px;display:flex;gap:6px;align-items:center}
  .item .t .star{color:#fbbf24;font-size:12px}
  .item .m{font-size:11.5px;color:var(--muted);display:flex;gap:8px;align-items:center}
  .badge{font-size:10.5px;padding:2px 8px;border-radius:10px;font-weight:600}
  .b-chatgpt{background:rgba(16,163,127,.15);color:#10a37f}
  .b-claude{background:rgba(217,119,87,.15);color:#d97757}
  .b-gemini{background:rgba(66,133,244,.15);color:#4285f4}
  .snip{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5}
  mark{background:rgba(251,191,36,.25);color:inherit;border-radius:3px;padding:0 2px}
  section{flex:1;display:flex;flex-direction:column;min-width:0}
  .convhead{
    display:flex;align-items:center;gap:14px;padding:14px 24px;
    border-bottom:1px solid var(--border);background:var(--bar);backdrop-filter:blur(10px)
  }
  .convhead[hidden]{display:none}
  .convhead .grow{flex:1;min-width:0}
  .convhead .title{font-size:15px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .convhead .meta{font-size:12px;color:var(--muted);display:flex;gap:10px;align-items:center;margin-top:4px}
  .btn{
    font-size:12.5px;padding:7px 14px;border-radius:9px;cursor:pointer;
    border:1px solid var(--border);background:var(--panel);color:var(--text);
    transition:all .15s;white-space:nowrap
  }
  .btn:hover{border-color:var(--a1);background:var(--panel2)}
  .btn.fav{color:#f59e0b}
  #msgs{flex:1;overflow-y:auto;padding:28px 24px;display:flex;flex-direction:column}
  .msg{display:flex;gap:12px;width:100%;max-width:840px;margin:0 auto 18px;animation:fade .25s ease}
  .avatar{
    width:34px;height:34px;border-radius:10px;flex-shrink:0;display:flex;
    align-items:center;justify-content:center;font-size:10.5px;font-weight:700
  }
  .avatar.user{background:linear-gradient(135deg,var(--a1),var(--a2));color:#fff}
  .avatar.assistant{background:var(--panel2);border:1px solid var(--border);color:var(--muted)}
  .bubble{
    position:relative;flex:1;min-width:0;padding:13px 16px;border-radius:12px;
    background:var(--panel);border:1px solid var(--border);
    font-size:14px;line-height:1.65;white-space:pre-wrap;word-wrap:break-word
  }
  .msg.user .bubble{background:rgba(99,102,241,.08);border-color:rgba(99,102,241,.25)}
  .copy{
    position:absolute;top:8px;right:8px;opacity:0;transition:opacity .15s;
    font-size:11px;padding:3px 9px;border-radius:6px;cursor:pointer;
    border:1px solid var(--border);background:var(--bar);color:var(--muted)
  }
  .bubble:hover .copy{opacity:1}
  .copy:hover{color:var(--text)}
  .dash{width:100%;max-width:840px;margin:0 auto;animation:fade .25s ease}
  .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:22px}
  .card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:18px}
  .card .num{font-size:28px;font-weight:700;background:linear-gradient(135deg,var(--a1),var(--a2));-webkit-background-clip:text;background-clip:text;color:transparent}
  .card .lbl{font-size:12px;color:var(--muted);margin-top:4px}
  .chart{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:18px}
  .chart h3{margin:0 0 14px;font-size:13px;color:var(--muted);font-weight:600}
  .empty{color:var(--muted);text-align:center;margin:auto;max-width:460px;padding:40px 20px}
  .empty h2{color:var(--text);font-size:20px;margin:18px 0 8px}
  .empty p{font-size:13.5px;line-height:1.7}
  .empty pre{
    text-align:left;font-size:12.5px;background:var(--panel);border:1px solid var(--border);
    border-radius:10px;padding:14px 16px;overflow-x:auto;color:var(--a1)
  }
  .btn:focus-visible,.chip:focus-visible,#q:focus-visible,.item:focus-visible{outline:2px solid var(--a1);outline-offset:2px}
  @keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
  @media (prefers-reduced-motion: reduce){.msg,.dash{animation:none}}
</style>
</head>
<body>
<header>
  <div class="logo" id="logo" title="Dashboard">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <defs><linearGradient id="g" x1="0" y1="0" x2="24" y2="24">
        <stop stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/>
      </linearGradient></defs>
      <path d="M12 2 L21 7 V17 L12 22 L3 17 V7 Z" stroke="url(#g)" stroke-width="2" stroke-linejoin="round"/>
      <path d="M9 9 V15 M15 9 V15 M9 12 H15" stroke="url(#g)" stroke-width="2" stroke-linecap="round"/>
    </svg>
    Hadid
  </div>
  <div class="searchwrap">
    <input id="q" placeholder="Search everything you ever discussed with AI..." autocomplete="off" aria-label="Search conversations">
    <span class="kbd">/</span>
  </div>
  <div id="stats"></div>
  <button class="btn" id="themebtn" title="Toggle theme" aria-label="Toggle color theme">\u263e</button>
</header>
<main>
  <aside>
    <div class="chips" id="chips"></div>
    <div id="list"></div>
  </aside>
  <section>
    <div class="convhead" id="convhead" hidden>
      <div class="grow">
        <div class="title" id="ctitle"></div>
        <div class="meta" id="cmeta"></div>
      </div>
      <button class="btn" id="favbtn"></button>
      <button class="btn" id="mdbtn">Export .md</button>
    </div>
    <div id="msgs"></div>
  </section>
</main>
<script>
var state = {source: null, favorites: false, current: null, currentConv: null};
var listEl = document.getElementById('list');
var msgsEl = document.getElementById('msgs');
var q = document.getElementById('q');
var NL = String.fromCharCode(10);

function api(path, opts){ return fetch(path, opts).then(function(r){ return r.json(); }); }
function el(tag, cls, text){
  var e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function badge(source){ return el('span', 'badge b-' + source, source); }

function renderStats(){
  api('/api/stats').then(function(s){
    var box = document.getElementById('stats');
    box.textContent = '';
    [[s.conversations, ' conversations'], [s.messages, ' messages']].forEach(function(x){
      var p = el('span', 'pill');
      p.appendChild(el('b', null, String(x[0])));
      p.appendChild(document.createTextNode(x[1]));
      box.appendChild(p);
    });
  });
}

var CHIPS = [
  {label: 'All', source: null, fav: false},
  {label: 'ChatGPT', source: 'chatgpt', fav: false},
  {label: 'Claude', source: 'claude', fav: false},
  {label: 'Gemini', source: 'gemini', fav: false},
  {label: '\u2605 Favorites', source: null, fav: true}
];
function renderChips(){
  var box = document.getElementById('chips');
  box.textContent = '';
  CHIPS.forEach(function(c){
    var active = state.favorites === c.fav && state.source === c.source;
    var chip = el('div', 'chip' + (active ? ' active' : ''), c.label);
    chip.tabIndex = 0;
    chip.setAttribute('role', 'button');
    chip.onkeydown = function(ev){
      if (ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); chip.onclick(); }
    };
    chip.onclick = function(){
      state.source = c.source;
      state.favorites = c.fav;
      renderChips();
      refresh();
    };
    box.appendChild(chip);
  });
}

function refresh(){
  var query = q.value.trim();
  if (query){
    var url = '/api/search?q=' + encodeURIComponent(query);
    if (state.source) url += '&source=' + state.source;
    api(url).then(renderResults);
  } else {
    var url2 = '/api/conversations';
    var params = [];
    if (state.source) params.push('source=' + state.source);
    if (state.favorites) params.push('favorites=1');
    if (params.length) url2 += '?' + params.join('&');
    api(url2).then(renderConversations);
  }
}

function renderConversations(convs){
  listEl.textContent = '';
  if (!convs.length){
    listEl.appendChild(el('div', 'item', 'Nothing here yet.'));
    return;
  }
  convs.forEach(function(c){
    var item = el('div', 'item' + (state.current === c.id ? ' active' : ''));
    var t = el('div', 't');
    if (c.favorite) t.appendChild(el('span', 'star', '\u2605'));
    t.appendChild(document.createTextNode(c.title || 'Untitled'));
    var m = el('div', 'm');
    m.appendChild(badge(c.source));
    var date = (c.created_at || '').slice(0, 10) || '\u2014';
    m.appendChild(document.createTextNode(date + ' \u00b7 ' + c.message_count + ' msgs'));
    item.appendChild(t);
    item.appendChild(m);
    item.tabIndex = 0;
    item.onkeydown = function(ev){ if (ev.key === 'Enter') item.onclick(); };
    item.onclick = function(){ openConv(c.id); };
    listEl.appendChild(item);
  });
}

function snippetEl(s){
  var d = el('div', 'snip');
  var parts = s.split('\u00ab');
  d.appendChild(document.createTextNode(parts[0]));
  for (var i = 1; i < parts.length; i++){
    var j = parts[i].indexOf('\u00bb');
    if (j < 0){ d.appendChild(document.createTextNode(parts[i])); continue; }
    d.appendChild(el('mark', null, parts[i].slice(0, j)));
    d.appendChild(document.createTextNode(parts[i].slice(j + 1)));
  }
  return d;
}

function renderResults(results){
  listEl.textContent = '';
  if (!results.length){
    listEl.appendChild(el('div', 'item', 'No results.'));
    return;
  }
  results.forEach(function(r){
    var item = el('div', 'item' + (state.current === r.conversation_id ? ' active' : ''));
    item.appendChild(el('div', 't', r.title || 'Untitled'));
    var m = el('div', 'm');
    m.appendChild(badge(r.source));
    m.appendChild(document.createTextNode(r.role));
    item.appendChild(m);
    item.appendChild(snippetEl(r.snippet));
    item.tabIndex = 0;
    item.onkeydown = function(ev){ if (ev.key === 'Enter') item.onclick(); };
    item.onclick = function(){ openConv(r.conversation_id); };
    listEl.appendChild(item);
  });
}

function updateFavBtn(fav){
  var b = document.getElementById('favbtn');
  b.textContent = fav ? '\u2605 Favorited' : '\u2606 Favorite';
  b.className = 'btn' + (fav ? ' fav' : '');
}

function openConv(id){
  state.current = id;
  api('/api/conversation/' + id).then(function(c){
    state.currentConv = c;
    document.getElementById('convhead').hidden = false;
    document.getElementById('ctitle').textContent = c.title || 'Untitled';
    var meta = document.getElementById('cmeta');
    meta.textContent = '';
    meta.appendChild(badge(c.source));
    var date = (c.created_at || '').slice(0, 10);
    meta.appendChild(document.createTextNode(date + ' \u00b7 ' + c.messages.length + ' messages'));
    updateFavBtn(c.favorite);
    msgsEl.textContent = '';
    c.messages.forEach(function(msg){
      var role = msg.role === 'user' ? 'user' : 'assistant';
      var row = el('div', 'msg ' + role);
      row.appendChild(el('div', 'avatar ' + role, role === 'user' ? 'You' : 'AI'));
      var bubble = el('div', 'bubble');
      var btn = el('button', 'copy', 'Copy');
      btn.onclick = function(){
        navigator.clipboard.writeText(msg.content);
        btn.textContent = 'Copied';
        setTimeout(function(){ btn.textContent = 'Copy'; }, 1200);
      };
      bubble.appendChild(btn);
      bubble.appendChild(document.createTextNode(msg.content));
      row.appendChild(bubble);
      msgsEl.appendChild(row);
    });
    msgsEl.scrollTop = 0;
    refresh();
  });
}

document.getElementById('favbtn').onclick = function(){
  if (state.current == null) return;
  api('/api/conversation/' + state.current + '/favorite', {method: 'POST'})
    .then(function(r){
      if (state.currentConv) state.currentConv.favorite = r.favorite;
      updateFavBtn(r.favorite);
      refresh();
      renderStats();
    });
};

document.getElementById('mdbtn').onclick = function(){
  var c = state.currentConv;
  if (!c) return;
  var lines = ['# ' + (c.title || 'Untitled'), '',
               '- Source: ' + c.source,
               '- Created: ' + (c.created_at || 'unknown'), ''];
  c.messages.forEach(function(m){
    lines.push('## ' + (m.role === 'user' ? 'You' : 'Assistant'));
    lines.push('');
    lines.push(m.content);
    lines.push('');
  });
  var blob = new Blob([lines.join(NL)], {type: 'text/markdown'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (c.title || 'conversation').replace(/[^a-zA-Z0-9]+/g, '-') + '.md';
  a.click();
  URL.revokeObjectURL(a.href);
};

function emptyState(){
  var empty = el('div', 'empty');
  empty.appendChild(el('h2', null, 'Your AI conversations, in one place.'));
  empty.appendChild(el('p', null,
    'Import your ChatGPT, Claude, or Gemini exports and search everything locally. Nothing ever leaves your machine.'));
  empty.appendChild(el('pre', null,
    'hadid import auto chatgpt-export.zip' + NL +
    'hadid import claude  conversations.json' + NL +
    'hadid import gemini  MyActivity.json'));
  return empty;
}

function buildChart(act){
  var NS = 'http://www.w3.org/2000/svg';
  var W = 760, H = 170, pad = 4;
  var max = 1;
  act.forEach(function(a){ if (a.n > max) max = a.n; });
  var svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + (H + 24));
  svg.setAttribute('width', '100%');
  var n = act.length;
  var bw = Math.max(4, (W - (n - 1) * pad) / n);
  act.forEach(function(a, i){
    var h = Math.max(3, (a.n / max) * H);
    var r = document.createElementNS(NS, 'rect');
    r.setAttribute('x', i * (bw + pad));
    r.setAttribute('y', H - h);
    r.setAttribute('width', bw);
    r.setAttribute('height', h);
    r.setAttribute('rx', 3);
    r.setAttribute('fill', '#6366f1');
    r.setAttribute('opacity', '0.85');
    var t = document.createElementNS(NS, 'title');
    t.textContent = a.month + ': ' + a.n + ' messages';
    r.appendChild(t);
    svg.appendChild(r);
  });
  function label(x, text, anchor){
    var t = document.createElementNS(NS, 'text');
    t.setAttribute('x', x);
    t.setAttribute('y', H + 17);
    t.setAttribute('fill', '#8a90a6');
    t.setAttribute('font-size', '11');
    t.setAttribute('text-anchor', anchor);
    t.textContent = text;
    svg.appendChild(t);
  }
  if (n){
    label(0, act[0].month, 'start');
    if (n > 1) label(W, act[n - 1].month, 'end');
  }
  return svg;
}

function renderDashboard(){
  Promise.all([api('/api/stats'), api('/api/activity')]).then(function(res){
    var s = res[0], act = res[1];
    msgsEl.textContent = '';
    var dash = el('div', 'dash');
    var cards = el('div', 'cards');
    [[s.conversations, 'Conversations'], [s.messages, 'Messages'], [s.favorites, 'Favorites']]
      .forEach(function(x){
        var c = el('div', 'card');
        c.appendChild(el('div', 'num', String(x[0])));
        c.appendChild(el('div', 'lbl', x[1]));
        cards.appendChild(c);
      });
    dash.appendChild(cards);
    if (act.length){
      var chart = el('div', 'chart');
      chart.appendChild(el('h3', null, 'Messages per month'));
      chart.appendChild(buildChart(act));
      dash.appendChild(chart);
    }
    msgsEl.appendChild(dash);
  });
}

function showHome(){
  api('/api/conversations').then(function(convs){
    msgsEl.textContent = '';
    if (!convs.length){ msgsEl.appendChild(emptyState()); }
    else { renderDashboard(); }
  });
}

document.getElementById('logo').onclick = function(){
  state.current = null;
  state.currentConv = null;
  document.getElementById('convhead').hidden = true;
  showHome();
  refresh();
};

function applyTheme(t){
  document.body.className = t === 'light' ? 'light' : '';
  document.getElementById('themebtn').textContent = t === 'light' ? '\u2600' : '\u263e';
}
document.getElementById('themebtn').onclick = function(){
  var t = document.body.className === 'light' ? 'dark' : 'light';
  try { localStorage.setItem('hadid-theme', t); } catch (e) {}
  applyTheme(t);
};

var timer = null;
q.addEventListener('input', function(){
  clearTimeout(timer);
  timer = setTimeout(refresh, 250);
});
document.addEventListener('keydown', function(e){
  if (e.key === '/' && document.activeElement !== q){ e.preventDefault(); q.focus(); }
  if (e.key === 'Escape'){ q.value = ''; q.blur(); refresh(); }
});

function init(){
  var t = 'dark';
  try { t = localStorage.getItem('hadid-theme') || 'dark'; } catch (e) {}
  applyTheme(t);
  renderChips();
  renderStats();
  refresh();
  showHome();
}
init();
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    """Request handler. The archive is shared and guarded by a lock."""

    server_version = "Hadid"
    archive: Archive | None = None
    lock = threading.Lock()

    # -- helpers ---------------------------------------------------------

    def _host_allowed(self) -> bool:
        return host_is_allowed(self.headers.get("Host"))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in _SECURITY_HEADERS:
            self.send_header(name, value)
        if content_type.startswith("application/json"):
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    # -- routes ----------------------------------------------------------

    def do_GET(self) -> None:
        if not self._host_allowed():
            self._send(403, b"Forbidden", "text/plain")
            return
        if self.archive is None:  # pragma: no cover - misconfiguration guard
            self._json({"error": "server not ready"}, status=500)
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        if path == "/":
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/conversations":
            source = qs.get("source", [None])[0]
            favorites = qs.get("favorites", ["0"])[0] in ("1", "true")
            with self.lock:
                data = self.archive.list_conversations(
                    source=source, favorites_only=favorites
                )
            self._json(data)
        elif path == "/api/search":
            query = qs.get("q", [""])[0]
            source = qs.get("source", [None])[0]
            if not query.strip():
                self._json([])
                return
            with self.lock:
                data = self.archive.search(query, source=source)
            self._json(data)
        elif path == "/api/stats":
            with self.lock:
                data = self.archive.stats()
            self._json(data)
        elif path == "/api/activity":
            with self.lock:
                data = self.archive.activity()
            self._json(data)
        elif path.startswith("/api/conversation/"):
            try:
                conv_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                self._json({"error": "invalid id"}, status=400)
                return
            with self.lock:
                conv = self.archive.get_conversation(conv_id)
            if conv is None:
                self._json({"error": "not found"}, status=404)
            else:
                self._json(conv)
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self) -> None:
        if not self._host_allowed():
            self._send(403, b"Forbidden", "text/plain")
            return
        if self.archive is None:  # pragma: no cover - misconfiguration guard
            self._json({"error": "server not ready"}, status=500)
            return
        parsed = urllib.parse.urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        if (
            len(parts) == 4
            and parts[0] == "api"
            and parts[1] == "conversation"
            and parts[3] == "favorite"
        ):
            try:
                conv_id = int(parts[2])
            except ValueError:
                self._json({"error": "invalid id"}, status=400)
                return
            with self.lock:
                value = self.archive.toggle_favorite(conv_id)
            if value is None:
                self._json({"error": "not found"}, status=404)
            else:
                self._json({"favorite": value})
        else:
            self._send(404, b"Not found", "text/plain")

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug("%s - %s", self.address_string(), fmt % args)


def serve(
    db_path: str = DEFAULT_DB_PATH, host: str = "127.0.0.1", port: int = 8642
) -> None:
    """Start the local web app (loopback use only)."""
    if host not in _ALLOWED_HOSTS:
        logger.warning(
            "binding to %s exposes your archive beyond this machine", host
        )
    _Handler.archive = Archive(db_path, allow_threads=True)
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"Hadid is running at http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        _Handler.archive.close()
