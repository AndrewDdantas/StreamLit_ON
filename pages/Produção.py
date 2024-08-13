import locale as lo
import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime, timedelta 
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

def term(ax, atual, alvo, data):

    if atual / alvo <= 0.2:
        cor_termometro_cheio = 'red'
    elif atual / alvo <= 0.7:
        cor_termometro_cheio = 'yellow'
    else:
        cor_termometro_cheio = 'green'

    # Adicionando barras do termômetro
    ax.barh(0.5, (atual / alvo) * 100, 1, color=cor_termometro_cheio, edgecolor='black')
    ax.barh(0.5, (100 - (atual / alvo) * 100), 1, left=(atual / alvo) * 100, color='lightgray', edgecolor='black')

    # Ajustando os limites dos eixos
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    faltando = alvo - atual
    faltando = fmt_num(faltando, 'NORMAL', 1)
    alvo = fmt_num(alvo, 'NORMAL', 1)
    atual = fmt_num(atual, 'NORMAL', 1)
    # Adicionando texto
    ax.text(50, 1.2, f'Programado: {alvo}      Separado: {atual}       Faltando: {faltando}',
            ha='center', va='center', fontsize=20)
    ax.text(50, 1.2+0.25, f'{data}',
            ha='center', va='center', fontsize=30)

def table(ax, dados):
    ax.axis('off')
    tabela = ax.table(cellText=dados.values, colLabels=dados.columns, loc='upper left')
    tabela.auto_set_font_size(False)
    tabela.auto_set_column_width(col=list(range(len(dados.columns))))
    tabela.set_fontsize(14)
    tabela.scale(1,3)
    ax.set_ylim(-10000, 100000)
    for (i,j), cell in tabela._cells.items():
        cell.get_text().set_ha('center')
        if i == 0 or i ==  max(key[0] for key in tabela._cells.keys()):
            cell.set_fontsize(14)
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor('#00B0F0')
            cell.get_text().set_ha('center')
        else:
            cell.set_text_props(weight='bold', color='black')

st.set_page_config(
    page_title="Produção",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="auto",  # Pode ser "auto", "expanded", ou "collapsed"
)

with open('style.css', 'r') as f: #abre o css
    css_string = f.read()


# Injetar o CSS no Streamlit
st.markdown(f'<style>{css_string}</style>', unsafe_allow_html=True)
# funções 

def fmt_num(valor, tipo, casas=0): # Função para formatar números.
    if tipo == 'REAL':
        return lo.format_string(f"R$ %0.{casas}f",valor,grouping=True)
    if tipo == 'CUBAGEM':
        return "{:,.1f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == 'NORMAL':
        return "{:,.0f}".format(valor).replace(',', 'X').replace('.', ',').replace('X', '.')
    if tipo == "PORCENTAGEM":
        return f"{{:.{casas}%}}".format(valor).replace('.',',')

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

# Baixando informações da grade
planilha = client.open_by_key(st.secrets['grade']) 
grade = planilha.worksheet('Dados_consolidado')
dados_grade = grade.get_values('b3:k')
dados_grade = pd.DataFrame(dados_grade)
dados_grade.columns = ['DTPROGRAMACAO', 'STATUS', 'OPERACAO', 'ID_CARGA', 'DTOFERECIMENTO', 'HROFERECIMENTO', 'FILIAL',
                                    'ROTA', 'LOTE', 'TURNO']
dados_grade = dados_grade.loc[dados_grade['DTPROGRAMACAO'] != '']
dados_grade['LOTE'] = dados_grade['LOTE'].astype(str)
dados_grade['DTPROGRAMACAO'] = dados_grade['DTPROGRAMACAO'] + '/2024' 
dados_grade['DTPROGRAMACAO'] = pd.to_datetime(dados_grade['DTPROGRAMACAO'], format='%d/%m/%Y')
dados_grade = dados_grade.sort_values('DTPROGRAMACAO')

