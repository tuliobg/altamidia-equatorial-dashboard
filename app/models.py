from sqlalchemy import (
    Boolean, Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.db import Base


class Unidade(Base):
    __tablename__ = "unidades"

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)
    tipo = Column(String, nullable=True)  # 'U' urbana / 'R' rural
    status = Column(String, nullable=False, default="Ativa")  # Ativa / Desativada / Fora do rateio
    geradora = Column(Boolean, nullable=False, default=False)
    pct_rateio_atual = Column(Float, nullable=False, default=0.0)
    pct_rateio_sugerido = Column(Float, nullable=False, default=0.0)

    codigos = relationship("UnidadeCodigo", back_populates="unidade", cascade="all, delete-orphan")
    faturas = relationship("Fatura", back_populates="unidade", cascade="all, delete-orphan")


class UnidadeCodigo(Base):
    __tablename__ = "unidade_codigos"

    id = Column(Integer, primary_key=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    codigo = Column(String, nullable=False, index=True)

    unidade = relationship("Unidade", back_populates="codigos")

    __table_args__ = (UniqueConstraint("codigo", name="uq_unidade_codigo"),)


class Fatura(Base):
    __tablename__ = "faturas"

    id = Column(Integer, primary_key=True)
    unidade_id = Column(Integer, ForeignKey("unidades.id"), nullable=False)
    ano_mes = Column(Date, nullable=False, index=True)

    kwh_tax = Column(Float, default=0.0)
    cip_tax = Column(Float, default=0.0)
    real_consumo = Column(Float, default=0.0)
    energia_injetada = Column(Float, default=0.0)
    diferenca_kw = Column(Float, default=0.0)
    acumulado = Column(Float, default=0.0)
    a_expirar = Column(Float, default=0.0)

    # real_valor = "custo sem solar" = real_consumo * kwh_tax + cip_tax
    real_valor = Column(Float, default=0.0)
    # pago = valor real do boleto (ja com desconto de energia compensada)
    pago = Column(Float, default=0.0)
    # diferenca = real_valor - pago = economia do mes
    diferenca = Column(Float, default=0.0)

    unidade = relationship("Unidade", back_populates="faturas")

    __table_args__ = (UniqueConstraint("unidade_id", "ano_mes", name="uq_unidade_mes"),)


class Investimento(Base):
    __tablename__ = "investimento"

    id = Column(Integer, primary_key=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)


class Config(Base):
    __tablename__ = "config"

    chave = Column(String, primary_key=True)
    valor = Column(String, nullable=True)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True, index=True)
    nome = Column(String, nullable=True)
    # "admin": acesso completo (cadastro, upload de fatura, gerenciar usuários)
    # "leitura": só visualiza Painel, Consumo, Rateio e Alertas
    papel = Column(String, nullable=False, default="leitura")
    ativo = Column(Boolean, nullable=False, default=True)
