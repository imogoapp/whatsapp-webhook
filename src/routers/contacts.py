from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from src.db.storage import db

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)

# Models
class ContactNameUpdate(BaseModel):
    name: str

class ContactResponse(BaseModel):
    id: int
    wa_id: str
    profile: str
    name: Optional[str]
    create_in: str
    activate_bot: bool
    activate_automatic_message: bool
    create_for_phone_number: str
    last_message_timestamp: Optional[int]

# ==================== ENDPOINTS ====================

@router.get("/by-phone/{phone_number_id}")
def get_contacts_by_phone(
    phone_number_id: str, 
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=500)
):
    """Lista contatos por phone_number_id (settings)"""
    contacts = db.get_contacts_by_phone_number(phone_number_id, skip, limit)
    return {
        "total": len(contacts),
        "skip": skip,
        "limit": limit,
        "data": contacts
    }

@router.get("/{contact_id}")
def get_contact(contact_id: int):
    """Busca um contato pelo ID"""
    contact = db.get_contact(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    return contact

@router.patch("/{contact_id}/name")
def update_contact_name(contact_id: int, payload: ContactNameUpdate):
    """Atualiza o nome do contato"""
    result = db.update_contact_name(contact_id, payload.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{contact_id}/automatic-message/activate")
def activate_automatic_message(contact_id: int):
    """Ativa mensagem automática"""
    result = db.set_contact_automatic_message(contact_id, True)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{contact_id}/automatic-message/deactivate")
def deactivate_automatic_message(contact_id: int):
    """Desativa mensagem automática"""
    result = db.set_contact_automatic_message(contact_id, False)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{contact_id}/bot/activate")
def activate_bot(contact_id: int):
    """Ativa bot do contato"""
    result = db.set_contact_bot(contact_id, True)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{contact_id}/bot/deactivate")
def deactivate_bot(contact_id: int):
    """Desativa bot do contato"""
    result = db.set_contact_bot(contact_id, False)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result