# -*- coding: utf-8 -*-
"""
Eventwochen-Reporter - GUI-App (laeuft lokal im Browser).

Start:
    python app.py

Oeffnet automatisch http://127.0.0.1:5151 im Standardbrowser. Dort kannst
du fuer die aktuelle (oder eine beliebige) Eventwoche jedes Event einsehen,
Feedback eintragen/aendern oder per Klick auf "Feedback vom letzten Mal
behalten" einfach ueberspringen. Am Ende erzeugst du per Knopfdruck das
docx-Dokument.
"""

import os
import threading
import webbrowser
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash

import db
from config import OUTPUT_DIR
from cycle import current_week_info, week_info_for
from seed_data import SEED_DATA
from docx_export import build_docx

app = Flask(__name__)
app.secret_key = "eventwochen-reporter-local"

WEEK_NAMES = {1: "Eventwoche 1", 2: "Eventwoche 2", 3: "Eventwoche 3", 4: "Eventwoche 4"}

db.init_db()
db.seed_events(SEED_DATA, overwrite=False)


def get_week(week_arg):
    if week_arg:
        return week_info_for(int(week_arg))
    return current_week_info()


@app.route("/", methods=["GET"])
def index():
    week_arg = request.args.get("week")
    week_number, week_start, week_end = get_week(week_arg)
    events = db.get_events(week_number)

    last_doc = db.get_last_run(week_number)

    return render_template(
        "index.html",
        week_number=week_number,
        week_names=WEEK_NAMES,
        week_start=week_start,
        week_end=week_end,
        events=events,
        today=date.today(),
        last_doc=last_doc,
    )


@app.route("/save", methods=["POST"])
def save():
    week_number = int(request.form["week_number"])
    week_start_iso = request.form["week_start"]
    week_end_iso = request.form["week_end"]

    events = db.get_events(week_number)
    changed = 0
    for ev in events:
        field = f"feedback_{ev['event_order']}"
        new_text = request.form.get(field, "").strip()
        if new_text and new_text != (ev["feedback"] or ""):
            db.update_feedback(week_number, ev["event_order"], new_text, week_start_iso)
            changed += 1

    # aktualisierte Liste fuer das Dokument
    events = db.get_events(week_number)
    week_start = date.fromisoformat(week_start_iso)
    week_end = date.fromisoformat(week_end_iso)

    path = build_docx(WEEK_NAMES[week_number], week_number, week_start, week_end, events)
    db.log_run(week_number, week_start, week_end, path)

    flash(f"Dokument erstellt ({changed} Feedback-Eintrag/e aktualisiert).", "success")
    return redirect(url_for("index", week=week_number))


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5151")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5151, debug=False)
