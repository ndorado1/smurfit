"""
API FastAPI del agente conversacional.

Endpoints:
- GET    /chats                  → lista de conversaciones (sidebar)
- POST   /chats                  → crear nueva conversacion
- DELETE /chats/{chat_id}        → eliminar conversacion
- GET    /chats/{chat_id}/messages → historial de la conversacion
- POST   /chats/{chat_id}/messages → enviar mensaje y recibir respuesta del agente
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
import json

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

import db
from agent import PROVIDERS, run_agent, stream_agent

# Carpeta donde se monta el frontend buildeado (lo copia el Dockerfile multi-stage).
# En desarrollo no existe — el frontend corre con Vite en :5173.
STATIC_DIR = Path(__file__).parent / "static"


def require_user(x_user_id: str | None = Header(default=None)) -> str:
    """Dependency: extrae y valida el usuario del header X-User-Id."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Falta el header X-User-Id.")
    if x_user_id not in db.ALLOWED_USERS:
        raise HTTPException(
            status_code=403,
            detail=f"Usuario no autorizado. Permitidos: {db.ALLOWED_USERS}",
        )
    return x_user_id


def get_provider(x_model_provider: str | None = Header(default=None)) -> str:
    """Dependency: extrae el proveedor de LLM del header X-Model-Provider.
    Default: 'commercial' si no se envia (compatibilidad con clientes antiguos).
    """
    provider = x_model_provider or "commercial"
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Proveedor invalido: {provider}. Validos: {list(PROVIDERS)}",
        )
    return provider


def require_chat_owned_by(chat_id: str, user_id: str) -> dict:
    """Verifica que el chat exista y pertenezca al usuario."""
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado.")
    if chat["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Este chat no te pertenece.")
    return chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    db.init_schema()
    yield
    db.close_pool()


app = FastAPI(title="Smurfit Westrock — Agente Conversacional", lifespan=lifespan)

# Todos los endpoints de la API van bajo /api. En produccion FastAPI tambien
# sirve el frontend en /, asi que esta separacion evita colisiones.
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://llm.innovatec.co",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatCreate(BaseModel):
    title: str | None = None


class ChatTitleUpdate(BaseModel):
    title: str


class MessageIn(BaseModel):
    content: str
    sampling: dict | None = None  # {temperature, top_p, top_k, max_tokens, ...}


class MessageOut(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    tool_used: str | None
    created_at: str


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[str]


# ── Endpoints: chats ──────────────────────────────────────────────────────────

@api.get("/users")
def list_users():
    """Devuelve la lista de usuarios permitidos (pantalla de login)."""
    return {"users": db.ALLOWED_USERS}


@api.get("/chats")
def list_chats(user_id: str = Depends(require_user)):
    chats = db.list_chats(user_id)
    return [{**c, "id": str(c["id"]),
             "created_at": c["created_at"].isoformat(),
             "updated_at": c["updated_at"].isoformat()} for c in chats]


@api.post("/chats")
def create_chat(payload: ChatCreate, user_id: str = Depends(require_user)):
    title = payload.title or "Nueva conversacion"
    c = db.create_chat(user_id, title)
    return {**c, "id": str(c["id"]),
            "created_at": c["created_at"].isoformat(),
            "updated_at": c["updated_at"].isoformat()}


@api.patch("/chats/{chat_id}")
def update_chat(chat_id: str, payload: ChatTitleUpdate, user_id: str = Depends(require_user)):
    require_chat_owned_by(chat_id, user_id)
    db.update_chat_title(chat_id, payload.title)
    return {"ok": True}


@api.delete("/chats/{chat_id}")
def remove_chat(chat_id: str, user_id: str = Depends(require_user)):
    require_chat_owned_by(chat_id, user_id)
    db.delete_chat(chat_id)
    return {"ok": True}


# ── Endpoints: messages ───────────────────────────────────────────────────────

@api.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str, user_id: str = Depends(require_user)):
    require_chat_owned_by(chat_id, user_id)
    msgs = db.get_messages(chat_id)
    return [{**m, "id": str(m["id"]), "chat_id": str(m["chat_id"]),
             "created_at": m["created_at"].isoformat()} for m in msgs]


