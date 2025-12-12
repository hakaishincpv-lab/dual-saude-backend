# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, api, demo_setup


# (Opcional) manter em dev.
# Em produção, o ideal é usar Alembic migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dual Saúde API",
    version="0.1.0",
    description="Backend da aplicação Dual Saúde (Auth + API + Demo Setup).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # depois a gente restringe por domínio do app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "API Dual Saúde funcionando 🚀"}


# Auth já tem prefix "/auth" no router? se não tiver, mantém prefix aqui.
app.include_router(auth.router)

# ✅ IMPORTANTE:
# Se o seu routers/api.py já tem prefix="/api", NÃO coloca prefix aqui.
# (e o api.py que você colou eu ajustei pra ter prefix="/api")
app.include_router(api.router)

# demo_setup já tem prefix="/api" lá dentro, então inclui direto:
app.include_router(demo_setup.router)
