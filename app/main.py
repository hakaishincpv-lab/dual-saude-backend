from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, api, demo_setup


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


@app.get("/")
def read_root():
    return {"message": "API Dual Saúde funcionando 🚀"}


app.include_router(auth.router)
app.include_router(api.router)
app.include_router(demo_setup.router)
