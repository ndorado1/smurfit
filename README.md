# Smurfit Westrock — Asistente Conversacional

Agente conversacional con memoria, router de herramientas y UI tipo ChatGPT para Smurfit Kappa Colombia (Cartón de Colombia / Smurfit Westrock). Responde preguntas combinando dos fuentes: **RAG documental** sobre el sitio web oficial y **datos estructurados** curados manualmente.

> Desplegado en [`llm.innovatec.co`](https://llm.innovatec.co)

## Arquitectura

```
React (Vite + Tailwind)
      │ fetch /api/*
      ▼
FastAPI ──► LangChain Agent (create_tool_calling_agent)
              ├─ Tool: search_knowledge_base  → FAISS local (Gemini embeddings)
              └─ Tool: get_company_info       → JSON estructurado
              ▲
              │  historial
PostgreSQL ───┘
```

Una sola imagen Docker sirve ambos:
- `/` → React SPA buildeado
- `/api/*` → endpoints del agente
- `/api/chats/{id}/messages/stream` → SSE con eventos del agente en tiempo real

## Modelos soportados

| Perfil | Proveedor | Modelo |
|---|---|---|
| Comercial | OpenAI directo | `gpt-5.1` |
| Open-Source | OpenRouter | `qwen/qwen3.5-9b` |

El usuario elige desde la UI; los settings de muestreo (temperature, top_p, etc.) se guardan en localStorage por proveedor.

## Stack

| Capa | Tecnología |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Orquestación | LangChain `create_tool_calling_agent` |
| Tools | RAG (FAISS + Gemini) + Datos estructurados (JSON) |
| LLM | OpenAI GPT-5.1 / OpenRouter Qwen 3.5 9B |
| Persistencia | PostgreSQL con `psycopg-pool` |
| Streaming | Server-Sent Events |
| Observabilidad | LangSmith (opcional) |
| Frontend | React 18 + Vite + Tailwind |
| Container | Dockerfile multi-stage (Node build → Python serve) |

## Desarrollo local

### Opción A — sin Docker (más rápido para iterar)

**Backend:**
```bash
cd backend
cp .env.example .env  # editar con tus API keys
uv sync
uv run uvicorn main:app --reload --port 8000
```

**Frontend (otra terminal):**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Opción B — con Docker (igual que en producción)

```bash
docker build -t smurfit .
docker run --rm -p 8000:8000 --env-file backend/.env smurfit
# http://localhost:8000
```

## Variables de entorno

Ver [`backend/.env.example`](backend/.env.example) para la plantilla completa. Lo crítico:

```bash
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-v1-...
GOOGLE_API_KEY=...                # para los embeddings del FAISS
DB_HOST=easypanel.innovatec.co
DB_PORT=5438
DB_NAME=llm
DB_USER=postgres
DB_PASSWORD=...
LANGSMITH_API_KEY=lsv2_pt_...     # opcional, para tracing
```

## Deployment a Easypanel

Ver [`DEPLOYMENT.md`](DEPLOYMENT.md) — paso a paso para conectar este repo a Easypanel, configurar el dominio y las variables de entorno.

## Usuarios

Hardcoded para el alcance del taller. Cada uno tiene su propio historial de conversaciones en Postgres.

```
antonio · bradley · camilo · simon
```

## Casos de prueba (cumplimiento del enunciado)

| Caso | Pregunta de ejemplo | Tool esperada |
|---|---|---|
| **RAG** | *¿Qué es la cartulina Óptima y para qué sirve?* | `search_knowledge_base` |
| **Datos estructurados** | *¿Cuál es el NIT de la empresa?* | `get_company_info` |
| **Memoria** | *Háblame de sus productos* → *¿Cuál mencionaste primero?* | RAG + resolución por contexto |
| **Multi-tool** | *¿Qué hacen en la planta de Cali y dónde queda?* | Ambas tools |

## Estructura del repo

```
.
├── Dockerfile                # multi-stage: Node build → Python serve
├── .dockerignore
├── DEPLOYMENT.md             # guía Easypanel
├── README.md
├── backend/
│   ├── main.py               # FastAPI + APIRouter /api + servido del SPA
│   ├── agent.py              # LangChain agent con router
│   ├── db.py                 # Postgres con connection pool
│   ├── tools/
│   │   ├── rag_tool.py       # FAISS + Gemini embeddings
│   │   └── structured_tool.py
│   ├── data/
│   │   ├── company_info.json
│   │   └── faiss_index_gemini/   # índice incluido en el repo
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/{ChatWindow, MessageBubble, Sidebar, Login, ModelSelect, SettingsModal, ...}.jsx
    │   └── lib/api.js
    ├── vite.config.js
    └── package.json
```

---

Este repo es la **Entrega 2** del taller de LLMs. Para el código de la Entrega 1 (RAG con Streamlit), ver [github.com/simonc2123/LLM-ENTREGA-01](https://github.com/simonc2123/LLM-ENTREGA-01).
