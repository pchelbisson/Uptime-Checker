FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

RUN groupadd -r appgroup && useradd -r -g appgroup -s /sbin/nologin appuser

COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

ENV APP_PORT=8000

CMD uvicorn main:app --host 0.0.0.0 --port ${APP_PORT}