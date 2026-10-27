"""Página: sobre o sistema, limitações e privacidade."""

from __future__ import annotations

import streamlit as st

from safecat.config import Settings
from safecat.esocial.tables import TabelaESocial
from safecat.ui import services


def render(cfg: Settings) -> None:
    st.title("Sobre o SafeCAT AI")
    st.markdown(
        """
O SafeCAT AI apoia o SESMT no **registro interno** de acidentes de trabalho, na organização dos
dados exigidos pelo evento **S-2210 (CAT)** do eSocial, na investigação de causa raiz (5 Porquês)
e no acompanhamento de indicadores.

**O que o sistema não faz**

- Não transmite a CAT ao eSocial. O PDF gerado é um *documento auxiliar*; a CAT oficial é o
  evento S-2210 enviado pelo empregador.
- Não define causas nem diagnósticos. A análise é uma **sugestão automática** que precisa ser
  revisada pelo SESMT.
- Não presume dados: campos ausentes ficam em branco ou como "não informado".

**Privacidade (LGPD)**

- CPF e dados de saúde (CID, atestado, relato) são dados pessoais — os de saúde, **sensíveis**
  (art. 11 da Lei 13.709/2018). O acesso deve ser restrito a quem precisa.
- A listagem mostra o CPF mascarado; relato e CID só aparecem sob demanda.
- Os logs não registram relato, CID nem CPF completo.
- Registros podem ser excluídos definitivamente no Histórico. A retenção é definida pela
  organização (`SAFECAT_RETENTION_DAYS` + comando `safecat purge`).
- Com IA habilitada, o relato e o atestado enviados para análise são processados pela API da
  Anthropic. Avalie a base legal e o contrato antes de habilitar.
"""
    )
    st.subheader("Tabelas de referência carregadas")
    cat = services.catalogo_from(cfg)
    for t in TabelaESocial:
        n = len(cat.esocial(t))
        st.markdown(f"- {t.titulo}: **{n}** código(s)" + ("" if n else " — não importada (entrada manual)"))
    st.markdown(f"- CID-10 (DATASUS): **{len(cat.cid10())}** códigos")
