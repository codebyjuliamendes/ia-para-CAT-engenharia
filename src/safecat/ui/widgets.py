"""Componentes reutilizáveis da UI (sem HTML customizado)."""

from __future__ import annotations

import re
from collections.abc import Sequence

import streamlit as st

from safecat.esocial.tables import Catalogo, Entrada, TabelaESocial

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|>~<])")

OPCAO_NAO_INFORMADO = "Não informado"


def md(texto: str) -> str:
    """Escapa texto do usuário para exibição segura em ``st.markdown``."""
    return _MD_SPECIAL.sub(r"\\\1", texto)


def sim_nao(label: str, key: str, *, help: str | None = None) -> bool | None:
    escolha = st.radio(label, [OPCAO_NAO_INFORMADO, "Sim", "Não"], key=key, horizontal=True, help=help)
    return None if escolha == OPCAO_NAO_INFORMADO else escolha == "Sim"


def codigo_tabela(
    label: str,
    catalogo: Catalogo,
    tabelas: Sequence[TabelaESocial],
    key: str,
    *,
    help: str | None = None,
) -> tuple[str | None, str | None]:
    """Seleção de código de tabela do eSocial.

    Com a tabela oficial importada: busca por texto (sem acentos) e seleção.
    Sem a tabela: digitação manual do código de 9 dígitos e da descrição.
    Retorna ``(codigo, descricao)`` ou ``(None, None)``.
    """
    entradas: list[Entrada] = []
    for t in tabelas:
        entradas.extend(catalogo.esocial(t).entradas.values())
    numeros = [str(t.value) for t in tabelas]
    nomes = f" {numeros[0]}" if len(numeros) == 1 else "s " + " e ".join(numeros)

    if entradas:
        busca = st.text_input(f"{label} — buscar (Tabela{nomes})", key=f"{key}_busca", help=help)
        if not busca:
            return None, None
        achados: list[Entrada] = []
        for t in tabelas:
            achados.extend(catalogo.esocial(t).buscar(busca, limite=30))
        if not achados:
            st.caption("Nenhum código encontrado para a busca.")
            return None, None
        opcoes = {f"{e.codigo} - {e.descricao}": e for e in achados}
        escolha = st.selectbox(f"{label} — selecione", list(opcoes), key=f"{key}_sel")
        e = opcoes[escolha] if escolha else None
        return (e.codigo, e.descricao) if e else (None, None)

    st.caption(
        f"Tabela{nomes} do eSocial não importada neste ambiente. Informe o código conforme a tabela oficial "
        "vigente (ver README: importação de tabelas)."
    )
    c1, c2 = st.columns([1, 2])
    codigo = c1.text_input(f"{label} — código (9 dígitos)", key=f"{key}_cod", max_chars=9, help=help)
    descricao = c2.text_input(f"{label} — descrição", key=f"{key}_desc")
    codigo = codigo.strip()
    descricao = descricao.strip()
    if not codigo and not descricao:
        return None, None
    return codigo or None, descricao or None
