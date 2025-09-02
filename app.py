import streamlit as st
import pandas as pd
import gspread
from gspread import Cell
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz

# ─── BLOQUEIO POR SENHA ────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    with st.sidebar:
        senha = st.text_input("🔒 Senha de acesso", type="password")
        if senha == "fa@maringa":
            st.session_state.authenticated = True
            st.rerun()
        elif senha:
            st.error("Senha incorreta")
    st.stop()

# ─── 0) Injeta locale pt-BR ──────────────────────────────────────────────
st.markdown(
    """
    <script>
      document.documentElement.lang = 'pt-BR';
      document.documentElement.setAttribute('translate', 'no');
      var metaNotrans = document.createElement('meta');
      metaNotrans.name = 'google';
      metaNotrans.content = 'notranslate';
      document.head.appendChild(metaNotrans);
      var metaLang = document.createElement('meta');
      metaLang.httpEquiv = 'Content-Language';
      metaLang.content = 'pt-BR';
      document.head.appendChild(metaLang);
    </script>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/pt.js"></script>
    <script>
      if (window.flatpickr) {
        window.flatpickr.localize(window.flatpickr.l10ns.pt);
      }
    </script>
    """,
    unsafe_allow_html=True
)

# ─── 1) Configuração da página ────────────────────────────────────────────
st.set_page_config(page_title="Recebimentos de Marketplaces", layout="wide")

# ─── 2) Título ────────────────────────────────────────────────────────────
st.markdown("<h1>📊 Recebimentos de Marketplaces</h1>", unsafe_allow_html=True)

# ─── 3) Conexão com o Google Sheets ───────────────────────────────────────
SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ===== MUDANÇA AQUI: Lendo o arquivo creds.json diretamente =====
creds = Credentials.from_service_account_file("creds.json", scopes=SCOPES)
# ================================================================

gc = gspread.authorize(creds)
ws = gc.open_by_key(SHEET_KEY).worksheet("Dados")
header = ws.row_values(1)
IDX_BY = header.index("Baixado por") + 1
IDX_DT = header.index("Data da Baixa") + 1


