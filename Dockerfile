FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5151

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output snapshots

EXPOSE 5151

CMD ["gunicorn", "--bind", "0.0.0.0:5151", "--workers", "1", "--timeout", "120", "app:app"]
