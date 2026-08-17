#!/usr/bin/env python3
"""
Vereins-Auflösung
=================
Ordnet einen Vereinsnamen (z.B. von OpenLigaDB: "SV Waldhof Mannheim") dem
passenden Transfermarkt-Link zu -- über Transfermarkts eigene Schnellsuche.

Das funktioniert für alle Wettbewerbe gleichermaßen (1./2./3. Liga, DFB-Pokal):
Beim Pokal kann der Gegner aus jeder Liga kommen (bis runter zur Regionalliga),
darum lohnt sich keine feste Vereinsliste pro Liga mehr -- die Schnellsuche
deckt automatisch alles ab.

Hansa Rostock bleibt zusätzlich fest hinterlegt (FALLBACK_TEAMS) als schneller,
garantiert richtiger Pfad und Absicherung falls die Suche kurz mal hakt.
"""
import re

from bs4 import BeautifulSoup

from scraper import make_session

SEARCH_URL = 'https://www.transfermarkt.de/schnellsuche/ergebnis/schnellsuche'

FALLBACK_TEAMS = {
    'hansa rostock': ('FC Hansa Rostock', 'https://www.transfermarkt.de/fc-hansa-rostock/startseite/verein/30'),
}

# Junioren-/Nachwuchsteams werden bei der Auswahl übersprungen, außer die
# Anfrage selbst verlangt explizit danach (z.B. eine echte U19-Begegnung).
JUGEND_TOKENS = ('u17', 'u19', 'u21', 'u23', 'jugend', 'akademie', 'fussballschule', 'nachwuchs')


class ClubNotFound(Exception):
    pass


def _fold(s):
    s = s.lower().replace('.', '')
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        s = s.replace(a, b)
    return ' '.join(s.split())


def _search_query(name):
    """Transfermarkts Schnellsuche liefert bei einem führenden '1. '/'1 '
    (z.B. '1. FC Saarbrücken', '1. FC Köln') fälschlich kein Ergebnis --
    dafür für die Suche selbst weglassen, für den Namensabgleich aber die
    Original-Schreibweise behalten."""
    return re.sub(r'^1\.?\s+', '', name.strip())


def _slug(display_name):
    return display_name.replace(' ', '_').replace('.', '').replace('/', '-')


def _is_jugendteam(name):
    folded = _fold(name)
    return any(tok in folded for tok in JUGEND_TOKENS)


def search_club(name, session=None):
    """Sucht einen Verein über Transfermarkts Schnellsuche.
    Gibt Liste von (anzeigename, tm_url) zurück, in TM-Relevanz-Reihenfolge."""
    session = session or make_session()
    r = session.get(SEARCH_URL, params={'query': name}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'lxml')

    results = []
    seen = set()
    for a in soup.select('a[href*="/startseite/verein/"]'):
        href = a.get('href', '')
        text = a.get_text(strip=True)
        m = re.search(r'/([^/]+)/startseite/verein/(\d+)', href)
        if not text or not m or href in seen:
            continue
        seen.add(href)
        slug, vid = m.group(1), m.group(2)
        results.append((text, f'https://www.transfermarkt.de/{slug}/startseite/verein/{vid}'))
    return results


def resolve_club(name):
    """Findet zu einem Vereinsnamen (z.B. von OpenLigaDB) den Transfermarkt-Link.
    Gibt (anzeigename, tm_url, ordner_slug) zurück oder wirft ClubNotFound."""
    key = _fold(name)

    for fname, (display, url) in FALLBACK_TEAMS.items():
        if _fold(fname) in key or key in _fold(fname):
            return display, url, _slug(display)

    try:
        results = search_club(_search_query(name))
    except Exception as e:
        raise ClubNotFound(
            f"Transfermarkt ist gerade nicht erreichbar -- '{name}' konnte "
            f"nicht zugeordnet werden. Bitte später erneut versuchen."
        ) from e
    if not results:
        raise ClubNotFound(f"Verein '{name}' wurde bei Transfermarkt nicht gefunden.")

    # Bevorzugt: exakter Namenstreffer, der kein Nachwuchsteam ist. Sonst der
    # erste nicht-Nachwuchs-Treffer -- Transfermarkts eigene Sortierung ist
    # bereits nach Relevanz. Fragt die Anfrage selbst nach einem Nachwuchsteam
    # (z.B. "U19"), zählt die Nachwuchs-Sperre nicht.
    anfrage_ist_jugend = _is_jugendteam(name)
    exakt = [r for r in results if _fold(r[0]) == key]
    fuer_auswahl = exakt or results

    for text, url in fuer_auswahl:
        if anfrage_ist_jugend or not _is_jugendteam(text):
            return text, url, _slug(text)

    text, url = fuer_auswahl[0]
    return text, url, _slug(text)


if __name__ == '__main__':
    import sys
    name = ' '.join(sys.argv[1:]) or 'Hansa Rostock'
    try:
        display, url, slug = resolve_club(name)
        print(f"'{name}' -> {display}\n  {url}\n  Ordner: {slug}")
    except ClubNotFound as e:
        print(f'Nicht gefunden: {e}')
