"""Validações de identificadores brasileiros e códigos usados na CAT.

Todas as funções são puras e não dependem de rede.
"""

from __future__ import annotations

import re

UFS: frozenset[str] = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()  # noqa: SIM905
)

_CID_RE = re.compile(r"^[A-Z]\d{2}\d?$")
_ESOCIAL_CODE_RE = re.compile(r"^\d{9}$")
_CPF_IN_TEXT_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


_SEPARADORES_OK = re.compile(r"^[\d.\-/\s]*$")


def only_digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _digitos_estritos(value: str) -> str | None:
    """Dígitos do valor, ou ``None`` se houver caracteres além de dígitos e separadores."""
    return only_digits(value) if _SEPARADORES_OK.match(value) else None


def validate_cpf(value: str) -> bool:
    """Valida CPF pelos dígitos verificadores (módulo 11)."""
    digits = _digitos_estritos(value)
    if digits is None or len(digits) != 11 or digits == digits[0] * 11:
        return False
    nums = [int(d) for d in digits]
    for size in (9, 10):
        total = sum(n * w for n, w in zip(nums[:size], range(size + 1, 1, -1), strict=True))
        dv = (total * 10) % 11 % 10
        if dv != nums[size]:
            return False
    return True


def validate_pis(value: str) -> bool:
    """Valida PIS/PASEP/NIT (11 dígitos, pesos 3,2,9,8,7,6,5,4,3,2)."""
    digits = _digitos_estritos(value)
    if digits is None or len(digits) != 11 or digits == digits[0] * 11:
        return False
    weights = (3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    total = sum(int(d) * w for d, w in zip(digits[:10], weights, strict=True))
    dv = 11 - (total % 11)
    if dv >= 10:
        dv = 0
    return dv == int(digits[10])


def validate_cnpj(value: str) -> bool:
    """Valida CNPJ numérico ou alfanumérico (12 posições alfanuméricas + 2 DVs numéricos)."""
    raw = re.sub(r"[^0-9A-Za-z]", "", value).upper()
    if len(raw) != 14 or not raw[12:].isdigit() or not raw[:12].isalnum():
        return False
    if raw == raw[0] * 14:
        return False
    values = [ord(c) - 48 for c in raw]
    for size in (12, 13):
        weights = list(range(size - 7, 1, -1)) + list(range(9, 1, -1))
        total = sum(v * w for v, w in zip(values[:size], weights, strict=True))
        rest = total % 11
        dv = 0 if rest < 2 else 11 - rest
        if dv != values[size]:
            return False
    return True


def normalize_cid(value: str) -> str:
    """Normaliza CID-10 para o formato do eSocial (sem ponto, maiúsculo): ``s52.5`` -> ``S525``."""
    return re.sub(r"[\s.\-]", "", value).upper()


def validate_cid(value: str) -> bool:
    """Formato CID-10 aceito pelo eSocial: letra + 2 dígitos + subcategoria opcional (3-4 posições)."""
    return bool(_CID_RE.match(normalize_cid(value)))


def validate_uf(value: str) -> bool:
    return value.upper() in UFS


def validate_esocial_code(value: str) -> bool:
    """Códigos das Tabelas 13/14/15/16/17 do eSocial são numéricos de 9 dígitos."""
    return bool(_ESOCIAL_CODE_RE.match(value))


def format_cpf(value: str) -> str:
    d = only_digits(value)
    if len(d) != 11:
        return value
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def mask_cpf(value: str | None) -> str:
    """Máscara para exibição/log, no padrão adotado pelo governo: ``***.456.789-**``."""
    if not value:
        return ""
    d = only_digits(value)
    if len(d) != 11:
        return "***"
    return f"***.{d[3:6]}.{d[6:9]}-**"


def redact_cpfs(text: str) -> str:
    """Substitui qualquer CPF presente num texto pela versão mascarada."""
    return _CPF_IN_TEXT_RE.sub(lambda m: mask_cpf(m.group(0)), text)
