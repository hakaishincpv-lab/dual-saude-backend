from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Empresa, FuncionarioAutorizado, Usuario
from app import schemas
from app.routers.auth import get_current_user  # pega usuário logado via token JWT


router = APIRouter(prefix="/api", tags=["API"])


@router.get("/hello")
def hello():
    return {"message": "API Dual Saúde online"}


@router.post("/setup-demo")
def setup_demo(db: Session = Depends(get_db)):
    """
    Cria dados de demonstração para testes:

    - 1 empresa: "Empresa Demo Dual Saúde"
    - 1 funcionário autorizado nessa empresa
    """

    # Empresa demo
    empresa_nome = "Empresa Demo Dual Saúde"
    empresa = db.query(Empresa).filter(Empresa.nome == empresa_nome).first()
    if not empresa:
        empresa = Empresa(
            nome=empresa_nome,
            cnpj="00.000.000/0001-00",
            ativo=True,
        )
        db.add(empresa)
        db.commit()
        db.refresh(empresa)

    # Funcionário autorizado demo
    cpf_demo = "12345678900"
    email_demo = "colaborador.demo@empresa.com"
    funcionario = (
        db.query(FuncionarioAutorizado)
        .filter(
            FuncionarioAutorizado.empresa_id == empresa.id,
            FuncionarioAutorizado.cpf == cpf_demo,
        )
        .first()
    )
    if not funcionario:
        funcionario = FuncionarioAutorizado(
            nome="Colaborador Demo",
            cpf=cpf_demo,
            email=email_demo,
            ativo=True,
            empresa_id=empresa.id,
        )
        db.add(funcionario)
        db.commit()
        db.refresh(funcionario)

    return {
        "message": "Dados de demonstração criados/atualizados com sucesso.",
        "empresa": {"id": empresa.id, "nome": empresa.nome},
        "funcionario_autorizado": {
            "id": funcionario.id,
            "nome": funcionario.nome,
            "cpf": funcionario.cpf,
            "email": funcionario.email,
        },
        "instrucoes_teste": {
            "empresa_nome_para_cadastro": empresa.nome,
            "cpf_para_cadastro": cpf_demo,
            "email_sugerido_para_usuario": email_demo,
        },
    }


@router.get("/me", response_model=schemas.UsuarioRead)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user
