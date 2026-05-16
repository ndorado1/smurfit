"""
Herramienta de datos estructurados.

Lee company_info.json y permite recuperar datos puntuales (NIT, teléfonos,
horarios, sedes, certificaciones) sin pasar por el RAG. Es determinista
y rápida — el agente la elige cuando la pregunta apunta a un dato concreto.
"""

import json
from pathlib import Path
from langchain_core.tools import tool

_DATA_PATH = Path(__file__).parent.parent / "data" / "company_info.json"

with open(_DATA_PATH, encoding="utf-8") as f:
    COMPANY = json.load(f)


@tool
def get_company_info(query: str) -> str:
    """
    Recupera datos estructurados oficiales de Smurfit Kappa Colombia.

    Úsala SIEMPRE para preguntas sobre:
    - NIT, razón social, nombre comercial
    - Teléfonos, correos, sitio web, horarios de atención
    - Direcciones exactas de plantas/sedes
    - Cantidad de empleados por planta o globales
    - Certificaciones por planta (FSC, ISO, LEED)
    - Año de fundación, fusión, datos históricos numéricos
    - Listado de productos principales

    NO la uses para preguntas abiertas sobre productos, servicios, historia
    narrativa o sostenibilidad — para eso usa `search_knowledge_base`.

    Args:
        query: La pregunta o término a buscar (ej. "telefono", "sedes en cali",
               "nit", "horarios", "certificaciones medellin").

    Returns:
        Cadena JSON con la información estructurada relevante.
    """
    q = query.lower()
    result: dict = {}

    # Datos básicos
    if any(k in q for k in ["nit", "razon social", "razón social", "nombre legal"]):
        result["razon_social"] = COMPANY["razon_social"]
        result["nit"] = COMPANY["nit"]

    if any(k in q for k in ["telefono", "teléfono", "contacto", "llamar", "phone"]):
        result["telefono_principal"] = COMPANY["telefono_principal"]
        result["telefonos_por_sede"] = {
            s["ciudad"]: s["telefono"] for s in COMPANY["sedes"]
        }

    if any(k in q for k in ["email", "correo", "mail"]):
        result["email_servicio_cliente"] = COMPANY["email_servicio_cliente"]
        result["email_gerente_general"] = COMPANY["email_gerente_general"]

    if any(k in q for k in ["horario", "atencion", "atención", "horas"]):
        result["horarios_atencion"] = COMPANY["horarios_atencion"]

    if any(k in q for k in ["web", "sitio", "url", "página"]):
        result["sitio_web"] = COMPANY["sitio_web"]

    # Sedes - filtrar por ciudad si se menciona
    sede_cities = ["cali", "bogota", "bogotá", "barranquilla", "medellin", "medellín", "guarne"]
    mencion_ciudad = next((c for c in sede_cities if c in q), None)
    if mencion_ciudad or any(k in q for k in ["sede", "planta", "ubicacion", "ubicación", "direccion", "dirección"]):
        if mencion_ciudad:
            norm = mencion_ciudad.replace("bogota", "bogotá").replace("medellin", "medellín")
            sedes_match = [s for s in COMPANY["sedes"] if norm in s["ciudad"].lower()]
            result["sedes"] = sedes_match if sedes_match else COMPANY["sedes"]
        else:
            result["sedes"] = COMPANY["sedes"]

    # Certificaciones
    if any(k in q for k in ["certificacion", "certificación", "fsc", "iso", "leed"]):
        result["certificaciones_por_sede"] = {
            s["ciudad"]: s["certificaciones"] for s in COMPANY["sedes"]
        }

    # Empleados
    if any(k in q for k in ["empleado", "personal", "trabajador", "plantilla"]):
        result["empleados_global"] = COMPANY["datos_globales"]["empleados_global"]
        result["empleados_por_sede"] = {
            s["ciudad"]: s["empleados_aprox"] for s in COMPANY["sedes"]
        }

    # Datos globales / históricos
    if any(k in q for k in ["fundacion", "fundación", "año", "fusion", "fusión", "global",
                              "paises", "países", "hectareas", "hectáreas", "forestal", "departamento"]):
        result["datos_globales"] = COMPANY["datos_globales"]

    # Productos
    if any(k in q for k in ["producto", "servicio", "fabrica", "fabrica"]):
        result["productos_principales"] = COMPANY["productos_principales"]

    # Si no matcheó nada específico, devolver datos básicos como fallback
    if not result:
        result = {
            "razon_social": COMPANY["razon_social"],
            "nit": COMPANY["nit"],
            "telefono_principal": COMPANY["telefono_principal"],
            "email_servicio_cliente": COMPANY["email_servicio_cliente"],
            "horarios_atencion": COMPANY["horarios_atencion"],
            "sitio_web": COMPANY["sitio_web"],
            "nota": "No se encontro coincidencia especifica; devolviendo datos basicos.",
        }

    return json.dumps(result, ensure_ascii=False, indent=2)
