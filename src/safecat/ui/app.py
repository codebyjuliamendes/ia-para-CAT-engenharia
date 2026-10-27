"""Aplicação Streamlit. Execute com ``streamlit run streamlit_app.py`` (na raiz do repositório)."""

from __future__ import annotations

import streamlit as st

from safecat.ui import page_dashboard, page_historico, page_nova, page_sobre, services

PAGINAS = {
    "Painel HSE": page_dashboard.render,
    "Registrar CAT": page_nova.render,
    "Histórico": page_historico.render,
    "Sobre e privacidade": page_sobre.render,
}


def main() -> None:
    st.set_page_config(page_title="SafeCAT AI", page_icon=":material/health_and_safety:", layout="wide")
    cfg = services.settings()

    with st.sidebar:
        st.title("SafeCAT AI")
        st.caption("Apoio ao SESMT: CAT (eSocial S-2210), causa raiz e indicadores")
        pagina = st.radio("Navegação", list(PAGINAS), key="nav")
        st.divider()
        analyzer = services.analyzer(cfg)
        if analyzer.usa_llm:
            st.success(f"Análise por IA ativa ({cfg.llm_model}). Sugestões sempre exigem revisão.")
        else:
            st.warning(
                "Modo demonstração: sem provedor de IA configurado. As sugestões são genéricas, "
                "determinísticas e não afirmam causas."
            )
        st.caption("O PDF é um documento auxiliar. A CAT oficial é transmitida pelo eSocial (S-2210).")

    PAGINAS[pagina](cfg)


if __name__ == "__main__":
    main()
