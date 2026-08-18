"""
Transfermarkt Scraper
Holt alle Spielerdaten (Kader, Stats, Profil, Transfers) für einen Verein.
"""
import requests
import warnings
import time
import re
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.transfermarkt.de/',
    'Connection': 'keep-alive',
}

# Ländernamen (wie TM sie nennt) → 3-Buchstaben-Kürzel
COUNTRY_CODES = {
    'Deutschland': 'DEU', 'Frankreich': 'FRA', 'Spanien': 'ESP',
    'Italien': 'ITA', 'England': 'ENG', 'Portugal': 'POR',
    'Niederlande': 'NED', 'Belgien': 'BEL', 'Österreich': 'AUT',
    'Schweiz': 'SUI', 'Polen': 'POL', 'Tschechien': 'CZE',
    'Slowakei': 'SVK', 'Ungarn': 'HUN', 'Kroatien': 'CRO',
    'Serbien': 'SRB', 'Slowenien': 'SVN', 'Rumänien': 'ROU',
    'Bulgarien': 'BUL', 'Griechenland': 'GRE', 'Türkei': 'TUR',
    'Ukraine': 'UKR', 'Russland': 'RUS', 'Schweden': 'SWE',
    'Norwegen': 'NOR', 'Dänemark': 'DEN', 'Finnland': 'FIN',
    'Island': 'ISL', 'Schottland': 'SCO', 'Wales': 'WAL',
    'Irland': 'IRL', 'USA': 'USA', 'Kanada': 'CAN',
    'Brasilien': 'BRA', 'Argentinien': 'ARG', 'Mexiko': 'MEX',
    'Kolumbien': 'COL', 'Chile': 'CHI', 'Uruguay': 'URU',
    'Japan': 'JPN', 'Südkorea': 'KOR', 'China': 'CHN',
    'Australien': 'AUS', 'Nigeria': 'NGA', 'Ghana': 'GHA',
    'Kamerun': 'CMR', 'Senegal': 'SEN', 'Marokko': 'MAR',
    'Tunesien': 'TUN', 'Ägypten': 'EGY', 'Elfenbeinküste': 'CIV',
    'Kosovo': 'KOS', 'Albanien': 'ALB', 'Nordmazedonien': 'MKD',
    'Bosnien-Herzegowina': 'BIH', 'Montenegro': 'MNE',
    'Estland': 'EST', 'Lettland': 'LVA', 'Litauen': 'LTU',
    'Weißrussland': 'BLR', 'Moldau': 'MDA', 'Georgien': 'GEO',
    'Armenien': 'ARM', 'Aserbaidschan': 'AZE', 'Kasachstan': 'KAZ',
    'Iran': 'IRN', 'Saudi-Arabien': 'KSA', 'Israel': 'ISR',
    'Kap Verde': 'CPV', 'Guinea': 'GUI', 'Mali': 'MLI',
    'Kongo DR': 'COD', 'Angola': 'ANG', 'Sambia': 'ZAM',
    'Jamaika': 'JAM', 'Trinidad und Tobago': 'TTO',
    'Honduras': 'HON', 'Costa Rica': 'CRC', 'Panama': 'PAN',
    'Venezuela': 'VEN', 'Peru': 'PER', 'Ecuador': 'ECU',
    'Bolivien': 'BOL', 'Paraguay': 'PAR', 'Nordirland': 'NIR',
    'Luxemburg': 'LUX', 'Malta': 'MLT', 'Zypern': 'CYP',
    'Färöer Inseln': 'FRO', 'Guinea-Bissau': 'GNB',
    'Guinea-Bissau': 'GNB', 'Mosambik': 'MOZ',
}

WETTBEWERB_LIGA_NAMES = {
    'L3': '3. Liga',
    'L2': '2. Bundesliga',
    'L1': 'Bundesliga',
    'GB1': 'Premier League',
    'ES1': 'LaLiga',
    'IT1': 'Serie A',
    'FR1': 'Ligue 1',
    'NL1': 'Eredivisie',
    'A1':  'Bundesliga (A)',
    'RU1': 'Premier Liga',
    'TR1': 'Süper Lig',
}

