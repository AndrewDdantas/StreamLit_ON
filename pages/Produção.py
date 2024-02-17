import locale as lo
import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import numpy as np
from datetime import datetime, timedelta 
import streamlit as st
import matplotlib.pyplot as plt

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
        return lo.format_string(f"%0.{casas}f",valor,grouping=True)
    if tipo == 'NORMAL':
        return lo.format_string(f"%0.{casas}f",valor,grouping=True)
    if tipo == "PORCENTAGEM":
        return f"{{:.{casas}%}}".format(valor).replace('.',',')

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
dados_grade.columns = ['DTPROGRAMACAO', 'STATUS', 'OPERACAO', 'ID_CARGA',
                        'ORDEM', 'DTOFERECIMENTO', 'HROFERECIMENTO', 'FILIAL',
                                    'ROTA', 'LOTE', 'TURNO']
dados_grade = dados_grade.loc[dados_grade['DTPROGRAMACAO'] != '']
dados_grade['LOTE'] = dados_grade['LOTE'].astype(str)
dados_grade['DTPROGRAMACAO'] = dados_grade['DTPROGRAMACAO'] + '/2024' 
dados_grade['DTPROGRAMACAO'] = pd.to_datetime(dados_grade['DTPROGRAMACAO'], format='%d/%m/%Y')
dados_grade = dados_grade.sort_values('DTPROGRAMACAO')

BASE_STREAMLIT = client.open_by_key('19wq-kacGtgwRS8ZMUpDofA4rpOEMO4r_1SGBtcc7oxM') 
base = BASE_STREAMLIT.worksheet('STATUS_OPERAÇÃO')
base = base.get_values('A2:N')
wis = pd.DataFrame(base)
wis.columns = ['DATA_CORTE','LOTE','PROGRAMACAO','CUB_PROGRAMADA','PEDIDOS','SEPARADO','CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA','CANCELADO','PENDENTE_SEP','CUB_PENDENTE_SEP','PENDENTE_CONF','CUB_PENDENTE_CONF']
#wis = pd.read_csv('https://redash-inteligencia-comercial.luizalabs.com/api/queries/3298/results.csv?api_key=v7DWvNtOfySsUbGbiemzgJbfapQDyZeu77A9dOm0')
wis['LOTE'] = wis['LOTE'].astype(str)
wis[['PROGRAMACAO','CUB_PROGRAMADA','PEDIDOS','SEPARADO','CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA','CANCELADO','PENDENTE_SEP','CUB_PENDENTE_SEP','PENDENTE_CONF','CUB_PENDENTE_CONF']] = wis[['PROGRAMACAO','CUB_PROGRAMADA','PEDIDOS','SEPARADO','CUB_SEPARADA','CONFERIDO','CUB_CONFERIDA','CANCELADO','PENDENTE_SEP','CUB_PENDENTE_SEP','PENDENTE_CONF','CUB_PENDENTE_CONF']].apply(lambda x: x.str.replace(',','.')).astype(float)

join_dados = pd.merge(wis,dados_grade,how="inner", on="LOTE")

    
def definir_status(row):
    if row['PROGRAMACAO'] - row['SEPARADO'] <= 0 or row['STATUS'] == '7.Carreg. Finalizado':
        return 'SEPARADO'
    else:
        return 'PENDENTE'

join_dados['STATUS_AJUSTADO'] = join_dados.apply(definir_status, axis=1)

pendente = join_dados[join_dados['STATUS_AJUSTADO'] == 'PENDENTE']
pendente = pendente['DTPROGRAMACAO'].sort_values().unique()

hr = join_dados.groupby(['DTPROGRAMACAO','HROFERECIMENTO','DTOFERECIMENTO']).agg({'PROGRAMACAO':'sum', 'CUB_PROGRAMADA': 'sum', 'SEPARADO':'sum','CUB_SEPARADA':'sum'}).reset_index()
hr = hr.loc[hr['DTPROGRAMACAO'].isin(pendente)]
hr['OFERECIMENTO'] = hr['DTOFERECIMENTO'] +' '+hr['HROFERECIMENTO']
hr['PEN_PEÇAS'] = hr['PROGRAMACAO'] - hr['SEPARADO']
hr['PEN_CUB'] = hr['CUB_PROGRAMADA'] - hr['CUB_SEPARADA']
hr = hr[['DTPROGRAMACAO','OFERECIMENTO', 'PROGRAMACAO', 'CUB_PROGRAMADA', 'SEPARADO', 'CUB_SEPARADA', 'PEN_PEÇAS', 'PEN_CUB']]
hr['OFERECIMENTO'] = pd.to_datetime(hr['OFERECIMENTO'], format='%d/%m/%Y %H:%M')
hr = hr.sort_values('OFERECIMENTO')
hr['OFERECIMENTO'] = hr['OFERECIMENTO'].dt.time
hr['DTPROGRAMACAO'] = hr['DTPROGRAMACAO'].dt.strftime('%d/%m/%Y')
pendente = pendente.strftime('%d/%m/%Y')


