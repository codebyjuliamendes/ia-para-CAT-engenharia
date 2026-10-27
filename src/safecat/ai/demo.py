"""Analisador determinístico de demonstração (sem chave, sem rede).

Princípio: **não afirmar nada que não esteja no relato**. O modo demonstração:

* reproduz o relato como único fato conhecido;
* monta as perguntas dos 5 Porquês, sem respondê-las;
* aponta lacunas de informação (hora, local, tarefa, equipamento, EPI, testemunhas);
* sugere controles genéricos pela hierarquia de controles, sempre como itens a verificar,
  escolhidos por palavras presentes no relato (e citando a palavra que motivou a sugestão).
"""

from __future__ import annotations

import re

from safecat.ai.schemas import AnaliseResultado, AnaliseSugerida, Controles, Origem, Porque
from safecat.esocial.tables import normalize_text

_MAX_CITACAO = 160


def _primeira_frase(relato: str) -> str:
    texto = " ".join(relato.split())
    partes = re.split(r"(?<=[.!?;])\s", texto, maxsplit=1)
    frase = partes[0].rstrip(".!?;")
    if len(frase) > _MAX_CITACAO:
        frase = frase[: _MAX_CITACAO - 1].rstrip() + "…"
    return frase


# (palavras normalizadas, tema, controles por nível). Todos redigidos como verificação.
_TEMAS: list[tuple[tuple[str, ...], str, dict[str, list[str]]]] = [
    (
        ("maquina", "prensa", "torno", "serra", "fresa", "esteira", "engrenagem", "equipamento"),
        "máquinas e equipamentos",
        {
            "engenharia": [
                "Verificar proteções fixas/móveis e dispositivos de intertravamento da máquina envolvida (NR-12).",
                "Verificar se há parada de emergência acessível e funcional.",
            ],
            "administrativo": [
                "Verificar se existe procedimento de bloqueio e etiquetagem (LOTO) para intervenções.",
                "Verificar capacitação do operador para a máquina envolvida (NR-12).",
            ],
        },
    ),
    (
        ("queda", "caiu", "escorreg", "tropec", "piso", "escada", "altura", "andaime"),
        "quedas e superfícies",
        {
            "eliminacao": ["Avaliar se a tarefa pode ser executada sem exposição ao desnível/ao trecho envolvido."],
            "engenharia": [
                "Verificar condições do piso, drenagem, iluminação e guarda-corpos no local.",
                "Se trabalho em altura, verificar sistemas de proteção coletiva (NR-35).",
            ],
            "administrativo": ["Verificar rotina de inspeção, limpeza e sinalização do local."],
        },
    ),
    (
        ("empilhadeira", "veiculo", "caminhao", "transpalete", "carro", "moto", "onibus", "atropel"),
        "veículos e movimentação",
        {
            "engenharia": ["Verificar segregação entre rotas de pedestres e de veículos."],
            "administrativo": [
                "Verificar habilitação/treinamento do condutor e plano de circulação interna.",
            ],
        },
    ),
    (
        ("carga", "peso", "levant", "carreg", "esforco", "repetit", "postura"),
        "ergonomia e movimentação manual",
        {
            "engenharia": ["Avaliar meios mecânicos de auxílio à movimentação de cargas."],
            "administrativo": ["Verificar a análise ergonômica do posto de trabalho (NR-17)."],
        },
    ),
    (
        ("quimic", "produto", "solvente", "acido", "vapor", "gas", "queimad", "calor", "quente", "eletric", "choque"),
        "energias perigosas e agentes químicos/térmicos",
        {
            "substituicao": ["Avaliar substituição do produto/processo por alternativa menos perigosa."],
            "engenharia": ["Verificar enclausuramento, ventilação local exaustora ou isolamento da fonte."],
            "administrativo": ["Verificar FDS/FISPQ disponível e capacitação para o risco envolvido."],
        },
    ),
    (
        ("faca", "estilete", "corte", "cortou", "lamina", "ferramenta"),
        "ferramentas e objetos cortantes",
        {
            "substituicao": ["Avaliar ferramenta com lâmina retrátil ou de menor risco."],
            "administrativo": ["Verificar estado de conservação das ferramentas e procedimento de uso."],
        },
    ),
]

