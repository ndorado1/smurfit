# syntax=docker/dockerfile:1.7
# ============================================================================
# Dockerfile multi-stage: Node compila el frontend, Python sirve TODO.
# Resultado: una sola imagen que expone el puerto 8000 con:
#   /         -> React SPA buildeado por Vite
#   /api/*    -> FastAPI con el agente conversacional
#   /assets/* -> JS/CSS/imagenes del build de Vite
# ============================================================================


# ─── Etapa 1: build del frontend ──────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Instalar dependencias primero para aprovechar cache de Docker
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

# Copiar el resto y buildear
COPY frontend/ ./
RUN npm run build
# Output esperado: /app/dist/{index.html, assets/...}


# ─── Etapa 2: backend con frontend embebido ──────────────────────────────────
FROM python:3.11-slim AS runtime

# Dependencias del sistema necesarias para psycopg y compilacion
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (gestor rapido de paquetes Python)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copiar manifest primero para cachear la instalacion de dependencias
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Copiar el codigo del backend
COPY backend/ ./

# Copiar el frontend buildeado al lugar donde FastAPI lo sirve
COPY --from=frontend-builder /app/dist ./static

# Variables por defecto (sobreescribibles via .env del runtime)
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

EXPOSE 8000

# Easypanel y la mayoria de PaaS hacen healthcheck a / o /api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/api/health || exit 1

# Arrancar el server. --proxy-headers permite que respete X-Forwarded-* de Easypanel.
CMD ["sh", "-c", "uv run uvicorn main:app --host ${HOST} --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
