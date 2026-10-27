"""Análise assistida: provedor LLM real (Anthropic) ou modo demonstração determinístico."""

from __future__ import annotations

from safecat.ai.base import Analyzer, AnalyzerError
from safecat.ai.demo import DemoAnalyzer
from safecat.config import Settings


def build_analyzer(settings: Settings) -> Analyzer:
    """LLM quando há chave configurada (e o modo demo não foi forçado); senão, demonstração."""
    if settings.llm_enabled and settings.anthropic_api_key is not None:
        from safecat.ai.llm import AnthropicAnalyzer

        return AnthropicAnalyzer(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            max_tokens=settings.llm_max_tokens,
            effort=settings.llm_effort,
            server_fallback=settings.llm_server_fallback,
        )
    return DemoAnalyzer()


__all__ = ["Analyzer", "AnalyzerError", "DemoAnalyzer", "build_analyzer"]
