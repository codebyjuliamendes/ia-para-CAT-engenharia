"""Fluxos principais da UI com o AppTest do Streamlit (modo demonstração, banco temporário)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from safecat.domain.models import Lateralidade, TipoAcidente, TipoCat
from safecat.store import CatRepository, make_engine

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


@pytest.fixture
def at() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    assert not app.exception
    return app


def _ir(app: AppTest, pagina: str) -> None:
    app.sidebar.radio(key="nav").set_value(pagina).run()
    assert not app.exception


def _textos(app: AppTest) -> str:
    partes = [m.value for m in app.markdown] + [str(e.value) for e in app.error] + [str(w.value) for w in app.warning]
    partes += [str(s.value) for s in app.success] + [str(i.value) for i in app.info] + [c.value for c in app.caption]
    return "\n".join(partes).replace("\\", "")  # remove escapes de Markdown


def test_inicio_modo_demonstracao_e_dashboard_vazio(at: AppTest) -> None:
    assert "Modo demonstração" in " ".join(str(w.value) for w in at.sidebar.warning)
    assert any("Ainda não há CATs" in str(i.value) for i in at.info)


def test_validacao_impede_salvar_dados_invalidos(at: AppTest) -> None:
    _ir(at, "Registrar CAT")
    at.text_input(key="f_nome").set_value("Fulano de Tal")
    at.text_input(key="f_cpf").set_value("111.111.111-11")
    at.button(key="btn_salvar").click().run()
    texto = _textos(at)
    assert "Corrija os campos" in texto
    assert "CPF" in texto
    assert "Data do acidente" in texto
    assert "Tipo de CAT: campo obrigatório" in texto
    assert "Tipo de acidente: campo obrigatório" in texto


def test_fluxo_completo_registrar_analisar_salvar_historico(at: AppTest, db_url: str) -> None:
    _ir(at, "Registrar CAT")
    at.text_input(key="f_nome").set_value("Joana Prado")
    at.text_input(key="f_cpf").set_value("529.982.247-25")
    at.text_input(key="f_setor").set_value("Logística")
    at.selectbox(key="f_tpcat").set_value(TipoCat.INICIAL)
    at.selectbox(key="f_tpacid").set_value(TipoAcidente.TIPICO)
    at.date_input(key="f_dtacid").set_value(date.today() - timedelta(days=1))
    at.text_area(key="f_relato").set_value("Ao operar a prensa, a colaboradora prensou o dedo da mão esquerda.")
    at.text_input(key="f_parte_cod").set_value("123456789")
    at.text_input(key="f_parte_desc").set_value("Dedo")
    at.run()
    at.button(key="btn_salvar").click().run()
    assert "Lateralidade: campo obrigatório" in _textos(at)  # nunca presumida
    at.selectbox(key="f_lateral").set_value(Lateralidade.ESQUERDA).run()

    at.button(key="btn_analisar").click().run()
    assert not at.exception
    assert any("Sugestão automática — revisar" in str(w.value) for w in at.warning)
    assert any("Modo demonstração" in str(w.value) for w in at.warning)
    # Respostas dos 5 Porquês ficam em branco para o SESMT preencher.
    assert at.text_area(key="f_pq_0").value == ""
    at.text_area(key="f_pq_0").set_value("Proteção da prensa estava aberta.")
    at.checkbox(key="f_revisada").check()
    at.text_input(key="f_revisor").set_value("Téc. Segurança")
    at.button(key="btn_salvar").click().run()
    assert not at.exception
    assert any("salva no histórico" in str(s.value) for s in at.success)
    assert at.get("download_button")

    repo = CatRepository(make_engine(db_url))
    (resumo,) = repo.list_resumos()
    reg = repo.get(resumo.id)
    assert reg is not None
    assert reg.analise_revisada
    assert reg.analise is not None
    assert reg.analise.analise.cinco_porques[0].resposta_sugerida == "Proteção da prensa estava aberta."
    assert reg.cat.parte_atingida is not None
    assert reg.cat.parte_atingida.parte.codigo == "123456789"

    # Nova sessão (equivale a recarregar a página): o registro continua no histórico.
    novo = AppTest.from_file(APP, default_timeout=30)
    novo.run()
    _ir(novo, "Histórico")
    df = novo.dataframe[0].value
    assert list(df["Acidentado"]) == ["Joana Prado"]
    assert list(df["CPF"]) == ["***.982.247-**"]
    assert "Relato" not in df.columns
    assert "529.982.247-25" not in _textos(novo)
    novo.toggle(key=f"h_full_{resumo.id}").set_value(True).run()
    assert "529.982.247-25" in _textos(novo)

    _ir(novo, "Painel HSE")
    assert next(m.value for m in novo.metric) == "1"

    _ir(novo, "Histórico")
    novo.checkbox(key=f"h_conf_{resumo.id}").check().run()
    novo.button(key=f"h_del_{resumo.id}").click().run()
    assert repo.list_resumos() == []


def test_paginas_sobre_e_atestado_sem_chave(at: AppTest) -> None:
    _ir(at, "Sobre e privacidade")
    texto = _textos(at)
    assert "Tabela 13 - Parte do corpo atingida" in texto
    assert "LGPD" in texto
    _ir(at, "Registrar CAT")
    assert any("imagens e PDFs escaneados" in c.value for c in at.caption)


def test_tabelas_importadas_habilitam_busca_e_cid(at: AppTest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from safecat.esocial.tables import TabelaESocial, importar_tabela

    origem = tmp_path / "t13.csv"
    origem.write_text("codigo;descricao\n100000001;Região de teste A\n100000002;Região de teste B\n", encoding="utf-8")
    importar_tabela(origem, TabelaESocial.PARTE_CORPO, tmp_path / "tab")
    monkeypatch.setenv("SAFECAT_TABLES_DIR", str(tmp_path / "tab"))
    app = AppTest.from_file(APP, default_timeout=30)
    app.run()
    _ir(app, "Registrar CAT")
    app.text_input(key="f_parte_busca").set_value("regiao teste b").run()
    assert app.selectbox(key="f_parte_sel").value == "100000002 - Região de teste B"
    app.text_input(key="f_parte_busca").set_value("inexistente").run()
    assert any("Nenhum código" in c.value for c in app.caption)

    app.checkbox(key="f_tem_atestado").check().run()
    app.text_input(key="f_cid_busca").set_value("S52.5").run()
    assert app.selectbox(key="f_cid_sel").value.startswith("S525")
    app.text_input(key="f_cid_busca").set_value("Y99.9").run()
    assert any("CID não encontrado" in c.value for c in app.caption)
    app.text_input(key="f_emit_nome").set_value("Dra. Lia Reis")
    app.text_input(key="f_emit_num").set_value("4321")
    app.button(key="btn_salvar").click().run()
    texto = _textos(app)
    assert "Conselho: campo obrigatório" in texto
    app.selectbox(key="f_emit_oc").set_value("CRM")
    app.button(key="btn_salvar").click().run()
    texto = _textos(app)
    assert "UF do conselho" in texto
    assert "Data do atendimento" in texto


def test_analise_exige_relato(at: AppTest) -> None:
    _ir(at, "Registrar CAT")
    at.button(key="btn_analisar").click().run()
    assert any("Escreva o relato" in str(e.value) for e in at.error)


def test_dashboard_com_dados_e_taxas(at: AppTest, db_url: str) -> None:
    from safecat.domain.models import Cat

    repo = CatRepository(make_engine(db_url))
    repo.add(
        Cat.model_validate(
            {
                "trabalhador": {"nome": "Caio Reis", "cpf": "52998224725", "setor": "Pintura"},
                "tipo_cat": 1,
                "tipo_acidente": 1,
                "data_acidente": (date.today() - timedelta(days=2)).isoformat(),
                "relato": "Respingo de solvente atingiu o olho direito durante a limpeza da pistola.",
                "gravidade": "leve",
                "parte_atingida": {"parte": {"codigo": "100000001", "descricao": "Olho"}, "lateralidade": 2},
            }
        )
    )
    _ir(at, "Painel HSE")
    assert next(m.value for m in at.metric) == "1"
    for opcao in ["Dias perdidos por setor", "Parte do corpo", "Gravidade", "Tipo de acidente", "Ocorrências por mês"]:
        at.selectbox(key="d_ind").set_value(opcao).run()
        assert not at.exception
