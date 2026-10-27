"""Recursos compartilhados pela UI (criados uma vez por processo)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from safecat.ai import Analyzer, build_analyzer
from safecat.config import EmployerSettings, Settings
from safecat.esocial.tables import Catalogo
from safecat.logging_setup import setup_logging
from safecat.store import CatRepository, make_engine, migrate


def settings() -> Settings:
    # Não usa o cache global: cada sessão lê o ambiente atual (útil em testes).
    return Settings()


@st.cache_resource(show_spinner=False)
def repository(database_url: str) -> CatRepository:
    setup_logging(Settings().log_level)
    migrate(database_url)
    return CatRepository(make_engine(database_url))


@st.cache_resource(show_spinner=False)
def catalogo(tables_dir: str | None) -> Catalogo:
    return Catalogo(Path(tables_dir) if tables_dir else None)


@st.cache_resource(show_spinner=False, max_entries=4)
def _analyzer_cached(cfg_json: str) -> Analyzer:
    # A chave entra na chave do cache apenas em memória do processo; nunca é persistida.
    return build_analyzer(Settings.model_validate_json(cfg_json))


def analyzer(cfg: Settings) -> Analyzer:
    """Um cliente por configuração (evita recriar conexões HTTP a cada interação)."""
    dados = cfg.model_dump(mode="json")
    if cfg.anthropic_api_key is not None:
        dados["anthropic_api_key"] = cfg.anthropic_api_key.get_secret_value()
    return _analyzer_cached(json.dumps(dados, sort_keys=True))


def employer() -> EmployerSettings:
    return EmployerSettings()


def repo_from(cfg: Settings) -> CatRepository:
    return repository(cfg.database_url)


def catalogo_from(cfg: Settings) -> Catalogo:
    return catalogo(str(cfg.tables_dir) if cfg.tables_dir else None)
