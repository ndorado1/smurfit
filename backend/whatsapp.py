"""
Integracion con WhatsApp via Meta Cloud API — Via 2 (servidor propio, sin n8n).

Flujo (Modulo 3, punto 3):
  GET  /webhook  -> verificacion del webhook (Meta envia hub.challenge)
  POST /webhook  -> recibe mensajes entrantes

Patron critico de produccion: el POST responde 200 INMEDIATAMENTE y procesa el
mensaje en segundo plano. Si tardara (el agente toma 5-30s), Meta reenviaria el
webhook y el usuario recibiria respuestas duplicadas.

El thread_id del agente = numero de telefono del usuario, de modo que cada
contacto de WhatsApp tiene su propia memoria conversacional persistente.
"""

import hashlib
import hmac
import os

import httpx
from fastapi import APIRouter, BackgroundTasks, Request, Response

from agent import run_agent_collect

wa_router = APIRouter()

GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0")


def _cfg(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# IDs de mensajes ya procesados (best-effort anti-duplicados en memoria).
_seen_message_ids: set[str] = set()


# ── Verificacion del webhook (GET) ────────────────────────────────────────────

@wa_router.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == _cfg("WHATSAPP_VERIFY_TOKEN"):
        return Response(content=challenge or "", media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


# ── Recepcion de mensajes (POST) ──────────────────────────────────────────────

def _valid_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Valida X-Hub-Signature-256 si hay APP_SECRET configurado. Si no, se omite."""
    secret = _cfg("WHATSAPP_APP_SECRET")
    if not secret:
        return True  # validacion desactivada (no hay secret configurado)
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.split("=", 1)[1])


@wa_router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw = await request.body()
    if not _valid_signature(raw, request.headers.get("X-Hub-Signature-256")):
        return Response(status_code=403)

    data = await request.json()

    # Estructura Meta: entry[].changes[].value.messages[]
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue  # solo texto por ahora
                msg_id = msg.get("id", "")
                if msg_id in _seen_message_ids:
                    continue  # duplicado (reintento de Meta)
                _seen_message_ids.add(msg_id)
                phone = msg.get("from", "")
                text = msg.get("text", {}).get("body", "").strip()
                if phone and text:
                    # Procesar en background → responder 200 ya mismo
                    background_tasks.add_task(_process_message, phone, text)

    return Response(status_code=200)


async def _process_message(phone: str, text: str) -> None:
    """Corre el agente (thread_id = telefono) y responde por WhatsApp."""
    try:
        provider = _cfg("WHATSAPP_PROVIDER", "commercial")
        answer = await run_agent_collect(thread_id=phone, user_input=text, provider=provider)
        if not answer:
            answer = ("Disculpa, no pude generar una respuesta en este momento. "
                      "¿Podrias reformular tu pregunta?")
    except Exception as e:
        print(f"[whatsapp] error procesando mensaje de {phone}: {e}")
        answer = ("Estamos teniendo un inconveniente tecnico. Por favor intenta "
                  "de nuevo o contacta a Smurfit Kappa Colombia al +57 (602) 691 4000.")
    await _send_message(phone, answer)


async def _send_message(to: str, text: str) -> None:
    """Envia un mensaje de texto via Meta Cloud API."""
    phone_number_id = _cfg("WHATSAPP_PHONE_NUMBER_ID")
    token = _cfg("WHATSAPP_TOKEN")
    if not phone_number_id or not token:
        print("[whatsapp] faltan WHATSAPP_PHONE_NUMBER_ID o WHATSAPP_TOKEN")
        return

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_number_id}/messages"
    # WhatsApp limita el cuerpo a 4096 chars
    body = text[:4096]
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            print(f"[whatsapp] error enviando a {to}: {resp.status_code} {resp.text}")