FOOT_MAP = {
    'rechts': 'R', 'links': 'L', 'beide': 'B',
    'right': 'R', 'left': 'L', 'both': 'B',
}


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get_soup(session, url, delay=1.0):
    """Seite laden und als BeautifulSoup zurückgeben."""
    time.sleep(delay)
    r = session.get(url, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.content, 'lxml')


def extract_player_id(href):
    """Spieler-ID aus TM-URL extrahieren: /name/profil/spieler/12345 → 12345"""
    m = re.search(r'/spieler/(\d+)', href or '')
    return m.group(1) if m else None


def clean_name(cell):
    """
    Holt den vollen Spielernamen aus einer TM-Tabellenzelle.
    Nutzt den Spielerprofil-Link als primäre Quelle (robuster als span.hide-for-small,
    da Leihspieler dort ein Vereinswappen statt des Namens haben).
    """
    # Primär: Link mit /spieler/ in href → title-Attribut ist immer der volle Name
    for a in cell.find_all('a', href=True):
        if '/spieler/' in a.get('href', ''):
            title = a.get('title', '').strip()
            if title:
                return title
            text = a.get_text(strip=True)
            if text:
                return text
    # Fallback: span.hide-for-small (für Leihspieler ohne /spieler/ link)
    span = cell.find('span', class_='hide-for-small')
    if span:
        a = span.find('a')
        if a:
            return a.get_text(strip=True)
    # Letzter Fallback: img title
    img = cell.find('img', title=True)
    if img:
        return img.get('title', '').strip()
    return ''


