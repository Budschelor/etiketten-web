#!/usr/bin/env python3
"""
Spieltage
=========
Holt Spielpläne von OpenLigaDB (kostenlose, offizielle Fußball-Datenbank,
kein Login nötig) -- für 1./2./3. Liga und DFB-Pokal. Liefert dieselben
Begegnungen und Anstoßzeiten wie kicker.de -- kicker.de selbst blockiert
automatisierte Abrufe (Bot-Schutz), OpenLigaDB nicht.

Beim Pokal heißen die "Spieltage" Runden (1. Runde, Achtelfinale, ...) --
darum immer erst get_gruppen() abfragen, um die gültigen Nummern + Namen für
einen Wettbewerb zu bekommen, statt eine feste Spieltag-Anzahl anzunehmen.
"""
import requests
from datetime import datetime

WETTBEWERBE = {
    'bl1': '1. Bundesliga',
    'bl2': '2. Bundesliga',
    'bl3': '3. Liga',
    'dfb': 'DFB-Pokal',
}

# Bevorzugter Transfermarkt-Wettbewerbscode für die Saisonstatistik-Anzeige
# (siehe scraper.detect_wettbewerb) -- beim Pokal kann der Gegner aus jeder
# Liga kommen, L1 ist da nur ein vernünftiger Standard-Tie-Break.
TM_PREFERRED = {'bl1': 'L1', 'bl2': 'L2', 'bl3': 'L3', 'dfb': 'L1'}

HANSA_NAMES = ('hansa rostock', 'fc hansa rostock')


def determine_season():
    """Aktuelle Saison bestimmen (Saison beginnt im Sommer)."""
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1


def get_gruppen(wettbewerb, saison=None):
    """Verfügbare Spieltage/Runden eines Wettbewerbs.
    Gibt Liste von Dicts zurück: {'nr', 'name'} (z.B. {'nr':1,'name':'1. Runde'})."""
    saison = saison or determine_season()
    url = f'https://api.openligadb.de/getavailablegroups/{wettbewerb}/{saison}'
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    return [{'nr': g['groupOrderID'], 'name': g['groupName']}
            for g in sorted(data, key=lambda g: g['groupOrderID'])]


def get_spiele(wettbewerb, nr, saison=None):
    """Alle Begegnungen eines Spieltags/einer Runde.
    Gibt Liste von Dicts zurück: {'heim', 'gast', 'anstoss' (datetime|None)}."""
    saison = saison or determine_season()
    url = f'https://api.openligadb.de/getmatchdata/{wettbewerb}/{saison}/{nr}'
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    spiele = []
    for m in data:
        try:
            anstoss = datetime.fromisoformat(m['matchDateTime'])
        except (KeyError, ValueError, TypeError):
            anstoss = None
        spiele.append({
            'heim': m['team1']['teamName'],
            'gast': m['team2']['teamName'],
            'anstoss': anstoss,
        })
    spiele.sort(key=lambda s: s['anstoss'] or datetime.max)
    return spiele


def ist_hansa_spiel(spiel):
    """Rein kosmetisch fürs Hervorheben in der Liste -- filtert nicht."""
    return any(n in spiel['heim'].lower() for n in HANSA_NAMES) \
        or any(n in spiel['gast'].lower() for n in HANSA_NAMES)


if __name__ == '__main__':
    import sys
    wettbewerb = sys.argv[1] if len(sys.argv) > 1 else 'bl3'
    nr = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    saison = determine_season()
    print(f'\n{WETTBEWERBE.get(wettbewerb, wettbewerb)}, Saison {saison}/{saison+1}:\n')
    gruppen = get_gruppen(wettbewerb, saison)
    match = next((g for g in gruppen if g['nr'] == nr), None)
    print(f"  Runde/Spieltag: {match['name'] if match else nr}\n")
    for s in get_spiele(wettbewerb, nr, saison):
        zeit = s['anstoss'].strftime('%a %d.%m. %H:%M') if s['anstoss'] else '?'
        marker = ' *HANSA*' if ist_hansa_spiel(s) else ''
        print(f"  {zeit}  {s['heim']} - {s['gast']}{marker}")
