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


class UsuarioCreate(UsuarioBase):
    empresa_nome: str
    senha: str


class UsuarioRead(UsuarioBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True


# ==========================
# Token
# ==========================
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
