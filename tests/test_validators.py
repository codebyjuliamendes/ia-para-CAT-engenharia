from __future__ import annotations

import pytest

from safecat.domain import validators as v
from tests.conftest import PIS_VALIDO, gerar_pis


@pytest.mark.parametrize("cpf", ["529.982.247-25", "52998224725", "111.444.777-35"])
def test_cpf_valido(cpf: str) -> None:
    assert v.validate_cpf(cpf)


@pytest.mark.parametrize("cpf", ["529.982.247-24", "111.111.111-11", "123", "", "5299822472a5"])
def test_cpf_invalido(cpf: str) -> None:
    assert not v.validate_cpf(cpf)


def test_pis_valido_e_invalido() -> None:
    assert v.validate_pis(PIS_VALIDO)
    assert v.validate_pis(gerar_pis("1700000000"))  # caso com resto que leva DV a 0
    errado = PIS_VALIDO[:-1] + str((int(PIS_VALIDO[-1]) + 1) % 10)
    assert not v.validate_pis(errado)
    assert not v.validate_pis("00000000000")
    assert not v.validate_pis("123")


@pytest.mark.parametrize("cnpj", ["11.222.333/0001-81", "11222333000181", "12.ABC.345/01DE-35"])
def test_cnpj_valido(cnpj: str) -> None:
    assert v.validate_cnpj(cnpj)


@pytest.mark.parametrize("cnpj", ["11.222.333/0001-80", "00000000000000", "1122233300018", "12ABC34501DEAB"])
def test_cnpj_invalido(cnpj: str) -> None:
    assert not v.validate_cnpj(cnpj)


@pytest.mark.parametrize(("raw", "norm"), [("s52", "S52"), ("S52.5", "S525"), (" t14 ", "T14"), ("M75-1", "M751")])
def test_cid_normaliza_e_valida(raw: str, norm: str) -> None:
    assert v.normalize_cid(raw) == norm
    assert v.validate_cid(raw)


@pytest.mark.parametrize("cid", ["52", "SS2", "S5", "S52.55", "", "S52A"])
def test_cid_invalido(cid: str) -> None:
    assert not v.validate_cid(cid)


def test_uf_e_codigo_esocial() -> None:
    assert v.validate_uf("sp")
    assert not v.validate_uf("XX")
    assert v.validate_esocial_code("753030000")
    assert not v.validate_esocial_code("75303000")
    assert not v.validate_esocial_code("75303000A")


def test_mascara_e_formatacao_cpf() -> None:
    assert v.mask_cpf("529.982.247-25") == "***.982.247-**"
    assert v.mask_cpf(None) == ""
    assert v.mask_cpf("123") == "***"
    assert v.format_cpf("52998224725") == "529.982.247-25"
    assert v.format_cpf("abc") == "abc"
    assert v.redact_cpfs("cpf 529.982.247-25 e 52998224725") == "cpf ***.982.247-** e ***.982.247-**"
