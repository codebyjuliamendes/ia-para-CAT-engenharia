"""Documento auxiliar da CAT em PDF (ReportLab).

Imprime somente dados fornecidos e validados; ausentes aparecem como "não informado".
Todas as páginas levam marca d'água e rodapé lembrando que a CAT oficial é o evento
S-2210 transmitido ao eSocial.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import date, datetime, time
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from safecat.ai.schemas import AVISO_REVISAO, AnaliseResultado, Origem
from safecat.config import EmployerSettings
from safecat.domain.models import Cat, CodigoTabela

NAO_INFORMADO = "não informado"
RODAPE = "Documento auxiliar — a CAT oficial é transmitida pelo eSocial (S-2210)."
MARCA_DAGUA = "DOCUMENTO AUXILIAR"

_styles = getSampleStyleSheet()
_TITULO = ParagraphStyle("titulo", parent=_styles["Heading1"], fontSize=15, leading=19, alignment=1)
_SUB = ParagraphStyle("sub", parent=_styles["Normal"], fontSize=8.5, alignment=1, textColor=colors.HexColor("#475569"))
_SECAO = ParagraphStyle(
    "secao",
    parent=_styles["Heading2"],
    fontSize=11,
    leading=14,
    spaceBefore=8,
    spaceAfter=4,
    textColor=colors.HexColor("#0c4a6e"),
)
_ROTULO = ParagraphStyle(
    "rotulo", parent=_styles["Normal"], fontSize=7.5, leading=9, textColor=colors.HexColor("#475569")
)
_VALOR = ParagraphStyle("valor", parent=_styles["Normal"], fontSize=9, leading=11.5)
_TEXTO = ParagraphStyle("texto", parent=_styles["Normal"], fontSize=9, leading=12)
_ALERTA = ParagraphStyle(
    "alerta",
    parent=_TEXTO,
    backColor=colors.HexColor("#fef3c7"),
    borderPadding=4,
    textColor=colors.HexColor("#78350f"),
)

_ASSINATURA = ParagraphStyle("assinatura", parent=_TEXTO, alignment=1)

_LARGURA = A4[0] - 30 * mm


def _txt(value: object) -> str:
    if value is None or value == "":
        return NAO_INFORMADO
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, CodigoTabela):
        return f"{value.codigo} - {value.descricao}"
    return str(value)


def _p(text: str, style: ParagraphStyle = _TEXTO) -> Paragraph:
    return Paragraph(escape(text), style)


def _grade(campos: Sequence[tuple[str, object]], colunas: int = 2) -> Table:
    celulas: list[object] = [[_p(rotulo, _ROTULO), _p(_txt(valor), _VALOR)] for rotulo, valor in campos]
    linhas: list[list[object]] = [celulas[i : i + colunas] for i in range(0, len(celulas), colunas)]
    if linhas and len(linhas[-1]) < colunas:
        linhas[-1] += [""] * (colunas - len(linhas[-1]))
    t = Table(linhas, colWidths=[_LARGURA / colunas] * colunas)
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _decorar(canvas: Canvas, doc: SimpleDocTemplate) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.Color(0.6, 0.6, 0.6, alpha=0.12))
    canvas.setFont("Helvetica-Bold", 52)
    canvas.translate(A4[0] / 2, A4[1] / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, MARCA_DAGUA)
    canvas.restoreState()
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#334155"))
    canvas.drawString(15 * mm, 10 * mm, RODAPE)
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf_cat(
    cat: Cat,
    empregador: EmployerSettings,
    *,
    analise: AnaliseResultado | None = None,
    analise_revisada: bool = False,
    registro_id: int | None = None,
    gerado_em: datetime | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Documento auxiliar de CAT",
        author="SafeCAT AI",
    )
    t = cat.trabalhador
    story: list[Flowable] = [
        _p("Comunicação de Acidente de Trabalho — documento auxiliar", _TITULO),
        _p(
            f"Registro interno nº {registro_id if registro_id is not None else 'não salvo'} · "
            f"gerado em {_txt(gerado_em or datetime.now())} · {RODAPE}",
            _SUB,
        ),
        Spacer(1, 6),
        _p("1. Empregador", _SECAO),
        _grade(
            [
                ("Razão social", empregador.razao_social),
                ("CNPJ", empregador.cnpj),
                ("CNAE", empregador.cnae),
                ("Endereço", empregador.endereco),
            ]
        ),
        _p("2. Acidentado", _SECAO),
        _grade(
            [
                ("Nome", t.nome),
                ("CPF", t.cpf_formatado),
                ("PIS/NIT", t.pis_nit),
                ("Data de nascimento", t.data_nascimento),
                ("Matrícula", t.matricula),
                ("Cargo/função", t.cargo),
                ("Setor", t.setor),
            ]
        ),
        _p("3. Acidente", _SECAO),
        _grade(
            [
                ("Tipo de CAT (tpCat)", cat.tipo_cat.rotulo),
                ("Tipo de acidente (tpAcid)", cat.tipo_acidente.rotulo),
                ("Data do acidente", cat.data_acidente),
                ("Hora do acidente", cat.hora_acidente),
                ("Horas trabalhadas antes", cat.horas_trabalhadas_antes),
                ("Último dia trabalhado", cat.ultimo_dia_trabalhado),
                ("Houve afastamento?", cat.houve_afastamento),
                ("Houve óbito?", cat.obito),
                ("Data do óbito", cat.data_obito if cat.obito else None),
                ("Comunicação à autoridade policial", cat.comunicacao_policia),
                ("Tipo de local", cat.local.tipo.rotulo if cat.local else None),
                ("Local (especificação)", cat.local.descricao if cat.local else None),
                (
                    "Município/UF",
                    " / ".join(x for x in (cat.local.municipio, cat.local.uf) if x) if cat.local else None,
                ),
                ("Gravidade (classificação interna)", cat.gravidade.rotulo if cat.gravidade else None),
                ("Parte atingida (Tabela 13)", cat.parte_atingida.parte if cat.parte_atingida else None),
                ("Lateralidade", cat.parte_atingida.lateralidade.rotulo if cat.parte_atingida else None),
                ("Agente causador", cat.agente_causador),
                ("Situação geradora", cat.situacao_geradora),
            ]
        ),
    ]

    a = cat.atestado
    story += [
        _p("4. Atestado médico", _SECAO),
        _grade(
            [
                ("Data do atendimento", a.data_atendimento if a else None),
                ("Hora do atendimento", a.hora_atendimento if a else None),
                ("Internação", a.internacao if a else None),
                ("Duração estimada do tratamento (dias)", a.duracao_tratamento_dias if a else None),
                ("Afastamento durante o tratamento", a.afastamento if a else None),
                ("Natureza da lesão (Tabela 17)", a.natureza_lesao if a else None),
                (
                    "CID-10",
                    f"{a.cid} - {a.cid_descricao}" if a and a.cid and a.cid_descricao else (a.cid if a else None),
                ),
                ("Diagnóstico provável", a.diagnostico_provavel if a else None),
                ("Descrição complementar da lesão", a.descricao_complementar if a else None),
                ("Emitente", f"{a.emitente.nome} ({a.emitente.registro})" if a and a.emitente else None),
                ("Observação", a.observacao if a else None),
            ]
        ),
        _p("5. Relato da ocorrência", _SECAO),
        _p(cat.relato),
    ]

    if analise is not None:
        origem = "modo demonstração (sem IA)" if analise.origem is Origem.DEMONSTRACAO else f"IA ({analise.modelo})"
        status = "revisada pelo SESMT" if analise_revisada else "NÃO revisada"
        story += [
            _p("6. Análise de causa raiz — sugestão automática", _SECAO),
            _p(f"{AVISO_REVISAO} Origem: {origem}. Situação: {status}.", _ALERTA),
            Spacer(1, 4),
        ]
        an = analise.analise
        for i, pq in enumerate(an.cinco_porques, start=1):
            resp = pq.resposta_sugerida or "(a investigar)"
            story.append(_p(f"{i}º Por quê: {pq.pergunta} — {resp}"))
        story.append(_p(f"Hipótese de causa raiz: {an.hipotese_causa_raiz or '(a definir pelo SESMT)'}"))
        niveis = (
            ("Eliminação", an.controles.eliminacao),
            ("Substituição", an.controles.substituicao),
            ("Engenharia", an.controles.engenharia),
            ("Administrativo", an.controles.administrativo),
            ("EPI", an.controles.epi),
        )
        for nome, itens in niveis:
            for item in itens:
                story.append(_p(f"• [{nome}] {item}"))
        for lacuna in an.lacunas:
            story.append(_p(f"• Apurar: {lacuna}"))

    pend = cat.pendencias_s2210()
    story.append(_p("7. Pendências para o S-2210", _SECAO))
    if pend:
        story += [_p(f"• {p}") for p in pend]
    else:
        story.append(_p("Nenhuma pendência identificada nos campos controlados por este sistema."))

    story += [Spacer(1, 22)]
    assinaturas = Table(
        [
            [
                Paragraph("_______________________________<br/>Responsável SESMT / empregador", _ASSINATURA),
                Paragraph("_______________________________<br/>Acidentado ou representante", _ASSINATURA),
            ]
        ],
        colWidths=[_LARGURA / 2] * 2,
    )
    assinaturas.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(assinaturas)

    doc.build(story, onFirstPage=_decorar, onLaterPages=_decorar)
    return buffer.getvalue()
