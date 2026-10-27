from __future__ import annotations

from datetime import date

import pytest

from safecat import analytics
from safecat.store import LinhaIndicador


def _l(setor: str | None, parte: str | None, dias: int, grav: str | None = "Leve", mes: int = 1) -> LinhaIndicador:
    return LinhaIndicador(
        setor=setor,
        data_acidente=date(2024, mes, 10),
        tipo_acidente="Típico",
        gravidade=grav,
        parte_corpo=parte,
        dias_perdidos=dias,
    )


LINHAS = [
    _l("Usinagem", "Mão (exceto punho ou dedos)", 10),
    _l("Usinagem", "Dedo", 0, mes=2),
    _l("Expedição", "Articulação do tornozelo", 5, "Moderada"),
    _l(None, None, 0, None),
]


@pytest.mark.parametrize(
    ("desc", "regiao"),
    [
        ("Crânio (inclusive encéfalo)", "Cabeça"),
        ("Pescoço", "Pescoço"),
        ("Antebraço (entre o punho e o cotovelo)", "Membros superiores"),
        ("Tórax (inclusive órgãos internos)", "Tronco"),
        ("Pé (exceto artelhos)", "Membros inferiores"),
        ("Quadril", "Membros inferiores"),
        ("Partes múltiplas", analytics.OUTRAS),
        (None, analytics.OUTRAS),
        ("Pé", "Membros inferiores"),
    ],
)
def test_regiao_corporal(desc: str | None, regiao: str) -> None:
    assert analytics.regiao_corporal(desc) == regiao


def test_resumo_e_contagens() -> None:
    r = analytics.resumo(LINHAS)
    assert (r.total, r.dias_perdidos, r.com_afastamento) == (4, 15, 2)
    assert r.media_dias == pytest.approx(7.5)
    assert analytics.resumo([]).media_dias == 0.0
    assert analytics.contagem(LINHAS, "setor") == {"Usinagem": 2, "Expedição": 1, analytics.SEM_SETOR: 1}
    assert analytics.dias_por(LINHAS, "setor")["Usinagem"] == 10
    assert analytics.por_mes(LINHAS) == {"2024-01": 3, "2024-02": 1}
    reg = analytics.por_regiao(LINHAS)
    assert reg["Membros superiores"] == 2
    assert reg["Membros inferiores"] == 1
    assert reg[analytics.OUTRAS] == 1
    assert reg["Cabeça"] == 0


def test_taxas_por_setor() -> None:
    taxas = analytics.taxas_por_setor(LINHAS, {"Usinagem": 200_000, "Expedição": 100_000, "Vazio": 0})
    assert [t.setor for t in taxas] == ["Usinagem", "Expedição"]
    u = taxas[0]
    assert u.taxa_frequencia == pytest.approx(10.0)
    assert u.taxa_gravidade == pytest.approx(50.0)
    assert taxas[1].taxa_gravidade == pytest.approx(50.0)
