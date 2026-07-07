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
