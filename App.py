import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import pytz

# ------------------------------
# Configuração da página
# ------------------------------
st.set_page_config(page_title="Registro de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes | Perecíveis")

# ------------------------------
# CSS + JavaScript: rolagem inteligente para Android
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
    // ---------- ROLAGEM INTELIGENTE PARA O PRÓXIMO CAMPO (ANDROID) ----------
    function scrollToElement(element, offset = 80) {
        if (!element) return;
        // Usa scrollIntoView com alinhamento suave e bloqueio no início
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
            inline: 'nearest'
        });
        // Ajuste fino para compensar cabeçalhos fixos ou barra superior
        setTimeout(() => {
            const rect = element.getBoundingClientRect();
            const currentScroll = window.scrollY;
            const targetScroll = currentScroll + rect.top - offset;
            window.scrollTo({ top: targetScroll, behavior: 'smooth' });
        }, 100);
    }

    function getNextFocusableElement(currentElement) {
        // Seleciona todos os campos de entrada, selects, textareas, datepickers e comboboxes
        const focusableSelectors = [
            'input:not([type="hidden"])', 'select', 'textarea',
            '[role="combobox"]', '[data-testid="stSelectbox"]',
            '[data-testid="stDateInput"] input', '[data-testid="stTextInput"] input',
            '[contenteditable="true"]'
        ];
        const focusableElements = Array.from(document.querySelectorAll(focusableSelectors.join(',')))
            .filter(el => el.offsetParent !== null); // apenas visíveis
        
        const currentIndex = focusableElements.indexOf(currentElement);
        if (currentIndex !== -1 && currentIndex + 1 < focusableElements.length) {
            return focusableElements[currentIndex + 1];
        }
        return null;
    }

    // Função principal: ao preencher/perder foco, exibe o próximo campo
    function onFieldInteraction(event) {
        const target = event.target;
        // Aguarda o término da interação (ex: após digitar ou ao sair do campo)
        setTimeout(() => {
            // Se o campo perdeu foco (blur) ou se o usuário pressionou Enter/Next
            const nextField = getNextFocusableElement(target);
            if (nextField) {
                scrollToElement(nextField, 100);
            } else {
                // Se não há próximo campo, mantém o atual visível
                scrollToElement(target, 80);
            }
        }, 150);
    }

    function onKeydownHandler(event) {
        // Detecta tecla Enter ou "Next" (código 9 = Tab, 13 = Enter)
        if (event.key === 'Enter' || event.key === 'Tab') {
            // Pequeno delay para permitir a mudança de foco natural
            setTimeout(() => {
                const active = document.activeElement;
                if (active) {
                    const next = getNextFocusableElement(active);
                    if (next) scrollToElement(next, 100);
                    else scrollToElement(active, 80);
                }
            }, 50);
        }
    }

    // ---------- AJUSTE PARA DROPDOWN (mantido do original) ----------
    function adjustDropdownPosition(selectElement) {
        let dropdown = selectElement.nextElementSibling;
        if (!dropdown || !dropdown.matches('[role="listbox"], .st-bq, .st-br, [data-testid="stSelectboxDropdown"]')) {
            dropdown = selectElement.parentElement?.querySelector('[role="listbox"]');
        }
        if (!dropdown) return;
        
        const rect = selectElement.getBoundingClientRect();
        const dropdownHeight = dropdown.offsetHeight;
        const viewportHeight = window.innerHeight;
        const spaceBelow = viewportHeight - rect.bottom;
        const spaceAbove = rect.top;
        
        if (spaceAbove > spaceBelow || spaceBelow < dropdownHeight) {
            dropdown.style.top = 'auto';
            dropdown.style.bottom = `${viewportHeight - rect.top + 8}px`;
            dropdown.style.transformOrigin = 'bottom';
        } else {
            dropdown.style.top = `${rect.bottom + 5}px`;
            dropdown.style.bottom = 'auto';
            dropdown.style.transformOrigin = 'top';
        }
    }

    function setupSelectBehavior(selectElement) {
        if (selectElement.hasAttribute('data-dropdown-adjusted')) return;
        selectElement.setAttribute('data-dropdown-adjusted', 'true');
        selectElement.addEventListener('click', () => setTimeout(() => adjustDropdownPosition(selectElement), 50));
        selectElement.addEventListener('focus', () => setTimeout(() => adjustDropdownPosition(selectElement), 50));
        window.addEventListener('resize', () => {
            if (document.activeElement === selectElement) adjustDropdownPosition(selectElement);
        });
    }

    // ---------- REGISTRA EVENTOS EM TODOS OS CAMPOS ----------
    function attachFieldBehaviors() {
        const focusableSelectors = [
            'input:not([type="hidden"])', 'select', 'textarea',
            '[role="combobox"]', '[data-testid="stSelectbox"]',
            '[data-testid="stDateInput"] input', '[data-testid="stTextInput"] input'
        ];
        const fields = document.querySelectorAll(focusableSelectors.join(','));
        
        fields.forEach(field => {
            if (!field.hasAttribute('data-scroll-enhanced')) {
                field.setAttribute('data-scroll-enhanced', 'true');
                // Evento blur: ao sair do campo, rola para o próximo
                field.addEventListener('blur', onFieldInteraction);
                // Evento keydown para Enter/Tab
                field.addEventListener('keydown', onKeydownHandler);
                // Para selects e comboboxes, também ajusta dropdown
                if (field.matches('select, [role="combobox"], [data-testid="stSelectbox"]')) {
                    setupSelectBehavior(field);
                }
            }
        });
    }

    // Executa inicial e observa mudanças no DOM (Streamlit recarrega partes)
    attachFieldBehaviors();
    const observer = new MutationObserver(() => attachFieldBehaviors());
    observer.observe(document.body, { childList: true, subtree: true });

    // Ajuste extra para quando o teclado virtual abre/fecha (viewport resize)
    let lastViewportHeight = window.innerHeight;
    window.addEventListener('resize', () => {
        const newHeight = window.innerHeight;
        const activeElement = document.activeElement;
        if (activeElement && newHeight !== lastViewportHeight) {
            // Teclado abriu ou fechou: rola suavemente para o campo ativo
            setTimeout(() => {
                scrollToElement(activeElement, 80);
            }, 50);
        }
        lastViewportHeight = newHeight;
    });
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
# Reset via query_params
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
# Estados da sessão
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

sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# 1. Seleção de câmara e vaga
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