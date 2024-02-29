import pandas as pd
import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import streamlit as st

scope = ['https://spreadsheets.google.com/feeds', # Definição de link para conexão com API.
        'https://www.googleapis.com/auth/drive'] 
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    './credentials.json', scope) # Definição de acesso via chave json.
client = gs.authorize(credentials)

BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 
fechamento = BASE_STREAMLIT.worksheet('FECHAMENTO')
fechamento = pd.DataFrame(fechamento.get_values('A2:B26'))
base = BASE_STREAMLIT.worksheet('CARTEIRA')
base = base.get_values('A2:AC')


carteira  = pd.DataFrame(base)
carteira.columns = ['NUMPEDVEN','TPNOTA','TIPO_PEDIDO','CODFILTRANSFFAT','CANAL_VENDAS','CODMODAL','DESCRICAO','MODALIDADE','DESCRICAOROTA','DATA_APROVACAO','DTPEDIDO','DTENTREGA','PREVENTREGA','DTLIBFAT_MOD','FAMILIA','FILORIG','STATUS','ITEM','LINHA','NUMLOTE','NUMPEDCOMP','QTCOMP','PRECOUNIT','CUB_UNIT','STATUS_OPERACAO','SITUACAO','STATUS_OPERACAO_GERENCIAL','CUBTOTAL','VALTOTAL']
carteira_vendas = carteira[(carteira['TIPO_PEDIDO'] == 'VENDAS') & (carteira['STATUS_OPERACAO_GERENCIAL'] != 'PROGRAMADO')]

def num(valor):
    return float(valor.replace(',','.'))
def fmt_num(valor):
    return "{:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')

carteira_vendas['VALTOTAL'] = carteira_vendas['VALTOTAL'].apply(num)

status = carteira_vendas.groupby('STATUS').agg({'VALTOTAL':'sum'})
status.loc['Total'] = status.sum()
status = status.reset_index()
status['VALTOTAL'] = status['VALTOTAL'].apply(fmt_num)

top_lotes = carteira_vendas[carteira_vendas['STATUS_OPERACAO'] == 'EM PROCESSO']
top_lotes = top_lotes.groupby('NUMLOTE').agg({'VALTOTAL': 'sum'}).head(10).reset_index()
top_lotes['VALTOTAL'] = top_lotes['VALTOTAL'].apply(fmt_num)


resultado = carteira_vendas['VALTOTAL'].sum()
meta = 1624000

fechamento[1] = fechamento[1].apply(lambda x: 0 if x == '' else x.replace('.', '')).fillna(0).astype(float)
fechamento[0] = 'D:' + fechamento[0].str.split('-').str[2].str.split(' ').str[0] + ' H:' + fechamento[0].str.split('-').str[2].str.split(' ').str[1]


col1, col2 = st.columns(2)
col1.write(f'Resultado: {fmt_num(resultado)}')
col1.write(f'Meta: {fmt_num(meta)}')
col1.write(f'Dif: {fmt_num(resultado-meta)}')

col2.dataframe(top_lotes)

bas, ax2 = plt.subplots(1, 1,  figsize=(30, 7))

ax2.plot(fechamento[0].values.tolist() , fechamento[1].values.tolist())
ax2.set_title('Fechamento 29/02/2024')
for index, val in enumerate(fechamento[1]):
    valu = fmt_num(val)
    ax2.text(index, val, f'{valu}', ha='center', va='bottom', color='white', fontsize=16)
    rect = patches.Rectangle((index-0.7, val), 1.3, 200000, linewidth=1, edgecolor='b', facecolor='b', alpha=1)
    ax2.add_patch(rect)

if resultado < meta:
    c = 'g'
else:
    c = 'r'

ax2.axhline(y=meta, color=c, linestyle='--', label='Meta: R$1.624.000')
ax2.text(24, meta, f'Meta:\n{fmt_num(meta)}', ha='center', va='bottom', color='white', fontsize=16)
rect = patches.Rectangle((len(fechamento[0]) - 2, meta+10000), 2, 400000, linewidth=1, edgecolor=c, facecolor=c, alpha=1)
ax2.add_patch(rect)
ax2.set_xticklabels(fechamento[0], rotation=45)
ax2.yaxis.set_visible(False)
plt.tight_layout()

st.pyplot(bas)