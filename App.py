import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date
import re
import pytz  # Para fuso horário correto

# ------------------------------
# Configuração da página
# ------------------------------
st.set_page_config(page_title="Registro de Paletes", layout="centered")

st.title("❄️ Entrada de Paletes | Perecíveis")

# ------------------------------
# CSS customizado + JavaScript para scroll no foco (solução Android + teclado)
# ------------------------------
st.markdown("""
<style>
h1, h2 {
    text-align: center;
}
h1 {
    font-size: 1.5rem !important;
    white-space: nowrap;
}
@media (max-width: 480px) {
    h1 {
        font-size: 1.2rem !important;
    }
}
div[data-testid="column"] button[kind="primaryFormSubmit"]:has(> div > p:contains("Finalizar e enviar")) {
    background-color: #28a745 !important;
    border-color: #28a745 !important;
}
div[data-testid="column"] button[kind="primaryFormSubmit"]:has(> div > p:contains("Finalizar e enviar")):hover {
    background-color: #218838 !important;
    border-color: #1e7e34 !important;
}
</style>

<script>
document.addEventListener("DOMContentLoaded", function() {
    // Função para rolar o elemento focado para uma posição visível acima do teclado
    function scrollToFocusedElement(element) {
        // Aguarda um pequeno delay para o teclado começar a aparecer
        setTimeout(() => {
            const rect = element.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            // Altura estimada do teclado (média ~40% da tela, mas usamos margem segura)
            const keyboardEstimate = viewportHeight * 0.4;
            // Posição alvo: queremos que o elemento fique a 80px do topo após a rolagem
            const targetTop = rect.top + window.scrollY - 80;
            
            // Se o elemento estiver na metade inferior da tela (próximo ao teclado)
            if (rect.bottom > viewportHeight - keyboardEstimate) {
                window.scrollTo({
                    top: targetTop,
                    behavior: "smooth"
                });
            } else {
                // Pequeno ajuste suave mesmo se já estiver visível
                window.scrollBy({
                    top: 0,
                    behavior: "smooth"
                });
            }
        }, 250); // Tempo suficiente para o teclado começar a abrir
    }

    // Observador de redimensionamento (teclado abre/fecha)
    let lastViewportHeight = window.innerHeight;
    let focusedElementAtResize = null;
    
    function onResize() {
        const newHeight = window.innerHeight;
        if (newHeight !== lastViewportHeight && document.activeElement) {
            // O teclado mudou o tamanho da viewport
            focusedElementAtResize = document.activeElement;
            scrollToFocusedElement(focusedElementAtResize);
        }
        lastViewportHeight = newHeight;
    }
    
    window.addEventListener('resize', onResize);

    // Seleciona todos os campos que podem receber foco
    const focusableSelectors = [
        'input', 'select', 'textarea',
        '[class*="st-b6"]', '[class*="st-b7"]',
        '[role="combobox"]', '[data-testid="stSelectbox"]',
        '[data-testid="stDateInput"]', '[data-testid="stTextInput"]'
    ];

    function addScrollListener(el) {
        if (!el.hasAttribute('data-scroll-listener')) {
            el.setAttribute('data-scroll-listener', 'true');
            el.addEventListener('focus', function(e) {
                scrollToFocusedElement(e.target);
            });
        }
    }

    // Adiciona listeners aos elementos existentes
    const focusableElements = document.querySelectorAll(focusableSelectors.join(','));
    focusableElements.forEach(addScrollListener);

    // Observador para elementos adicionados dinamicamente (Streamlit rerun)
    const observer = new MutationObserver(() => {
        const newElements = document.querySelectorAll(focusableSelectors.join(','));
        newElements.forEach(addScrollListener);
    });
    observer.observe(document.body, { childList: true, subtree: true });
});
</script>
""", unsafe_allow_html=True)

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

    # Ordem correta das colunas
    colunas_corretas = ["registro", "camara", "camara-vaga", "produto-marca", "produto-descricao", "validade"]

    header = sheet.row_values(1)
    if not header:
        sheet.append_row(colunas_corretas)
    elif header != colunas_corretas:
        if "registro" not in header:
            sheet.insert_cols(1)
            sheet.update_cell(1, 1, "registro")
    return sheet

def carregar_dados_existentes(sheet):
    dados = sheet.get_all_records()
    return pd.DataFrame(dados)

def combina_existe(camara, vaga, df_existente):
    if df_existente.empty:
        return False
    return ((df_existente['camara'] == camara) & (df_existente['camara-vaga'] == vaga)).any()

