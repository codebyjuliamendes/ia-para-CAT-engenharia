"""Tradução de erros de validação Pydantic para mensagens legíveis."""

from __future__ import annotations

from pydantic import ValidationError

ROTULOS: dict[str, str] = {
    "trabalhador": "Acidentado",
    "nome": "Nome",
    "cpf": "CPF",
    "pis_nit": "PIS/NIT",
    "data_nascimento": "Data de nascimento",
    "tipo_cat": "Tipo de CAT",
    "tipo_acidente": "Tipo de acidente",
    "data_acidente": "Data do acidente",
    "hora_acidente": "Hora do acidente",
    "horas_trabalhadas_antes": "Horas trabalhadas antes do acidente",
    "data_obito": "Data do óbito",
    "local": "Local do acidente",
    "tipo": "Tipo",
    "uf": "UF",
    "parte_atingida": "Parte atingida",
    "parte": "Parte do corpo",
    "agente_causador": "Agente causador",
    "situacao_geradora": "Situação geradora",
    "natureza_lesao": "Natureza da lesão",
    "codigo": "Código",
    "descricao": "Descrição",
    "atestado": "Atestado",
    "data_atendimento": "Data do atendimento",
    "duracao_tratamento_dias": "Duração do tratamento",
    "cid": "CID-10",
    "emitente": "Emitente",
    "numero": "Número do registro",
    "relato": "Relato",
    "lateralidade": "Lateralidade",
    "orgao_classe": "Conselho",
}

_MSGS = {
    "missing": "campo obrigatório",
    "string_too_short": "muito curto",
    "string_too_long": "muito longo",
    "less_than_equal": "valor acima do permitido",
    "greater_than_equal": "valor abaixo do permitido",
    "enum": "selecione uma opção válida",
    "int_parsing": "número inválido",
    "int_type": "número inválido",
    "date_parsing": "data inválida",
    "date_from_datetime_parsing": "data inválida",
    "date_type": "data inválida",
    "time_parsing": "hora inválida",
    "time_type": "hora inválida",
    "bool_type": "valor inválido",
}


def mensagens(exc: ValidationError) -> list[str]:
    out: list[str] = []
    for err in exc.errors():
        partes = [ROTULOS.get(str(p), str(p)) for p in err["loc"] if not isinstance(p, int)]
        msg = _MSGS.get(err["type"], err["msg"])
        msg = msg.removeprefix("Value error, ")
        campo = " › ".join(partes) if partes else "Registro"
        out.append(f"{campo}: {msg}")
    return out