def get_squad_stats(session, verein_id, saison='2025', wettbewerb='L3'):
    """
    Holt Kaderliste + Saisonstats in einem Durchgang — gefiltert auf einen Wettbewerb.
    wettbewerb='L3' = 3. Liga (Standard), '' = alle Wettbewerbe zusammen.
    Gibt dict zurück: player_id → {number, name, position, age, nationality,
                                    photo_url, profile_url, games, starts,
                                    goals, assists, yellow, yellow_red, red}
    """
    print(f"  Lade Leistungsdaten (Saison {saison}, Wettbewerb: {wettbewerb or 'alle'})...")
    url = (
        f'https://www.transfermarkt.de/x/leistungsdaten/verein/{verein_id}'
        f'/plus/1?reldata={wettbewerb}%26{saison}&saison={saison}'
    )
    soup = get_soup(session, url, delay=1.5)
    table = soup.find('table', class_='items')
    if not table:
        print("  WARNUNG: Keine Tabelle auf Leistungsdaten-Seite gefunden!")
        return {}

    players = {}
    rows = table.find_all('tr', class_=['odd', 'even'])
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 14:
            continue

        # Rückennummer
        number = cells[0].get_text(strip=True)

        # Name: aus cell 1 (inline-table mit hide-for-small)
        name = clean_name(cells[1])

        # Profil-Link + Spieler-ID: in cell 1
        profile_link = None
        for a in cells[1].find_all('a', href=True):
            if '/spieler/' in a.get('href', ''):
                profile_link = a
                break
        profile_url = ('https://www.transfermarkt.de' + profile_link['href']
                       if profile_link else '')
        player_id = extract_player_id(profile_link['href'] if profile_link else '')
        if not player_id:
            continue

        # Position: in cell 1 (zweite Zeile der inline-table) oder cell 4
        position = ''
        inline_table = cells[1].find('table', class_='inline-table')
        if inline_table:
            trs = inline_table.find_all('tr')
            if len(trs) > 1:
                position = trs[1].get_text(strip=True)
        if not position and len(cells) > 4:
            position = cells[4].get_text(strip=True)

        # Alter: cell 5
        age = cells[5].get_text(strip=True) if len(cells) > 5 else '-'

        # Nationalität aus Flag-Bild: cell 6
        nationality = '-'
        if len(cells) > 6:
            flag_img = cells[6].find('img')
            if flag_img:
                nat_name = flag_img.get('title', '')
                nationality = COUNTRY_CODES.get(nat_name, nat_name[:3].upper() if nat_name else '-')

        # Foto-URL: in cell 1, das img-Tag (src direkt nutzbar)
        photo_url = ''
        if inline_table:
            photo_img = inline_table.find('img')
            if photo_img:
                # Direkte src (kein lazy-loading hier auf dieser Seite)
                src = photo_img.get('src', '')
                if src and 'data:image' not in src:
                    photo_url = src
                    # Portrait/small → medium für bessere Qualität
                    photo_url = photo_url.replace('/small/', '/medium/')

        def cell_val(idx):
            if idx >= len(cells):
                return '-'
            v = cells[idx].get_text(strip=True)
            return v if v and v != '' else '-'

        # Stats: Im Kader | Startelf | Tore | Vorlagen | Gelb | GelbRot | Rot
        games_squad = cell_val(7)
        starts = cell_val(8)
        goals = cell_val(9)
        assists = cell_val(10)
        yellow = cell_val(11)
        yellow_red = cell_val(12)
        red = cell_val(13)

        # Spiele-Format: "XX (YY)" wie im Dokument — bei leeren/fehlenden Werten → 0 (0)
        try:
            g = int(str(games_squad).strip()) if str(games_squad).strip() not in ('-', '', 'None') else 0
            s = int(str(starts).strip()) if str(starts).strip() not in ('-', '', 'None') else 0
        except (ValueError, TypeError):
            g, s = 0, 0
        games_display = f'{g} ({s})'

        def fmt_stat(v):
            return '0' if v == '-' else v

        players[player_id] = {
            'number': number,
            'name': name,
            'position': position,
            'age': age,
            'nationality': nationality,
            'photo_url': photo_url,
            'profile_url': profile_url,
            'games_display': games_display,
            'starts_raw': s,
            'goals': fmt_stat(goals),
            'assists': fmt_stat(assists),
            'yellow': fmt_stat(yellow),
            'yellow_red': fmt_stat(yellow_red),
            'red': fmt_stat(red),
            # Wird noch ergänzt:
            'foot': '-',
            'height': '-',
            'team_since': '',
            'transfer_info': '-',
            # Nur für Torhüter (sonst '-'):
            'gegentore': '-',
            'zu_null': '-',
        }

    print(f"  → {len(players)} Spieler gefunden.")
    return players


def get_player_profiles(session, players, delay=1.0):
    """
    Holt für jeden Spieler: Fuß, Größe, Im Team seit.
    Ergänzt das players-Dict direkt.
    """
    total = len(players)
    for i, (pid, data) in enumerate(players.items(), 1):
        print(f"  Profil {i}/{total}: {data['name']}...")
        try:
            soup = get_soup(session, data['profile_url'], delay=delay)
            info_table = soup.find('div', class_='info-table')
            if not info_table:
                continue

            # Paare aus label (regular) + value (bold) aufbauen
            spans = info_table.find_all('span', class_='info-table__content')
            info = {}
            for j in range(0, len(spans) - 1, 2):
                label = spans[j].get_text(strip=True).rstrip(':')
                value = spans[j + 1].get_text(strip=True)
                info[label] = value

            # Fuß
            fuss_raw = info.get('Fuß', '-').lower().strip()
            data['foot'] = FOOT_MAP.get(fuss_raw, fuss_raw[:1].upper() if fuss_raw not in ('-', '') else '-')

            # Größe: "1,92 m"
            data['height'] = info.get('Größe', '-').replace('\xa0', ' ')

            # Im Team seit
            data['team_since'] = info.get('Im Team seit', '')

            # Geburtsdatum: z.B. "06.12.1993 (32)"
            data['geburtsdatum'] = info.get('Geb./Alter', '-')

        except Exception as e:
            print(f"    Fehler beim Profil von {data['name']}: {e}")


