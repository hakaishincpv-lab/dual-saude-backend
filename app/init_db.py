from app.database import Base, engine
from app import models  # importa para registrar Empresa, FuncionarioAutorizado, Usuario


def init_db():
    print("📦 Criando tabelas no banco dual_saude.db ...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso.")


if __name__ == "__main__":
    init_db()
