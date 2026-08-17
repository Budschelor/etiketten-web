#!/usr/bin/env python3
"""
Taktikboard
===========
Baut aus den Kaderdaten zweier Teams eine eigenstaendige HTML-Datei
(Taktikboard fuers iPad/Browser) -- Kernlogik uebernommen aus
~/Travis/webapp_generator.py, hier als importierbare Funktion statt Skript.
"""
import base64
import json
import os
from datetime import date, timedelta

POS_SHORT = {
    'Torwart':'TW','Innenverteidiger':'IV','Rechter Verteidiger':'RV','Linker Verteidiger':'LV',
    'Defensives Mittelfeld':'ZDM','Zentrales Mittelfeld':'ZM','Rechtes Mittelfeld':'RM',
    'Linkes Mittelfeld':'LM','Offensives Mittelfeld':'OM','Rechter Fluegel':'RF','Linker Fluegel':'LF',
    'Linksaussen':'LA','Rechtsaussen':'RA','Haengende Spitze':'HS','Mittelstuermer':'ST','Sturm':'ST',
}
POS_GROUP = {
    'TW':'tw',
    'IV':'def','LV':'def','RV':'def','LAV':'def','RAV':'def',
    'ZDM':'mid','ZM':'mid','DM':'mid','OM':'mid','LM':'mid','RM':'mid','LF':'mid','RF':'mid',
    'LA':'att','RA':'att','ST':'att','HS':'att','MS':'att',
}
GROUP_ORDER = {'tw':0,'def':1,'mid':2,'att':3,'unk':4}


def photo_b64(path):
    """Foto auf Thumbnail-Groesse schrumpfen und als base64 einbetten."""
    if not path or not os.path.exists(path): return ''
    try:
        from PIL import Image
        import io
        img = Image.open(path).convert('RGB')
        img.thumbnail((100, 130), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=75, optimize=True)
        data = base64.b64encode(buf.getvalue()).decode()
        return 'data:image/jpeg;base64,' + data
    except Exception:
        ext = 'png' if path.lower().endswith('.png') else 'jpeg'
        with open(path, 'rb') as f: data = base64.b64encode(f.read()).decode()
        return f'data:image/{ext};base64,{data}'


