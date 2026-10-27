from __future__ import annotations

import io

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from safecat.ai import DemoAnalyzer
from safecat.ai.base import AnalyzerError
from safecat.ai.extraction import MAX_BYTES, extrair_atestado, ler_texto_atestado
from safecat.ai.schemas import DadosAtestado

TEXTO = (
    "ATESTADO MÉDICO. Atesto que a Sra. Conceição Gonçalves de Araújo esteve sob meus cuidados em "
    "12/03/2024, necessitando de 10 (dez) dias de afastamento. CID-10: S62.3. "
    "Dr. Fábio Rocha - CRM/SP 123456"
)


def _pdf(linhas: list[str]) -> bytes:
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=A4)
    y = 800
    for linha in linhas:
        c.drawString(40, y, linha)
        y -= 16
    if not linhas:
        c.rect(50, 50, 200, 200, fill=1)
    c.save()
    return buf.getvalue()


def test_regex_le_nome_acentuado_e_campos() -> None:
    d = ler_texto_atestado(TEXTO)
    assert d.nome_paciente == "Conceição Gonçalves de Araújo"
    assert d.cid == "S623"
    assert d.dias_afastamento == 10
    assert d.conselho == "CRM"
    assert d.conselho_numero == "123456"
    assert d.conselho_uf == "SP"
    assert d.data_atendimento == "2024-03-12"


def test_regex_nao_inventa_quando_ausente() -> None:
    d = ler_texto_atestado("Documento sem dados relevantes. Data 31/02/2024 inválida e 01/01/2999 futura.")
    assert d == DadosAtestado(
        nome_paciente=None,
        data_atendimento=None,
        dias_afastamento=None,
        cid=None,
        medico_nome=None,
        conselho=None,
        conselho_numero=None,
        conselho_uf=None,
    )
    d2 = ler_texto_atestado("Paciente: Rui Paz. CRM 999 / XX")
    assert d2.nome_paciente == "Rui Paz"
    assert d2.conselho_uf is None


def test_pdf_com_texto_sem_llm_usa_o_texto_do_arquivo() -> None:
    pdf = _pdf(
        [
            "ATESTADO MEDICO",
            "Atesto que o Sr. Joao Pereira esteve sob cuidados em 05/02/2024",
            "necessitando de 3 dias de repouso. CID S93.4. CRM 54321-RJ",
        ]
    )
    res = extrair_atestado(pdf, "application/pdf", DemoAnalyzer())
    assert res.metodo == "texto-pdf"
    assert res.dados is not None
    assert res.dados.nome_paciente == "Joao Pereira"
    assert res.dados.cid == "S934"
    assert res.dados.conselho_uf == "RJ"
    assert res.dados.dias_afastamento == 3


def test_imagem_sem_llm_informa_e_nao_preenche() -> None:
    res = extrair_atestado(b"\x89PNG\r\n", "image/png", DemoAnalyzer())
    assert res.metodo == "indisponivel"
    assert res.dados is None
    assert res.mensagem is not None
    assert "ANTHROPIC_API_KEY" in res.mensagem


def test_pdf_escaneado_sem_llm() -> None:
    res = extrair_atestado(_pdf([]), "application/pdf", DemoAnalyzer())
    assert res.metodo == "indisponivel"
    assert res.dados is None


def test_arquivo_invalido_grande_ou_tipo_errado() -> None:
    assert extrair_atestado(b"nao e pdf", "application/pdf", DemoAnalyzer()).mensagem == (
        "Não foi possível ler o PDF enviado."
    )
    assert extrair_atestado(b"0" * (MAX_BYTES + 1), "image/png", DemoAnalyzer()).metodo == "indisponivel"
    assert "não suportado" in (extrair_atestado(b"x", "text/plain", DemoAnalyzer()).mensagem or "")


class _FakeLLM:
    """Dublê de Analyzer com LLM (sem rede)."""

    def __init__(self, *, falhar: bool = False, nada: bool = False) -> None:
        self.falhar = falhar
        self.nada = nada
        self.recebido: list[str] = []

    @property
    def descricao(self) -> str:
        return "fake"

    @property
    def usa_llm(self) -> bool:
        return True

    def analisar(self, relato: str) -> object:  # pragma: no cover - não usado aqui
        raise NotImplementedError

    def _dados(self) -> DadosAtestado | None:
        if self.falhar:
            raise AnalyzerError("Falha simulada.")
        if self.nada:
            return None
        return ler_texto_atestado(TEXTO)

    def ler_atestado(self, conteudo: bytes, media_type: str) -> DadosAtestado | None:
        self.recebido.append(media_type)
        return self._dados()

    def estruturar_texto_atestado(self, texto: str) -> DadosAtestado | None:
        self.recebido.append(texto)
        return self._dados()


def test_com_llm_texto_e_visao() -> None:
    fake = _FakeLLM()
    pdf = _pdf(["Atesto que o Sr. Joao Pereira esteve sob cuidados medicos em 05/02/2024."])
    res = extrair_atestado(pdf, "application/pdf", fake)  # type: ignore[arg-type]
    assert res.metodo == "llm-texto"
    assert "Joao Pereira" in fake.recebido[0]  # o texto real do PDF foi enviado
    res2 = extrair_atestado(b"img", "image/jpeg", fake)  # type: ignore[arg-type]
    assert res2.metodo == "llm-visao"
    assert fake.recebido[-1] == "image/jpeg"


def test_com_llm_falhando_cai_para_regex_ou_informa() -> None:
    pdf = _pdf(["Atesto que o Sr. Joao Pereira esteve sob cuidados medicos em 05/02/2024."])
    res = extrair_atestado(pdf, "application/pdf", _FakeLLM(falhar=True))  # type: ignore[arg-type]
    assert res.metodo == "texto-pdf"
    assert res.mensagem is not None
    assert "Falha simulada" in res.mensagem
    res2 = extrair_atestado(b"img", "image/png", _FakeLLM(falhar=True))  # type: ignore[arg-type]
    assert res2.metodo == "indisponivel"
    res3 = extrair_atestado(b"img", "image/png", _FakeLLM(nada=True))  # type: ignore[arg-type]
    assert res3.dados is None
