# IA para CAT - Gerador de Relatório PDF Oficial (ReportLab)

import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_cat_pdf(data):
    """Generates a professional PDF containing the CAT accident report data."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles for High Aesthetics
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        alignment=1, # Center
    )
    
    section_style = ParagraphStyle(
        name='SectionStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0284c7'),
        spaceAfter=6,
        spaceBefore=12,
    )
    
    label_style = ParagraphStyle(
        name='LabelStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#475569'),
    )
    
    value_style = ParagraphStyle(
        name='ValueStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#0f172a'),
    )

    story = []
    
    # Title
    story.append(Paragraph("COMUNICAÇÃO DE ACIDENTE DE TRABALHO (CAT)", title_style))
    story.append(Paragraph("Emitido de forma Automatizada via Inteligência Artificial - eSocial Ready", ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=1, textColor=colors.HexColor('#64748b'), fontSize=9)))
    story.append(Spacer(1, 15))
    
    # Helper to build section tables
    def build_grid(fields):
        table_data = []
        for row in fields:
            row_data = []
            for item in row:
                if len(item) == 2:
                    lbl, val = item
                    p_lbl = Paragraph(lbl, label_style)
                    p_val = Paragraph(str(val) if val else "", value_style)
                    cell_content = [p_lbl, Spacer(1, 2), p_val]
                    row_data.append(cell_content)
                else:
                    row_data.append("")
            table_data.append(row_data)
            
        t = Table(table_data, colWidths=[530 / len(row) for row in fields[0]])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    # 1. Employer Information
    story.append(Paragraph("1. DADOS DO EMPREGADOR", section_style))
    employer_fields = [
        [("Razão Social:", "Indústria de Componentes LinhaMestre Ltda"), ("CNPJ:", "12.345.678/0001-90")],
        [("CNAE Principal:", "2539-0/01 (Serviços de Usinagem e Metalurgia)"), ("Endereço:", "Av. Industrial, 1500 - Distrito Metalúrgico, Sorocaba-SP")]
    ]
    story.append(build_grid(employer_fields))
    story.append(Spacer(1, 10))
    
    # 2. Injured Worker Information
    story.append(Paragraph("2. DADOS DO ACIDENTADO", section_style))
    worker_fields = [
        [("Nome Completo:", data.get("nome", "Carlos Eduardo da Silva")), ("CPF:", data.get("cpf", "123.456.789-00"))],
        [("Nascimento:", data.get("nascimento", "15/08/1994")), ("Cargo / Função:", data.get("cargo", "Operador de Máquinas CNC"))],
        [("PIS / NIT:", data.get("pis", "120.43210.89-1")), ("Departamento:", data.get("setor", "Usinagem/Logística"))]
    ]
    story.append(build_grid(worker_fields))
    story.append(Spacer(1, 10))
    
    # 3. Accident Details
    story.append(Paragraph("3. DETALHES DO ACIDENTE E DA LESÃO", section_style))
    accident_fields = [
        [("Data do Acidente:", data.get("data_acidente", "30/07/2026")), ("Hora do Acidente:", data.get("hora_acidente", "14:20"))],
        [("Tipo de Acidente (eSocial):", data.get("tipo_acidente", "Típico")), ("Gravidade estimada:", data.get("gravidade", "Leve"))],
        [("Código eSocial Parte do Corpo:", data.get("esocial_parte_corpo_codigo", "300000000")), ("Região Afetada:", data.get("esocial_parte_corpo_desc", "Membros Superiores"))],
        [("CID-10 da Lesão:", f"{data.get('cid_codigo', 'S52')} - {data.get('cid_descricao', 'Fratura do antebraço')}") , ("Afastamento:", f"{data.get('dias_afastamento', 15)} dias")]
    ]
    story.append(build_grid(accident_fields))
    story.append(Spacer(1, 10))

    # 4. Medical CRM and Diagnostic Summary
    story.append(Paragraph("4. INFORMAÇÕES MÉDICAS & ANÁLISE DE CAUSA RAIZ (SESMT)", section_style))
    medical_fields = [
        [("Médico Assistente (CRM):", data.get("crm_medico", "54321-SP")), ("Data da Emissão da CAT:", data.get("data_emissao", "31/07/2026"))],
        [("Causa Raiz Identificada pela IA (Causa Primária):", data.get("causa_raiz", "Falha de proteção em máquina")), ("Descrição do Acidente:", data.get("descricao", "Operador sofreu acidente ao realizar atividade na máquina."))]
    ]
    story.append(build_grid(medical_fields))
    story.append(Spacer(1, 20))
    
    # Signatures placeholder
    sig_data = [
        [Paragraph("____________________________________________<br/>Assinatura do Empregador / SESMT", ParagraphStyle(name='Sig1', parent=styles['Normal'], alignment=1)),
         Paragraph("____________________________________________<br/>Assinatura do Médico (Atestado)", ParagraphStyle(name='Sig2', parent=styles['Normal'], alignment=1))]
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sig_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
