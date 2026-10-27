"""Modelos de domínio da CAT, alinhados aos principais campos do evento S-2210 do eSocial.

Referência: leiaute S-1.3, schema oficial ``evtCAT.xsd`` (grupos ``cat``, ``localAcidente``,
``parteAtingida``, ``agenteCausador``, ``atestado`` e ``emitente``). Nomes de campos do leiaute
aparecem entre parênteses nas descrições.

Regras gerais:

* Nada recebe valor padrão inventado. Campo não informado é ``None``.
* Validações que tornariam o registro impossível (CPF inválido, data futura, datas
  incoerentes) lançam erro.
* Campos que o S-2210 exige mas que podem ainda não estar disponíveis no momento do
  registro interno são reportados por :meth:`Cat.pendencias_s2210`, sem bloquear o salvamento.
"""

from __future__ import annotations

import re
from datetime import date, time
from enum import IntEnum, StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from safecat.domain.validators import (
    format_cpf,
    normalize_cid,
    only_digits,
    validate_cid,
    validate_cpf,
    validate_esocial_code,
    validate_pis,
    validate_uf,
)

# Data a partir da qual o leiaute exige hora do acidente também para acidente de trajeto.
TRAJETO_HORA_OBRIGATORIA_DESDE = date(2022, 1, 26)
# Data a partir da qual o agente causador de acidente típico/trajeto deve vir só da Tabela 14.
AGENTE_SOMENTE_TABELA_14_DESDE = date(2024, 1, 22)

_HORAS_RE = re.compile(r"^(\d{1,2}):(\d{2})$")

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TipoCat(IntEnum):
    """``tpCat``."""

    INICIAL = 1
    REABERTURA = 2
    COMUNICACAO_OBITO = 3

    @property
    def rotulo(self) -> str:
        return {1: "Inicial", 2: "Reabertura", 3: "Comunicação de óbito"}[self.value]


class TipoAcidente(IntEnum):
    """``tpAcid``."""

    TIPICO = 1
    DOENCA = 2
    TRAJETO = 3

    @property
    def rotulo(self) -> str:
        return {1: "Típico", 2: "Doença", 3: "Trajeto"}[self.value]


class TipoLocal(IntEnum):
    """``localAcidente/tpLocal``."""

    ESTABELECIMENTO_BRASIL = 1
    ESTABELECIMENTO_EXTERIOR = 2
    ESTABELECIMENTO_TERCEIROS = 3
    VIA_PUBLICA = 4
    AREA_RURAL = 5
    EMBARCACAO = 6
    OUTROS = 9

    @property
    def rotulo(self) -> str:
        return {
            1: "Estabelecimento do empregador no Brasil",
            2: "Estabelecimento do empregador no exterior",
            3: "Estabelecimento de terceiros onde o empregador presta serviços",
            4: "Via pública",
            5: "Área rural",
            6: "Embarcação",
            9: "Outros",
        }[self.value]


class Lateralidade(IntEnum):
    """``parteAtingida/lateralidade``."""

    NAO_APLICAVEL = 0
    ESQUERDA = 1
    DIREITA = 2
    AMBAS = 3

    @property
    def rotulo(self) -> str:
        return {0: "Não aplicável", 1: "Esquerda", 2: "Direita", 3: "Ambas"}[self.value]


class OrgaoClasse(IntEnum):
    """``emitente/ideOC``."""

    CRM = 1
    CRO = 2
    RMS = 3

    @property
    def rotulo(self) -> str:
        return {1: "CRM", 2: "CRO", 3: "RMS"}[self.value]


class Gravidade(StrEnum):
    """Classificação interna do SESMT (não é campo do S-2210)."""

    LEVE = "leve"
    MODERADA = "moderada"
    GRAVE = "grave"
    FATAL = "fatal"

    @property
    def rotulo(self) -> str:
        return self.value.capitalize()


class CodigoTabela(BaseModel):
    """Código de 9 dígitos de uma tabela do eSocial com a descrição usada no registro."""

    model_config = ConfigDict(frozen=True)

    codigo: str
    descricao: Texto

    @field_validator("codigo")
    @classmethod
    def _codigo(cls, value: str) -> str:
        value = value.strip()
        if not validate_esocial_code(value):
            raise ValueError("código do eSocial deve ter 9 dígitos numéricos")
        return value


