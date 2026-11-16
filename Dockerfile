FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5151 \
    DB_PATH=/app/data/eventwochen.db \
    OUTPUT_DIR=/app/output \
    SNAPSHOT_DIR=/app/snapshots

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output snapshots data \
    && chmod +x docker-entrypoint.sh run.sh \
    && if [ -f eventwochen.db ]; then cp eventwochen.db data/eventwochen.db; fi

EXPOSE 5151

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5151", "--workers", "1", "--timeout", "120", "app:app"]
