from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/auth", tags=["Auth"])

# =========================================================
# CONFIG
# =========================================================

SECRET_KEY = "CHANGE_ME_SUPER_SECRET"  # mover para env depois
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# =========================================================
# HELPERS
# =========================================================

def _digits_only(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    return "".join(filter(str.isdigit, s))


def _norm_spaces(s: Optional[str]) -> str:
    return " ".join((s or "").strip().split())


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    # bcrypt aceita até 72 chars
    return pwd_context.hash(password[:72])


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_email(db: Session, email: str):
    return (
        db.query(models.Usuario)
        .filter(models.Usuario.email == email)
        .first()
    )

# =========================================================
# AUTH CORE
# =========================================================

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.ativo:
        return None
    return user

# =========================================================
# REGISTER (SEM AUTORIZAÇÃO PRÉVIA – DEMO / APP)
# =========================================================

@router.post("/register", response_model=schemas.UsuarioRead)
def register_user(
    payload: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
):
    cpf = _digits_only(payload.cpf)
    celular = _digits_only(payload.celular)
    email = payload.email.strip().lower()

    if not cpf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF inválido.",
        )

    # CPF único
    if db.query(models.Usuario).filter(models.Usuario.cpf == cpf).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado. Faça login.",
        )

    # E-mail único
    if db.query(models.Usuario).filter(models.Usuario.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado. Faça login.",
        )

    try:
        user = models.Usuario(
            nome=_norm_spaces(payload.nome),
            cpf=cpf,
            email=email,
            celular=celular,
            empresa_id=1,  # empresa técnica padrão (demo/app)
            hashed_password=get_password_hash(payload.senha),
            ativo=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    except IntegrityError as e:
        db.rollback()
        print("INTEGRITY ERROR /auth/register:", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível concluir o cadastro.",
        )

    except Exception as e:
        db.rollback()
        print("ERROR /auth/register:", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro inesperado ao criar usuário.",
        )

# =========================================================
# LOGIN (COMPATÍVEL COM FLUTTER)
# =========================================================

@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = (form_data.username or "").strip().lower()
    password = form_data.password

    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
    )

# =========================================================
# CURRENT USER (JWT)
# =========================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.id == int(user_id))
        .first()
    )
    if not user:
        raise credentials_exception

    return user


@router.get("/me", response_model=schemas.UsuarioRead)
def read_users_me(
    current_user: models.Usuario = Depends(get_current_user),
):
    return current_user
