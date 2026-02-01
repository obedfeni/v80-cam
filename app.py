# v380_cloudinary_app.py
# Fixed Streamlit app for V380 camera with Cloudinary integration
# Requirements: pip install streamlit opencv-python cloudinary

import streamlit as st
import cv2
import cloudinary
import cloudinary.uploader
import numpy as np
import time
import io
from datetime import datetime
import threading
import queue

# --- Configuration ---
RTSP_URL = 'rtsp://your_username:your_password@your_camera_ip:554/live/ch00_1'
CLOUDINARY_CLOUD_NAME = 'your_cloud_name'
CLOUDINARY_API_KEY = 'your_api_key'
CLOUDINARY_API_SECRET = 'your_api_secret'

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# --- Session State ---
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False
if 'frame' not in st.session_state:
    st.session_state.frame = None
if 'upload_status' not in st.session_state:
    st.session_state.upload_status = ""
if 'last_url' not in st.session_state:
    st.session_state.last_url = None

# --- UI ---
st.title("📷 V380 Camera + Cloudinary")

# Sidebar
st.sidebar.header("Settings")
url_input = st.sidebar.text_input("RTSP URL", RTSP_URL, type="password")
quality = st.sidebar.selectbox("Quality", ["Low (ch00_1)", "High (ch00_0)"])

# Main area
col1, col2 = st.columns([3, 1])

with col1:
    frame_placeholder = st.empty()
    status = st.empty()

with col2:
    st.subheader("Controls")
    
    # Toggle camera
    if not st.session_state.camera_active:
        if st.button("▶️ Start", type="primary", use_container_width=True):
            st.session_state.camera_active = True
            st.rerun()
    else:
        if st.button("⏹️ Stop", type="secondary", use_container_width=True):
            st.session_state.camera_active = False
            st.rerun()
    
    # Capture button
    if st.button("📸 Capture", disabled=not st.session_state.camera_active, 
                 use_container_width=True):
        if st.session_state.frame is not None:
            with st.spinner("Uploading..."):
                try:
                    _, buffer = cv2.imencode('.jpg', st.session_state.frame)
                    img_bytes = io.BytesIO(buffer)
                    
                    result = cloudinary.uploader.upload(
                        img_bytes,
                        resource_type="image",
                        public_id=f"v380_{int(time.time())}"
                    )
                    
                    st.session_state.last_url = result['secure_url']
                    st.session_state.upload_status = "✅ Uploaded!"
                except Exception as e:
                    st.session_state.upload_status = f"❌ Error: {e}"
            st.rerun()
    
    # Status
    if st.session_state.upload_status:
        st.info(st.session_state.upload_status)
    
    # Last image
    if st.session_state.last_url:
        st.subheader("Last Upload")
        st.image(st.session_state.last_url, use_container_width=True)
        st.markdown(f"[Open]({st.session_state.last_url})")

# --- Camera Loop ---
def run_camera():
    # Adjust URL for quality
    url = url_input
    if "ch00_" in url:
        base = url.rsplit("ch00_", 1)[0]
        ch = "0" if "High" in quality else "1"
        url = f"{base}ch00_{ch}"
    
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        status.error("Failed to connect")
        st.session_state.camera_active = False
        return
    
    while st.session_state.camera_active:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        
        st.session_state.frame = frame.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
        time.sleep(0.03)
    
    cap.release()

# Run camera if active
if st.session_state.camera_active:
    run_camera()
