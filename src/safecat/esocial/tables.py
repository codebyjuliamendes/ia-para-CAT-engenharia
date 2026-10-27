"""Carga e busca das tabelas de referência (eSocial e CID-10).

As tabelas ficam em arquivos CSV versionados (``codigo;descricao``, UTF-8) dentro do pacote,
em ``safecat/data``. Um diretório externo (``SAFECAT_TABLES_DIR``) pode sobrepor qualquer
arquivo, o que permite importar a versão oficial vigente sem rebuild da imagem
(ver ``safecat import-table``).
"""

from __future__ import annotations

import csv
import io
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from importlib import resources
from pathlib import Path

from safecat.domain.validators import normalize_cid, validate_cid, validate_esocial_code

HEADER = ("codigo", "descricao")


class TabelaESocial(IntEnum):
    """Tabelas do eSocial usadas pelo S-2210 (numeração do leiaute S-1.x)."""

    PARTE_CORPO = 13
    AGENTE_CAUSADOR_ACIDENTE = 14
    AGENTE_SITUACAO_DOENCA = 15
    SITUACAO_GERADORA_ACIDENTE = 16
    NATUREZA_LESAO = 17

    @property
    def titulo(self) -> str:
        return {
            13: "Tabela 13 - Parte do corpo atingida",
            14: "Tabela 14 - Agente causador do acidente de trabalho",
            15: "Tabela 15 - Agente causador / situação geradora de doença profissional",
            16: "Tabela 16 - Situação geradora do acidente de trabalho",
            17: "Tabela 17 - Descrição da natureza da lesão",
        }[self.value]

    @property
    def arquivo(self) -> str:
        return f"tabela{self.value}.csv"


def normalize_text(text: str) -> str:
    """Minúsculas, sem acentos e com espaços colapsados (para busca)."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


@dataclass(frozen=True, slots=True)
class Entrada:
    codigo: str
    descricao: str


@dataclass(slots=True)
class Tabela:
    nome: str
    entradas: dict[str, Entrada] = field(default_factory=dict)
    _indice: list[tuple[str, str, Entrada]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._indice = [(normalize_text(e.codigo), normalize_text(e.descricao), e) for e in self.entradas.values()]

    def __len__(self) -> int:
        return len(self.entradas)

    @property
    def vazia(self) -> bool:
        return not self.entradas

    def get(self, codigo: str) -> Entrada | None:
        return self.entradas.get(codigo)

    def buscar(self, consulta: str, limite: int = 50) -> list[Entrada]:
        """Busca por código (prefixo) ou por todas as palavras da descrição, ignorando acentos."""
        q = normalize_text(consulta)
        if not q:
            return []
        termos = q.split()
        por_codigo: list[Entrada] = []
        por_texto: list[Entrada] = []
        for cod, desc, entrada in self._indice:
            if cod.startswith(q.replace(".", "")):
                por_codigo.append(entrada)
            elif all(t in desc for t in termos):
                por_texto.append(entrada)
        return (por_codigo + por_texto)[:limite]


def parse_csv(text: str, *, validar: str) -> dict[str, Entrada]:
    """Lê CSV ``codigo;descricao``. ``validar`` é ``"esocial"`` ou ``"cid"``."""
    entradas: dict[str, Entrada] = {}
    reader = csv.reader(io.StringIO(text), delimiter=";", quoting=csv.QUOTE_NONE)
    for n, row in enumerate(reader, start=1):
        if not row or not "".join(row).strip():
            continue
        if n == 1 and tuple(c.strip().lower() for c in row[:2]) == HEADER:
            continue
        if len(row) < 2:
            raise ValueError(f"linha {n}: esperado 'codigo;descricao'")
        codigo, descricao = row[0].strip(), ";".join(row[1:]).strip()
        if validar == "cid":
            codigo = normalize_cid(codigo)
            ok = validate_cid(codigo)
        else:
            codigo = codigo.replace(".", "")
            ok = validate_esocial_code(codigo)
        if not ok:
            raise ValueError(f"linha {n}: código inválido {codigo!r}")
        if not descricao:
            raise ValueError(f"linha {n}: descrição vazia")
        entradas[codigo] = Entrada(codigo, descricao)
    return entradas


def write_csv(entradas: Iterable[Entrada], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as fh:
        fh.write(";".join(HEADER) + "\n")
        for e in sorted(entradas, key=lambda x: x.codigo):
            fh.write(f"{e.codigo};{e.descricao}\n")


def _ler(relativo: str, override_dir: Path | None) -> str:
    if override_dir is not None:
        candidato = override_dir / relativo
        if candidato.is_file():
            return candidato.read_text(encoding="utf-8")
    return resources.files("safecat.data").joinpath(relativo).read_text(encoding="utf-8")


class Catalogo:
    """Acesso às tabelas carregadas (com cache em memória)."""

    def __init__(self, override_dir: Path | None = None) -> None:
        self._override = override_dir
        self._cache: dict[str, Tabela] = {}

    def esocial(self, tabela: TabelaESocial) -> Tabela:
        chave = f"esocial/{tabela.arquivo}"
        if chave not in self._cache:
            self._cache[chave] = Tabela(tabela.titulo, parse_csv(_ler(chave, self._override), validar="esocial"))
        return self._cache[chave]

    def cid10(self) -> Tabela:
        chave = "cid10/cid10.csv"
        if chave not in self._cache:
            self._cache[chave] = Tabela("CID-10", parse_csv(_ler(chave, self._override), validar="cid"))
        return self._cache[chave]

    def descricao_cid(self, codigo: str) -> str | None:
        entrada = self.cid10().get(normalize_cid(codigo))
        return entrada.descricao if entrada else None


def importar_tabela(origem: Path, tabela: TabelaESocial, destino_dir: Path) -> int:
    """Valida o CSV de ``origem`` e grava em ``destino_dir``. Retorna o número de códigos."""
    texto = origem.read_text(encoding="utf-8-sig")
    entradas = parse_csv(texto, validar="esocial")
    if not entradas:
        raise ValueError("arquivo sem nenhum código")
    write_csv(entradas.values(), destino_dir / "esocial" / tabela.arquivo)
    return len(entradas)
