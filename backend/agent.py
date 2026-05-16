"""
Agente conversacional con router de herramientas.

El LLM (OpenAI) recibe la pregunta del usuario junto con el historial de la
conversacion y DECIDE automaticamente cual herramienta usar:

- `search_knowledge_base`: para preguntas abiertas (RAG sobre FAISS).
- `get_company_info`: para datos estructurados (contacto, sedes, NIT, etc.).

Tambien puede responder directamente sin herramienta si la pregunta es
conversacional pura (saludos, agradecimientos, aclaraciones).
"""

import os

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from tools.rag_tool import search_knowledge_base
from tools.structured_tool import get_company_info

# Proveedores de LLM soportados
PROVIDERS = ("commercial", "local")
DEFAULT_OPENAI_MODEL = "gpt-5.1"
# "local" en realidad usa OpenRouter (API OpenAI-compatible) con un modelo Qwen.
# Lo mantenemos como "local" en la UI por coherencia con el modulo 1, donde
# representa el modelo open-source. La diferencia funcional vs comercial sigue
# siendo: distinto proveedor, distintos parametros, distinto costo.
DEFAULT_OPENROUTER_MODEL = "qwen/qwen3.5-9b"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


SYSTEM_PROMPT = """Eres el asistente virtual oficial de Smurfit Kappa Colombia \
(Carton de Colombia / Smurfit Westrock), empresa lider en empaques sostenibles \
con mas de 80 anos de historia en Colombia.

# ROL Y AUDIENCIA
Atiendes consultas de tres perfiles: (a) clientes y prospectos B2B, \
(b) proveedores, (c) visitantes que investigan a la empresa. \
Tu tono es profesional, preciso y conciso. Sin lenguaje de marketing.

# HERRAMIENTAS DISPONIBLES
Tienes acceso a DOS herramientas. Debes decidir cual usar (o usar las dos) \
para cada pregunta del usuario.

## Herramienta 1: `get_company_info(query)` — DATOS ESTRUCTURADOS
Fuente: base de datos JSON curada manualmente (deterministica).
Usar cuando la pregunta busque un DATO CONCRETO Y PUNTUAL:
- Telefonos, correos, sitio web, redes sociales
- NIT, razon social, nombre comercial
- Horarios de atencion
- Direcciones exactas de plantas y sedes
- Cantidad de empleados (global o por planta)
- Certificaciones por planta (FSC, ISO, LEED)
- Anos de fundacion, fusiones, hectareas forestales

## Herramienta 2: `search_knowledge_base(query)` — RAG DOCUMENTAL
Fuente: indice FAISS sobre el sitio web oficial (recuperacion semantica).
Usar cuando la pregunta sea ABIERTA, NARRATIVA O CUALITATIVA:
- Descripcion de productos y servicios (que es X, para que sirve)
- Historia narrativa, evolucion corporativa, hitos
- Sostenibilidad, valores, compromisos ambientales
- Procesos productivos, tecnologias, innovacion
- Cualquier consulta cualitativa sin un dato concreto exacto.

# PROCESO PARA RESPONDER (chain-of-thought obligatorio)
Sigue estos pasos en orden para cada pregunta:

1. CLASIFICA la pregunta:
   - ¿Pide un DATO PUNTUAL (numero, direccion, fecha, contacto)? -> Herramienta 1
   - ¿Pide una EXPLICACION o DESCRIPCION? -> Herramienta 2
   - ¿Pide AMBAS COSAS? -> Llama a las dos herramientas y combina.
   - ¿Es conversacional ("hola", "gracias")? -> Responde sin herramientas.

2. SI HAY HISTORIAL DE CONVERSACION:
   - Resuelve referencias (pronombres "ese", "el primero", "ahi") usando \
   el contexto previo ANTES de llamar a la herramienta.
   - Reformula la consulta de la herramienta con el sujeto explicito.

3. LLAMA A LA HERRAMIENTA CORRECTA con un query claro y especifico.

4. SINTETIZA la respuesta a partir del resultado de la herramienta.
   No la copies literal: integra los datos en una respuesta natural.

5. SI LA HERRAMIENTA NO TIENE LA INFORMACION:
   Responde EXACTAMENTE: "Esa informacion no esta disponible en la \
documentacion oficial. Te recomiendo contactar directamente a Smurfit \
Kappa Colombia al telefono +57 (602) 691 4000 o servicioalcliente.co@smurfitwestrock.com."

# EJEMPLOS DE ROUTING (zero-shot guidance)

Ejemplo A — dato puntual:
  Usuario: "¿Cual es el NIT de la empresa?"
  Razonamiento: dato concreto numerico -> Herramienta 1.
  Accion: get_company_info("NIT")

Ejemplo B — pregunta abierta:
  Usuario: "¿Que es la cartulina Optima?"
  Razonamiento: definicion / descripcion de producto -> Herramienta 2.
  Accion: search_knowledge_base("cartulina Optima usos caracteristicas")

Ejemplo C — referencia que requiere memoria:
  Historial:
    Usuario: "Hablame de los productos de la empresa"
    Asistente: "Smurfit Kappa fabrica empaques corrugados, cartulina Optima, \
Bag-in-Box, sacos de papel..."
  Usuario actual: "¿Donde fabrican el primero?"
  Razonamiento: "el primero" = empaques corrugados. La pregunta pide \
ubicacion = dato puntual -> Herramienta 1.
  Accion: get_company_info("plantas corrugadoras sedes")

Ejemplo D — pregunta que requiere ambas:
  Usuario: "¿Que productos hacen en la planta de Cali y donde queda?"
  Razonamiento: necesito direccion (dato puntual) + tipo de productos \
(narrativo) -> ambas herramientas.
  Accion 1: get_company_info("planta Cali")
  Accion 2: search_knowledge_base("productos planta Cali")

Ejemplo E — conversacional puro:
  Usuario: "Hola, ¿como estas?"
  Razonamiento: saludo, sin necesidad de informacion.
  Accion: Responder directamente sin herramientas.

# FORMATO DE RESPUESTA

Idioma: español formal pero accesible.

Por tipo de pregunta:
- Dato simple (un valor): respuesta directa en 1-2 oraciones.
  Ej: "El NIT de Smurfit Kappa Cartón de Colombia es 890.300.406-9."

- Listado de sedes/plantas: usa una tabla Markdown con columnas \
**Ciudad | Direccion | Telefono** (y certificaciones si las preguntan).

- Listado de productos o caracteristicas: lista con vinetas.

- Pregunta narrativa (historia, sostenibilidad): 2-4 parrafos cortos. \
Sin marketing exagerado.

- Si llamaste a dos herramientas: integra la respuesta, NO uses \
encabezados tipo "Datos estructurados" / "Documentacion". Hazlo natural.

# RESTRICCIONES ABSOLUTAS (no negociables)

- USA UNICAMENTE la informacion devuelta por las herramientas.
- NO uses conocimiento de preentrenamiento sobre la empresa, NI SIQUIERA \
si crees conocerlo.
- NO inventes telefonos, direcciones, precios, fechas, NITs ni correos.
- NO mezcles informacion de Smurfit Kappa Colombia con la de filiales de \
otros paises.
- NO uses lenguaje de marketing ("lider indiscutible", "el mejor", "innovador \
a nivel mundial") salvo que el documento lo diga literalmente.
- NO inventes los nombres de las herramientas en tu respuesta visible al \
usuario (no digas "consulte la base de datos estructurada"); simplemente \
responde la pregunta.

# CASO ESPECIAL: SIN DATOS

Si DESPUES de llamar a la(s) herramienta(s) correcta(s) la informacion no \
aparece, NO inventes ni redirijas a otra herramienta — responde con la \
frase canonica del paso 5 del proceso."""


