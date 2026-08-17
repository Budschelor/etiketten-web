# Etiketten-Web

Web-App fuer die Redaktion: Spieltag waehlen -> die Partie von Hansa Rostock wird
automatisch erkannt -> Spieleretiketten (Word, je ein Dokument pro Team) und ein
Taktikboard werden gebaut und als ZIP-Datei zum Download angeboten.

Datenquellen:
- **Spielplan/Anstosszeiten**: [OpenLigaDB](https://www.openligadb.de/) -- eine
  kostenlose, offizielle Fussball-Datenbank. Liefert dieselben Begegnungen wie
  kicker.de; kicker.de selbst blockiert automatisierte Abrufe (Bot-Schutz) und
  konnte deshalb nicht direkt angezapft werden.
- **Spielerdaten & Fotos**: transfermarkt.de (wie im lokalen Tool in `~/Travis`).

## Lokal starten

```bash
pip install -r requirements.txt
python3 server.py
```

Dann `http://localhost:5050` oeffnen.

## Deployment auf Render.com (kostenlos)

Gleicher Ablauf wie beim Leichtathletik-Projekt (`Athletenkarte-Web`):

1. Dieses Repo auf GitHub pushen (siehe unten).
2. Auf [render.com](https://render.com) mit dem GitHub-Account anmelden.
3. **New +** -> **Blueprint** -> dieses Repo auswaehlen (Render erkennt
   `render.yaml` automatisch).
4. Nach ein paar Minuten ist die App unter einer Adresse wie
   `https://etiketten-web.onrender.com` erreichbar -- dieser Link geht an die
   Kollegen in der Redaktion.

**Hinweis:** Auf der kostenlosen Stufe schlaeft die App nach 15 Minuten ohne
Aufruf ein. Der erste Aufruf danach dauert dann ca. 30-60 Sekunden zum
Aufwachen. Ein Durchlauf (zwei Kader + Fotos laden) dauert danach wie gewohnt
ca. 3-5 Minuten -- die Seite zeigt den Fortschritt live an.

## Repo auf GitHub anlegen und pushen

```bash
git remote add origin https://github.com/<dein-nutzername>/etiketten-web.git
git branch -M main
git push -u origin main
```

## Unterschied zur lokalen Desktop-Version (`~/Travis`)

Die Skripte in `~/Travis` (`etiketten.py`, `webapp_generator.py`) legen die
fertigen Dateien weiterhin automatisch auf dem eigenen Schreibtisch ab -- das
bleibt unveraendert und ist unabhaengig von dieser Web-App.

Diese Web-App laeuft dagegen auf einem fremden Server (Render), der keinen
Zugriff auf den Schreibtisch eines Kollegen hat. Kollegen bekommen darum einen
Download-Button mit einer ZIP-Datei (beide Word-Etiketten + Taktikboard drin),
die sie selbst speichern.
