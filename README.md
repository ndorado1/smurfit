# Módulo 2 — Agente Conversacional

Evolución del sistema RAG del módulo 1 a un **agente conversacional** con:

- **Memoria persistente** en PostgreSQL (historial por conversación)
- **Router de herramientas**: el LLM decide entre 2 fuentes de información
  - `search_knowledge_base` → RAG sobre FAISS (reutiliza el índice del módulo 1)
  - `get_company_info` → datos estructurados desde JSON (NIT, sedes, teléfonos…)
- **Interfaz tipo ChatGPT** en React + Vite + Tailwind, paleta azul Smurfit
- **LLM:** OpenAI (`gpt-5.1`)

## Arquitectura

```
React (Vite + Tailwind)
      │  fetch /api
      ▼
FastAPI ──► LangChain Agent (create_tool_calling_agent)
              ├─ Tool: search_knowledge_base  → FAISS (Gemini embeddings)
              └─ Tool: get_company_info       → JSON estructurado
              ▲
              │  historial
PostgreSQL ───┘
```

## Estructura

```
modulo2-agente/
├── backend/
│   ├── main.py                  # FastAPI
│   ├── agent.py                 # Agente + router + system prompt
│   ├── db.py                    # Persistencia Postgres
│   ├── tools/
│   │   ├── rag_tool.py          # Reutiliza FAISS del módulo 1
│   │   └── structured_tool.py   # Datos estructurados
│   ├── data/company_info.json   # Catálogo de datos puntuales
│   ├── pyproject.toml
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── components/{Sidebar,ChatWindow,MessageBubble,ChatInput}.jsx
    │   └── lib/api.js
    ├── package.json
    └── tailwind.config.js
```

## Setup — Backend

```bash
cd backend
cp .env.example .env
# Edita .env con tus credenciales:
#   OPENAI_API_KEY=sk-...
#   GOOGLE_API_KEY=...           (la misma que usa app_rag_comercial.py)
#   DB_PASSWORD=...

uv sync                    # instala dependencias
uv run uvicorn main:app --reload --port 8000
```

La API arranca en `http://localhost:8000`. En el primer arranque crea las tablas `chats` y `messages` en Postgres automáticamente.

## Setup — Frontend

```bash
cd frontend
npm install
npm run dev
```

El UI arranca en `http://localhost:5173`. El proxy de Vite redirige `/api/*` al backend en `:8000`.

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| GET    | `/chats` | Lista de conversaciones |
| POST   | `/chats` | Crear nueva conversación |
| PATCH  | `/chats/{id}` | Renombrar |
| DELETE | `/chats/{id}` | Eliminar (cascade) |
| GET    | `/chats/{id}/messages` | Historial |
| POST   | `/chats/{id}/messages` | Enviar mensaje al agente |
| GET    | `/health` | Status y modelo activo |

## Casos de prueba (cumplimiento del enunciado)

1. **RAG:** *"¿Qué es la cartulina Óptima y cuáles son sus usos?"* → debe llamar a `search_knowledge_base`.
2. **Datos estructurados:** *"¿Cuál es el NIT de la empresa?"* → debe llamar a `get_company_info`.
3. **Memoria:** *"Háblame de sus productos"* → *"¿Cuál mencionaste primero?"* → la 2ª pregunta solo es resoluble con el contexto.
4. **Enrutamiento mixto:** conversación que alterne pregunta abierta + dato concreto + seguimiento.

## Prompt Engineering aplicado al agente

El `SYSTEM_PROMPT` de [`agent.py`](backend/agent.py) combina varias técnicas
reconocidas, cada una con un propósito específico:

| Técnica | Cómo se aplica | Mitiga |
|---|---|---|
| **Role prompting + audiencia** | Persona "asistente virtual oficial", público B2B | Tono y formalidad consistente |
| **Tool documentation** | Cada tool tiene docstring detallado + sección dedicada en el prompt | Que el LLM elija mal la herramienta |
| **Chain-of-thought obligatorio** | Bloque "PROCESO PARA RESPONDER" con 5 pasos numerados | Decisiones de routing sin razonamiento |
| **Zero-shot routing** | Sin ejemplos resueltos en formato Q→A; solo guías de decisión | Sobreajuste a ejemplos concretos |
| **Few-shot de routing (A–E)** | 5 ejemplos cortos de *cómo razonar* la elección de tool | Confusión entre tools en casos límite |
| **Multi-tool reasoning** | Ejemplo D enseña a invocar 2 tools cuando se necesita | Respuestas incompletas |
| **Reference resolution** | Paso 2 obliga a resolver pronombres con el historial antes de llamar la tool | Queries pobres por referencias no resueltas |
| **Output formatting por tipo** | Reglas distintas para datos simples / sedes / listas / narrativa | Formato inconsistente |
| **Fallback canónico exacto** | Frase literal con contacto cuando no hay datos | Alucinaciones para "llenar el silencio" |
| **Negative constraints** | "RESTRICCIONES ABSOLUTAS" prohíbe conocimiento externo, marketing y nombrar tools | Alucinaciones y leaks de implementación |
| **Idioma forzado** | Español formal | Salidas en inglés en contextos técnicos |

### Diferencia con el módulo 1

El módulo 1 (`app_rag.py`) usa **prompts de tarea única**: cada prompt
(QA, Summary, FAQ) tiene una sola función. El módulo 2 usa un **meta-prompt
de agente** que enseña a *decidir* entre herramientas, lo que requiere
técnicas adicionales: chain-of-thought de routing, multi-tool reasoning y
ejemplos de decisión.

## Reutilización del módulo 1

- Embeddings: `gemini-embedding-2-preview` (mismo que `app_rag_comercial.py`).
- Índice FAISS: `output/faiss_index_gemini/` se reutiliza tal cual, no se regenera.
- System prompt: extiende el patrón de prompts del módulo 1 con instrucciones de routing.

## Notas

- El campo `tool_used` en `messages` permite auditar qué herramienta usó el agente en cada respuesta. El frontend lo muestra como un badge sobre cada respuesta.
- Para producción, mover las credenciales a un secret manager y restringir CORS.
