# v380_cloudinary_app.py
# Fixed RTSP URL handling with validation and auto-correction

import streamlit as st
import cv2
import cloudinary
import cloudinary.uploader
import numpy as np
import time
import io
import socket
import re
from urllib.parse import quote
from datetime import datetime

# --- Configuration ---
RTSP_URL = 'rtsp://Atm_drinking_bar:Atm0543978023@192.168.100.124:554/live/ch00_1'

CLOUDINARY_CLOUD_NAME = 'your_cloud_name'
CLOUDINARY_API_KEY = 'your_api_key'
CLOUDINARY_API_SECRET = 'your_api_secret'

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
if 'last_url' not in st.session_state:
    st.session_state.last_url = None
if 'error_log' not in st.session_state:
    st.session_state.error_log = []
if 'fixed_url' not in st.session_state:
    st.session_state.fixed_url = None

# --- URL Validation & Fixing Functions ---
def validate_and_fix_rtsp(url):
    """Detect and fix common RTSP URL errors"""
    errors = []
    original = url
    
    # Fix 1: Remove spaces in username/password
    if ' ' in url:
        errors.append("❌ Spaces found in credentials - replacing with underscores")
        # Extract parts
        match = re.match(r'rtsp://([^@]+)@(.+)', url)
        if match:
            creds = match.group(1)
            rest = match.group(2)
            # Fix spaces in credentials only
            creds_fixed = creds.replace(' ', '_')
            url = f"rtsp://{creds_fixed}@{rest}"
    
    # Fix 2: Remove double colon @:192.168 → @192.168
    if '@:' in url:
        errors.append("❌ Double colon after @ - removing extra colon")
        url = url.replace('@:', '@')
    
    # Fix 3: Check for missing @ symbol
    if '@' not in url and 'rtsp://' in url:
        errors.append("❌ Missing @ symbol before IP address")
    
    # Fix 4: Check IP format
    ip_match = re.search(r'@(\d+\.\d+\.\d+\.\d+)', url)
    if not ip_match:
        errors.append("⚠️ Could not detect valid IP address")
    else:
        ip = ip_match.group(1)
        octets = ip.split('.')
        if not all(0 <= int(o) <= 255 for o in octets):
            errors.append(f"❌ Invalid IP address: {ip}")
    
    # Fix 5: URL encode special characters in password
    if ':' in url:
        try:
            auth_part = url.split('@')[0].replace('rtsp://', '')
            user, pwd = auth_part.split(':', 1)
            # Check if already encoded
            if '%' not in pwd:
                # Encode special chars except already safe ones
                safe_pwd = quote(pwd, safe='')
                if safe_pwd != pwd:
                    errors.append(f"🔧 Encoded special characters in password")
                    url = url.replace(f":{pwd}@", f":{safe_pwd}@")
        except:
            pass
    
    return url, errors, original != url

def test_rtsp_connection(url):
    """Test if RTSP stream is reachable"""
    try:
        # Extract IP and port
        match = re.search(r'@([^:/]+)(?::(\d+))?', url)
        if not match:
            return False, "Could not parse IP from URL"
        
        ip = match.group(1)
        port = int(match.group(2)) if match.group(2) else 554
        
        # Test TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result != 0:
            return False, f"Cannot connect to {ip}:{port} - Camera offline or RTSP not enabled"
        
        # Test RTSP stream
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return True, "Connected successfully!"
        else:
            return False, "TCP port open but RTSP stream rejected - check credentials or RTSP settings"
            
    except Exception as e:
        return False, f"Connection error: {str(e)}"

# --- UI ---
st.title("📷 V380 Camera + Cloudinary")

# URL Input with validation
st.subheader("RTSP Configuration")
url_col1, url_col2 = st.columns([3, 1])

with url_col1:
    rtsp_input = st.text_input(
        "RTSP URL", 
        RTSP_URL,
        help="Format: rtsp://username:password@ip:port/path",
        label_visibility="collapsed",
        placeholder="rtsp://username:password@192.168.1.100:554/live/ch00_1"
    )

with url_col2:
    if st.button("🔧 Validate & Fix URL", use_container_width=True):
        fixed, errors, was_changed = validate_and_fix_rtsp(rtsp_input)
        if was_changed:
            st.session_state.fixed_url = fixed
            st.success("URL Fixed!")
        else:
            st.info("URL looks good")

# Show fixed URL if available
if st.session_state.fixed_url:
    st.code(f"Fixed URL: {st.session_state.fixed_url}", language=None)
    if st.button("Use Fixed URL"):
        rtsp_input = st.session_state.fixed_url
        st.session_state.fixed_url = None
        st.rerun()

# Manual fix section
with st.expander("🔍 URL Troubleshooter"):
    st.markdown("""
    **Common Issues with your URL:**
    
    Your URL: `rtsp://Atm drinking bar:Atm0543978023@:192.168.100.124:554/live/ch00_1`
    
    | Issue | Fix |
    |-------|-----|
    | Spaces in username `Atm drinking bar` | Replace with underscores: `Atm_drinking_bar` |
    | Double colon `@:` | Remove extra colon: `@192.168` |
    | Special characters in password | Keep as-is or URL encode if needed |
    
    **Corrected URL:**
    ```
    rtsp://Atm_drinking_bar:Atm0543978023@192.168.100.124:554/live/ch00_1
    ```
    """)
    
    # Manual test
    if st.button("Test Connection to Current URL"):
        with st.spinner("Testing..."):
            success, msg = test_rtsp_connection(rtsp_input)
            if success:
                st.success(msg)
            else:
                st.error(msg)
                st.info("💡 If port is open but stream fails, RTSP may be disabled on camera. See guide below.")

