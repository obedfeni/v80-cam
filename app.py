# v380_cloudinary_app.py
# Fixed Streamlit app for V380 camera with Cloudinary integration
# Requirements: pip install streamlit opencv-python cloudinary python-dotenv

import streamlit as st
import cv2
import cloudinary
import cloudinary.uploader
import numpy as np
import time
import io
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables (optional - for security)
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="V380 Camera + Cloudinary",
    page_icon="📷",
    layout="wide"
)

# --- Configuration ---
# Option 1: Use environment variables (recommended for deployment)
# RTSP_URL = os.getenv('RTSP_URL', 'rtsp://admin:password@192.168.1.100:554/live/ch00_1')
# CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
# CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
# CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

# Option 2: Hardcoded (easier for testing, but less secure)
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

# --- Session State Initialization ---
if 'camera_running' not in st.session_state:
    st.session_state.camera_running = False
if 'last_uploaded_url' not in st.session_state:
    st.session_state.last_uploaded_url = None
if 'frame' not in st.session_state:
    st.session_state.frame = None
if 'capture_requested' not in st.session_state:
    st.session_state.capture_requested = False

# --- Sidebar Configuration ---
st.sidebar.title("⚙️ Configuration")

# RTSP URL input
rtsp_url = st.sidebar.text_input("RTSP URL", value=RTSP_URL, type="password")
st.sidebar.caption("Format: rtsp://username:password@ip:port/path")

# Stream settings
stream_quality = st.sidebar.selectbox(
    "Stream Quality",
    ["High (ch00_0)", "Low (ch00_1)"],
    index=1
)

# Auto-retry settings
enable_retry = st.sidebar.checkbox("Auto-reconnect on failure", value=True)
max_retries = st.sidebar.number_input("Max retries", min_value=1, max_value=10, value=5)

# --- Main App Layout ---
st.title("📷 V380 Camera with Cloudinary Integration")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live Feed")
    video_placeholder = st.empty()
    status_placeholder = st.empty()

with col2:
    st.subheader("Controls")
    
    # Start/Stop camera button
    if not st.session_state.camera_running:
        if st.button("▶️ Start Camera", type="primary", use_container_width=True):
            st.session_state.camera_running = True
            st.rerun()
    else:
        if st.button("⏹️ Stop Camera", type="secondary", use_container_width=True):
            st.session_state.camera_running = False
            st.rerun()
    
    # Capture button (only enabled when camera is running)
    capture_disabled = not st.session_state.camera_running
    if st.button("📸 Capture & Upload", 
                 disabled=capture_disabled,
                 type="primary" if not capture_disabled else "secondary",
                 use_container_width=True):
        st.session_state.capture_requested = True
        st.rerun()
    
    # Status display
    st.subheader("Status")
    status_text = st.empty()
    
    # Last uploaded image display
    if st.session_state.last_uploaded_url:
        st.subheader("Last Upload")
        st.image(st.session_state.last_uploaded_url, use_container_width=True)
        st.caption(f"Uploaded at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown(f"[View in Cloudinary]({st.session_state.last_uploaded_url})")

# --- Camera Logic ---
def get_rtsp_url(base_url, quality):
    """Adjust stream path based on quality selection"""
    if "ch00_" in base_url:
        base = base_url.rsplit('ch00_', 1)[0]
        suffix = "0" if quality == "High (ch00_0)" else "1"
        return f"{base}ch00_{suffix}"
    return base_url

def upload_to_cloudinary(frame, timestamp):
    """Upload frame to Cloudinary"""
    try:
        # Convert frame to bytes
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        img_bytes = io.BytesIO(buffer)
        
        # Generate unique public_id
        public_id = f"v380_snapshot_{timestamp}_{int(time.time())}"
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            img_bytes,
            resource_type="image",
            public_id=public_id,
            folder="v380_snapshots"  # Organizes uploads in a folder
        )
        
        return upload_result['secure_url']
    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {str(e)}")

def process_camera():
    """Main camera processing loop"""
    url = get_rtsp_url(rtsp_url, stream_quality)
    cap = cv2.VideoCapture(url)
    
    # Set buffer size to reduce latency
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        status_text.error("❌ Failed to open RTSP stream. Check URL and camera.")
        st.session_state.camera_running = False
        return
    
    status_text.success("✅ Connected to camera")
    
    retry_count = 0
    
    try:
        while st.session_state.camera_running and retry_count < max_retries:
            ret, frame = cap.read()
            
            if not ret:
                status_text.warning(f"⚠️ Frame read failed. Retry {retry_count + 1}/{max_retries}")
                retry_count += 1
                
                if enable_retry:
                    cap.release()
                    time.sleep(2)
                    cap = cv2.VideoCapture(url)
                    continue
                else:
                    break
            
            # Reset retry count on successful frame
            retry_count = 0
            
            # Store frame for capture
            st.session_state.frame = frame.copy()
            
            # Convert to RGB for display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Display frame
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            
            # Handle capture request
            if st.session_state.capture_requested and st.session_state.frame is not None:
                status_text.info("📤 Uploading snapshot...")
                
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    url = upload_to_cloudinary(st.session_state.frame, timestamp)
                    
                    st.session_state.last_uploaded_url = url
                    st.session_state.capture_requested = False
                    
                    status_text.success(f"✅ Uploaded successfully!")
                    st.rerun()  # Refresh to show uploaded image
                    
                except Exception as e:
                    status_text.error(f"❌ Upload failed: {str(e)}")
                    st.session_state.capture_requested = False
            
            # Small delay to prevent overwhelming the CPU
            time.sleep(0.03)  # ~30 FPS max
            
    except Exception as e:
        status_text.error(f"❌ Camera error: {str(e)}")
    
    finally:
        cap.release()
        status_text.info("⏹️ Camera stopped")

# --- Run Camera ---
if st.session_state.camera_running:
    process_camera()

# --- Instructions ---
st.divider()
with st.expander("📋 Setup Instructions"):
    st.markdown("""
    ### Required Information from Your V380 Camera:
    
    1. **RTSP URL Components:**
       - **Username**: Usually `admin` (check V380 app settings)
       - **Password**: Set in V380 app → Device Settings → RTSP/ONVIF
       - **IP Address**: Find in your router's admin panel or V380 app
       - **Port**: Usually `554` (check RTSP settings in app)
       - **Stream Path**: Try `ch00_0` (high quality) or `ch00_1` (low bandwidth)
    
    2. **Cloudinary Setup:**
       - Sign up at [cloudinary.com](https://cloudinary.com)
       - Get your Cloud Name, API Key, and API Secret from the dashboard
       - Replace the placeholder values in the code
    
    3. **Testing RTSP URL:**
       - Test in VLC Media Player first: `Media → Open Network Stream`
       - Paste your RTSP URL to verify it works before running this app
    
    ### Security Tips:
    - Use environment variables for credentials in production
    - Don't commit passwords to git repositories
    - Consider using a `.env` file (see code comments)
    """)

# --- Footer ---
st.caption("Built with Streamlit | Connects to V380 cameras via RTSP | Uploads to Cloudinary")
