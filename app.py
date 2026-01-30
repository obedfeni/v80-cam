# app.py
# Production-ready Streamlit app for V380 camera with Cloudinary integration
# Deploy to Render.com

import streamlit as st
import cv2
import cloudinary
import cloudinary.uploader
import numpy as np
import time
import io
import os
from datetime import datetime
import threading
import queue

# --- Page Config MUST BE FIRST STREAMLIT COMMAND ---
st.set_page_config(
    page_title="V380 Camera + Cloudinary",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Configuration from Environment Variables (Secure) ---
# These will be set in Render's Environment Variables section
RTSP_URL = os.getenv('RTSP_URL', 'rtsp://your_username:your_password@your_camera_ip:554/live/ch00_1')
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', 'your_cloud_name')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', 'your_api_key')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', 'your_api_secret')

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
    st.session_status = ""
if 'last_url' not in st.session_state:
    st.session_state.last_url = None
if 'stop_signal' not in st.session_state:
    st.session_state.stop_signal = False

# --- UI ---
st.title("📷 V380 Camera + Cloudinary")

# Sidebar
st.sidebar.header("Settings")

# Use secrets for RTSP URL in production, text input for local testing
if os.getenv('RENDER'):
    st.sidebar.info("Using RTSP_URL from environment variables")
    url_input = RTSP_URL
else:
    url_input = st.sidebar.text_input("RTSP URL", RTSP_URL, type="password")

quality = st.sidebar.selectbox("Quality", ["Low (ch00_1)", "High (ch00_0)"])

# Cloudinary connection test
try:
    # Test Cloudinary config
    if CLOUDINARY_CLOUD_NAME != 'your_cloud_name':
        st.sidebar.success("☁️ Cloudinary configured")
    else:
        st.sidebar.warning("⚠️ Using placeholder Cloudinary config")
except Exception as e:
    st.sidebar.error(f"Cloudinary error: {e}")

# Main area
col1, col2 = st.columns([3, 1])

with col1:
    frame_placeholder = st.empty()
    status_placeholder = st.empty()

with col2:
    st.subheader("Controls")
    
    # Toggle camera
    if not st.session_state.camera_active:
        if st.button("▶️ Start Stream", type="primary", use_container_width=True):
            st.session_state.camera_active = True
            st.session_state.stop_signal = False
            st.rerun()
    else:
        if st.button("⏹️ Stop Stream", type="secondary", use_container_width=True):
            st.session_state.camera_active = False
            st.session_state.stop_signal = True
            st.rerun()
    
    # Capture button
    if st.button("📸 Capture & Upload", disabled=not st.session_state.camera_active, 
                 use_container_width=True):
        if st.session_state.frame is not None:
            with st.spinner("Uploading to Cloudinary..."):
                try:
                    # Convert frame to bytes
                    _, buffer = cv2.imencode('.jpg', st.session_state.frame)
                    img_bytes = io.BytesIO(buffer)
                    
                    # Upload to Cloudinary with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    public_id = f"v380_{timestamp}"
                    
                    result = cloudinary.uploader.upload(
                        img_bytes,
                        resource_type="image",
                        public_id=public_id,
                        folder="v380_camera"
                    )
                    
                    st.session_state.last_url = result['secure_url']
                    st.session_state.upload_status = "✅ Uploaded successfully!"
                    
                except Exception as e:
                    st.session_state.upload_status = f"❌ Error: {str(e)}"
            st.rerun()
    
    # Status display
    if st.session_state.get('upload_status'):
        if "✅" in st.session_state.upload_status:
            st.success(st.session_state.upload_status)
        else:
            st.error(st.session_state.upload_status)
    
    # Last uploaded image
    if st.session_state.last_url:
        st.subheader("Last Upload")
        st.image(st.session_state.last_url, use_container_width=True)
        st.markdown(f"[Open in Cloudinary]({st.session_state.last_url})")

# --- Camera Loop with proper cleanup ---
def run_camera():
    # Adjust URL for quality selection
    url = url_input
    if "ch00_" in url:
        base = url.rsplit("ch00_", 1)[0]
        ch = "0" if "High" in quality else "1"
        url = f"{base}ch00_{ch}"
    
    # OpenCV Video Capture with timeout settings
    cap = cv2.VideoCapture(url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Set connection timeout (3 seconds)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
    
    if not cap.isOpened():
        status_placeholder.error("❌ Failed to connect to camera. Check RTSP URL.")
        st.session_state.camera_active = False
        return
    
    status_placeholder.info("🎥 Camera connected - Streaming...")
    
    frame_count = 0
    while st.session_state.camera_active and not st.session_state.stop_signal:
        ret, frame = cap.read()
        if not ret:
            frame_count += 1
            if frame_count > 30:  # Allow some buffer frames
                status_placeholder.warning("⚠️ Connection lost. Retrying...")
                time.sleep(1)
                break
            continue
        
        frame_count = 0
        st.session_state.frame = frame.copy()
        
        # Convert BGR to RGB for Streamlit
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Display frame
        frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
        
        # Control frame rate (~15 FPS)
        time.sleep(0.066)
    
    # Cleanup
    cap.release()
    frame_placeholder.empty()
    status_placeholder.info("⏹️ Stream stopped")
    st.session_state.camera_active = False

# Run camera if active
if st.session_state.camera_active:
    run_camera()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("🔧 [Render Deployment Guide](https://render.com/docs/deploy-streamlit)")
