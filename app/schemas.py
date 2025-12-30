from typing import Optional
from pydantic import BaseModel, EmailStr


# ==========================
# Usuário
# ==========================
class UsuarioBase(BaseModel):
    nome: str
    cpf: str
    email: EmailStr
    celular: Optional[str] = None


class UsuarioCreate(BaseModel):
    nome: str
    cpf: str
    email: EmailStr
    celular: Optional[str] = None
    senha: str
    # ⚠️ empresa não é mais obrigatória para cadastro no app
    empresa_nome: Optional[str] = None


class UsuarioRead(UsuarioBase):
    id: int
    empresa_id: int
    ativo: bool

    class Config:
        from_attributes = True


# ==========================
# Token / Auth
# ==========================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
