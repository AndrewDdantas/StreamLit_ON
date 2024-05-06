import streamlit as st
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer
import cv2

class QRCodeReader(VideoTransformerBase):
    def transform(self, frame):
        image = frame.to_ndarray(format="bgr24")
        data = decode_qr_code(image)
        if data:
            st.success(f"QR Code lido: {data}")
        return frame

def main():
    st.title("Leitor de QR Code")
    webrtc_ctx = webrtc_streamer(
        key="example",
        video_transformer_factory=QRCodeReader,
        async_transform=True,
    )
if __name__ == "__main__":
    main()

