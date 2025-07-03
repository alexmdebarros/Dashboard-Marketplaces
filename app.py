import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, GridSelectionMode

# ─── 0) Injeta locale flatpickr pt-BR ─────────────────────────────────────────
st.markdown(
    """
    <script>document.documentElement.lang = 'pt-BR';</script>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/pt.js"></script>
    <script>
      if (window.flatpickr) {
        window.flatpickr.localize(window.flatpickr.l10ns.pt);
      }
    </script>
    """,
    unsafe_allow_html=True,
)

# ─── 1) Configuração da página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Recebimentos de Marketplaces",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── 2) Cabeçalho ─────────────────────────────────────────────────────────────
st.markdown(
    "<h1>📊 Recebimentos de Marketplaces</h1>"
    "<h3 style='margin-top:0;'>Visualize e gerencie suas receitas</h3>",
    unsafe_allow_html=True
)

# ─── 3) Conexão com Google Sheets ────────────────────────────────────────────
SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES    = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
creds     = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
gc        = gspread.authorize(creds)
ws        = gc.open_by_key(SHEET_KEY).worksheet("Dados")
header    = ws.row_values(1)
col_idx_dt = header.index("Data da Baixa") + 1
col_idx_by = header.index("Baixado por")   + 1

# ─── 4) Função para ler e tratar dados ────────────────────────────────────────
@st.cache_data
def load_data():
    all_vals = ws.get_all_values()
    df_raw   = pd.DataFrame(all_vals[1:], columns=all_vals[0])
    df = pd.DataFrame({
        "Data":          pd.to_datetime(df_raw["Data"], dayfirst=True, errors="coerce"),
        "Marketplace":   df_raw["Marketplace"],
        "Valor_raw":     df_raw["Valor"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float),
        "Banco / Conta": df_raw["Banco / Conta"],
        "Data da Baixa": pd.to_datetime(df_raw["Data da Baixa"], dayfirst=True, errors="coerce"),
        "Baixado por":   df_raw["Baixado por"].fillna(""),
    })
    df["Valor"] = df["Valor_raw"].map(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df["Data_str"]      = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"].dt.strftime("%d/%m/%Y %H:%M:%S").fillna("")
    return df

df = load_data()

# ─── 5) Filtros na sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    mn = df["Data"].min().date()
    mx = df["Data"].max().date()
    start = st.date_input("Data Início", mn, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    end   = st.date_input("Data Fim",    mx, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    status = st.radio("Status de Baixa", ["Todos", "Baixados", "Pendentes"])
    mp_sel = st.multiselect("Marketplace",   sorted(df["Marketplace"].unique()))
    conta_sel = st.multiselect("Banco / Conta", sorted(df["Banco / Conta"].unique()))
    by_sel = st.multiselect("Baixado por", sorted(df["Baixado por"].unique()))

# ─── 6) Aplica filtros ────────────────────────────────────────────────────────
df_f = df[(df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)]
if status == "Baixados":
    df_f = df_f[df_f["Baixado por"] != ""]
elif status == "Pendentes":
    df_f = df_f[df_f["Baixado por"] == ""]
if mp_sel:
    df_f = df_f[df_f["Marketplace"].isin(mp_sel)]
if conta_sel:
    df_f = df_f[df_f["Banco / Conta"].isin(conta_sel)]
if by_sel:
    df_f = df_f[df_f["Baixado por"].isin(by_sel)]

# ─── 7) Exibe KPIs lado a lado ───────────────────────────────────────────────
total  = df_f["Valor_raw"].sum()
count  = len(df_f)
ticket = total / count if count else 0.0
c1, c2, c3 = st.columns(3, gap="large")
c1.metric("💰 Total Recebido", f"R$ {total:,.2f}")
c2.metric("📝 Lançamentos",    f"{count}")
c3.metric("🎯 Ticket Médio",    f"R$ {ticket:,.2f}")

# ─── 8) Tabela com seleção ───────────────────────────────────────────────────
df_t = df_f.reset_index().rename(columns={"index":"_orig_index"})
df_t["row_number"] = df_t["_orig_index"] + 2
df_t["Data"]          = df_t["Data_str"]
df_t["Data da Baixa"] = df_t["DataBaixa_str"]
df_display = df_t[[
    "row_number","Data","Marketplace","Valor",
    "Banco / Conta","Baixado por","Data da Baixa"
]]

gb = GridOptionsBuilder.from_dataframe(df_display)
gb.configure_selection(selection_mode=GridSelectionMode.SINGLE, use_checkbox=True)
gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
gb.configure_column("row_number", hide=True)
opts = gb.build()

grid_resp = AgGrid(
    df_display,
    gridOptions=opts,
    update_mode=GridUpdateMode.NO_UPDATE,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    fit_columns_on_grid_load=True,
    height=400,
    width="100%",
    theme="streamlit"
)

# ─── 9) Formulário de edição ─────────────────────────────────────────────────
selected = grid_resp["selected_rows"]
if selected:
    sel = selected[0]
    rn = int(sel["row_number"])
    st.markdown("### ✏️ Editar lançamento selecionado")
    colA, colB = st.columns([2, 1])
    with colA:
        st.write(f"**Data:** {sel['Data']}")
        st.write(f"**Marketplace:** {sel['Marketplace']}")
        st.write(f"**Valor:** {sel['Valor']}")
        st.write(f"**Banco / Conta:** {sel['Banco / Conta']}")
        novo = st.text_input("Baixado por", value=sel["Baixado por"])
    with colB:
        if st.button("💾 Salvar alterações"):
            ws.update_cell(rn, col_idx_by, novo)
            ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S") if novo else ""
            ws.update_cell(rn, col_idx_dt, ts)
            st.success("Salvo com sucesso!")
            st.experimental_rerun()
