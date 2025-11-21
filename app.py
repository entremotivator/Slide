import streamlit as st
import time
import re
from typing import List
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

def get_all_images_from_folder(folder_url: str, credentials_json: str) -> List[dict]:
    """
    Get ALL image files from a Google Drive folder with pagination.
    
    Args:
        folder_url: Google Drive folder URL or ID
        credentials_json: Service account credentials JSON
        
    Returns:
        List of dicts with image info (id, name, url)
    """
    try:
        folder_id = extract_folder_id(folder_url)
    except ValueError as e:
        raise ValueError(f"Invalid folder URL: {e}")
    
    if not credentials_json:
        raise ValueError("Credentials required")
    
    try:
        service = get_drive_service(credentials_json)
        
        all_images = []
        page_token = None
        
        # Query for ALL image files in the folder with pagination
        while True:
            query = f"'{folder_id}' in parents and (mimeType contains 'image/') and trashed=false"
            
            results = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, createdTime)",
                pageSize=1000,  # Max page size
                pageToken=page_token,
                orderBy='createdTime'  # Order by creation time
            ).execute()
            
            files = results.get('files', [])
            
            # Add each file to the list
            for file in files:
                file_id = file['id']
                direct_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                all_images.append({
                    'id': file_id,
                    'name': file.get('name', 'Untitled'),
                    'url': direct_url,
                    'mime_type': file.get('mimeType', '')
                })
            
            # Check if there are more pages
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        return all_images
        
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
        'images': None,  # Changed to store full image info
        'credentials_loaded': False,
        'loading_complete': False
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
    
    .image-name {
        text-align: center;
        font-size: 14px;
        color: #666;
        margin-top: 10px;
        font-style: italic;
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
        help="Upload your Google Drive service account credentials file",
        key='creds_uploader'
    )
    
    if uploaded_file is not None:
        try:
            credentials_json = uploaded_file.read().decode('utf-8')
            st.session_state.credentials = credentials_json
            st.session_state.credentials_loaded = True
            st.session_state.loading_complete = False  # Reset loading flag
            st.success("✅ Credentials loaded!")
        except Exception as e:
            st.error(f"❌ Error loading credentials: {str(e)}")
            st.session_state.credentials = None
            st.session_state.credentials_loaded = False
    
    # Show status if credentials are loaded
    if st.session_state.get('credentials_loaded', False):
        if st.session_state.images:
            st.info(f"✅ {len(st.session_state.images)} images loaded")
        
        if st.button("🗑️ Clear Credentials & Reset"):
            st.session_state.credentials = None
            st.session_state.credentials_loaded = False
            st.session_state.images = None
            st.session_state.loading_complete = False
            st.session_state.current_index = 0
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
    
    show_filenames = st.checkbox("Show Filenames", value=True)
    
    st.divider()
    
    st.caption("💡 **Instructions:**")
    st.caption("1. Upload service account JSON")
    st.caption("2. Images will load automatically")
    st.caption("3. Service account needs Viewer access")

# ==================== MAIN APP ====================

# Header
st.markdown("""
<div class="main-header">
    <h1>🎬 Google Drive Slideshow</h1>
    <p>Auto-looping image viewer</p>
</div>
""", unsafe_allow_html=True)

# Check credentials
if not st.session_state.credentials:
    st.warning("⚠️ **Step 1:** Upload service account JSON file in the sidebar")
    st.info("""
    **Setup Instructions:**
    
    1. Upload your service account credentials JSON file
    2. Make sure the service account email has **Viewer** access to the Google Drive folder
    3. Images will load automatically once credentials are provided
    """)
    st.stop()

# AUTO-LOAD images when credentials are available
if st.session_state.credentials and not st.session_state.loading_complete:
    with st.spinner("🔄 Loading all images from Google Drive..."):
        try:
            images = get_all_images_from_folder(
                FOLDER_URL, 
                st.session_state.credentials
            )
            if images:
                st.session_state.images = images
                st.session_state.loading_complete = True
                st.success(f"✅ Successfully loaded {len(images)} images!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ No images found in folder")
                st.info("Make sure the service account has access to the folder and it contains image files")
                st.stop()
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("""
            **Troubleshooting:**
            - Verify the service account email has Viewer access to the folder
            - Check that the credentials JSON file is valid
            - Ensure the folder contains image files
            - Folder ID should be correct in the URL
            """)
            if st.button("🔄 Retry Loading"):
                st.session_state.loading_complete = False
                st.rerun()
            st.stop()

# Check if images are loaded
if not st.session_state.images:
    st.info("Loading images...")
    st.stop()

images = st.session_state.images
total_images = len(images)

if total_images == 0:
    st.error("No images found in the folder")
    st.stop()

# Controls
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("⏮️ First"):
        st.session_state.current_index = 0
        st.rerun()

with col2:
    if st.button("◀️ Previous"):
        st.session_state.current_index = (st.session_state.current_index - 1) % total_images
        st.rerun()

with col3:
    play_text = "⏸️ Pause" if st.session_state.auto_play else "▶️ Play"
    if st.button(play_text):
        st.session_state.auto_play = not st.session_state.auto_play
        st.rerun()

with col4:
    if st.button("▶️ Next"):
        st.session_state.current_index = (st.session_state.current_index + 1) % total_images
        st.rerun()

with col5:
    if st.button("⏭️ Last"):
        st.session_state.current_index = total_images - 1
        st.rerun()

# Progress bar
progress = (st.session_state.current_index + 1) / total_images
st.progress(progress, text=f"Image {st.session_state.current_index + 1} of {total_images}")

st.markdown("---")

# Display current image
current_image = images[st.session_state.current_index]
current_image_url = current_image['url']
current_image_name = current_image['name']

col_left, col_center, col_right = st.columns([1, 6, 1])

with col_center:
    st.image(
        current_image_url, 
        use_column_width=True,
        caption=f"Image {st.session_state.current_index + 1} / {total_images}"
    )
    
    if show_filenames:
        st.markdown(f'<div class="image-name">📄 {current_image_name}</div>', unsafe_allow_html=True)

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
if st.session_state.auto_play:
    time.sleep(slide_interval)
    if auto_loop:
        st.session_state.current_index = (st.session_state.current_index + 1) % total_images
    else:
        # Stop at the end if loop is off
        if st.session_state.current_index < total_images - 1:
            st.session_state.current_index += 1
        else:
            st.session_state.auto_play = False
    st.rerun()
