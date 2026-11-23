# API de Trámites — imagen para Cloud Run (servicio) y Cloud Run Jobs (migrate, bootstrap-admin).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
COPY pyproject.toml ./
COPY src ./src
RUN pip install . && useradd --create-home --uid 10001 app

COPY alembic.ini ./
COPY migrations ./migrations

# Sin privilegios de root dentro del contenedor.
USER app
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
