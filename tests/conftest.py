from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from safecat.domain.models import Cat
from safecat.store import CatRepository, make_engine, migrate

CPF_VALIDO = "52998224725"  # exemplo clássico de CPF válido (fictício)


def gerar_pis(base10: str) -> str:
    pesos = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    dv = 11 - sum(int(d) * w for d, w in zip(base10, pesos, strict=True)) % 11
    return base10 + str(0 if dv >= 10 else dv)


PIS_VALIDO = gerar_pis("1204567890")


@pytest.fixture(autouse=True)
def _ambiente_isolado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Nenhum teste lê .env real, chave de API ou banco local."""
    monkeypatch.chdir(tmp_path)
    for var in ("ANTHROPIC_API_KEY", "SAFECAT_ANTHROPIC_API_KEY", "SAFECAT_TABLES_DIR", "SAFECAT_FORCE_DEMO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SAFECAT_DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def repo(db_url: str) -> CatRepository:
    migrate(db_url)
    return CatRepository(make_engine(db_url))


@pytest.fixture
def cat_dados() -> Callable[..., dict[str, Any]]:
    def _make(**over: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "trabalhador": {"nome": "Maria da Silva", "cpf": "529.982.247-25", "setor": "Expedição"},
            "tipo_cat": 1,
            "tipo_acidente": 1,
            "data_acidente": (date.today() - timedelta(days=3)).isoformat(),
            "relato": "Ao descer a escada do mezanino a colaboradora escorregou e torceu o tornozelo direito.",
        }
        base.update(over)
        return base

    return _make


@pytest.fixture
def cat_minima(cat_dados: Callable[..., dict[str, Any]]) -> Cat:
    return Cat.model_validate(cat_dados())


@pytest.fixture
def cat_completa(cat_dados: Callable[..., dict[str, Any]]) -> Cat:
    hoje = date.today()
    return Cat.model_validate(
        cat_dados(
            trabalhador={
                "nome": "José Araújo",
                "cpf": CPF_VALIDO,
                "pis_nit": PIS_VALIDO,
                "data_nascimento": "1990-05-04",
                "cargo": "Operador",
                "setor": "Usinagem",
                "matricula": "A-77",
            },
            hora_acidente="09:30",
            horas_trabalhadas_antes="02:15",
            comunicacao_policia=False,
            ultimo_dia_trabalhado=(hoje - timedelta(days=3)).isoformat(),
            houve_afastamento=True,
            gravidade="moderada",
            local={"tipo": 1, "descricao": "Posto 3", "uf": "sp", "municipio": "Sorocaba"},
            parte_atingida={"parte": {"codigo": "123456789", "descricao": "Antebraço"}, "lateralidade": 2},
            agente_causador={"codigo": "111111111", "descricao": "Torno"},
            situacao_geradora={"codigo": "222222222", "descricao": "Impacto"},
            atestado={
                "data_atendimento": (hoje - timedelta(days=2)).isoformat(),
                "hora_atendimento": "10:15",
                "internacao": False,
                "duracao_tratamento_dias": 15,
                "afastamento": True,
                "natureza_lesao": {"codigo": "333333333", "descricao": "Fratura"},
                "cid": "s52.5",
                "cid_descricao": "Fratura da extremidade distal do rádio",
                "emitente": {"nome": "Dra. Ana Costa", "orgao_classe": 1, "numero": "123456", "uf": "SP"},
            },
        )
    )
