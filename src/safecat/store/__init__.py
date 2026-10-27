"""Persistência (SQLAlchemy 2 + Alembic). SQLite por padrão; compatível com PostgreSQL."""

from __future__ import annotations

from alembic import command
from alembic.config import Config

from safecat.store.repository import CatCompleta, CatRepository, CatResumo, LinhaIndicador, make_engine


def alembic_config(database_url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", "safecat.store:migrations")
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return cfg


def migrate(database_url: str) -> None:
    """Aplica todas as migrações pendentes (idempotente)."""
    command.upgrade(alembic_config(database_url), "head")


__all__ = ["CatCompleta", "CatRepository", "CatResumo", "LinhaIndicador", "make_engine", "migrate"]
