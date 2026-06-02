"""
Herramienta de accion critica — sujeta a Human-in-the-Loop (Modulo 3).

`registrar_solicitud_cotizacion` simula una accion con efecto de negocio
(registrar un lead comercial que un asesor seguira). Por ser una accion que
"escribe" / compromete a la empresa, el HumanInTheLoopMiddleware la intercepta
y exige aprobacion humana (approve / edit / reject) antes de ejecutarse.

Esto demuestra control de flujos criticos: el agente NO ejecuta acciones
sensibles de forma autonoma sin supervision.
"""

import json
from datetime import datetime, timezone

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Nombre de la tool — referenciado por el HumanInTheLoopMiddleware en agent.py
TOOL_NAME = "registrar_solicitud_cotizacion"


class CotizacionInput(BaseModel):
    """Esquema estricto para registrar una solicitud de cotizacion."""
    producto: str = Field(description="Producto o servicio de interes del cliente.")
    cantidad: str = Field(description="Cantidad o volumen estimado (ej. '5000 cajas/mes').")
    email_contacto: str = Field(description="Correo del cliente para el seguimiento comercial.")
    nombre_cliente: str = Field(default="", description="Nombre del cliente o empresa. Opcional.")


@tool(args_schema=CotizacionInput)
def registrar_solicitud_cotizacion(
    producto: str,
    cantidad: str,
    email_contacto: str,
    runtime: ToolRuntime,
    nombre_cliente: str = "",
) -> str:
    """Registra una solicitud de cotizacion para que un asesor comercial de
    Smurfit Westrock contacte al cliente.

    Usar SOLO cuando el cliente exprese intencion concreta de cotizar o comprar
    y haya proporcionado producto, cantidad y un correo de contacto.
    Esta accion queda pendiente de aprobacion de un asesor humano antes de
    confirmarse.
    """
    # Si el LLM no capturo el nombre del cliente, usa el usuario de la sesion
    # (el perfil web, o el telefono en WhatsApp) inyectado via ToolRuntime.
    cliente = nombre_cliente
    canal = "web"
    try:
        ctx_user = getattr(runtime.context, "user_id", "") or ""
        if not cliente:
            cliente = ctx_user
        # thread_id estilo telefono (solo digitos, >=10) -> canal whatsapp
        if ctx_user.isdigit() and len(ctx_user) >= 10:
            canal = "whatsapp"
    except Exception:
        ctx_user = ""

    # Persiste el lead en la tabla cotizaciones (Postgres). Esta es la accion
    # "critica" que el HumanInTheLoopMiddleware protege: solo se ejecuta tras
    # la aprobacion humana, y aqui SI escribe en la base de datos.
    try:
        import db
        row = db.add_cotizacion(
            producto=producto,
            cantidad=cantidad,
            email_contacto=email_contacto,
            nombre_cliente=cliente,
            canal=canal,
            thread_id=ctx_user or None,
        )
        cot_id = str(row["id"])
    except Exception as e:
        return (f"No se pudo registrar la cotizacion en este momento ({type(e).__name__}). "
                "Por favor intenta de nuevo o contacta a Smurfit Kappa Colombia.")

    registro = {
        "id": cot_id,
        "producto": producto,
        "cantidad": cantidad,
        "email_contacto": email_contacto,
        "nombre_cliente": cliente or "(no especificado)",
        "registrado_en": datetime.now(timezone.utc).isoformat(),
    }
    return (
        f"Solicitud de cotizacion registrada (ID {cot_id[:8]}). Un asesor comercial "
        f"contactara al cliente.\n{json.dumps(registro, ensure_ascii=False, indent=2)}"
    )
