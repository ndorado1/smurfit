"""
Vector store de la base de conocimiento, respaldado por PostgreSQL + pgvector.

Reemplaza el FAISS-en-archivo del Modulo 2 por un vector store mutable y
persistente (PGVector), lo que habilita el feature de "Entrenamiento":
subir PDFs en runtime que enriquecen la KB sin reconstruir la imagen.

Reutilizado por:
  - ingest_kb.py   (siembra inicial del web scraping)
  - agent.py       (recuperacion semantica via dynamic_prompt)
  - kb_api.py      (endpoints de estado / upload / delete)

Embeddings: Google Gemini gemini-embedding-2 GA (3072 dims, multimodal).
Busqueda: exacta (sin indice HNSW/ivfflat — a esta escala es instantanea
y pgvector limita los indices a ~2000 dims).
"""

import os
import time
from urllib.parse import quote_plus

import psycopg
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from psycopg.rows import dict_row

# Modelo MULTIMODAL de embeddings de Gemini (texto, imagenes, PDFs).
# gemini-embedding-2 GA (ya no preview): 3072 dims, cuota amplia.
# Mandatorio para documentos complejos.
EMBED_MODEL = "models/gemini-embedding-2"
EMBED_DIMS = 3072
COLLECTION_NAME = "smurfit_kb"

# Fuentes de chunks (queda en metadata.source de cada documento)
SOURCE_WEB = "web_scraping"
SOURCE_PDF_PREFIX = "pdf"  # ej. "pdf:catalogo_2026.pdf"


def connection_url() -> str:
    """URL SQLAlchemy para PGVector. URL-encodea el password (puede tener '+')."""
    user = os.getenv("KB_DB_USER", "postgres")
    pw = quote_plus(os.getenv("KB_DB_PASSWORD", ""))
    host = os.getenv("KB_DB_HOST", "easypanel.innovatec.co")
    port = os.getenv("KB_DB_PORT", "5439")
    db = os.getenv("KB_DB_NAME", "supabase")
    return f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"


_embeddings: GoogleGenerativeAIEmbeddings | None = None


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY no configurada en el entorno.")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBED_MODEL, google_api_key=api_key
        )
    return _embeddings


_vectorstore: PGVector | None = None


def get_vectorstore() -> PGVector:
    """Devuelve (lazy, singleton) el PGVector de la KB."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = PGVector(
            embeddings=get_embeddings(),
            collection_name=COLLECTION_NAME,
            connection=connection_url(),
            use_jsonb=True,
        )
    return _vectorstore


# ── Conexion psycopg directa (para metricas y tabla de documentos) ────────────

def _pg_conn() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("KB_DB_HOST", "easypanel.innovatec.co"),
        port=os.getenv("KB_DB_PORT", "5439"),
        dbname=os.getenv("KB_DB_NAME", "supabase"),
        user=os.getenv("KB_DB_USER", "postgres"),
        password=os.getenv("KB_DB_PASSWORD", ""),
        autocommit=True,
        row_factory=dict_row,
    )


def init_kb_schema() -> None:
    """Crea la tabla de documentos subidos (PDFs). Idempotente."""
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_documents (
                doc_id       TEXT PRIMARY KEY,
                filename     TEXT NOT NULL,
                chunk_count  INTEGER NOT NULL DEFAULT 0,
                char_count   INTEGER NOT NULL DEFAULT 0,
                uploaded_by  TEXT,
                uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )


# ── Insercion por lotes con retry (compartida con ingest_kb.py) ───────────────

def add_documents_batched(
    docs: list[Document],
    ids: list[str],
    batch: int = 20,
    on_progress=None,
) -> None:
    """Inserta documentos en PGVector en lotes, con reintento ante 429 de Gemini."""
    vs = get_vectorstore()
    total = len(docs)
    for i in range(0, total, batch):
        bd, bi = docs[i : i + batch], ids[i : i + batch]
        for attempt in range(4):
            try:
                vs.add_documents(bd, ids=bi)
                break
            except Exception as e:
                msg = str(e)
                if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) and attempt < 3:
                    time.sleep(30)
                else:
                    raise
        if on_progress:
            on_progress(min(i + batch, total), total)
        if i + batch < total:
            time.sleep(1.0)


# ── Tabla de documentos subidos ───────────────────────────────────────────────

def register_document(doc_id: str, filename: str, chunk_count: int,
                      char_count: int, uploaded_by: str | None) -> None:
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO kb_documents (doc_id, filename, chunk_count, char_count, uploaded_by)
               VALUES (%s, %s, %s, %s, %s)""",
            (doc_id, filename, chunk_count, char_count, uploaded_by),
        )


def list_documents() -> list[dict]:
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM kb_documents ORDER BY uploaded_at DESC")
        rows = cur.fetchall()
    return [{**r, "uploaded_at": r["uploaded_at"].isoformat()} for r in rows]


def get_document(doc_id: str) -> dict | None:
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM kb_documents WHERE doc_id = %s", (doc_id,))
        return cur.fetchone()


def delete_document(doc_id: str, chunk_count: int) -> None:
    """Borra los chunks del PDF en PGVector y su registro."""
    ids = [f"{doc_id}_{i}" for i in range(chunk_count)]
    if ids:
        get_vectorstore().delete(ids=ids)
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM kb_documents WHERE doc_id = %s", (doc_id,))


# ── Estado de la KB (dashboard de Entrenamiento) ──────────────────────────────

def kb_status() -> dict:
    with _pg_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM langchain_pg_embedding")
        total = cur.fetchone()["n"]
        cur.execute(
            """SELECT count(*) AS n FROM langchain_pg_embedding
               WHERE cmetadata->>'source' = %s""",
            (SOURCE_WEB,),
        )
        web = cur.fetchone()["n"]
        cur.execute("SELECT count(*) AS n FROM kb_documents")
        n_docs = cur.fetchone()["n"]
    return {
        "total_chunks": total,
        "chunks_web_scraping": web,
        "chunks_pdf": total - web,
        "documentos_pdf": n_docs,
        "modelo_embeddings": EMBED_MODEL.replace("models/", ""),
        "dimensiones": EMBED_DIMS,
        "vector_store": "PostgreSQL + pgvector",
        "coleccion": COLLECTION_NAME,
    }
