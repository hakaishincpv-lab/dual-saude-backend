from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models import Usuario
from app.models.financeiro import CategoriaFinanceira

# ============================================================
# IMPORT OPCIONAL (NÃO QUEBRA SE O MODEL AINDA NÃO EXISTIR)
# ============================================================
try:
    from app.models.financeiro import DadosPagamento  # type: ignore
except Exception:
    DadosPagamento = None  # fallback seguro

router = APIRouter(tags=["Web - Financeiro"])


# ============================================================
# CATEGORIAS (SEU CÓDIGO ORIGINAL - INTACTO)
# ============================================================
@router.get("/painel/financeiro/categorias", response_class=HTMLResponse)
def listar_categorias(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    templates = request.app.state.templates

    categorias = (
        db.query(CategoriaFinanceira)
        .filter(CategoriaFinanceira.empresa_id == user.empresa_id)
        .order_by(CategoriaFinanceira.tipo, CategoriaFinanceira.nome)
        .all()
    )

    return templates.TemplateResponse(
        "financeiro/categorias.html",
        {
            "request": request,
            "title": "Categorias Financeiras",
            "categorias": categorias,
        },
    )


@router.post("/painel/financeiro/categorias/criar")
def criar_categoria(
    nome: str = Form(...),
    tipo: str = Form(...),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    categoria = CategoriaFinanceira(
        nome=nome.strip(),
        tipo=tipo,
        empresa_id=user.empresa_id,
    )
    db.add(categoria)
    db.commit()

    return RedirectResponse(
        url="/painel/financeiro/categorias",
        status_code=303,
    )


@router.get("/painel/financeiro/categorias/excluir/{categoria_id}")
def excluir_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    categoria = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.id == categoria_id,
            CategoriaFinanceira.empresa_id == user.empresa_id,
        )
        .first()
    )

    if categoria:
        db.delete(categoria)
        db.commit()

    return RedirectResponse(
        url="/painel/financeiro/categorias",
        status_code=303,
    )


# ============================================================
# NOVO: DADOS DE PAGAMENTO (TELA + CADASTRO)
# - Regras: PIX OU CONTA BANCÁRIA
# - Sem quebrar se model/template ainda não existir
# ============================================================

@router.get("/painel/financeiro/pagamentos", response_class=HTMLResponse)
def listar_pagamentos(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    templates = request.app.state.templates

    # Se o model ainda não existe, não quebra o painel
    if DadosPagamento is None:
        return HTMLResponse(
            """
            <h2>Dados de Pagamento</h2>
            <p>O model <b>DadosPagamento</b> ainda não foi encontrado em <code>app.models.financeiro</code>.</p>
            <p>Envie o arquivo do model financeiro para eu aplicar o patch incremental com a tabela/colunas.</p>
            """,
            status_code=200,
        )

    pagamentos = (
        db.query(DadosPagamento)
        .filter(DadosPagamento.empresa_id == user.empresa_id)
        .order_by(DadosPagamento.nome.asc())
        .all()
    )

    # Se o template ainda não existe, não quebra: fallback HTML simples
    try:
        return templates.TemplateResponse(
            "financeiro/pagamentos.html",
            {
                "request": request,
                "title": "Dados de Pagamento",
                "pagamentos": pagamentos,
            },
        )
    except Exception:
        rows = ""
        for p in pagamentos:
            rows += (
                "<tr>"
                f"<td>{getattr(p, 'nome', '')}</td>"
                f"<td>{getattr(p, 'tipo_servico', '')}</td>"
                f"<td>{getattr(p, 'forma', '')}</td>"
                f"<td>{getattr(p, 'pix_chave', '') or ''}</td>"
                f"<td>{getattr(p, 'banco', '') or ''}</td>"
                f"<td>{getattr(p, 'agencia', '') or ''}</td>"
                f"<td>{getattr(p, 'conta', '') or ''}</td>"
                f"<td>{getattr(p, 'tipo_conta', '') or ''}</td>"
                "</tr>"
            )

        return HTMLResponse(
            f"""
            <h2>Dados de Pagamento</h2>
            <p><i>Template <code>financeiro/pagamentos.html</code> não encontrado. Exibindo fallback.</i></p>

            <h3>Novo cadastro</h3>
            <form method="post" action="/painel/financeiro/pagamentos/criar">
              <div><label>Nome:</label><br><input name="nome" required></div><br>
              <div><label>Tipo de serviço:</label><br><input name="tipo_servico" required></div><br>

              <div>
                <label>Forma:</label><br>
                <select name="forma" required>
                  <option value="PIX">PIX</option>
                  <option value="CONTA">CONTA BANCÁRIA</option>
                </select>
              </div><br>

              <div><label>Chave PIX (se PIX):</label><br><input name="pix_chave"></div><br>

              <div><label>Banco (se CONTA):</label><br><input name="banco"></div>
              <div><label>Agência (se CONTA):</label><br><input name="agencia"></div>
              <div><label>Conta (se CONTA):</label><br><input name="conta"></div>
              <div><label>Tipo de conta (se CONTA):</label><br><input name="tipo_conta"></div><br>

              <button type="submit">Salvar</button>
            </form>

            <h3>Cadastros</h3>
            <table border="1" cellpadding="6" cellspacing="0">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Tipo Serviço</th>
                  <th>Forma</th>
                  <th>PIX</th>
                  <th>Banco</th>
                  <th>Agência</th>
                  <th>Conta</th>
                  <th>Tipo Conta</th>
                </tr>
              </thead>
              <tbody>{rows}</tbody>
            </table>
            """,
            status_code=200,
        )


@router.post("/painel/financeiro/pagamentos/criar")
def criar_pagamento(
    nome: str = Form(...),
    tipo_servico: str = Form(...),
    forma: str = Form(...),  # PIX | CONTA
    pix_chave: str | None = Form(None),
    banco: str | None = Form(None),
    agencia: str | None = Form(None),
    conta: str | None = Form(None),
    tipo_conta: str | None = Form(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    # Se o model ainda não existe, não quebra
    if DadosPagamento is None:
        return RedirectResponse(url="/painel/financeiro/pagamentos", status_code=303)

    forma_norm = (forma or "").upper().strip()
    if forma_norm not in ("PIX", "CONTA"):
        forma_norm = "PIX"

    nome = (nome or "").strip()
    tipo_servico = (tipo_servico or "").strip()

    pix = (pix_chave or "").strip() or None
    bco = (banco or "").strip() or None
    ag = (agencia or "").strip() or None
    cta = (conta or "").strip() or None
    tcta = (tipo_conta or "").strip() or None

    # Regra: PIX OU CONTA
    if forma_norm == "PIX":
        bco = ag = cta = tcta = None
    else:
        pix = None

    pagamento = DadosPagamento(
        empresa_id=user.empresa_id,
        nome=nome,
        tipo_servico=tipo_servico,
        forma=forma_norm,
        pix_chave=pix,
        banco=bco,
        agencia=ag,
        conta=cta,
        tipo_conta=tcta,
    )

    db.add(pagamento)
    db.commit()

    return RedirectResponse(
        url="/painel/financeiro/pagamentos",
        status_code=303,
    )
