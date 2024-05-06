import cv2
import streamlit as st
from qrcode import QRCode

def decode_qr_code(image):
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(image)
    return data

def main():
    st.title("Leitor de QR Code")

    video_capture = cv2.VideoCapture(0)

    while True:
        _, frame = video_capture.read()
        
        data = decode_qr_code(frame)
        
        if data:
            st.success(f"QR Code lido: {data}")
        
        # Exibir o frame na interface do Streamlit
        st.image(frame, channels="BGR", use_column_width=True)

if __name__ == "__main__":
    main()