class Trabalhador(BaseModel):
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=70)]
    cpf: str
    pis_nit: str | None = None
    data_nascimento: date | None = None
    matricula: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None
    cargo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    setor: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, value: str) -> str:
        if not validate_cpf(value):
            raise ValueError("CPF inválido (dígitos verificadores não conferem)")
        return only_digits(value)

    @field_validator("pis_nit")
    @classmethod
    def _pis(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if not validate_pis(value):
            raise ValueError("PIS/NIT inválido (dígito verificador não confere)")
        return only_digits(value)

    @field_validator("matricula", "cargo", "setor", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def cpf_formatado(self) -> str:
        return format_cpf(self.cpf)


class Emitente(BaseModel):
    """Médico/dentista que emitiu o atestado (``emitente``)."""

    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=70)]
    orgao_classe: OrgaoClasse
    numero: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=14)]
    uf: str | None = None

    @field_validator("numero")
    @classmethod
    def _numero(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("número do registro profissional deve conter apenas letras e dígitos")
        return value.upper()

    @field_validator("uf")
    @classmethod
    def _uf(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip().upper()
        if not validate_uf(value):
            raise ValueError("UF inválida")
        return value

    @model_validator(mode="after")
    def _uf_obrigatoria(self) -> Self:
        if self.orgao_classe in (OrgaoClasse.CRM, OrgaoClasse.CRO) and self.uf is None:
            raise ValueError("UF do conselho é obrigatória para CRM/CRO")
        return self

    @property
    def registro(self) -> str:
        sufixo = f"/{self.uf}" if self.uf else ""
        return f"{self.orgao_classe.rotulo} {self.numero}{sufixo}"


class Atestado(BaseModel):
    """Dados do atestado médico (grupo ``atestado`` do S-2210)."""

    data_atendimento: date
    hora_atendimento: time | None = None
    internacao: bool | None = None
    duracao_tratamento_dias: int | None = Field(default=None, ge=0, le=9999)
    afastamento: bool | None = None
    natureza_lesao: CodigoTabela | None = None  # dscLesao (Tabela 17)
    descricao_complementar: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    diagnostico_provavel: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
    cid: str | None = None
    cid_descricao: str | None = None
    observacao: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    emitente: Emitente | None = None

    @field_validator("cid")
    @classmethod
    def _cid(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if not validate_cid(value):
            raise ValueError("CID-10 em formato inválido (ex.: S52 ou S52.5)")
        return normalize_cid(value)

    @field_validator("descricao_complementar", "diagnostico_provavel", "observacao", "cid_descricao", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class LocalAcidente(BaseModel):
    tipo: TipoLocal
    descricao: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
    uf: str | None = None
    municipio: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None

    @field_validator("uf")
    @classmethod
    def _uf(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip().upper()
        if not validate_uf(value):
            raise ValueError("UF inválida")
        return value


class ParteAtingida(BaseModel):
    parte: CodigoTabela  # codParteAting (Tabela 13)
    lateralidade: Lateralidade


class Cat(BaseModel):
    """Registro interno de uma CAT (documento auxiliar ao S-2210)."""

    trabalhador: Trabalhador
    tipo_cat: TipoCat
    tipo_acidente: TipoAcidente
    data_acidente: date
    hora_acidente: time | None = None
    horas_trabalhadas_antes: str | None = None  # HH:MM, até 99:59 (hrsTrabAntesAcid)
    obito: bool = False
    data_obito: date | None = None
    comunicacao_policia: bool | None = None
    ultimo_dia_trabalhado: date | None = None
    houve_afastamento: bool | None = None
    local: LocalAcidente | None = None
    parte_atingida: ParteAtingida | None = None
    agente_causador: CodigoTabela | None = None  # codAgntCausador (Tabela 14; 15 para doença)
    situacao_geradora: CodigoTabela | None = None  # codSitGeradora
    atestado: Atestado | None = None
    relato: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=4000)]
    gravidade: Gravidade | None = None

    @field_validator("horas_trabalhadas_antes")
    @classmethod
    def _horas_antes(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        m = _HORAS_RE.match(value.strip())
        if not m or int(m.group(2)) > 59:
            raise ValueError("horas trabalhadas antes do acidente devem estar no formato HH:MM (até 99:59)")
        return f"{int(m.group(1)):02d}:{m.group(2)}"

    @field_validator("data_acidente")
    @classmethod
    def _data_acidente(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("data do acidente não pode ser futura")
        if value.year < 1900:
            raise ValueError("data do acidente inválida")
        return value

    @model_validator(mode="after")
    def _coerencia(self) -> Self:
        hoje = date.today()
        nasc = self.trabalhador.data_nascimento
        if nasc is not None and nasc >= self.data_acidente:
            raise ValueError("data de nascimento deve ser anterior à data do acidente")
        if self.tipo_acidente is TipoAcidente.DOENCA and self.hora_acidente is not None:
            raise ValueError("hora do acidente não deve ser informada quando o tipo é Doença")
        if self.tipo_cat is TipoCat.COMUNICACAO_OBITO and not self.obito:
            raise ValueError("CAT de comunicação de óbito exige indicação de óbito")
        if self.tipo_cat is TipoCat.REABERTURA and self.obito:
            raise ValueError("CAT de reabertura não pode indicar óbito")
        if self.obito:
            if self.data_obito is None:
                raise ValueError("data do óbito é obrigatória quando houve óbito")
            if self.atestado is not None and self.atestado.afastamento:
                raise ValueError("quando houve óbito, o indicativo de afastamento do atestado deve ser 'não'")
        if self.data_obito is not None:
            if not self.obito:
                raise ValueError("data do óbito informada sem indicação de óbito")
            if not self.data_acidente <= self.data_obito <= hoje:
                raise ValueError("data do óbito deve estar entre a data do acidente e hoje")
        if self.ultimo_dia_trabalhado is not None and self.ultimo_dia_trabalhado > hoje:
            raise ValueError("último dia trabalhado não pode ser futuro")
        if self.atestado is not None:
            atend = self.atestado.data_atendimento
            if not self.data_acidente <= atend <= hoje:
                raise ValueError("data do atendimento deve estar entre a data do acidente e hoje")
        return self

    def pendencias_s2210(self) -> list[str]:
        """Campos exigidos pelo S-2210 que ainda faltam neste registro."""
        faltas: list[str] = []
        exige_hora = self.tipo_acidente is TipoAcidente.TIPICO or (
            self.tipo_acidente is TipoAcidente.TRAJETO and self.data_acidente >= TRAJETO_HORA_OBRIGATORIA_DESDE
        )
        if exige_hora and self.hora_acidente is None:
            faltas.append("Hora do acidente (hrAcid)")
        if exige_hora and self.horas_trabalhadas_antes is None:
            faltas.append("Horas trabalhadas antes do acidente (hrsTrabAntesAcid)")
        if self.comunicacao_policia is None:
            faltas.append("Houve comunicação à autoridade policial? (indComunPolicia)")
        if self.ultimo_dia_trabalhado is None:
            faltas.append("Último dia trabalhado (ultDiaTrab)")
        if self.houve_afastamento is None:
            faltas.append("Houve afastamento? (houveAfast)")
        if self.local is None:
            faltas.append("Local do acidente (localAcidente)")
        if self.parte_atingida is None:
            faltas.append("Parte do corpo atingida - Tabela 13 (codParteAting)")
        if self.agente_causador is None:
            faltas.append("Agente causador (codAgntCausador)")
        if self.situacao_geradora is None:
            faltas.append("Situação geradora (codSitGeradora)")
        if self.atestado is None:
            faltas.append("Atestado médico (atestado)")
        else:
            a = self.atestado
            if a.hora_atendimento is None:
                faltas.append("Hora do atendimento (hrAtendimento)")
            if a.internacao is None:
                faltas.append("Indicativo de internação (indInternacao)")
            if a.duracao_tratamento_dias is None:
                faltas.append("Duração estimada do tratamento (durTrat)")
            if a.afastamento is None:
                faltas.append("Afastamento durante o tratamento (indAfast)")
            if a.natureza_lesao is None:
                faltas.append("Natureza da lesão - Tabela 17 (dscLesao)")
            if a.cid is None:
                faltas.append("CID-10 (codCID)")
            if a.emitente is None:
                faltas.append("Emitente do atestado (emitente)")
        return faltas

    @property
    def dias_perdidos(self) -> int:
        """Dias de afastamento considerados nos indicadores (0 se não houve afastamento)."""
        if self.atestado is None or not self.atestado.afastamento:
            return 0
        return self.atestado.duracao_tratamento_dias or 0
