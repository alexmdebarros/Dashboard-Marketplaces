import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
    unsafe_allow_html=True
)

# ─── 1) Configuração da página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Recebimentos de Marketplaces",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    "<h1>📊 Recebimentos de Marketplaces</h1>"
    "<h3>Visualize e gerencie suas receitas</h3>",
    unsafe_allow_html=True
)

# ─── 2) Conexão com Google Sheets ───────────────────────────────────────────
SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES    = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
creds     = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPES
)
gc     = gspread.authorize(creds)
ws     = gc.open_by_key(SHEET_KEY).worksheet("Dados")
header = ws.row_values(1)
idx_dt = header.index("Data da Baixa") + 1
idx_by = header.index("Baixado por")   + 1

# ─── 3) Parser de Valor e carga de dados ─────────────────────────────────────
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

@st.cache_data
def load_data():
    raw_vals = ws.get_all_values()
    df_raw = pd.DataFrame(raw_vals[1:], columns=raw_vals[0])
    df = pd.DataFrame({
        "Data":          pd.to_datetime(df_raw["Data"], dayfirst=True, errors="coerce"),
        "Marketplace":   df_raw["Marketplace"],
        "Valor_raw":     df_raw["Valor"].apply(parse_val),
        "Banco / Conta": df_raw["Banco / Conta"],
        "Data da Baixa": pd.to_datetime(df_raw["Data da Baixa"], dayfirst=True, errors="coerce"),
        "Baixado por":   df_raw["Baixado por"].fillna(""),
    })
    df["Valor"] = df["Valor_raw"].map(
        lambda x: f"R$ {x:,.2f}"
                  .replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df["Data_str"]      = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"]\
                             .dt.strftime("%d/%m/%Y %H:%M:%S")\
                             .fillna("")
    return df

df = load_data()

# ─── 4) Estilos dos KPI cards ────────────────────────────────────────────────
st.markdown("""
<style>
.kpi-card {
  background: #fff;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  text-align: center;
}
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.kpi-label { font-size: 0.9rem; color: #555; margin-bottom: 0.4rem; }
.kpi-value { font-size: 1.6rem; font-weight: 600; color: #111; }
.kpi-total  { border: 2px solid #1E90FF !important; }
.kpi-count  { border: 2px solid #2ECC71 !important; }
.kpi-ticket { border: 2px solid #9B59B6 !important; }
</style>
""", unsafe_allow_html=True)

# ─── 5) Sidebar com filtros ──────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")

    with st.expander("📅 Período de Recebimento", expanded=True):
        mn = df["Data"].min().date()
        mx = df["Data"].max().date()
        dt0 = st.date_input("Início", mn, min_value=mn, max_value=mx, format="DD/MM/YYYY")
        dt1 = st.date_input("Fim",    mx, min_value=mn, max_value=mx, format="DD/MM/YYYY")

    with st.expander("🔍 Status de Baixa", expanded=True):
        status = st.radio("Status", ["Todos", "Baixados", "Pendentes"])

    with st.expander("🛒 Marketplaces"):
        mp_sel = st.multiselect("Selecione", sorted(df["Marketplace"].unique()))

    with st.expander("🏦 Contas"):
        conta_sel = st.multiselect("Selecione", sorted(df["Banco / Conta"].unique()))

    with st.expander("✅ Baixado por"):
        by_sel = st.multiselect("Selecione", sorted(df["Baixado por"].unique()))

# ─── 6) Aplica filtros ──────────────────────────────────────────────────────
df_f = df[(df["Data"].dt.date >= dt0) & (df["Data"].dt.date <= dt1)]
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

# ─── 7) Renderiza KPIs ───────────────────────────────────────────────────────
tot, cnt = df_f["Valor_raw"].sum(), len(df_f)
tick     = tot / cnt if cnt else 0.0

c1, c2, c3 = st.columns(3, gap="large")
for col, (lbl, val, cls) in zip((c1, c2, c3), [
    ("Total Recebido", tot,  "kpi-total"),
    ("Lançamentos",    cnt,  "kpi-count"),
    ("Ticket Médio",   tick, "kpi-ticket")
]):
    disp = str(val) if lbl == "Lançamentos" else f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    with col:
        st.markdown(
            f"<div class='kpi-card {cls}'>"
            f"<div class='kpi-label'>{lbl}</div>"
            f"<div class='kpi-value'>{disp}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

# ─── 8) Prepara e exibe AgGrid ─────────────────────────────────────────────
df_t = df_f.copy()
df_t["Data"]          = df_t["Data_str"]
df_t["Data da Baixa"] = df_t["DataBaixa_str"]
df_t = df_t[["Data","Marketplace","Valor","Banco / Conta","Baixado por","Data da Baixa"]] \
       .reset_index().rename(columns={"index":"_orig_index"})

gb = GridOptionsBuilder.from_dataframe(df_t)
gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
gb.configure_column("_orig_index", hide=True)
gb.configure_column("Baixado por", editable=True)
opts = gb.build()

grid = AgGrid(
    df_t, gridOptions=opts, update_mode=GridUpdateMode.VALUE_CHANGED,
    height=600, fit_columns_on_grid_load=True, width="100%", theme="streamlit"
)

# ─── 9) Auto‐save ────────────────────────────────────────────────────────────
upd = pd.DataFrame(grid["data"])
for _, r in upd.iterrows():
    i    = int(r["_orig_index"])
    orig = df.loc[i, "Baixado por"]
    raw  = r.get("Baixado por")
    new  = "" if pd.isna(raw) or raw is None else str(raw).strip()
    if new != orig:
        row_num = i + 2
        ws.update_cell(row_num, idx_by, new)
        if new:
            ws.update_cell(row_num, idx_dt, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        else:
            ws.update_cell(row_num, idx_dt, "")
        st.experimental_rerun()
