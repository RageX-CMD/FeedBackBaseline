# -*- coding: utf-8 -*-
"""Erstellt das Textdokument fuer eine Eventwoche."""

import os
from datetime import date

from config import OUTPUT_DIR


def build_txt(week_label, week_number, week_start, week_end, events):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    lines = [
        f"{week_label} - Feedback-Report",
        "",
        f"Zeitraum: {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}",
        f"Erstellt am: {date.today().strftime('%d.%m.%Y')}",
        "",
    ]

    for ev in events:
        lines.append(f"{ev['event_order']} - {ev['name']}")
        feedback_text = (ev["feedback"] or "").strip()
        lines.append(feedback_text if feedback_text else "(kein Feedback vorhanden)")
        lines.append("")

    filename = f"Eventwoche_{week_number}_{week_start.isoformat()}.txt"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    return path
