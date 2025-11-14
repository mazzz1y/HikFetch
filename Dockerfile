FROM python:3.13-slim

RUN \
    --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app

COPY app.py .
COPY src/ src/
COPY static/ static/
COPY templates/ templates/

USER 1337:1337

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]