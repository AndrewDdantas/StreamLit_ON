import gspread as gs
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.patches as patches

st.set_page_config(
    page_title="Meu App Streamlit",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",  # Pode ser "wide" ou "centered"
    initial_sidebar_state="auto",  # Pode ser "auto", "expanded", ou "collapsed"
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

sheet = client.open_by_key('1gPbStQWesvP3SyUB9r3RmiqHTKncrfFoOlCo_kzaRMU')
worksheet = sheet.worksheet('Base SQL')


data = worksheet.get_values('a:p')

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

fig = plt.figure(layout="constrained", figsize=(30, 12))

gs = GridSpec(3, 6, figure=fig)
ax1 = fig.add_subplot(gs[:1, :3])
ax2 = fig.add_subplot(gs[0:3, 3:-1])
ax3 = fig.add_subplot(gs[1:3, :-3])
ax4 = fig.add_subplot(gs[0:3, 5:])

rectangle1 = patches.Rectangle((0.15, 0.2), 0.3, 0.3, linewidth=1, edgecolor='none', facecolor='#ED7D31')
rectangle2 = patches.Rectangle((0.15, 0.6), 0.3, 0.3, linewidth=1, edgecolor='none', facecolor='#00B0F0')
rectangle3 = patches.Rectangle((0.55, 0.2), 0.3, 0.3, linewidth=1, edgecolor='none', facecolor='red')
rectangle4 = patches.Rectangle((0.55, 0.6), 0.3, 0.3, linewidth=1, edgecolor='none', facecolor='green')

ax1.add_patch(rectangle1)
ax1.add_patch(rectangle2)
ax1.add_patch(rectangle3)
ax1.add_patch(rectangle4)

rectangle1 = patches.Rectangle((0, 0.81), 1, 0.17, linewidth=1, edgecolor='none', facecolor='#00B0F0')
rectangle2 = patches.Rectangle((0, 0.61), 1, 0.17, linewidth=1, edgecolor='none', facecolor='#00B0F0')
rectangle3 = patches.Rectangle((0, 0.41), 1, 0.17, linewidth=1, edgecolor='none', facecolor='#00B0F0')
rectangle4 = patches.Rectangle((0, 0.21), 1, 0.17, linewidth=1, edgecolor='none', facecolor='#00B0F0')
rectangle5 = patches.Rectangle((0, 0.01), 1, 0.17, linewidth=1, edgecolor='none', facecolor='#00B0F0')

ax4.add_patch(rectangle1)
ax4.add_patch(rectangle2)
ax4.add_patch(rectangle3)
ax4.add_patch(rectangle4)
ax4.add_patch(rectangle5)

ax1.text(0.3, 0.75, f'Total Pedidos\n{total}', ha='center', va='center', fontsize=25, color='white', weight='bold')
ax1.text(0.3, 0.35, f'Vence Hoje\n{vence}', ha='center', va='center', fontsize=25, color='white', weight='bold')
ax1.text(0.7, 0.75, f'A Vencer\n{a_vence}', ha='center', va='center', fontsize=25, color='white', weight='bold')
ax1.text(0.7, 0.35, f'Vencidos\n{venci}', ha='center', va='center', fontsize=25, color='white', weight='bold')

ax4.text(0.5, 0.89, f'Total Pedidos\n{df2[0][0]}', ha='center', va='center', fontsize=40, color='white', weight='bold')
ax4.text(0.5, 0.69, f'Pendentes\n{df2[1][0]}', ha='center', va='center', fontsize=40, color='white', weight='bold')
ax4.text(0.5, 0.49, f'%NS\n{df2[2][0]}', ha='center', va='center', fontsize=40, color='white', weight='bold')
ax4.text(0.5, 0.29, f'Saldo Meta (%)\n{df2[3][0]}', ha='center', va='center', fontsize=30, color='white', weight='bold')
ax4.text(0.5, 0.09, f'Saldo de Pendentes\npara meta(Pedidos)\n{df2[4][0]}', ha='center', va='center', fontsize=30, color='white', weight='bold')

ax1.axis('off')
ax2.axis('off')
ax3.axis('off')
ax4.axis('off')

tabela1 = ax2.table(cellText=trans.values, colLabels=trans.columns, loc='upper left')
tabela1.auto_set_font_size(False)
tabela1.set_fontsize(15)
tabela1.scale(1, 2)

for (i,j), cell in tabela1._cells.items():
    cell.get_text().set_ha('center')
    if i == 0:
        if j == 1:
            cell.set_fontsize(17)
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor('green')
            cell.get_text().set_ha('center')
        elif j == 2:
            cell.set_fontsize(17)
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor('#ED7D31')
            cell.get_text().set_ha('center')
        elif j == 3:
            cell.set_fontsize(17)
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor('red')
            cell.get_text().set_ha('center')
        else:
            cell.set_fontsize(17)
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor('#00B0F0')
            cell.get_text().set_ha('center')

    else:
        cell.set_text_props(weight='bold', color='black')


for i in range(len(trans)+1):
    for o in range(len(trans.columns)):
        if o > 0:
            cell = tabela1[(i, o)]
            cell.set_width(0.17)
        else:
            cell = tabela1[(i, 0)]
            cell.set_width(0.3)



tabela2 = ax3.table(cellText=data.values, colLabels=data.columns, loc='upper left')
tabela2.auto_set_font_size(False)
tabela2.set_fontsize(15)
tabela2.scale(1, 2)


for key, cell in tabela2.get_celld().items():
    if key[0] == 0:
        cell.get_text().set_text('\n'.join(cell.get_text().get_text().split()))

for (i,j), cell in tabela2._cells.items():
    cell.get_text().set_ha('center')
    if i == 0:
        cell.set_fontsize(17)
        cell.set_text_props(weight='bold', color='w')
        cell.set_facecolor('#00B0F0')
        cell.get_text().set_ha('center')
    else:
        cell.set_text_props(weight='bold', color='black')

for o in range(min(len(data), len(data.columns))):
    cell = tabela2[(0, o)]
    cell.set_height(0.1)


fig.suptitle("Preventivo Entregas", fontsize=40)


st.pyplot(fig)