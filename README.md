# Naruto Online Eventwochen-Reporter

Kleine lokale App (laeuft im Browser) fuer den Feedback-Report zu den 4
Eventwochen im Forum-Zyklus. Wenn du fuer ein Event nichts Neues eintraegst,
wird automatisch das Feedback vom letzten Mal in Word- und Textdokument
uebernommen.

## Starten mit Docker (empfohlen)

Docker Desktop muss installiert sein. Im Projektordner:

```
docker compose up --build
```

Danach im Browser `http://127.0.0.1:5151` oeffnen. Datenbank und erzeugte
Dateien bleiben ueber Volumes erhalten (`eventwochen.db` und `output/`).
Zum Beenden `Strg+C` bzw. `docker compose down`.

## Starten ohne Docker

1. Python 3 muss installiert sein.
2. Abhaengigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```
3. Starten:
   ```
   python app.py
   ```

Es oeffnet sich automatisch ein Browserfenster auf `http://127.0.0.1:5151`.
Falls nicht, den Link einfach manuell im Browser oeffnen.

Die App zeigt automatisch die aktuell laufende Eventwoche (Donnerstag bis
Mittwoch) mit allen Events. Zu jedem Event siehst du das zuletzt
gespeicherte Feedback. Du kannst:
- ein Textfeld ausfuellen -> wird als neues Feedback gespeichert,
- oder das Feld einfach leer lassen -> das alte Feedback bleibt stehen
  (kein Zwang, jedes Event neu zu kommentieren).

Oben kannst du jederzeit zwischen Eventwoche 1-4 wechseln (z.B. um
nachtraeglich Feedback fuer eine andere Woche einzutragen).

Unten auf "Word- und Textdokument erstellen" klicken -> Word (.docx) und
Text (.txt) werden erzeugt und koennen direkt aus der App heruntergeladen
werden (Links erscheinen oben auf der Seite).

Oben in der App steht die Upload-Frist (immer Mittwoch, Ende der laufenden
Eventwoche). Darueber kannst du einmalig `Kalender-Erinnerung (.ics)`
herunterladen und in Outlook, Google Kalender oder Apple Kalender
importieren. Der Termin wiederholt sich jede Woche mittwochs 18:00
(Zeitzone Europe/Berlin) und erinnert dich am Dienstag sowie 15 Minuten
vorher.

Zum Beenden das Terminal-Fenster schliessen bzw. mit Strg+C stoppen.

## Zeitraum / Zyklus

Neue Events erscheinen im Forum immer donnerstags, jede Eventwoche laeuft
also Donnerstag bis Mittwoch. Fixpunkt: Eventwoche 2 lief vom 10.09.2026
bis 16.09.2026 - daraus berechnet die App automatisch alle anderen Wochen
(Woche 1 -> 2 -> 3 -> 4 -> 1 ... je 7 Tage, 28 Tage Zykluslaenge).

Falls die App irgendwann die falsche Woche anzeigt (z.B. weil sich der
Rhythmus im Spiel verschoben hat), in `config.py` das `START_DATE`
einmalig an einen bekannten Donnerstag anpassen, an dem sicher
Eventwoche 1 begonnen hat. Danach rechnet sich wieder alles automatisch
weiter.

## Daten

Alle Events und dein bisheriges Feedback zu Eventwoche 1-3 sind in
`seed_data.py` bereits vorbefuellt (dein Originaltext). Eventwoche 4 ist
mit allen 20 Events angelegt, aber noch ohne Feedback.

Alles, was du in der App eintraegst, wird dauerhaft in `eventwochen.db`
(SQLite, wird beim ersten Start automatisch angelegt) gespeichert:
- `events` - aktuellstes Feedback je Event
- `feedback_history` - komplette Historie aller Aenderungen (mit Datum)
- `runs` - Protokoll aller erzeugten Dokumente

Die Datei `eventwochen.db` bitte nicht loeschen, sonst geht die Historie
verloren.

## Dateien

- `app.py` - die App (starten mit `python app.py`)
- `templates/index.html` - Oberflaeche
- `config.py` - Einstellungen (Zyklus-Startdatum)
- `cycle.py` - Logik zur Berechnung der aktuellen Eventwoche
- `db.py` - Datenbankzugriff (SQLite)
- `docx_export.py` - erzeugt das Word-Dokument
- `txt_export.py` - erzeugt das Textdokument
- `ics_export.py` - Kalender-Erinnerung jeden Mittwoch (.ics)
- `seed_data.py` - dein Anfangs-Feedback zu allen Events
- `eventwochen.db` - die Datenbank (wird automatisch erstellt/gepflegt)
- `output/` - hier landen die erzeugten Word- und Textdateien
- `Dockerfile` / `docker-compose.yml` - Start per Docker