def salvar_registros(sheet, registros):
    # Define o fuso horário de Santa Catarina (Brasil) -> UTC-3
    tz = pytz.timezone('America/Sao_Paulo')
    for reg in registros:
        timestamp = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        sheet.append_row([
            timestamp,
            reg['camara'],
            reg['camara-vaga'],
            reg['produto-marca'],
            reg['produto-descricao'],
            reg['validade']
        ])

def excluir_registros_vaga(sheet, camara, vaga):
    """Exclui todas as linhas da planilha que correspondem à câmara e vaga informadas."""
    all_values = sheet.get_all_values()
    if not all_values:
        return 0
    rows_to_delete = []
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) >= 3 and row[1] == camara and row[2] == vaga:
            rows_to_delete.append(i)
    for row_num in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(row_num)
    return len(rows_to_delete)

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
if 'exibir_gerenciamento' not in st.session_state:
    st.session_state.exibir_gerenciamento = False

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
        st.error(f"⚠️ A combinação {camara_selecionada} / {vaga_selecionada} já está sendo usada.")
        st.session_state.bloqueado = True
        st.session_state.camara = None
        st.session_state.vaga = None
        st.session_state.exibir_gerenciamento = True
    else:
        st.success("Vaga disponível!")
        st.session_state.bloqueado = False
        st.session_state.camara = camara_selecionada
        st.session_state.vaga = vaga_selecionada
        st.session_state.exibir_gerenciamento = False
else:
    st.session_state.bloqueado = False
    st.session_state.camara = None
    st.session_state.vaga = None
    st.session_state.exibir_gerenciamento = False

# ------------------------------
# 1.1 Gerenciamento de vaga ocupada
# ------------------------------
if st.session_state.exibir_gerenciamento and camara_selecionada != "Selecione a câmara" and vaga_selecionada != "Selecione a vaga":
    with st.expander("🔍 Gerenciar vaga ocupada", expanded=True):
        df_filtrado = df_existente[
            (df_existente['camara'] == camara_selecionada) &
            (df_existente['camara-vaga'] == vaga_selecionada)
        ]
        st.write(f"**Registros encontrados para {camara_selecionada} / {vaga_selecionada}:**")
        if not df_filtrado.empty:
            # Exibe também a coluna 'registro'
            st.dataframe(df_filtrado[['registro', 'produto-marca', 'produto-descricao', 'validade']], use_container_width=True)
        else:
            st.info("Nenhum registro detalhado encontrado (inconsistência de dados).")

        st.divider()
        st.warning("⚠️ **Ação irreversível:** Excluir todos os registros desta vaga.")
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            confirmar_exclusao = st.checkbox("✅ Confirmar exclusão de todos os registros desta vaga")
        with col_confirm2:
            if st.button("🗑️ Excluir todos os registros", type="primary", disabled=not confirmar_exclusao):
                with st.spinner("Excluindo registros..."):
                    num_excluidos = excluir_registros_vaga(sheet, camara_selecionada, vaga_selecionada)
                if num_excluidos > 0:
                    st.success(f"{num_excluidos} registro(s) excluído(s) com sucesso! A vaga agora está livre.")
                    df_existente = carregar_dados_existentes(sheet)
                    st.session_state.bloqueado = False
                    st.session_state.camara = camara_selecionada
                    st.session_state.vaga = vaga_selecionada
                    st.session_state.exibir_gerenciamento = False
                    st.session_state.produtos_temp = []
                    force_reset()
                else:
                    st.error("Nenhum registro foi excluído. Verifique se a combinação realmente existe.")
        st.info("💡 Após excluir, a vaga ficará livre para novo cadastro.")

# ------------------------------
# 2. Adicionar produtos (se vaga disponível)
# ------------------------------
if not st.session_state.bloqueado and st.session_state.camara and st.session_state.vaga:
    st.subheader("📦 Produtos no Palete")

    with st.form(key="produto_form", clear_on_submit=True):
        marca_opcoes = [
            "", "Seara", "Seara | Doriana", "Seara | Primor", "Seara | Excelsior",
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

    if st.session_state.produtos_temp:
        st.write("**Produtos neste palete:**")
        for i, p in enumerate(st.session_state.produtos_temp, 1):
            st.write(f"{i}. {p['produto-marca']} - {p['produto-descricao']} (val.: {p['validade']})")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("➕ Adicionar mais", use_container_width=True, type="secondary"):
                st.rerun()
        with col2:
            if st.button("Finalizar e enviar", use_container_width=True, type="primary", key="finalizar_button"):
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
    if st.session_state.bloqueado and not st.session_state.exibir_gerenciamento:
        st.info("🔁 Altere a câmara ou vaga para uma combinação livre.")