def birthday_this_week(geb_str):
    """Prueft ob Geburtstag (TM-Format: '06.12.1993 (32)') in diese Kalenderwoche faellt."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    try:
        date_part = geb_str.split('(')[0].strip()
        parts = date_part.split('.')
        day, month = int(parts[0]), int(parts[1])
        bday = date(today.year, month, day)
        return week_start <= bday <= week_end
    except Exception:
        return False


def build_players(raw):
    result = []
    for i, p in enumerate(raw):
        ps = POS_SHORT.get(p.get('position',''), p.get('position','')[:3])
        g  = POS_GROUP.get(ps, 'unk')
        result.append({
            'id':str(i), 'number':p.get('number',''), 'name':p.get('name',''),
            'last':p.get('name','').strip().split()[-1] if p.get('name','').strip() else '',
            'pos':ps, 'group':g, 'go':GROUP_ORDER.get(g,4),
            'foot':p.get('foot','-'), 'age':p.get('age','-'),
            'height':p.get('height','-'), 'nationality':p.get('nationality','-'),
            'games':p.get('games_display','0 (0)'), 'goals':p.get('goals','0'),
            'assists':p.get('assists','0'), 'yellow':p.get('yellow','0'),
            'yellow_red':p.get('yellow_red','0'), 'red':p.get('red','0'),
            'gegentore':p.get('gegentore','-'), 'zu_null':p.get('zu_null','-'),
            'transfer':p.get('transfer_info','-'),
            'photo':photo_b64(p.get('local_photo','')),
            'birthday':birthday_this_week(p.get('geburtsdatum','-')),
        })
    result.sort(key=lambda p:(p['go'], int(p['number']) if str(p['number']).isdigit() else 999))
    return result


def build_coach(coach_raw):
    """Wandelt das rohe Trainer-Dict von scraper.get_coach_info() in das
    Format um, das das Taktikboard-Template erwartet (oder None)."""
    if not coach_raw:
        return None
    return {
        'name':        coach_raw.get('name', ''),
        'role':        coach_raw.get('role', 'Trainer'),
        'age':         coach_raw.get('age', ''),
        'nationality': coach_raw.get('nationality', ''),
        'amtsantritt': coach_raw.get('amtsantritt', ''),
        'pps':         coach_raw.get('pps', ''),
        'photo':       photo_b64(coach_raw.get('local_photo', '')),
    }


HTML = r'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Taktikboard">
<title>Taktikboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{width:100%;height:100%;overflow:hidden;background:#0f151c;
  font-family:-apple-system,BlinkMacSystemFont,sans-serif;-webkit-user-select:none;user-select:none}
#app{display:flex;flex-direction:column;height:100vh;padding:5px;gap:4px}
#header{display:flex;justify-content:space-between;align-items:center;
  flex-shrink:0;height:26px;padding:0 4px}
.team-title{font-size:12px;font-weight:700;color:#ecf0f1;letter-spacing:.2px;width:200px}
.team-title.right{text-align:right}
#app-title{display:flex;align-items:center;justify-content:center;gap:6px;flex:1}
#clock-display{font-size:14px;font-weight:700;color:#4a8fa8;letter-spacing:2px;min-width:52px;text-align:center;font-variant-numeric:tabular-nums}
#clock-display.running{color:#64c8e8;text-shadow:0 0 6px rgba(100,200,232,.25);cursor:pointer}
#clock-display.paused{color:#e67e22;text-shadow:none;cursor:pointer}
.clock-btn{font-size:9px;font-weight:700;color:#3d5166;background:#0d141c;border:1px solid #253545;border-radius:3px;padding:3px 8px;cursor:pointer;touch-action:manipulation;transition:.15s;letter-spacing:.5px}
.clock-btn:active,.clock-btn.active-half{color:#64c8e8;border-color:#4a8fa8;background:#0f1922}
#fields{display:flex;gap:0;flex:1;min-height:0;border:1.5px solid #253545;border-radius:10px;overflow:hidden}
.field-zone{flex:1;background:#18232e;position:relative;overflow:hidden;transition:background .15s}
#field-0{border-right:2px solid #2a4055}
#field-1{border-left:none}
.field-zone.drag-over{background:#1a2d40}
.fz-label{position:absolute;top:8px;font-size:8px;font-weight:700;color:#2a4055;text-transform:uppercase;letter-spacing:1px;pointer-events:none;white-space:nowrap}
#field-0 .fz-label{left:8px}
#field-1 .fz-label{right:8px}
#field-0::after,#field-1::after{content:'';position:absolute;top:50%;transform:translateY(-50%);width:6px;height:6px;border-radius:50%;background:#2a4055;pointer-events:none}
#field-0::after{right:-4px}
#field-1::after{left:-4px}
#lists{display:flex;gap:4px;flex-shrink:0;height:150px}
.player-list{flex:1;background:#131c26;border:1px solid #1e2f3e;border-radius:8px;display:flex;flex-direction:column;overflow:hidden}
.pl-header{display:flex !important;align-items:center;gap:4px;padding:4px 8px;background:#0f1922;border-bottom:1px solid #1e2f3e;font-size:9px;font-weight:700;color:#4a6278;text-transform:uppercase;letter-spacing:.8px;flex-shrink:0}
.pl-hdr-text{flex:1}
.view-btn{background:none;border:1px solid #253545;border-radius:3px;color:#4a6278;font-size:8px;padding:2px 7px;cursor:pointer;flex-shrink:0;touch-action:manipulation;font-weight:700;letter-spacing:.3px}
.view-btn.active{color:#64c8e8;border-color:#4a8fa8;background:#0f1922}
.pl-scroll{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.pl-scroll::-webkit-scrollbar{display:none}
.pl-row{display:flex;align-items:center;gap:6px;padding:5px 8px;cursor:grab;touch-action:none;border-bottom:1px solid #1a2535;transition:opacity .2s,background .15s}
.pl-row:active{background:#1e2f3e}
.pl-row.on-field{opacity:.3;cursor:default;pointer-events:none}
.pl-row.on-field.subbed-in{opacity:.85}
.pl-row.on-field.subbed-in .pl-sub{opacity:1}
.pl-row.fp-hidden{display:none}
.pl-dot{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.pl-dot.tw{background:#FFD966}
.pl-dot.def{background:#9DC3E6}
.pl-dot.mid{background:#A9D18E}
.pl-dot.att{background:#F4B183}
.pl-dot.unk{background:#aaa}
.pl-num{font-size:9px;font-weight:700;color:#6b8aaa;min-width:18px;text-align:right}
.fc-bday{font-size:10px;margin-right:2px}
.pl-name{font-size:10px;font-weight:500;color:#c8d8e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
.pl-sub{font-size:10px;font-weight:900;flex-shrink:0;opacity:0;transition:opacity .2s}
.pl-sub.active{opacity:1}
.pl-sub.is-out{color:#e74c3c}
.pl-sub.is-in{color:#27ae60}
.pl-remove{font-size:12px;color:#3d5166;background:none;border:none;padding:0 6px;cursor:pointer;flex-shrink:0;touch-action:manipulation;line-height:1;opacity:.6}
.pl-remove:active{color:#e74c3c;opacity:1}
#undo-toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1e2f3e;border:1px solid #4a8fa8;border-radius:6px;padding:7px 12px;display:flex;align-items:center;gap:10px;font-size:11px;color:#c8d8e8;z-index:99999;opacity:0;transition:opacity .2s;pointer-events:none;white-space:nowrap}
#undo-toast.visible{opacity:1;pointer-events:auto}
.undo-btn{background:#4a8fa8;border:none;border-radius:3px;color:#fff;font-size:10px;font-weight:700;padding:3px 9px;cursor:pointer;touch-action:manipulation}
.hdr-tw{background:#FFD966}
.hdr-def{background:#9DC3E6}
.hdr-mid{background:#A9D18E}
.hdr-att{background:#F4B183}
.hdr-unk{background:#dfe6e9}
.fc{position:absolute;width:160px;height:118px;background:#fff;border-radius:5px;box-shadow:0 3px 14px rgba(0,0,0,.55);display:flex;flex-direction:column;overflow:hidden;touch-action:none;min-width:120px;min-height:100px}
.fc.dragging{box-shadow:0 10px 30px rgba(0,0,0,.7);transform:scale(1.03);z-index:8000}
.fc-head{display:flex;align-items:center;padding:3px 20px 3px 4px;gap:3px;font-weight:800;color:rgba(0,0,0,.72);flex-shrink:0;cursor:grab;touch-action:none;height:20px}
.fc-head-num{font-size:12px;min-width:18px;line-height:1}
.fc-head-name{font-size:7.5px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;line-height:1}
.fc-head-pos{font-size:8px;font-weight:900}
.fc-close{position:absolute;top:2px;right:2px;width:16px;height:16px;background:rgba(0,0,0,.2);border:none;border-radius:50%;color:rgba(0,0,0,.7);font-size:10px;line-height:16px;text-align:center;cursor:pointer;z-index:10;padding:0;touch-action:manipulation}
.fc-close:active{background:rgba(0,0,0,.4)}
.fc-stats{display:flex;align-items:center;padding:2px 4px;background:#f5f6f8;border-top:1px solid #e0e3e8;border-bottom:1px solid #e0e3e8;gap:2px;flex-shrink:0;height:16px}
.fc-info{font-size:6.5px;color:#555;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fc-sv{font-size:6.5px;font-weight:700;color:#222;background:#e4e7ec;border-radius:2px;padding:1px 3px;white-space:nowrap}
.fc-body{flex:1;display:flex;min-height:0;overflow:hidden}
.fc-photo{width:48px;min-width:48px;overflow:hidden;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:#edf0f2;border-right:1px solid #e0e3e8;position:relative}
.fc-photo img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block}
.fc-photo .nop{font-size:22px;opacity:.3}
.fc-notes{flex:1;min-width:0;min-height:0}
.fc-notes textarea{width:100%;height:100%;border:none;outline:none;background:#fff;font-size:8px;font-family:-apple-system,sans-serif;padding:3px 4px;resize:none;color:#333;line-height:1.4;touch-action:auto}
.fc-notes textarea::placeholder{color:#ccc;font-size:7.5px}
.fc-transfer{padding:2px 4px;font-size:6px;color:#777;text-align:center;border-top:1px solid #e0e3e8;background:#f5f6f8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0;height:13px;line-height:9px}
.fc-resize{position:absolute;bottom:0;right:0;width:20px;height:20px;cursor:nwse-resize;touch-action:none;z-index:10;display:flex;align-items:center;justify-content:center}
.fc-resize::after{content:'';display:block;width:9px;height:9px;border-right:2px solid #bbb;border-bottom:2px solid #bbb;border-radius:1px}
.fc-subs{display:flex;gap:2px;flex-shrink:0}
.fc-sub{width:16px;height:16px;border:none;border-radius:50%;font-size:9px;line-height:16px;text-align:center;padding:0;cursor:pointer;touch-action:manipulation;opacity:.45;transition:opacity .15s,transform .1s;color:#fff;font-weight:900}
.fc-sub:active{transform:scale(.9)}
.fc-sub.sub-out{background:#c0392b}
.fc-sub.sub-in{background:#27ae60}
.fc-sub.active{opacity:1;transform:scale(1.15)}
.fc-sub-min{font-size:7px;color:#aaa;min-width:14px;text-align:center;line-height:16px;flex-shrink:0;font-weight:600}
.fc.is-out{border-left:3px solid #e74c3c}
.fc.is-in{border-left:3px solid #2ecc71}
.fc.is-out .fc-photo::after,.fc.is-in .fc-photo::after{content:'';position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none}
.fc.is-out .fc-photo::after{background:rgba(231,76,60,.18)}
.fc.is-in .fc-photo::after{background:rgba(46,204,113,.18)}
.fc-ghost{opacity:.88}
.fc-coach .fc-head{background:#1a3a5c;color:#ecf0f1}
.fc-coach-label{font-size:8px;font-weight:900;color:#ecf0f1;text-transform:uppercase;letter-spacing:1.5px;flex:1}
.fc-coach-body{display:flex;flex-shrink:0;overflow:hidden}
.fc-coach-photo{width:52px;min-width:52px;overflow:hidden;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:#edf0f2;border-right:1px solid #e0e3e8}
.fc-coach-photo img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block}
.fc-coach-photo .nop{font-size:22px;opacity:.3}
.fc-coach-info{flex:1;padding:4px 5px;display:flex;flex-direction:column;gap:2px;overflow:hidden}
.fc-coach-name{font-size:10px;font-weight:800;color:#1a2535;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fc-coach-role{font-size:8.5px;color:#888;font-style:italic}
.fc-coach-detail{font-size:8px;color:#555}
.fc-coach-notes{flex:1;min-height:28px;border-top:1px solid #e0e3e8}
.fc-coach-notes textarea{width:100%;height:100%;border:none;outline:none;background:#fff;font-size:8px;font-family:-apple-system,sans-serif;padding:3px 4px;resize:none;color:#333;line-height:1.4;touch-action:auto}
.fc-coach-notes textarea::placeholder{color:#ccc;font-size:7.5px}
</style>
</head>
<body>
<div id="undo-toast"><span id="undo-msg"></span><button class="undo-btn" onclick="undoRemove()">&#8617; Rückgängig</button></div>
<div id="app">
  <div id="header">
    <span class="team-title" id="t0name">__TEAM0__</span>
    <div id="app-title">
      <button class="clock-btn" id="btn-0" onclick="startClock(0)">&#9679; 0&#8242;</button>
      <span id="clock-display" onclick="togglePause()" title="Pause / Weiter">00:00</span>
      <button class="clock-btn" id="btn-45" onclick="startClock(45)">45&#8242; &#9679;</button>
    </div>
    <span class="team-title right" id="t1name">__TEAM1__</span>
  </div>

  <div id="fields">
    <div class="field-zone" id="field-0" data-team="0">
      <span class="fz-label">&#9668; __TEAM0__</span>
    </div>
    <div class="field-zone" id="field-1" data-team="1">
      <span class="fz-label">__TEAM1__ &#9658;</span>
    </div>
  </div>

  <div id="lists">
    <div class="player-list" id="list-0" data-team="0">
      <div class="pl-header"><span class="pl-hdr-text">__TEAM0__</span><button class="view-btn active" id="vbtn-0-all" onclick="setView(0,'all')">Alle</button><button class="view-btn" id="vbtn-0-bank" onclick="setView(0,'bank')">Bank</button></div>
      <div class="pl-scroll" id="scroll-0"></div>
    </div>
    <div class="player-list" id="list-1" data-team="1">
      <div class="pl-header"><span class="pl-hdr-text">__TEAM1__</span><button class="view-btn active" id="vbtn-1-all" onclick="setView(1,'all')">Alle</button><button class="view-btn" id="vbtn-1-bank" onclick="setView(1,'bank')">Bank</button></div>
      <div class="pl-scroll" id="scroll-1"></div>
    </div>
  </div>
</div>

<script>
const TEAMS = __DATA__;
const idx = {};
TEAMS.forEach((t,ti) => t.players.forEach(p => { idx[`${ti}-${p.id}`] = p; }));
const pl = (ti,pid) => idx[`${ti}-${pid}`];

const MATCH_KEY = '__MATCH_KEY__';
const IS_SERVER = (window.location.protocol !== 'file:');
function _loadState() {
  if (IS_SERVER) {
    // Per Server: Stand vom Mac holen
    try {
      const x = new XMLHttpRequest();
      x.open('GET', '/api/state?key=' + encodeURIComponent(MATCH_KEY), false);
      x.send();
      if (x.status === 200) {
        const s = JSON.parse(x.responseText);
        if (s && s.notes !== undefined) return s;
      }
    } catch(e) {}
    // Server hat noch keinen Stand → lokalen Stand übertragen
    try {
      const r = localStorage.getItem(MATCH_KEY);
      if (r) {
        fetch('/api/state?key=' + encodeURIComponent(MATCH_KEY),
          {method:'POST', headers:{'Content-Type':'application/json'}, body:r});
        return JSON.parse(r);
      }
    } catch(e) {}
  } else {
    try { const r=localStorage.getItem(MATCH_KEY); return r?JSON.parse(r):{notes:{},cards:{},coach:{}}; } catch(e) {}
  }
  return {notes:{},cards:{},coach:{}};
}
function _saveState() {
  _lastSyncHash = JSON.stringify(appState);
  if (IS_SERVER) {
    try { fetch('/api/state?key='+encodeURIComponent(MATCH_KEY),
      {method:'POST',headers:{'Content-Type':'application/json'},body:_lastSyncHash}); } catch(e) {}
  }
  try { localStorage.setItem(MATCH_KEY, _lastSyncHash); } catch(e) {}
}
const appState = _loadState();
let _lastSyncHash = JSON.stringify(appState);

const NOTES = { 0: {}, 1: {} };
Object.entries(appState.notes||{}).forEach(([k,v]) => {
  const sep=k.indexOf('_'); const ti=parseInt(k.slice(0,sep)); const pid=k.slice(sep+1);
  const p=pl(ti,pid); if(p) NOTES[ti][p.name]=v;
});

// Aufstellungs-Nummern (befüllt via: python3 aufstellung.py)
const LINEUP_NUMBERS = { 0: new Set(), 1: new Set() };

function cardHTML(p, ti) {
  const info  = `${p.age} / ${p.height} / ${p.nationality}`;
  const cards = `${p.yellow}/${p.yellow_red}/${p.red}`;
  const isTW  = p.pos === 'TW';
  const stat3 = isTW ? `${p.gegentore}GT` : `${p.goals}G`;
  const stat4 = isTW ? `${p.zu_null}ZN`   : `${p.assists}A`;
  const photo = p.photo
    ? `<img src="${p.photo}" alt="${p.last}" draggable="false">`
    : `<span class="nop">&#128100;</span>`;
  const noteText = ((NOTES[ti]||{})[p.name]||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  return `
    <button class="fc-close" title="Entfernen">&#x2715;</button>
    <div class="fc-head hdr-${p.group}">
      <span class="fc-head-num">${p.number}</span>
      <span class="fc-head-name">${p.name} (${p.foot})</span>
      <span class="fc-head-pos">${p.pos}</span>
      <div class="fc-subs">
        <button class="fc-sub sub-out" title="Auswechslung">&#9660;</button>
        <span class="fc-sub-min"></span>
        <button class="fc-sub sub-in"  title="Einwechslung">&#9650;</button>
      </div>
    </div>
    <div class="fc-stats">
      <span class="fc-info">${info}</span>
      <span class="fc-sv">${p.games}</span>
      <span class="fc-sv">${stat3}</span>
      <span class="fc-sv">${stat4}</span>
      <span class="fc-sv">${cards}</span>
    </div>
    <div class="fc-body">
      <div class="fc-photo">${photo}</div>
      <div class="fc-notes"><textarea placeholder="Notizen...">${noteText}</textarea></div>
    </div>
    <div class="fc-transfer">${p.transfer}</div>
    <div class="fc-resize"></div>`;
}

function makeCard(ti, pid, x, y) {
  const p = pl(ti, pid);
  const card = document.createElement('div');
  card.className = 'fc';
  card.dataset.team = String(ti);
  card.dataset.pid  = String(pid);
  card.style.left = x + 'px';
  card.style.top  = y + 'px';
  card.innerHTML = cardHTML(p, ti);

  card.querySelector('.fc-close').addEventListener('pointerdown', e => {
    e.stopPropagation(); removeCard(card);
  });

  function setListSub(state) {
    const row = document.querySelector(`#scroll-${card.dataset.team} .pl-row[data-pid="${card.dataset.pid}"]`);
    if (!row) return;
    const ind = row.querySelector('.pl-sub');
    ind.classList.remove('active','is-out','is-in');
    row.classList.remove('subbed-in');
    const min = getMatchMinute();
    if (state === 'out') { ind.textContent = min ? `▼ ${min}'` : '▼'; ind.classList.add('active','is-out'); }
    if (state === 'in')  { ind.textContent = min ? `▲ ${min}'` : '▲'; ind.classList.add('active','is-in'); row.classList.add('subbed-in'); }
  }
  function updateCardMin(active) {
    const s = card.querySelector('.fc-sub-min');
    if (s) s.textContent = active ? getMatchMinute() : '';
  }
  card.querySelector('.sub-out').addEventListener('pointerdown', e => {
    e.stopPropagation();
    const btn = e.currentTarget;
    const on = !btn.classList.contains('active');
    card.querySelector('.sub-in').classList.remove('active');
    card.classList.remove('is-in');
    btn.classList.toggle('active', on);
    card.classList.toggle('is-out', on);
    setListSub(on ? 'out' : null); updateCardMin(on);
  });
  card.querySelector('.sub-in').addEventListener('pointerdown', e => {
    e.stopPropagation();
    const btn = e.currentTarget;
    const on = !btn.classList.contains('active');
    card.querySelector('.sub-out').classList.remove('active');
    card.classList.remove('is-out');
    btn.classList.toggle('active', on);
    card.classList.toggle('is-in', on);
    setListSub(on ? 'in' : null); updateCardMin(on);
  });

  card.querySelector('textarea').addEventListener('pointerdown', e => e.stopPropagation());
  card.querySelector('textarea').addEventListener('input', e => {
    const _ti=parseInt(card.dataset.team), _pid=card.dataset.pid, _p=pl(_ti,_pid);
    if(_p) NOTES[_ti][_p.name]=e.target.value;
    if(!appState.notes) appState.notes={};
    appState.notes[card.dataset.team+'_'+card.dataset.pid]=e.target.value;
    _saveState();
  });
  card.querySelector('.fc-resize').addEventListener('pointerdown', onResizeDown);
  card.querySelector('.fc-head').addEventListener('pointerdown', e => onCardDown(e, card));
  return card;
}

function removeCard(card) {
  const ti = card.dataset.team, pid = card.dataset.pid;
  if (appState.cards) delete appState.cards[ti+'_'+pid];
  _saveState();
  card.remove();
  const row = document.querySelector(`#scroll-${ti} .pl-row[data-pid="${pid}"]`);
  if (row) { row.classList.remove('on-field', 'fp-hidden'); }
}

TEAMS.forEach((team, ti) => {
  const scroll = document.getElementById(`scroll-${ti}`);
  team.players.forEach(p => {
    const row = document.createElement('div');
    row.className = 'pl-row';
    row.dataset.team = String(ti);
    row.dataset.pid  = String(p.id);
    row.innerHTML = `<span class="pl-dot ${p.group}"></span><span class="pl-num">${p.number}</span><span class="pl-name">${p.name}</span><span class="pl-sub"></span><button class="pl-remove" title="Entfernen">✕</button>`;
    row.addEventListener('pointerdown', onListDown);
    row.querySelector('.pl-remove').addEventListener('pointerdown', e => { e.stopPropagation(); removePlayerRow(row); });
    scroll.appendChild(row);
  });
});

let drag = null;
function onListDown(e) {
  const row = e.currentTarget;
  if (row.classList.contains('on-field')) return;
  e.preventDefault();
  const ti = row.dataset.team, pid = row.dataset.pid;
  const card = makeCard(parseInt(ti), pid, 0, 0);
  card.classList.add('fc-ghost');
  const cw=160, ch=118, offX=cw/2, offY=30;
  card.style.cssText = `position:fixed;left:${e.clientX-offX}px;top:${e.clientY-offY}px;width:${cw}px;height:${ch}px;z-index:9000;pointer-events:none;`;
  document.body.appendChild(card);
  drag = { card, ti, pid, offX, offY, fromList:true, listRow:row };
  document.addEventListener('pointermove', onDragMove, {passive:false});
  document.addEventListener('pointerup', onDragUp);
  document.addEventListener('pointercancel', onDragUp);
}
function onCardDown(e, card) {
  e.preventDefault(); e.stopPropagation();
  const rect = card.getBoundingClientRect();
  const offX = e.clientX-rect.left, offY = e.clientY-rect.top;
  const ti = card.dataset.team, pid = card.dataset.pid;
  card.classList.add('dragging');
  card.style.cssText = `position:fixed;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px;z-index:9000;pointer-events:none;`;
  document.body.appendChild(card);
  drag = { card, ti, pid, offX, offY, fromList:false, origW:rect.width, origH:rect.height };
  document.addEventListener('pointermove', onDragMove, {passive:false});
  document.addEventListener('pointerup', onDragUp);
  document.addEventListener('pointercancel', onDragUp);
}
function onDragMove(e) {
  if (!drag) return; e.preventDefault();
  drag.card.style.left = (e.clientX-drag.offX)+'px';
  drag.card.style.top  = (e.clientY-drag.offY)+'px';
  document.querySelectorAll('.field-zone').forEach(z=>z.classList.remove('drag-over'));
  const zone = document.elementFromPoint(e.clientX,e.clientY)?.closest('.field-zone');
  if (zone && zone.dataset.team===String(drag.ti)) zone.classList.add('drag-over');
}
function onDragUp(e) {
  if (!drag) return;
  document.removeEventListener('pointermove', onDragMove);
  document.removeEventListener('pointerup', onDragUp);
  document.removeEventListener('pointercancel', onDragUp);
  document.querySelectorAll('.field-zone').forEach(z=>z.classList.remove('drag-over'));
  const {card,ti,pid,offX,offY,fromList,origW,origH} = drag; drag=null;
  card.classList.remove('dragging','fc-ghost');
  const zone = document.elementFromPoint(e.clientX,e.clientY)?.closest('.field-zone');
  if (zone && zone.dataset.team===String(ti)) {
    const zr=zone.getBoundingClientRect();
    const cardW=origW||parseInt(card.style.width)||160, cardH=origH||parseInt(card.style.height)||118;
    const x=Math.max(0,Math.min(e.clientX-offX-zr.left,zr.width-cardW));
    const y=Math.max(0,Math.min(e.clientY-offY-zr.top,zr.height-cardH));
    card.style.cssText = `left:${x}px;top:${y}px;width:${cardW}px;height:${cardH}px;`;
    zone.appendChild(card);
    if (fromList) { const row=document.querySelector(`#scroll-${ti} .pl-row[data-pid="${pid}"]`); if(row){ row.classList.add('on-field'); if(viewMode[parseInt(ti)]==='bank') row.classList.add('fp-hidden'); } }
    if (!appState.cards) appState.cards={};
    appState.cards[ti+'_'+pid]={x,y,w:cardW,h:cardH};
    _saveState();
  } else {
    card.remove();
    if (!fromList) {
      const z0=document.getElementById(`field-${ti}`);
      const nc=makeCard(parseInt(ti),pid,20,20);
      if(origW){nc.style.width=origW+'px';nc.style.height=origH+'px';}
      z0.appendChild(nc);
      if (!appState.cards) appState.cards={};
      appState.cards[ti+'_'+pid]={x:20,y:20,w:origW||160,h:origH||118};
      _saveState();
    }
  }
}

let resz=null;
function onResizeDown(e) {
  e.stopPropagation(); e.preventDefault();
  const card=e.currentTarget.closest('.fc');
  resz={card,startX:e.clientX,startY:e.clientY,startW:card.offsetWidth,startH:card.offsetHeight};
  card.style.userSelect='none';
  document.addEventListener('pointermove',onResizeMove,{passive:false});
  document.addEventListener('pointerup',onResizeUp);
  document.addEventListener('pointercancel',onResizeUp);
}
function onResizeMove(e) {
  if(!resz)return; e.preventDefault();
  const {card,startX,startY,startW,startH}=resz;
  card.style.width  = Math.max(100,Math.min(500,startW+e.clientX-startX))+'px';
  card.style.height = Math.max(90, Math.min(500,startH+e.clientY-startY))+'px';
}
function onResizeUp() {
  if(!resz)return;
  const {card:rc}=resz;
  resz.card.style.userSelect='';
  document.removeEventListener('pointermove',onResizeMove);
  document.removeEventListener('pointerup',onResizeUp);
  document.removeEventListener('pointercancel',onResizeUp);
  if(rc.dataset.pid==='__coach__'){
    const _ti=parseInt(rc.dataset.team);
    if(!appState.coach)appState.coach={};
    if(!appState.coach[_ti])appState.coach[_ti]={};
    appState.coach[_ti].pos={x:parseInt(rc.style.left)||0,y:parseInt(rc.style.top)||0,w:rc.offsetWidth,h:rc.offsetHeight};
    _saveState();
  } else {
    const _k=rc.dataset.team+'_'+rc.dataset.pid;
    if(appState.cards&&appState.cards[_k]){appState.cards[_k].w=rc.offsetWidth;appState.cards[_k].h=rc.offsetHeight;_saveState();}
  }
  resz=null;
}

// Spieluhr
let clockInterval=null, clockElapsed=0, clockRunning=false;
function startClock(h) {
  if(clockInterval) clearInterval(clockInterval);
  clockElapsed=h*60; clockRunning=true;
  document.getElementById('btn-0').classList.toggle('active-half',h===0);
  document.getElementById('btn-45').classList.toggle('active-half',h===45);
  const cd=document.getElementById('clock-display');
  cd.classList.add('running'); cd.classList.remove('paused');
  renderClock();
  clockInterval=setInterval(()=>{clockElapsed++;renderClock();},1000);
}
function togglePause() {
  if(!clockRunning) return;
  const cd=document.getElementById('clock-display');
  if(clockInterval) {
    clearInterval(clockInterval); clockInterval=null;
    cd.classList.add('paused');
  } else {
    clockInterval=setInterval(()=>{clockElapsed++;renderClock();},1000);
    cd.classList.remove('paused');
  }
}
function renderClock() {
  const m=Math.floor(clockElapsed/60), s=clockElapsed%60;
  document.getElementById('clock-display').textContent=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
}
function getMatchMinute() {
  if(!clockRunning) return '';
  return (Math.floor(clockElapsed/60)+1)+"'";
}

// Spieler entfernen mit Undo
let _lastRemoved = null, _undoTimer = null;
function removePlayerRow(row) {
  if (_undoTimer) clearTimeout(_undoTimer);
  _lastRemoved = { row, parent: row.parentNode, next: row.nextSibling };
  row.remove();
  document.getElementById('undo-msg').textContent = row.querySelector('.pl-name').textContent + ' entfernt';
  const t = document.getElementById('undo-toast');
  t.classList.add('visible');
  _undoTimer = setTimeout(() => { t.classList.remove('visible'); _lastRemoved = null; }, 4000);
}
function undoRemove() {
  if (!_lastRemoved) return;
  clearTimeout(_undoTimer);
  _lastRemoved.parent.insertBefore(_lastRemoved.row, _lastRemoved.next);
  _lastRemoved = null;
  document.getElementById('undo-toast').classList.remove('visible');
}

// Ansicht: Alle / Bank
const viewMode = {0:'all', 1:'all'};
function setView(ti, mode) {
  viewMode[ti] = mode;
  document.getElementById('vbtn-'+ti+'-all').classList.toggle('active', mode==='all');
  document.getElementById('vbtn-'+ti+'-bank').classList.toggle('active', mode==='bank');
  document.querySelectorAll('#scroll-'+ti+' .pl-row').forEach(function(row) {
    row.classList.toggle('fp-hidden', mode==='bank' && row.classList.contains('on-field'));
  });
}

// ── Trainer-Karte ─────────────────────────────────────────────────────────────
function coachCardHTML(coach) {
  const photo = coach.photo
    ? `<img src="${coach.photo}" alt="${coach.name}" draggable="false">`
    : `<span class="nop">&#128101;</span>`;
  const age = coach.age
    ? `${coach.age}${coach.nationality ? ' &middot; ' + coach.nationality : ''}`
    : '';
  const since = coach.amtsantritt ? `Amtsantritt: ${coach.amtsantritt}` : '';
  return `
    <button class="fc-close" title="Entfernen">&#x2715;</button>
    <div class="fc-head">
      <span class="fc-coach-label">&#128101; MITARBEITER</span>
    </div>
    <div class="fc-coach-body">
      <div class="fc-coach-photo">${photo}</div>
      <div class="fc-coach-info">
        <div class="fc-coach-name">${coach.name}</div>
        <div class="fc-coach-role">${coach.role||'Trainer'}</div>
        ${age ? `<div class="fc-coach-detail">Alter: ${age}</div>` : ''}
        ${since ? `<div class="fc-coach-detail">${since}</div>` : ''}
        ${coach.pps ? `<div class="fc-coach-detail" style="color:#1a3a5c;font-weight:700">&#8709; ${coach.pps} Pkt/Spiel</div>` : ''}
      </div>
    </div>
    <div class="fc-coach-notes"><textarea placeholder="Notizen..."></textarea></div>
    <div class="fc-resize"></div>`;
}

function makeCoachCard(ti, x, y) {
  const coach = TEAMS[ti] && TEAMS[ti].coach;
  if (!coach) return null;
  const card = document.createElement('div');
  card.className = 'fc fc-coach';
  card.dataset.team = String(ti);
  card.dataset.pid  = '__coach__';
  card.style.left = x + 'px';
  card.style.top  = y + 'px';
  card.innerHTML = coachCardHTML(coach);
  // Notizen aus State laden
  const savedNotes = (appState.coach && appState.coach[ti] && appState.coach[ti].notes) || '';
  card.querySelector('textarea').value = savedNotes;
  card.querySelector('.fc-close').addEventListener('pointerdown', e => {
    e.stopPropagation();
    if(!appState.coach)appState.coach={};
    if(!appState.coach[ti])appState.coach[ti]={};
    delete appState.coach[ti].pos;
    _saveState();
    card.remove();
  });
  card.querySelector('textarea').addEventListener('pointerdown', e => e.stopPropagation());
  card.querySelector('textarea').addEventListener('input', e => {
    if(!appState.coach)appState.coach={};
    if(!appState.coach[ti])appState.coach[ti]={};
    appState.coach[ti].notes = e.target.value;
    _saveState();
  });
  card.querySelector('.fc-resize').addEventListener('pointerdown', onResizeDown);
  card.querySelector('.fc-head').addEventListener('pointerdown', e => onCoachCardDown(e, card));
  return card;
}

function onCoachCardDown(e, card) {
  e.preventDefault(); e.stopPropagation();
  const rect = card.getBoundingClientRect();
  const offX = e.clientX-rect.left, offY = e.clientY-rect.top;
  const ti = parseInt(card.dataset.team);
  card.classList.add('dragging');
  card.style.cssText = `position:fixed;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px;z-index:9000;pointer-events:none;`;
  document.body.appendChild(card);
  drag = { card, ti, pid:'__coach__', offX, offY, fromList:false, origW:rect.width, origH:rect.height };
  document.addEventListener('pointermove', onDragMove, {passive:false});
  document.addEventListener('pointerup', onCoachDragUp);
  document.addEventListener('pointercancel', onCoachDragUp);
}

function onCoachDragUp(e) {
  if(!drag)return;
  document.removeEventListener('pointermove', onDragMove);
  document.removeEventListener('pointerup', onCoachDragUp);
  document.removeEventListener('pointercancel', onCoachDragUp);
  document.querySelectorAll('.field-zone').forEach(z=>z.classList.remove('drag-over'));
  const {card, ti, offX, offY, origW, origH} = drag; drag = null;
  card.classList.remove('dragging');
  const zone = document.elementFromPoint(e.clientX, e.clientY)?.closest('.field-zone');
  const ownZone = document.getElementById(`field-${ti}`);
  const cardW = origW || 165, cardH = origH || 150;
  if(zone && parseInt(zone.dataset.team) === ti) {
    const zr = zone.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX-offX-zr.left, zr.width-cardW));
    const y = Math.max(0, Math.min(e.clientY-offY-zr.top, zr.height-cardH));
    card.style.cssText = `left:${x}px;top:${y}px;width:${cardW}px;height:${cardH}px;`;
    zone.appendChild(card);
    if(!appState.coach)appState.coach={};
    if(!appState.coach[ti])appState.coach[ti]={};
    appState.coach[ti].pos = {x, y, w:cardW, h:cardH};
    _saveState();
  } else {
    card.style.cssText = `left:20px;top:20px;width:${cardW}px;height:${cardH}px;`;
    ownZone.appendChild(card);
    if(!appState.coach)appState.coach={};
    if(!appState.coach[ti])appState.coach[ti]={};
    appState.coach[ti].pos = {x:20, y:20, w:cardW, h:cardH};
    _saveState();
  }
}

// Gespeicherte Aufstellung wiederherstellen
Object.entries(appState.cards||{}).forEach(([key,pos]) => {
  const sep=key.indexOf('_'); const ti=parseInt(key.slice(0,sep)); const pid=key.slice(sep+1);
  const p=pl(ti,pid); if(!p) return;
  const zone=document.getElementById('field-'+ti); if(!zone) return;
  const card=makeCard(ti,pid,pos.x,pos.y);
  card.style.width=pos.w+'px'; card.style.height=pos.h+'px';
  zone.appendChild(card);
  const row=document.querySelector('#scroll-'+ti+' .pl-row[data-pid="'+pid+'"]');
  if(row){row.classList.add('on-field'); if(viewMode[ti]==='bank') row.classList.add('fp-hidden');}
});

// ── Live-Sync (alle 3 Sekunden vom Server holen) ──────────────────────────────
function _applyRemoteState(remote) {
  if (!remote || remote.notes === undefined) return;
  // Karten platzieren / verschieben
  Object.entries(remote.cards || {}).forEach(([key, pos]) => {
    const sep=key.indexOf('_'), ti=parseInt(key.slice(0,sep)), pid=key.slice(sep+1);
    const zone=document.getElementById('field-'+ti); if(!zone) return;
    const existing=zone.querySelector('.fc[data-pid="'+pid+'"]');
    if (existing) {
      existing.style.left=pos.x+'px'; existing.style.top=pos.y+'px';
      existing.style.width=pos.w+'px'; existing.style.height=pos.h+'px';
    } else {
      const p=pl(ti,pid); if(!p) return;
      const card=makeCard(ti,pid,pos.x,pos.y);
      card.style.width=pos.w+'px'; card.style.height=pos.h+'px';
      zone.appendChild(card);
      const row=document.querySelector('#scroll-'+ti+' .pl-row[data-pid="'+pid+'"]');
      if(row){row.classList.add('on-field');if(viewMode[ti]==='bank')row.classList.add('fp-hidden');}
    }
  });
  // Karten entfernen die nicht mehr da sind
  document.querySelectorAll('.field-zone .fc:not(.fc-coach)').forEach(card => {
    const key=card.dataset.team+'_'+card.dataset.pid;
    if(!(remote.cards||{})[key]){
      const row=document.querySelector('#scroll-'+card.dataset.team+' .pl-row[data-pid="'+card.dataset.pid+'"]');
      if(row) row.classList.remove('on-field','fp-hidden','subbed-in');
      card.remove();
    }
  });
  // Notizen (nur wenn nicht gerade getippt wird)
  Object.entries(remote.notes||{}).forEach(([key,val]) => {
    const sep=key.indexOf('_'), ti=parseInt(key.slice(0,sep)), pid=key.slice(sep+1);
    const card=document.querySelector('.field-zone[data-team="'+ti+'"] .fc[data-pid="'+pid+'"]');
    if(card){const ta=card.querySelector('textarea');if(ta&&ta!==document.activeElement)ta.value=val;}
  });
  // Trainer-Karten
  Object.entries(remote.coach||{}).forEach(([ti,data]) => {
    if(!data||!data.pos) return;
    const existing=document.getElementById('field-'+ti)?.querySelector('.fc-coach');
    if(existing){
      existing.style.left=data.pos.x+'px'; existing.style.top=data.pos.y+'px';
      existing.style.width=(data.pos.w||165)+'px'; existing.style.height=(data.pos.h||150)+'px';
      if(data.notes!==undefined){const ta=existing.querySelector('textarea');if(ta&&ta!==document.activeElement)ta.value=data.notes;}
    }
  });
  Object.assign(appState, remote);
  _lastSyncHash = JSON.stringify(appState);
}
if (IS_SERVER) {
  setInterval(async () => {
    try {
      const r = await fetch('/api/state?key='+encodeURIComponent(MATCH_KEY));
      const remote = await r.json();
      const h = JSON.stringify(remote);
      if (h !== _lastSyncHash) _applyRemoteState(remote);
    } catch(e) {}
  }, 3000);
}

// Trainer-Karten platzieren
TEAMS.forEach((team, ti) => {
  if(!team.coach) return;
  const zone = document.getElementById(`field-${ti}`);
  const saved = appState.coach && appState.coach[ti] && appState.coach[ti].pos;
  const w = (saved && saved.w) || 165;
  const h = (saved && saved.h) || 150;
  let x, y;
  if(saved) {
    x = saved.x; y = saved.y;
  } else {
    const zr = zone.getBoundingClientRect();
    x = Math.max(0, Math.floor((zr.width - w) / 2));
    y = Math.max(0, zr.height - h - 10);
  }
  const card = makeCoachCard(ti, x, y);
  if(!card) return;
  card.style.width = w + 'px';
  card.style.height = h + 'px';
  zone.appendChild(card);
});

</script>
</body>
</html>
'''


def generate_taktikboard(team0_name, team0_players, team0_coach,
                          team1_name, team1_players, team1_coach,
                          saison, output_path):
    """Baut die Taktikboard-HTML-Datei fuer zwei Teams und schreibt sie nach
    output_path. team*_players muessen bereits durch build_players() gelaufen
    sein, team*_coach ist ein Dict (photo bereits durch photo_b64) oder None."""
    teams_data = [
        {'name': team0_name, 'players': team0_players, 'coach': team0_coach},
        {'name': team1_name, 'players': team1_players, 'coach': team1_coach},
    ]
    html = HTML
    html = html.replace('__TEAM0__', team0_name)
    html = html.replace('__TEAM1__', team1_name)
    html = html.replace('__DATA__', json.dumps(teams_data, ensure_ascii=False))

    t0 = team0_name.replace(' ', '_')
    t1 = team1_name.replace(' ', '_')
    html = html.replace('__MATCH_KEY__', f'taktikboard_{t0}_vs_{t1}_{saison}')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path
