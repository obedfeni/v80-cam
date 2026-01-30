# app.py - TEST VERSION with simulated camera feed
import os
os.environ['STREAMLIT_SERVER_ENABLECORS'] = 'false'
os.environ['STREAMLIT_SERVER_ENABLEXSRFPROTECTION'] = 'false'

import streamlit as st

# MUST BE FIRST STREAMLIT COMMAND
st.set_page_config(
    page_title="V380 Camera - TEST MODE",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clear cache
st.cache_data.clear()
st.cache_resource.clear()

import numpy as np
import cv2
import cloudinary
import cloudinary.uploader
import io
import time
from datetime import datetime

# --- Configuration ---
RTSP_URL = os.getenv('RTSP_URL', 'rtsp://demo:demo@192.168.1.100:554/live/ch00_1')
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')

# Configure Cloudinary only if credentials exist
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    cloudinary_ready = True
else:
    cloudinary_ready = False

# --- Session State ---
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False
if 'frame' not in st.session_state:
    st.session_state.frame = None
if 'last_url' not in st.session_state:
    st.session_state.last_url = None
if 'test_mode' not in st.session_state:
    st.session_state.test_mode = True

# --- UI ---
st.title("📷 V380 Camera + Cloudinary")
st.warning("⚠️ TEST MODE - Using simulated camera feed (No real camera connected)")

# Sidebar
st.sidebar.header("Settings")
st.sidebar.text_input("RTSP URL (hidden)", RTSP_URL, type="password", disabled=True)
st.sidebar.info("💡 Update RTSP_URL in Render environment variables when ready")

if cloudinary_ready:
    st.sidebar.success("☁️ Cloudinary: Connected")
else:
    st.sidebar.error("☁️ Cloudinary: Not configured\nAdd env vars in Render dashboard")

# Main area
col1, col2 = st.columns([3, 1])

with col1:
    frame_placeholder = st.empty()
    status_placeholder = st.empty()

with col2:
    st.subheader("Controls")
    
    # Toggle camera
    if not st.session_state.camera_active:
        if st.button("▶️ Start Test Stream", type="primary", use_container_width=True):
            st.session_state.camera_active = True
            st.rerun()
    else:
        if st.button("⏹️ Stop Stream", type="secondary", use_container_width=True):
            st.session_state.camera_active = False
            st.rerun()
    
    # Capture button
    capture_clicked = st.button(
        "📸 Capture & Upload", 
        disabled=not st.session_state.camera_active or not cloudinary_ready,
        use_container_width=True,
        help="Requires Cloudinary credentials" if not cloudinary_ready else "Capture frame"
    )
    
    if capture_clicked and st.session_state.frame is not None:
        with st.spinner("Uploading..."):
            try:
                _, buffer = cv2.imencode('.jpg', st.session_state.frame)
                img_bytes = io.BytesIO(buffer)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                result = cloudinary.uploader.upload(
                    img_bytes,
                    resource_type="image",
                    public_id=f"test_v380_{timestamp}",
                    folder="v380_test"
                )
                
                st.session_state.last_url = result['secure_url']
                st.success("✅ Uploaded!")
                
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")
    
    # Last upload
    if st.session_state.last_url:
        st.subheader("Last Upload")
        st.image(st.session_state.last_url, use_container_width=True)
        st.markdown(f"[Open]({st.session_state.last_url})")

# --- Simulated Camera Feed ---
def generate_test_frame(counter):
    """Generate a test pattern frame"""
    # Create 640x480 frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Moving gradient background
    offset = counter % 640
    for i in range(640):
        color = int(255 * ((i + offset) % 640) / 640)
        frame[:, i, 0] = color  # Blue channel
        frame[:, i, 1] = 128    # Green channel
        frame[:, i, 2] = 255 - color  # Red channel
    
    # Add timestamp text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = f"TEST MODE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    cv2.putText(frame, text, (50, 50), font, 0.8, (255, 255, 255), 2)
    
    # Add frame counter
    counter_text = f"Frame: {counter}"
    cv2.putText(frame, counter_text, (50, 100), font, 0.8, (0, 255, 0), 2)
    
    # Add "NO CAMERA" warning
    cv2.putText(frame, "NO CAMERA CONNECTED", (50, 240), font, 1.2, (0, 0, 255), 3)
    cv2.putText(frame, "Using simulated feed", (50, 280), font, 0.6, (200, 200, 200), 1)
    
    return frame

def run_test_camera():
    """Simulated camera loop"""
    status_placeholder.info("🎥 Test stream running (Simulated)")
    counter = 0
    
    while st.session_state.camera_active:
        frame = generate_test_frame(counter)
        st.session_state.frame = frame.copy()
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
        
        counter += 1
        time.sleep(0.1)  # 10 FPS

# Run camera if active
if st.session_state.camera_active:
    run_test_camera()
    frame_placeholder.empty()
    status_placeholder.info("⏹️ Stream stopped")

# Instructions for when you get the router IP
st.sidebar.markdown("---")
st.sidebar.subheader("Next Steps:")
st.sidebar.markdown("""
1. ✅ Fix this error first
2. 🏠 Get your router's public IP
3. 🔧 Set up port forwarding (port 554)
4. 📝 Update `RTSP_URL` in Render env vars
5. 🚀 Switch to real camera
""")
