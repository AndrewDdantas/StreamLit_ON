import streamlit as st
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer
import cv2
from PIL import Image

def decode_qr_code(image):
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(image)
    return data

def main():
    st.title("Leitor de QR Code")
    webrtc_ctx = webrtc_streamer(
        key="example",
        video_transformer_factory=decode_qr_code,
        async_transform=True,
        **{
            "audio": False,
        }
    )

if __name__ == "__main__":
    main()