def get_einsaetze_per_player(session, players, saison='2025', wettbewerb='L3', delay=0.8):
    """
    Holt für jeden Spieler Einsätze und Startelf via CEAPI.
    Einsätze = participationState=='played'
    Startelf  = played + isStarting==True
    games_display = 'Einsätze (Startelf)'
    """
    total = len(players)
    saison_int = int(saison)
    print(f"\n  Lade Einsätze/Startelf je Spieler ({total})...")

    for i, (pid, data) in enumerate(players.items(), 1):
        print(f"  {i}/{total}: {data['name']}...")
        try:
            url = f'https://www.transfermarkt.de/ceapi/performance-game/{pid}'
            time.sleep(delay)
            r = session.get(url, timeout=30,
                            headers={'Accept': 'application/json',
                                     'Referer': 'https://www.transfermarkt.de/'})
            r.raise_for_status()
            games = r.json().get('data', {}).get('performance', [])

            played = [
                g for g in games
                if g['gameInformation']['competitionId'] == wettbewerb
                and g['gameInformation']['seasonId'] == saison_int
                and g['statistics']['generalStatistics']['participationState'] == 'played'
            ]
            if not played:
                continue

            einsaetze = len(played)
            startelf = sum(
                1 for g in played
                if g['statistics']['playingTimeStatistics']['isStarting']
            )
            data['games_display'] = f'{einsaetze} ({startelf})'

        except Exception as e:
            print(f"    Fehler für {data['name']}: {e}")


def get_goalkeeper_stats(session, players, saison='2025', wettbewerb='L3', delay=1.0):
    """
    Holt für alle Torhüter: Gegentore und Zu-null-Spiele via CEAPI.
    """
    goalkeepers = {pid: d for pid, d in players.items()
                   if d.get('position', '').strip() == 'Torwart'}
    if not goalkeepers:
        return

    total = len(goalkeepers)
    print(f"\n  Lade Torhüter-Stats via CEAPI ({total} Keeper)...")
    saison_int = int(saison)

    for i, (pid, data) in enumerate(goalkeepers.items(), 1):
        print(f"  TW {i}/{total}: {data['name']}...")
        try:
            url = f'https://www.transfermarkt.de/ceapi/performance-game/{pid}'
            time.sleep(delay)
            r = session.get(url, timeout=30,
                            headers={'Accept': 'application/json',
                                     'Referer': 'https://www.transfermarkt.de/'})
            r.raise_for_status()
            games = r.json().get('data', {}).get('performance', [])

            filtered = [
                g for g in games
                if g['gameInformation']['competitionId'] == wettbewerb
                and g['gameInformation']['seasonId'] == saison_int
                and g['statistics']['generalStatistics']['participationState'] == 'played'
            ]
            if not filtered:
                continue

            gegentore = sum(g['clubsInformation']['club']['opponentGoalsTotal']
                            for g in filtered)
            zu_null = sum(1 for g in filtered
                          if g['clubsInformation']['club']['opponentGoalsTotal'] == 0)
            data['gegentore'] = str(gegentore)
            data['zu_null'] = str(zu_null)

        except Exception as e:
            print(f"    TW-Stats Fehler für {data['name']}: {e}")


def get_transfer_info(session, verein_id, delay=1.5):
    """
    Holt Transferhistorie (Zugänge) für mehrere Saisons.
    Gibt dict zurück: player_id → {prev_club, fee}
    """
    print("  Lade Transferdaten (mehrere Saisons)...")
    transfer_map = {}

    for saison in ['2025', '2024', '2023', '2022', '2021', '2020', '2019']:
        url = (
            f'https://www.transfermarkt.de/x/transfers/verein/{verein_id}'
            f'/saison_id/{saison}'
        )
        try:
            soup = get_soup(session, url, delay=delay)
            tables = soup.find_all('table', class_='items')
            if not tables:
                continue

            # Erste Tabelle = Zugänge
            zugaenge_table = tables[0]
            rows = zugaenge_table.find_all('tr', class_=['odd', 'even'])
            new_in_season = 0
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 10:
                    continue

                # Spieler-ID aus Link in cell 1
                pid = None
                for a in cells[1].find_all('a', href=True):
                    if '/spieler/' in a['href']:
                        pid = extract_player_id(a['href'])
                        break

                if not pid or pid in transfer_map:
                    continue

                # Herkunftsverein: cell 9
                prev_club = cells[9].get_text(strip=True) if len(cells) > 9 else '-'
                # Ablöse: letztes cell (meist cell 11)
                fee = cells[-1].get_text(strip=True) if cells else '-'
                fee = fee if fee else 'ablösefrei'

                transfer_map[pid] = {
                    'prev_club': prev_club,
                    'fee': fee,
                }
                new_in_season += 1

            if new_in_season:
                print(f"    Saison {saison}: {new_in_season} Zugänge")

        except Exception as e:
            print(f"    Fehler Saison {saison}: {e}")

    print(f"  → {len(transfer_map)} Transfer-Einträge gefunden.")
    return transfer_map


