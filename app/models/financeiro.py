from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Date, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base


class CategoriaFinanceira(Base):
    __tablename__ = "financeiro_categorias"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    nome = Column(String, nullable=False, index=True)
    tipo = Column(String, nullable=False, index=True)  # "RECEITA" | "DESPESA"
    ativo = Column(Boolean, default=True)

    empresa = relationship("Empresa")
    lancamentos = relationship("LancamentoFinanceiro", back_populates="categoria")


class LancamentoFinanceiro(Base):
    __tablename__ = "financeiro_lancamentos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    tipo = Column(String, nullable=False, index=True)  # "RECEITA" | "DESPESA"
    categoria_id = Column(Integer, ForeignKey("financeiro_categorias.id"), nullable=True, index=True)

    descricao = Column(String, nullable=False)
    observacao = Column(Text, nullable=True)

    valor = Column(Numeric(12, 2), nullable=False, default=0)

    data_lancamento = Column(Date, nullable=False, index=True)  # competência
    data_vencimento = Column(Date, nullable=True, index=True)
    data_pagamento = Column(Date, nullable=True, index=True)

    status = Column(String, nullable=False, default="PENDENTE", index=True)  # "PENDENTE" | "PAGO"
    forma_pagamento = Column(String, nullable=True)  # "PIX", "Cartão", "Boleto", etc.

    empresa = relationship("Empresa")
    categoria = relationship("CategoriaFinanceira", back_populates="lancamentos")


# ============================================================
# NOVO: DADOS DE PAGAMENTO (PIX OU CONTA BANCÁRIA)
# ============================================================
class DadosPagamento(Base):
    __tablename__ = "financeiro_dados_pagamento"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    nome = Column(String, nullable=False, index=True)  # nome do favorecido / recebedor
    tipo_servico = Column(String, nullable=False, index=True)  # ex: "Consulta", "Nutrição", "Psicologia"

    # "PIX" | "CONTA"
    forma = Column(String, nullable=False, index=True)

    # PIX
    pix_chave = Column(String, nullable=True)

    # CONTA BANCÁRIA
    banco = Column(String, nullable=True)
    agencia = Column(String, nullable=True)
    conta = Column(String, nullable=True)
    tipo_conta = Column(String, nullable=True)  # ex: "Corrente", "Poupança"

    ativo = Column(Boolean, default=True)

    empresa = relationship("Empresa")


# ============================================================
# COMPATIBILIDADE (IMPORT ANTIGO DO SEU models/__init__.py)
# O projeto tenta importar PagamentoDestino.
# Mantemos alias para NÃO QUEBRAR a aplicação.
# ============================================================
PagamentoDestino = DadosPagamento
