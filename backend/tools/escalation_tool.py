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
    nombre_cliente: str = "",
) -> str:
    """Registra una solicitud de cotizacion para que un asesor comercial de
    Smurfit Westrock contacte al cliente.

    Usar SOLO cuando el cliente exprese intencion concreta de cotizar o comprar
    y haya proporcionado producto, cantidad y un correo de contacto.
    Esta accion queda pendiente de aprobacion de un asesor humano antes de
    confirmarse.
    """
    registro = {
        "producto": producto,
        "cantidad": cantidad,
        "email_contacto": email_contacto,
        "nombre_cliente": nombre_cliente or "(no especificado)",
        "registrado_en": datetime.now(timezone.utc).isoformat(),
        "estado": "aprobado_y_registrado",
    }
    return (
        "Solicitud de cotizacion registrada correctamente. Un asesor comercial "
        f"contactara al cliente.\n{json.dumps(registro, ensure_ascii=False, indent=2)}"
    )
