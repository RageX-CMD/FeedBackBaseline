# -*- coding: utf-8 -*-
"""
Eventwochen-Reporter - GUI-App (laeuft lokal im Browser).

Start:
    python app.py

Oder per Docker:
    docker compose up --build

Oeffnet automatisch http://127.0.0.1:5151 im Standardbrowser (nur beim
lokalen Python-Start). Dort kannst du fuer die aktuelle (oder eine
beliebige) Eventwoche jedes Event einsehen, Feedback eintragen/aendern
oder das Feld leer lassen, um das alte Feedback zu behalten. Am Ende
erzeugst du per Knopfdruck Word- und Textdokument.
"""

import os
import threading
import webbrowser
from datetime import date, timedelta

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, Response

import db
from config import OUTPUT_DIR, HOST, PORT, SNAPSHOT_DIR, FORUM_LINKS, forum_post_url
from cycle import current_week_info, week_info_for
from seed_data import SEED_DATA
from docx_export import build_docx
from txt_export import build_txt
from ics_export import build_ics
from discord_export import build_discord_parts
from forum_compare import capture_forum_url, analyze

app = Flask(__name__)
app.secret_key = "eventwochen-reporter-local"
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

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
    last_docx, last_txt = download_names(last_doc)

    today = date.today()
    current_num, current_start, current_end = current_week_info(today)
    current_run = db.get_last_run(current_num)
    uploaded_this_week = bool(
        current_run and current_run.get("week_start") == current_start.isoformat()
    )
    days_until_deadline = (current_end - today).days
    discord_parts = build_discord_parts(
        WEEK_NAMES[week_number], week_start, week_end, events
    )

    current_snap = db.get_snapshot_for_week(week_number, week_start.isoformat())
    previous_snap = db.get_previous_snapshot(week_number, week_start.isoformat())
    curr_images = db.get_snapshot_images(current_snap["id"]) if current_snap else []
    prev_images = db.get_snapshot_images(previous_snap["id"]) if previous_snap else []
    forum_analysis = (
        analyze(previous_snap, current_snap, prev_images, curr_images)
        if current_snap
        else None
    )

    forum_links = FORUM_LINKS.get(week_number, {})
    forum_old_url = forum_post_url(forum_links["old"]) if forum_links.get("old") else ""
    forum_new_url = forum_post_url(forum_links["new"]) if forum_links.get("new") else ""
    forum_new_is_current = forum_links.get("new_is_current", True)

    return render_template(
        "index.html",
        week_number=week_number,
        week_names=WEEK_NAMES,
        week_start=week_start,
        week_end=week_end,
        events=events,
        today=today,
        last_doc=last_doc,
        last_docx=last_docx,
        last_txt=last_txt,
        current_num=current_num,
        current_end=current_end,
        days_until_deadline=days_until_deadline,
        uploaded_this_week=uploaded_this_week,
        discord_parts=discord_parts,
        current_snap=current_snap,
        forum_analysis=forum_analysis,
        forum_old_url=forum_old_url,
        forum_new_url=forum_new_url,
        forum_new_is_current=forum_new_is_current,
    )


@app.route("/kalender.ics")
def kalender():
    return Response(
        build_ics(),
        mimetype="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=Eventwochen-Upload-Erinnerung.ics"},
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

    docx_path = build_docx(WEEK_NAMES[week_number], week_number, week_start, week_end, events)
    build_txt(WEEK_NAMES[week_number], week_number, week_start, week_end, events)
    db.log_run(week_number, week_start, week_end, os.path.basename(docx_path))

    flash(f"Word- und Textdokument erstellt ({changed} Feedback-Eintrag/e aktualisiert).", "success")
    return redirect(url_for("index", week=week_number))


@app.route("/snapshot", methods=["POST"])
def snapshot():
    week_number = int(request.form["week_number"])
    week_start_iso = request.form["week_start"]
    old_url = (request.form.get("forum_url_old") or "").strip()
    new_url = (request.form.get("forum_url_new") or "").strip()

    if not new_url:
        flash("Bitte den Link zur aktuellen Eventwoche eintragen.", "error")
        return redirect(url_for("index", week=week_number))

    try:
        if old_url:
            old_start = (date.fromisoformat(week_start_iso) - timedelta(days=28)).isoformat()
            old_text, old_images, old_events = capture_forum_url(old_url)
            db.save_snapshot(week_number, old_start, old_url, old_text, old_images, old_events)
        new_text, new_images, new_events = capture_forum_url(new_url)
        db.save_snapshot(week_number, week_start_iso, new_url, new_text, new_images, new_events)
    except Exception as exc:
        flash(f"Forum-Link nicht lesbar: {exc}", "error")
        return redirect(url_for("index", week=week_number))

    flash("Forum-Links geladen. Vergleich steht oben.", "success")
    return redirect(url_for("index", week=week_number))


@app.route("/snapshots/<path:filename>")
def snapshot_file(filename):
    return send_from_directory(SNAPSHOT_DIR, filename)


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


def download_names(last_doc):
    if not last_doc:
        return None, None
    stored = (last_doc["docx_path"] or "").replace("\\", "/")
    docx_name = os.path.basename(stored)
    txt_name = os.path.splitext(docx_name)[0] + ".txt"
    last_docx = docx_name if os.path.isfile(os.path.join(OUTPUT_DIR, docx_name)) else None
    last_txt = txt_name if os.path.isfile(os.path.join(OUTPUT_DIR, txt_name)) else None
    return last_docx, last_txt


def open_browser():
    webbrowser.open_new(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    if HOST in ("127.0.0.1", "localhost"):
        threading.Timer(1.0, open_browser).start()
    app.run(host=HOST, port=PORT, debug=False)
