"""
Capa de persistencia con PostgreSQL.

Maneja:
- Inicializacion del schema (tablas chats y messages)
- Connection pool para reusar conexiones (evita handshake TCP+TLS por request)
- CRUD basico de chats y mensajes
- Carga del historial para inyectar en el contexto del agente
"""

import os
import uuid
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _conninfo() -> str:
    # Modulo 3: TODO consolidado en el Postgres pgvector (mismo que kb_store y
    # memory). Se leen primero las KB_DB_* (fuente de verdad); DB_* solo como
    # override opcional. Asi una env DB_* vieja no rompe la conexion.
    host = os.getenv("KB_DB_HOST") or os.getenv("DB_HOST", "easypanel.innovatec.co")
    port = os.getenv("KB_DB_PORT") or os.getenv("DB_PORT", "5439")
    dbname = os.getenv("KB_DB_NAME") or os.getenv("DB_NAME", "supabase")
    user = os.getenv("KB_DB_USER") or os.getenv("DB_USER", "postgres")
    password = os.getenv("KB_DB_PASSWORD") or os.getenv("DB_PASSWORD", "")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


# Pool global. Se crea en open_pool() (lifespan startup) y se cierra en close_pool().
# min_size=2, max_size=10 -> mantiene siempre 2 conexiones abiertas, escala hasta 10
# bajo carga concurrente. Esto evita el TCP+TLS handshake en cada request
# (~100-400ms contra un host remoto como easypanel).
_pool: ConnectionPool | None = None


def open_pool() -> None:
    global _pool
    if _pool is not None:
        return
    _pool = ConnectionPool(
        conninfo=_conninfo(),
        min_size=1,
        max_size=10,
        timeout=15,
        kwargs={"row_factory": dict_row},
        open=True,
    )
    # No bloqueamos el arranque si la DB tarda: el pool conecta en background
    # cuando este disponible. Antes un hipo de la DB tumbaba toda la app.
    try:
        _pool.wait(timeout=8)
    except Exception as e:
        print(f"[db] Pool aun no listo al arranque ({e}); conectara en background.")


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    if _pool is None:
        # Fallback: si nadie llamo a open_pool() todavia (ej. tests), abre uno bajo demanda
        open_pool()
    assert _pool is not None
    with _pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


ALLOWED_USERS = ["antonio", "bradley", "camilo", "simon"]


def init_schema() -> None:
    """Crea las tablas si no existen. Idempotente.

    Tambien agrega la columna user_id a chats si no existe (migracion
    in-place desde una version sin usuarios).
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id          UUID PRIMARY KEY,
                user_id     TEXT NOT NULL DEFAULT 'antonio',
                title       TEXT NOT NULL DEFAULT 'Nueva conversacion',
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            ALTER TABLE chats
                ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'antonio';

            CREATE INDEX IF NOT EXISTS idx_chats_user_updated
                ON chats(user_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS messages (
                id          UUID PRIMARY KEY,
                chat_id     UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
                content     TEXT NOT NULL,
                tool_used   TEXT,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_messages_chat_created
                ON messages(chat_id, created_at);
            """
        )


# ── Chats ─────────────────────────────────────────────────────────────────────

def create_chat(user_id: str, title: str = "Nueva conversacion") -> dict:
    chat_id = str(uuid.uuid4())
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chats (id, user_id, title) VALUES (%s, %s, %s) RETURNING *",
            (chat_id, user_id, title),
        )
        return cur.fetchone()


def list_chats(user_id: str, limit: int = 50) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM chats
            WHERE user_id = %s
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return cur.fetchall()


def get_chat(chat_id: str) -> dict | None:
    """Devuelve un chat por ID o None si no existe (para validar ownership)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM chats WHERE id = %s", (chat_id,))
        return cur.fetchone()


def delete_chat(chat_id: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM chats WHERE id = %s", (chat_id,))


def update_chat_title(chat_id: str, title: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE chats SET title = %s, updated_at = NOW() WHERE id = %s",
            (title, chat_id),
        )


def touch_chat(chat_id: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE chats SET updated_at = NOW() WHERE id = %s", (chat_id,))


# ── Messages ──────────────────────────────────────────────────────────────────

def add_message(
    chat_id: str, role: str, content: str, tool_used: str | None = None
) -> dict:
    msg_id = str(uuid.uuid4())
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (id, chat_id, role, content, tool_used)
            VALUES (%s, %s, %s, %s, %s) RETURNING *
            """,
            (msg_id, chat_id, role, content, tool_used),
        )
        return cur.fetchone()


def get_messages(chat_id: str, limit: int = 200) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM messages
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            (chat_id, limit),
        )
        return cur.fetchall()