BASE_STREAMLIT = client.open_by_key(st.secrets['bases']) 
base = BASE_STREAMLIT.worksheet('STATUS_OPERAÇÃO')
base = base.get_values('A2:N')
wis = pd.DataFrame(base)
wis.columns = ['DATA_CORTE','LOTE','PROGRAMACAO','CUB_PROGRAMADA','PEDIDOS','SEPARADO','CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA','PENDENTE_SEP','CUB_PENDENTE_SEP','PENDENTE_CONF','CUB_PENDENTE_CONF']
wis['LOTE'] = wis['LOTE'].astype(str)
wis[['PROGRAMACAO','CUB_PROGRAMADA','PEDIDOS','SEPARADO','CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA','PENDENTE_SEP','CUB_PENDENTE_SEP','PENDENTE_CONF','CUB_PENDENTE_CONF']] = wis[['PROGRAMACAO','CUB_PROGRAMADA','PEDIDOS','SEPARADO','CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA','PENDENTE_SEP','CUB_PENDENTE_SEP','PENDENTE_CONF','CUB_PENDENTE_CONF']].apply(lambda x: x.str.replace(',','.')).astype(float)

join_dados = pd.merge(wis,dados_grade,how="inner", on="LOTE")

priorizacao = BASE_STREAMLIT.worksheet('PRIORIZAÇÃO')
priorizacao = priorizacao.get_values('a1:ac')
priorizacao = pd.DataFrame(priorizacao[1:], columns=priorizacao[0]) 
priorizacao = pd.pivot_table(priorizacao,'VARIAVEL', ['DT_CARREGAMENTO_PCP','DOCAS'],['DS_APLICACAO','PRIORIZADO'], 'nunique')
  
def definir_status(row):
    if row['PROGRAMACAO'] - row['CONFERIDO'] <= 0: 
        return 'SEPARADO'
    else:
        return 'PENDENTE'

join_dados['STATUS_AJUSTADO'] = join_dados.apply(definir_status, axis=1)

pendente = join_dados[join_dados['STATUS_AJUSTADO'] == 'PENDENTE']

pendente = pendente['DTPROGRAMACAO'].sort_values().unique()

hr = join_dados.groupby(['DTPROGRAMACAO','HROFERECIMENTO','DTOFERECIMENTO']).agg({'ID_CARGA':'nunique', 'PROGRAMACAO':'sum', 'CUB_PROGRAMADA': 'sum', 'SEPARADO':'sum','CONFERIDO':'sum', 'CUB_SEPARADA':'sum','CUB_CONFERIDA':'sum'}).reset_index()
hr = hr.loc[hr['DTPROGRAMACAO'].isin(pendente)]
hr['OFERECIMENTO'] = hr['DTOFERECIMENTO'] +' '+hr['HROFERECIMENTO']
hr = hr[['DTPROGRAMACAO','ID_CARGA','OFERECIMENTO', 'PROGRAMACAO', 'CUB_PROGRAMADA', 'SEPARADO', 'CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA']]
hr['OFERECIMENTO'] = pd.to_datetime(hr['OFERECIMENTO'], format='%d/%m/%Y %H:%M')
hr = hr.sort_values('OFERECIMENTO')
hr['OFERECIMENTO'] = hr['OFERECIMENTO'].dt.time
hr['DTPROGRAMACAO'] = hr['DTPROGRAMACAO'].dt.strftime('%d/%m/%Y')
data_dist = pendente.strftime('%d/%m/%Y')


v = 5*len(data_dist)
if len(data_dist) > 3: 
    tea = 25+v
else:
    tea = 20+v
fig = plt.figure(figsize=(35, tea))


