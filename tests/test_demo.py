from __future__ import annotations

from safecat.ai import DemoAnalyzer, build_analyzer
from safecat.ai.schemas import AVISO_REVISAO, Origem
from safecat.config import Settings


def test_demo_nao_inventa_causas() -> None:
    relato = "Operador prensou a mão na prensa hidráulica durante a troca de ferramenta."
    res = DemoAnalyzer().analisar(relato)
    an = res.analise
    assert res.origem is Origem.DEMONSTRACAO
    assert res.aviso == AVISO_REVISAO
    assert len(an.cinco_porques) == 5
    assert all(p.resposta_sugerida is None and p.evidencia is None for p in an.cinco_porques)
    assert an.hipotese_causa_raiz is None
    assert "Operador prensou a mão" in an.cinco_porques[0].pergunta
    assert an.resumo_fatos == [f"Relato informado: {relato}"]
    # Controles específicos citam o termo do relato que os motivou; nada de empilhadeira/óleo.
    assert any("termo 'maquina'" in c or "termo 'prensa'" in c for c in an.controles.engenharia)
    texto = " ".join(an.controles.engenharia + an.controles.administrativo + an.controles.epi).lower()
    assert "empilhadeira" not in texto
    assert "óleo" not in texto


def test_demo_queda_sem_fatos_inventados() -> None:
    an = DemoAnalyzer().analisar("Funcionária sofreu uma queda no pátio.").analise
    assert any("termo 'queda'" in c for c in an.controles.engenharia)
    assert "Horário do acidente." in an.lacunas
    assert "Local exato do acidente (setor/posto)." not in an.lacunas  # 'pátio' está no relato
    todos = " ".join(p.pergunta for p in an.cinco_porques)
    assert "óleo" not in todos
    assert "empilhadeira" not in todos


def test_demo_relato_generico_e_longo() -> None:
    relato = "Algo aconteceu " * 30
    an = DemoAnalyzer().analisar(relato).analise
    assert an.cinco_porques[0].pergunta.endswith('…"?')
    assert an.controles.engenharia == []
    assert an.controles.eliminacao


def test_demo_nao_le_imagens() -> None:
    d = DemoAnalyzer()
    assert d.ler_atestado(b"x", "image/png") is None
    assert d.estruturar_texto_atestado("x") is None
    assert not d.usa_llm
    assert "demonstração" in d.descricao


def test_build_analyzer_sem_chave_e_demo() -> None:
    assert isinstance(build_analyzer(Settings()), DemoAnalyzer)
    assert isinstance(build_analyzer(Settings(ANTHROPIC_API_KEY="sk-test", force_demo=True)), DemoAnalyzer)
    assert isinstance(build_analyzer(Settings(ANTHROPIC_API_KEY="  ")), DemoAnalyzer)


def test_build_analyzer_com_chave() -> None:
    from safecat.ai.llm import AnthropicAnalyzer

    a = build_analyzer(Settings(ANTHROPIC_API_KEY="sk-test", llm_model="claude-opus-5-5"))
    assert isinstance(a, AnthropicAnalyzer)
    assert a.usa_llm
    assert a.modelo == "claude-opus-5-5"
    assert "claude-opus-5-5" in a.descricao
