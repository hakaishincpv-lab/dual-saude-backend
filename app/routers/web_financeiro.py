from datetime import date, datetime
from calendar import monthrange

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.database import get_db
from app.models import Usuario
from app.models.financeiro import CategoriaFinanceira, LancamentoFinanceiro

# Import compatível: se o projeto usa PagamentoDestino no __init__.py,
# este alias existe no financeiro.py (PagamentoDestino = DadosPagamento)
try:
    from app.models.financeiro import DadosPagamento  # type: ignore
except Exception:
    DadosPagamento = None

from app.routers.web_auth import get_current_user_web  # cookie auth do painel

router = APIRouter(tags=["Web - Financeiro"])


def _parse_ym(ym: str | None) -> tuple[int, int]:
    today = date.today()
    if not ym:
        return (today.year, today.month)
    try:
        y, m = ym.split("-")
        return (int(y), int(m))
    except Exception:
        return (today.year, today.month)


def _month_bounds(y: int, m: int) -> tuple[date, date]:
    last_day = monthrange(y, m)[1]
    start = date(y, m, 1)
    end = date(y, m, last_day)
    return start, end


def _money(v) -> float:
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def _redir(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def _nav_ctx(current: str, ym: str) -> dict:
    return {"fin_current": current, "ym": ym}


@router.get("/painel/financeiro", response_class=HTMLResponse)
def financeiro_dashboard(
    request: Request,
    ym: str | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    templates = request.app.state.templates

    y, m = _parse_ym(ym)
    start, end = _month_bounds(y, m)

    base_q = (
        db.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.empresa_id == user.empresa_id)
        .filter(LancamentoFinanceiro.data_lancamento >= start)
        .filter(LancamentoFinanceiro.data_lancamento <= end)
    )

    totais = (
        db.query(
            func.coalesce(
                func.sum(case((LancamentoFinanceiro.tipo == "RECEITA", LancamentoFinanceiro.valor), else_=0)),
                0,
            ).label("receitas"),
            func.coalesce(
                func.sum(case((LancamentoFinanceiro.tipo == "DESPESA", LancamentoFinanceiro.valor), else_=0)),
                0,
            ).label("despesas"),
            func.coalesce(
                func.sum(case((LancamentoFinanceiro.status == "PENDENTE", LancamentoFinanceiro.valor), else_=0)),
                0,
            ).label("pendentes"),
        )
        .filter(
            LancamentoFinanceiro.empresa_id == user.empresa_id,
            LancamentoFinanceiro.data_lancamento >= start,
            LancamentoFinanceiro.data_lancamento <= end,
        )
        .first()
    )

    receitas = _money(totais.receitas)
    despesas = _money(totais.despesas)
    saldo = receitas - despesas
    pendentes = _money(totais.pendentes)

    ultimos = base_q.order_by(LancamentoFinanceiro.data_lancamento.desc()).limit(8).all()

    return templates.TemplateResponse(
        "financeiro/dashboard.html",
        {
            "request": request,
            "title": "Financeiro",
            "receitas": receitas,
            "despesas": despesas,
            "saldo": saldo,
            "pendentes": pendentes,
            "ultimos": ultimos,
            "periodo_label": f"{m:02d}/{y}",
            **_nav_ctx("dashboard", f"{y}-{m:02d}"),
        },
    )


@router.get("/painel/financeiro/categorias", response_class=HTMLResponse)
def categorias_listar(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
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
            **_nav_ctx("categorias", ""),
        },
    )


@router.post("/painel/financeiro/categorias/criar")
def categorias_criar(
    nome: str = Form(...),
    tipo: str = Form(...),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    nome = (nome or "").strip()
    tipo = (tipo or "").strip().upper()

    if tipo not in ("RECEITA", "DESPESA"):
        return _redir("/painel/financeiro/categorias")

    exists = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.empresa_id == user.empresa_id,
            CategoriaFinanceira.tipo == tipo,
            func.lower(CategoriaFinanceira.nome) == nome.lower(),
        )
        .first()
    )

    if not exists and nome:
        db.add(CategoriaFinanceira(nome=nome, tipo=tipo, empresa_id=user.empresa_id))
        db.commit()

    return _redir("/painel/financeiro/categorias")


