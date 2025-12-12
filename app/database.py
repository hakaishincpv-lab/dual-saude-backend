import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Usa DATABASE_URL do servidor (Render/Railway/etc). Se não existir, cai no SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dual_saude.db")

# Alguns provedores entregam postgres:// e o SQLAlchemy espera postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


class Base(DeclarativeBase):
    pass


# connect_args só é necessário no SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # ajuda em conexões “dormindo”/dropadas no servidor
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
