"""Configuração de logs com mascaramento de CPF.

Política: o código nunca envia relato, CID ou dados do atestado para o log. Este filtro é
uma defesa adicional que mascara qualquer CPF que apareça numa mensagem.
"""

from __future__ import annotations

import logging

from safecat.domain.validators import redact_cpfs


class CpfRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = redact_cpfs(message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger("safecat")
    if any(isinstance(f, CpfRedactingFilter) for h in root.handlers for f in h.filters):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(CpfRedactingFilter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    root.propagate = False