st.session_state['pendentes'] = pendente
pecas_html = ''
cub_html = ''
o = 0
for i in pendente:
    
    df = hr[hr['DTPROGRAMACAO'] == i]
    pec_percen = fmt_num(df['SEPARADO'].sum() / df['PROGRAMACAO'].sum(), "PORCENTAGEM")
    pec_men = fmt_num( (1 - df['SEPARADO'].sum() / df['PROGRAMACAO'].sum()) , "PORCENTAGEM")
    pec_separado = df['SEPARADO'].sum()
    pec_programa = df['PROGRAMACAO'].sum()
    pec_pendente = df['PROGRAMACAO'].sum() - df['SEPARADO'].sum()
    pecas = df[['DTPROGRAMACAO', 'OFERECIMENTO', 'PROGRAMACAO', 'SEPARADO', 'PEN_PEÇAS']]
    pecas[['PROGRAMACAO', 'SEPARADO', 'PEN_PEÇAS']] = pecas[['PROGRAMACAO', 'SEPARADO', 'PEN_PEÇAS']].map(fmt_num, tipo='NORMAL')
    pec_html = pecas.to_html(classes="pec_con", index=False)


    cub_percen = fmt_num(df['CUB_SEPARADA'].sum() / df['CUB_PROGRAMADA'].sum(), "PORCENTAGEM")
    cub_men = fmt_num((1 - df['CUB_SEPARADA'].sum() / df['CUB_PROGRAMADA'].sum()), "PORCENTAGEM")
    cub_separado = fmt_num(df['CUB_SEPARADA'].sum(), 'CUBAGEM')
    cub_programa = fmt_num(df['CUB_PROGRAMADA'].sum(), 'CUBAGEM')
    cub_pendente = fmt_num(df['CUB_PROGRAMADA'].sum() - df['CUB_SEPARADA'].sum(), 'CUBAGEM')
    cubagem = df[['CUB_PROGRAMADA', 'CUB_SEPARADA', 'PEN_CUB']]
    cubagem = cubagem.map(fmt_num, tipo="CUBAGEM", casas=2)
    cubagem_html = cubagem.to_html(classes="cub_con", index=False)

    pecas_html += f"""
        <div class="tex">
        <h2>Peças</h2>
        <h2>{i}</h2>
        </div>
        <div class="Cab">
            <div class="itens">
                <h2>Programado</h2>
                <p>{fmt_num(pec_programa, 'NORMAL')}</p>
            </div>
            <div class="itens">
                <h2>Separado</h2>
                <p>{fmt_num(pec_separado, 'NORMAL')}</p>
            </div>
            <div class="itens">
                <h2>Pendente</h2>
                <p>{fmt_num(pec_pendente, 'NORMAL')}</p>
            </div>
        </div>
        <div class="cont">
            <div class="termometro">
                <div class="mercurio" style="background: linear-gradient(to left, rgb(192, 191, 191) {pec_men}, transparent {pec_percen});"></div>
                </div>
            </div>
        </div>
        """
    pecas_html += pec_html

    cub_html += f"""
        <div class="tex">
        <h2>Cubagem</h2>
        <h2>{i}</h2>
        </div>
        <div class="Cab">
            <div class="itens">
                <h2>Programado</h2>
                <p>{cub_programa}</p>
            </div>
            <div class="itens">
                <h2>Separado</h2>
                <p>{cub_separado}</p>
            </div>
            <div class="itens">
                <h2>Pendente</h2>
                <p>{cub_pendente}</p>
            </div>
        </div>
        <div class="cont">
            <div class="termometro">
                <div class="mercurio" style="background: linear-gradient(to left, rgb(192, 191, 191) {cub_men}, transparent {cub_percen});"></div>
                </div>
            </div>
        </div>
        """
    cub_html += cubagem_html
col1, col2 = st.columns(2)

col1.markdown(pecas_html, unsafe_allow_html=True)

col2.markdown(cub_html, unsafe_allow_html=True)


# Rort produção por turno.
base = BASE_STREAMLIT.worksheet('PRODUÇÃO_TURNO')
base = base.get_values('A2:F')
wis_turno = pd.DataFrame(base)
#wis_turno = pd.read_csv('https://redash-inteligencia-comercial.luizalabs.com/api/queries/3308/results.csv?api_key=GMn4FZUYx3uiUueVl9Xc5ZPtEXTM5d0sliwI0dkg')
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

hoje = datetime.now()
h = int(hoje.strftime('%H'))
if h <= 6:
    hoje = datetime.now() - timedelta(1)
else:
    hoje = datetime.now()
data_hoje = hoje.strftime('%Y-%m-%d')

join_turno = join_turno.loc[join_turno['DT_COMPETENCIA'] == data_hoje]

som = join_turno.groupby(['HORA']).agg({'QT_SEPARADO': 'sum', 'CUBAGEM': 'sum'}).reset_index()

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
ax[0].bar(som['HORA'].astype(int).sort_values().astype(str),som['QT_SEPARADO'])
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
ax[1].bar(som['HORA'].astype(int).sort_values().astype(str),som['CUBAGEM'])
ax[1].set_ylim(0,y)
ax[1].grid(False)
avg = fmt_num(som['CUBAGEM'].mean(), 'NORMAL',1)
avc = som['CUBAGEM'].mean()
smm = som['CUBAGEM'].sum()

for index, val in enumerate(som['CUBAGEM']):
    valu = fmt_num(val, 'CUBAGEM', 1)
    ax[1].text(index, val, f'{valu}', ha='center', va='bottom')
ax[1].axhline(y=avc, color='r', linestyle='--', label=f'Média: {avg}')
ax[1].legend([avg,smm],loc ="upper left")
ax[1].set_title(f'Cubagem')
fig.suptitle(f'Acompanhamento hora a hora {data}')

col2.pyplot(fig)


