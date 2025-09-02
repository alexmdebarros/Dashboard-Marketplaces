import streamlit as st
import pandas as pd
import gspread
from gspread import Cell
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# --- 1) Configuração da página ---
st.set_page_config(page_title="Recebimentos de Marketplaces", layout="wide")

# --- 2) Autenticação (Login) ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# Renderiza o formulário de login na página principal, ANTES de qualquer outra coisa.
name, authentication_status, username = authenticator.login(location='main')

if st.session_state["authentication_status"] is False:
    st.error('Usuário ou senha incorreta.')
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, insira seu usuário e senha.')
    st.stop()

# --- O RESTO DO SEU APP SÓ VAI RODAR SE O LOGIN FOR BEM-SUCEDIDO ---

# --- 3) Barra Lateral com Logout e Filtros ---
with st.sidebar:
    st.write(f'Bem-vindo *{st.session_state["name"]}*')
    # O botão de logout agora está corretamente na 'sidebar'.
    authenticator.logout('Logout', 'sidebar')
    st.divider()
    if st.button("🔄 Atualizar dados agora"):
        # Esta chamada a load_data() é segura porque a função será definida antes de ser usada.
        load_data.clear()
        st.rerun()
    st.header("Filtros")

# --- 4) Injeta locale pt-BR (Opcional, mas mantido do seu original) ---
st.markdown(
    """
    <script>
      document.documentElement.lang = 'pt-BR';
    </script>
    """,
    unsafe_allow_html=True
)

# --- 5) Título ---
st.markdown("<h1>📊 Recebimentos de Marketplaces</h1>", unsafe_allow_html=True)

# --- 6) Conexão com o Google Sheets ---
# ATENÇÃO: Esta parte usa st.secrets. Você precisará configurar isso no Streamlit Cloud.
try:
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    gc = gspread.authorize(creds)
    ws = gc.open_by_key(st.secrets["SHEETS_KEY"]).worksheet("Dados")
    header = ws.row_values(1)
    IDX_BY = header.index("Baixado por") + 1
    IDX_DT = header.index("Data da Baixa") + 1
except Exception as e:
    st.error("Erro ao conectar com o Google Sheets. Verifique se os 'secrets' estão configurados corretamente no Streamlit Cloud.")
    st.error(f"Detalhe do erro: {e}")
    st.stop()


# --- 7) Carregamento e tratamento dos dados ---
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
    df["Valor"] = df["Valor_raw"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    df["Data_str"] = df["Data"].dt.strftime("%d/%m/%Y")
    df["DataBaixa_str"] = df["Data da Baixa"].dt.strftime("%d/%m/%Y %H:%M:%S").fillna("")
    return df

df = load_data()

# Adiciona o resto dos filtros na sidebar
with st.sidebar:
    mn = df["Data"].min().date()
    mx = df["Data"].max().date()
    start = st.date_input("Data Início", mn, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    end = st.date_input("Data Fim", mx, min_value=mn, max_value=mx, format="DD/MM/YYYY")
    status = st.radio("Status de Baixa", ["Todos", "Baixados", "Pendentes"])
    mp_sel = st.multiselect("Marketplace", sorted(df["Marketplace"].unique()))
    conta_sel = st.multiselect("Banco / Conta", sorted(df["Banco / Conta"].unique()))
    by_sel = st.multiselect("Baixado por", sorted(df["Baixado por"].unique()))

# --- 8) Aplicação dos Filtros ---
df_f = df[(df["Data"].dt.date >= start) & (df["Data"].dt.date <= end)]
if status == "Baixados": df_f = df_f[df_f["Baixado por"] != ""]
elif status == "Pendentes": df_f = df_f[df_f["Baixado por"] == ""]
if mp_sel: df_f = df_f[df_f["Marketplace"].isin(mp_sel)]
if conta_sel: df_f = df_f[df_f["Banco / Conta"].isin(conta_sel)]
if by_sel: df_f = df_f[df_f["Baixado por"].isin(by_sel)]

# --- 9) KPI Cards ---
def fmt_ptbr(valor: float) -> str:
    s = f"{valor:,.2f}"; inteiro, dec = s.split('.'); inteiro = inteiro.replace(',', '.'); return f"{inteiro},{dec}"

total = df_f["Valor_raw"].sum()
count = len(df_f)

if count > 0:
    porcent_b = len(df_f[df_f["Baixado por"] != ""]) / len(df_f) * 100
    porcent_n = len(df_f[df_f["Baixado por"] == ""]) / len(df_f) * 100
    baixados = df_f[df_f["Data da Baixa"].notna()]
    if not baixados.empty:
        baixados["Dias para Baixa"] = (baixados["Data da Baixa"] - baixados["Data"]).dt.days
        media_dias = baixados["Dias para Baixa"].mean()
    else:
        media_dias = None
else:
    porcent_b = porcent_n = 0
    media_dias = None

c1, c2, c3, c4, c5 = st.columns(5, gap="small")
c1.metric("💰 Total Recebido", f"R$ {fmt_ptbr(total)}")
c2.metric("📝 Lançamentos", f"{count}")
c3.metric("✅ Baixados(%)", f"{porcent_b:.2f}%" if not pd.isna(porcent_b) else "-")
c4.metric("❌ Pendentes(%)", f"{porcent_n:.2f}%" if not pd.isna(porcent_n) else "-")
c5.metric("⏱️ Tempo Médio Baixa", f"{media_dias:.1f} dias" if media_dias is not None and not pd.isna(media_dias) else "-")

st.divider()

# --- 10) Editor de dados ---
df_edit = df_f.reset_index().rename(columns={"index": "_orig_index"})
df_edit["row_number"] = df_edit["_orig_index"] + 2
df_edit["Data"] = df_edit["Data_str"]
df_edit["Data da Baixa"] = df_edit["DataBaixa_str"]
display_df = df_edit[["row_number", "Data", "Marketplace", "Valor","Banco / Conta", "Baixado por", "Data da Baixa"]].set_index("row_number")

edited = st.data_editor(
    display_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Data": st.column_config.TextColumn(disabled=True),
        "Marketplace": st.column_config.TextColumn(disabled=True),
        "Valor": st.column_config.TextColumn(disabled=True),
        "Banco / Conta": st.column_config.TextColumn(disabled=True),
        "Data da Baixa": st.column_config.TextColumn(disabled=True),
        "Baixado por": st.column_config.TextColumn(required=False, max_chars=50)
    }
)

mask = edited["Baixado por"].fillna("").astype(str).str.strip() != display_df["Baixado por"].fillna("").astype(str).str.strip()
if mask.any():
    if st.button("💾 Salvar alterações", type="primary"):
        with st.spinner("Salvando..."):
            cells = []
            tz = pytz.timezone("America/Sao_Paulo")
            now = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
            for rn in edited.index[mask]:
                raw_value = edited.at[rn, "Baixado por"]
                new_usr = str(raw_value).strip() if pd.notna(raw_value) else ""
                cells.append(Cell(rn, IDX_BY, new_usr))
                cells.append(Cell(rn, IDX_DT, "" if new_usr == "" else now))
            ws.update_cells(cells)
            st.success("✅ Alterações salvas com sucesso!")
            load_data.clear()
            st.rerun()

