# Imagen del backend (FastAPI + LangGraph). Contexto de construcción: backend/
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Primero las dependencias: esta capa se reutiliza si requirements.txt no cambia.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# El proceso corre sin privilegios de root.
RUN useradd --system --uid 10001 --no-create-home appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

# /health exige token, así que el estado del contenedor se comprueba con una
# conexión TCP al puerto de la API (no abre ningún endpoint sin proteger).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 3).close()"

# --proxy-headers: la API queda detrás de Caddy (HTTPS); respeta X-Forwarded-*.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
