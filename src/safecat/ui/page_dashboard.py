"""Página: painel HSE com indicadores calculados a partir do banco."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from safecat import analytics
from safecat.config import Settings
from safecat.ui import services

# Posições (x, y) dos marcadores no esquema corporal.
_POSICOES: dict[str, tuple[float, float]] = {
    "Cabeça": (0.0, 9.2),
    "Pescoço": (0.0, 8.2),
    "Membros superiores": (1.6, 6.2),
    "Tronco": (0.0, 6.0),
    "Membros inferiores": (0.55, 2.2),
}
# Contorno esquemático (linhas) do corpo.
_SILHUETA: list[tuple[list[float], list[float]]] = [
    ([0, 0], [8.6, 3.8]),  # coluna
    ([-1.6, 1.6], [7.6, 7.6]),  # ombros
    ([-1.6, -2.0, -2.2], [7.6, 5.6, 3.9]),  # braço esq.
    ([1.6, 2.0, 2.2], [7.6, 5.6, 3.9]),  # braço dir.
    ([-0.8, 0.8], [3.8, 3.8]),  # quadril
    ([-0.8, -0.9, -1.0], [3.8, 1.8, 0.0]),  # perna esq.
    ([0.8, 0.9, 1.0], [3.8, 1.8, 0.0]),  # perna dir.
]


def _mapa_corporal(contagens: dict[str, int]) -> go.Figure:
    fig = go.Figure()
    for xs, ys in _SILHUETA:
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"width": 6, "color": "rgba(128,128,128,0.45)"},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_shape(type="circle", x0=-0.6, x1=0.6, y0=8.6, y1=9.8, line={"color": "rgba(128,128,128,0.45)", "width": 4})
    nomes = list(_POSICOES)
    valores = [contagens.get(n, 0) for n in nomes]
    maximo = max(valores) or 1
    fig.add_trace(
        go.Scatter(
            x=[_POSICOES[n][0] for n in nomes],
            y=[_POSICOES[n][1] for n in nomes],
            mode="markers+text",
            text=[str(v) for v in valores],
            textposition="middle center",
            textfont={"color": ["white" if v / maximo > 0.55 else "#111827" for v in valores], "size": 14},
            marker={
                "size": [26 + 34 * v / maximo for v in valores],
                "color": valores,
                "colorscale": "OrRd",
                "cmin": -0.25 * maximo,  # mantém o valor zero visível nos dois temas
                "cmax": maximo,
                "line": {"width": 1, "color": "rgba(0,0,0,0.4)"},
                "showscale": False,
            },
            customdata=nomes,
            hovertemplate="%{customdata}: %{text} ocorrência(s)<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_xaxes(visible=False, range=[-3.2, 3.2])
    fig.update_yaxes(visible=False, range=[-0.5, 10.2], scaleanchor="x")
    fig.update_layout(height=460, margin={"l": 0, "r": 0, "t": 10, "b": 0})
    return fig


def _barras(dados: dict[str, int], titulo: str, eixo: str) -> go.Figure:
    fig = go.Figure(go.Bar(x=list(dados.values()), y=list(dados.keys()), orientation="h"))
    fig.update_xaxes(rangemode="tozero", dtick=max(1, math.ceil(max(dados.values(), default=1) / 6)))
    fig.update_layout(
        title=titulo,
        height=320,
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        xaxis_title=eixo,
        yaxis={"autorange": "reversed"},
    )
    return fig


def render(cfg: Settings) -> None:
    st.title("Painel HSE")
    repo = services.repo_from(cfg)
    linhas = repo.linhas_indicadores()
    if not linhas:
        st.info("Ainda não há CATs registradas. Os indicadores aparecem aqui a partir do primeiro registro.")
        return

    r = analytics.resumo(linhas)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ocorrências registradas", r.total)
    c2.metric("Com afastamento", r.com_afastamento)
    c3.metric("Dias perdidos", r.dias_perdidos)
    c4.metric("Média de dias por afastamento", f"{r.media_dias:.1f}")

    col_mapa, col_graf = st.columns([1, 1.4])
    with col_mapa:
        st.subheader("Mapa corporal")
        regioes = analytics.por_regiao(linhas)
        st.plotly_chart(_mapa_corporal(regioes), width="stretch", theme="streamlit", key="mapa")
        outras = regioes.get(analytics.OUTRAS, 0)
        st.caption(
            "Agrupamento aproximado pela descrição da parte atingida (Tabela 13). "
            f"Múltiplas/outras/não informadas: {outras}."
        )
    with col_graf:
        indicador = st.selectbox(
            "Indicador",
            [
                "Ocorrências por setor",
                "Dias perdidos por setor",
                "Parte do corpo",
                "Gravidade",
                "Tipo de acidente",
                "Ocorrências por mês",
            ],
            key="d_ind",
        )
        if indicador == "Ocorrências por setor":
            fig = _barras(analytics.contagem(linhas, "setor"), indicador, "Ocorrências")
        elif indicador == "Dias perdidos por setor":
            fig = _barras(analytics.dias_por(linhas, "setor"), indicador, "Dias")
        elif indicador == "Parte do corpo":
            fig = _barras(analytics.contagem(linhas, "parte_corpo"), indicador, "Ocorrências")
        elif indicador == "Gravidade":
            fig = _barras(analytics.contagem(linhas, "gravidade"), indicador, "Ocorrências")
        elif indicador == "Tipo de acidente":
            fig = _barras(analytics.contagem(linhas, "tipo_acidente"), indicador, "Ocorrências")
        else:
            mes = analytics.por_mes(linhas)
            fig = go.Figure(go.Bar(x=list(mes.keys()), y=list(mes.values())))
            fig.update_xaxes(type="category")
            fig.update_yaxes(rangemode="tozero", dtick=max(1, math.ceil(max(mes.values(), default=1) / 6)))
            fig.update_layout(title=indicador, height=320, margin={"l": 10, "r": 10, "t": 40, "b": 10})
        st.plotly_chart(fig, width="stretch", theme="streamlit", key="grafico")

    st.subheader("Taxas de frequência e gravidade por setor")
    st.caption(
        "Informe as horas-homem trabalhadas (HHT) do período por setor. TF = acidentes × 10⁶ / HHT; "
        "TG = dias perdidos × 10⁶ / HHT (critério da NBR 14280). Considera todos os registros do banco."
    )
    setores = list(analytics.contagem(linhas, "setor"))
    base = pd.DataFrame({"Setor": setores, "Horas-homem (HHT)": [None] * len(setores)})
    editado = st.data_editor(
        base,
        hide_index=True,
        disabled=["Setor"],
        key="d_hht",
        width="stretch",
        column_config={"Horas-homem (HHT)": st.column_config.NumberColumn(min_value=0.0, step=1000.0)},
    )
    hht = {
        str(row["Setor"]): float(row["Horas-homem (HHT)"])
        for _, row in editado.iterrows()
        if pd.notna(row["Horas-homem (HHT)"])
    }
    taxas = analytics.taxas_por_setor(linhas, hht)
    if taxas:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Setor": t.setor,
                        "Acidentes": t.acidentes,
                        "Dias perdidos": t.dias_perdidos,
                        "HHT": t.horas_homem,
                        "TF": round(t.taxa_frequencia, 2),
                        "TG": round(t.taxa_gravidade, 2),
                    }
                    for t in taxas
                ]
            ),
            hide_index=True,
            width="stretch",
        )
