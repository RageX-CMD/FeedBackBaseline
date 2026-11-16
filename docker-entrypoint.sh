#!/bin/sh
# Linux-sicherer Start: SQLite-Datei darf kein Verzeichnis sein
# (passiert, wenn Docker eine fehlende Bind-Mount-Datei als Ordner anlegt).
set -e

mkdir -p /app/data /app/output /app/snapshots

DB_FILE="${DB_PATH:-/app/data/eventwochen.db}"

if [ -d "$DB_FILE" ]; then
  echo "Fehler: $DB_FILE ist ein Verzeichnis statt einer Datei."
  echo "Docker hat das angelegt, weil die Datei auf dem Host fehlte."
  echo "Fix: docker compose down && rm -rf data/eventwochen.db && mkdir -p data && touch data/eventwochen.db && docker compose up --build"
  exit 1
fi

# Alte DB aus dem Image-/Projektroot einmalig nach data/ uebernehmen
if [ ! -f "$DB_FILE" ] && [ -f /app/eventwochen.db ] && [ ! -d /app/eventwochen.db ]; then
  cp /app/eventwochen.db "$DB_FILE"
fi

export DB_PATH="$DB_FILE"
exec "$@"
