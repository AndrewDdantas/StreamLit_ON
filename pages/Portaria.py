import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
import pytz

st.set_page_config(
    page_title="Meu App Streamlit",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="collapsed",  # Pode ser "auto", "expanded", ou "collapsed"
)

scope = ['https://spreadsheets.google.com/feeds', # Definição de link para conexão com API.
        'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    './credentials.json', scope) # Definição de acesso via chave json.
client = gs.authorize(credentials)


# Baixando informações da grade
planilha = client.open_by_key('13ZBSdVjqRsQQwE8a6abpi99myjo72w1ife-vjUrzMCs') 
grade = planilha.worksheet('Dados_consolidado_2023')
dados_grade = grade.get_values('b3:l')
dados_grade = pd.DataFrame(dados_grade)
dados_grade.columns = ['DATA_PROG', 'STATUS', 'OPERACAO', 'IDCARGA',
                        'ORDEM', 'DATA_OFEREC', 'OFEREC', 'FILIAL',
                                    'ROTA', 'LOTE', 'TURNO']

BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 
base = BASE_STREAMLIT.worksheet('PORTARIA')
base = base.get_values('A2:I')
base = pd.DataFrame(base)
base.columns = ['CODENTVEIC','APRESENTACAO','ENTRADA','SAIDA','CODCOMANDA','PLACAVEIC','CPF','NOMEMOTORISTA','IDCARGA']
carros = base

def calcula_permanencia(row):
    if row['ENTRADA'] == '':
        return ''
    e = pd.to_datetime(row['ENTRADA'])
    fuso_horario = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso_horario)
    s = pd.to_datetime(row['SAIDA']) if row['SAIDA'] != '' else pd.to_datetime(agora.strftime('%Y-%m-%d %H:%M'))
    return pd.to_timedelta(s - e , unit='ms')


carros['PERMANENCIA'] = carros.apply(calcula_permanencia, axis=1)
carros = carros.fillna(0)

carros = carros[carros['IDCARGA'] != '']

carros['IDCARGA'] = carros['IDCARGA'].astype(float).round(0).astype(int).astype(str)

def numero_ajustado(valor):
    indice_6 = valor.find('6')
    if indice_6 != -1:
    # Extrair os 7 números após o primeiro '6' encontrado
        resultado = valor[indice_6 :indice_6 + 7]
    else:
        resultado = valor
    return resultado

carros['IDCARGA'] = carros['IDCARGA'].apply(numero_ajustado)

merge = pd.merge(dados_grade, carros, how='left', on='IDCARGA')

merge['DATA_PROG'] = merge['DATA_PROG'] + '/2024' 



merge = merge.loc[(merge['LOTE'] != '')]

if 'pendentes' in st.session_state:
    data = st.session_state['pendentes']
else:
    data = merge['DATA_PROG'].drop_duplicates().values.tolist()
    data = st.multiselect("Qual data de programação você deseja?", data)



merge = merge.loc[(merge['DATA_PROG'].isin(data))]
merge['OFEREC'] = pd.to_datetime(merge['DATA_OFEREC'] + ' ' + merge['OFEREC'], format='%d/%m/%Y %H:%M')
merge = merge.sort_values(by='OFEREC')
merge = merge.drop_duplicates(subset=['DATA_PROG', 'OFEREC','IDCARGA','FILIAL'])
merge = merge.groupby(['DATA_PROG', 'OFEREC','IDCARGA']).agg({
    'FILIAL': lambda x: ', '.join(map(str, x.unique())),  # Para strings
    'ENTRADA': 'max',
    'SAIDA': 'max',
    'PERMANENCIA': 'max'
}).reset_index()

def status(df):
    if all(pd.isnull(df[col]) or df[col] == '' for col in ['ENTRADA', 'SAIDA', 'PERMANENCIA']):
        return 'Não Chegou'
    elif (df['ENTRADA'] != '') and (df['SAIDA'] == ''):
        return 'No Pátio'
    else:
        return 'Liberado'
merge['STATUS'] = merge.apply(status, axis=1)


statuss = merge.groupby('STATUS').agg({'IDCARGA': 'nunique'}).reset_index()
nchegou = statuss['IDCARGA'].loc[statuss['STATUS'] == 'Não Chegou'].sum()
liberado = statuss['IDCARGA'].loc[statuss['STATUS'] == 'Liberado'].sum()
npatio = statuss['IDCARGA'].loc[statuss['STATUS'] == 'No Pátio'].sum()

col1, col2, col3 = st.columns(3)

col1.metric('No Pátio',npatio)
col2.metric('Liberado',liberado)
col3.metric('Não Chegou',nchegou)
merge['PERMANENCIA'] = pd.to_timedelta(merge['PERMANENCIA'], unit='ms')
merge = merge.fillna('')
merge['PERMANENCIA'] = merge['PERMANENCIA'].apply(lambda x: '' if x == pd.NaT else x)


def colorir_linha(s):
    # Verifica cada valor em s (série) e retorna a cor de fundo correspondente
    return [
        'background-color: green; color: white' if x == 'Liberado' else
        'background-color: red; color: white' if x == 'Não Chegou' else
        'background-color: yellow; color: black' if x == 'No Pátio' else
        ''  # Sem cor de fundo se não atender a nenhuma condição
        for x in s
    ]

# Aplicando o estilo ao DataFrame
df_estilizado = merge.style.apply(colorir_linha, subset=['STATUS'])

# Convertendo o DataFrame estilizado para HTML
html = df_estilizado.to_html(escape=False)

# Exibindo o DataFrame estilizado no Streamlit
st.markdown(html, unsafe_allow_html=True)
