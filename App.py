import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pytz

# ==============================
# CONSTANTES
# ==============================

SHEET_ID = "1HoN-VLyO5y9wJ4NKdpz42-BljRzT4VeJVY-Wio4CO6g"
TIMEZONE = pytz.timezone("America/Sao_Paulo")
COLUNAS = ["registro", "camara", "camara-vaga", "produto-marca", "produto-descricao", "validade"]

CAMARAS = ["Resfriados 1", "Resfriados 2", "Congelados 1", "Congelados 2"]
VAGAS = [
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

MARCAS = [
    "", "Seara", "Seara | Doriana", "Seara | Primor", "Seara | Excelsior",
    "Seara | Macedo", "Seara | Rezende (pizza)", "Lar", "BRF | Perdigão",
    "BRF | Sadia", "BRF | Claybom", "BRF | Qualy", "BRF | Becel",
    "Aurora", "Aurora | Peperi", "Aurora | Nobre", "Outro"
]

CSS = """
<style>
h1, h2 { text-align: center; }
h1 { font-size: 1.5rem !important; white-space: nowrap; }
@media (max-width: 480px) { h1 { font-size: 1.2rem !important; } }
div[data-testid="column"] button[kind="primaryFormSubmit"]:has(> div > p:contains("Finalizar e enviar")) {
    background-color: #28a745 !important;
    border-color: #28a745 !important;
}
div[data-testid="column"] button[kind="primaryFormSubmit"]:has(> div > p:contains("Finalizar e enviar")):hover {
    background-color: #218838 !important;
    border-color: #1e7e34 !important;
}
</style>
"""

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================

st.set_page_config(page_title="Registro de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes | Perecíveis")
st.markdown(CSS, unsafe_allow_html=True)

# ==============================
# GERENCIAMENTO DE SESSÃO
# ==============================

def init_session_state() -> None:
    """Inicializa as variáveis de estado da sessão."""
    defaults = {
        "produtos_temp": [],
        "camara": None,
        "vaga": None,
        "bloqueado": False,
        "exibir_gerenciamento": False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ==============================
# GOOGLE SHEETS
# ==============================

class SheetManager:
    """Gerencia todas as operações com a planilha Google Sheets."""
    def __init__(self):
        self.client = self._authenticate()
        self.sheet = self._get_sheet()

    def _authenticate(self):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)

    def _get_sheet(self):
        sheet = self.client.open_by_key(SHEET_ID).sheet1
        header = sheet.row_values(1)
        if not header:
            sheet.append_row(COLUNAS)
        elif header != COLUNAS:
            if "registro" not in header:
                sheet.insert_cols(1)
                sheet.update_cell(1, 1, "registro")
        return sheet

    def get_all_records(self) -> pd.DataFrame:
        """Retorna todos os registros da planilha como DataFrame."""
        dados = self.sheet.get_all_records()
        return pd.DataFrame(dados)

    def save_registros(self, registros: List[Dict]) -> None:
        """Salva uma lista de registros na planilha."""
        for reg in registros:
            timestamp = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")
            self.sheet.append_row([
                timestamp,
                reg["camara"],
                reg["camara-vaga"],
                reg["produto-marca"],
                reg["produto-descricao"],
                reg["validade"]
            ])

    def delete_registros_by_vaga(self, camara: str, vaga: str) -> int:
        """Remove todos os registros de uma determinada vaga. Retorna quantidade excluída."""
        all_values = self.sheet.get_all_values()
        if not all_values:
            return 0
        rows_to_delete = []
        for i, row in enumerate(all_values[1:], start=2):
            if len(row) >= 3 and row[1] == camara and row[2] == vaga:
                rows_to_delete.append(i)
        for row_num in sorted(rows_to_delete, reverse=True):
            self.sheet.delete_rows(row_num)
        return len(rows_to_delete)

# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def combina_existe(camara: str, vaga: str, df: pd.DataFrame) -> bool:
    """Verifica se a combinação câmara/vaga já existe no DataFrame."""
    if df.empty:
        return False
    return ((df["camara"] == camara) & (df["camara-vaga"] == vaga)).any()

def force_reset() -> None:
    """Força o reset da página incrementando o token nos query params."""
    token = st.query_params.get("reset_token", 0)
    try:
        token = int(token)
    except (ValueError, TypeError):
        token = 0
    st.query_params["reset_token"] = token + 1
    st.rerun()

def filtrar_df_vaga(df: pd.DataFrame, camara: str, vaga: str) -> pd.DataFrame:
    """Retorna DataFrame filtrado pela câmara e vaga."""
    return df[(df["camara"] == camara) & (df["camara-vaga"] == vaga)]

# ==============================
# COMPONENTES DA UI
# ==============================

def selecionar_localizacao(sheet_mgr: SheetManager, df_existente: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Renderiza os seletores de câmara e vaga, gerencia bloqueio e exibição de gerenciamento."""
    camara_opts = ["Selecione a câmara"] + CAMARAS
    vaga_opts = ["Selecione a vaga"] + VAGAS

    reset_token = st.query_params.get("reset_token", 0)
    try:
        reset_token = int(reset_token)
    except (ValueError, TypeError):
        reset_token = 0

    camara = st.selectbox("Câmara", camara_opts, index=0, key=f"camara_{reset_token}")
    vaga = st.selectbox("Vaga", vaga_opts, index=0, key=f"vaga_{reset_token}")

    if camara != "Selecione a câmara" and vaga != "Selecione a vaga":
        if combina_existe(camara, vaga, df_existente):
            st.error(f"⚠️ A combinação {camara} / {vaga} já está sendo usada.")
            st.session_state.bloqueado = True
            st.session_state.camara = None
            st.session_state.vaga = None
            st.session_state.exibir_gerenciamento = True
            return None, None
        else:
            st.success("Vaga disponível!")
            st.session_state.bloqueado = False
            st.session_state.camara = camara
            st.session_state.vaga = vaga
            st.session_state.exibir_gerenciamento = False
            return camara, vaga
    else:
        st.session_state.bloqueado = False
        st.session_state.camara = None
        st.session_state.vaga = None
        st.session_state.exibir_gerenciamento = False
        return None, None

def gerenciar_vaga_ocupada(sheet_mgr: SheetManager, df_existente: pd.DataFrame, camara: str, vaga: str) -> None:
    """Exibe o expansor de gerenciamento da vaga ocupada e permite exclusão."""
    with st.expander("🔍 Gerenciar vaga ocupada", expanded=True):
        df_filtrado = filtrar_df_vaga(df_existente, camara, vaga)
        st.write(f"**Registros encontrados para {camara} / {vaga}:**")
        if not df_filtrado.empty:
            st.dataframe(df_filtrado[["registro", "produto-marca", "produto-descricao", "validade"]], use_container_width=True)
        else:
            st.info("Nenhum registro detalhado encontrado (inconsistência de dados).")

        st.divider()
        st.warning("⚠️ **Ação irreversível:** Excluir todos os registros desta vaga.")
        col1, col2 = st.columns(2)
        with col1:
            confirmar = st.checkbox("✅ Confirmar exclusão de todos os registros desta vaga")
        with col2:
            if st.button("🗑️ Excluir todos os registros", type="primary", disabled=not confirmar):
                with st.spinner("Excluindo registros..."):
                    num_excluidos = sheet_mgr.delete_registros_by_vaga(camara, vaga)
                if num_excluidos > 0:
                    st.success(f"{num_excluidos} registro(s) excluído(s) com sucesso! A vaga agora está livre.")
                    # Força recarregamento dos dados
                    st.session_state.bloqueado = False
                    st.session_state.camara = camara
                    st.session_state.vaga = vaga
                    st.session_state.exibir_gerenciamento = False
                    st.session_state.produtos_temp = []
                    force_reset()
                else:
                    st.error("Nenhum registro foi excluído. Verifique se a combinação realmente existe.")
        st.info("💡 Após excluir, a vaga ficará livre para novo cadastro.")

def formulario_produto() -> Optional[Dict]:
    """Exibe o formulário de adição de produto. Retorna o dicionário do produto se adicionado, senão None."""
    with st.form(key="produto_form", clear_on_submit=True):
        marca = st.selectbox("Produto / Marca", MARCAS, index=0)
        descricao = st.text_input("Descrição do produto (ex.: Peito de frango, 1kg)")
        data_validade = st.date_input("Validade", value=None, format="DD/MM/YYYY", help="Selecione a data no calendário")
        adicionado = st.form_submit_button("➕ Adicionar este produto")

        if adicionado:
            if not marca.strip():
                st.error("Por favor, selecione uma marca/produto válida.")
                return None
            if data_validade is None:
                st.error("Por favor, selecione a data de validade.")
                return None
            if not descricao.strip():
                st.error("Por favor, informe a descrição do produto.")
                return None
            return {
                "produto-marca": marca,
                "produto-descricao": descricao,
                "validade": data_validade.strftime("%d/%m/%Y")
            }
    return None

def exibir_produtos_adicionados() -> None:
    """Mostra a lista de produtos temporários e fornece botões de ação."""
    if not st.session_state.produtos_temp:
        return

    st.write("**Produtos neste palete:**")
    for i, p in enumerate(st.session_state.produtos_temp, 1):
        st.write(f"{i}. {p['produto-marca']} - {p['produto-descricao']} (val.: {p['validade']})")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ Adicionar mais", use_container_width=True, type="secondary"):
            st.rerun()
    with col2:
        if st.button("Finalizar e enviar", use_container_width=True, type="primary", key="finalizar_button"):
            registros = [
                {
                    "camara": st.session_state.camara,
                    "camara-vaga": st.session_state.vaga,
                    "produto-marca": p["produto-marca"],
                    "produto-descricao": p["produto-descricao"],
                    "validade": p["validade"]
                }
                for p in st.session_state.produtos_temp
            ]
            try:
                sheet_mgr.save_registros(registros)
                st.success(f"{len(registros)} produto(s) registrado(s) com sucesso!")
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

# ==============================
# FLUXO PRINCIPAL
# ==============================

st.subheader("📍 Localização do Palete")

sheet_mgr = SheetManager()
df_existente = sheet_mgr.get_all_records()

camara, vaga = selecionar_localizacao(sheet_mgr, df_existente)

# Gerenciamento de vaga ocupada (se necessário)
if st.session_state.exibir_gerenciamento and camara and vaga:
    gerenciar_vaga_ocupada(sheet_mgr, df_existente, camara, vaga)

# Adição de produtos se vaga disponível
if not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga:
    st.subheader("📦 Produtos no Palete")
    novo_produto = formulario_produto()
    if novo_produto:
        st.session_state.produtos_temp.append(novo_produto)
        st.success(f"Produto '{novo_produto['produto-marca']}' adicionado! Total: {len(st.session_state.produtos_temp)}")
        st.rerun()
    exibir_produtos_adicionados()
elif st.session_state.bloqueado and not st.session_state.exibir_gerenciamento:
    st.info("🔁 Altere a câmara ou vaga para uma combinação livre.")