@router.get("/painel/financeiro/categorias/excluir/{categoria_id}")
def categorias_excluir(
    categoria_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    cat = (
        db.query(CategoriaFinanceira)
        .filter(CategoriaFinanceira.id == categoria_id, CategoriaFinanceira.empresa_id == user.empresa_id)
        .first()
    )
    if cat:
        db.delete(cat)
        db.commit()
    return _redir("/painel/financeiro/categorias")


@router.get("/painel/financeiro/lancamentos", response_class=HTMLResponse)
def lancamentos_listar(
    request: Request,
    ym: str | None = None,
    status: str | None = None,
    tipo: str | None = None,
    categoria_id: int | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    templates = request.app.state.templates

    y, m = _parse_ym(ym)
    start, end = _month_bounds(y, m)

    q = (
        db.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.empresa_id == user.empresa_id)
        .filter(LancamentoFinanceiro.data_lancamento >= start)
        .filter(LancamentoFinanceiro.data_lancamento <= end)
    )

    if status in ("PENDENTE", "PAGO"):
        q = q.filter(LancamentoFinanceiro.status == status)
    if tipo in ("RECEITA", "DESPESA"):
        q = q.filter(LancamentoFinanceiro.tipo == tipo)
    if categoria_id:
        q = q.filter(LancamentoFinanceiro.categoria_id == categoria_id)

    lancamentos = q.order_by(LancamentoFinanceiro.data_lancamento.desc()).all()

    categorias = (
        db.query(CategoriaFinanceira)
        .filter(CategoriaFinanceira.empresa_id == user.empresa_id)
        .order_by(CategoriaFinanceira.tipo, CategoriaFinanceira.nome)
        .all()
    )

    return templates.TemplateResponse(
        "financeiro/lancamentos.html",
        {
            "request": request,
            "title": "Lançamentos",
            "lancamentos": lancamentos,
            "categorias": categorias,
            "f_status": status or "",
            "f_tipo": tipo or "",
            "f_categoria_id": categoria_id or "",
            **_nav_ctx("lancamentos", f"{y}-{m:02d}"),
        },
    )


@router.post("/painel/financeiro/lancamentos/criar")
def lancamentos_criar(
    tipo: str = Form(...),
    categoria_id: int | None = Form(None),
    descricao: str = Form(...),
    valor: str = Form(...),
    data_lancamento: str = Form(...),
    status: str = Form("PENDENTE"),
    forma_pagamento: str | None = Form(None),
    data_vencimento: str | None = Form(None),
    data_pagamento: str | None = Form(None),
    observacao: str | None = Form(None),
    ym: str | None = Form(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    tipo = (tipo or "").upper().strip()
    status = (status or "PENDENTE").upper().strip()
    descricao = (descricao or "").strip()

    if tipo not in ("RECEITA", "DESPESA"):
        return _redir("/painel/financeiro/lancamentos")

    v = (valor or "0").replace(".", "").replace(",", ".")
    try:
        v_num = float(v)
    except Exception:
        v_num = 0.0

    def pd(s: str | None):
        if not s:
            return None
        return datetime.strptime(s, "%Y-%m-%d").date()

    lanc = LancamentoFinanceiro(
        empresa_id=user.empresa_id,
        tipo=tipo,
        categoria_id=categoria_id or None,
        descricao=descricao,
        valor=v_num,
        data_lancamento=pd(data_lancamento),
        data_vencimento=pd(data_vencimento),
        data_pagamento=pd(data_pagamento),
        status=status if status in ("PENDENTE", "PAGO") else "PENDENTE",
        forma_pagamento=(forma_pagamento or "").strip() or None,
        observacao=(observacao or "").strip() or None,
    )

    db.add(lanc)
    db.commit()

    y, m = _parse_ym(ym)
    return _redir(f"/painel/financeiro/lancamentos?ym={y}-{m:02d}")


@router.get("/painel/financeiro/lancamentos/excluir/{lanc_id}")
def lancamentos_excluir(
    lanc_id: int,
    ym: str | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    lanc = (
        db.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.id == lanc_id, LancamentoFinanceiro.empresa_id == user.empresa_id)
        .first()
    )
    if lanc:
        db.delete(lanc)
        db.commit()

    y, m = _parse_ym(ym)
    return _redir(f"/painel/financeiro/lancamentos?ym={y}-{m:02d}")


@router.get("/painel/financeiro/lancamentos/marcar-pago/{lanc_id}")
def lancamentos_marcar_pago(
    lanc_id: int,
    ym: str | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    lanc = (
        db.query(LancamentoFinanceiro)
        .filter(LancamentoFinanceiro.id == lanc_id, LancamentoFinanceiro.empresa_id == user.empresa_id)
        .first()
    )
    if lanc:
        lanc.status = "PAGO"
        if not lanc.data_pagamento:
            lanc.data_pagamento = date.today()
        db.commit()

    y, m = _parse_ym(ym)
    return _redir(f"/painel/financeiro/lancamentos?ym={y}-{m:02d}")


@router.get("/painel/financeiro/relatorios", response_class=HTMLResponse)
def financeiro_relatorios(
    request: Request,
    ym: str | None = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    templates = request.app.state.templates

    y, m = _parse_ym(ym)
    start, end = _month_bounds(y, m)

    rows = (
        db.query(
            LancamentoFinanceiro.tipo,
            func.coalesce(func.sum(LancamentoFinanceiro.valor), 0).label("total"),
        )
        .filter(
            LancamentoFinanceiro.empresa_id == user.empresa_id,
            LancamentoFinanceiro.data_lancamento >= start,
            LancamentoFinanceiro.data_lancamento <= end,
        )
        .group_by(LancamentoFinanceiro.tipo)
        .all()
    )

    receitas = 0.0
    despesas = 0.0
    for r in rows:
        if r.tipo == "RECEITA":
            receitas = _money(r.total)
        elif r.tipo == "DESPESA":
            despesas = _money(r.total)

    resultado = receitas - despesas

    fluxo = (
        db.query(
            LancamentoFinanceiro.tipo,
            func.coalesce(func.sum(LancamentoFinanceiro.valor), 0).label("total"),
        )
        .filter(
            LancamentoFinanceiro.empresa_id == user.empresa_id,
            LancamentoFinanceiro.status == "PAGO",
            LancamentoFinanceiro.data_pagamento.isnot(None),
            LancamentoFinanceiro.data_pagamento >= start,
            LancamentoFinanceiro.data_pagamento <= end,
        )
        .group_by(LancamentoFinanceiro.tipo)
        .all()
    )

    caixa_in = 0.0
    caixa_out = 0.0
    for f in fluxo:
        if f.tipo == "RECEITA":
            caixa_in = _money(f.total)
        elif f.tipo == "DESPESA":
            caixa_out = _money(f.total)

    caixa_liquido = caixa_in - caixa_out

    return templates.TemplateResponse(
        "financeiro/relatorios.html",
        {
            "request": request,
            "title": "Relatórios",
            "periodo_label": f"{m:02d}/{y}",
            "dre_receitas": receitas,
            "dre_despesas": despesas,
            "dre_resultado": resultado,
            "caixa_in": caixa_in,
            "caixa_out": caixa_out,
            "caixa_liquido": caixa_liquido,
            **_nav_ctx("relatorios", f"{y}-{m:02d}"),
        },
    )


# ============================================================
# DADOS DE PAGAMENTO
# ============================================================
@router.get("/painel/financeiro/pagamentos", response_class=HTMLResponse)
def pagamentos_listar(
    request: Request,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    templates = request.app.state.templates

    if DadosPagamento is None:
        return HTMLResponse(
            """
            <h2>Dados de Pagamento</h2>
            <p>Model <b>DadosPagamento</b> não encontrado em <code>app.models.financeiro</code>.</p>
            """,
            status_code=200,
        )

    pagamentos = (
        db.query(DadosPagamento)
        .filter(DadosPagamento.empresa_id == user.empresa_id)
        .order_by(DadosPagamento.nome.asc())
        .all()
    )

    return templates.TemplateResponse(
        "financeiro/pagamentos.html",
        {
            "request": request,
            "title": "Dados de Pagamento",
            "pagamentos": pagamentos,
            "fin_current": "pagamentos",
            "ym": "",
        },
    )


@router.post("/painel/financeiro/pagamentos/criar")
def pagamentos_criar(
    nome: str = Form(...),
    tipo_servico: str = Form(...),
    forma: str = Form(...),  # PIX | CONTA
    pix_chave: str | None = Form(None),
    banco: str | None = Form(None),
    agencia: str | None = Form(None),
    conta: str | None = Form(None),
    tipo_conta: str | None = Form(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user_web),
):
    if DadosPagamento is None:
        return _redir("/painel/financeiro/pagamentos")

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

    return _redir("/painel/financeiro/pagamentos")
