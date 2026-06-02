"""Dependencias FastAPI compartidas entre main.py y kb_api.py."""

from fastapi import Header, HTTPException

import db
from agent import PROVIDERS


def require_user(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Falta el header X-User-Id.")
    if x_user_id not in db.ALLOWED_USERS:
        raise HTTPException(
            status_code=403,
            detail=f"Usuario no autorizado. Permitidos: {db.ALLOWED_USERS}",
        )
    return x_user_id


def get_provider(x_model_provider: str | None = Header(default=None)) -> str:
    provider = x_model_provider or "commercial"
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Proveedor invalido: {provider}. Validos: {list(PROVIDERS)}",
        )
    return provider
