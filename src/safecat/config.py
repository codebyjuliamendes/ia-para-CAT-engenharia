"""Configuração da aplicação via variáveis de ambiente (prefixo ``SAFECAT_``).

A chave da Anthropic é lida de ``ANTHROPIC_API_KEY`` (nome padrão do SDK) e mantida
como :class:`~pydantic.SecretStr` para nunca aparecer em logs ou ``repr``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from safecat.domain.validators import only_digits, validate_cnpj


class EmployerSettings(BaseSettings):
    """Dados do empregador impressos no documento auxiliar.

    Nada é preenchido por padrão: se não configurado, o PDF mostra "não informado".
    """

    model_config = SettingsConfigDict(env_prefix="SAFECAT_EMPREGADOR_", env_file=".env", extra="ignore")

    razao_social: str | None = None
    cnpj: str | None = None
    cnae: str | None = None
    endereco: str | None = None

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        digits = only_digits(value)
        if not validate_cnpj(digits):
            raise ValueError("SAFECAT_EMPREGADOR_CNPJ inválido (dígitos verificadores não conferem)")
        return digits


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAFECAT_", env_file=".env", extra="ignore")

    database_url: str = Field(
        default="sqlite:///./safecat.db",
        description="URL SQLAlchemy. Ex.: sqlite:////data/safecat.db ou postgresql+psycopg://...",
    )
    tables_dir: Path | None = Field(
        default=None,
        description="Diretório com tabelas eSocial importadas (sobrepõe as empacotadas).",
    )
    retention_days: int = Field(
        default=0,
        ge=0,
        description="Retenção (dias) usada por `safecat purge`. 0 = sem expurgo automático.",
    )
    log_level: str = "INFO"

    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "SAFECAT_ANTHROPIC_API_KEY"),
    )
    llm_model: str = "claude-opus-5-5"
    llm_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_max_tokens: int = Field(default=8000, ge=512, le=32000)
    llm_effort: str = Field(default="medium", pattern="^(low|medium|high|xhigh|max)$")
    llm_server_fallback: bool = Field(
        default=True,
        description="Usa o fallback no servidor da Anthropic quando o modelo recusar a solicitação.",
    )
    force_demo: bool = Field(default=False, description="Força o modo demonstração mesmo com chave.")

    @field_validator("anthropic_api_key")
    @classmethod
    def _empty_key_is_none(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().strip():
            return None
        return value

    @property
    def llm_enabled(self) -> bool:
        return self.anthropic_api_key is not None and not self.force_demo


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_employer() -> EmployerSettings:
    return EmployerSettings()
