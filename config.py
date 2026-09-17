"""
Konfiguration fuer den Eventwochen-Reporter.

WICHTIG: START_DATE ist das Datum, an dem Eventwoche 1 der aktuellen
Zyklus-Rotation begonnen hat (ein DONNERSTAG - neue Events kommen im
Forum immer donnerstags, jede Eventwoche laeuft also Donnerstag bis
Mittwoch). Der Zyklus laeuft danach automatisch weiter:
Woche 1 -> Woche 2 -> Woche 3 -> Woche 4 -> Woche 1 ...
jede Eventwoche dauert 7 Tage (WEEK_LENGTH_DAYS), der ganze Zyklus also
28 Tage.

Bekannter Fixpunkt: Eventwoche 2 lief vom 10.09.2026 (Do) bis 16.09.2026
(Mi) -> daraus ergibt sich Eventwoche 1 = 03.09.2026 (Do) - 09.09.2026 (Mi).

Wenn du merkst, dass die vom Skript berechnete Eventwoche nicht mit der
tatsaechlich im Spiel laufenden Woche uebereinstimmt, passe START_DATE
einmalig an einen bekannten Donnerstag an, an dem sicher Eventwoche 1
begonnen hat. Danach rechnet sich alles automatisch weiter.
"""

import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Donnerstag, an dem Eventwoche 1 zuletzt sicher begonnen hat.
# --> Bei Bedarf anpassen!
START_DATE = date(2026, 9, 3)

WEEK_LENGTH_DAYS = 7
NUM_WEEKS_IN_CYCLE = 4

DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "eventwochen.db"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "output"))
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", os.path.join(BASE_DIR, "snapshots"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5151"))

FORUM_POST_BASE = "https://forum-narutode.narutowebgame.com/page/show-post-{id}-1.html"

# Letzter bekannter Foren-Post je Eventwoche (alt = vorheriger Zyklus).
# Eventwoche 4 hat diese Runde noch keinen neuen Post — new ist deshalb
# "letztes Mal" (8217), old ist der Stand davor (8213).
FORUM_LINKS = {
    1: {"old": 8214, "new": 8219, "new_is_current": True},
    2: {"old": 8215, "new": 8221, "new_is_current": True},
    3: {"old": 8216, "new": 8224, "new_is_current": True},
    4: {"old": 8213, "new": 8217, "new_is_current": False},
}


def forum_post_url(post_id):
    return FORUM_POST_BASE.format(id=post_id)