# ─── 4) Carregamento e tratamento dos dados ───────────────────────────────
@st.cache_data(ttl=600)
def load_data():
    all_values = ws.get_all_values()
    header = all_values[0]
    data = all_values[1:]
    
    raw = pd.DataFrame(data, columns=header)
    
    if "Data da Baixa" not in raw.columns:
        raw["Data da Baixa"] = None
    if "Baixado por" not in raw.columns:
        raw["Baixado por"] = ""

    df = pd.DataFrame({
        "Data":           pd.to_datetime(raw["Data"], dayfirst=True, errors="coerce"),
        "Marketplace":    raw["Marketplace"],
        "Valor_raw":      raw["Valor"]
                            .str.replace(".", "", regex=False)
                            .str.replace(",", ".", regex=False)
                            .astype(float),
        "Banco / Conta":  raw["Banco / Conta"],
        "Data da Baixa":  pd.to_datetime(raw["Data da Baixa"], dayfirst=True, errors="coerce"),
        "Baixado por":    raw["Baixado por"].fillna(""),
    })
    df["Valor"] = df["Valor_raw"].map(
        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    df["Data_str"] = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"].apply(lambda x: x.strftime("%d/%m/%Y %H:%M:%S") if pd.notnull(x) else "")
    return df

df = load_data()

# ─── 5) Filtros na Sidebar ────────────────────────────────────────────────
with st.sidebar:
    if st.button("🔄 Atualizar dados agora"):
        st.cache_data.clear()
        st.rerun()
    st.header("Filtros")
    if not df.empty and not df["Data"].dropna().empty:
        mn = df["Data"].min().date()
        mx = df["Data"].max().date()
        start = st.date_input("Data Início", mn, min_value=mn, max_value=mx, format="DD/MM/YYYY")
        end = st.date_input("Data Fim", mx, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    else:
        st.warning("Não há dados de data para filtrar.")
        st.stop()
        
    status = st.radio("Status de Baixa", ["Todos", "Baixados", "Pendentes"])
    mp_sel = st.multiselect("Marketplace", sorted(df["Marketplace"].unique()))
    conta_sel = st.multiselect("Banco / Conta", sorted(df["Banco / Conta"].unique()))
    by_sel = st.multiselect("Baixado por", sorted(df["Baixado por"].unique()))

# ─── 6) Aplicação dos Filtros ─────────────────────────────────────────────
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

# ─── 7) KPI Cards ─────────────────────────────────────────────────────────
def fmt_ptbr(valor: float) -> str:
    s = f"{valor:,.2f}"
    inteiro, dec = s.split('.')
    inteiro = inteiro.replace(',', '.')
    return f"{inteiro},{dec}"

total = df_f["Valor_raw"].sum()
count = len(df_f)
ticket = total / count if count else 0.0

if count > 0:
    porcent_b = len(df_f[df_f["Baixado por"] != ""]) / count * 100
    porcent_n = len(df_f[df_f["Baixado por"] == ""]) / count * 100
else:
    porcent_b = 0
    porcent_n = 0

baixados = df_f[df_f["Data da Baixa"].notna()]
if not baixados.empty:
    baixados = baixados.copy() 
    baixados["Dias para Baixa"] = (baixados["Data da Baixa"] - baixados["Data"]).dt.days
    media_dias = baixados["Dias para Baixa"].mean()
else:
    media_dias = None

c1, c2, c3, c4, c5 = st.columns(5, gap="small")
c1.metric("💰 Total Recebido", f"R$ {fmt_ptbr(total)}")
c2.metric("📝 Lançamentos", f"{count}")
c3.metric("✅ Baixados(%)", f"{porcent_b:.2f}%" if count > 0 else "-")
c4.metric("❌ Pendentes(%)", f"{porcent_n:.2f}%" if count > 0 else "-")
c5.metric("⏱️ Tempo Médio Baixa", f"{media_dias:.1f} dias" if media_dias is not None else "-")

# ─── 8) Editor de dados ────────────────────────────────────────────────────
df_edit = df_f.reset_index().rename(columns={"index": "_orig_index"})
df_edit["row_number"] = df_edit["_orig_index"] + 2
df_edit["Data"] = df_edit["Data_str"]
df_edit["Data da Baixa"] = df_edit["DataBaixa_str"]

display_df = df_edit[[
    "row_number", "Data", "Marketplace", "Valor",
    "Banco / Conta", "Baixado por", "Data da Baixa"
]].set_index("row_number", drop=False)

edited = st.data_editor(
    display_df,
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "Data": st.column_config.TextColumn("Data", disabled=True),
        "Marketplace": st.column_config.TextColumn("Marketplace", disabled=True),
        "Valor": st.column_config.TextColumn("Valor", disabled=True),
        "Banco / Conta": st.column_config.TextColumn("Banco / Conta", disabled=True),
        "Data da Baixa": st.column_config.TextColumn("Data da Baixa", disabled=True),
        "Baixado por": st.column_config.TextColumn("Baixado por", required=False, max_chars=50),
        "row_number": None,
    }
)

# Protege coluna da baixa (impede que qualquer alteração seja salva)
edited["Data da Baixa"] = display_df["Data da Baixa"]

# Detecta mudanças em 'Baixado por'
mask = edited["Baixado por"].fillna("").astype(str).str.strip() != \
       display_df["Baixado por"].fillna("").astype(str).str.strip()

if mask.any():
    if st.button("💾 Salvar alterações"):
        cells = []
        tz = pytz.timezone("America/Sao_Paulo")
        now = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
        for rn in edited.index[mask]:
            raw_value = edited.at[rn, "Baixado por"]
            new_usr = str(raw_value).strip() if pd.notna(raw_value) else ""
            cells.append(Cell(row=rn, col=IDX_BY, value=new_usr))
            cells.append(Cell(row=rn, col=IDX_DT, value="" if new_usr == "" else now))
        
        if cells:
            ws.update_cells(cells, value_input_option='USER_ENTERED')
            st.success("✅ Alterações salvas com sucesso!")
            st.cache_data.clear() 
            st.rerun()