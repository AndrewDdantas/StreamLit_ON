from pyzbar.pyzbar import decode
from PIL import Image
import streamlit as st
import json

# Cria uma lista vazia para armazenar os dados lidos dos QR codes
itens = []

# Função para ler o QR code de uma imagem e retornar os dados
def ler_qrcode(arquivo):
    img = Image.open(arquivo)
    resultado = decode(img)

    for result in resultado:
        dados = result.data.decode('utf-8')
        dados = dados.replace("'", '"')
        dados = json.loads(dados)
        return 'Dados do QR: ' + dados.get('<<CPF>>')

# Cria uma seção de formulário no Streamlit
with st.form('Teste'):
    # Adiciona um campo de upload de arquivo ao formulário
    arq = st.file_uploader('Arquivo')

    # Adiciona um botão de envio ao formulário
    button = st.form_submit_button('Enviar')

    # Verifica se o botão de envio foi pressionado
    if button:
        with st.spinner("Aguarde..."):
            # Chama a função para ler o QR code e armazena o resultado em 'dad'
            dad = ler_qrcode(arq)
            st.write(dad)
            # Adiciona o resultado à lista de itens
            itens.append(dad)

# Atualiza a lista exibida no Streamlit
st.write(itens)