def _build_llm(provider: str, sampling: dict | None = None):
    """Crea el LLM segun el proveedor y parametros de muestreo opcionales.

    sampling es un dict con keys parciales:
      temperature, top_p, top_k (solo local), max_tokens, repeat_penalty (local),
      frequency_penalty (commercial), presence_penalty (commercial).
    """
    s = sampling or {}

    if provider == "local":
        # OpenRouter (API OpenAI-compatible) con modelo Qwen
        kwargs = {
            "model": os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
            "base_url": os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL),
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "temperature": s.get("temperature", 0.2),
            "top_p": s.get("top_p", 0.9),
            "frequency_penalty": s.get("frequency_penalty", 0.0),
            "presence_penalty": s.get("presence_penalty", 0.0),
            "streaming": True,
            "default_headers": {
                # OpenRouter pide estos headers para attribution (opcionales)
                "HTTP-Referer": os.getenv("APP_URL", "https://llm.innovatec.co"),
                "X-Title": "Smurfit Westrock Asistente",
            },
        }
        max_tokens = s.get("max_tokens")
        if max_tokens and int(max_tokens) > 0:
            kwargs["max_tokens"] = int(max_tokens)
        return ChatOpenAI(**kwargs)

    # Default: comercial OpenAI directo
    kwargs = {
        "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "temperature": s.get("temperature", 0.2),
        "top_p": s.get("top_p", 1.0),
        "frequency_penalty": s.get("frequency_penalty", 0.0),
        "presence_penalty": s.get("presence_penalty", 0.0),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "streaming": True,
    }
    max_tokens = s.get("max_tokens")
    if max_tokens and int(max_tokens) > 0:
        kwargs["max_tokens"] = int(max_tokens)
    return ChatOpenAI(**kwargs)