i = 1
c = 0
r = 1
t = 3
while i <= len(data_dist):
    
    gs1 = GridSpec(3*len(data_dist), 4, wspace=1, hspace=1)
    ax1 = fig.add_subplot(gs1[c:r, :2])
    ax2 = fig.add_subplot(gs1[r:t, :2])
    ax3 = fig.add_subplot(gs1[c:r, 2:4])
    ax4 = fig.add_subplot(gs1[r:t, 2:4])
    te = hr.loc[hr['DTPROGRAMACAO'] == data_dist[i-1]]
    term(ax1, te['SEPARADO'].sum(), te['PROGRAMACAO'].sum(), data_dist[i-1])
    term(ax3, te['CUB_SEPARADA'].sum(), te['CUB_PROGRAMADA'].sum(), data_dist[i-1])

    
    pecas = te[['DTPROGRAMACAO','OFERECIMENTO','ID_CARGA', 'PROGRAMACAO', 'SEPARADO','CONFERIDO']]
    pecas["% SEP"] = pecas['SEPARADO'] / pecas['PROGRAMACAO']
    pecas["% CONF"] = pecas['CONFERIDO'] / pecas['PROGRAMACAO']
    pecas['PEND SEP'] = pecas['PROGRAMACAO'] - pecas['SEPARADO'] 
    pecas['PEND CONF'] = pecas['PROGRAMACAO'] - pecas['CONFERIDO']
    total_pecas = pecas[['ID_CARGA','PROGRAMACAO', 'SEPARADO','CONFERIDO','PEND SEP','PEND CONF']].sum()
    media_pecas = pecas[["% SEP","% CONF"]].mean()

    total_row = pd.DataFrame([['Total']+['-'] + total_pecas.tolist()+media_pecas.tolist()])
    total_row = total_row[[0,1,2,3,4,5,8,6,7,9]]
    total_row.columns = ['DTPROGRAMACAO','OFERECIMENTO', 'ID_CARGA', 'PROGRAMACAO', 'SEPARADO','PEND SEP','% SEP','CONFERIDO','PEND CONF','% CONF']

    pecas = pecas[['DTPROGRAMACAO', 'OFERECIMENTO', 'ID_CARGA', 'PROGRAMACAO', 'SEPARADO','PEND SEP','% SEP','CONFERIDO','PEND CONF','% CONF']]
    pecas = pd.concat([pecas,total_row], ignore_index=True)
    
    pecas.loc[:, '% SEP'] = pecas['% SEP'].apply(fmt_num, tipo='PORCENTAGEM', casas=1)
    pecas.loc[:, '% CONF'] = pecas['% CONF'].apply(fmt_num, tipo='PORCENTAGEM', casas=1)
    pecas.loc[:, 'PROGRAMACAO'] = pecas['PROGRAMACAO'].apply(fmt_num, tipo='NORMAL')
    pecas.loc[:, 'SEPARADO'] = pecas['SEPARADO'].apply(fmt_num, tipo='NORMAL')
    
    pecas.columns = ['DT_PROG', 'OFEREC',  'CARGAS','PEÇAS_PROG', 'SEPARADO', 'PEND SEP','% SEP', 'CONFERIDO','PEND CONF','% CONF']

    cubagem = te[['CUB_PROGRAMADA', 'CUB_SEPARADA','CUB_CONFERIDA']]
    cubagem['% SEP'] = cubagem['CUB_SEPARADA'] / cubagem['CUB_PROGRAMADA']
    cubagem['% CONF'] = cubagem['CUB_CONFERIDA'] / cubagem['CUB_PROGRAMADA']
    cubagem['PEND SEP'] = cubagem['CUB_PROGRAMADA'] - cubagem['CUB_SEPARADA']
    cubagem['PEND CONF'] = cubagem['CUB_PROGRAMADA'] - cubagem['CUB_CONFERIDA'] 
    cubagem_total = cubagem[['CUB_PROGRAMADA', 'CUB_SEPARADA','PEND SEP','CUB_CONFERIDA','PEND CONF']].sum()
    cubagem_media = cubagem[['% SEP','% CONF']].mean()
    cubagem_row = pd.DataFrame([cubagem_total.tolist()+cubagem_media.tolist()])
    cubagem_row = cubagem_row[[0,1,2,5,3,4,6]]
    cubagem_row.columns = ['CUB_PROGRAMADA', 'CUB_SEPARADA','PEND SEP','% SEP','CUB_CONFERIDA','PEND CONF','% CONF']
    cubagem = pd.concat([cubagem,cubagem_row], ignore_index=True)
    
    cubagem.loc[:, 'CUB_CONFERIDA'] = cubagem['CUB_CONFERIDA'].apply(fmt_num, tipo='CUBAGEM', casas=2)
    cubagem.loc[:, '% SEP'] = cubagem['% SEP'].apply(fmt_num, tipo='PORCENTAGEM', casas=1)
    cubagem.loc[:, '% CONF'] = cubagem['% CONF'].apply(fmt_num, tipo='PORCENTAGEM', casas=1)
    cubagem.loc[:, 'CUB_PROGRAMADA'] = cubagem['CUB_PROGRAMADA'].apply(fmt_num, tipo='CUBAGEM', casas=2)
    cubagem.loc[:, 'CUB_SEPARADA'] = cubagem['CUB_SEPARADA'].apply(fmt_num, tipo='CUBAGEM', casas=2)
    cubagem.loc[:, 'PEND SEP'] = cubagem['PEND SEP'].apply(fmt_num, tipo='CUBAGEM', casas=2)
    cubagem.loc[:, 'PEND CONF'] = cubagem['PEND CONF'].apply(fmt_num, tipo='CUBAGEM', casas=2)
    cubagem = cubagem[['CUB_PROGRAMADA', 'CUB_SEPARADA','PEND SEP','% SEP','CUB_CONFERIDA','PEND CONF','% CONF']]

    table(ax2, pecas)
    table(ax4, cubagem)
    
    i += 1
    c = c+3
    r = r+3
    t = t+3
