import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Meu App Streamlit",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="auto",  # Pode ser "auto", "expanded", ou "collapsed"
)

scope = ['https://spreadsheets.google.com/feeds', # Definição de link para conexão com API.
         'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    'credentials.json', scope) # Definição de acesso via chave json.
client = gs.authorize(credentials)

sheet = client.open_by_key('1pyFMoqM-onb1sBQiBDkNeenkt6WIx6DlBVHV4KhIEL4')
worksheet = sheet.worksheet('Base SQL')


data = worksheet.get_values('d:s')

df = pd.DataFrame(data)

calculadora = sheet.worksheet('Cal NS')
df2 = calculadora.get_values('c3:C7')

columns = df.iloc[:1].values.tolist()[0]
df.columns = columns
df = df.drop(index=0)
df['A Vencer'] = df.apply(lambda x: 1 if (x['FINALIZADOR'] == 'PENDENTE') & (x['STATUS PRAZO'] == 'À VENCER') else 0, axis=1)
df['Vencido'] = df.apply(lambda x: 1 if (x['FINALIZADOR'] == 'PENDENTE') & (x['STATUS PRAZO'] == 'VENCIDO') else 0, axis=1)
df['Vence Hoje'] = df.apply(lambda x: 1 if (x['FINALIZADOR'] == 'PENDENTE') & (x['STATUS PRAZO'] == 'VENCE HOJE') else 0, axis=1)
df['Total'] = df.apply(lambda x: 1 if (x['FINALIZADOR'] == 'PENDENTE') else 0, axis=1)
d2 = df.loc[(df['REGIONAL']!='CORREIOS') & (df['REGIONAL']!='FRACIONADO')] 
df = df.loc[(df['REGIONAL']!='CORREIOS') & (df['REGIONAL']!='FRACIONADO') & (df['FINALIZADOR'] == 'PENDENTE')]
def var(x):
    if x == 'Endere o do Cliente Destino n o Localizado': 
        return 'Endereço Não_Localizado'
    elif x == 'Em rota de entrega':
        return 'Em Entrega'
    elif x == '1a Tentativa Cliente Ausente':
        return '1a_Tentativa Cliente_Ausente'
    elif x == 'Saiu para Entrega':
        return 'Saiu_para Entrega'
    elif x == 'Troca de transportadora':
        return 'Troca transportadora'

df['STATUS FINAL'] = df['STATUS FINAL'].apply(var)
df.sort_values('STATUS FINAL', ascending=False)

dina = df.loc[(df['STATUS FINAL'] != '') & (df['STATUS PRAZO'] == 'VENCE HOJE')]
dina = dina.groupby(['TRANSP CORRIGIDA', 'STATUS FINAL']).agg({'Total': 'sum'}).fillna(0).reset_index()
din = pd.pivot_table(dina, values='Total', index='TRANSP CORRIGIDA', columns='STATUS FINAL', aggfunc='sum', fill_value=0)
din = din[din.sum().sort_values(ascending=False).index]
din = din.iloc[:, :5]
data = pd.DataFrame(din)
data = data.head(16)
try:
    data = data.reset_index().sort_values('Em Entrega', ascending=False)
except:
    data = data.reset_index()
trans = df.groupby('TRANSP CORRIGIDA').agg({'A Vencer': 'sum', 'Vence Hoje': 'sum', 'Vencido': 'sum', 'Total': 'sum'}).reset_index()
total = trans['Total'].sum()
a_vence = trans['A Vencer'].sum()
vence = trans['Vence Hoje'].sum()
venci = trans['Vencido'].sum()
trans = trans.sort_values(['Vence Hoje', 'Vencido'], ascending=False).head(26) # Grid para encaixe de Dashboard.


# Ler o arquivo CSS e converter em string
with open('style.css', 'r') as f:
    css_string = f.read()

# Injetar o CSS no Streamlit
st.markdown(f'<style>{css_string}</style>', unsafe_allow_html=True)

html_content = f'''
<div class="box_large">
    <div class="info-box1">
        <h2>Total de Pedidos</h2>
        <p>{total}</p>
    </div>
    <div class="info-box2">
        <h2>A Vencer</h2>
        <p>{a_vence}</p>
    </div>
</div>
<div class="box_large">
    <div class="info-box3">
        <h2>Vence Hoje</h2>
        <p>{vence}</p>
    </div>
    <div class="info-box4">
        <h2>Vencidos</h2>
        <p>{venci}</p>
    </div>
</div>
'''

html_table = trans.to_html(classes='info-table', index=False) # Tabela transportadoras2

data.columns.name = None

html_table2 = data.to_html(classes="Table2", index=False)





col1, col2, col3 = st.columns([3, 2, 1])
col1.markdown(html_content, unsafe_allow_html=True)
col1.markdown(html_table2, unsafe_allow_html=True)
col2.markdown(html_table, unsafe_allow_html=True)

total_pedidos = df2[0][0]
pendentes = df2[1][0]
ns = df2[2][0]
saldo = df2[3][0]
saldo_pendentes = df2[4][0]


html_content2 = f'''<div class="box_large_calc">
<div class="box">
    <h2>Total de Pedidos</h2>
    <p>{total_pedidos}</p>
</div>
<div class="box">
    <h2>Pendentes</h2>
    <p>{pendentes}</p>
</div>
<div class="box">
    <h2>% NS</h2>
    <p>{ns}</p>
</div>
<div class="box">
    <h2>Saldo</h2>
    <p>{saldo}</p>
</div>
<div class="box">
    <h2>Saldo pendente para Meta</h2>
    <p>{saldo_pendentes}</p>
</div>
</div>

'''


col3.markdown(html_content2, unsafe_allow_html=True)