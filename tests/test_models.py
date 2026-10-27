from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from safecat.domain.models import (
    Atestado,
    Cat,
    CodigoTabela,
    Emitente,
    Gravidade,
    Lateralidade,
    LocalAcidente,
    OrgaoClasse,
    TipoAcidente,
    TipoCat,
    TipoLocal,
    Trabalhador,
)

Dados = Callable[..., dict[str, Any]]
HOJE = date.today()


def test_cat_minima_tem_pendencias(cat_minima: Cat) -> None:
    pend = cat_minima.pendencias_s2210()
    assert "Hora do acidente (hrAcid)" in pend
    assert any("Tabela 13" in p for p in pend)
    assert "Atestado médico (atestado)" in pend
    assert cat_minima.dias_perdidos == 0
    assert cat_minima.trabalhador.cpf == "52998224725"
    assert cat_minima.trabalhador.cpf_formatado == "529.982.247-25"


def test_cat_completa_sem_pendencias(cat_completa: Cat) -> None:
    assert cat_completa.pendencias_s2210() == []
    assert cat_completa.dias_perdidos == 15
    assert cat_completa.atestado is not None
    assert cat_completa.atestado.cid == "S525"
    assert cat_completa.local is not None
    assert cat_completa.local.uf == "SP"
    assert cat_completa.horas_trabalhadas_antes == "02:15"


def test_atestado_pendencias_parciais(cat_dados: Dados) -> None:
    cat = Cat.model_validate(cat_dados(atestado={"data_atendimento": (HOJE - timedelta(days=1)).isoformat()}))
    pend = cat.pendencias_s2210()
    assert "CID-10 (codCID)" in pend
    assert "Emitente do atestado (emitente)" in pend
    assert any("Tabela 17" in p for p in pend)


@pytest.mark.parametrize(
    ("over", "trecho"),
    [
        ({"data_acidente": (HOJE + timedelta(days=1)).isoformat()}, "futura"),
        ({"data_acidente": "1850-01-01"}, "inválida"),
        ({"trabalhador": {"nome": "Maria", "cpf": "111.111.111-11"}}, "CPF"),
        ({"trabalhador": {"nome": "Maria Lima", "cpf": "52998224725", "pis_nit": "12345678901"}}, "PIS"),
        ({"relato": "curto"}, "relato"),
        ({"tipo_acidente": 2, "hora_acidente": "10:00"}, "Doença"),
        ({"tipo_cat": 3}, "óbito"),
        ({"tipo_cat": 2, "obito": True, "data_obito": HOJE.isoformat()}, "reabertura"),
        ({"obito": True}, "data do óbito"),
        ({"data_obito": HOJE.isoformat()}, "sem indicação"),
        ({"horas_trabalhadas_antes": "10:75"}, "HH:MM"),
        ({"horas_trabalhadas_antes": "abc"}, "HH:MM"),
        ({"ultimo_dia_trabalhado": (HOJE + timedelta(days=2)).isoformat()}, "futuro"),
        ({"tipo_cat": 9}, "tipo_cat"),
    ],
)
def test_cat_invalida(cat_dados: Dados, over: dict[str, Any], trecho: str) -> None:
    with pytest.raises(ValidationError) as exc:
        Cat.model_validate(cat_dados(**over))
    assert trecho.lower() in str(exc.value).lower()


def test_datas_incoerentes(cat_dados: Dados) -> None:
    dt = HOJE - timedelta(days=5)
    with pytest.raises(ValidationError, match="nascimento"):
        Cat.model_validate(
            cat_dados(
                data_acidente=dt.isoformat(),
                trabalhador={"nome": "Ana Paula", "cpf": "52998224725", "data_nascimento": dt.isoformat()},
            )
        )
    with pytest.raises(ValidationError, match="atendimento"):
        Cat.model_validate(
            cat_dados(data_acidente=dt.isoformat(), atestado={"data_atendimento": (dt - timedelta(days=1)).isoformat()})
        )
    with pytest.raises(ValidationError, match="óbito"):
        Cat.model_validate(
            cat_dados(data_acidente=dt.isoformat(), obito=True, data_obito=(dt - timedelta(days=1)).isoformat())
        )
    with pytest.raises(ValidationError, match="afastamento"):
        Cat.model_validate(
            cat_dados(
                tipo_cat=3,
                obito=True,
                data_obito=HOJE.isoformat(),
                atestado={"data_atendimento": HOJE.isoformat(), "afastamento": True},
            )
        )


