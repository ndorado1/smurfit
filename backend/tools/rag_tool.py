"""
Herramienta RAG sobre la base de conocimiento de Smurfit Kappa Colombia.

Reutiliza el indice FAISS construido en el modulo 1 con embeddings de
Google Gemini (gemini-embedding-2-preview). El indice vive en
`output/faiss_index_gemini/` en la raiz del proyecto.

Esta es la herramienta de informacion no-estructurada: preguntas abiertas,
narrativas, descripciones de productos/servicios, historia, sostenibilidad.
"""

import os
from pathlib import Path

from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# Indice FAISS local al backend (incluido en el repo y en la imagen Docker).
# Estructura esperada: backend/data/faiss_index_gemini/{index.faiss, index.pkl}
_BACKEND_ROOT = Path(__file__).parent.parent
_FAISS_PATH = _BACKEND_ROOT / "data" / "faiss_index_gemini"
_EMBED_MODEL = "models/gemini-embedding-2-preview"
_TOP_K = 4

_vectorstore: FAISS | None = None


def _get_vectorstore() -> FAISS:
    """Carga (lazy) el FAISS existente del modulo 1."""
    global _vectorstore
    if _vectorstore is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY no configurada en el entorno.")

        if not _FAISS_PATH.exists():
            raise RuntimeError(
                f"Indice FAISS no encontrado en {_FAISS_PATH}. "
                "Ejecuta primero `make rag-comercial` para generarlo."
            )

        # Sin override de api_version: gemini-embedding-2-preview solo
        # existe en v1beta (default), no en v1.
        embeddings = GoogleGenerativeAIEmbeddings(
            model=_EMBED_MODEL, google_api_key=api_key
        )

        _vectorstore = FAISS.load_local(
            str(_FAISS_PATH), embeddings, allow_dangerous_deserialization=True
        )
    return _vectorstore


@tool
def search_knowledge_base(query: str) -> str:
    """
    Busca informacion en la base de conocimiento documental de Smurfit Kappa
    Colombia mediante recuperacion semantica (RAG).

    Usa esta herramienta para preguntas abiertas y narrativas sobre:
    - Productos y servicios (descripcion detallada, usos, beneficios)
    - Historia de la empresa, fusiones, evolucion corporativa
    - Sostenibilidad, valores, compromisos ambientales
    - Procesos productivos, tecnologias, innovacion
    - Comunicacion corporativa, noticias, premios
    - Cualquier consulta cualitativa donde no exista un dato concreto.

    NO la uses para preguntas sobre telefonos, direcciones, NIT, horarios,
    correos o numero de empleados — para eso usa `get_company_info`.

    Args:
        query: La pregunta del usuario tal cual o reformulada.

    Returns:
        Hasta 4 fragmentos relevantes del knowledge base separados por '---'.
    """
    vs = _get_vectorstore()
    docs = vs.similarity_search(query, k=_TOP_K)
    if not docs:
        return "No se encontro informacion relevante en la base de conocimiento."
    return "\n\n---\n\n".join(d.page_content for d in docs)
