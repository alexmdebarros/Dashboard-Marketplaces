import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# 0) Injeta script para definir idioma como pt-BR e evitar prompt de tradução
st.markdown(
    """
    <script>
      document.documentElement.lang = 'pt-BR';
    </script>
    """,
    unsafe_allow_html=True,
)

# 1) Configuração da página
st.set_page_config(
    page_title="Recebimentos de Marketplaces",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal e subtítulo
st.markdown(
    "<h1 style='margin-bottom:0.1rem;'>📊 Recebimentos de Marketplaces</h1>"
    "<h3 style='margin-top:0;'>Visualize e gerencie suas receitas</h3>",
    unsafe_allow_html=True
)

# --- 2) Conexão com Google Sheets ---
SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES    = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
creds     = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPES
)
gc        = gspread.authorize(creds)
ws        = gc.open_by_key(SHEET_KEY).worksheet("Dados")
header    = ws.row_values(1)
col_idx_dt_baixa = header.index("Data da Baixa") + 1
col_idx_baixado  = header.index("Baixado por")   + 1

# --- 3) Parser robusto para Valor ---
def parse_val(v):
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except:
        return 0.0

# --- 4) Carrega e trata os dados (cache) ---
@st.cache_data
def load_data():
    vals   = ws.get_all_values()
    df_raw = pd.DataFrame(vals[1:], columns=vals[0])
    df = pd.DataFrame({
        "Data":          pd.to_datetime(df_raw["Data"], dayfirst=True, errors="coerce"),
        "Marketplace":   df_raw["Marketplace"],
        "Valor_raw":     df_raw["Valor"].apply(parse_val),
        "Banco / Conta": df_raw["Banco / Conta"],
        "Data da Baixa": pd.to_datetime(df_raw["Data da Baixa"], dayfirst=True, errors="coerce"),
        "Baixado por":   df_raw["Baixado por"].fillna(""),
    })
    df["Valor"]         = df["Valor_raw"].map(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df["Data_str"]      = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"].dt.strftime("%d/%m/%Y %H:%M:%S").fillna("")
    return df

df = load_data()

# --- 5) CSS para KPI cards coloridos e lado a lado ---
st.markdown("""
<style>
.kpi-container {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.5rem 0;
}
.kpi-card {
  flex: 1;
  background: #ffffff;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  text-align: center;
}
.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.kpi-label { font-size: 0.85rem; color: #555; margin-bottom: 0.4rem; }
.kpi-value { font-size: 1.6rem; font-weight: 600; color: #111; }
/* contornos coloridos */
.kpi-total  { border: 2px solid #1E90FF !important; }
.kpi-count  { border: 2px solid #2ECC71 !important; }
.kpi-ticket { border: 2px solid #9B59B6 !important; }
</style>
""", unsafe_allow_html=True)

# --- 6) Sidebar com filtros em expanders ---
with st.sidebar:
    st.header("Filtros")
    with st.expander("📅 Período de Recebimento", expanded=True):
        min_date = df["Data"].min().date()
        max_date = df["Data"].max().date()
        data_start = st.date_input("Data Início", min_value=min_date, max_value=max_date, value=min_date)
        data_end   = st.date_input("Data Fim",    min_value=min_date, max_value=max_date, value=max_date)
    with st.expander("🔍 Status de Baixa", expanded=True):
        status = st.radio("Status", ["Todos", "Baixados", "Pendentes"])
    with st.expander("🛒 Marketplaces"):
        mp_sel = st.multiselect("Selecione", sorted(df["Marketplace"].unique()))
    with st.expander("🏦 Contas"):
        conta_sel = st.multiselect("Selecione", sorted(df["Banco / Conta"].unique()))
    with st.expander("✅ Baixado por"):
        baixado_sel = st.multiselect("Selecione", sorted(df["Baixado por"].unique()))

# --- 7) Aplica filtros ---
df_f = df[
    (df["Data"].dt.date >= data_start) &
    (df["Data"].dt.date <= data_end)
]
if status == "Baixados":
    df_f = df_f[df_f["Baixado por"] != ""]
elif status == "Pendentes":
    df_f = df_f[df_f["Baixado por"] == ""]
if mp_sel:
    df_f = df_f[df_f["Marketplace"].isin(mp_sel)]
if conta_sel:
    df_f = df_f[df_f["Banco / Conta"].isin(conta_sel)]
if baixado_sel:
    df_f = df_f[df_f["Baixado por"].isin(baixado_sel)]

# --- 8) Exibe os KPI cards ---
total, count = df_f["Valor_raw"].sum(), len(df_f)
ticket = total / count if count else 0.0

st.markdown("<div class='kpi-container'>", unsafe_allow_html=True)
for lbl, val, cls in [
    ("Total Recebido", total,  "kpi-total"),
    ("Lançamentos",    count,  "kpi-count"),
    ("Ticket Médio",   ticket, "kpi-ticket"),
]:
    txt = f"{val}" if lbl=="Lançamentos" else f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    st.markdown(f"""
      <div class='kpi-card {cls}'>
        <div class='kpi-label'>{lbl}</div>
        <div class='kpi-value'>{txt}</div>
      </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# --- 9) Prepara e exibe a tabela com AgGrid ---
df_t = df_f.copy()
df_t["Data"]          = df_t["Data_str"]
df_t["Data da Baixa"] = df_t["DataBaixa_str"]
df_t = df_t[[
    "Data","Marketplace","Valor","Banco / Conta",
    "Baixado por","Data da Baixa"
]].reset_index().rename(columns={"index":"_orig_index"})

gb = GridOptionsBuilder.from_dataframe(df_t)
gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
gb.configure_column("_orig_index", hide=True)
gb.configure_column("Baixado por", editable=True)
opts = gb.build()

grid = AgGrid(
    df_t, gridOptions=opts,
    update_mode=GridUpdateMode.VALUE_CHANGED,
    height=600, fit_columns_on_grid_load=True,
    width="100%", theme="streamlit"
)

# --- 10) Auto‐save ao editar 'Baixado por' ---
df_up = pd.DataFrame(grid["data"])
for _, row in df_up.iterrows():
    idx     = int(row["_orig_index"])
    orig_usr= df.loc[idx, "Baixado por"]
    raw_usr = row.get("Baixado por")
    new_usr = "" if pd.isna(raw_usr) or raw_usr is None else str(raw_usr).strip()
    if new_usr != orig_usr:
        r = idx + 2
        ws.update_cell(r, col_idx_baixado, new_usr)
        if new_usr:
            ws.update_cell(r, col_idx_dt_baixa, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        else:
            ws.update_cell(r, col_idx_dt_baixa, "")
        st.experimental_rerun()