st.text('Status Produção CD 2650')
st.pyplot(fig)

# Rort produção por turno.
base = BASE_STREAMLIT.worksheet('PRODUÇÃO_TURNO')
base = base.get_values('A2:F')
wis_turno = pd.DataFrame(base)
wis_turno.columns = ['DT_COMPETENCIA','LOTE','TURNO','QT_SEPARADO','CUBAGEM','HORA']
wis_turno['LOTE'] = wis_turno['LOTE'].astype(str)
wis_turno[['QT_SEPARADO','CUBAGEM']] = wis_turno[['QT_SEPARADO','CUBAGEM']].apply(lambda x: x.str.replace(',','.')).astype(float)
join_turno = pd.merge(wis_turno,dados_grade,how='inner', on='LOTE')

join_turno['DTPROGRAMACAO'] = pd.to_datetime(join_turno['DTPROGRAMACAO'], format='%d/%m/%Y')
condicao = [(join_turno['DTPROGRAMACAO'] == join_turno['DT_COMPETENCIA']),
            (join_turno['DTPROGRAMACAO'] > join_turno['DT_COMPETENCIA']),
            (join_turno['DTPROGRAMACAO'] < join_turno['DT_COMPETENCIA'])]

opcap = ['PRODUÇÃO\nDIA','ADIANTADO','ATRASADO']
opcap2 = ['b','c','a']
join_turno['STATUS'] = np.select(condicao,opcap)
join_turno['sort'] = np.select(condicao,opcap2)

hoje = datetime.now() - timedelta(hours=3)
h = int(hoje.strftime('%H'))
if h <= 6:
    hoje = datetime.now() - timedelta(1)
else:
    hoje = datetime.now()
data_hoje = hoje.strftime('%Y-%m-%d')

join_turno = join_turno.loc[join_turno['DT_COMPETENCIA'] == data_hoje]

som = join_turno.groupby(['HORA']).agg({'QT_SEPARADO': 'sum', 'CUBAGEM': 'sum'}).reset_index()
som['HORA'] = som['HORA'].astype(int)
som = som.sort_values('HORA')

soma_m = join_turno.groupby(['TURNO_x','DT_COMPETENCIA','STATUS','sort']).agg({'QT_SEPARADO': 'sum', 'CUBAGEM': 'sum'}).reset_index().sort_values('sort')
soma_m = soma_m[['TURNO_x','DT_COMPETENCIA','STATUS','QT_SEPARADO','CUBAGEM']]

unique_data = soma_m['DT_COMPETENCIA'].unique()
o = 0


