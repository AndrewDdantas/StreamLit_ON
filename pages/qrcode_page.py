import streamlit as st
import cv2
import numpy as np

def decode_qr_code(image):
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecodeMulti(image)
    return data

def main():
    st.title("Leitor de QR Code")

    st.markdown("# Capturar Imagem")
    capture = st.button("Capturar")

    if capture:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cap.release()
            st.sidebar.image(frame, channels="BGR", caption="Imagem Capturada")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            qr_code_data = decode_qr_code(gray)
            if qr_code_data:
                st.success(f"QR Code lido: {qr_code_data}")
            else:
                st.warning("Nenhum QR Code encontrado na imagem.")

if __name__ == "__main__":
    main()