@api.post("/chats/{chat_id}/messages", response_model=ChatResponse)
def send_message(
    chat_id: str,
    payload: MessageIn,
    user_id: str = Depends(require_user),
    provider: str = Depends(get_provider),
):
    chat = require_chat_owned_by(chat_id, user_id)
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Mensaje vacio.")

    # 1. Persistir mensaje del usuario
    db.add_message(chat_id, role="user", content=payload.content)

    # 2. Recuperar historial completo de la conversacion
    history = db.get_messages(chat_id)
    prior_history = history[:-1]

    # 3. Ejecutar el agente
    try:
        answer, tools_used = run_agent(
            payload.content, prior_history,
            provider=provider, sampling=payload.sampling,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del agente: {e}")

    # 4. Persistir respuesta del asistente
    tool_used = tools_used[0] if tools_used else None
    db.add_message(chat_id, role="assistant", content=answer, tool_used=tool_used)
    db.touch_chat(chat_id)

    # 5. Autotitulo si la conversacion sigue siendo "Nueva conversacion"
    if chat["title"] == "Nueva conversacion":
        snippet = payload.content[:40].strip()
        db.update_chat_title(chat_id, snippet + ("..." if len(payload.content) > 40 else ""))

    return ChatResponse(answer=answer, tools_used=tools_used)


@api.post("/chats/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    payload: MessageIn,
    user_id: str = Depends(require_user),
    provider: str = Depends(get_provider),
):
    """Version streaming del envio de mensaje (SSE).

    El cliente recibe eventos `tool_start`, `tool_end`, `token` y `done` en
    tiempo real, lo que permite mostrar 'pensando...', 'consultando datos
    estructurados...', y la respuesta token a token (efecto maquina de
    escribir).
    """
    chat = require_chat_owned_by(chat_id, user_id)
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Mensaje vacio.")

    # Persistir mensaje del usuario y obtener historial previo
    db.add_message(chat_id, role="user", content=payload.content)
    history = db.get_messages(chat_id)
    prior_history = history[:-1]

    async def event_stream():
        import traceback
        full_answer = ""
        tools_used: list[str] = []
        try:
            async for event in stream_agent(
                payload.content, prior_history,
                provider=provider, sampling=payload.sampling,
            ):
                if event["type"] == "done":
                    full_answer = event["answer"]
                    tools_used = event["tools_used"]
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            # Imprimir stack completo en consola del backend
            print("=" * 60)
            print(f"[ERROR STREAM] chat_id={chat_id} user={user_id}")
            traceback.print_exc()
            print("=" * 60)
            err = {"type": "error", "message": f"{type(e).__name__}: {e}"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
            # Guardar un mensaje de error como respuesta del asistente para
            # que el historial muestre que algo paso
            db.add_message(
                chat_id, role="assistant",
                content=f"_⚠ Error al procesar la pregunta: {type(e).__name__}_",
                tool_used=None,
            )
            db.touch_chat(chat_id)
            return

        # Persistir respuesta del asistente al terminar el stream
        tool_used = tools_used[0] if tools_used else None
        db.add_message(chat_id, role="assistant", content=full_answer, tool_used=tool_used)
        db.touch_chat(chat_id)

        # Autotitulo si la conversacion sigue siendo "Nueva conversacion"
        if chat["title"] == "Nueva conversacion":
            snippet = payload.content[:40].strip()
            db.update_chat_title(chat_id, snippet + ("..." if len(payload.content) > 40 else ""))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # desactiva buffering de Nginx si aplica
            "Connection": "keep-alive",
        },
    )


@api.get("/health")
def health():
    return {
        "status": "ok",
        "providers": {
            "commercial": os.getenv("OPENAI_MODEL", "gpt-5.1"),
            "local": os.getenv("OPENROUTER_MODEL", "qwen/qwen3.5-9b"),
        },
        "users": db.ALLOWED_USERS,
    }


# ── Registrar el router de la API ────────────────────────────────────────────

app.include_router(api)


# ── Servir el frontend buildeado (SPA) ───────────────────────────────────────
# En produccion, el Dockerfile multi-stage copia `frontend/dist` a `backend/static`.
# En desarrollo esta carpeta no existe — el frontend corre con `npm run dev` en :5173.

if STATIC_DIR.exists():
    # Sirve los assets de Vite (JS, CSS, imagenes) con cache-control correcto
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Cualquier ruta no-API devuelve index.html (client-side routing del SPA).

        Si el archivo existe en /static (favicon, etc.), lo sirve directamente;
        de lo contrario, devuelve index.html para que React maneje la ruta.
        """
        target = STATIC_DIR / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")
