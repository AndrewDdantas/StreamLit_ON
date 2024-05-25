import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import gspread as gs

def fmt_num(valor, tipo, casas=0): # Função para formatar números.
    if isinstance(valor,str):
        return ''
    if tipo == 'CUBAGEM':
        return "{:,.1f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == 'NORMAL':
        return "{:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == "PORCENTAGEM":
        return f"{{:.{casas}%}}".format(valor).replace('.',',')

st.set_page_config(
    page_title="PORTARIA",
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
ocupação = BASE_STREAMLIT.worksheet('OCUPAÇÃO 2650').get_all_values()
db = pd.DataFrame(ocupação[1:], columns=ocupação[0])

capacidade = db['CAPACIDADE'].str.replace(',','.').astype(float).sum()

ocupado = db['OCUPADO'].str.replace(',','.').astype(float).sum()

disponivel = capacidade - ocupado

col1, col2, col3 = st.columns(3)
col1.subheader('Capacidade: ' + fmt_num(capacidade, 'NORMAL'))
col2.subheader('Disponivel: ' + fmt_num(disponivel, 'NORMAL') + ' | ' + fmt_num(disponivel/capacidade,'PORCENTAGEM'))
col3.subheader('Ocupado: ' + fmt_num(ocupado, 'NORMAL') + ' | ' + fmt_num(ocupado/capacidade,'PORCENTAGEM'))

st.divider()

st.dataframe(db,hide_index=True)
