"""Contrato comum aos provedores de análise."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from safecat.ai.schemas import AnaliseResultado, DadosAtestado


class AnalyzerError(RuntimeError):
    """Falha recuperável do provedor (rede, limite de uso, recusa, resposta inválida).

    A mensagem é segura para exibir ao usuário e não contém dados do relato.
    """


@runtime_checkable
class Analyzer(Protocol):
    @property
    def descricao(self) -> str:
        """Rótulo exibido na UI e no PDF (ex.: 'Modo demonstração')."""
        ...

    @property
    def usa_llm(self) -> bool: ...

    def analisar(self, relato: str) -> AnaliseResultado:
        """Gera sugestão de 5 Porquês e controles a partir do relato."""
        ...

    def ler_atestado(self, conteudo: bytes, media_type: str) -> DadosAtestado | None:
        """Lê um atestado em imagem/PDF. Retorna ``None`` se o provedor não suporta."""
        ...

    def estruturar_texto_atestado(self, texto: str) -> DadosAtestado | None:
        """Estrutura texto já extraído de um atestado. ``None`` se não suportado."""
        ...
