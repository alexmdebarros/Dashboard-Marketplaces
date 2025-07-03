import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ─── Conexão com Google Sheets ───────────────────────────────────────────────
SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPES)
gc    = gspread.authorize(creds)
ws    = gc.open_by_key(SHEET_KEY).worksheet("Dados")

# índices das colunas
header      = ws.row_values(1)
IDX_BY      = header.index("Baixado por")   + 1
IDX_DT      = header.index("Data da Baixa") + 1

# ─── Carrega e transforma ─────────────────────────────────────────────────────
@st.cache_data
def load_data():
    raw = pd.DataFrame(ws.get_all_values()[1:], columns=ws.get_all_values()[0])
    df = pd.DataFrame({
        "Data":          pd.to_datetime(raw["Data"], dayfirst=True, errors="coerce"),
        "Marketplace":   raw["Marketplace"],
        "Valor_raw":     raw["Valor"].str.replace(".", "", regex=False)
                                   .str.replace(",", ".", regex=False).astype(float),
        "Banco / Conta": raw["Banco / Conta"],
        "Data da Baixa": pd.to_datetime(raw["Data da Baixa"], dayfirst=True, errors="coerce"),
        "Baixado por":   raw["Baixado por"].fillna(""),
    })
    df["Valor"] = df["Valor_raw"].map(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df["Data_str"]      = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"].dt.strftime("%d/%m/%Y %H:%M:%S").fillna("")
    return df

df = load_data()

# ─── Filtros ─────────────────────────────────────────────────────────────────
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

# ─── KPIs ────────────────────────────────────────────────────────────────────
total  = df_f["Valor_raw"].sum()
count  = len(df_f)
ticket = total / count if count else 0.0
c1, c2, c3 = st.columns(3, gap="large")
c1.metric("💰 Total Recebido", f"R$ {total:,.2f}")
c2.metric("📝 Lançamentos",    f"{count}")
c3.metric("🎯 Ticket Médio",    f"R$ {ticket:,.2f}")

# ─── Prepara tabela para edição ──────────────────────────────────────────────
# mantemos o índice original p/ referenciar a linha no Sheets
df_edit = df_f.reset_index().rename(columns={"index":"_orig_index"})
df_edit["row_number"]    = df_edit["_orig_index"] + 2
df_edit["Data"]          = df_edit["Data_str"]
df_edit["Data da Baixa"] = df_edit["DataBaixa_str"]

# só as colunas que queremos mostrar/editar
display_df = df_edit[[
    "row_number","Data","Marketplace","Valor",
    "Banco / Conta","Baixado por","Data da Baixa"
]].set_index("row_number", drop=False)

# ─── Experimental Data Editor ────────────────────────────────────────────────
edited = st.experimental_data_editor(
    display_df,
    num_rows="fixed",
    use_container_width=True
)

# ─── Detecta mudanças em “Baixado por” ────────────────────────────────────────
mask = edited["Baixado por"] != display_df["Baixado por"]
if mask.any():
    if st.button("💾 Salvar alterações"):
        # prepara batch de Cells
        cells = []
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        for rn in edited.index[mask]:
            new_usr = str(edited.at[rn, "Baixado por"]).strip()
            # célula do “Baixado por”
            cells.append(gspread.Cell(rn, IDX_BY, new_usr))
            # célula do timestamp
            ts = now if new_usr else ""
            cells.append(gspread.Cell(rn, IDX_DT, ts))

        # UM único request ao Sheets
        ws.update_cells(cells)

        st.success("Alterações salvas com sucesso!")
        # limpa cache e recarrega
        load_data.clear()
        st.experimental_rerun()