def test_obito_valido(cat_dados: Dados) -> None:
    cat = Cat.model_validate(cat_dados(tipo_cat=3, obito=True, data_obito=HOJE.isoformat()))
    assert cat.tipo_cat is TipoCat.COMUNICACAO_OBITO


def test_trajeto_antigo_nao_exige_hora(cat_dados: Dados) -> None:
    cat = Cat.model_validate(cat_dados(tipo_acidente=3, data_acidente="2021-06-01"))
    assert "Hora do acidente (hrAcid)" not in cat.pendencias_s2210()
    cat2 = Cat.model_validate(cat_dados(tipo_acidente=2))
    assert "Hora do acidente (hrAcid)" not in cat2.pendencias_s2210()


def test_codigo_tabela() -> None:
    assert CodigoTabela(codigo=" 753030000 ", descricao="x").codigo == "753030000"
    with pytest.raises(ValidationError, match="9 dígitos"):
        CodigoTabela(codigo="7530", descricao="x")
    with pytest.raises(ValidationError):
        CodigoTabela(codigo="753030000", descricao="  ")


def test_emitente() -> None:
    e = Emitente(nome="Dr. Paulo", orgao_classe=OrgaoClasse.CRM, numero="12345", uf="rj")
    assert e.registro == "CRM 12345/RJ"
    assert Emitente(nome="Dra. Rita", orgao_classe=OrgaoClasse.RMS, numero="99").registro == "RMS 99"
    with pytest.raises(ValidationError, match="UF do conselho"):
        Emitente(nome="Dr. Paulo", orgao_classe=OrgaoClasse.CRM, numero="12345")
    with pytest.raises(ValidationError, match="orgao_classe"):
        Emitente(nome="Dr. Paulo", numero="12345", uf="SP")  # conselho nunca é presumido
    with pytest.raises(ValidationError, match="UF inválida"):
        Emitente(nome="Dr. Paulo", orgao_classe=OrgaoClasse.CRM, numero="12345", uf="ZZ")
    with pytest.raises(ValidationError, match="letras e dígitos"):
        Emitente(nome="Dr. Paulo", orgao_classe=OrgaoClasse.CRM, numero="12-345", uf="SP")
    assert Emitente(nome="Dr. Paulo", orgao_classe=OrgaoClasse.RMS, numero="1", uf=" ").uf is None


def test_atestado_e_local() -> None:
    a = Atestado(data_atendimento=HOJE, cid="", observacao="  ")
    assert a.cid is None
    assert a.observacao is None
    with pytest.raises(ValidationError, match="CID-10"):
        Atestado(data_atendimento=HOJE, cid="XYZ")
    with pytest.raises(ValidationError):
        Atestado(data_atendimento=HOJE, duracao_tratamento_dias=10000)
    assert LocalAcidente(tipo=TipoLocal.VIA_PUBLICA, uf="").uf is None
    with pytest.raises(ValidationError):
        LocalAcidente(tipo=TipoLocal.VIA_PUBLICA, uf="QQ")


def test_trabalhador_campos_em_branco() -> None:
    t = Trabalhador(nome="Ana Lima", cpf="52998224725", pis_nit="", setor="  ", cargo="")
    assert t.pis_nit is None
    assert t.setor is None
    assert t.cargo is None


def test_rotulos_enums() -> None:
    assert [t.rotulo for t in TipoCat] == ["Inicial", "Reabertura", "Comunicação de óbito"]
    assert [t.rotulo for t in TipoAcidente] == ["Típico", "Doença", "Trajeto"]
    assert TipoLocal.OUTROS.rotulo == "Outros"
    assert all(t.rotulo for t in TipoLocal)
    assert Lateralidade.AMBAS.rotulo == "Ambas"
    assert Gravidade.FATAL.rotulo == "Fatal"
    assert OrgaoClasse.CRO.rotulo == "CRO"
