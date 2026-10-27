"""Página: registrar nova CAT."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st
from pydantic import ValidationError

from safecat.ai import Analyzer, AnalyzerError
from safecat.ai.extraction import extrair_atestado
from safecat.ai.schemas import AVISO_REVISAO, AnaliseResultado, DadosAtestado, Origem, Porque
from safecat.config import Settings
from safecat.domain.models import (
    Cat,
    Gravidade,
    Lateralidade,
    OrgaoClasse,
    TipoAcidente,
    TipoCat,
    TipoLocal,
)
from safecat.domain.validators import UFS
from safecat.esocial.tables import Catalogo, TabelaESocial
from safecat.pdf import gerar_pdf_cat
from safecat.store import CatRepository
from safecat.ui import services
from safecat.ui.errors import mensagens
from safecat.ui.widgets import OPCAO_NAO_INFORMADO, codigo_tabela, md, sim_nao

UFS_ORDENADAS = [OPCAO_NAO_INFORMADO, *sorted(UFS)]


def _sem_padrao(key: str) -> dict[str, Any]:
    """``value=None`` só quando o campo ainda não foi pré-preenchido via session_state."""
    return {} if key in st.session_state else {"value": None}


def _aplicar_extracao(dados: DadosAtestado) -> list[str]:
    """Pré-preenche campos (antes de os widgets serem criados nesta execução)."""
    ss = st.session_state
    preenchidos: list[str] = []
    if dados.nome_paciente:
        ss["f_nome"] = dados.nome_paciente
        preenchidos.append("nome")
    if dados.data_atendimento:
        ss["f_tem_atestado"] = True
        ss["f_dtatend"] = date.fromisoformat(dados.data_atendimento)
        preenchidos.append("data do atendimento")
    if dados.dias_afastamento is not None:
        ss["f_tem_atestado"] = True
        ss["f_durtrat"] = dados.dias_afastamento
        preenchidos.append("dias")
    if dados.cid:
        ss["f_tem_atestado"] = True
        ss["f_cid_busca"] = dados.cid
        preenchidos.append("CID")
    if dados.medico_nome:
        ss["f_emit_nome"] = dados.medico_nome
        preenchidos.append("médico")
    if dados.conselho_numero:
        ss["f_emit_num"] = dados.conselho_numero
        preenchidos.append("registro do médico")
    if dados.conselho in {"CRM", "CRO", "RMS"}:
        ss["f_emit_oc"] = dados.conselho
    if dados.conselho_uf:
        ss["f_emit_uf"] = dados.conselho_uf
    return preenchidos


def _secao_atestado(analyzer: Analyzer) -> None:
    st.subheader("1. Atestado médico (opcional)")
    arquivo = st.file_uploader(
        "Envie o atestado (PDF, PNG ou JPG, até 10 MB)", type=["pdf", "png", "jpg", "jpeg"], key="f_upload"
    )
    if not analyzer.usa_llm:
        st.caption(
            "Sem provedor de IA configurado: PDFs com texto são lidos por regras simples; imagens e PDFs "
            "escaneados exigem preenchimento manual."
        )
    if arquivo is not None and st.button("Ler dados do atestado", key="btn_ler"):
        media = arquivo.type or "application/octet-stream"
        if media == "image/jpg":
            media = "image/jpeg"
        with st.spinner("Lendo o documento enviado..."):
            res = extrair_atestado(arquivo.getvalue(), media, analyzer)
        if res.dados is None:
            st.warning(res.mensagem or "Não foi possível extrair dados do arquivo.")
        else:
            campos = _aplicar_extracao(res.dados)
            origem = {
                "texto-pdf": "texto do PDF (regras simples)",
                "llm-texto": "IA sobre o texto do PDF",
                "llm-visao": "IA (leitura da imagem)",
            }.get(res.metodo, res.metodo)
            if campos:
                st.success(f"Campos pré-preenchidos a partir do arquivo — {origem}: {', '.join(campos)}. Confira tudo.")
            else:
                st.info("Nenhum campo reconhecido no documento. Preencha manualmente.")
            if res.mensagem:
                st.warning(res.mensagem)


def _enum_select(label: str, enum_cls: Any, key: str, *, opcional: bool = False, help: str | None = None) -> Any:
    membros = list(enum_cls)
    opcoes: list[Any] = ([None] if opcional else []) + membros
    return st.selectbox(
        label,
        opcoes,
        format_func=lambda m: OPCAO_NAO_INFORMADO if m is None else m.rotulo,
        key=key,
        help=help,
    )


def _uf(label: str, key: str) -> str | None:
    v = st.selectbox(label, UFS_ORDENADAS, key=key)
    return None if v == OPCAO_NAO_INFORMADO else v


def _coletar(catalogo: Catalogo) -> dict[str, Any]:
    hoje = date.today()
    d: dict[str, Any] = {}

    st.subheader("2. Acidentado")
    c1, c2 = st.columns(2)
    trab: dict[str, Any] = {
        "nome": c1.text_input("Nome completo *", key="f_nome", max_chars=70),
        "cpf": c2.text_input("CPF *", key="f_cpf", max_chars=14, placeholder="000.000.000-00"),
        "pis_nit": c1.text_input("PIS/NIT", key="f_pis", max_chars=14),
        "data_nascimento": c2.date_input(
            "Data de nascimento",
            value=None,
            min_value=date(1900, 1, 1),
            max_value=hoje,
            key="f_nasc",
            format="DD/MM/YYYY",
        ),
        "matricula": c1.text_input("Matrícula", key="f_matricula", max_chars=30),
        "cargo": c2.text_input("Cargo/função", key="f_cargo", max_chars=100),
        "setor": c1.text_input("Setor", key="f_setor", max_chars=100, help="Usado nos indicadores por setor."),
    }
    d["trabalhador"] = trab

    st.subheader("3. Acidente")
    c1, c2, c3 = st.columns(3)
    with c1:
        d["tipo_cat"] = _enum_select("Tipo de CAT *", TipoCat, "f_tpcat", opcional=True)
    with c2:
        d["tipo_acidente"] = _enum_select("Tipo de acidente *", TipoAcidente, "f_tpacid", opcional=True)
    with c3:
        d["gravidade"] = _enum_select(
            "Gravidade (classificação interna)",
            Gravidade,
            "f_grav",
            opcional=True,
            help="Classificação do SESMT para indicadores; não é campo do S-2210.",
        )
    c1, c2, c3 = st.columns(3)
    d["data_acidente"] = c1.date_input(
        "Data do acidente *",
        value=None,
        min_value=date(1900, 1, 1),
        max_value=hoje,
        key="f_dtacid",
        format="DD/MM/YYYY",
    )
    d["hora_acidente"] = c2.time_input("Hora do acidente", value=None, key="f_hracid", step=60)
    d["horas_trabalhadas_antes"] = c3.text_input("Horas trabalhadas antes (HH:MM)", key="f_hrstrab", max_chars=5)
    c1, c2, c3 = st.columns(3)
    d["ultimo_dia_trabalhado"] = c1.date_input(
        "Último dia trabalhado", value=None, max_value=hoje, key="f_ultdia", format="DD/MM/YYYY"
    )
    with c2:
        d["houve_afastamento"] = sim_nao("Houve afastamento?", "f_houveafast")
    with c3:
        d["comunicacao_policia"] = sim_nao("Comunicação à autoridade policial?", "f_policia")
    c1, c2 = st.columns(2)
    d["obito"] = c1.checkbox("Houve óbito", key="f_obito")
    if d["obito"]:
        d["data_obito"] = c2.date_input(
            "Data do óbito *", value=None, max_value=hoje, key="f_dtobito", format="DD/MM/YYYY"
        )

    with st.expander("Local do acidente", expanded=False):
        tipo_local = _enum_select("Tipo de local", TipoLocal, "f_tplocal", opcional=True)
        if tipo_local is not None:
            c1, c2, c3 = st.columns([2, 1, 1])
            descricao = c1.text_input("Especificação (pátio, posto de trabalho...)", key="f_localdesc")
            with c2:
                uf_local = _uf("UF do local", "f_localuf")
            municipio = c3.text_input("Município", key="f_localmun")
            d["local"] = {"tipo": tipo_local, "descricao": descricao, "uf": uf_local, "municipio": municipio}

    st.subheader("4. Lesão e enquadramento eSocial")
    cod, desc = codigo_tabela("Parte do corpo atingida", catalogo, [TabelaESocial.PARTE_CORPO], "f_parte")
    lateral = _enum_select(
        "Lateralidade da parte atingida",
        Lateralidade,
        "f_lateral",
        opcional=True,
        help="Obrigatória quando a parte atingida é informada.",
    )
    if cod or desc:
        d["parte_atingida"] = _limpar_vazios(
            {"parte": {"codigo": cod or "", "descricao": desc or ""}, "lateralidade": lateral}
        )
    tab_agente = [TabelaESocial.AGENTE_CAUSADOR_ACIDENTE]
    if d.get("tipo_acidente") is TipoAcidente.DOENCA:
        tab_agente.append(TabelaESocial.AGENTE_SITUACAO_DOENCA)
    cod, desc = codigo_tabela("Agente causador", catalogo, tab_agente, "f_agente")
    if cod or desc:
        d["agente_causador"] = {"codigo": cod or "", "descricao": desc or ""}
    cod, desc = codigo_tabela(
        "Situação geradora",
        catalogo,
        [TabelaESocial.AGENTE_SITUACAO_DOENCA, TabelaESocial.SITUACAO_GERADORA_ACIDENTE],
        "f_sitger",
    )
    if cod or desc:
        d["situacao_geradora"] = {"codigo": cod or "", "descricao": desc or ""}

    tem_atestado = st.checkbox("Há atestado médico", key="f_tem_atestado")
    if tem_atestado:
        d["atestado"] = _coletar_atestado(catalogo, hoje)

    st.subheader("5. Relato da ocorrência *")
    d["relato"] = st.text_area(
        "Descreva o que aconteceu: tarefa, local, equipamento, sequência de eventos, lesão.",
        key="f_relato",
        height=160,
        max_chars=4000,
    )
    return d


def _coletar_atestado(catalogo: Catalogo, hoje: date) -> dict[str, Any]:
    a: dict[str, Any] = {}
    c1, c2, c3 = st.columns(3)
    a["data_atendimento"] = c1.date_input(
        "Data do atendimento *", max_value=hoje, key="f_dtatend", format="DD/MM/YYYY", **_sem_padrao("f_dtatend")
    )
    a["hora_atendimento"] = c2.time_input("Hora do atendimento", value=None, key="f_hratend", step=60)
    a["duracao_tratamento_dias"] = c3.number_input(
        "Duração estimada do tratamento (dias)",
        min_value=0,
        max_value=9999,
        step=1,
        key="f_durtrat",
        **_sem_padrao("f_durtrat"),
    )
    c1, c2 = st.columns(2)
    with c1:
        a["internacao"] = sim_nao("Internação?", "f_intern")
    with c2:
        a["afastamento"] = sim_nao("Afastamento durante o tratamento?", "f_afast")

    cid_busca = st.text_input("CID-10 — código ou descrição", key="f_cid_busca", help="Ex.: S52, S52.5 ou 'antebraço'")
    if cid_busca.strip():
        achados = catalogo.cid10().buscar(cid_busca, limite=40)
        if achados:
            opcoes = {f"{e.codigo} - {e.descricao}": e for e in achados}
            escolha = st.selectbox("Selecione o CID-10", list(opcoes), key="f_cid_sel")
            if escolha:
                a["cid"] = opcoes[escolha].codigo
                a["cid_descricao"] = opcoes[escolha].descricao
        else:
            st.caption("CID não encontrado na tabela local; o código digitado será validado apenas pelo formato.")
            a["cid"] = cid_busca

    cod, desc = codigo_tabela("Natureza da lesão", catalogo, [TabelaESocial.NATUREZA_LESAO], "f_natureza")
    if cod or desc:
        a["natureza_lesao"] = {"codigo": cod or "", "descricao": desc or ""}
    c1, c2 = st.columns(2)
    a["diagnostico_provavel"] = c1.text_input("Diagnóstico provável", key="f_diag", max_chars=100)
    a["descricao_complementar"] = c2.text_input("Descrição complementar da lesão", key="f_desccomp", max_chars=200)
    a["observacao"] = st.text_input("Observação", key="f_obs", max_chars=255)

    st.markdown("**Emitente do atestado**")
    c1, c2, c3, c4 = st.columns([3, 1, 2, 1])
    nome = c1.text_input("Nome do médico/dentista", key="f_emit_nome", max_chars=70)
    oc = c2.selectbox("Conselho", [OPCAO_NAO_INFORMADO, *(o.rotulo for o in OrgaoClasse)], key="f_emit_oc")
    num = c3.text_input("Número do registro", key="f_emit_num", max_chars=14)
    with c4:
        uf = _uf("UF", "f_emit_uf")
    if nome.strip() or num.strip():
        a["emitente"] = _limpar_vazios(
            {"nome": nome, "orgao_classe": {o.rotulo: o for o in OrgaoClasse}.get(oc), "numero": num, "uf": uf}
        )
    return a


def _limpar_vazios(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v not in (None, "")}


def montar_cat(d: dict[str, Any]) -> Cat:
    payload = dict(d)
    payload["trabalhador"] = _limpar_vazios(d["trabalhador"])
    if "atestado" in d:
        payload["atestado"] = _limpar_vazios(d["atestado"])
    if "local" in d:
        payload["local"] = _limpar_vazios(d["local"])
    return Cat.model_validate(_limpar_vazios(payload))


def _secao_analise(analyzer: Analyzer, relato: str) -> AnaliseResultado | None:
    st.subheader("6. Investigação de causa raiz (5 Porquês) e plano de ação")
    st.info(
        "A análise abaixo é uma **sugestão automática** e precisa ser revisada e completada pelo SESMT "
        "com os envolvidos. Ela não substitui a investigação do acidente."
    )
    if st.button("Gerar sugestão de análise", key="btn_analisar"):
        if len(relato.strip()) < 10:
            st.error("Escreva o relato (mínimo de 10 caracteres) antes de gerar a sugestão.")
        else:
            with st.spinner("Gerando sugestão..."):
                try:
                    res = analyzer.analisar(relato)
                except AnalyzerError as exc:
                    st.error(str(exc))
                    res = None
            if res is not None:
                st.session_state["analise"] = res.model_dump(mode="json")
                for i, pq in enumerate(res.analise.cinco_porques):
                    st.session_state[f"f_pq_{i}"] = pq.resposta_sugerida or ""
                st.session_state["f_hipotese"] = res.analise.hipotese_causa_raiz or ""
                st.session_state["f_revisada"] = False

    bruto = st.session_state.get("analise")
    if not bruto:
        return None
    res = AnaliseResultado.model_validate(bruto)
    rotulo = "Modo demonstração (sem IA)" if res.origem is Origem.DEMONSTRACAO else f"IA — modelo {res.modelo}"
    st.warning(f"{AVISO_REVISAO} Origem: {rotulo}.")
    an = res.analise
    with st.container(border=True):
        st.markdown("**Fatos presentes no relato**")
        for f in an.resumo_fatos:
            st.markdown(f"- {md(f)}")
        st.markdown("**5 Porquês** — edite as respostas conforme a apuração")
        porques: list[Porque] = []
        for i, pq in enumerate(an.cinco_porques):
            resp = st.text_area(f"{i + 1}º {md(pq.pergunta)}", key=f"f_pq_{i}", height=68)
            if pq.evidencia:
                st.caption(f"Trecho do relato que sustenta a sugestão: “{md(pq.evidencia)}”")
            porques.append(Porque(pergunta=pq.pergunta, resposta_sugerida=resp.strip() or None, evidencia=pq.evidencia))
        hipotese = st.text_area("Causa raiz (conclusão do SESMT)", key="f_hipotese", height=68)

        st.markdown("**Hierarquia de controles (da mais para a menos eficaz)**")
        cols = st.columns(5)
        niveis = (
            ("Eliminação", an.controles.eliminacao),
            ("Substituição", an.controles.substituicao),
            ("Engenharia", an.controles.engenharia),
            ("Administrativo", an.controles.administrativo),
            ("EPI", an.controles.epi),
        )
        for col, (nome, itens) in zip(cols, niveis, strict=True):
            col.markdown(f"**{nome}**")
            for item in itens or ["—"]:
                col.caption(md(item))
        if an.lacunas:
            st.markdown("**Informações a apurar**")
            for lac in an.lacunas:
                st.markdown(f"- {md(lac)}")
    atualizada = an.model_copy(update={"cinco_porques": porques, "hipotese_causa_raiz": hipotese.strip() or None})
    return res.model_copy(update={"analise": atualizada})


def render(cfg: Settings) -> None:
    st.title("Registrar CAT")
    st.caption(
        "Os campos com * são obrigatórios para salvar. Os demais campos exigidos pelo S-2210 aparecem como "
        "pendências. Nenhum dado é preenchido automaticamente sem origem no documento ou no relato."
    )
    analyzer = services.analyzer(cfg)
    catalogo = services.catalogo_from(cfg)
    repo: CatRepository = services.repo_from(cfg)

    _secao_atestado(analyzer)
    dados = _coletar(catalogo)
    analise = _secao_analise(analyzer, dados.get("relato") or "")

    st.subheader("7. Salvar")
    revisada = False
    revisor = ""
    if analise is not None:
        c1, c2 = st.columns([1, 1])
        revisada = c1.checkbox("Revisei a análise sugerida", key="f_revisada")
        revisor = c2.text_input("Responsável pela revisão", key="f_revisor", max_chars=100)

    ja_salvo = st.session_state.get("ultimo_salvo") is not None
    if st.button(
        "Validar e salvar CAT",
        type="primary",
        key="btn_salvar",
        disabled=ja_salvo,
        help="Já salvo. Use 'Iniciar novo registro' para cadastrar outra CAT." if ja_salvo else None,
    ):
        try:
            cat = montar_cat(dados)
        except ValidationError as exc:
            st.error("Corrija os campos abaixo antes de salvar:")
            for m in mensagens(exc):
                st.markdown(f"- {md(m)}")
        else:
            novo_id = repo.add(cat, analise, analise_revisada=revisada, revisor=revisor.strip() or None)
            st.session_state["ultimo_salvo"] = novo_id
            st.session_state.pop("analise", None)
            st.rerun()  # re-renderiza com o botão de salvar desabilitado (evita duplicidade)

    ultimo = st.session_state.get("ultimo_salvo")
    if ultimo is not None and st.button("Iniciar novo registro (limpar formulário)", key="btn_limpar"):
        for k in [k for k in st.session_state if str(k).startswith("f_")]:
            del st.session_state[k]
        st.session_state.pop("ultimo_salvo", None)
        st.rerun()
    if ultimo is not None:
        reg = repo.get(int(ultimo))
        if reg is not None:
            st.success(f"CAT nº {reg.id} salva no histórico.")
            pend = reg.cat.pendencias_s2210()
            if pend:
                with st.expander(f"{len(pend)} pendência(s) para o S-2210"):
                    for p in pend:
                        st.markdown(f"- {md(p)}")
            pdf = gerar_pdf_cat(
                reg.cat,
                services.employer(),
                analise=reg.analise,
                analise_revisada=reg.analise_revisada,
                registro_id=reg.id,
            )
            st.download_button(
                "Baixar documento auxiliar (PDF)",
                data=pdf,
                file_name=f"cat_{reg.id}.pdf",
                mime="application/pdf",
                key="dl_novo",
            )