_CONTROLES_GERAIS = {
    "eliminacao": ["Avaliar, com a equipe, se o perigo envolvido pode ser eliminado da tarefa."],
    "substituicao": [],
    "engenharia": [],
    "administrativo": [
        "Revisar a análise de risco (APR/PGR) da tarefa relatada à luz desta ocorrência.",
        "Comunicar a ocorrência e as lições aprendidas às equipes expostas ao mesmo perigo.",
    ],
    "epi": [
        "Verificar se os EPIs indicados para a tarefa constam no PGR, têm CA válido e estavam em uso "
        "(EPI é a última barreira, não substitui as medidas anteriores).",
    ],
}

_LACUNAS: list[tuple[tuple[str, ...], str]] = [
    ((r"\b\d{1,2}[:h]\d{0,2}\b", r"\bmanha\b", r"\btarde\b", r"\bnoite\b", r"\bhoras?\b"), "Horário do acidente."),
    (
        (r"\bsetor\b", r"\blinha\b", r"\bgalpao\b", r"\barea\b", r"\bpatio\b", r"\bposto\b", r"\bdeposito\b"),
        "Local exato do acidente (setor/posto).",
    ),
    ((r"\bepi\b", r"\bluva", r"\bcapacete\b", r"\boculos\b", r"\bbota", r"\bcalcado"), "EPIs em uso no momento."),
    ((r"\btestemunh", r"\bcolega", r"\bsupervisor"), "Testemunhas e quem prestou o primeiro atendimento."),
    (
        (r"\btarefa\b", r"\batividade\b", r"\boperando\b", r"\bexecutando\b", r"\bfazendo\b"),
        "Tarefa que era executada.",
    ),
    ((r"\btreinad", r"\bcapacitad", r"\bprocedimento\b"), "Treinamento e procedimento aplicáveis à tarefa."),
]


class DemoAnalyzer:
    """Implementação de :class:`~safecat.ai.base.Analyzer` sem LLM."""

    @property
    def descricao(self) -> str:
        return "Modo demonstração (sem IA): sugestão automática — revisar"

    @property
    def usa_llm(self) -> bool:
        return False

    def analisar(self, relato: str) -> AnaliseResultado:
        norm = normalize_text(relato)
        frase = _primeira_frase(relato)

        porques = [
            Porque(pergunta=f'Por que ocorreu: "{frase}"?', resposta_sugerida=None, evidencia=None),
            Porque(
                pergunta="Por que a condição ou ação identificada na resposta anterior existia no momento?",
                resposta_sugerida=None,
                evidencia=None,
            ),
            Porque(
                pergunta=(
                    "Por que essa condição não foi detectada ou corrigida antes (inspeção, manutenção, supervisão)?"
                ),
                resposta_sugerida=None,
                evidencia=None,
            ),
            Porque(
                pergunta="Por que as barreiras previstas (procedimento, proteção, treinamento) não impediram o evento?",
                resposta_sugerida=None,
                evidencia=None,
            ),
            Porque(
                pergunta="Por que o sistema de gestão (planejamento, recursos, análise de risco) permitiu essa falha?",
                resposta_sugerida=None,
                evidencia=None,
            ),
        ]

        niveis: dict[str, list[str]] = {k: list(v) for k, v in _CONTROLES_GERAIS.items()}
        for palavras, tema, controles in _TEMAS:
            achadas = sorted({p for p in palavras if p in norm})
            if not achadas:
                continue
            motivo = f" [sugerido pelo termo '{achadas[0]}' no relato; tema: {tema}]"
            for nivel, itens in controles.items():
                niveis[nivel].extend(item + motivo for item in itens)

        lacunas = [texto for padroes, texto in _LACUNAS if not any(re.search(p, norm) for p in padroes)]
        lacunas.append("Respostas para cada nível dos 5 Porquês, apuradas com os envolvidos.")

        analise = AnaliseSugerida(
            resumo_fatos=[f"Relato informado: {' '.join(relato.split())}"],
            cinco_porques=porques,
            hipotese_causa_raiz=None,
            controles=Controles(**niveis),
            lacunas=lacunas,
        )
        return AnaliseResultado(origem=Origem.DEMONSTRACAO, modelo=None, analise=analise)

    def ler_atestado(self, conteudo: bytes, media_type: str) -> None:
        return None

    def estruturar_texto_atestado(self, texto: str) -> None:
        return None
