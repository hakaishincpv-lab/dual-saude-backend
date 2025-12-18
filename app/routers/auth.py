from datetime import datetime, timedelta
from typing import Optional
import os
import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import schemas
from app.database import get_db
from app.models import Empresa, FuncionarioAutorizado, Usuario

router = APIRouter(tags=["Auth"], prefix="/auth")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-dual-saude-muda-isso-producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", (s or ""))


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_email(db: Session, email: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[Usuario]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not getattr(user, "ativo", True):
        return None
    return user


@router.post("/register", response_model=schemas.UsuarioRead)
def register_user(payload: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Normalizações importantes (evita máscara quebrar validação/unique)
    empresa_nome = _norm_spaces(payload.empresa_nome)
    cpf = _digits_only(payload.cpf)
    celular = _digits_only(payload.celular) if payload.celular else None
    email = (payload.email or "").strip().lower()

    # 1) Empresa
    empresa = db.query(Empresa).filter(Empresa.nome.ilike(empresa_nome)).first()
    if not empresa or not getattr(empresa, "ativo", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa não encontrada ou inativa. Verifique com o RH.",
        )

    # 2) Duplicidade (mensagem clara)
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado. Use outro e-mail ou faça login.",
        )

    if db.query(Usuario).filter(Usuario.cpf == cpf).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado. Faça login ou solicite suporte.",
        )

    # 3) CPF autorizado
    funcionario = (
        db.query(FuncionarioAutorizado)
        .filter(
            FuncionarioAutorizado.empresa_id == empresa.id,
            FuncionarioAutorizado.cpf == cpf,
            FuncionarioAutorizado.ativo.is_(True),
        )
        .first()
    )

    if not funcionario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu CPF não está autorizado para uso do app. Procure o RH da sua empresa.",
        )

    # ✅ CAUSA MAIS COMUM DO SEU ERRO ATUAL:
    # CPF autorizado já foi usado (funcionario já vinculado a um usuário)
    if getattr(funcionario, "usuario_id", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este CPF já foi utilizado para cadastro. Faça login ou solicite suporte.",
        )

    # 4) Cria usuário e vincula funcionário em 1 transação
    try:
        user = Usuario(
            nome=payload.nome,
            cpf=cpf,
            email=email,
            celular=celular,
            empresa_id=empresa.id,
            hashed_password=get_password_hash(payload.senha),
            ativo=True,
        )
        db.add(user)
        db.flush()  # garante user.id sem commit

        funcionario.usuario_id = user.id

        db.commit()
        db.refresh(user)
        return user

    except IntegrityError as e:
        db.rollback()
        print("INTEGRITY ERROR /auth/register:", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível concluir o cadastro (dados já existentes ou vínculo inválido).",
        )
    except Exception as e:
        db.rollback()
        print("ERROR /auth/register:", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível concluir o cadastro, verifique os dados e tente novamente.",
        )


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username.strip().lower(), form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user
