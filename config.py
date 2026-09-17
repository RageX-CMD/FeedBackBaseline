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

from datetime import date

# Donnerstag, an dem Eventwoche 1 zuletzt sicher begonnen hat.
# --> Bei Bedarf anpassen!
START_DATE = date(2026, 9, 3)

WEEK_LENGTH_DAYS = 7
NUM_WEEKS_IN_CYCLE = 4

DB_PATH = "eventwochen.db"
OUTPUT_DIR = "output"
