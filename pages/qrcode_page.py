import streamlit as st
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer
import cv2

class QRCodeReader(VideoTransformerBase):
    def transform(self, frame):
        image = frame.to_ndarray(format="bgr24")
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(image)
        if data:
            st.success(f"QR Code lido: {data}")
        return image

def main():
    st.title("Leitor de QR Code")
    webrtc_ctx = webrtc_streamer(
        key="example",
        video_transformer_factory=QRCodeReader,
        async_transform=True,
        video_codec="h264",  # Especifica o codec de vídeo
    )
if __name__ == "__main__":
    main()

