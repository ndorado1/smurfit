"""
Checkpointer de memoria conversacional — AsyncPostgresSaver (Modulo 3).

Reemplaza la inyeccion manual de historial del Modulo 2. Con el checkpointer,
cada turno solo envia el mensaje nuevo + un thread_id; el checkpointer
restaura automaticamente todo el historial de esa conversacion.

Se usa la variante ASYNC porque el agente se ejecuta con astream/ainvoke
(FastAPI async). El checkpointer se inicializa una vez en el lifespan.

thread_id:
  - Web UI   -> el UUID del chat
  - WhatsApp -> el numero de telefono del usuario

Vive en el mismo Postgres+pgvector del Modulo 3 (servicio 'supabase').
"""

import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def _conninfo() -> str:
    # Formato keyword de psycopg (no URL) — el password puede tener '+' sin encodear.
    return (
        f"host={os.getenv('KB_DB_HOST', 'easypanel.innovatec.co')} "
        f"port={os.getenv('KB_DB_PORT', '5439')} "
        f"dbname={os.getenv('KB_DB_NAME', 'supabase')} "
        f"user={os.getenv('KB_DB_USER', 'postgres')} "
        f"password={os.getenv('KB_DB_PASSWORD', '')}"
    )


_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def setup_checkpointer() -> AsyncPostgresSaver:
    """Inicializa el pool async + checkpointer y crea sus tablas. Idempotente.
    Llamar una vez en el lifespan del servidor."""
    global _pool, _checkpointer
    if _checkpointer is None:
        _pool = AsyncConnectionPool(
            conninfo=_conninfo(),
            max_size=10,
            open=False,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
        )
        await _pool.open()
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
    return _checkpointer


def get_checkpointer() -> AsyncPostgresSaver:
    """Devuelve el checkpointer ya inicializado (sync getter)."""
    if _checkpointer is None:
        raise RuntimeError(
            "Checkpointer no inicializado. Llama setup_checkpointer() en el lifespan."
        )
    return _checkpointer


async def close_checkpointer() -> None:
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
    _pool = None
    _checkpointer = None
