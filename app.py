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
    unsafe_allow_html=True,
)

# ─── 1) Configurações da página ────────────────────────────────────────────────
st.set_page_config(
    page_title="Recebimentos de Marketplaces",
    layout="wide",
)

# ─── 2) Cabeçalho ─────────────────────────────────────────────────────────────
st.markdown(
    "<h1>📊 Recebimentos de Marketplaces</h1>"
    "<h3 style='margin-top:0;'>Visualize e gerencie suas receitas</h3>",
    unsafe_allow_html=True
)

# ─── 3) Conexão com Google Sheets ────────────────────────────────────────────
SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["google_service_account"], scopes=SCOPES
)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SHEET_KEY).worksheet("Dados")
header = ws.row_values(1)
col_idx_dt = header.index("Data da Baixa") + 1
col_idx_by = header.index("Baixado por") + 1

# ─── 4) Carrega e trata dados ─────────────────────────────────────────────────
@st.cache_data
def load_data():
    raw = pd.DataFrame(ws.get_all_values()[1:], columns=ws.get_all_values()[0])
    df = pd.DataFrame({
        "Data":          pd.to_datetime(raw["Data"], dayfirst=True, errors="coerce"),
        "Marketplace":   raw["Marketplace"],
        "Valor_raw":     raw["Valor"]
                             .str.replace(".", "", regex=False)
                             .str.replace(",", ".", regex=False)
                             .astype(float),
        "Banco / Conta": raw["Banco / Conta"],
        "Data da Baixa": pd.to_datetime(raw["Data da Baixa"], dayfirst=True, errors="coerce"),
        "Baixado por":   raw["Baixado por"].fillna(""),
    })
    df["Valor"] = df["Valor_raw"].map(
        lambda x: f"R$ {x:,.2f}"
                  .replace(",", "X")
                  .replace(".", ",")
                  .replace("X", ".")
    )
    df["Data_str"]      = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"]\
                              .dt.strftime("%d/%m/%Y %H:%M:%S")\
                              .fillna("")
    return df

df = load_data()

# ─── 5) Filtros na sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    mn    = df["Data"].min().date()
    mx    = df["Data"].max().date()
    start = st.date_input("Data Início", mn, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    end   = st.date_input("Data Fim",    mx, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    status    = st.radio("Status de Baixa", ["Todos", "Baixados", "Pendentes"])
    mp_sel    = st.multiselect("Marketplace",   sorted(df["Marketplace"].unique()))
    conta_sel = st.multiselect("Banco / Conta", sorted(df["Banco / Conta"].unique()))
    by_sel    = st.multiselect("Baixado por",   sorted(df["Baixado por"].unique()))

# ─── 6) Aplica filtros ───────────────────────────────────────────────────────
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

# ─── 7) Exibe KPIs ───────────────────────────────────────────────────────────
total  = df_f["Valor_raw"].sum()
count  = len(df_f)
ticket = total / count if count else 0.0
c1, c2, c3 = st.columns(3, gap="large")
c1.metric("💰 Total Recebido", f"R$ {total:,.2f}")
c2.metric("📝 Lançamentos",    f"{count}")
c3.metric("🎯 Ticket Médio",    f"R$ {ticket:,.2f}")

# ─── 8) Prepara tabela editável + botão Salvar condicional ──────────────────
df_t = df_f.reset_index().rename(columns={"index": "_orig_index"})
df_t["row_number"]     = df_t["_orig_index"] + 2
df_t["Data"]           = df_t["Data_str"]
df_t["Data da Baixa"]  = df_t["DataBaixa_str"]

grid_df = df_t[[
    "row_number", "Data", "Marketplace", "Valor",
    "Banco / Conta", "Baixado por", "Data da Baixa"
]]

# Construímos um mapa original garantindo string
orig_map = {
    int(row["row_number"]): str(row.get("Baixado por") or "").strip()
    for row in grid_df.to_dict(orient="records")
}

gb = GridOptionsBuilder.from_dataframe(grid_df)
gb.configure_default_column(resizable=True, wrapText=True, autoHeight=True)
gb.configure_column("Baixado por", editable=True)
gb.configure_column("row_number", hide=True)
grid_opts = gb.build()

col1, col2 = st.columns([8, 1], gap="small")
with col1:
    grid_resp = AgGrid(
        grid_df,
        gridOptions=grid_opts,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        fit_columns_on_grid_load=True,
        height=400,
        width="100%",
        theme="streamlit",
    )

# Reconstruímos o mapa atual também convertendo sempre para string
curr_map = {
    int(row["row_number"]): str(row.get("Baixado por") or "").strip()
    for row in grid_resp["data"]
}

# Se qualquer valor mudou, mostramos o botão
edited = any(curr_map[rn] != orig_map.get(rn, "") for rn in curr_map)

with col2:
    if edited:
        if st.button("💾 Salvar alterações"):
            for rn, new_usr in curr_map.items():
                old_usr = orig_map.get(rn, "")
                if new_usr != old_usr:
                    ws.update_cell(rn, col_idx_by, new_usr)
                    if new_usr:
                        ws.update_cell(
                            rn,
                            col_idx_dt,
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        )
                    else:
                        ws.update_cell(rn, col_idx_dt, "")
            st.success("Alterações salvas com sucesso!")
            st.experimental_rerun()
