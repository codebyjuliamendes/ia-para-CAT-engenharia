from __future__ import annotations

from pathlib import Path

import pytest

from safecat.esocial.tables import Catalogo, Entrada, Tabela, TabelaESocial, importar_tabela, normalize_text, parse_csv


def test_normalize_text() -> None:
    assert normalize_text("  Antebraço  E   MÃO ") == "antebraco e mao"


def test_tabelas_esocial_empacotadas_estao_vazias_ate_importar() -> None:
    cat = Catalogo()
    for t in TabelaESocial:
        tabela = cat.esocial(t)
        assert tabela.vazia
        assert t.titulo.startswith(f"Tabela {t.value}")
    assert TabelaESocial.PARTE_CORPO.arquivo == "tabela13.csv"


@pytest.mark.parametrize(
    ("cid", "descricao"),
    [
        ("S52", "Fratura do antebraço"),
        ("S62", "Fratura ao nível do punho e da mão"),
        ("S93", "Luxação, entorse e distensão das articulações e dos ligamentos ao nível do tornozelo e do pé"),
        ("T20", "Queimadura e corrosão da cabeça e pescoço"),
        ("S09", "Outros traumatismos da cabeça e os não especificados"),
        ("M75", "Lesões do ombro"),
        ("S53", "Luxação, entorse e distensão das articulações e dos ligamentos do cotovelo"),
        ("T14", "Traumatismo de região não especificada do corpo"),
    ],
)
def test_cid10_descricoes_datasus(cid: str, descricao: str) -> None:
    assert Catalogo().descricao_cid(cid) == descricao


def test_cid10_busca_sem_acento_e_por_codigo() -> None:
    cid = Catalogo().cid10()
    assert len(cid) > 14000
    assert cid.buscar("S52.5")[0].codigo == "S525"
    achados = {e.codigo for e in cid.buscar("fratura antebraco")}
    assert "S52" in achados
    assert cid.buscar("   ") == []
    assert Catalogo().descricao_cid("Y999") is None


def test_parse_csv_valida() -> None:
    texto = "codigo;descricao\n753030000;Crânio\n\n753050000;Ouvido; externo\n"
    ent = parse_csv(texto, validar="esocial")
    assert ent["753050000"].descricao == "Ouvido; externo"
    with pytest.raises(ValueError, match="código inválido"):
        parse_csv("12;x\n", validar="esocial")
    with pytest.raises(ValueError, match="descrição vazia"):
        parse_csv("753030000;\n", validar="esocial")
    with pytest.raises(ValueError, match="esperado"):
        parse_csv("753030000\n", validar="esocial")
    assert parse_csv("s52.5;Fratura\n", validar="cid")["S525"].descricao == "Fratura"


def test_tabela_busca() -> None:
    t = Tabela("x", {"753030000": Entrada("753030000", "Crânio (inclusive encéfalo)")})
    assert t.get("753030000") is not None
    assert t.buscar("cranio")[0].codigo == "753030000"
    assert t.buscar("7530")[0].codigo == "753030000"
    assert t.buscar("perna") == []


def test_importar_e_sobrepor(tmp_path: Path) -> None:
    origem = tmp_path / "t13.csv"
    origem.write_text("﻿codigo;descricao\n753030000;Teste A\n753050000;Teste B\n", encoding="utf-8")
    destino = tmp_path / "tabelas"
    assert importar_tabela(origem, TabelaESocial.PARTE_CORPO, destino) == 2
    cat = Catalogo(destino)
    assert len(cat.esocial(TabelaESocial.PARTE_CORPO)) == 2
    assert cat.esocial(TabelaESocial.NATUREZA_LESAO).vazia  # não sobreposta: usa a empacotada
    vazio = tmp_path / "vazio.csv"
    vazio.write_text("codigo;descricao\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sem nenhum"):
        importar_tabela(vazio, TabelaESocial.PARTE_CORPO, destino)
