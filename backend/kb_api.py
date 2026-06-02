"""
Endpoints de "Entrenamiento" — gestion de la base de conocimiento (Modulo 3).

Permite enriquecer la KB en runtime subiendo PDFs (se extraen, se dividen en
chunks con RecursiveCharacterTextSplitter, se embeben con Gemini y se insertan
en PGVector) y muestra el estado actual de la KB para el dashboard.

  GET    /api/kb/status          -> metricas de la KB
  GET    /api/kb/documents       -> PDFs ingeridos
  POST   /api/kb/upload          -> subir y procesar un PDF
  DELETE /api/kb/documents/{id}  -> eliminar un PDF y sus chunks
"""

import io
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

import kb_store
from deps import require_user

kb_router = APIRouter(prefix="/api/kb")


def _embed_document_bg(doc_id: str, docs: list[Document], ids: list[str]) -> None:
    """Tarea en background: genera embeddings y los inserta en PGVector.
    Actualiza el estado del documento (ready / error) al terminar."""
    try:
        kb_store.add_documents_batched(docs, ids, batch=20)
        kb_store.update_document_status(doc_id, "ready", error=None)
        print(f"[kb] documento {doc_id} procesado: {len(docs)} chunks.")
    except Exception as e:
        print(f"[kb] error procesando {doc_id}: {e}")
        # Limpieza de chunks parciales + marcar error
        try:
            kb_store.get_vectorstore().delete(ids=ids)
        except Exception:
            pass
        kb_store.update_document_status(doc_id, "error", error=str(e)[:500])


@kb_router.get("/status")
def kb_status(user_id: str = Depends(require_user)):
    return kb_store.kb_status()


@kb_router.get("/documents")
def kb_documents(user_id: str = Depends(require_user)):
    return kb_store.list_documents()


@kb_router.delete("/documents/{doc_id}")
def kb_delete(doc_id: str, user_id: str = Depends(require_user)):
    doc = kb_store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    kb_store.delete_document(doc_id, doc["chunk_count"])
    return {"ok": True, "deleted_chunks": doc["chunk_count"]}


@kb_router.post("/upload")
def kb_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(require_user),
):
    """Sube un PDF. La extraccion + chunking se hace al instante; los embeddings
    (lo lento) se procesan en BACKGROUND para no bloquear la peticion ni timeoutear
    con PDFs grandes. El front muestra el estado 'procesando' y hace polling."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Archivo vacio.")

    # 1. Extraer texto del PDF
    try:
        reader = PdfReader(io.BytesIO(raw))
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el PDF: {e}")

    text = text.strip()
    if len(text) < 50:
        raise HTTPException(
            status_code=400,
            detail="El PDF no contiene texto extraible (¿es un escaneo sin OCR?).",
        )

    # 2. Chunking (rapido)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No se generaron chunks del PDF.")

    # 3. Registrar como 'procesando' y agendar los embeddings en background
    doc_id = uuid.uuid4().hex
    source = f"{kb_store.SOURCE_PDF_PREFIX}:{file.filename}"
    docs = [
        Document(
            page_content=c,
            metadata={"source": source, "doc_id": doc_id, "filename": file.filename},
        )
        for c in chunks
    ]
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]

    kb_store.register_document(
        doc_id=doc_id, filename=file.filename, chunk_count=len(chunks),
        char_count=len(text), uploaded_by=user_id, status="processing",
    )
    background_tasks.add_task(_embed_document_bg, doc_id, docs, ids)

    return {
        "ok": True,
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
        "chars": len(text),
        "status": "processing",
    }
