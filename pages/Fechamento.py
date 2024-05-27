import pandas as pd
import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st
from datetime import datetime, timedelta
st.set_page_config(
    page_title="Meu App Streamlit",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="collapsed",  # Pode ser "auto", "expanded", ou "collapsed"
)

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

scope = ['https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    json, scope)
client = gs.authorize(credentials)

BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 


base = BASE_STREAMLIT.worksheet('CARTEIRA')
base = base.get_values('A2:AC')

wis = BASE_STREAMLIT.worksheet('STATUS_OPERAÇÃO')
wis = wis.get_values('A2:N')
wis = pd.DataFrame(wis)
wis = wis[[1,12,10]]
wis.columns = ['Lote', 'Pendente Sep', 'Pendente Conf']

carteira  = pd.DataFrame(base)
carteira.columns = ['NUMPEDVEN','TPNOTA','TIPO_PEDIDO','CODFILTRANSFFAT','CANAL_VENDAS','CODMODAL','DESCRICAO','MODALIDADE','DESCRICAOROTA','DATA_APROVACAO','DTPEDIDO','DTENTREGA','PREVENTREGA','DTLIBFAT_MOD','FAMILIA','FILORIG','STATUS','ITEM','LINHA','NUMLOTE','NUMPEDCOMP','QTCOMP','PRECOUNIT','CUB_UNIT','STATUS_OPERACAO','SITUACAO','STATUS_OPERACAO_GERENCIAL','CUBTOTAL','VALTOTAL']
carteira_vendas = carteira[(carteira['TIPO_PEDIDO'] == 'VENDAS') & (carteira['STATUS_OPERACAO_GERENCIAL'] != 'PROGRAMADO')]

def num(valor):
    try:
        return float(valor.replace(',','.'))
    except:
        return valor

#fechamento[1] = fechamento[1].apply(num)
def fmt_num(valor):
    if isinstance(valor, str):
        return valor
    else:
        return "{:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')

carteira_vendas['VALTOTAL'] = carteira_vendas['VALTOTAL'].apply(num)

status = carteira_vendas.groupby('STATUS').agg({'VALTOTAL':'sum'})
status.loc['Total'] = status.sum()
status = status.reset_index()
status['VALTOTAL'] = status['VALTOTAL'].apply(fmt_num)

top_lotes = carteira_vendas[(carteira_vendas['STATUS_OPERACAO'] == 'EM PROCESSO') & (carteira_vendas['STATUS'] != '6-Conferido Aguardando Fat')]
top_lotes = top_lotes.groupby('NUMLOTE').agg({'VALTOTAL': 'sum'}).sort_values('VALTOTAL', ascending=False).head(10).reset_index()
top_lotes['VALTOTAL'] = top_lotes['VALTOTAL'].apply(fmt_num)
top_lotes = pd.merge(top_lotes, wis, how='left', left_on='NUMLOTE', right_on='Lote')
top_lotes = top_lotes[['Lote', 'VALTOTAL', 'Pendente Sep', 'Pendente Conf']]

top_pedidos = carteira_vendas[carteira_vendas['STATUS_OPERACAO'] != 'EM PROCESSO']
top_pedidos = top_pedidos.groupby('NUMPEDVEN').agg({'VALTOTAL': 'sum'}).sort_values('VALTOTAL', ascending=False).head(10).reset_index()
top_pedidos['VALTOTAL'] = top_pedidos['VALTOTAL'].apply(fmt_num)

lot_faturar = carteira_vendas[carteira_vendas['STATUS'] == '6-Conferido Aguardando Fat']
lote_faturar = lot_faturar['NUMLOTE'].nunique()

resultado = carteira_vendas['VALTOTAL'].sum()
meta = 1116768

#fechamento[0] = 'D:' + fechamento[0].str.split('-').str[2].str.split(' ').str[0] + ' H:' + fechamento[0].str.split('-').str[2].str.split(' ').str[1]


col1, col2, col3 = st.columns(3)
col1.subheader(f'Resultado: {fmt_num(resultado)}')
col1.subheader(f'Meta: {fmt_num(meta)}')
if resultado-meta > 0:
   col1.subheader(f'Dif: :red[{fmt_num(resultado-meta)}]') 
else:
    col1.subheader(f'Dif: :green[{fmt_num(resultado-meta)}]')
col1.subheader(f"Lotes para Faturar: " + str(lote_faturar))
col1.dataframe(data=status, hide_index=True)

col2.dataframe(data=top_lotes, hide_index=True)

col3.dataframe(top_pedidos, hide_index=True)


