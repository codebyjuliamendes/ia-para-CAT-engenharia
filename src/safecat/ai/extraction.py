"""Extração de dados do atestado médico enviado pelo usuário.

Fluxo (nunca usa texto fictício no lugar do arquivo):

1. PDF com camada de texto: o texto é lido com ``pypdf``. Com LLM disponível, o texto é
   estruturado pela IA; sem LLM, usa-se um leitor por expressões regulares sobre esse texto.
2. Imagem ou PDF escaneado (sem texto): requer o provedor de IA (visão). Sem chave, a função
   informa que a extração automática não está disponível e o usuário preenche os campos.
"""

from __future__ import annotations

import io
import logging
import re
from datetime import date

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from safecat.ai.base import Analyzer, AnalyzerError
from safecat.ai.schemas import DadosAtestado, ExtracaoResultado
from safecat.domain.validators import normalize_cid, validate_cid, validate_uf

log = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024
MIN_TEXTO_UTIL = 40
IMAGENS = {"image/png", "image/jpeg", "image/webp"}

_NOME_LETRAS = r"[A-Za-zÀ-ÖØ-öø-ÿ'´`\-]+"
_NOME_RE = re.compile(
    rf"(?:paciente|sr\.?\(?a?\)?\.?|sra\.?|senhor\(?a?\)?)\s*[:\-]?\s*"
    rf"(?P<nome>{_NOME_LETRAS}(?:\s+(?:d[aeo]s?\s+|e\s+)?{_NOME_LETRAS}){{1,7}})",
    re.IGNORECASE,
)
_CID_RE = re.compile(r"\bCID(?:[\s\-]*10)?\s*[:\-]?\s*(?P<cid>[A-Z]\s?\d{2}(?:\.?\d)?)\b", re.IGNORECASE)
_CRM_RE = re.compile(
    r"\b(?P<conselho>CRM|CRO)\s*[\-/:]?\s*(?:(?P<uf1>[A-Z]{2})\s*[\-/:]?\s*)?(?P<num>\d{1,9})"
    r"(?:\s*[\-/]\s*(?P<uf2>[A-Z]{2}))?\b",
    re.IGNORECASE,
)
_DIAS_RE = re.compile(r"\b(?P<dias>\d{1,3})\s*(?:\([^)]{0,30}\)\s*)?dias?\b", re.IGNORECASE)
_DATA_RE = re.compile(r"\b(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<a>\d{4})\b")
_STOP_NOME = re.compile(r"\s+(?:esteve|necessita|portador|foi|deve|encontra|compareceu|sob|para)\b.*$", re.I)


def texto_do_pdf(conteudo: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(conteudo))
        return "\n".join((page.extract_text() or "") for page in reader.pages[:10]).strip()
    except (PdfReadError, ValueError, KeyError, OSError) as exc:
        raise ValueError("Não foi possível ler o PDF enviado.") from exc


def ler_texto_atestado(texto: str) -> DadosAtestado:
    """Leitura determinística por regex sobre o texto REAL do documento."""
    nome = None
    if m := _NOME_RE.search(texto):
        nome = _STOP_NOME.sub("", " ".join(m.group("nome").split())).strip() or None

    cid = None
    if m := _CID_RE.search(texto):
        bruto = normalize_cid(m.group("cid"))
        cid = bruto if validate_cid(bruto) else None

    conselho = numero = uf = None
    if m := _CRM_RE.search(texto):
        conselho = m.group("conselho").upper()
        numero = m.group("num")
        cand = (m.group("uf1") or m.group("uf2") or "").upper()
        uf = cand if validate_uf(cand) else None

    dias = None
    if m := _DIAS_RE.search(texto):
        dias = int(m.group("dias"))

    data = None
    for m in _DATA_RE.finditer(texto):
        try:
            d = date(int(m.group("a")), int(m.group("m")), int(m.group("d")))
        except ValueError:
            continue
        if d <= date.today():
            data = d.isoformat()
            break

    return DadosAtestado(
        nome_paciente=nome,
        data_atendimento=data,
        dias_afastamento=dias,
        cid=cid,
        medico_nome=None,
        conselho=conselho,
        conselho_numero=numero,
        conselho_uf=uf,
    )


def extrair_atestado(conteudo: bytes, media_type: str, analyzer: Analyzer) -> ExtracaoResultado:
    if len(conteudo) > MAX_BYTES:
        return ExtracaoResultado(metodo="indisponivel", mensagem="Arquivo maior que 10 MB.")

    if media_type == "application/pdf":
        try:
            texto = texto_do_pdf(conteudo)
        except ValueError as exc:
            return ExtracaoResultado(metodo="indisponivel", mensagem=str(exc))
        if len(texto) >= MIN_TEXTO_UTIL:
            if analyzer.usa_llm:
                try:
                    dados = analyzer.estruturar_texto_atestado(texto)
                    if dados is not None:
                        return ExtracaoResultado(metodo="llm-texto", dados=dados)
                except AnalyzerError as exc:
                    log.warning("Falha ao estruturar atestado via IA; usando leitura por texto")
                    return ExtracaoResultado(
                        metodo="texto-pdf",
                        dados=ler_texto_atestado(texto),
                        mensagem=f"{exc} Campos lidos por regras simples; confira.",
                    )
            return ExtracaoResultado(metodo="texto-pdf", dados=ler_texto_atestado(texto))
        # PDF sem texto (escaneado): segue para visão.
    elif media_type not in IMAGENS:
        return ExtracaoResultado(metodo="indisponivel", mensagem=f"Formato não suportado: {media_type}.")

    if not analyzer.usa_llm:
        return ExtracaoResultado(
            metodo="indisponivel",
            mensagem=(
                "A leitura automática de imagens e PDFs escaneados requer o provedor de IA "
                "(configure ANTHROPIC_API_KEY). Preencha os campos manualmente a partir do documento."
            ),
        )
    try:
        dados = analyzer.ler_atestado(conteudo, media_type)
    except AnalyzerError as exc:
        return ExtracaoResultado(metodo="indisponivel", mensagem=str(exc))
    if dados is None:
        return ExtracaoResultado(metodo="indisponivel", mensagem="O provedor não suporta leitura de imagens.")
    return ExtracaoResultado(metodo="llm-visao", dados=dados)
