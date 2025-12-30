from datetime import timedelta
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario

# Importa as configs/token do seu auth.py (sem alterar a API)
from app.routers.auth import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_password,
    create_access_token,
)

router = APIRouter(tags=["Web - Auth"])

COOKIE_NAME = "ds_token"


def _redir(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


@router.get("/painel/login", response_class=HTMLResponse)
def painel_login_get(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "painel_login.html",
        {"request": request, "title": "Login - Painel Dual Saúde"},
    )


@router.post("/painel/login")
def painel_login_post(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_db),
):
    email = (email or "").strip().lower()
    senha = senha or ""

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user or not verify_password(senha, user.hashed_password):
        return _redir("/painel/login?err=1")

    expire_minutes = int(ACCESS_TOKEN_EXPIRE_MINUTES or 720)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=expire_minutes),
    )

    resp = _redir("/painel")
    resp.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # em HTTPS real, você pode colocar True
        max_age=expire_minutes * 60,
    )
    return resp


@router.get("/painel/logout")
def painel_logout():
    resp = _redir("/painel/login")
    resp.delete_cookie(COOKIE_NAME)
    return resp


# =========================
# Dependency para páginas WEB (cookie)
# =========================
def get_current_user_web(
    request: Request,
    db: Session = Depends(get_db),
) -> Usuario:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        # sem cookie -> manda pro login do painel
        raise RedirectResponse(url="/painel/login", status_code=303)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if not email:
            raise ValueError("Token sem sub")
    except (JWTError, Exception):
        raise RedirectResponse(url="/painel/login", status_code=303)

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        raise RedirectResponse(url="/painel/login", status_code=303)

    return user
