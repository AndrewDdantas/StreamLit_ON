import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import gspread as gs
from time import sleep
from datetime import datetime, timedelta

st.set_page_config(
    page_title="PORTARIA",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="collapsed",  # Pode ser "auto", "expanded", ou "collapsed"

)


scope = ['https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    './credentials.json', scope)
client = gs.authorize(credentials)


BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 
portaria_controle = BASE_STREAMLIT.worksheet('PORTARIA CONTROLE')

portaria_controle.columns = ['DTPROGRAMACAO','IDCARGA','ROTA_MASTER','STATUS PRODUÇÃO','DOCA','OFERECIMENTO','STATUS MOTORISTA','Observação']
window_size = 15
st.title('Acompanhamento Cargas')
hora_cont = st.empty()
container = st.empty()

status_colors = {
    '1 Pendente de Docagem': '#F0F8FF',  # Cor para o status 1
    '2 Pendente Separação': '#FFFF00',  # Cor para o status 2
    '3 Pendente Conferencia': '#FFD700',  # Cor para o status 3
    '4 Aguardando Carregamento': '#FF8C00',
    '5 Em Carregamento': '#32CD32',
    '6 Aguardando Liberação': '#008000',
}

status_colors_font = {
    '1 Pendente de Docagem': 'red',  # Cor para o status 1
    '2 Pendente Separação': 'black',  # Cor para o status 2
    '3 Pendente Conferencia': 'black',  # Cor para o status 3
    '4 Aguardando Carregamento': 'white',
    '5 Em Carregamento': 'white',
    '6 Aguardando Liberação': 'white',
}

def rolar_dataframe(window_size):

    df = pd.DataFrame(portaria_controle.get_values('A2:H'))
    df.columns = ['DTPROGRAMACAO','IDCARGA','ROTA_MASTER','STATUS PRODUÇÃO','DOCA','CARREGAMENTO','STATUS MOTORISTA','OBSERVAÇÃO']
    df = df[['DTPROGRAMACAO','STATUS PRODUÇÃO','IDCARGA','ROTA_MASTER','DOCA','CARREGAMENTO','STATUS MOTORISTA','OBSERVAÇÃO']]
    n_rows = len(df)
    index = 0
    h_atualizacao = (datetime.now()-timedelta(hours=3)) + timedelta(minutes=5)
    hora_cont.subheader((datetime.now()-timedelta(hours=3)).strftime('%H:%M'))
    while True:
        def apply_status_color(value):
            return f'background-color: {status_colors.get(value, "black")} ; color: {status_colors_font.get(value, "black")}; font-weight: 900; text-align: center'

        # Aplicar estilos condicionais à coluna 'Status Produção'
        window = df.iloc[index:index+window_size]
        styled_df = window.style.map(apply_status_color, subset=['STATUS PRODUÇÃO'])
        
        container.table(styled_df,index=False)

        index = (index + 1) % n_rows

        sleep(5)
        if (datetime.now()-timedelta(hours=3)) > h_atualizacao:
            hora_cont.subheader((datetime.now()-timedelta(hours=3)).strftime('%H:%M'))
            df = pd.DataFrame(portaria_controle.get_values('A2:H'))
            df.columns = ['DTPROGRAMACAO','IDCARGA','ROTA_MASTER','STATUS PRODUÇÃO','DOCA','CARREGAMENTO','STATUS MOTORISTA','OBSERVAÇÃO']
            df = df[['DTPROGRAMACAO','STATUS PRODUÇÃO','IDCARGA','ROTA_MASTER','DOCA','CARREGAMENTO','STATUS MOTORISTA','OBSERVAÇÃO']]
            h_atualizacao = (datetime.now()-timedelta(hours=3)) + timedelta(minutes=5)


rolar_dataframe(window_size)
