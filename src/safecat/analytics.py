"""Indicadores HSE calculados a partir dos registros do banco (funções puras)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from safecat.esocial.tables import normalize_text
from safecat.store.repository import LinhaIndicador

SEM_SETOR = "Não informado"

# Agrupamento aproximado por palavras da descrição da parte do corpo (Tabela 13).
# Serve só para o mapa corporal; o código exato fica no registro.
REGIOES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Cabeça", ("cabeca", "cranio", "olho", "ouvido", "nariz", "boca", "face", "mandibula", "dente", "labio")),
    ("Pescoço", ("pescoco", "garganta")),
    (
        "Membros superiores",
        ("membro superior", "membros superiores", "ombro", "braco", "cotovelo", "antebraco", "punho", "mao", "dedo"),
    ),
    ("Tronco", ("tronco", "torax", "dorso", "costas", "coluna", "abdome", "abdomen", "lombar", "peito")),
    (
        "Membros inferiores",
        (
            "membro inferior",
            "membros inferiores",
            "quadril",
            "coxa",
            "joelho",
            "perna",
            "tornozelo",
            "pe ",
            "pe,",
            "artelho",
        ),
    ),
)
OUTRAS = "Múltiplas / outras / não informado"


def regiao_corporal(descricao: str | None) -> str:
    if not descricao:
        return OUTRAS
    norm = normalize_text(descricao) + " "
    encontradas = [nome for nome, palavras in REGIOES if any(p in norm for p in palavras)]
    if len(encontradas) == 1:
        return encontradas[0]
    if norm.strip() in {"pe", "pes"}:
        return "Membros inferiores"
    return OUTRAS


@dataclass(frozen=True, slots=True)
class Resumo:
    total: int
    dias_perdidos: int
    media_dias: float
    com_afastamento: int


def resumo(linhas: Sequence[LinhaIndicador]) -> Resumo:
    total = len(linhas)
    dias = sum(linha.dias_perdidos for linha in linhas)
    com_afast = sum(1 for linha in linhas if linha.dias_perdidos > 0)
    return Resumo(
        total=total, dias_perdidos=dias, media_dias=(dias / com_afast) if com_afast else 0.0, com_afastamento=com_afast
    )


def contagem(linhas: Sequence[LinhaIndicador], campo: str) -> dict[str, int]:
    c: Counter[str] = Counter()
    for linha in linhas:
        valor = getattr(linha, campo)
        c[str(valor) if valor else SEM_SETOR] += 1
    return dict(c.most_common())


def dias_por(linhas: Sequence[LinhaIndicador], campo: str) -> dict[str, int]:
    c: Counter[str] = Counter()
    for linha in linhas:
        valor = getattr(linha, campo)
        c[str(valor) if valor else SEM_SETOR] += linha.dias_perdidos
    return dict(c.most_common())


def por_regiao(linhas: Sequence[LinhaIndicador]) -> dict[str, int]:
    c: Counter[str] = Counter(regiao_corporal(linha.parte_corpo) for linha in linhas)
    return {nome: c.get(nome, 0) for nome, _ in REGIOES} | {OUTRAS: c.get(OUTRAS, 0)}


def por_mes(linhas: Sequence[LinhaIndicador]) -> dict[str, int]:
    c: Counter[str] = Counter(linha.data_acidente.strftime("%Y-%m") for linha in linhas)
    return dict(sorted(c.items()))


@dataclass(frozen=True, slots=True)
class TaxaSetor:
    setor: str
    acidentes: int
    dias_perdidos: int
    horas_homem: float
    taxa_frequencia: float
    taxa_gravidade: float


def taxas_por_setor(linhas: Sequence[LinhaIndicador], horas_homem: Mapping[str, float]) -> list[TaxaSetor]:
    """Taxas de frequência e gravidade (por 1.000.000 de horas-homem, critério da NBR 14280).

    ``horas_homem`` é informado pelo usuário por setor; setores sem HHT positiva são omitidos.
    Considera todos os registros (com e sem afastamento) no numerador da frequência.
    """
    acidentes = contagem(linhas, "setor")
    dias = dias_por(linhas, "setor")
    out: list[TaxaSetor] = []
    for setor, hht in horas_homem.items():
        if hht is None or hht <= 0:
            continue
        n = acidentes.get(setor, 0)
        d = dias.get(setor, 0)
        out.append(
            TaxaSetor(
                setor=setor,
                acidentes=n,
                dias_perdidos=d,
                horas_homem=float(hht),
                taxa_frequencia=n * 1_000_000 / hht,
                taxa_gravidade=d * 1_000_000 / hht,
            )
        )
    return sorted(out, key=lambda t: t.taxa_frequencia, reverse=True)