def download_photo(session, url, player_id, photo_dir):
    """Lädt Spielerfoto herunter und gibt lokalen Pfad zurück."""
    import os
    if not url:
        return None
    ext = 'jpg' if '.jpg' in url.lower() else 'png'
    local_path = os.path.join(photo_dir, f'{player_id}.{ext}')
    if os.path.exists(local_path):
        return local_path
    try:
        time.sleep(0.5)
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(r.content)
            return local_path
    except Exception as e:
        print(f"    Foto-Fehler für {player_id}: {e}")
    return None


def get_coach_info(team_url, photo_dir, wettbewerb='L3'):
    """
    Holt den Cheftrainer von der TM-Mitarbeiter-Seite des Vereins.
    Spalten der Tabelle: 0=Foto+Name, 1=Foto, 2=Name, 3=Rolle, 4=Alter,
                         5=Nationalität, 6=Amtsantritt, 7=Vertrag bis, 8=Letzter Verein
    Zusätzlich: PPS (Punkte pro Spiel) aus dem Trainer-Profil.
    Gibt dict zurück oder None wenn kein Trainer gefunden.
    """
    import os
    session = make_session()
    try:
        print("  Lade Trainer-Info...")
        # /startseite/ → /mitarbeiter/ (oder direkt bauen)
        m_url = re.sub(r'/[^/]+/verein/', '/mitarbeiter/verein/', team_url)
        if '/mitarbeiter/' not in m_url:
            m_url = team_url  # Fallback

        soup = None
        for attempt in range(3):
            try:
                soup = get_soup(session, m_url, delay=1.5 + attempt * 2)
                break
            except Exception as e:
                if attempt < 2:
                    print(f"  Verbindungsproblem, Versuch {attempt+2}/3 in {3+attempt*2}s...")
                    time.sleep(3 + attempt * 2)
                else:
                    raise
        if soup is None:
            return None

        trainer = None
        for tr in soup.find_all('tr'):
            if not tr.find('a', href=re.compile(r'/trainer/')):
                continue
            cells = tr.find_all('td')
            if len(cells) < 7:
                continue

            role = cells[3].get_text(strip=True)
            if role not in ('Trainer', 'Cheftrainer'):
                continue  # Co-Trainer, Torwarttrainer usw. überspringen

            # Profil-URL für spätere Stats-Abfrage
            profile_url = ''
            a_link = cells[2].find('a', href=re.compile(r'/trainer/'))
            if a_link:
                profile_url = 'https://www.transfermarkt.de' + a_link.get('href', '')

            name = cells[2].get_text(strip=True)
            if not name and a_link:
                name = a_link.get('title', '').strip() or a_link.get_text(strip=True)

            age = cells[4].get_text(strip=True)

            nationality = ''
            flag_img = cells[5].find('img')
            if flag_img:
                flag_title = flag_img.get('title', '').strip()
                nationality = COUNTRY_CODES.get(flag_title,
                              flag_title[:3].upper() if flag_title else '')

            amtsantritt = cells[6].get_text(strip=True)

            # Foto: Zellen 0+1 haben portrait-URLs
            photo_url = ''
            for cell in cells[:2]:
                img = cell.find('img')
                if img:
                    src = img.get('src', '')
                    if src and 'portrait' in src:
                        photo_url = re.sub(r'/portrait/\w+', '/portrait/medium', src)
                        break

            trainer = {
                'name': name, 'role': role, 'age': age,
                'nationality': nationality, 'amtsantritt': amtsantritt,
                'photo_url': photo_url, 'local_photo': None,
                'profile_url': profile_url, 'pps': '',
            }
            break  # Ersten Head Coach nehmen

        if not trainer:
            print("  WARNUNG: Kein Cheftrainer in der Tabelle gefunden.")
            return None

        # Foto herunterladen
        if trainer['photo_url']:
            os.makedirs(photo_dir, exist_ok=True)
            local = download_photo(session, trainer['photo_url'], 'coach', photo_dir)
            trainer['local_photo'] = local

        # PPS (Punkte pro Spiel) vom Trainer-Profil holen
        if trainer['profile_url']:
            try:
                liga_name = WETTBEWERB_LIGA_NAMES.get(wettbewerb, '')
                prof_soup = None
                for attempt in range(3):
                    try:
                        prof_soup = get_soup(session, trainer['profile_url'], delay=1.2 + attempt * 2)
                        break
                    except Exception:
                        if attempt < 2:
                            print(f"  PPS-Retry {attempt+2}/3...")
                            time.sleep(3 + attempt * 2)
                if prof_soup is None:
                    raise RuntimeError("Profil nicht erreichbar nach 3 Versuchen")
                stat_tables = prof_soup.find_all('table')
                if len(stat_tables) >= 2:
                    pps_gesamt = ''
                    pps_liga = ''
                    for row in stat_tables[1].find_all('tr'):
                        cells2 = row.find_all('td')
                        if len(cells2) < 7:
                            continue
                        row_label = cells2[0].get_text(strip=True)
                        pps_val   = cells2[6].get_text(strip=True)
                        if row_label == 'Insgesamt:':
                            pps_gesamt = pps_val
                        if liga_name and row_label == liga_name:
                            pps_liga = pps_val
                    trainer['pps'] = pps_liga or pps_gesamt
                    if trainer['pps']:
                        label = liga_name or 'gesamt'
                        print(f"  → PPS ({label}): {trainer['pps']}")
            except Exception as e:
                print(f"  Trainer-PPS Fehler: {e}")

        print(f"  → Trainer: {trainer['name']} ({trainer['role']}, Amtsantritt: {trainer['amtsantritt']})")
        return trainer

    except Exception as e:
        print(f"  Trainer-Info Fehler: {e}")
        return None


