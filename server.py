#!/usr/bin/env python3
"""
Etiketten-Web -- Spieleretiketten & Taktikboard fuer die Redaktion.
Start lokal:  python3 server.py  ->  http://localhost:5050

Ablauf: Wettbewerb waehlen (1./2./3. Liga oder DFB-Pokal) -> Spieltag/Runde
waehlen -> Paarung aus der Liste anklicken -> im Hintergrund werden die
Kader beider Teams von Transfermarkt geladen (Saison wird aus dem heutigen
Datum bestimmt, siehe spieltage.determine_season), zwei Word-Etiketten-
Dateien + ein Taktikboard gebaut und als ZIP zum Download angeboten.
"""
import os
import re
import tempfile
import threading
import time
import uuid
import zipfile

import requests
from flask import Flask, request, jsonify, send_file

import spieltage
import teams
from scraper import collect_team_data, get_coach_info
from docx_generator import generate_etiketten
from taktikboard import build_players, build_coach, generate_taktikboard

MAX_VERSUCHE = 3


def _mit_wiederholung(fn, job_id, label):
    """Ruft fn() auf und versucht es bei einem Netzwerk-Timeout/-Fehler bis zu
    MAX_VERSUCHE Mal erneut -- Transfermarkt ist gelegentlich kurz instabil,
    Kollegen sollen dafuer nicht selbst neu starten muessen."""
    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            return fn()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if versuch == MAX_VERSUCHE:
                raise
            _set_job(job_id, message=f'{label} -- Transfermarkt antwortet gerade langsam, '
                                      f'Versuch {versuch + 1}/{MAX_VERSUCHE} ...')
            time.sleep(5)


app = Flask(__name__)

JOBS = {}
JOBS_LOCK = threading.Lock()


def _safe_slug(name):
    s = re.sub(r'[^A-Za-z0-9_-]+', '_', name.strip())
    return s.strip('_') or 'Team'


def _set_job(job_id, **fields):
    with JOBS_LOCK:
        JOBS[job_id].update(fields)


