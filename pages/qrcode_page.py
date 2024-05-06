import streamlit as st
from PIL import Image
import numpy as np

def main():
    st.title("Captura e Processamento de Imagem")

    # Usando o Streamlit para capturar a imagem da câmera
    st.write("Por favor, clique no botão abaixo para capturar a imagem da câmera:")
    capture_button = st.button("Capturar Imagem")

    # Se o botão for pressionado
    if capture_button:
        # Usando o Streamlit para capturar a imagem da câmera
        st.write("Capturando imagem da câmera...")
        image = st.image([], channels="BGR", caption="Imagem Capturada")
        image_container = st.empty()

        # Processando a imagem com OpenCV
        st.write("Processando imagem...")
        processed_image = process_image(image_container)

        # Exibindo a imagem processada
        st.image(processed_image, caption="Imagem Processada", use_column_width=True)

def process_image(image_container):
    # Capturando a imagem da câmera usando o Streamlit
    img = image_container.image_data

    # Convertendo a imagem para um formato adequado para processamento com OpenCV
    img_array = np.array(img)

    # Processando a imagem usando OpenCV (por exemplo, converter para escala de cinza)
    # Aqui você pode adicionar qualquer processamento adicional que desejar

    # Convertendo a imagem processada de volta para o formato adequado para exibição com Streamlit
    processed_img = Image.fromarray(img_array)

    return processed_img

if __name__ == "__main__":
    main()

