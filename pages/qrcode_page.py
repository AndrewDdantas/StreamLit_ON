import streamlit as st
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer
from pyzbar import pyzbar
from PIL import Image

class QRCodeReader(VideoTransformerBase):
    def transform(self, frame):
        image = frame.to_image()
        decoded_objects = pyzbar.decode(image)
        for obj in decoded_objects:
            if obj.type == 'QRCODE':
                st.success(f"QR Code lido: {obj.data.decode('utf-8')}")
        return image

def main():
    st.title("Leitor de QR Code")
    st.sidebar.title("Configurações")

    webrtc_ctx = webrtc_streamer(
        key="example",
        video_transformer_factory=QRCodeReader,
        mode= "video",
        async_transform=True,
        object_detection_sample_rate=5,
        **{
            "audio": False,
        }
    )

if __name__ == "__main__":
    main()
