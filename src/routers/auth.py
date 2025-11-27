from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from src.db.storage import db
from src.utils.jwt_handler import create_access_token, verify_token
from typing import Optional

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()

# Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

# Dependency para proteger rotas
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida o token JWT e retorna os dados do usuário"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int = payload.get("user_id")
    email: str = payload.get("email")
    
    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Busca usuário no banco
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )
    
    if not user['activate']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário desativado",
        )
    
    return user

# Endpoints
@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest):
    """Login com email e senha, retorna JWT token"""
    
    # Autentica usuário
    user = db.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria token JWT
    access_token = create_access_token(
        data={"user_id": user["id"], "name": user["name"], "email": user["email"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"       
    }

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna informações do usuário autenticado"""
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "create_in": current_user["create_in"].strftime('%Y-%m-%d %H:%M:%S'),
        "activate": current_user["activate"]
    }

@router.post("/verify")
def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica se o token é válido"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    
    return {"valid": True, "payload": payload}