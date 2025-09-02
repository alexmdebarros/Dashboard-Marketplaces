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

SHEET_KEY = "19UwqUZlIZJ_kZVf1hTZw1_Nds2nYnu6Hx8igOQVsDfk"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ==================== INÍCIO DO TESTE DE EMERGÊNCIA ====================
# AVISO: APAGUE ESTE BLOCO DEPOIS DO TESTE! NÃO DEIXE CREDENCIAIS NO CÓDIGO!

creds_info = {
    "type": "service_account",
    "project_id": "dashboard-receb-marketplaces",
    "private_key_id": "895def82184723e839915e52903074cbc8402b37",
    "private_key": """-----BEGIN PRIVATE KEY-----
    MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDFw8854N0f0P8i
    zLsOxpEIDJoybh2E4nCOZtC2H3vviostdpeS3yMWAt3o2BrROopkx6jHBtAMzEL0
    tynlUF4ZJlp3D3nQDPT4ifjLa4rVghi+4kTNZJgJ6PH8gXEDM5zImaxlhfpdudXq
    lGtoPUDVdXS359xUyNR/sXCoEiBIvmFVBBKHZqvZvvMp9NNj5JAFsKKuJNBXMMU
    7b3mWl8YteI6zg+y+uOzdmDxXEogp7JKq8igobMSefhYpqUKdQVPudEgZOL5wf3N
    9fmuh7E0RBgNi4VWyTsnqjaoYu+iIgUnMgK1ZVBzO4IqkmDzXLk5/Df5Q3p8Jt5E
    wo02PJyLAgMBAAECggEAEqTvq+q1nhLDguHfPrjconAht2BnOwhoCRzLT2gvdHlQ
    vrP//TI5KhGSHyoEeTY2JuMl18GeKp61L0H3Wq2VeXSCsdfNKZ6XF7lWMcNNPuy5
    bYGCcASsSr7h1WbUozMh9E18kcOsQ1rKPofIina/3n/oxY+/12RpmDI/xzCSR5k0
    swEL+BRvFCI72Yw7+8kcQZ2+StUFKHpXC5AfpaFjrPiF2KC9NBzy5tkqKmz590JA
    8T0waM94zkEudgXHJA16kmPLn9CvvtdtEOh0064FGeA3ZxZ2AN/j9ljsWpIJEcwD
    t+zuZvEwXuA58v3aBn+KvuEcLPb2Q6QwdMLjEypXFQKBgQDtHj0/dbJ9wXi+KnIf
    VOQJzIiL1z/7Mh0Q892N53zpEt9o9wz+pt2NCS2KAruu1yd6ldml1y4BQTc9fYk6
    AUxjlNbFqCJjB8SL4VBVaTixeno0nqVCGKEOhkJpHP4q7bxDYg/uzzSoRwH4HUjA
    B9YgWddWfRAq9fRce2LTWGU+TQKBgQDVg1YlVMTPKq3AVDgJuPs6sLubwWaSEor6
    /q/NpDS6pLACgjER1zfAiZcg6Kes8u+lYefsjMGLVikn/BDWC843tLKw1As+uhvx
    vAX3TID06nCQ3QQXZEfWMHYMQVBwb1LSKOEYe543WGOvVV7M+HiaZCNYcGghJ8Aa
    iP3y1g4iNwKBgBzvDLA6r24S9qXVzhkupajgcWUG/gKr6coQx98x+RcDu4k2ZDqK
    qAw2q3zkunwqOuIFeQp4iF+U0qXJNL6EPAsGtXJnAtMstnoPI1tYvJdDh7f2B9pZ
    4QVBssbax9T7L3bVd3Y/iIBkMcRR5newPRuzeshN+HQVkRzb3YJGjgwdAoGAShnX
    1wLxfxjHzp0sCavKfVcC9Y6Mo5uN4ohryUn5BuHLOEOo9hEkh0z5R3GXZ/20UEiH
    bmB3d31CsV7ZFQBp5IlxDs+4y19Z/W6M/4PsqZOH167tEZU7HUoaXix411y7eLa5
    UH7urTSe/CX7zdVaPfMNFU+FxCQAlvT+db32j8cCgYANUZeAQyeaNs07osa5jNuy
    KYidO5sMc0HRQyNpN+ZsWl0EGrvM93MKfsIG2qaovKs6zugFHxGMnGRGYUwIYMc9
    OaLw0r6WTVMqSlXrNyQ0GVaQfuV87GnZwXRAA6g28BRLJvLl0OauRv7xBoz+yoNv
    uS4bSrv4YZDkjfgfCrj3IQ==
    -----END PRIVATE KEY-----
    """,
    "client_email": "streamlit-dashboard@dashboard-receb-marketplaces.iam.gserviceaccount.com",
    "client_id": "116139259994891481926",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/streamlit-dashboard%40dashboard-receb-marketplaces.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

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