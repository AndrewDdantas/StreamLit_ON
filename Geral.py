import streamlit as st
import pandas as pd
import locale as lo
from datetime import datetime, timedelta
import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', # Definição de link para conexão com API.
        'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    './credentials.json', scope) # Definição de acesso via chave json.
client = gs.authorize(credentials)

BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 


def fmt_num(valor, tipo, casas=0): # Função para formatar números.
    if isinstance(valor,str):
        return ''
    if tipo == 'REAL':
        return lo.format_string(f"R$ %0.{casas}f",valor,grouping=True)
    if tipo == 'CUBAGEM':
        return "{:,.1f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == 'NORMAL':
        return "{:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == "PORCENTAGEM":
        return f"{{:.{casas}%}}".format(valor).replace('.',',')

st.set_page_config(
    page_title="Base Carteira",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="auto",  # Pode ser "auto", "expanded", ou "collapsed"
)

# Adicionando um cabeçalho personalizado
st.title('Bem vindo, Neo!')

st.write('Carteira Liberados')

if 'carteira' not in st.session_state and 'estoque' not in st.session_state and 'faturados' not in st.session_state and 'Black_2022' not in st.session_state:

    base = BASE_STREAMLIT.worksheet('CARTEIRA')
    base = base.get_values('A2:AC')
    df = pd.DataFrame(base)
    df.columns = ['NUMPEDVEN','TPNOTA','TIPO_PEDIDO','CODFILTRANSFFAT','CANAL_VENDAS','CODMODAL','DESCRICAO','MODALIDADE','DESCRICAOROTA','DATA_APROVACAO','DTPEDIDO','DTENTREGA','PREVENTREGA','DTLIBFAT_MOD','FAMILIA','FILORIG','STATUS','ITEM','LINHA','NUMLOTE','NUMPEDCOMP','QTCOMP','PRECOUNIT','CUB_UNIT','STATUS_OPERACAO','SITUACAO','STATUS_OPERACAO_GERENCIAL','CUBTOTAL','VALTOTAL']
    df['CODFILTRANSFFAT'] = df['CODFILTRANSFFAT'].astype(str)
    df['VALTOTAL'] = df['VALTOTAL'].str.replace(',','.').astype(float)
    df['CUBTOTAL'] = df['CUBTOTAL'].str.replace(',', '.').astype(float)
    df = df.sort_values('NUMPEDVEN')
    deparamodais = pd.read_excel('de_para_modais.xlsx','Modais')
    deparamodais = deparamodais.astype(str)
    deparafiliais = pd.read_excel('de_para_modais.xlsx','Filiais')
    deparafiliais = deparafiliais.astype(str)
    deparafiliais['Cód'] = deparafiliais['Cód'].astype(str)
    dp_cdEntrega = pd.read_excel('de_para_modais.xlsx','CD Entrega')
    dp_cdEntrega = dp_cdEntrega.astype(str)
    df_union = pd.merge(df,deparamodais,how='left', on='CODMODAL')
    df_union = pd.merge(df_union,deparafiliais, how='left',left_on='CODFILTRANSFFAT', right_on='Cód')
    df_union = pd.merge(df_union,dp_cdEntrega, how='left',left_on='DESCRICAOROTA', right_on='Rota')
    st.session_state['carteira'] = df_union


df_filter = st.session_state['carteira']

status = df_filter.groupby('STATUS').agg({'QTCOMP': 'sum', 'CUBTOTAL': 'sum'}).head(10)
status.loc['Total'] = status.sum()
status['CUBTOTAL'] = status['CUBTOTAL'].apply(fmt_num, tipo='CUBAGEM', casas=1)
status['QTCOMP'] = status['QTCOMP'].apply(fmt_num, tipo='NORMAL')
status = status.reset_index()
status.columns = ['Status', 'Peças', 'Cubagem']


