from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from src.db.storage import db
from src.utils.email_sender import send_reset_email

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None


class PasswordUpdate(BaseModel):
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    create_in: str
    activate: bool


class PasswordReset(BaseModel):
    email: EmailStr


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    """Cria um novo usuário"""
    new_user = db.create_user(user.name, user.email, user.password)
    
    if not new_user:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    return {
        "id": new_user["id"],
        "name": new_user["name"],
        "email": new_user["email"],
        "create_in": new_user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
        "activate": new_user["activate"]
    }


@router.get("/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 100):
    """Lista todos os usuários"""
    users = db.get_users(skip, limit)
    
    return [
        {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "create_in": user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
            "activate": user["activate"]
        }
        for user in users
    ]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    """Consulta um usuário específico"""
    user = db.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "create_in": user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
        "activate": user["activate"]
    }


@router.patch("/{user_id}/name", response_model=UserResponse)
def update_user_name(user_id: int, user_update: UserUpdate):
    """Atualiza o nome do usuário"""
    # Verifica se usuário existe
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if not user_update.name:
        raise HTTPException(status_code=400, detail="Nome não pode ser vazio")
    
    updated_user = db.update_user_name(user_id, user_update.name)
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Erro ao atualizar usuário")
    
    return {
        "id": updated_user["id"],
        "name": updated_user["name"],
        "email": updated_user["email"],
        "create_in": updated_user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
        "activate": updated_user["activate"]
    }


@router.patch("/{user_id}/password")
def update_user_password(user_id: int, password_update: PasswordUpdate):
    """Atualiza a senha do usuário"""
    # Verifica se usuário existe
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    success = db.update_user_password(user_id, password_update.password)
    
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao atualizar senha")
    
    return {"message": "Senha atualizada com sucesso"}


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: int):
    """Desativa a conta do usuário"""
    # Verifica se usuário existe
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    updated_user = db.deactivate_user(user_id)
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Erro ao desativar usuário")
    
    return {
        "id": updated_user["id"],
        "name": updated_user["name"],
        "email": updated_user["email"],
        "create_in": updated_user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
        "activate": updated_user["activate"]
    }


@router.patch("/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: int):
    """Ativa a conta do usuário"""
    # Verifica se usuário existe
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    updated_user = db.activate_user(user_id)
    
    if not updated_user:
        raise HTTPException(status_code=500, detail="Erro ao ativar usuário")
    
    return {
        "id": updated_user["id"],
        "name": updated_user["name"],
        "email": updated_user["email"],
        "create_in": updated_user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
        "activate": updated_user["activate"]
    }


@router.post("/reset-password")
def reset_password(payload: PasswordReset):
    """Recupera senha do usuário enviando email com nova senha numérica"""
    result = db.reset_user_password(payload.email)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Envia email com nova senha
    email_sent = send_reset_email(
        nome=result["name"],
        email=result["email"],
        senha=result["new_password"]
    )
    
    if not email_sent:
        # Senha foi alterada mas email falhou
        return {
            "success": True,
            "message": "Senha resetada mas houve erro ao enviar email. Entre em contato com suporte.",
            "email_sent": False
        }
    
    return {
        "success": True,
        "message": f"Nova senha enviada para {result['email']}",
        "email_sent": True
    }