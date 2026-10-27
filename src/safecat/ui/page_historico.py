"""Página: histórico de CATs (com minimização de dados pessoais)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from safecat.ai.schemas import AVISO_REVISAO, Origem
from safecat.config import Settings
from safecat.pdf import gerar_pdf_cat
from safecat.ui import services
from safecat.ui.widgets import md


def render(cfg: Settings) -> None:
    st.title("Histórico de CATs")
    repo = services.repo_from(cfg)
    resumos = repo.list_resumos()
    if not resumos:
        st.info("Nenhuma CAT registrada ainda. Use 'Registrar CAT' no menu.")
        return

    df = pd.DataFrame(
        [
            {
                "ID": r.id,
                "Acidentado": r.nome,
                "CPF": r.cpf_mascarado,
                "Setor": r.setor or "—",
                "Data": r.data_acidente.strftime("%d/%m/%Y"),
                "Tipo": r.tipo_acidente,
                "Gravidade": r.gravidade or "—",
                "Parte do corpo": r.parte_corpo or "—",
                "Dias perdidos": r.dias_perdidos,
                "Pendências S-2210": r.pendencias,
                "Análise revisada": "Sim" if r.analise_revisada else "Não",
            }
            for r in resumos
        ]
    )
    st.dataframe(df, hide_index=True, width="stretch")
    st.caption("CPF mascarado na listagem. Relato e CID só aparecem no detalhe, sob demanda.")

    ids = [r.id for r in resumos]
    cat_id = st.selectbox("Abrir registro", ids, format_func=lambda i: f"CAT nº {i}", key="h_sel")
    if cat_id is None:
        return
    reg = repo.get(int(cat_id))
    if reg is None:
        st.warning("Registro não encontrado (pode ter sido excluído).")
        return
    cat = reg.cat

    mostrar = st.toggle(
        "Exibir dados pessoais e de saúde (CPF completo, relato, CID)",
        key=f"h_full_{cat_id}",
        help="Dados sensíveis (LGPD art. 11). Exiba apenas quando necessário.",
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Acidentado:** {md(cat.trabalhador.nome)}")
        cpf = cat.trabalhador.cpf_formatado if mostrar else next(r.cpf_mascarado for r in resumos if r.id == cat_id)
        st.markdown(f"**CPF:** {md(cpf)}")
        st.markdown(f"**Setor:** {md(cat.trabalhador.setor or 'não informado')}")
        st.markdown(f"**Data do acidente:** {cat.data_acidente.strftime('%d/%m/%Y')}")
    with c2:
        st.markdown(f"**Tipo de CAT:** {cat.tipo_cat.rotulo} · **Tipo de acidente:** {cat.tipo_acidente.rotulo}")
        st.markdown(f"**Gravidade:** {cat.gravidade.rotulo if cat.gravidade else 'não informada'}")
        if cat.parte_atingida:
            p = cat.parte_atingida
            st.markdown(f"**Parte atingida:** {md(p.parte.codigo)} - {md(p.parte.descricao)} ({p.lateralidade.rotulo})")
        st.markdown(f"**Dias perdidos:** {cat.dias_perdidos}")
    if mostrar:
        if cat.atestado and cat.atestado.cid:
            st.markdown(f"**CID-10:** {md(cat.atestado.cid)} {md(cat.atestado.cid_descricao or '')}")
        st.markdown("**Relato:**")
        st.text(cat.relato)

    if reg.analise is not None:
        origem = "modo demonstração" if reg.analise.origem is Origem.DEMONSTRACAO else f"IA ({reg.analise.modelo})"
        status = "revisada" if reg.analise_revisada else "não revisada"
        st.caption(f"Análise: {AVISO_REVISAO} Origem: {origem}; {status}.")

    pend = cat.pendencias_s2210()
    if pend:
        with st.expander(f"{len(pend)} pendência(s) para o S-2210"):
            for item in pend:
                st.markdown(f"- {md(item)}")

    pdf = gerar_pdf_cat(
        cat, services.employer(), analise=reg.analise, analise_revisada=reg.analise_revisada, registro_id=reg.id
    )
    st.download_button(
        "Baixar documento auxiliar (PDF)",
        data=pdf,
        file_name=f"cat_{reg.id}.pdf",
        mime="application/pdf",
        key=f"h_dl_{reg.id}",
    )

    with st.expander("Excluir registro"):
        st.write("A exclusão é definitiva e remove todos os dados pessoais deste registro do banco.")
        confirmar = st.checkbox(f"Confirmo a exclusão da CAT nº {reg.id}", key=f"h_conf_{reg.id}")
        if st.button("Excluir definitivamente", disabled=not confirmar, key=f"h_del_{reg.id}"):
            repo.delete(reg.id)
            st.session_state.pop("h_sel", None)
            st.success(f"CAT nº {reg.id} excluída.")
            st.rerun()
