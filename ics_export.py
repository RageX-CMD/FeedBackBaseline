# -*- coding: utf-8 -*-
"""Erzeugt eine wiederkehrende Kalender-Erinnerung (.ics) fuer den Mittwoch."""

from datetime import date, datetime, timedelta, timezone

from config import START_DATE


def first_wednesday(start: date = START_DATE) -> date:
    """Erster Mittwoch der Eventwoche (Do-Mi), relativ zum Zyklus-Start."""
    # START_DATE ist ein Donnerstag -> +6 Tage = Mittwoch
    return start + timedelta(days=6)


def build_ics() -> bytes:
    """
    Woechentliche Erinnerung jeden Mittwoch 18:00 (Europe/Berlin),
    mit Alarm am Dienstag 18:00 (ein Tag vorher).
    """
    first = first_wednesday()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    start_local = first.strftime("%Y%m%dT180000")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Eventwochen-Reporter//DE",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VTIMEZONE",
        "TZID:Europe/Berlin",
        "X-LIC-LOCATION:Europe/Berlin",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0200",
        "TZNAME:CEST",
        "DTSTART:19700329T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0200",
        "TZOFFSETTO:+0100",
        "TZNAME:CET",
        "DTSTART:19701025T030000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
        "BEGIN:VEVENT",
        "UID:eventwochen-upload-mittwoch@eventwochen-reporter",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=Europe/Berlin:{start_local}",
        "DURATION:PT30M",
        "RRULE:FREQ=WEEKLY;BYDAY=WE",
        "SUMMARY:Eventwochen-Feedback spaetestens heute hochladen",
        "DESCRIPTION:Dokumente in der Eventwochen-App erstellen "
        "(Word/TXT) und spaetestens heute (Mittwoch) im Forum hochladen.\\n"
        "App: http://127.0.0.1:5151",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Morgen (Mittwoch) Eventwochen-Feedback hochladen",
        "TRIGGER:-P1D",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "DESCRIPTION:Eventwochen-Feedback spaetestens heute hochladen",
        "TRIGGER:-PT15M",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines).encode("utf-8")