def _build_agent(provider: str, sampling: dict | None = None) -> AgentExecutor:
    llm = _build_llm(provider, sampling)
    tools = [get_company_info, search_knowledge_base]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        return_intermediate_steps=True,
        max_iterations=5,
        handle_parsing_errors=True,
    )


# Cache de agentes por proveedor (lazy). Solo se cachean los agentes con
# parametros DEFAULT — si el usuario pasa sampling custom, se construye uno
# nuevo cada vez (el costo es despreciable, microsegundos).
_AGENTS: dict[str, AgentExecutor] = {}


def get_agent(provider: str = "commercial", sampling: dict | None = None) -> AgentExecutor:
    if provider not in PROVIDERS:
        raise ValueError(f"Proveedor invalido: {provider}. Validos: {PROVIDERS}")
    if sampling:
        # Custom sampling: construir fresh, no cachear
        return _build_agent(provider, sampling)
    if provider not in _AGENTS:
        _AGENTS[provider] = _build_agent(provider)
    return _AGENTS[provider]


def db_messages_to_lc(db_messages: list[dict]) -> list:
    """Convierte registros de BD a mensajes de LangChain para el historial."""
    history = []
    for m in db_messages:
        if m["role"] == "user":
            history.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            history.append(AIMessage(content=m["content"]))
    return history


def run_agent(
    user_input: str,
    db_history: list[dict],
    provider: str = "commercial",
    sampling: dict | None = None,
) -> tuple[str, list[str]]:
    """
    Ejecuta el agente sincronicamente. Devuelve (respuesta, herramientas_usadas).
    """
    agent = get_agent(provider, sampling)
    chat_history = db_messages_to_lc(db_history)

    result = agent.invoke({
        "input": user_input,
        "chat_history": chat_history,
    })

    tools_used: list[str] = []
    for step in result.get("intermediate_steps", []):
        action, _observation = step
        tools_used.append(action.tool)

    return result["output"], tools_used


async def stream_agent(
    user_input: str,
    db_history: list[dict],
    provider: str = "commercial",
    sampling: dict | None = None,
):
    """
    Ejecuta el agente con streaming. Es un generador asincrono que produce
    diccionarios listos para serializar como Server-Sent Events:

      {"type": "tool_start",  "tool": "<nombre>"}
      {"type": "tool_end",    "tool": "<nombre>"}
      {"type": "token",       "content": "<texto>"}
      {"type": "done",        "answer": "<texto completo>", "tools_used": [...]}

    Los tokens emitidos solo provienen de la FASE FINAL de respuesta
    (no de los chunks que contienen la decision de tool calling, que tienen
    `content` vacio).
    """
    agent = get_agent(provider, sampling)
    chat_history = db_messages_to_lc(db_history)

    tools_used: list[str] = []
    full_answer = ""
    # Fallback: algunos modelos (ej. ChatOllama con tool-calling) no emiten
    # los tokens del response final via `on_chat_model_stream`. Capturamos
    # el output desde `on_chain_end` del AgentExecutor para no quedarnos sin
    # respuesta visible.
    final_output_fallback = ""

    async for event in agent.astream_events(
        {"input": user_input, "chat_history": chat_history},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_tool_start":
            tools_used.append(event["name"])
            yield {"type": "tool_start", "tool": event["name"]}

        elif kind == "on_tool_end":
            yield {"type": "tool_end", "tool": event["name"]}

        elif kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            content = getattr(chunk, "content", "")
            # Algunos modelos retornan content como lista de partes
            if isinstance(content, list):
                content = "".join(
                    c.get("text", "") if isinstance(c, dict) else str(c)
                    for c in content
                )
            if content:
                full_answer += content
                yield {"type": "token", "content": content}

        elif kind == "on_chain_end":
            # El AgentExecutor emite on_chain_end con el output final.
            # Lo guardamos por si nunca llegaron tokens via stream.
            data = event.get("data", {})
            output = data.get("output")
            if isinstance(output, dict) and "output" in output:
                final_output_fallback = output["output"]

    # Si los tokens no llegaron por streaming, emite la respuesta entera de golpe
    if not full_answer.strip() and final_output_fallback.strip():
        full_answer = final_output_fallback
        yield {"type": "token", "content": final_output_fallback}

    yield {"type": "done", "answer": full_answer, "tools_used": tools_used}