# Sidebar controls
st.sidebar.header("Camera Controls")

# Auto-apply fixes to input
working_url, fix_msgs, _ = validate_and_fix_rtsp(rtsp_input)
if fix_msgs:
    st.sidebar.warning("URL Issues Detected:")
    for msg in fix_msgs:
        st.sidebar.text(msg)
    st.sidebar.code(working_url)
    if st.sidebar.button("Apply Fixes"):
        rtsp_input = working_url
        st.rerun()

# Main controls
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("Live Feed")
    frame_placeholder = st.empty()
    status_placeholder = st.empty()

with col2:
    st.subheader("Actions")
    
    # Start/Stop
    if not st.session_state.camera_active:
        if st.button("▶️ Start Camera", type="primary", use_container_width=True):
            # Validate before starting
            final_url, errors, changed = validate_and_fix_rtsp(rtsp_input)
            if errors:
                st.session_state.error_log = errors
            st.session_state.camera_active = True
            st.session_state.working_url = final_url
            st.rerun()
    else:
        if st.button("⏹️ Stop Camera", type="secondary", use_container_width=True):
            st.session_state.camera_active = False
            st.rerun()
    
    # Show errors
    if st.session_state.error_log:
        with st.expander("⚠️ URL Warnings", expanded=True):
            for err in st.session_state.error_log:
                st.text(err)
    
    # Capture
    if st.button("📸 Capture", disabled=not st.session_state.camera_active, use_container_width=True):
        if st.session_state.frame is not None:
            with st.spinner("Uploading..."):
                try:
                    _, buffer = cv2.imencode('.jpg', st.session_state.frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    img_bytes = io.BytesIO(buffer)
                    
                    result = cloudinary.uploader.upload(
                        img_bytes,
                        resource_type="image",
                        public_id=f"v380_{int(time.time())}",
                        folder="v380_snapshots"
                    )
                    
                    st.session_state.last_url = result['secure_url']
                    st.success("✅ Uploaded!")
                except Exception as e:
                    st.error(f"Upload failed: {e}")
            st.rerun()
    
    # Last upload
    if st.session_state.last_url:
        st.subheader("Last Upload")
        st.image(st.session_state.last_url, use_column_width=True)
        st.markdown(f"[View Full Size]({st.session_state.last_url})")

# --- Camera Loop ---
def run_camera():
    url = st.session_state.get('working_url', rtsp_input)
    
    # Final validation
    url, _, _ = validate_and_fix_rtsp(url)
    
    status_placeholder.info(f"Connecting to: {url.replace(url.split('@')[0].split(':')[-1], '***')}")  # Hide password
    
    cap = cv2.VideoCapture(url)
    
    if not cap.isOpened():
        status_placeholder.error("❌ Failed to open stream")
        st.session_state.camera_active = False
        
        # Diagnose why
        ip_match = re.search(r'@([^:/]+)', url)
        if ip_match:
            ip = ip_match.group(1)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((ip, 554))
                sock.close()
                if result != 0:
                    st.error(f"Cannot reach {ip}:554 - Camera may be offline or RTSP disabled")
                else:
                    st.error("Port 554 is open but RTSP rejected - Wrong credentials or RTSP not enabled")
            except:
                pass
        st.rerun()
        return
    
    status_placeholder.success("✅ Connected")
    st.session_state.error_log = []
    
    frame_count = 0
    while st.session_state.camera_active:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            frame_count += 1
            if frame_count > 50:  # 5 seconds of no frames
                status_placeholder.warning("⚠️ Connection lost - retrying...")
                cap.release()
                cap = cv2.VideoCapture(url)
                frame_count = 0
            continue
        
        frame_count = 0
        st.session_state.frame = frame.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
        time.sleep(0.03)
    
    cap.release()
    status_placeholder.info("⏹️ Stopped")

if st.session_state.camera_active:
    run_camera()

# --- Setup Guide ---
with st.expander("📋 V380 RTSP Setup Guide (Read if connection fails)"):
    st.markdown("""
    ### Enable RTSP on V380 Camera
    
    **Method 1: SD Card (Most Reliable)**
    1. Create text file named `ceshi.ini`
    2. Add: `[CONST_PARAM]`
    3. Add: `rtsp=1`
    4. Copy to SD card root
    5. Insert into camera (powered off)
    6. Power on, wait 3 minutes
    7. Remove SD card, restart camera
    
    **Method 2: V380 Pro App**
    - Some versions have RTSP toggle in: Device Settings → Network → RTSP/ONVIF
    
    **Correct URL Format:**
    ```
    rtsp://username:password@192.168.100.124:554/live/ch00_1
    ```
    
    **Your Fixed URL:**
    ```
    rtsp://Atm_drinking_bar:Atm0543978023@192.168.100.124:554/live/ch00_1
    ```
    
    ### Alternative URLs to Try:
    - `rtsp://Atm_drinking_bar:Atm0543978023@192.168.100.124:554/live/ch00_0`
    - `rtsp://Atm_drinking_bar:Atm0543978023@192.168.100.124:554/onvif1`
    - `rtsp://admin:admin@192.168.100.124:554/live/ch00_0` (default creds)
    """)
