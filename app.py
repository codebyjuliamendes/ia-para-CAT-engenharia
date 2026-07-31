# IA para CAT Engenharia - Painel Principal do Sistema

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from PIL import Image

# Importar utilitários locais
from utils.ai_engine import process_certificate_ocr, analyze_accident_narrative, search_cid, CID_10_DATABASE
from utils.pdf_generator import generate_cat_pdf

# Configuração da Página do Streamlit
st.set_page_config(
    page_title="SafeCAT AI - Inteligência Artificial para Engenharia de Segurança",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar estilos CSS customizados
def load_local_css():
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_local_css()

# Banco de dados simulado na sessão para persistência durante o teste da demo
if 'cat_history' not in st.session_state:
    st.session_state['cat_history'] = [
        {
            "id": 1,
            "nome": "João Alberto Souza",
            "cpf": "123.876.543-11",
            "nascimento": "12/03/1988",
            "cargo": "Ajudante de Carga",
            "pis": "123.45678.90-1",
            "setor": "Logística / Expedição",
            "data_acidente": "15/07/2026",
            "hora_acidente": "09:30",
            "tipo_acidente": "Típico",
            "gravidade": "Moderada",
            "esocial_parte_corpo_codigo": "300000000",
            "esocial_parte_corpo_desc": "Membros Superiores",
            "cid_codigo": "S62",
            "cid_descricao": "Fratura ao nível do punho e da mão",
            "dias_afastamento": 30,
            "crm_medico": "12456-SP",
            "data_emissao": "16/07/2026",
            "causa_raiz": "Piso oleoso causou escorregamento ao carregar peso manualmente.",
            "descricao": "Colaborador escorregou em poça de óleo hidráulico enquanto carregava palete de peças, caindo sobre o punho direito."
        },
        {
            "id": 2,
            "nome": "Marcos Vinicius Lima",
            "cpf": "456.123.789-22",
            "nascimento": "22/11/1995",
            "cargo": "Operador de Torno",
            "pis": "124.98765.43-2",
            "setor": "Usinagem",
            "data_acidente": "22/07/2026",
            "hora_acidente": "16:45",
            "tipo_acidente": "Típico",
            "gravidade": "Leve",
            "esocial_parte_corpo_codigo": "300000000",
            "esocial_parte_corpo_desc": "Membros Superiores",
            "cid_codigo": "S52",
            "cid_descricao": "Fratura do antebraço",
            "dias_afastamento": 15,
            "crm_medico": "32145-SP",
            "data_emissao": "23/07/2026",
            "causa_raiz": "Uso de ferramentas rotativas com folgas mecânicas sem proteção adequada.",
            "descricao": "Ao ajustar gabarito no torno mecânico, a peça travou e rebateu contra o braço esquerdo do operador."
        },
        {
            "id": 3,
            "nome": "Ana Júlia Santos",
            "cpf": "789.456.123-33",
            "nascimento": "05/05/1991",
            "cargo": "Analista Administrativo",
            "pis": "130.65432.10-9",
            "setor": "Administração",
            "data_acidente": "25/07/2026",
            "hora_acidente": "08:15",
            "tipo_acidente": "Trajeto",
            "gravidade": "Leve",
            "esocial_parte_corpo_codigo": "400000000",
            "esocial_parte_corpo_desc": "Membros Inferiores",
            "cid_codigo": "S93",
            "cid_descricao": "Entorse e distensão ao nível do tornozelo e do pé",
            "dias_afastamento": 7,
            "crm_medico": "87541-SP",
            "data_emissao": "26/07/2026",
            "causa_raiz": "Buraco em via pública de pedestres durante deslocamento casa-trabalho.",
            "descricao": "Colaboradora torceu o tornozelo esquerdo ao descer do ônibus a caminho do trabalho."
        }
    ]

# --- Sidebar ---
st.sidebar.markdown("<h2 style='text-align: center; color: #06b6d4;'>🛡️ SafeCAT AI</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-size: 0.85em; color: #64748b;'>Engine Inteligente de Segurança do Trabalho</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

menu = st.sidebar.radio("Navegação", ["Dashboard HSE", "Emitir Nova CAT (IA)", "Histórico de CATs", "Sobre o Pitch"])

st.sidebar.markdown("---")
st.sidebar.info("""
    **Hackathon Mode**
    - Autocomplete de CID-10
    - OCR Médico Integrado
    - 5 Porquês por Generative AI
    - eSocial Tabela 14/24
""")

# --- ABA 1: DASHBOARD HSE ---
if menu == "Dashboard HSE":
    st.markdown("<h1>🛡️ SafeCAT AI - Painel Executivo HSE</h1>", unsafe_allow_html=True)
    st.write("Visão unificada das ocorrências de acidentes e indicadores de frequência/gravidade.")
    
    # 1. Métricas Principais
    df_history = pd.DataFrame(st.session_state['cat_history'])
    total_accidents = len(df_history)
    total_days_off = df_history['dias_afastamento'].sum()
    avg_days_off = df_history['dias_afastamento'].mean()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Ocorrências", total_accidents)
    col2.metric("Dias Perdidos (Total)", f"{total_days_off} dias")
    col3.metric("Média de Afastamento", f"{avg_days_off:.1f} dias")
    col4.metric("Status eSocial", "100% Integrado", delta="eSocial V2.5")
    
    st.markdown("---")
    
    # 2. Body Injury Map & Charts Row
    col_map, col_chart = st.columns([1.2, 1.8])
    
    with col_map:
        st.subheader("🩺 Mapa de Calor de Lesões")
        st.write("Partes do corpo mais afetadas pelas ocorrências catalogadas.")
        
        # Agrupar dados por parte do corpo
        body_counts = df_history['esocial_parte_corpo_desc'].value_counts()
        
        head_qty = body_counts.get("Cabeça", 0)
        upper_qty = body_counts.get("Membros Superiores", 0)
        lower_qty = body_counts.get("Membros Inferiores", 0)
        trunk_qty = body_counts.get("Tronco", 0)
        multi_qty = body_counts.get("Regiões Múltiplas", 0)
        
        # Renderizar representação do corpo baseada em grid
        st.markdown(f"""
        <div class="injury-map-container">
            <div style='background: rgba(6, 182, 212, {0.1 + min(head_qty*0.2, 0.9)}); border: 1px solid #06b6d4; padding: 10px; margin: 5px; border-radius: 8px;'>
                <strong>Cabeça:</strong> {head_qty} acidente(s)
            </div>
            <div style='display: flex; justify-content: space-between;'>
                <div style='background: rgba(6, 182, 212, {0.1 + min(upper_qty*0.2, 0.9)}); border: 1px solid #06b6d4; padding: 10px; margin: 5px; border-radius: 8px; width: 45%;'>
                    <strong>Membros Superiores:</strong> {upper_qty}
                </div>
                <div style='background: rgba(6, 182, 212, {0.1 + min(trunk_qty*0.2, 0.9)}); border: 1px solid #06b6d4; padding: 10px; margin: 5px; border-radius: 8px; width: 45%;'>
                    <strong>Tronco:</strong> {trunk_qty}
                </div>
            </div>
            <div style='background: rgba(6, 182, 212, {0.1 + min(lower_qty*0.2, 0.9)}); border: 1px solid #06b6d4; padding: 10px; margin: 5px; border-radius: 8px;'>
                <strong>Membros Inferiores:</strong> {lower_qty}
            </div>
            <div style='background: rgba(6, 182, 212, {0.1 + min(multi_qty*0.2, 0.9)}); border: 1px solid #06b6d4; padding: 10px; margin: 5px; border-radius: 8px; font-size: 0.9em; opacity: 0.7;'>
                Regiões Múltiplas / Geral: {multi_qty}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_chart:
        st.subheader("📊 Análise de Distribuição")
        chart_type = st.selectbox("Selecione o indicador", ["Acidentes por Setor", "Tipos de Acidente (eSocial)", "Gravidade dos Incidentes"])
        
        if chart_type == "Acidentes por Setor":
            fig = px.bar(df_history, x='setor', title="Ocorrências por Setor", color='setor', color_discrete_sequence=px.colors.sequential.Cyan_r)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#f8fafc')
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "Tipos de Acidente (eSocial)":
            fig = px.pie(df_history, names='tipo_acidente', title="Tipos de Ocorrência", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#f8fafc')
            st.plotly_chart(fig, use_container_width=True)
        else: # Gravidade
            fig = px.bar(df_history, x='gravidade', title="Distribuição por Gravidade", color='gravidade', color_discrete_sequence=['#22c55e', '#eab308', '#ef4444'])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#f8fafc')
            st.plotly_chart(fig, use_container_width=True)

# --- ABA 2: EMITIR NOVA CAT COM IA ---
elif menu == "Emitir Nova CAT (IA)":
    st.markdown("<h1>🤖 Geração Assistida de CAT via IA</h1>", unsafe_allow_html=True)
    st.write("Suba o atestado médico digitalizado para extrair dados ou digite o relato da ocorrência para análise inteligente.")
    
    st.markdown("### 1. Ingestão Inteligente e OCR")
    
    col_ocr, col_cert = st.columns([1.5, 1.5])
    
    ocr_data = {}
    
    with col_ocr:
        uploaded_file = st.file_uploader("Upload do Atestado Médico (Imagem ou PDF)", type=["jpg", "png", "pdf"])
        
        # Simulação de OCR se arquivo for fornecido
        if uploaded_file is not None:
            st.success("Arquivo recebido com sucesso. Processando OCR por Inteligência Artificial...")
            # Fornece um texto de atestado médico padrão para o mock ler
            mock_text = """
            Atesto para os devidos fins que o Sr. Carlos Eduardo da Silva esteve sob cuidados médicos
            no dia 30/07/2026 necessitando de 15 dias de repouso por motivo de saúde devido a fratura
            no punho esquerdo correspondente ao código CID S52. CRM 54321-SP.
            """
            ocr_data = process_certificate_ocr(mock_text)
            
            st.json(ocr_data)
        else:
            st.info("Dica: Carregue um atestado médico simulado para ver a extração de dados inteligente da IA (Nome, CRM, CID-10, Afastamento).")
            
    with col_cert:
        st.write("**Dados Extraídos do Atestado:**")
        patient_name = st.text_input("Nome do Acidentado*", value=ocr_data.get("paciente", ""))
        patient_cpf = st.text_input("CPF*", value="111.222.333-44")
        days_off = st.number_input("Dias de Afastamento*", min_value=0, value=ocr_data.get("dias_afastamento", 0))
        crm_medico = st.text_input("CRM do Médico*", value=ocr_data.get("crm_medico", ""))
        
        # Busca Dinâmica de CID-10
        cid_query = st.text_input("Buscar CID-10 (Código ou Descrição)*", value=ocr_data.get("cid_codigo", ""))
        if cid_query:
            cids_found = search_cid(cid_query)
            selected_cid = st.selectbox("Selecione o CID correspondente*", list(cids_found.keys()))
            cid_desc = CID_10_DATABASE.get(selected_cid, "Outros traumatismos")
            st.info(f"Diagnóstico Mapeado: **{cid_desc}**")
        else:
            selected_cid = "T14"
            cid_desc = "Traumatismo indeterminado"

    st.markdown("---")
    st.markdown("### 2. Análise do Acidente & Investigação de Causa Raiz")
    
    narrative_input = st.text_area(
        "Descreva a ocorrência em linguagem natural (Relato do supervisor)*",
        placeholder="Ex: O operador estava limpando a prensa mecânica quando deslizou a luva e prensou o braço direito na barreira acrílica sem intertravamento..."
    )
    
    if st.button("Analisar Incidente com IA"):
        if not narrative_input:
            st.error("Por favor, relate o acidente para que a IA possa conduzir a investigação.")
        else:
            with st.spinner("Conduzindo análise de causa raiz (5 Porquês) e enquadramento do eSocial..."):
                analysis_results = analyze_accident_narrative(narrative_input)
                
                st.session_state['analysis'] = analysis_results
                st.session_state['narrative'] = narrative_input
                st.success("Análise concluída com sucesso!")
                
    if 'analysis' in st.session_state:
        res = st.session_state['analysis']
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write("##### 🔬 Enquadramento Técnico")
            st.write(f"**Tipo de Acidente:** {res['tipo_acidente']}")
            st.write(f"**Gravidade Estimada:** {res['gravidade']}")
            st.write(f"**eSocial Categoria Corpo:** {res['esocial_parte_corpo_desc']} (Cod: {res['esocial_parte_corpo_codigo']})")
            
        with col_res2:
            st.write("##### 🛡️ Causa Raiz Principal")
            st.info(res['causa_raiz'])
            
        st.markdown("##### 🪵 Investigação dos 5 Porquês (Análise de Causa)")
        for idx, why in enumerate(res['cinco_porques']):
            st.markdown(f"**{idx+1}º Porquê:** {why}")
            
        st.markdown("##### 🚀 Plano de Ação Recomendado (Hierarquia de Controles)")
        col_rec1, col_rec2, col_rec3 = st.columns(3)
        col_rec1.warning(f"**Engenharia/Eliminação:**\n\n{res['recomendacoes']['Eliminação/Engenharia']}")
        col_rec2.info(f"**Administrativo:**\n\n{res['recomendacoes']['Administrativo']}")
        col_rec3.success(f"**EPI recomendado:**\n\n{res['recomendacoes']['EPI']}")

        st.markdown("---")
        st.markdown("### 3. Emissão da CAT Oficial")
        
        # Formulação final da CAT para exportação
        cat_payload = {
            "nome": patient_name,
            "cpf": patient_cpf,
            "nascimento": "15/08/1994",
            "cargo": "Operador de Máquinas CNC",
            "pis": "120.43210.89-1",
            "setor": "Usinagem/Logística",
            "data_acidente": datetime.today().strftime("%d/%m/%Y"),
            "hora_acidente": "14:20",
            "tipo_acidente": res['tipo_acidente'],
            "gravidade": res['gravidade'],
            "esocial_parte_corpo_codigo": res['esocial_parte_corpo_codigo'],
            "esocial_parte_corpo_desc": res['esocial_parte_corpo_desc'],
            "cid_codigo": selected_cid,
            "cid_descricao": cid_desc,
            "dias_afastamento": days_off,
            "crm_medico": crm_medico,
            "data_emissao": datetime.today().strftime("%d/%m/%Y"),
            "causa_raiz": res['causa_raiz'],
            "descricao": st.session_state['narrative']
        }
        
        col_save, col_dl = st.columns(2)
        with col_save:
            if st.button("Salvar CAT no Histórico"):
                # Garante ID único
                new_id = len(st.session_state['cat_history']) + 1
                cat_payload["id"] = new_id
                st.session_state['cat_history'].append(cat_payload)
                st.success(f"CAT ID {new_id} salva com sucesso no banco de dados corporativo!")
                
        with col_dl:
            pdf_bytes = generate_cat_pdf(cat_payload)
            st.download_button(
                label="📥 Exportar CAT Oficial em PDF",
                data=pdf_bytes,
                file_name=f"cat_{patient_name.replace(' ', '_').lower()}.pdf",
                mime="application/pdf"
            )

# --- ABA 3: HISTÓRICO DE CATS ---
elif menu == "Histórico de CATs":
    st.markdown("<h1>📋 Histórico de Ocorrências e Emissões</h1>", unsafe_allow_html=True)
    st.write("Lista de CATs geradas pelo sistema, prontas para visualização, download ou re-geração de PDF.")
    
    df_history = pd.DataFrame(st.session_state['cat_history'])
    
    if not df_history.empty:
        # Limpar colunas técnicas de visualização
        st.dataframe(df_history[["id", "nome", "setor", "data_acidente", "tipo_acidente", "gravidade", "cid_codigo", "dias_afastamento"]], use_container_width=True, hide_index=True)
        
        st.markdown("### Detalhes Individuais da Ocorrência")
        selected_cat_id = st.selectbox("Selecione o ID do Relatório", options=df_history['id'].tolist())
        
        selected_row = df_history[df_history['id'] == selected_cat_id].iloc[0].to_dict()
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"**Paciente:** {selected_row['nome']} | CPF: {selected_row['cpf']}")
            st.markdown(f"**Setor:** {selected_row['setor']} | Cargo: {selected_row['cargo']}")
            st.markdown(f"**Acidente:** {selected_row['data_acidente']} às {selected_row['hora_acidente']}")
            st.markdown(f"**Código CID-10:** {selected_row['cid_codigo']} - {selected_row['cid_descricao']}")
        with col_d2:
            st.markdown(f"**Tipo de Acidente:** {selected_row['tipo_acidente']}")
            st.markdown(f"**Gravidade:** {selected_row['gravidade']}")
            st.markdown(f"**Causa Raiz:** {selected_row['causa_raiz']}")
            st.markdown(f"**Afastamento:** {selected_row['dias_afastamento']} dias")
            
        pdf_bytes = generate_cat_pdf(selected_row)
        st.download_button(
            label=f"📥 Download PDF da CAT de {selected_row['nome']}",
            data=pdf_bytes,
            file_name=f"cat_{selected_row['nome'].replace(' ', '_').lower()}.pdf",
            mime="application/pdf",
            key=f"dl_{selected_cat_id}"
        )
    else:
        st.info("Nenhuma CAT cadastrada no momento.")

# --- ABA 4: PITCH DO HACKATHON ---
else:
    st.markdown("<h1>🏆 SafeCAT AI - Pitch do Hackathon</h1>", unsafe_allow_html=True)
    
    st.markdown("""
    ### 🎯 O Problema
    A emissão de **Comunicação de Acidente de Trabalho (CAT)** no Brasil é altamente burocrática e cheia de regras de conformidade com o **eSocial** (Tabelas 14 e 24).
    - Engenheiros de Segurança e Supervisores gastam horas classificando lesões, descobrindo o CID-10 correspondente e preenchendo formulários do governo.
    - Erros de digitação geram **pesadas multas** trabalhistas e previdenciárias.
    - O mais grave: após o preenchimento, os dados são simplesmente arquivados, sem que uma investigação séria de causa raiz (ex: 5 Porquês) seja feita para evitar novos acidentes.

    ### 💡 A Solução: SafeCAT AI
    Unificamos **IA Generativa**, **OCR Médico** e **Engenharia de Segurança** em um único SaaS corporativo de alta performance.
    1. **Extração Automática:** A IA faz o parsing do atestado médico via OCR e preenche 80% do formulário eSocial de imediato.
    2. **Busca e Sugestão Inteligente:** A IA descobre o código eSocial da parte do corpo afetada e do CID de forma instantânea.
    3. **Investigação Integrada (Root Cause):** O supervisor conta como o acidente ocorreu e a IA gera uma árvore dos **5 Porquês** estruturada e propõe planos de ação na hierarquia de controles (EPIs, Engenharia e Processo).
    4. **Painel Preventivo:** O painel HSE plota automaticamente o mapa de calor corporal de lesões, identificando padrões de risco silenciosos por setor.

    ### 🚀 Diferenciais Competitivos
    - **ACID Compliant e eSocial Ready:** Integração imediata das tabelas 14 e 24.
    - **Proativo, não apenas reativo:** Transforma obrigações burocráticas em planos de ação de engenharia de segurança reais.
    - **Visual Impressionante:** Interface escura otimizada com gradientes ciano neon e mapa de lesões interativo.
    """)
