import streamlit as st
import cv2
from pyzbar.pyzbar import decode
from PIL import Image

def decode_qr_code(image):
    data = decode(image)
    if data:
        return data[0].data.decode('utf-8')
    return None

def main():
    st.title("Leitor de QR Code")

    st.sidebar.markdown("# Capturar Imagem")
    capture = st.sidebar.button("Capturar")

    if capture:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cap.release()
            st.sidebar.image(frame, channels="BGR", caption="Imagem Capturada")
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            qr_code_data = decode_qr_code(image)
            if qr_code_data:
                st.success(f"QR Code lido: {qr_code_data}")
            else:
                st.warning("Nenhum QR Code encontrado na imagem.")

if __name__ == "__main__":
    main()


