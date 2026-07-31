# IA para CAT - Engine de Inteligência Artificial (Simulada para Hackathon)

import re

# Dicionário de CIDs comuns em acidentes de trabalho
CID_10_DATABASE = {
    "S52": "Fratura do antebraço",
    "S62": "Fratura ao nível do punho e da mão",
    "S93": "Entorse e distensão das articulações e dos ligamentos ao nível do tornozelo e do pé",
    "T20": "Queimadura da cabeça e do pescoço",
    "S09": "Outros traumatismos e os não especificados da cabeça",
    "M75": "Lesões do ombro (L.E.R. / D.O.R.T.)",
    "S53": "Luxação, entorse e distensão das articulações e dos ligamentos do cotovelo",
    "T14": "Traumatismo de região não especificada do corpo",
}

# Dicionário eSocial Tabela 24 (Codificação de Acidentes - Parte de Corpo)
ESOCIAL_TABLE_24 = {
    "100000000": "Cabeça (crânio, face, olhos, ouvidos)",
    "300000000": "Membros Superiores (ombro, braço, cotovelo, punho, mão, dedos)",
    "400000000": "Membros Inferiores (quadril, coxa, joelho, perna, tornozelo, pé, dedos)",
    "200000000": "Tronco (dorso, coluna, tórax, abdômen)",
    "500000000": "Regiões Múltiplas",
}

def search_cid(query):
    """Busca aproximada de CID-10 na base de dados."""
    query = query.upper()
    results = {}
    for code, desc in CID_10_DATABASE.items():
        if query in code or query in desc.upper():
            results[code] = desc
    return results if results else {"T14": "Traumatismo de região não especificada"}

def process_certificate_ocr(raw_text):
    """Simula o processamento OCR de um atestado médico por LLM."""
    raw_text_lower = raw_text.lower()
    
    # Extração simples via regex para a demo de hackathon
    crm_match = re.search(r'crm\s*[:\-]?\s*(\d+)', raw_text_lower)
    crm = crm_match.group(1) if crm_match else "54321-SP"
    
    cid_match = re.search(r'cid\s*[:\-]?\s*([a-z]\d{2})', raw_text_lower)
    cid = cid_match.group(1).upper() if cid_match else "S52"
    
    name_match = re.search(r'atesto que o sr\(a\)\.?\s*([a-zA-Z\s]+)\s*(?:esteve|necessita)', raw_text_lower)
    patient_name = name_match.group(1).strip().title() if name_match else "Carlos Eduardo da Silva"
    
    days_match = re.search(r'(\d+)\s*(?:dias|dia)', raw_text_lower)
    days_off = int(days_match.group(1)) if days_match else 15
    
    cid_desc = CID_10_DATABASE.get(cid, "Traumatismo / Fratura Indeterminada")
    
    return {
        "paciente": patient_name,
        "crm_medico": crm,
        "cid_codigo": cid,
        "cid_descricao": cid_desc,
        "dias_afastamento": days_off,
        "data_atestado": "2026-07-30"
    }

