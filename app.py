import streamlit as st
import time
import re
from typing import List
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# ==================== GOOGLE DRIVE SERVICE CODE ====================

def extract_folder_id(url: str) -> str:
    """Extract folder ID from Google Drive URL."""
    patterns = [
        r'/folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'^([a-zA-Z0-9_-]+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract folder ID from URL: {url}")

def get_drive_service(credentials_json):
    """Create Google Drive service using credentials."""
    try:
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        raise Exception(f"Failed to create Drive service: {str(e)}")

def get_image_urls_from_folder(folder_url: str, credentials_json: str = None) -> List[str]:
    """
    Get direct image URLs from a Google Drive folder.
    
    Args:
        folder_url: Google Drive folder URL or ID
        credentials_json: Service account credentials JSON (optional)
        
    Returns:
        List of direct image URLs
    """
    try:
        folder_id = extract_folder_id(folder_url)
    except ValueError as e:
        raise ValueError(f"Invalid folder URL: {e}")
    
    # If no credentials provided, return empty list
    if not credentials_json:
        return []
    
    try:
        service = get_drive_service(credentials_json)
        
        # Query for image files in the folder
        query = f"'{folder_id}' in parents and (mimeType contains 'image/')"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, thumbnailLink, webContentLink)",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        # Convert to direct image URLs
        image_urls = []
        for file in files:
            file_id = file['id']
            # Use direct download link
            direct_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            image_urls.append(direct_url)
        
        return image_urls
    except Exception as e:
        raise Exception(f"Error fetching images from Drive: {str(e)}")

# ==================== END GOOGLE DRIVE SERVICE CODE ====================

# Page config
st.set_page_config(
    page_title="Google Drive Slideshow", 
    layout="wide", 
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

# Initialize ALL session state variables at the start
def init_session_state():
    """Initialize all session state variables with defaults."""
    defaults = {
        'credentials': None,
        'current_index': 0,
        'auto_play': True,
        'image_urls': None,
        'credentials_loaded': False
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# Call initialization before any other code
init_session_state()

# Hardcoded Google Drive folder URL
FOLDER_URL = "https://drive.google.com/drive/folders/1LfSwuD7WxbS0ZdDeGo0hpiviUx6vMhqs?usp=sharing"

# Custom CSS
st.markdown("""
<style>
    .stImage {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    img {
        max-height: 70vh;
        object-fit: contain;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .main-header {
        text-align: center;
        padding: 15px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("🔧 Configuration")
    
    st.subheader("📁 Google Drive Folder")
    st.code(FOLDER_URL, language="text")
    
    st.divider()
    
    st.subheader("🔑 Service Account Credentials")
    
    # File uploader for service account JSON
    uploaded_file = st.file_uploader(
        "Upload Service Account JSON",
        type=['json'],
        help="Upload your Google Drive service account credentials file"
    )
    
    if uploaded_file is not None:
        try:
            credentials_json = uploaded_file.read().decode('utf-8')
            st.session_state.credentials = credentials_json
            st.session_state.credentials_loaded = True
            st.success("✅ Credentials loaded!")
        except Exception as e:
            st.error(f"❌ Error loading credentials: {str(e)}")
            st.session_state.credentials = None
            st.session_state.credentials_loaded = False
    elif st.session_state.get('credentials_loaded', False):
        st.info("✅ Credentials already loaded")
        if st.button("🗑️ Clear Credentials"):
            st.session_state.credentials = None
            st.session_state.credentials_loaded = False
            st.session_state.image_urls = None
            st.rerun()
    
    st.divider()
    
    st.subheader("⚙️ Slideshow Settings")
    slide_interval = st.slider(
        "Slide Interval (seconds)", 
        min_value=1, 
        max_value=10, 
        value=3
    )
    
    auto_loop = st.checkbox("Auto Loop", value=True)
    
    st.divider()
    
    st.caption("💡 **Instructions:**")
    st.caption("1. Upload service account JSON")
    st.caption("2. Grant the service account email access to the Google Drive folder")
    st.caption("3. Click 'Load Images' to start")

# ==================== MAIN APP ====================

# Header
st.markdown("""
<div class="main-header">
    <h1>🎬 Google Drive Slideshow</h1>
    <p>Auto-looping image viewer</p>
</div>
""", unsafe_allow_html=True)

if not st.session_state.credentials:
    st.warning("⚠️ **Step 1:** Upload service account JSON file in the sidebar")
    st.info("""
    **Why images aren't showing in Streamlit Community:**
    
    - The service account credentials file must be uploaded each session
    - The service account email must have **Viewer** access to the Google Drive folder
    - Check that the folder URL is correct and publicly shared OR shared with your service account email
    """)
    st.stop()

# Load images button
if st.session_state.credentials and st.session_state.image_urls is None:
    if st.button("🔄 Load Images from Google Drive", type="primary", use_container_width=True):
        with st.spinner("Connecting to Google Drive..."):
            try:
                image_urls = get_image_urls_from_folder(
                    FOLDER_URL, 
                    st.session_state.credentials
                )
                if image_urls:
                    st.session_state.image_urls = image_urls
                    st.success(f"✅ Successfully loaded {len(image_urls)} images!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ No images found in folder")
                    st.info("Make sure the service account has access to the folder")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("""
                **Troubleshooting:**
                - Verify the service account email has access to the folder
                - Check that the credentials JSON file is valid
                - Ensure the folder contains image files
                """)

# Check if images are loaded
if st.session_state.image_urls is None:
    st.info("👆 Click 'Load Images' button above to fetch photos from Google Drive")
    st.stop()

image_urls = st.session_state.image_urls
total_images = len(image_urls)

if total_images == 0:
    st.error("No images found in the folder")
    st.stop()

# Controls
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("⏮️ First"):
        st.session_state.current_index = 0

with col2:
    if st.button("◀️ Previous"):
        st.session_state.current_index = (st.session_state.current_index - 1) % total_images

with col3:
    play_text = "⏸️ Pause" if st.session_state.auto_play else "▶️ Play"
    if st.button(play_text):
        st.session_state.auto_play = not st.session_state.auto_play

with col4:
    if st.button("▶️ Next"):
        st.session_state.current_index = (st.session_state.current_index + 1) % total_images

with col5:
    if st.button("⏭️ Last"):
        st.session_state.current_index = total_images - 1

# Progress bar
progress = (st.session_state.current_index + 1) / total_images
st.progress(progress, text=f"Image {st.session_state.current_index + 1} of {total_images}")

st.markdown("---")

# Display current image
current_image_url = image_urls[st.session_state.current_index]

col_left, col_center, col_right = st.columns([1, 6, 1])

with col_center:
    st.image(
        current_image_url, 
        use_column_width=True,
        caption=f"Image {st.session_state.current_index + 1} / {total_images}"
    )

# Status info
info_col1, info_col2, info_col3 = st.columns(3)

with info_col1:
    status = "▶️ Auto-playing" if st.session_state.auto_play else "⏸️ Paused"
    st.info(status)

with info_col2:
    st.info(f"⏱️ {slide_interval}s interval")

with info_col3:
    st.info(f"🔄 Loop: {'On' if auto_loop else 'Off'}")

# Auto-advance logic
if st.session_state.auto_play and auto_loop:
    time.sleep(slide_interval)
    st.session_state.current_index = (st.session_state.current_index + 1) % total_images
    st.rerun()
