from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import Base, engine
from app.routers import auth, api, demo_setup, web
from app.routers.web_financeiro import router as web_financeiro_router
from app.routers.web_auth import router as web_auth_router

# (Dev) Em produção, o ideal é Alembic migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dual Saúde API",
    version="0.1.0",
    description="Backend da aplicação Dual Saúde",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static e Templates (Painel Web)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def read_root():
    return {"message": "API Dual Saúde funcionando 🚀"}


# =========================
# APIs (não mexer)
# =========================
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(demo_setup.router)

# =========================
# Web (Painel)
# =========================
app.include_router(web_auth_router)        # /painel/login  /painel/logout
app.include_router(web.router)             # /painel
app.include_router(web_financeiro_router)  # /painel/financeiro...
