from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Empresa(Base):
    __tablename__ = "empresas"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    cnpj = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)

    funcionarios = relationship(
        "FuncionarioAutorizado",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )

    usuarios = relationship(
        "Usuario",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )


class FuncionarioAutorizado(Base):
    __tablename__ = "funcionarios_autorizados"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cpf = Column(String, index=True, nullable=False)
    email = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="funcionarios")

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario = relationship("Usuario", back_populates="funcionario", uselist=False)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    cpf = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    celular = Column(String, nullable=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="usuarios")

    hashed_password = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)

    funcionario = relationship(
        "FuncionarioAutorizado",
        back_populates="usuario",
        uselist=False,
    )
