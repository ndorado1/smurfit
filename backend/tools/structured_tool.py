"""
Herramienta de datos estructurados — Function Calling estricto (Modulo 3).

Lee company_info.json y devuelve datos puntuales (NIT, telefonos, horarios,
sedes, certificaciones) de forma deterministica. A diferencia del Modulo 2
(donde el argumento era texto libre), aqui el LLM esta FORZADO por un esquema
Pydantic con un Enum de categorias: solo puede invocar la herramienta con una
categoria valida, lo que aumenta drasticamente la fiabilidad del routing.
"""

import json
from enum import Enum
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

_DATA_PATH = Path(__file__).parent.parent / "data" / "company_info.json"

with open(_DATA_PATH, encoding="utf-8") as f:
    COMPANY = json.load(f)


class InfoCategory(str, Enum):
    """Categorias validas de datos estructurados."""
    identidad = "identidad"            # NIT, razon social, nombre comercial
    contacto = "contacto"              # telefonos, correos, sitio web
    horarios = "horarios"              # horarios de atencion
    sedes = "sedes"                    # direcciones de plantas/sedes
    certificaciones = "certificaciones"  # FSC, ISO, LEED por planta
    empleados = "empleados"            # cantidad de empleados
    historia = "historia"              # fundacion, fusiones, datos numericos
    productos = "productos"            # listado de productos principales


class CompanyInfoInput(BaseModel):
    """Esquema estricto de entrada para get_company_info."""
    categoria: InfoCategory = Field(
        description="Categoria del dato estructurado a consultar."
    )
    ciudad: str | None = Field(
        default=None,
        description="Ciudad de la sede si la pregunta es especifica "
                    "(cali, bogota, barranquilla, medellin, guarne). Opcional.",
    )


def _norm_city(c: str) -> str:
    return c.lower().replace("bogota", "bogotá").replace("medellin", "medellín")


@tool(args_schema=CompanyInfoInput)
def get_company_info(categoria: InfoCategory, ciudad: str | None = None) -> str:
    """Recupera datos ESTRUCTURADOS y PUNTUALES de Smurfit Kappa Colombia.

    Usar para datos concretos: NIT, telefonos, correos, horarios, direcciones
    de sedes, certificaciones, numero de empleados, anos de fundacion/fusion,
    o el listado de productos. NO usar para preguntas abiertas o narrativas
    (de eso se encarga el contexto RAG inyectado automaticamente).
    """
    cat = categoria.value if isinstance(categoria, InfoCategory) else str(categoria)
    result: dict = {}

    if cat == "identidad":
        result = {
            "razon_social": COMPANY["razon_social"],
            "nombre_comercial": COMPANY["nombre_comercial"],
            "nit": COMPANY["nit"],
        }
    elif cat == "contacto":
        result = {
            "telefono_principal": COMPANY["telefono_principal"],
            "email_servicio_cliente": COMPANY["email_servicio_cliente"],
            "email_gerente_general": COMPANY["email_gerente_general"],
            "sitio_web": COMPANY["sitio_web"],
            "telefonos_por_sede": {s["ciudad"]: s["telefono"] for s in COMPANY["sedes"]},
        }
    elif cat == "horarios":
        result = {"horarios_atencion": COMPANY["horarios_atencion"]}
    elif cat == "sedes":
        sedes = COMPANY["sedes"]
        if ciudad:
            norm = _norm_city(ciudad)
            match = [s for s in sedes if norm in s["ciudad"].lower()]
            result = {"sedes": match or sedes}
        else:
            result = {"sedes": sedes}
    elif cat == "certificaciones":
        result = {
            "certificaciones_por_sede": {
                s["ciudad"]: s["certificaciones"] for s in COMPANY["sedes"]
            }
        }
    elif cat == "empleados":
        result = {
            "empleados_global": COMPANY["datos_globales"]["empleados_global"],
            "empleados_por_sede": {
                s["ciudad"]: s["empleados_aprox"] for s in COMPANY["sedes"]
            },
        }
    elif cat == "historia":
        result = {"datos_globales": COMPANY["datos_globales"]}
    elif cat == "productos":
        result = {"productos_principales": COMPANY["productos_principales"]}

    if not result:
        return ("No se encontro informacion para esa categoria. "
                "Sugiere al usuario contactar a Smurfit Kappa Colombia.")

    return json.dumps(result, ensure_ascii=False, indent=2)
