from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from safecat import cli
from safecat.config import EmployerSettings, Settings, get_employer, get_settings
from safecat.domain.models import Cat
from safecat.store import CatRepository, make_engine


@pytest.fixture(autouse=True)
def _limpa_cache() -> None:
    get_settings.cache_clear()
    get_employer.cache_clear()


def test_settings_padroes_sem_segredos() -> None:
    s = Settings()
    assert not s.llm_enabled
    assert s.llm_model == "claude-opus-5-5"
    k = Settings(ANTHROPIC_API_KEY="sk-secreta")
    assert k.llm_enabled
    assert "sk-secreta" not in repr(k)
    with pytest.raises(ValidationError):
        Settings(llm_effort="turbo")


def test_empregador_valida_cnpj(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EmployerSettings().razao_social is None
    assert EmployerSettings(cnpj="").cnpj is None
    monkeypatch.setenv("SAFECAT_EMPREGADOR_CNPJ", "11.222.333/0001-81")
    assert get_employer().cnpj == "11222333000181"
    with pytest.raises(ValidationError, match="CNPJ"):
        EmployerSettings(cnpj="11.222.333/0001-00")


def test_cli_migrate_import_purge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cat_dados: Callable[..., dict[str, Any]],
) -> None:
    assert cli.main(["migrate"]) == 0
    assert "Migrações aplicadas" in capsys.readouterr().out

    csv = tmp_path / "t17.csv"
    csv.write_text("codigo;descricao\n100000001;Teste\n", encoding="utf-8")
    assert cli.main(["import-table", "17", str(csv)]) == 2  # sem destino
    destino = tmp_path / "tab"
    assert cli.main(["import-table", "17", str(csv), "--destino", str(destino)]) == 0
    assert (destino / "esocial" / "tabela17.csv").is_file()
    assert cli.main(["import-table", "17", str(tmp_path / "nao-existe.csv"), "--destino", str(destino)]) == 1

    assert cli.main(["purge"]) == 0
    assert "Nada a fazer" in capsys.readouterr().out
    repo = CatRepository(make_engine(get_settings().database_url))
    repo.add(Cat.model_validate(cat_dados(data_acidente=(date.today() - timedelta(days=50)).isoformat())))
    assert cli.main(["purge", "--older-than-days", "30"]) == 0
    assert "1 registro" in capsys.readouterr().out