def detect_wettbewerb(session, verein_id, saison, preferred='L3'):
    """Erkennt automatisch den aktuellen Wettbewerb des Vereins.
    Prüft L1, L2 und L3 und nimmt den Code mit den meisten Spielern.
    Nicht-deutsche Ligen (ACL2 etc.) werden direkt durchgereicht."""
    candidates = ['L1', 'L2', 'L3']
    if preferred not in candidates:
        return preferred
    counts = {}
    for code in candidates:
        url = (
            f'https://www.transfermarkt.de/x/leistungsdaten/verein/{verein_id}'
            f'/plus/1?reldata={code}%26{saison}&saison={saison}'
        )
        try:
            soup = get_soup(session, url, delay=1.0)
            table = soup.find('table', class_='items')
            rows = table.find_all('tr', class_=['odd', 'even']) if table else []
            # Nur Zeilen mit echten Stats zählen (mind. 1 Spiel)
            with_stats = 0
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 14:
                    games_text = cells[7].get_text(strip=True) if len(cells) > 7 else '0'
                    try:
                        if int(games_text) > 0:
                            with_stats += 1
                    except ValueError:
                        pass
            counts[code] = with_stats
        except Exception:
            counts[code] = 0
    # Bei Gleichstand (z.B. Saisonstart, noch 0 Einsätze überall) gewinnt der
    # gewünschte Wettbewerb -- sonst würde immer der erste Kandidat ('L1')
    # gewinnen, egal was aufgerufen wurde.
    best_count = max(counts.values())
    tied = [code for code in candidates if counts[code] == best_count]
    best_code = preferred if preferred in tied else tied[0]
    print(f"  → Liga erkannt: {best_code} (L1:{counts['L1']}, L2:{counts['L2']}, L3:{counts['L3']} Spieler mit Einsätzen)")
    return best_code


