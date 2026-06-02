"""
Siembra inicial de la base de conocimiento en PGVector.

Lee el knowledge_base_rag.md COMPLETO (producto del web scraping del Modulo 1),
lo divide en chunks con RecursiveCharacterTextSplitter y los inserta en el
vector store PGVector con metadata source="web_scraping".

Usa ids deterministas (hash del contenido) para que re-ejecutar el script
haga UPSERT en lugar de duplicar chunks.

Uso:
    uv run python ingest_kb.py                  # usa output/knowledge_base_rag.md
    uv run python ingest_kb.py /ruta/al/kb.md   # archivo explicito
"""

import hashlib
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from kb_store import SOURCE_WEB, get_vectorstore

# Ruta por defecto: taller-celsia/output/knowledge_base_rag.md
_DEFAULT_KB = Path(__file__).parent.parent.parent / "output" / "knowledge_base_rag.md"

# gemini-embedding-2 GA tiene cuota amplia: batches de 20 sin esperas largas.
BATCH = 20
MAX_RETRIES = 4
SLEEP_BETWEEN_BATCHES = 1.0
WAIT_ON_429 = 30.0


def _chunk_id(text: str) -> str:
    """Id estable por contenido → re-ejecutar hace upsert, no duplica."""
    return "web_" + hashlib.md5(text.encode("utf-8")).hexdigest()


def main() -> None:
    kb_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_KB
    if not kb_path.exists():
        print(f"ERROR: no se encontro el KB en {kb_path}")
        sys.exit(1)

    kb_text = kb_path.read_text(encoding="utf-8")
    print(f"KB leido: {len(kb_text):,} caracteres desde {kb_path.name}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_text(kb_text)
    print(f"Chunks generados: {len(chunks)}")

    # Deduplicar por id (hash del contenido). El KB tiene secciones repetidas
    # que producen chunks identicos → mismo id → colision en el upsert.
    seen: set[str] = set()
    docs: list[Document] = []
    ids: list[str] = []
    for c in chunks:
        cid = _chunk_id(c)
        if cid in seen:
            continue
        seen.add(cid)
        ids.append(cid)
        docs.append(
            Document(
                page_content=c,
                metadata={"source": SOURCE_WEB, "origin": kb_path.name},
            )
        )
    print(f"Chunks unicos (sin duplicados): {len(docs)}")

    vs = get_vectorstore()

    total = len(docs)
    done = 0
    for i in range(0, total, BATCH):
        batch_docs = docs[i : i + BATCH]
        batch_ids = ids[i : i + BATCH]
        for attempt in range(MAX_RETRIES):
            try:
                vs.add_documents(batch_docs, ids=batch_ids)
                break
            except Exception as e:
                msg = str(e)
                if ("429" in msg or "RESOURCE_EXHAUSTED" in msg) and attempt < MAX_RETRIES - 1:
                    print(f"  rate limit en batch {i//BATCH+1}, esperando {WAIT_ON_429:.0f}s (intento {attempt+1})...", flush=True)
                    time.sleep(WAIT_ON_429)
                else:
                    raise
        done = min(i + BATCH, total)
        print(f"  insertados {done}/{total}", flush=True)
        if i + BATCH < total:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    print(f"\nListo. {total} chunks del web scraping sembrados en PGVector "
          f"(coleccion 'smurfit_kb', source='{SOURCE_WEB}').")


if __name__ == "__main__":
    main()