for i in unique_data:
    o += 1
    dt = i
    soma_l = soma_m[soma_m['DT_COMPETENCIA'] == dt]
    soma_f = soma_m.groupby(['TURNO_x']).agg({'QT_SEPARADO': 'sum', 'CUBAGEM': 'sum'}).reset_index()
    
    fig, axs = plt.subplots(2, len(soma_f), figsize=(len(soma_f)*5, 10))
    
    for i, (_, row) in enumerate(soma_f.iterrows()):
        turno = row['TURNO_x']
        data = pd.to_datetime(soma_l['DT_COMPETENCIA'].iloc[0], format='%Y-%m-%d').strftime('%d/%m/%Y')
        turno_df = soma_l[soma_l['TURNO_x'] == turno]

        # Plot QT_SEPARADO
        if len(soma_f) == 1:
            ax1 = axs[0]
        else:
            ax1 = axs[0, i]
        ax1.bar(turno_df['STATUS'], turno_df['QT_SEPARADO'])
        ax1.grid(False)
        for index, value in enumerate(turno_df['QT_SEPARADO']):
            valu = fmt_num(value,'NORMAL')
            ax1.text(index, value, f'{valu}', ha='center', va='bottom')
        ax1.set_title(f'{turno} do dia {data}')
        y = max(turno_df['QT_SEPARADO'])*1.2
        ax1.set_ylim(0, y)
        smm = turno_df['QT_SEPARADO'].sum()
        smm = fmt_num(smm, 'NORMAL')
        ax1.legend([smm])

        # Plot CUBAGEM
        if len(soma_f) == 1:
            ax2 = axs[1]
        else:
            ax2 = axs[1,i]
        
        ax2.bar(turno_df['STATUS'], turno_df['CUBAGEM'])
        ax2.grid(False)
        for index, value in enumerate(turno_df['CUBAGEM']):
            valu = fmt_num(value,'CUBAGEM',1)
            ax2.text(index, value, f'{valu}', ha='center', va='bottom')
        ax2.set_title(f'{turno} do dia {data}')
        y = max(turno_df['CUBAGEM'])*1.2
        ax2.set_ylim(0, y)
        smm = turno_df['CUBAGEM'].sum()
        smm = fmt_num(smm, 'CUBAGEM', 1)
        ax2.legend([smm])


    plt.tight_layout()
col1, col2 = st.columns(2)
col1.pyplot(fig)

fig, ax = plt.subplots(2, 1, figsize=(2+len(som['QT_SEPARADO'])*0.9, 10))
ax[0].bar(som['HORA'].astype(str),som['QT_SEPARADO'])
ax[0].grid(False)
y = max(som['QT_SEPARADO'])*1.2
ax[0].set_ylim(0,y)
for index, val in enumerate(som['QT_SEPARADO']):
    valu = fmt_num(val, 'NORMAL')
    ax[0].text(index, val, f'{valu}', ha='center', va='bottom')
avg = fmt_num(som['QT_SEPARADO'].mean(), 'NORMAL',1)
avc = som['QT_SEPARADO'].mean()
smm = som['QT_SEPARADO'].sum()
ax[0].axhline(y=avc, color='r', linestyle='--', label=f'Média: {avg}')
ax[0].legend([f'Média {avg}',f'Total {smm}'],loc ="upper left")
ax[0].set_title(f'Peças')

y = max(som['CUBAGEM'])*1.2
ax[1].bar(som['HORA'].astype(str),som['CUBAGEM'])
ax[1].set_ylim(0,y)
ax[1].grid(False)
avg = fmt_num(som['CUBAGEM'].mean(), 'NORMAL',1)
avc = som['CUBAGEM'].mean()
smm = fmt_num(som['CUBAGEM'].sum(), 'NORMAL',1)

for index, val in enumerate(som['CUBAGEM']):
    valu = fmt_num(val, 'CUBAGEM', 1)
    ax[1].text(index, val, f'{valu}', ha='center', va='bottom')
ax[1].axhline(y=avc, color='r', linestyle='--', label=f'Média: {avg}')
ax[1].legend([avg,smm],loc ="upper left")
ax[1].set_title(f'Cubagem')
fig.suptitle(f'Acompanhamento hora a hora {data}')

col2.pyplot(fig)


ba = join_dados.groupby(['DTPROGRAMACAO','HROFERECIMENTO','DTOFERECIMENTO','LOTE']).agg({'PROGRAMACAO':'sum', 'CUB_PROGRAMADA': 'sum', 'SEPARADO':'sum','CUB_SEPARADA':'sum'}).reset_index()
ba = ba.loc[ba['DTPROGRAMACAO'].isin(pendente)]
ba['Pendente'] = ba['PROGRAMACAO'] - ba['SEPARADO'] 
ba = ba.loc[ba['Pendente'] > 0]

st.dataframe(ba)
st.dataframe(priorizacao)