def collect_team_data(team_url, saison='2025', photo_dir='photos', wettbewerb='L3'):
    """
    Hauptfunktion: Sammelt alle Daten für einen Verein.
    team_url: z.B. 'https://www.transfermarkt.de/fc-hansa-rostock/startseite/verein/30'
    wettbewerb: Transfermarkt-Wettbewerbs-ID, z.B. 'L3' für 3. Liga (Standard)
    Gibt Liste von Spieler-Dicts zurück (sortiert nach Rückennummer).
    """
    import os
    os.makedirs(photo_dir, exist_ok=True)

    # Verein-ID aus URL extrahieren
    m = re.search(r'/verein/(\d+)', team_url)
    if not m:
        raise ValueError(f"Keine Verein-ID in URL gefunden: {team_url}")
    verein_id = m.group(1)
    print(f"\n=== Starte Datenabruf für Verein-ID {verein_id} ===")

    session = make_session()

    # Liga automatisch erkennen (nur bei deutschen Ligen)
    wettbewerb = detect_wettbewerb(session, verein_id, saison, preferred=wettbewerb)

    # 1. Kader + Stats
    players = get_squad_stats(session, verein_id, saison, wettbewerb=wettbewerb)
    if not players:
        raise RuntimeError("Keine Spielerdaten geladen!")

    # 2. Spielerprofile (Fuß + Größe + Im Team seit)
    print("\n  Lade Spielerprofile...")
    get_player_profiles(session, players)

    # 3. Einsätze/Startelf von Einzelseiten (alle Spieler)
    get_einsaetze_per_player(session, players, saison, wettbewerb)

    # 4. Torhüter-Stats: Gegentore + Zu-null via CEAPI
    get_goalkeeper_stats(session, players, saison, wettbewerb)

    # 5. Transfer-Info
    print("\n  Lade Transfer-Informationen...")
    transfer_map = get_transfer_info(session, verein_id)

    # Transfer-Info mit Spielern verknüpfen
    for pid, data in players.items():
        t = transfer_map.get(pid)
        if t:
            prev_club = t['prev_club']
            fee = t['fee']
            since = data.get('team_since', '')
            if since:
                data['transfer_info'] = f"{prev_club} ({since}), {fee}"
            else:
                data['transfer_info'] = f"{prev_club}, {fee}"
        else:
            # Kein Transfer gefunden → zumindest "Im Team seit" anzeigen
            since = data.get('team_since', '')
            data['transfer_info'] = f"Im Verein seit {since}" if since else '-'

    # 6. Fotos herunterladen
    print(f"\n  Lade Fotos herunter nach '{photo_dir}'...")
    downloaded = 0
    for pid, data in players.items():
        local = download_photo(session, data['photo_url'], pid, photo_dir)
        data['local_photo'] = local
        if local:
            downloaded += 1
    print(f"  → {downloaded}/{len(players)} Fotos heruntergeladen.")

    # 5. Sortieren nach Rückennummer
    def sort_key(item):
        try:
            return int(item[1]['number'])
        except (ValueError, TypeError):
            return 999

    sorted_players = [v for k, v in sorted(players.items(), key=sort_key)]
    print(f"\n=== Fertig: {len(sorted_players)} Spieler gesammelt ===")
    return sorted_players


if __name__ == '__main__':
    # Schnelltest
    players = collect_team_data(
        'https://www.transfermarkt.de/fc-hansa-rostock/startseite/verein/30',
        photo_dir='/tmp/photos_test'
    )
    for p in players[:3]:
        print(p)
