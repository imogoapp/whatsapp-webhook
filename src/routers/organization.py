from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from src.db.storage import db

router = APIRouter(
    prefix="/organization",
    tags=["Organization"]
)

# Models
class OrgCreate(BaseModel):
    organization_name: str = Field(min_length=1)
    create_by: Optional[int] = None

class OrgRename(BaseModel):
    organization_name: str = Field(min_length=1)

class OrgUserLink(BaseModel):
    user_id: int
    role: Optional[str] = Field(default="user", pattern="^(user|user_admin|user_creator)$")

class OrgUserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(user|user_admin|user_creator)$")

class OrgSettingsCreate(BaseModel):
    default_bot: Optional[str] = None
    default_profile: Optional[str] = "human"
    wa_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    meta_token: Optional[str] = None

# ==================== CRUD ORGANIZAÇÃO ====================
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrgCreate):
    """Cria uma nova organização"""
    org = db.create_organization(payload.organization_name, payload.create_by)
    if not org:
        raise HTTPException(status_code=500, detail="Erro ao criar organização")
    return org

@router.get("/")
def list_organizations(skip: int = 0, limit: int = 100):
    """Lista todas as organizações"""
    orgs = db.get_all_organizations(skip, limit)
    return orgs

@router.get("/{org_id}")
def get_organization(org_id: int):
    """Busca uma organização pelo ID"""
    org = db.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return org

@router.patch("/{org_id}/deactivate")
def deactivate_organization(org_id: int):
    """Desativa uma organização"""
    org = db.deactivate_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return {"success": True, "message": f"Organização ID {org_id} desativada", "data": org}

@router.patch("/{org_id}/name")
def rename_organization(org_id: int, payload: OrgRename):
    """Atualiza o nome da organização"""
    org = db.update_organization_name(org_id, payload.organization_name)
    if not org:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return {"success": True, "message": "Nome atualizado", "data": org}

# ==================== USUÁRIOS DA ORGANIZAÇÃO ====================
@router.post("/{org_id}/users")
def add_user(org_id: int, payload: OrgUserLink):
    """Adiciona um usuário à organização"""
    result = db.add_user_to_organization(org_id, payload.user_id, payload.role or 'user')
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.get("/{org_id}/users")
def list_organization_users(org_id: int):
    """Lista todos os usuários de uma organização"""
    users = db.list_organization_users(org_id)
    return users

@router.delete("/{org_id}/users/{user_id}")
def remove_user(org_id: int, user_id: int):
    """Remove um usuário da organização"""
    result = db.remove_user_from_organization(org_id, user_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{org_id}/users/{user_id}/role")
def update_user_role(org_id: int, user_id: int, payload: OrgUserRoleUpdate):
    """Atualiza o papel do usuário na organização"""
    result = db.update_organization_user_role(org_id, user_id, payload.role)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{org_id}/users/{user_id}/activate")
def activate_user(org_id: int, user_id: int):
    """Ativa um usuário na organização"""
    result = db.set_organization_user_active(org_id, user_id, True)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.patch("/{org_id}/users/{user_id}/deactivate")
def deactivate_user(org_id: int, user_id: int):
    """Desativa um usuário na organização"""
    result = db.set_organization_user_active(org_id, user_id, False)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

# ==================== ORGANIZAÇÕES DO USUÁRIO ====================
@router.get("/user/{user_id}/organizations")
def list_user_organizations(user_id: int):
    """Lista todas as organizações que o usuário participa"""
    orgs = db.get_user_organizations(user_id)
    return orgs

# ==================== SETTINGS ====================
@router.post("/{org_id}/settings", status_code=status.HTTP_201_CREATED)
def create_settings(org_id: int, payload: OrgSettingsCreate):
    """Cria settings para a organização"""
    row = db.create_settings(
        org_id,
        payload.default_bot,
        payload.default_profile,
        payload.wa_id,
        payload.phone_number_id,
        payload.webhook_verify_token,
        payload.meta_token
    )
    if not row:
        raise HTTPException(status_code=400, detail="Erro ao criar settings")
    return {"success": True, "message": "Settings criado", "data": row}

@router.get("/{org_id}/settings")
def list_organization_settings(org_id: int):
    """Lista todos os settings de uma organização"""
    settings = db.get_organization_settings(org_id)
    return settings

@router.delete("/settings/{settings_id}")
def remove_settings(settings_id: int):
    """Remove settings por ID"""
    ok = db.delete_settings(settings_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Erro ao remover settings")
    return {"success": True, "message": "Settings removido"}