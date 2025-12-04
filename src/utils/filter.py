from typing import Any, Dict
from src.db.storage import db
from src.utils.websocket_manager import manager
import asyncio


def receiver_from_metadata(metadata: Dict[str, Any]) -> str:
    """Extrai o receptor dos metadados"""
    return metadata.get("display_phone_number") or metadata.get("phone_number_id") or "-"


def extract_message_text(msg: Dict[str, Any]) -> str:
    """Extrai o texto/conteúdo de qualquer tipo de mensagem"""
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


def translate_status(status: str) -> str:
    """Traduz status para português"""
    mapa = {
        "sent": "enviada",
        "delivered": "entregue",
        "read": "lida",
        "failed": "falhou",
        "deleted": "apagada",
        "pending": "pendente"
    }
    return mapa.get((status or "").lower(), status or "-")


def process_messages(value: Dict[str, Any]) -> None:
    """Processa mensagens recebidas"""
    metadata = value.get("metadata", {})
    receiver = receiver_from_metadata(metadata)
    phone_number_id = metadata.get("phone_number_id", "-")

    for msg in value.get("messages", []):
        sender = msg.get("from") or "-"
        msg_type = msg.get("type") or "-"
        body = extract_message_text(msg) or "-"
        timestamp = msg.get("timestamp", 0)
        
        print("\n" + "="*50)
        print("📨 MENSAGEM RECEBIDA")
        print("="*50)
        print(f"Quem enviou: {sender}")
        print(f"Quem Recebeu: {receiver}")
        print(f"Phone Number ID: {phone_number_id}")
        print(f"Tipo de mensagem: {msg_type}")
        print(f"Mensagem: {body}")
        print(f"Timestamp: {timestamp}")
        print("="*50 + "\n")
        
        # Salva/atualiza contato
        for contact in value.get("contacts", []):
            wa_id = contact.get("wa_id")
            name = (contact.get("profile") or {}).get("name")
            if wa_id and phone_number_id != "-":
                db.save_or_update_contact(
                    wa_id=wa_id,
                    name=name or wa_id,
                    phone_number_id=phone_number_id,
                    timestamp=int(timestamp)
                )


def process_statuses(value: Dict[str, Any]) -> None:
    """Processa atualizações de status"""
    metadata = value.get("metadata", {})
    business = metadata.get("display_phone_number") or metadata.get("phone_number_id") or "-"

    for st in value.get("statuses", []):
        recipient = st.get("recipient_id") or "-"
        status_pt = translate_status(st.get("status"))
        msg_id = st.get("id") or "-"
        
        print("\n" + "="*50)
        print("📊 STATUS ATUALIZADO")
        print("="*50)
        print(f"Quem enviou: {business}")
        print(f"Quem Recebeu: {recipient}")
        print(f"Status da mensagem: {status_pt}")
        print(f"Mensagem ID: {msg_id}")
        print("="*50 + "\n")


def process_contacts_only(value: Dict[str, Any]) -> None:
    """Processa eventos de contato sem mensagem"""
    metadata = value.get("metadata", {})
    receiver = receiver_from_metadata(metadata)
    
    for c in value.get("contacts", []):
        sender = c.get("wa_id") or "-"
        name = (c.get("profile") or {}).get("name") or "-"
        
        print("\n" + "="*50)
        print("👤 EVENTO DE CONTATO")
        print("="*50)
        print(f"Quem enviou: {sender}")
        print(f"Quem Recebeu: {receiver}")
        print(f"Nome: {name}")
        print("="*50 + "\n")


def process_webhook_payload(data: dict):
    """Processa o payload do webhook"""
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            
            phone_number_id = metadata.get("phone_number_id", "-")
            messages = value.get("messages")
            
            if messages:
                for message in messages:
                    msg_from = message.get("from")
                    msg_type = message.get("type")
                    timestamp = message.get("timestamp")
                    
                    contact_name = "Desconhecido"
                    contacts = value.get("contacts", [])
                    if contacts:
                        profile = contacts[0].get("profile", {})
                        contact_name = profile.get("name", "Desconhecido")
                    
                    db.save_or_update_contact(
                        wa_id=msg_from,
                        name=contact_name,
                        phone_number_id=phone_number_id,
                        timestamp=int(timestamp)
                    )
                    
                    content = ""
                    if msg_type == "text":
                        content = message.get("text", {}).get("body", "")
                    elif msg_type in ["image", "video", "audio", "document"]:
                        content = f"[{msg_type.upper()}] {message.get(msg_type, {}).get('caption', 'Sem legenda')}"
                    
                    saved_message = db.create_session_message(
                        wa_id=msg_from,
                        wa_id_received=metadata.get("display_phone_number", phone_number_id),
                        phone_number_id=phone_number_id,
                        content=content,
                        payload=message,
                        is_user_message=True,
                        message_status='received'
                    )
                    
                    # 🔥 ENVIA VIA WEBSOCKET
                    if saved_message:
                        ws_payload = {
                            "type": "new_message",
                            "phone_number_id": phone_number_id,
                            "wa_id": msg_from,
                            "contact_name": contact_name,
                            "message": {
                                "id": saved_message["id"],
                                "content": content,
                                "message_type": msg_type,
                                "timestamp": timestamp,
                                "is_user_message": True,
                                "session_id": saved_message["session_id"]
                            }
                        }
                        
                        # Envia para conexões específicas do número
                        asyncio.create_task(manager.broadcast_to_phone(phone_number_id, ws_payload))
                        
                        # Envia para conexões globais
                        asyncio.create_task(manager.broadcast_global(ws_payload))
                        
                        # Envia atualização para lista de chats
                        asyncio.create_task(manager.broadcast_to_phone(
                            f"chats_{phone_number_id}",
                            {
                                "type": "chat_updated",
                                "phone_number_id": phone_number_id,
                                "wa_id": msg_from,
                                "contact_name": contact_name,
                                "last_message": content,
                                "timestamp": timestamp
                            }
                        ))
                    
                    print(f"  └─ Tipo: {msg_type}")
                    if msg_type == "text":
                        print(f"  └─ Mensagem: {content}")
            
            if value.get("statuses"):
                process_statuses(value)
            
            if value.get("contacts") and not value.get("messages") and not value.get("statuses"):
                process_contacts_only(value)