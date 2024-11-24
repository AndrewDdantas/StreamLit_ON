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

GRADE = client.open_by_key(st.secrets['grade']) 

st.title('Visão Status Carregamento')

def get_data_transport():
    try:
        grade = GRADE.worksheet('Dados_consolidado')
        dados_grade = grade.get_values('b2:j')
        dados_grade = pd.DataFrame(dados_grade[1:], columns=dados_grade[0])
        dados_grade['num_status'] = dados_grade['STATUS'].str[0]
        dados_grade = dados_grade.loc[(dados_grade['LOTE'] != '') & (dados_grade['num_status'].isin(['1','2','3','4','5','6']))]

        de_para_report = GRADE.worksheet('FREQUÊNCIA')
        de_para_report = de_para_report.get_values('C4:Q')
        de_para_report = pd.DataFrame(de_para_report[1:], columns=de_para_report[0])

        data_join = pd.merge(dados_grade, de_para_report, how='left', left_on='FILIAL', right_on='Cód.')
        data_join = data_join.groupby(['DATA PROG.', 'ID / CARGA']).agg({'DATA OFEREC.':'first', 'Oferec. Carregamento':'first' ,'Master Report':'first', 'Puxada':'first', 'STATUS':'min'})
        data_join['SORT'] = pd.to_datetime(data_join['DATA OFEREC.'].astype(str) + ' ' + data_join['Oferec. Carregamento'].astype(str), format='%d/%m/%Y %H:%M')
        data_join = data_join.loc[data_join['SORT'] >= (datetime.now() - timedelta(days=3))]
        data_join['Limite Saída'] = (data_join['SORT'] + timedelta(hours=4)).dt.strftime('%d/%m/%Y %H:%M')
        data_join = data_join.sort_values('SORT').drop('SORT', axis=1).reset_index()

        data_join = data_join[['DATA PROG.', 'STATUS', 'ID / CARGA', 'Master Report', 'Puxada', 'Limite Saída']]
        return 200, data_join


    except Exception as e:
        return 500, e
stats, df = get_data_transport()

if stats == 200:
    STATUS_PALETA = {
        "1. Aguardando Inicio Produção": "#FFA500",  # Laranja
        "2. Em Separação": "#ffff00",
        "3. Conferindo": "#f6b26b",  # Amarelo ouro
        "4. Embalagem": "#4285f4",  # Verde claro
        "5. Separação Concl./ Aguard. Carreg.": "#ffc000",  # Verde médio
        "6. Em carregamento": "#38761d",  # Verde floresta
        "7. Carreg. Finalizado": "#006400"  # Verde escuro
    }
    
    # Função para estilizar uma coluna de status
    def style_status(status):
        """
        Retorna o estilo CSS baseado no status.
        """
        color = STATUS_PALETA.get(status, "#FFFFFF")  # Branco como padrão
        if color == "#ffff00":
            return f"background-color: {color}; color: black;"
        return f"background-color: {color}; color: white;"

    df = pd.DataFrame(df)
    
    # Aplicar estilos à coluna "Status"
    styled_df = df.style.applymap(style_status, subset=["STATUS"])
    
    # Mostrar no Streamlit
    st.table(styled_df)
else: 
    st.write(df)


