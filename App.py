import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date
import re

# ------------------------------
# Configuração da página
# ------------------------------
st.set_page_config(page_title="Registro de Paletes", layout="centered")
st.title("🍱 Entrada de Paletes - Câmaras Frias")

# ------------------------------
# Conexão com Google Sheets
# ------------------------------
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet_id = "1HoN-VLyO5y9wJ4NKdpz42-BljRzT4VeJVY-Wio4CO6g"
    sheet = client.open_by_key(sheet_id).sheet1
    return sheet

def carregar_dados_existentes(sheet):
    dados = sheet.get_all_records()
    return pd.DataFrame(dados)

def combina_existe(camara, vaga, df_existente):
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def salvar_registros(sheet, registros):
    for reg in registros:
        sheet.append_row([
            reg['camara'],
            reg['camara-vaga'],
            reg['produto-marca'],
            reg['produto-descricao'],
            reg['validade']
        ])

# ------------------------------
# Gerenciamento de reset via query_params
# ------------------------------
params = st.query_params
reset_token = params.get("reset_token", 0)
try:
    reset_token = int(reset_token)
except:
    reset_token = 0

def force_reset():
    st.query_params["reset_token"] = reset_token + 1
    st.rerun()

# ------------------------------
# Inicialização dos estados
# ------------------------------
if 'produtos_temp' not in st.session_state:
    st.session_state.produtos_temp = []
if 'camara' not in st.session_state:
    st.session_state.camara = None
if 'vaga' not in st.session_state:
    st.session_state.vaga = None
if 'bloqueado' not in st.session_state:
    st.session_state.bloqueado = False

# Carregar dados
sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# 1. Seleção da câmara e vaga
# ------------------------------
st.subheader("📍 Localização do Palete")

camaras = ["Resfriados 1", "Resfriados 2", "Congelados 1", "Congelados 2"]
camara_opts = ["Selecione a câmara"] + camaras
vagas = [
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
]
vaga_opts = ["Selecione a vaga"] + vagas

camara_selecionada = st.selectbox("Câmara", camara_opts, index=0, key=f"camara_{reset_token}")
vaga_selecionada = st.selectbox("Vaga", vaga_opts, index=0, key=f"vaga_{reset_token}")

if camara_selecionada != "Selecione a câmara" and vaga_selecionada != "Selecione a vaga":
    if combina_existe(camara_selecionada, vaga_selecionada, df_existente):
        st.error(f"⚠️ A combinação {camara_selecionada} / {vaga_selecionada} já está sendo usada. Escolha outra vaga.")
        st.session_state.bloqueado = True
        st.session_state.camara = None
        st.session_state.vaga = None
    else:
        # Formatação padronizada com st.success (igual aos produtos adicionados)
        st.success("Vaga disponível!")
        st.session_state.bloqueado = False
        st.session_state.camara = camara_selecionada
        st.session_state.vaga = vaga_selecionada
else:
    st.session_state.bloqueado = False
    st.session_state.camara = None
    st.session_state.vaga = None

# ------------------------------
# 2. Adicionar produtos (se vaga disponível)
# ------------------------------
if not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga:
    st.subheader("📦 Produtos no Palete")

    with st.form(key="produto_form", clear_on_submit=True):
        marca_opcoes = [
            "",  # opção vazia para não pré-selecionar nada
            "Seara", "Seara | Doriana", "Seara | Primor", "Seara | Excelsior",
            "Seara | Macedo", "Seara | Rezende (pizza)", "Lar", "BRF | Perdigão",
            "BRF | Sadia", "BRF | Claybom", "BRF | Qualy", "BRF | Becel",
            "Aurora", "Aurora | Peperi", "Aurora | Nobre", "Outro"
        ]
        marca = st.selectbox("Produto / Marca", marca_opcoes, index=0)
        descricao = st.text_input("Descrição do produto (ex.: Peito de frango, 1kg)")

        data_validade = st.date_input(
            "Validade", 
            value=None, 
            format="DD/MM/YYYY",
            help="Selecione a data no calendário"
        )

        adicionado = st.form_submit_button("➕ Adicionar este produto")

        if adicionado:
            if not marca.strip():
                st.error("Por favor, selecione uma marca/produto válida.")
            elif data_validade is None:
                st.error("Por favor, selecione a data de validade.")
            elif not descricao.strip():
                st.error("Por favor, informe a descrição do produto.")
            else:
                validade_str = data_validade.strftime("%d/%m/%Y")
                st.session_state.produtos_temp.append({
                    "produto-marca": marca,
                    "produto-descricao": descricao,
                    "validade": validade_str
                })
                st.success(f"Produto '{marca}' adicionado! Total: {len(st.session_state.produtos_temp)}")

    # Exibir lista de produtos
    if st.session_state.produtos_temp:
        st.write("**Produtos neste palete:**")
        for i, p in enumerate(st.session_state.produtos_temp, 1):
            st.write(f"{i}. {p['produto-marca']} - {p['produto-descricao']} (val.: {p['validade']})")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("➕ Adicionar mais", use_container_width=True, type="secondary"):
                st.rerun()
        with col2:
            if st.button("Finalizar e enviar", use_container_width=True, type="primary"):
                registros_para_gravar = []
                for prod in st.session_state.produtos_temp:
                    registros_para_gravar.append({
                        "camara": st.session_state.camara,
                        "camara-vaga": st.session_state.vaga,
                        "produto-marca": prod["produto-marca"],
                        "produto-descricao": prod["produto-descricao"],
                        "validade": prod["validade"]
                    })
                try:
                    salvar_registros(sheet, registros_para_gravar)
                    st.success(f"{len(registros_para_gravar)} produto(s) registrado(s) com sucesso!")
                    st.session_state.produtos_temp = []
                    st.session_state.camara = None
                    st.session_state.vaga = None
                    st.session_state.bloqueado = False
                    force_reset()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
        with col3:
            if st.button("🗑️ Cancelar palete", use_container_width=True, type="secondary"):
                st.session_state.produtos_temp = []
                st.session_state.camara = None
                st.session_state.vaga = None
                st.session_state.bloqueado = False
                force_reset()
else:
    if st.session_state.bloqueado:
        st.info("🔁 Altere a câmara ou vaga para uma combinação livre.")