top_familia = df_filter.groupby('FAMILIA').agg({'QTCOMP': 'sum', 'CUBTOTAL': 'sum'}).sort_values('CUBTOTAL', ascending=False).head(10)
top_familia['CUBTOTAL'] = top_familia['CUBTOTAL'].apply(fmt_num, tipo='CUBAGEM', casas=1)
top_familia['QTCOMP'] = top_familia['QTCOMP'].apply(fmt_num, tipo='NORMAL')
top_familia = top_familia.reset_index()
top_familia.columns = ['Familias', 'Peças', 'Cubagem']


modais_processo = df_filter[df_filter['STATUS'].isin(['2-Liberado','4-Lote em Separacao'])]
modais_processo['Carteira'] = modais_processo.apply(lambda x: x['CUBTOTAL'] if x['STATUS'] == '2-Liberado' else 0, axis=1)
modais_processo['Processo'] = modais_processo.apply(lambda x: x['CUBTOTAL'] if x['STATUS'] == '4-Lote em Separacao' else 0, axis=1)
modais_processo = modais_processo.groupby('Modal Master').agg({'QTCOMP':'sum', 'Carteira': 'sum', 'Processo': 'sum', 'CUBTOTAL': 'sum'})
modais_processo.loc['Total'] = modais_processo.sum()
modais_processo = modais_processo.applymap(fmt_num, tipo='CUBAGEM', casas=1).reset_index()
modais_processo.columns = ['Modal Master','Peças', 'Carteira', 'Processo', 'Cubagem']

carteira_dias = df_filter['CUBTOTAL'].sum()
val = {'Tipo':['Carteira Atual', 'Capacidade', 'Dias Em Carteira'], 'Valores':[fmt_num(carteira_dias, tipo='CUBAGEM'), '1.100', fmt_num(carteira_dias/1100, tipo='CUBAGEM', casas=2)]}
carteira_dias = pd.DataFrame(val)

df_filter['QTCOMP'] = df_filter['QTCOMP'].astype(float) 
dinamica_pecas = pd.pivot_table(df_filter, values='QTCOMP', index='Filial', columns='Modal Master', aggfunc='sum', fill_value=0)    
dinamica_pecas['Total'] = dinamica_pecas.sum(axis=1)
dinamica_pecas = dinamica_pecas.sort_values('Total', ascending=False).applymap(fmt_num, tipo='NORMAL')


dinamica_cub = pd.pivot_table(df_filter, values='CUBTOTAL', index='Filial', columns='Modal Master', aggfunc='sum', fill_value=0)
dinamica_cub['Total'] = dinamica_cub.sum(axis=1)
dinamica_cub = dinamica_cub.sort_values('Total', ascending=False).applymap(fmt_num, tipo='CUBAGEM', casas=1)

cd_entrega = df_filter[df_filter['Modal Master'] == 'CD Entrega']
cd_entrega = cd_entrega.groupby('Cidade').agg({'NUMPEDVEN':'nunique','QTCOMP':'sum', 'CUBTOTAL':'sum'}).reset_index().sort_values('CUBTOTAL', ascending=False)
cd_entrega['CUBTOTAL'] = cd_entrega['CUBTOTAL'].apply(fmt_num, tipo='CUBAGEM', casas=1)
cd_entrega['QTCOMP'] = cd_entrega['QTCOMP'].apply(fmt_num, tipo='NORMAL')


col1, col2, col3 = st.columns(3)

col1.dataframe(status, hide_index=True)
col2.dataframe(modais_processo, hide_index=True)
col3.dataframe(top_familia, hide_index=True)

col1.dataframe(carteira_dias, hide_index=True)

colun1, colun2, colun3 = st.columns(3)
colun1.write('Modais por Filial Peças.')
colun1.dataframe(dinamica_pecas)
colun2.write('Modais por Filial Cubagem.')
colun2.dataframe(dinamica_cub)
colun3.write('Cidades CD Entrega')
colun3.dataframe(cd_entrega, hide_index=True)