def analyze_accident_narrative(narrative):
    """
    Simula uma análise avançada LLM sobre a narrativa do acidente:
    - Classificação de Tipo e Gravidade
    - Investigação 5 Porquês (Root Cause)
    - Recomendações Preventivas (Hierarquia de Controles)
    - Enquadramento eSocial
    """
    narrative_lower = narrative.lower()
    
    # Classificação Básica
    tipo = "Típico"
    if "trajeto" in narrative_lower or "voltando para casa" in narrative_lower or "a caminho" in narrative_lower:
        tipo = "Trajeto"
    elif "lesão por esforço" in narrative_lower or "ler" in narrative_lower or "repetitivo" in narrative_lower:
        tipo = "Doença Ocupacional"

    gravidade = "Leve"
    if any(word in narrative_lower for word in ["fratura", "queimadura", "sangramento", "ambulância", "hospital"]):
        gravidade = "Moderada"
    if any(word in narrative_lower for word in ["amputação", "óbito", "perda de consciência", "cirurgia urgente"]):
        gravidade = "Grave"

    # Mapeamento de Parte do Corpo e eSocial
    part_code = "500000000"
    part_desc = "Regiões Múltiplas"
    
    if any(word in narrative_lower for word in ["cabeça", "olho", "rosto", "face", "crânio"]):
        part_code = "100000000"
        part_desc = "Cabeça"
    elif any(word in narrative_lower for word in ["braço", "mão", "dedo", "punho", "ombro", "cotovelo"]):
        part_code = "300000000"
        part_desc = "Membros Superiores"
    elif any(word in narrative_lower for word in ["perna", "pé", "joelho", "tornozelo", "coxa"]):
        part_code = "400000000"
        part_desc = "Membros Inferiores"
    elif any(word in narrative_lower for word in ["costas", "coluna", "tórax", "abdômen", "tronco"]):
        part_code = "200000000"
        part_desc = "Tronco"

    # Geração dos 5 Porquês baseados em palavras-chave para a Demo do Hackathon parecer incrivelmente inteligente
    if "queda" in narrative_lower or "escorregou" in narrative_lower:
        whys = [
            "O funcionário escorregou no piso molhado do corredor de expedição.",
            "Havia óleo hidráulico vazando de uma empilhadeira estacionada nas proximidades.",
            "A junta de vedação do pistão da empilhadeira falhou devido a desgaste excessivo.",
            "O plano de manutenção preventiva da empilhadeira estava atrasado em 3 semanas.",
            "Falta de pessoal técnico dedicado à manutenção programada no setor de logística."
        ]
        root_cause = "Falha organizacional na manutenção preventiva de maquinários críticos por subdimensionamento da equipe técnica."
        actions = {
            "Eliminação/Engenharia": "Instalar bandejas de contenção de óleo sob empilhadeiras e revisar juntas de vedação.",
            "Administrativo": "Sinalizar o piso molhado imediatamente e reestruturar o cronograma de manutenção preventiva no software ERP.",
            "EPI": "Adotar calçados de segurança com solado antiderrapante de alta aderência (Classe SRC)."
        }
    elif "máquina" in narrative_lower or "prensa" in narrative_lower or "corte" in narrative_lower:
        whys = [
            "O operador sofreu um corte no dedo indicador direito ao operar a fresadora.",
            "A barreira protetora acrílica da máquina estava levantada/desativada no momento da atividade.",
            "A barreira foi burlada pelo próprio operador para agilizar o posicionamento das peças.",
            "A máquina permite o acionamento mecânico mesmo com o sensor de barreira aberto (falha no intertravamento).",
            "A fresadora não passou pela adequação de segurança exigida pela norma regulamentadora NR-12."
        ]
        root_cause = "Equipamento produtivo operando em desconformidade com a NR-12 (ausência de sistema de intertravamento duplo canal seguro)."
        actions = {
            "Eliminação/Engenharia": "Instalar chaves de segurança codificadas e relé de segurança de categoria 4 para impedir o funcionamento com a barreira aberta.",
            "Administrativo": "Realizar treinamento de conscientização sobre riscos de bypass de segurança e criar LOTO (Lockout/Tagout).",
            "EPI": "Exigir uso de luva de proteção resistente a corte (Fator de proteção mecânica D ou F)."
        }
    else:
        whys = [
            f"O trabalhador sofreu um incidente relatado como: '{narrative}'.",
            "Houve exposição direta a um perigo não neutralizado na área operacional.",
            "Falta de análise preliminar de risco (APR) para a tarefa não rotineira.",
            "A equipe de SESMT não foi notificada sobre a mudança de layout na linha de montagem.",
            "Ausência de processo formal de gerenciamento de mudanças operacionais."
        ]
        root_cause = "Falha no processo de Gerenciamento de Mudanças Operacionais e ausência de APR."
        actions = {
            "Eliminação/Engenharia": "Isolar a zona de risco onde o acidente ocorreu até a elaboração de novos EPCs.",
            "Administrativo": "Elaborar nova APR (Análise Preliminar de Risco) e treinar a equipe no novo procedimento operacional padrão.",
            "EPI": "Garantir o uso obrigatório de óculos de proteção e calçados com biqueira de aço na área."
        }

    return {
        "tipo_acidente": tipo,
        "gravidade": gravidade,
        "esocial_parte_corpo_codigo": part_code,
        "esocial_parte_corpo_desc": part_desc,
        "cinco_porques": whys,
        "causa_raiz": root_cause,
        "recomendacoes": actions
    }
