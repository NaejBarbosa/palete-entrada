import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import re

# ------------------------------
# Configuração da página (mobile friendly)
# ------------------------------
st.set_page_config(page_title="Registro de Paletes", layout="centered")
st.title("🍱 Entrada de Paletes - Câmaras Frias")

# ------------------------------
# Conexão com Google Sheets
# ------------------------------
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # As credenciais vêm dos st.secrets (configuradas no Streamlit Cloud)
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Abre a planilha pelo ID (extraído da URL)
    sheet_id = "1HoN-VLyO5y9wJ4NKdpz42-BljRzT4VeJVY-Wio4CO6g"
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet

# ------------------------------
# Funções auxiliares
# ------------------------------
def carregar_dados_existentes(sheet):
    """Retorna um DataFrame com todos os registros da planilha"""
    dados = sheet.get_all_records()
    return pd.DataFrame(dados)

def combina_existe(camara, vaga, df_existente):
    """Verifica se a combinação câmara + vaga já foi registrada"""
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def validar_validade(data_str):
    """Valida formato dd/mm/aaaa e se a data é real"""
    padrao = r'^\d{2}/\d{2}/\d{4}$'
    if not re.match(padrao, data_str):
        return False
    try:
        datetime.strptime(data_str, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def salvar_registros(sheet, registros):
    """Adiciona uma lista de registros (cada registro é um dicionário) na planilha"""
    for reg in registros:
        sheet.append_row([
            reg['camara'],
            reg['camara-vaga'],
            reg['produto-marca'],
            reg['produto-descricao'],
            reg['validade']
        ])

# ------------------------------
# Sessão do formulário
# ------------------------------
if 'produtos_temp' not in st.session_state:
    st.session_state.produtos_temp = []   # lista de produtos (marca, descr, validade)
if 'camara' not in st.session_state:
    st.session_state.camara = None
if 'vaga' not in st.session_state:
    st.session_state.vaga = None
if 'bloqueado' not in st.session_state:
    st.session_state.bloqueado = False

# Conectar e carregar dados existentes (para validação)
try:
    sheet = conectar_planilha()
    df_existente = carregar_dados_existentes(sheet)
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    st.stop()

# ------------------------------
# 1. Seleção da câmara e vaga
# ------------------------------
st.subheader("📍 Localização do Palete")

camaras = ["Resfriados 1", "Resfriados 2", "Congelados 1", "Congelados 2"]
camara_selecionada = st.selectbox("Câmara", camaras, key="camara_select")
vaga_selecionada = st.selectbox("Vaga", [
    "A10D","A10E","A11D","A11E","A12D","A12E","A13D","A13E",
    "A20D","A20E","A21D","A21E","A22D","A22E","A23D","A23E",
    "A30D","A30E","A31D","A31E","A32D","A32E","A33D","A33E",
    "A40D","A40E","A41D","A41E","A42D","A42E","A43D","A43E",
    "A50D","A50E","A51D","A51E","A52D","A52E","A53D","A53E",
    "B10D","B10E","B11D","B11E","B12D","B12E","B13D","B13E",
    "B20D","B20E","B21D","B21E","B22D","B22E","B23D","B23E",
    "B30D","B30E","B31D","B31E","B32D","B32E","B33D","B33E",
    "B40D","B40E","B41D","B41E","B42D","B42E","B43D","B43E",
    "B50D","B50E","B51D","B51E","B52D","B52E","B53D","B53E"
], key="vaga_select")

# Verificar duplicidade
if camara_selecionada and vaga_selecionada:
    if combina_existe(camara_selecionada, vaga_selecionada, df_existente):
        st.error(f"⚠️ A combinação {camara_selecionada} / {vaga_selecionada} já está sendo usada. Escolha outra vaga.")
        st.session_state.bloqueado = True
    else:
        st.success("✅ Vaga disponível!")
        st.session_state.bloqueado = False
        st.session_state.camara = camara_selecionada
        st.session_state.vaga = vaga_selecionada

# ------------------------------
# 2. Adicionar produtos (se vaga disponível)
# ------------------------------
if not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga:
    st.subheader("📦 Produtos no Palete")
    
    with st.form(key="produto_form", clear_on_submit=True):
        marca_opcoes = [
            "Seara", "Seara | Doriana", "Seara | Primor", "Seara | Excelsior",
            "Seara | Macedo", "Seara | Rezende (pizza)", "Lar", "BRF | Perdigão",
            "BRF | Sadia", "BRF | Claybom", "BRF | Qualy", "BRF | Becel",
            "Aurora", "Aurora | Peperi", "Aurora | Nobre", "Outro"
        ]
        marca = st.selectbox("Produto / Marca", marca_opcoes)
        descricao = st.text_input("Descrição do produto (ex.: Peito de frango, 1kg)")
        validade = st.text_input("Validade (dd/mm/aaaa)")
        
        adicionado = st.form_submit_button("➕ Adicionar este produto")
        
        if adicionado:
            if not validar_validade(validade):
                st.error("Data inválida. Use o formato dd/mm/aaaa e uma data real.")
            elif not descricao.strip():
                st.error("Por favor, informe a descrição do produto.")
            else:
                st.session_state.produtos_temp.append({
                    "produto-marca": marca,
                    "produto-descricao": descricao,
                    "validade": validade
                })
                st.success(f"Produto '{marca}' adicionado! Total: {len(st.session_state.produtos_temp)}")
    
    # Exibir lista de produtos já adicionados
    if st.session_state.produtos_temp:
        st.write("**Produtos neste palete:**")
        for i, p in enumerate(st.session_state.produtos_temp, 1):
            st.write(f"{i}. {p['produto-marca']} - {p['produto-descricao']} (val.: {p['validade']})")
        
        # Botão finalizar
        if st.button("✅ Finalizar registro deste palete"):
            # Confirmação: adicionar mais produtos?
            confirmar = st.radio(
                "Deseja adicionar mais produtos para esta mesma câmara/vaga?",
                ("Sim, adicionar mais", "Não, finalizar e enviar")
            )
            if confirmar == "Não, finalizar e enviar":
                # Monta registros para gravar na planilha
                registros_para_gravar = []
                for prod in st.session_state.produtos_temp:
                    registros_para_gravar.append({
                        "camara": st.session_state.camara,
                        "camara-vaga": st.session_state.vaga,
                        "produto-marca": prod["produto-marca"],
                        "produto-descricao": prod["produto-descricao"],
                        "validade": prod["validade"]
                    })
                # Enviar para a planilha
                try:
                    salvar_registros(sheet, registros_para_gravar)
                    st.success(f"✅ {len(registros_para_gravar)} produto(s) registrado(s) com sucesso!")
                    # Limpar sessão para novo palete
                    st.session_state.produtos_temp = []
                    st.session_state.camara = None
                    st.session_state.vaga = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
else:
    if st.session_state.bloqueado:
        st.info("🔁 Altere a câmara ou vaga para uma combinação livre.")
