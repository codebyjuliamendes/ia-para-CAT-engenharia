"""Mapeamento ORM (SQLAlchemy 2). O esquema é versionado por Alembic (``store/migrations``)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _agora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class CatRecord(Base):
    __tablename__ = "cats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_agora, onupdate=_agora, nullable=False
    )

    # Colunas desnormalizadas para listagem e indicadores (sem relato nem CID).
    nome: Mapped[str] = mapped_column(String(70), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    setor: Mapped[str | None] = mapped_column(String(100))
    data_acidente: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo_acidente: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_cat: Mapped[int] = mapped_column(Integer, nullable=False)
    gravidade: Mapped[str | None] = mapped_column(String(20))
    parte_codigo: Mapped[str | None] = mapped_column(String(9))
    parte_descricao: Mapped[str | None] = mapped_column(String(200))
    dias_perdidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pendencias: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Documento completo (dados pessoais e de saúde) e análise sugerida.
    dados: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    analise: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    analise_revisada: Mapped[bool] = mapped_column(default=False, nullable=False)
    revisor: Mapped[str | None] = mapped_column(Text)
