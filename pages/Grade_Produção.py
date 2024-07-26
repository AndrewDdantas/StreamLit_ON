import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import gspread as gs
import pandas as pd
from io import StringIO
import altair as alt
import numpy as np

def fmt_num(valor, tipo, casas=0):
    if isinstance(valor,str):
        return ''
    if tipo == 'REAL':
        return "R$ {:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == 'CUBAGEM':
        return "{:,.1f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == 'NORMAL':
        return "{:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == "PORCENTAGEM":
        return f"{{:.{casas}%}}".format(valor).replace('.',',')

st.set_page_config(
    page_title="GERENCIAMENTO",
    page_icon=":chart_with_upwards_trend:",
    layout="wide", 
    initial_sidebar_state="auto",
)

st.title('Grade de Produção CD 2650')

json = {
    "type": "service_account",
    "project_id": st.secrets['project_id'],
    "private_key_id": st.secrets['KEY'],
    "private_key": st.secrets['private_key'],
    "client_email": st.secrets['client_email'],
    "client_id": st.secrets['client_id'],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/case-693%40digital-layout-402513.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
    }

# Define the scope and authenticate
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    json, scope)
client = gs.authorize(credentials)

base = client.open_by_key(st.secrets['bases']).worksheet('GRADE') 
db_data = base.get_all_values()
df = pd.DataFrame(db_data[1:], columns=db_data[0])

df = df.replace('', 0)

df[['PECAS', 'SEPARADO', 'CONFERIDO']] = df[['PECAS', 'SEPARADO', 'CONFERIDO']].astype(float)

df['CUBAGEM'] = df['CUBAGEM'].str.replace(',', '.').astype(float)
df['CUB_SEPARADA'] = df['CUB_SEPARADA'].str.replace(',', '.').astype(float)
df['CUB_CONFERIDA'] = df['CUB_CONFERIDA'].str.replace(',', '.').astype(float)
df[['DATA', 'HORA']] = df['DATA_PROGRAMACAO'].str.split(' ', expand=True)
df['DATA_PROGRAMACAO'] = df['DATA_PROGRAMACAO'].str.replace('/24 ', '/2024 ')
df['DATA_PROGRAMACAO'] = pd.to_datetime(df['DATA_PROGRAMACAO'], format='%Y-%m-%d %H:%M')

df = df.sort_values('DATA_PROGRAMACAO')

col1, col2 = st.columns(2)

fil = [''] + df['DATA'].drop_duplicates().values.tolist()
data = col1.selectbox('Data', fil)

fil_status = [''] + df['STATUS_LOTE'].drop_duplicates().values.tolist()
status = col2.selectbox('Status', fil_status)


if data == '':
    df_fil_data = df.loc[df['STATUS_LOTE'] != 'FATURADO']
    df_fil_data = df_fil_data['DATA'].drop_duplicates().values.tolist()
    df = df.loc[df['DATA'].isin(df_fil_data)]
else:
    df = df.loc[df['DATA'] == data]

if status != '':
    df = df.loc[df['STATUS_LOTE'] == status]



pec = fmt_num(df['PECAS'].sum(), 'NORMAL')
cub = fmt_num(df['CUBAGEM'].sum(),'CUBAGEM', 2)
col1.subheader( f'Planejado Peças: {pec}')
col1.subheader( f'Planejado Cubagem: {cub}')


df_rosca = pd.DataFrame({
    'category': ['Pendente', 'Produzido'],
    'value': [1-df['CONFERIDO'].sum()/df['PECAS'].sum(),df['CONFERIDO'].sum()/df['PECAS'].sum()]
})


chart = alt.Chart(df_rosca).mark_arc(innerRadius=70).encode(
    theta=alt.Theta(field="value", type="quantitative", stack=True),
    color=alt.Color(field="category", type="nominal", legend=alt.Legend(
        title="Status",
        titleFontSize=14,
        labelFontSize=12,
        orient='left',
        direction='vertical'
    ))
).properties(
    width=300,  # Ajuste a largura conforme necessário
    height=300,  # Ajuste a altura conforme necessário
    title="Distribuição de Valores por produção"
)

gra = int(df["CONFERIDO"].sum() / df["PECAS"].sum() * 100)
text = alt.Chart(pd.DataFrame({'text': [f'{gra}%']})).mark_text(
    size=30,
    align='center',
    baseline='middle',
    color='white'
).encode(
    text='text:N'
)

# Combinando o gráfico de rosca e o texto
chart = (chart + text).configure_view(
    strokeWidth=0
)

col2.altair_chart(chart)

col11, col12 = col1.columns(2)

ps = fmt_num(df['SEPARADO'].sum(), 'NORMAL')
cs = fmt_num(df['CUB_SEPARADA'].sum(),'CUBAGEM', 2)
psp = fmt_num(df['SEPARADO'].sum()/df['PECAS'].sum(), 'PORCENTAGEM', 2)
csp = fmt_num(df['CUB_SEPARADA'].sum()/df['CUBAGEM'].sum(), 'PORCENTAGEM', 2)
col11.write( f'Peças Separadas: {ps}')
col11.write( f'Cubagem Separada: {cs}')
col12.write( f'{psp}')
col12.write( f'{csp}')

pc = fmt_num(df['CONFERIDO'].sum(), 'NORMAL')
cc = fmt_num(df['CUB_CONFERIDA'].sum(),'CUBAGEM', 2)
pcs = fmt_num(df['CONFERIDO'].sum()/df['PECAS'].sum(), 'PORCENTAGEM', 2)
ccs = fmt_num(df['CUB_CONFERIDA'].sum()/df['CUBAGEM'].sum(), 'PORCENTAGEM', 2)

col11.write( f'Peças Conferidas: {pc}')
col11.write( f'Cubagem Conferida: {cc}')
col12.write( f'{pcs}')
col12.write( f'{ccs}')
try:
    docas = df.loc[df['STATUS_LOTE'] == 'EM PRODUCAO']
    docas['DOCA'] = docas['DOCA'].apply(lambda x: str(x)[:1] if len(str(x)) > 3 else str(x)[:2])
    docas['PEN_SEP'] = docas['CUBAGEM'] - df['CUB_SEPARADA']
    docas['PEN_CONF'] = docas['CUBAGEM'] - df['CUB_CONFERIDA']
    docas = docas.groupby('DOCA').agg({'CUBAGEM': 'sum', 'PEN_SEP': 'sum', 'PEN_CONF': 'sum'})
except:
    docas = pd.DataFrame()

oferecimento = df.groupby(['DATA', 'HORA']).agg({'ID_CARGA': 'nunique', 'PECAS': 'sum', 'SEPARADO': 'sum', 'CONFERIDO': 'sum', 'CUBAGEM': 'sum', 'CUB_SEPARADA': 'sum', 'CUB_CONFERIDA': 'sum'})
col1, col2 = st.columns([1, 2])
col1.dataframe(docas)
col2.dataframe(oferecimento)

st.dataframe(df, hide_index=True)
