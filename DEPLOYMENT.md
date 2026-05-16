# Deployment a Easypanel — `llm.innovatec.co`

Un solo contenedor sirve tanto el backend (FastAPI bajo `/api/*`) como el frontend React (SPA en `/`).

## Prerrequisitos

- Cuenta en [openrouter.ai](https://openrouter.ai) y API key (`OPENROUTER_API_KEY`)
- API key de OpenAI para el modelo comercial GPT-5.1
- API key de Google AI Studio para los embeddings de Gemini
- Postgres en easypanel (`easypanel.innovatec.co:5438`, base `llm`, user `postgres`)
- (Opcional) cuenta en LangSmith para tracing

## 1) Crear servicio en Easypanel

1. **Apps** → **+ Service** → **App**
2. Elige **GitHub** como source y conecta el repo
3. Branch: `main` (o el que uses)
4. **Build settings:**
   - **Build method:** `Dockerfile`
   - **Build context:** `modulo2-agente/` (o la carpeta raíz si moviste el código)
   - **Dockerfile path:** `Dockerfile`
5. **Resources:** 1 vCPU / 1 GB RAM es suficiente (sube si OpenRouter tarda en responder)

## 2) Variables de entorno

En el panel del servicio → **Environment**, pegá:

```bash
# OpenAI (modelo comercial)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.1

# OpenRouter (modelo open-source - Qwen)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=qwen/qwen3.5-9b
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Google Gemini (embeddings para el FAISS del modulo 1)
GOOGLE_API_KEY=...

# PostgreSQL (easypanel — usar el hostname interno si esta en el mismo proyecto)
DB_HOST=easypanel.innovatec.co
DB_PORT=5438
DB_NAME=llm
DB_USER=postgres
DB_PASSWORD=...

# LangSmith (opcional, observabilidad)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=smurfit-agente
LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# URL publica (para headers de OpenRouter)
APP_URL=https://llm.innovatec.co
```

> **Tip de seguridad:** marca cada variable sensible como **secret** en Easypanel para que no aparezca en logs.

## 3) Dominio

1. **Domains** → **+ Add Domain**
2. Domain: `llm.innovatec.co`
3. Port: `8000` (donde escucha el contenedor)
4. ✅ **HTTPS** (Let's Encrypt automático)

## 4) Deploy

Easypanel construye y arranca el servicio automáticamente al push de la rama configurada. El build dura ~3–5 minutos (Node + Python + dependencias).

Una vez arriba:

- Frontend: `https://llm.innovatec.co`
- Healthcheck: `https://llm.innovatec.co/api/health`

## Build local (opcional, para probar antes de subir)

```bash
cd modulo2-agente
docker build -t smurfit-agente .
docker run --rm -p 8000:8000 --env-file backend/.env smurfit-agente
# abre http://localhost:8000
```

## Estructura del contenedor

```
imagen final (python:3.11-slim, ~400 MB)
└── /app/
    ├── main.py, agent.py, db.py
    ├── tools/        # rag_tool.py, structured_tool.py
    ├── data/
    │   ├── company_info.json
    │   └── faiss_index_gemini/   # incluido en el repo
    ├── .venv/        # dependencias Python
    └── static/       # frontend buildeado por Vite (index.html, assets/, ...)
```

## Troubleshooting

| Problema | Causa probable | Solución |
|---|---|---|
| 502 / connection refused | Container no terminó de arrancar | Espera 30–60s, mira logs en Easypanel |
| `OPENROUTER_API_KEY no configurada` | Variable faltante | Agrégala en Environment y redeploy |
| CORS error en frontend | El dominio no está en `allow_origins` | Agrega tu dominio en `main.py` y redeploy |
| `psycopg.OperationalError: connection refused` | Postgres no accesible desde el container | Verifica `DB_HOST` y el firewall del Postgres |
| Stream se corta a mitad | Reverse proxy comprime SSE | En Easypanel, agregar header `X-Accel-Buffering: no` (ya está en el código) |
| Build falla en `npm ci` | `package-lock.json` desactualizado | Hacer `npm install` localmente y commitear el lock |

## Actualizar el FAISS index en producción

El índice está en `backend/data/faiss_index_gemini/`. Si regeneras el KB:

1. Copia el nuevo `index.faiss` y `index.pkl` a esa carpeta
2. `git commit && git push`
3. Easypanel reconstruye automáticamente

Como alternativa, mountar un volumen persistente en `/app/data/faiss_index_gemini` y subir los archivos vía SFTP/Easypanel UI.
