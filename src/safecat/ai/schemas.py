"""Estruturas de saída da análise e da extração. Validadas por Pydantic em ambos os provedores."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Origem(StrEnum):
    DEMONSTRACAO = "demonstracao"
    LLM = "llm"


AVISO_REVISAO = "Sugestão automática — revisar. Não substitui a investigação do SESMT."


class Porque(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pergunta: str = Field(description="Pergunta 'Por quê?' deste nível.")
    resposta_sugerida: str | None = Field(
        description="Resposta apoiada no relato, ou null quando o relato não permite responder.",
    )
    evidencia: str | None = Field(
        description="Trecho literal do relato que sustenta a resposta; null se não houver.",
    )


class Controles(BaseModel):
    """Medidas sugeridas pela hierarquia de controles (da mais para a menos eficaz)."""

    model_config = ConfigDict(extra="forbid")

    eliminacao: list[str]
    substituicao: list[str]
    engenharia: list[str]
    administrativo: list[str]
    epi: list[str]


class AnaliseSugerida(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resumo_fatos: list[str] = Field(description="Fatos explicitamente presentes no relato.")
    cinco_porques: list[Porque] = Field(description="Exatamente cinco níveis.")
    hipotese_causa_raiz: str | None = Field(
        description="Hipótese de causa raiz, somente se sustentada pelo relato; senão null.",
    )
    controles: Controles
    lacunas: list[str] = Field(description="Informações que faltam no relato e devem ser apuradas.")


class AnaliseResultado(BaseModel):
    """Análise + metadados de proveniência (guardados junto ao registro)."""

    origem: Origem
    modelo: str | None = None
    aviso: str = AVISO_REVISAO
    analise: AnaliseSugerida


class DadosAtestado(BaseModel):
    """Campos que podem ser lidos de um atestado. Tudo opcional: nada é presumido."""

    model_config = ConfigDict(extra="forbid")

    nome_paciente: str | None = Field(description="Nome do paciente, como escrito.")
    data_atendimento: str | None = Field(description="Data do atendimento/emissão no formato AAAA-MM-DD.")
    dias_afastamento: int | None = Field(description="Dias de afastamento/repouso indicados.")
    cid: str | None = Field(description="Código CID-10, se escrito no documento.")
    medico_nome: str | None = Field(description="Nome do médico/dentista emitente.")
    conselho: str | None = Field(description="CRM, CRO ou RMS, se escrito.")
    conselho_numero: str | None = Field(description="Número do registro no conselho.")
    conselho_uf: str | None = Field(description="UF do conselho (duas letras).")


class ExtracaoResultado(BaseModel):
    metodo: str  # "texto-pdf", "llm-visao", "llm-texto", "indisponivel"
    dados: DadosAtestado | None = None
    mensagem: str | None = None
