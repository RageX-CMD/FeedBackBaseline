"""Berechnung der aktuellen Eventwoche anhand des heutigen Datums."""

from datetime import date, timedelta
from config import START_DATE, WEEK_LENGTH_DAYS, NUM_WEEKS_IN_CYCLE


def current_week_info(today: date = None):
    """
    Gibt (eventwoche_nummer, woche_start, woche_ende) zurueck.
    eventwoche_nummer ist 1..NUM_WEEKS_IN_CYCLE.
    """
    if today is None:
        today = date.today()

    cycle_length = WEEK_LENGTH_DAYS * NUM_WEEKS_IN_CYCLE
    days_since_start = (today - START_DATE).days

    if days_since_start < 0:
        # Startdatum liegt in der Zukunft -> wir sind noch vor Zyklusbeginn,
        # rechnen rueckwaerts auf die letzte volle Zyklus-Wiederholung.
        days_since_start %= cycle_length

    position_in_cycle = days_since_start % cycle_length
    week_index = position_in_cycle // WEEK_LENGTH_DAYS  # 0-based
    eventwoche_nummer = int(week_index) + 1

    week_start = START_DATE + timedelta(
        days=int(week_index) * WEEK_LENGTH_DAYS
        + (days_since_start // cycle_length) * cycle_length
    )
    week_end = week_start + timedelta(days=WEEK_LENGTH_DAYS - 1)

    return eventwoche_nummer, week_start, week_end


def week_info_for(eventwoche_nummer: int, today: date = None):
    """
    Gibt Start-/Enddatum fuer eine explizit gewaehlte Eventwoche
    (1..4) zurueck — immer innerhalb des aktuellen 28-Tage-Zyklus
    (der Zyklus, der das heutige Datum enthaelt).

    So kannst du z.B. in Woche 3 noch Feedback fuer Woche 1 oder 2
    derselben Runde schreiben, ohne in den naechsten Zyklus zu springen.
    """
    if today is None:
        today = date.today()

    eventwoche_nummer = int(eventwoche_nummer)
    if eventwoche_nummer < 1 or eventwoche_nummer > NUM_WEEKS_IN_CYCLE:
        raise ValueError(f"Eventwoche muss 1..{NUM_WEEKS_IN_CYCLE} sein")

    current_num, current_start, _ = current_week_info(today)
    cycle_start = current_start - timedelta(
        days=(current_num - 1) * WEEK_LENGTH_DAYS
    )
    week_start = cycle_start + timedelta(
        days=(eventwoche_nummer - 1) * WEEK_LENGTH_DAYS
    )
    week_end = week_start + timedelta(days=WEEK_LENGTH_DAYS - 1)
    return eventwoche_nummer, week_start, week_end


if __name__ == "__main__":
    num, start, end = current_week_info()
    print(f"Aktuelle Eventwoche: {num} ({start.isoformat()} - {end.isoformat()})")
