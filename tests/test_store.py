from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy import inspect

from safecat.ai import DemoAnalyzer
from safecat.domain.models import Cat
from safecat.logging_setup import CpfRedactingFilter, setup_logging
from safecat.store import CatRepository, make_engine, migrate


def test_migracao_idempotente(db_url: str) -> None:
    migrate(db_url)
    migrate(db_url)
    insp = inspect(make_engine(db_url))
    assert "cats" in insp.get_table_names()
    assert "alembic_version" in insp.get_table_names()


def test_crud_e_minimizacao(repo: CatRepository, cat_completa: Cat, cat_minima: Cat) -> None:
    analise = DemoAnalyzer().analisar(cat_completa.relato)
    id1 = repo.add(cat_completa, analise, analise_revisada=True, revisor="Eng. Segurança")
    id2 = repo.add(cat_minima)

    resumos = repo.list_resumos()
    assert [r.id for r in resumos] == [id2, id1] or {r.id for r in resumos} == {id1, id2}
    r1 = next(r for r in resumos if r.id == id1)
    assert r1.cpf_mascarado == "***.982.247-**"
    assert r1.parte_corpo == "Antebraço"
    assert r1.dias_perdidos == 15
    assert r1.pendencias == 0
    assert r1.analise_revisada
    assert not hasattr(r1, "relato")
    assert not hasattr(r1, "cid")

    completo = repo.get(id1)
    assert completo is not None
    assert completo.cat == cat_completa
    assert completo.analise is not None
    assert completo.analise.analise == analise.analise
    assert completo.revisor == "Eng. Segurança"

    linhas = repo.linhas_indicadores()
    assert len(linhas) == 2
    assert not hasattr(linhas[0], "nome")

    assert repo.delete(id1)
    assert not repo.delete(id1)
    assert repo.get(id1) is None
    assert repo.get(9999) is None


def test_purge_por_retencao(repo: CatRepository, cat_dados: Callable[..., dict[str, Any]]) -> None:
    antiga = Cat.model_validate(cat_dados(data_acidente=(date.today() - timedelta(days=400)).isoformat()))
    recente = Cat.model_validate(cat_dados())
    repo.add(antiga)
    id_recente = repo.add(recente)
    assert repo.purge_older_than(365) == 1
    assert [r.id for r in repo.list_resumos()] == [id_recente]
    with pytest.raises(ValueError, match="positivo"):
        repo.purge_older_than(0)


def test_logs_nao_vazam_cpf_nem_relato(
    repo: CatRepository, cat_completa: Cat, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="safecat")
    logging.getLogger("safecat").propagate = True
    repo.add(cat_completa)
    texto = caplog.text
    assert cat_completa.trabalhador.cpf not in texto
    assert cat_completa.relato not in texto
    assert "S525" not in texto


def test_filtro_mascara_cpf() -> None:
    rec = logging.LogRecord("safecat", logging.INFO, __file__, 1, "cpf %s", ("529.982.247-25",), None)
    assert CpfRedactingFilter().filter(rec)
    assert rec.getMessage() == "cpf ***.982.247-**"
    setup_logging("DEBUG")
    setup_logging("DEBUG")  # idempotente
    handlers = logging.getLogger("safecat").handlers
    assert sum(any(isinstance(f, CpfRedactingFilter) for f in h.filters) for h in handlers) == 1
