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

scope = ['https://spreadsheets.google.com/feeds', # Definição de link para conexão com API.
        'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    './credentials.json', scope) # Definição de acesso via chave json.
client = gs.authorize(credentials)

BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 


fechamento = BASE_STREAMLIT.worksheet('FECHAMENTO')
fechamento = pd.DataFrame(fechamento.get_values('A2:c98'))
fechamento[0] = pd.to_datetime(fechamento[0] +":00")
dia = datetime.now() - timedelta(hours=4)
st.write(dia)
dia_fil = int(dia.strftime("%d"))
fechamento = fechamento[(fechamento[0].dt.day == dia_fil) | (fechamento[0] == f'2024-03-{dia_fil+1} 00:00:00')]
fechamento[0] = fechamento[0].dt.strftime("%Y-%m-%d %H")
fechamento = fechamento.fillna(0)
fechamento[1] = fechamento[1].apply(lambda x: 0 if x == '' else x)



base = BASE_STREAMLIT.worksheet('CARTEIRA')
base = base.get_values('A2:AC')


carteira  = pd.DataFrame(base)
carteira.columns = ['NUMPEDVEN','TPNOTA','TIPO_PEDIDO','CODFILTRANSFFAT','CANAL_VENDAS','CODMODAL','DESCRICAO','MODALIDADE','DESCRICAOROTA','DATA_APROVACAO','DTPEDIDO','DTENTREGA','PREVENTREGA','DTLIBFAT_MOD','FAMILIA','FILORIG','STATUS','ITEM','LINHA','NUMLOTE','NUMPEDCOMP','QTCOMP','PRECOUNIT','CUB_UNIT','STATUS_OPERACAO','SITUACAO','STATUS_OPERACAO_GERENCIAL','CUBTOTAL','VALTOTAL']
carteira_vendas = carteira[(carteira['TIPO_PEDIDO'] == 'VENDAS') & (carteira['STATUS_OPERACAO_GERENCIAL'] != 'PROGRAMADO')]

def num(valor):
    try:
        return float(valor.replace(',','.'))
    except:
        return valor

fechamento[1] = fechamento[1].apply(num)
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

top_pedidos = carteira_vendas[carteira_vendas['STATUS_OPERACAO'] != 'EM PROCESSO']
top_pedidos = top_pedidos.groupby('NUMPEDVEN').agg({'VALTOTAL': 'sum'}).sort_values('VALTOTAL', ascending=False).head(10).reset_index()
top_pedidos['VALTOTAL'] = top_lotes['VALTOTAL'].apply(fmt_num)


resultado = carteira_vendas['VALTOTAL'].sum()
meta = 1210000

fechamento[0] = 'D:' + fechamento[0].str.split('-').str[2].str.split(' ').str[0] + ' H:' + fechamento[0].str.split('-').str[2].str.split(' ').str[1]


col1, col2, col3 = st.columns(3)
col1.write(f'Resultado: {fmt_num(resultado)}')
col1.write(f'Meta: {fmt_num(meta)}')
col1.write(f'Dif: {fmt_num(resultado-meta)}')
col1.dataframe(data=status, hide_index=True)

col2.dataframe(data=top_lotes, hide_index=True)

col3.dataframe(top_pedidos, hide_index=True)
bas, ax2 = plt.subplots(1, 1,  figsize=(30, 7))

ax2.plot(fechamento[0].values.tolist() , fechamento[1].values.tolist())
ax2.set_title('Fechamento 31/03/2024')

for index, val in enumerate(fechamento[1]):
    valu = fmt_num(val)
    ax2.text(index, val, f'{valu}', ha='center', va='bottom', color='white', fontsize=16)
    rect = patches.Rectangle((index-0.7, val), 1.3, 300000, linewidth=1, edgecolor='b', facecolor='b', alpha=1)
    ax2.add_patch(rect)

if resultado < meta:
    c = 'g'
else:
    c = 'r'

ax2.axhline(y=meta, color=c, linestyle='--', label='Meta: R$1.210.000')
ax2.text(24, meta, f'Meta:\n{fmt_num(meta)}', ha='center', va='bottom', color='white', fontsize=16)
rect = patches.Rectangle((len(fechamento[0]) - 2, meta+10000), 2, 400000, linewidth=1, edgecolor=c, facecolor=c, alpha=1)
ax2.add_patch(rect)
ax2.set_xticklabels(fechamento[0], rotation=45)
ax2.yaxis.set_visible(False)
plt.tight_layout()

st.pyplot(bas)