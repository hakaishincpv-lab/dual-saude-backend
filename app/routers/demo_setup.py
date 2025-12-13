# app/routers/demo_setup.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Empresa, FuncionarioAutorizado


router = APIRouter(
    prefix="/api",
    tags=["Demo"],
)


@router.post("/setup-demo")
def setup_demo(db: Session = Depends(get_db)):
    # ============================
    # 1. Empresa Demo
    # ============================
    EMPRESA_NOME = "Empresa Demo Dual Saúde"

    empresa = (
        db.query(Empresa)
        .filter(Empresa.nome == EMPRESA_NOME)
        .first()
    )

    if not empresa:
        empresa = Empresa(nome=EMPRESA_NOME)
        db.add(empresa)
        db.commit()
        db.refresh(empresa)

    # ============================
    # 2. Funcionário autorizado
    # ============================
    CPF_DEMO = "12345678900"
    EMAIL_DEMO = "colaborador.demo@empresa.com"

    func = (
        db.query(FuncionarioAutorizado)
        .filter(
            FuncionarioAutorizado.cpf == CPF_DEMO,
            FuncionarioAutorizado.empresa_id == empresa.id,
        )
        .first()
    )

    if not func:
        func = FuncionarioAutorizado(
            nome="Colaborador Demo",
            cpf=CPF_DEMO,
            email=EMAIL_DEMO,
            empresa_id=empresa.id,
        )
        db.add(func)
        db.commit()
        db.refresh(func)

    return {
        "message": "Dados de demonstração criados/atualizados com sucesso.",
        "empresa": {
            "id": empresa.id,
            "nome": empresa.nome,
        },
        "funcionario_autorizado": {
            "id": func.id,
            "nome": func.nome,
            "cpf": func.cpf,
            "email": func.email,
        },
        "instrucoes_teste": {
            "empresa_nome_para_cadastro": empresa.nome,
            "cpf_para_cadastro": CPF_DEMO,
            "email_sugerido_para_usuario": EMAIL_DEMO,
        },
    }
