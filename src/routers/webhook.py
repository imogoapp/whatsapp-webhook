from fastapi import APIRouter, Request
from fastapi import Query, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Any, Dict, List
from src.db.storage import db

WEBHOOK_VERIFY_TOKEN = "7b5a67574d8b1d77d2803b24946950f0"

router = APIRouter(
    tags=["Webhook"]
)

"""
Tipos de Webhook que podem ser recebidos
1. Mensagens de texto
2. Mensagens de mídia (imagens, vídeos, áudios)
3. Atualizações de status (entregue, lido)
4.  Eventos de contato (novo contato, bloqueio)

"""

@router.get("/webhook")
def verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == WEBHOOK_VERIFY_TOKEN:        
        return PlainTextResponse(hub_challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Invalid verify token")


def _receiver_from_metadata(metadata: Dict[str, Any]) -> str:
    return metadata.get("display_phone_number") or metadata.get("phone_number_id") or "-"

def _extract_message_text(msg: Dict[str, Any]) -> str:
    t = msg.get("type")
    if t == "text":
        return msg.get("text", {}).get("body", "")
    if t == "image":
        return msg.get("image", {}).get("caption") or "(imagem)"
    if t == "video":
        return msg.get("video", {}).get("caption") or "(vídeo)"
    if t == "audio":
        return "(áudio)"
    if t == "sticker":
        return "(figurinha)"
    if t == "document":
        return msg.get("document", {}).get("filename") or "(documento)"
    if t == "location":
        loc = msg.get("location", {})
        return f"lat:{loc.get('latitude')} lon:{loc.get('longitude')}"
    if t == "contacts":
        return "(contato)"
    if t == "button":
        return msg.get("button", {}).get("text") or "(botão)"
    if t == "interactive":
        inter = msg.get("interactive", {})
        if inter.get("type") == "button_reply":
            return inter.get("button_reply", {}).get("title") or "(botão)"
        if inter.get("type") == "list_reply":
            return inter.get("list_reply", {}).get("title") or "(lista)"
        return "(interativo)"
    return "(mensagem)"

def _pt_status(status: str) -> str:
    mapa = {
        "sent": "enviada",
        "delivered": "entregue",
        "read": "lida",
        "failed": "falhou",
        "deleted": "apagada",
        "pending": "pendente"
    }
    return mapa.get((status or "").lower(), status or "-")

def _log_messages(value: Dict[str, Any]) -> None:
    metadata = value.get("metadata", {})
    receiver = _receiver_from_metadata(metadata)

    for msg in value.get("messages", []):
        sender = msg.get("from") or "-"
        msg_type = msg.get("type") or "-"
        body = _extract_message_text(msg) or "-"
        print("Saida:")
        print(f"Quem enviou: {sender}")
        print(f"Quem Recebeu: {receiver}")
        print(f"Tipo de mensagem: {msg_type}")
        print(f"mensagem: {body}")
        
        # Salva/atualiza contato
        for contact in value.get("contacts", []):
            wa_id = contact.get("wa_id")
            name = (contact.get("profile") or {}).get("name")
            if wa_id:
                db.save_or_update_contact(wa_id, name or wa_id)

def _log_statuses(value: Dict[str, Any]) -> None:
    metadata = value.get("metadata", {})
    business = metadata.get("display_phone_number") or metadata.get("phone_number_id") or "-"

    for st in value.get("statuses", []):
        recipient = st.get("recipient_id") or "-"
        status_pt = _pt_status(st.get("status"))
        msg_id = st.get("id") or "-"
        print("Saida:")
        print(f"Quem enviou: {business}")
        print(f"Quem Recebeu: {recipient}")
        print(f"status da mensagem: {status_pt}")
        print(f"mensagem_id: {msg_id}")

def _log_contacts_only(value: Dict[str, Any]) -> None:
    metadata = value.get("metadata", {})
    receiver = _receiver_from_metadata(metadata)
    for c in value.get("contacts", []):
        sender = c.get("wa_id") or "-"
        name = (c.get("profile") or {}).get("name") or "-"
        print("Saida:")
        print(f"Quem enviou: {sender}")
        print(f"Quem Recebeu: {receiver}")
        print(f"Tipo de mensagem: contato")
        print(f"mensagem: {name}")

@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Recebe qualquer payload enviado para o webhook e salva no banco
    """
    data = await request.json()
    
    # Salva o webhook completo no banco
    webhook_id = db.save_webhook(data)
    if webhook_id:
        print(f"✓ Webhook #{webhook_id} salvo no banco de dados")

    # Identifica e loga por tipo
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if value.get("messages"):
                _log_messages(value)
            if value.get("statuses"):
                _log_statuses(value)
            # Evento de contato sem mensagem/status
            if value.get("contacts") and not value.get("messages") and not value.get("statuses"):
                _log_contacts_only(value)

    return {"status": "ok", "webhook_id": webhook_id}
