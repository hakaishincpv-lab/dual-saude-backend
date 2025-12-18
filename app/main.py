from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

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

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"UNHANDLED ERROR: {request.method} {request.url}")
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.get("/")
def read_root():
    return {"message": "API Dual Saúde funcionando 🚀"}

app.include_router(auth.router)
app.include_router(api.router)
app.include_router(demo_setup.router)
