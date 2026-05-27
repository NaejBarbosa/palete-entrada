import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date
import pytz
import time
import uuid

# ------------------------------
# Configuração da página
# ------------------------------
st.set_page_config(page_title="Registro de Paletes", layout="centered")
st.title("❄️ Entrada de Paletes | Perecíveis")

# ------------------------------
# CSS mínimo (aparência + botões discretos)
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
/* Botões discretos de editar/excluir */
div[data-testid="column"] button:has(> div > p:contains("✏️")),
div[data-testid="column"] button:has(> div > p:contains("🗑️")) {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    opacity: 0.6;
    transition: opacity 0.2s ease;
    padding: 0 8px !important;
    min-width: 40px !important;
}
div[data-testid="column"] button:has(> div > p:contains("✏️")):hover,
div[data-testid="column"] button:has(> div > p:contains("🗑️")):hover {
    opacity: 1;
    background-color: transparent !important;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# Função para mensagem centralizada (com quebra controlada)
# ------------------------------
def exibir_mensagem_centralizada(mensagem, quebrar_linha=False):
    msg_id = f"msg_{uuid.uuid4().hex}"
    style_base = """
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 12px 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        font-weight: 500;
        font-size: 1rem;
        z-index: 9999;
        text-align: center;
        font-family: inherit;
        animation: fadeOutUp 0.5s ease-in-out 2.5s forwards;
    """
    if quebrar_linha and '<br>' in mensagem:
        partes = mensagem.split('<br>', 1)
        primeira = partes[0].strip()
        segunda = partes[1].strip() if len(partes) > 1 else ''
        conteudo_html = f'<span style="white-space: nowrap;">✅ {primeira}</span>'
        if segunda:
            conteudo_html += f'<br><span>{segunda}</span>'
        style_extra = "white-space: normal; max-width: 80vw; word-wrap: break-word;"
    elif quebrar_linha:
        conteudo_html = f'✅ {mensagem}'
        style_extra = "white-space: normal; max-width: 80vw; word-wrap: break-word;"
    else:
        conteudo_html = f'✅ {mensagem}'
        style_extra = "white-space: nowrap;"

    style_completo = style_base + style_extra
    html = f"""
    <div id="{msg_id}" style="{style_completo}">
        {conteudo_html}
    </div>
    <style>
        @keyframes fadeOutUp {{
            0% {{
                opacity: 1;
                transform: translate(-50%, -50%);
            }}
            100% {{
                opacity: 0;
                transform: translate(-50%, -80%);
                visibility: hidden;
            }}
        }}
    </style>
    <script>
        setTimeout(function() {{
            var el = document.getElementById("{msg_id}");
            if (el) el.remove();
        }}, 3000);
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)

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

# Estado para controle de edição
if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None
if 'edit_data' not in st.session_state:
    st.session_state.edit_data = None

sheet = conectar_planilha()
df_existente = carregar_dados_existentes(sheet)

# ------------------------------
# NOVA SEÇÃO: Consulta de registros existentes
# ------------------------------
st.checkbox("📋 Consultar registros existentes", key="check_consulta")

if st.session_state.check_consulta:
    st.markdown("---")
    camaras = ["Resfriados 1", "Resfriados 2", "Congelados 1", "Congelados 2"]
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

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_camara = st.selectbox("Câmara", ["Todas"] + camaras, key="filtro_camara")
    with col_f2:
        filtro_vaga = st.selectbox("Vaga", ["Todas"] + vagas, key="filtro_vaga")
    filtro_texto = st.text_input("Buscar em marca/descrição", key="filtro_texto")

    df_filtrado = df_existente.copy()
    if filtro_camara != "Todas":
        df_filtrado = df_filtrado[df_filtrado['camara'] == filtro_camara]
    if filtro_vaga != "Todas":
        df_filtrado = df_filtrado[df_filtrado['camara-vaga'] == filtro_vaga]
    if filtro_texto:
        texto = filtro_texto.lower()
        df_filtrado = df_filtrado[
            df_filtrado['produto-marca'].str.lower().str.contains(texto, na=False) |
            df_filtrado['produto-descricao'].str.lower().str.contains(texto, na=False)
        ]

    if filtro_camara != "Todas" and filtro_vaga != "Todas":
        st.write(f"**Registros encontrados para {filtro_camara} / {filtro_vaga}:**")
        if not df_filtrado.empty:
            st.dataframe(df_filtrado[['registro', 'produto-marca', 'produto-descricao', 'validade']], use_container_width=True)
        else:
            st.info("Nenhum registro encontrado para esta combinação.")
    else:
        st.write(f"**Registros encontrados: {len(df_filtrado)}**")
        if not df_filtrado.empty:
            st.dataframe(df_filtrado[['registro', 'camara', 'camara-vaga', 'produto-marca', 'produto-descricao', 'validade']], use_container_width=True)
        else:
            st.info("Nenhum registro corresponde aos filtros.")
    st.markdown("---")

# ------------------------------
# 1. Cadastro de Palete (exibido apenas se NÃO estiver consultando)
# ------------------------------
if not st.session_state.check_consulta:
    st.markdown("## 📦 Cadastro de Palete")
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
                        mensagem_exclusao = f"{num_excluidos} registro(s) excluído(s) com sucesso!<br>A vaga agora está livre."
                        exibir_mensagem_centralizada(mensagem_exclusao, quebrar_linha=True)
                        time.sleep(3)
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

        # --- Formulário de adição/edição de produto ---
        with st.form(key="produto_form", clear_on_submit=False):
            marca_opcoes = [
                "", "Seara", "Seara | Doriana", "Seara | Primor", "Seara | Excelsior",
                "Seara | Macedo", "Seara | Rezende (pizza)", "Lar", "BRF | Perdigão",
                "BRF | Sadia", "BRF | Claybom", "BRF | Qualy", "BRF | Becel",
                "Aurora", "Aurora | Peperi", "Aurora | Nobre", "Outro"
            ]

            # Valores iniciais para os campos (se estiver editando)
            initial_marca = st.session_state.edit_data['produto-marca'] if st.session_state.edit_data else ""
            initial_desc = st.session_state.edit_data['produto-descricao'] if st.session_state.edit_data else ""
            initial_validade = None
            if st.session_state.edit_data:
                try:
                    initial_validade = datetime.strptime(st.session_state.edit_data['validade'], "%d/%m/%Y").date()
                except:
                    initial_validade = None

            marca = st.selectbox("Produto / Marca", marca_opcoes, index=marca_opcoes.index(initial_marca) if initial_marca in marca_opcoes else 0)
            descricao = st.text_input("Descrição do produto (ex.: Peito de frango, 1kg)", value=initial_desc)
            data_validade = st.date_input(
                "Validade",
                value=initial_validade,
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
                    novo_produto = {
                        "produto-marca": marca,
                        "produto-descricao": descricao,
                        "validade": validade_str
                    }

                    # Se estiver em modo edição, remove o produto antigo
                    if st.session_state.edit_index is not None:
                        del st.session_state.produtos_temp[st.session_state.edit_index]
                        st.session_state.edit_index = None
                        st.session_state.edit_data = None

                    st.session_state.produtos_temp.append(novo_produto)
                    # Limpa o formulário forçando rerun (o clear_on_submit não funciona com valores iniciais)
                    st.rerun()

        # --- Lista de produtos temporários com botões de editar/excluir ---
        if st.session_state.produtos_temp:
            st.write("**Produtos neste palete:**")
            for i, p in enumerate(st.session_state.produtos_temp):
                col_desc, col_edit, col_del = st.columns([6, 1, 1])
                with col_desc:
                    st.write(f"{i+1}. {p['produto-marca']} - {p['produto-descricao']} (val.: {p['validade']})")
                with col_edit:
                    if st.button("✏️", key=f"edit_{i}", help="Editar produto"):
                        # Carrega dados para edição e remove da lista temporariamente
                        st.session_state.edit_index = i
                        st.session_state.edit_data = p.copy()
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{i}", help="Excluir produto"):
                        del st.session_state.produtos_temp[i]
                        # Se o produto excluído estava sendo editado, limpa o modo edição
                        if st.session_state.edit_index == i:
                            st.session_state.edit_index = None
                            st.session_state.edit_data = None
                        elif st.session_state.edit_index is not None and st.session_state.edit_index > i:
                            st.session_state.edit_index -= 1
                        st.rerun()

            # Botões de ação global (Finalizar, Cancelar, Adicionar mais)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("➕ Adicionar mais", use_container_width=True, type="secondary"):
                    # Apenas recarrega a página (já está no modo normal)
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
                        exibir_mensagem_centralizada(f"{len(registros_para_gravar)} produto(s) registrado(s) c