def _run_job(job_id, wettbewerb, nr, heim_name, gast_name, saison):
    try:
        tm_preferred = spieltage.TM_PREFERRED.get(wettbewerb, 'L1')

        _set_job(job_id, message=f'Ordne Vereine zu ({heim_name}, {gast_name}) ...')
        heim = teams.resolve_club(heim_name)
        gast = teams.resolve_club(gast_name)

        work_dir = tempfile.mkdtemp(prefix='etiketten_')
        wb_slug = _safe_slug(spieltage.WETTBEWERBE.get(wettbewerb, wettbewerb))
        folder_name = f'{wb_slug}_{nr:02d}_{_safe_slug(heim[0])}_vs_{_safe_slug(gast[0])}'
        out_dir = os.path.join(work_dir, folder_name)
        os.makedirs(out_dir, exist_ok=True)

        teams_taktik = []
        for name, url, slug in (heim, gast):
            _set_job(job_id, message=f'Lade Kader {name} von Transfermarkt ...')
            photo_dir = os.path.join(work_dir, 'fotos', slug)
            players_raw = _mit_wiederholung(
                lambda url=url, photo_dir=photo_dir: collect_team_data(
                    url, saison=saison, photo_dir=photo_dir, wettbewerb=tm_preferred),
                job_id, f'Lade Kader {name}')

            _set_job(job_id, message=f'Baue Etiketten fuer {name} ...')
            docx_path = os.path.join(out_dir, f'Etiketten_{_safe_slug(name)}_{saison}.docx')
            generate_etiketten(players_raw, docx_path, team_name=name)

            _set_job(job_id, message=f'Lade Trainer {name} ...')
            coach_raw = _mit_wiederholung(
                lambda url=url, photo_dir=photo_dir: get_coach_info(
                    url, photo_dir=photo_dir, wettbewerb=tm_preferred),
                job_id, f'Lade Trainer {name}')

            teams_taktik.append((name, build_players(players_raw), build_coach(coach_raw)))

        _set_job(job_id, message='Baue Taktikboard ...')
        (t0_name, t0_players, t0_coach), (t1_name, t1_players, t1_coach) = teams_taktik
        taktik_path = os.path.join(out_dir, f'Taktikboard_{_safe_slug(t0_name)}_vs_{_safe_slug(t1_name)}_{saison}.html')
        generate_taktikboard(t0_name, t0_players, t0_coach, t1_name, t1_players, t1_coach, saison, taktik_path)

        _set_job(job_id, message='Packe ZIP-Datei ...')
        zip_path = os.path.join(work_dir, f'{folder_name}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(out_dir):
                zf.write(os.path.join(out_dir, fname), arcname=os.path.join(folder_name, fname))

        _set_job(job_id, state='done', message='Fertig!', zip_path=zip_path,
                  zip_name=f'{folder_name}.zip')
    except teams.ClubNotFound as e:
        _set_job(job_id, state='error', message=str(e))
    except Exception as e:
        _set_job(job_id, state='error', message=f'Unerwarteter Fehler: {e}')


PAGE = '''
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spieleretiketten-Generator</title>
<style>
  :root {
    --navy: #0e2a4d; --navy-light: #1c4a82; --blue: #2f6fed; --blue-dark: #1f56c4;
    --green: #16a34a; --green-dark: #128a3e;
    --ink: #101828; --muted: #667085; --border: #e4e7ec;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: radial-gradient(circle at top, #eef2fb 0%, #e3e8f4 100%);
    color: var(--ink); min-height: 100vh; margin: 0;
    display: flex; justify-content: center; padding: 56px 20px 80px; line-height: 1.5;
  }
  .wrap { width: 100%; max-width: 560px; }
  .eyebrow {
    display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700;
    color: var(--navy-light); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px;
  }
  h1 {
    font-size: 28px; font-weight: 800; margin: 0 0 10px; letter-spacing: -0.02em; color: var(--navy);
  }
  .intro { color: var(--muted); font-size: 14.5px; margin: 0 0 28px; max-width: 56ch; }
  .panel {
    background: #fff; border: 1px solid var(--border); border-radius: 20px; padding: 28px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04), 0 12px 32px rgba(16,24,40,0.08);
  }
  form { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
  .field { display: flex; flex-direction: column; gap: 6px; flex: 1 1 160px; }
  label { font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  select {
    font-size: 15px; padding: 12px 14px; border: 1.5px solid var(--border); border-radius: 12px;
    background: #f9fafb; appearance: none; cursor: pointer; width: 100%;
    transition: border-color .15s, box-shadow .15s;
  }
  select:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px rgba(47,111,237,0.15); }
  button {
    cursor: pointer; font-size: 15px; font-weight: 700; border: none; border-radius: 12px;
    padding: 12px 22px; transition: transform .1s, background .15s, box-shadow .15s; white-space: nowrap;
  }
  button:disabled { opacity: .45; cursor: default; }
  button:active:not(:disabled) { transform: translateY(1px); }
  #load-btn { background: var(--navy); color: #fff; box-shadow: 0 4px 14px rgba(14,42,77,0.28); }
  #load-btn:hover:not(:disabled) { background: var(--navy-light); }

  #matches { margin-top: 22px; display: none; }
  .match-row {
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
    padding: 13px 14px; border-radius: 12px; border: 1.5px solid var(--border);
    margin-bottom: 8px; cursor: pointer; font-size: 14.5px; font-weight: 600;
    transition: border-color .12s, background .12s;
  }
  .match-row:hover { border-color: var(--blue); }
  .match-row.selected { border-color: var(--blue); background: #eef4ff; }
  .match-row.hansa { background: #fdf3e7; border-color: #e8b975; }
  .match-row.hansa.selected { background: #eef4ff; border-color: var(--blue); }
  .match-row .teams { display: flex; align-items: center; gap: 8px; }
  .match-row .vs { color: var(--muted); font-weight: 500; font-size: 13px; }
  .match-row .zeit { color: var(--muted); font-weight: 500; font-size: 12.5px; white-space: nowrap; }

  #gen-btn { background: var(--blue); color: #fff; margin-top: 8px; width: 100%; display: none;
    box-shadow: 0 4px 14px rgba(47,111,237,0.3); }
  #gen-btn:hover:not(:disabled) { background: var(--blue-dark); }

  #status { margin-top: 16px; font-size: 13.5px; color: var(--muted); min-height: 18px; }
  #status.error { color: #d92d20; font-weight: 600; }
  #download { display: none; margin-top: 16px; }
  #download a {
    display: block; text-align: center; background: var(--green); color: #fff; text-decoration: none;
    padding: 13px 22px; border-radius: 12px; font-weight: 700; box-shadow: 0 4px 14px rgba(22,163,74,0.3);
    transition: background .15s;
  }
  #download a:hover { background: var(--green-dark); }
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">⚽ Spielvorbereitung</div>
  <h1>Spieleretiketten-Generator</h1>
  <p class="intro">Wettbewerb, Spieltag und Paarung auswählen – ein Klick erstellt die
  Etiketten für beide Teams und das Taktikboard, fertig zum Download.</p>

  <div class="panel">
    <form id="f-auswahl">
      <div class="field">
        <label for="wettbewerb">Wettbewerb</label>
        <select id="wettbewerb">
          <option value="bl1">1. Bundesliga</option>
          <option value="bl2">2. Bundesliga</option>
          <option value="bl3" selected>3. Liga</option>
          <option value="dfb">DFB-Pokal</option>
        </select>
      </div>
      <div class="field">
        <label for="spieltag">Spieltag / Runde</label>
        <select id="spieltag"></select>
      </div>
      <button type="submit" id="load-btn">Spielplan laden</button>
    </form>

    <div id="matches"></div>

    <div id="status"></div>
    <button id="gen-btn">Etiketten &amp; Taktikboard erstellen</button>
    <div id="download"></div>
  </div>
</div>

<script>
const wettbewerbSel = document.getElementById('wettbewerb');
const spieltagSel = document.getElementById('spieltag');
const loadBtn = document.getElementById('load-btn');
const genBtn = document.getElementById('gen-btn');
const statusEl = document.getElementById('status');
const matchesEl = document.getElementById('matches');
const downloadEl = document.getElementById('download');
let currentWettbewerb = null;
let currentNr = null;
let selectedMatch = null;
let pollTimer = null;

function setStatus(msg, isError) {
  statusEl.textContent = msg || '';
  statusEl.classList.toggle('error', !!isError);
}

async function ladeGruppen() {
  spieltagSel.innerHTML = '<option>lädt ...</option>';
  loadBtn.disabled = true;
  try {
    const r = await fetch(`/api/gruppen/${wettbewerbSel.value}`);
    const data = await r.json();
    spieltagSel.innerHTML = '';
    (data.gruppen || []).forEach(g => {
      const o = document.createElement('option');
      o.value = g.nr; o.textContent = g.name;
      spieltagSel.appendChild(o);
    });
  } finally {
    loadBtn.disabled = false;
  }
}
wettbewerbSel.addEventListener('change', ladeGruppen);
ladeGruppen();

document.getElementById('f-auswahl').addEventListener('submit', async (e) => {
  e.preventDefault();
  clearInterval(pollTimer);
  downloadEl.style.display = 'none';
  genBtn.style.display = 'none';
  matchesEl.style.display = 'none';
  matchesEl.innerHTML = '';
  selectedMatch = null;
  loadBtn.disabled = true;
  setStatus('Lade Spielplan ...');
  currentWettbewerb = wettbewerbSel.value;
  currentNr = spieltagSel.value;
  try {
    const r = await fetch(`/api/spiele/${currentWettbewerb}/${currentNr}`);
    const data = await r.json();
    if (!r.ok) { setStatus(data.error || 'Fehler beim Laden.', true); return; }
    if (!data.spiele || !data.spiele.length) {
      setStatus('Für diese Runde stehen die Paarungen noch nicht fest.');
      return;
    }
    setStatus('');
    data.spiele.forEach(s => {
      const row = document.createElement('div');
      row.className = 'match-row' + (s.ist_hansa ? ' hansa' : '');
      row.innerHTML = `<div class="teams">${s.heim}<span class="vs">–</span>${s.gast}</div><div class="zeit">${s.anstoss}</div>`;
      row.addEventListener('click', () => {
        document.querySelectorAll('.match-row').forEach(el => el.classList.remove('selected'));
        row.classList.add('selected');
        selectedMatch = {heim: s.heim, gast: s.gast};
        genBtn.style.display = 'block';
        downloadEl.style.display = 'none';
        setStatus('');
      });
      matchesEl.appendChild(row);
    });
    matchesEl.style.display = 'block';
  } catch (err) {
    setStatus('Verbindungsfehler: ' + err, true);
  } finally {
    loadBtn.disabled = false;
  }
});

genBtn.addEventListener('click', async () => {
  if (!selectedMatch) return;
  genBtn.disabled = true;
  downloadEl.style.display = 'none';
  setStatus('Starte ...');
  try {
    const r = await fetch('/api/generate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({wettbewerb: currentWettbewerb, nr: currentNr,
                             heim: selectedMatch.heim, gast: selectedMatch.gast})
    });
    const data = await r.json();
    if (!r.ok) { setStatus(data.error || 'Fehler beim Start.', true); genBtn.disabled = false; return; }
    pollStatus(data.job_id);
  } catch (err) {
    setStatus('Verbindungsfehler: ' + err, true);
    genBtn.disabled = false;
  }
});

function pollStatus(jobId) {
  pollTimer = setInterval(async () => {
    const r = await fetch(`/api/status/${jobId}`);
    const data = await r.json();
    setStatus(data.message || '');
    if (data.state === 'done') {
      clearInterval(pollTimer);
      genBtn.disabled = false;
      downloadEl.innerHTML = `<a href="/api/download/${jobId}">ZIP herunterladen (${data.zip_name})</a>`;
      downloadEl.style.display = 'block';
    } else if (data.state === 'error') {
      clearInterval(pollTimer);
      genBtn.disabled = false;
      setStatus(data.message, true);
    }
  }, 3000);
}
</script>
</body>
</html>
'''


@app.route('/')
def index():
    return PAGE


@app.route('/api/gruppen/<wettbewerb>')
def api_gruppen(wettbewerb):
    if wettbewerb not in spieltage.WETTBEWERBE:
        return jsonify({'error': 'Unbekannter Wettbewerb.'}), 400
    saison = spieltage.determine_season()
    try:
        gruppen = spieltage.get_gruppen(wettbewerb, saison)
    except Exception as e:
        return jsonify({'error': f'Spielplan konnte nicht geladen werden: {e}'}), 502
    return jsonify({'gruppen': gruppen})


@app.route('/api/spiele/<wettbewerb>/<int:nr>')
def api_spiele(wettbewerb, nr):
    if wettbewerb not in spieltage.WETTBEWERBE:
        return jsonify({'error': 'Unbekannter Wettbewerb.'}), 400
    saison = spieltage.determine_season()
    try:
        spiele = spieltage.get_spiele(wettbewerb, nr, saison)
    except Exception as e:
        return jsonify({'error': f'Spielplan konnte nicht geladen werden: {e}'}), 502

    out = [{
        'heim': s['heim'], 'gast': s['gast'],
        'anstoss': s['anstoss'].strftime('%a %d.%m. %H:%M') if s['anstoss'] else '?',
        'ist_hansa': spieltage.ist_hansa_spiel(s),
    } for s in spiele]
    return jsonify({'spiele': out})


@app.route('/api/generate', methods=['POST'])
def api_generate():
    payload = request.get_json(force=True) or {}
    wettbewerb = payload.get('wettbewerb')
    heim = (payload.get('heim') or '').strip()
    gast = (payload.get('gast') or '').strip()
    try:
        nr = int(payload.get('nr'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Ungültiger Spieltag.'}), 400
    if wettbewerb not in spieltage.WETTBEWERBE or not heim or not gast:
        return jsonify({'error': 'Wettbewerb, Heim- und Gastteam werden benötigt.'}), 400

    saison = str(spieltage.determine_season())
    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {'state': 'running', 'message': 'Gestartet ...'}
    threading.Thread(target=_run_job, args=(job_id, wettbewerb, nr, heim, gast, saison), daemon=True).start()
    return jsonify({'job_id': job_id})


@app.route('/api/status/<job_id>')
def api_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({'error': 'Unbekannter Job.'}), 404
    return jsonify({k: v for k, v in job.items() if k != 'zip_path'})


@app.route('/api/download/<job_id>')
def api_download(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or job.get('state') != 'done':
        return jsonify({'error': 'Datei ist noch nicht fertig.'}), 404
    return send_file(job['zip_path'], as_attachment=True, download_name=job['zip_name'])


if __name__ == '__main__':
    app.run(port=5050, debug=True)
