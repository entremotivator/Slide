import streamlit as st
import os
import time
from pathlib import Path
from PIL import Image
import io
import json
import tempfile
from datetime import datetime
import re
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

# --- Configuration and Initialization ---

# Page config
st.set_page_config(
    layout="wide",
    page_title="Live Photos & Video Slideshow",
    page_icon="🎬"
)

# Initialize session state
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'files' not in st.session_state:
    st.session_state.files = []
if 'sort_order' not in st.session_state:
    st.session_state.sort_order = 'name'
if 'loop_mode' not in st.session_state:
    st.session_state.loop_mode = True
if 'loaded' not in st.session_state:
    st.session_state.loaded = False
if 'gdrive_authenticated' not in st.session_state:
    st.session_state.gdrive_authenticated = False
if 'drive_service' not in st.session_state:
    st.session_state.drive_service = None
if 'credentials_content' not in st.session_state:
    st.session_state.credentials_content = None
if 'token_pickle' not in st.session_state:
    st.session_state.token_pickle = None

# Supported formats
IMAGE_EXT = [".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp"]
VIDEO_EXT = [".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"]
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Custom CSS
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        color: #FF4B4B;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .file-counter {
        text-align: center;
        font-size: 1.5rem;
        margin: 1rem 0;
        color: #555;
        font-weight: 600;
    }
    .info-box {
        background: #d1ecf1;
        border: 2px solid #17a2b8;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎬 Live Photos & Video Slideshow Pro</div>', unsafe_allow_html=True)

# --- Utility Functions ---

def extract_folder_id(url):
    """Extracts the Google Drive folder ID from a URL."""
    try:
        if "id=" in url:
            match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        if "/folders/" in url:
            match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
    except Exception as e:
        st.error(f"Error parsing URL: {e}")
    return None

def initialize_drive_service():
    """Initializes and returns the Google Drive service object using OAuth2."""
    if not st.session_state.credentials_content:
        return None

    creds = None
    # 1. Load credentials from session state if available
    if st.session_state.token_pickle:
        try:
            creds = pickle.loads(st.session_state.token_pickle)
        except Exception as e:
            st.warning(f"Could not load saved token: {e}")
            st.session_state.token_pickle = None

    # 2. Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            st.session_state.token_pickle = pickle.dumps(creds)
        except Exception as e:
            st.error(f"Error refreshing token: {e}")
            creds = None # Force re-authentication

    # 3. If no valid credentials, start the OAuth flow
    if not creds or not creds.valid:
        # Use a temporary file to load client secrets for the flow
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_creds_file:
            temp_creds_file.write(st.session_state.credentials_content)
            temp_creds_path = temp_creds_file.name
        
        try:
            # The key fix: ensure the flow is correctly initialized for installed apps
            flow = Flow.from_client_secrets_file(
                temp_creds_path,
                scopes=SCOPES,
                # Use 'urn:ietf:wg:oauth:2.0:oob' for desktop/installed app flow
                redirect_uri='urn:ietf:wg:oauth:2.0:oob' 
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            st.info("🔐 **Authentication Required**")
            st.markdown(f"1. [Click here to authorize]({auth_url})")
            st.markdown("2. Copy the authorization code")
            
            # Use a unique key for the text input to prevent re-running on every change
            auth_code = st.text_input("3. Paste the authorization code here:", key="auth_code_input")
            
            if auth_code:
                try:
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    st.session_state.token_pickle = pickle.dumps(creds)
                    st.session_state.gdrive_authenticated = True
                    st.success("✅ Authentication successful! Please click 'Load Files' again.")
                    # Rerun to clear the auth prompt and proceed
                    st.rerun() 
                except Exception as e:
                    st.error(f"Authentication failed. Please check the code and try again. Error: {e}")
                    return None
            else:
                # Authentication is pending user input
                return None
        except Exception as e:
            st.error(f"Error initializing Drive service. **Ensure your JSON is for an 'Installed application' (Desktop app) or 'Web application'**. Error: {e}")
            return None
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_creds_path):
                os.unlink(temp_creds_path)

    # 4. Build the service if credentials are valid
    if creds and creds.valid:
        try:
            service = build('drive', 'v3', credentials=creds)
            st.session_state.gdrive_authenticated = True
            return service
        except Exception as e:
            st.error(f"Error building Drive service: {e}")
            return None
    
    return None

def load_gdrive_files(service, folder_id):
    """Loads media files from the specified Google Drive folder."""
    files = []
    page_token = None
    
    try:
        with st.spinner("📥 Loading files from Google Drive..."):
            while True:
                # Query for files in the folder that are not trashed
                query = f"'{folder_id}' in parents and trashed=false"
                
                # Add mimeType filter for better performance, though not strictly necessary
                # mime_types = " or ".join([f"mimeType contains '{ext}'" for ext in IMAGE_EXT + VIDEO_EXT])
                # query += f" and ({mime_types})"

                results = service.files().list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    name = item['name']
                    # Handle files without extensions (e.g., Google Docs) by skipping them
                    if '.' not in name:
                        continue
                        
                    ext = os.path.splitext(name)[1].lower()
                    
                    if ext in IMAGE_EXT + VIDEO_EXT:
                        files.append({
                            'id': item['id'],
                            'name': name,
                            'ext': ext,
                            'size': item.get('size', 0),
                            'created': item.get('createdTime', ''),
                            'modified': item.get('modifiedTime', ''),
                            'mime_type': item.get('mimeType', ''),
                            'source': 'gdrive'
                        })
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
        
        return files
    except HttpError as e:
        st.error(f"Google Drive API Error: {e.content.decode()}")
        st.warning("This often means the folder ID is incorrect or the Drive API is not enabled for your project.")
        return []
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return []

def download_gdrive_file(service, file_id):
    """Downloads a file from Google Drive."""
    try:
        from googleapiclient.http import MediaIoBaseDownload
        
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_content.seek(0)
        return file_content
    except Exception as e:
        st.error(f"Error downloading file: {e}")
        return None

# --- Sidebar Controls ---

with st.sidebar:
    st.header("⚙️ Settings & Controls")
    
    source_type = st.radio("📂 Choose Source:", ["Local Folder", "Google Drive (with Auth)"], 
                          help="Select where your media files are stored")
    
    st.divider()
    
    if source_type == "Google Drive (with Auth)":
        st.subheader("🔐 Google Drive Setup")
        
        # Instructions for the user to get the correct credentials
        with st.expander("📖 Setup Instructions (Crucial Fix)", expanded=not st.session_state.credentials_content):
            st.markdown("""
            **The Fix:** The error "Client secrets must be for a web or installed app" means you are likely using a **Service Account** JSON, which is for server-to-server communication. This app requires **User Authentication (OAuth 2.0)**.
            
            **Step-by-step Guide for OAuth 2.0 Credentials:**
            
            1. **Go to Google Cloud Console**
               - Visit [console.cloud.google.com](https://console.cloud.google.com)
            
            2. **Create/Select Project**
               - Create a new project or select existing one
            
            3. **Enable Google Drive API**
               - Go to "APIs & Services" > "Library"
               - Search for "Google Drive API" and click "Enable"
            
            4. **Create OAuth Credentials**
               - Go to "APIs & Services" > "Credentials"
               - Click "+ CREATE CREDENTIALS"
               - Select "OAuth client ID"
               - **Crucial:** Choose **"Desktop app"** as the Application type. (This is the type that works with the code's authentication flow).
               - Name it (e.g., "Slideshow App") and click "Create".
            
            5. **Download JSON**
               - Click the download icon next to your newly created OAuth 2.0 Client ID.
               - This file is your `client_secrets.json`.
            
            6. **Upload Below**
               - Upload the downloaded JSON file.
            """)
        
        # File uploader for credentials
        uploaded_creds = st.file_uploader(
            "Upload client_secrets.json (OAuth 2.0 Client ID)",
            type=['json'],
            help="Upload your Google OAuth credentials file (must be 'Desktop app' type)",
            key="creds_uploader"
        )
        
        if uploaded_creds:
            try:
                credentials_content = uploaded_creds.read().decode('utf-8')
                json.loads(credentials_content)  # Validate JSON
                st.session_state.credentials_content = credentials_content
                st.success("✅ Credentials file uploaded successfully! Proceed to authentication.")
            except json.JSONDecodeError:
                st.error("Error: The uploaded file is not a valid JSON file.")
            except Exception as e:
                st.error(f"Error reading credentials: {e}")
        
        if st.session_state.credentials_content:
            st.divider()
            
            # Initialize service if not done
            if st.session_state.drive_service is None or not st.session_state.gdrive_authenticated:
                st.session_state.drive_service = initialize_drive_service()
            
            if st.session_state.drive_service:
                st.success("🔗 Connected to Google Drive!")
                
                # Folder URL input
                gdrive_url = st.text_input(
                    "Google Drive Folder URL:",
                    value="", # Clear default value to force user input
                    placeholder="Paste the URL of your Google Drive folder",
                    help="Paste the URL of your Google Drive folder"
                )
                
                if st.button("📥 Load Files from Google Drive", type="primary", use_container_width=True):
                    if not gdrive_url:
                        st.error("Please enter a Google Drive Folder URL.")
                    else:
                        folder_id = extract_folder_id(gdrive_url)
                        if folder_id:
                            files = load_gdrive_files(st.session_state.drive_service, folder_id)
                            if files:
                                st.session_state.files = sorted(files, key=lambda x: x['name'])
                                st.session_state.current_idx = 0
                                st.session_state.loaded = True
                                st.success(f"✅ Loaded {len(files)} files!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.warning("No media files found in the folder or access denied.")
                        else:
                            st.error("Invalid Google Drive URL. Could not extract folder ID.")
            
            elif st.session_state.credentials_content and not st.session_state.gdrive_authenticated:
                st.warning("Please complete the authentication steps above.")
    
    else:  # Local Folder (Simplified for this fix)
        st.subheader("📁 Local Files")
        st.info("💡 Best for fast, offline access to your media")
        
        folder_path = st.text_input(
            "Folder Path:",
            placeholder="/home/ubuntu/media",
            help="Enter the full path to your media folder"
        )
        
        if st.button("📁 Load Files", type="primary", use_container_width=True):
            p = Path(folder_path)
            if not p.exists():
                st.error("❌ Folder not found. Please check the path.")
            elif not p.is_dir():
                st.error("❌ Path is not a folder")
            else:
                files = [f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT + VIDEO_EXT]
                if files:
                    st.session_state.files = [
                        {
                            'path': f,
                            'ext': f.suffix.lower(),
                            'name': f.name,
                            'size': f.stat().st_size,
                            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                            'source': 'local'
                        }
                        for f in sorted(files)
                    ]
                    st.session_state.current_idx = 0
                    st.session_state.loaded = True
                    st.success(f"✅ Loaded {len(files)} files!")
                    st.balloons()
                    st.rerun()
                else:
                    st.warning("No media files found in folder")
        
    st.divider()
    
    # Placeholder for other settings (Playback, Sorting, etc.)
    st.subheader("⏱️ Playback Settings")
    duration = st.slider("Display Duration:", min_value=1, max_value=30, value=3, step=1, format="%d sec")
    st.session_state.loop_mode = st.checkbox("🔄 Loop Slideshow", value=True)
    st.selectbox("✨ Transition Effect:", ["None", "Fade", "Slide"])
    
    st.divider()
    
    if st.session_state.files:
        st.subheader("📊 Statistics")
        st.metric("📁 Total Files", len(st.session_state.files))

# --- Main Content Area ---

if not st.session_state.files:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### 👋 Welcome to Live Photos & Video Slideshow Pro!")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("""
    ### ☁️ **Google Drive Mode Fix**
    
    The main issue was that the authentication flow was expecting an **OAuth 2.0 Client ID** (for a "Desktop app" or "Web application") but was likely receiving a **Service Account** key.
    
    **To use Google Drive:**
    1. **Follow the updated instructions in the sidebar** to create and download an **OAuth 2.0 Client ID** JSON file (Application type: **Desktop app**).
    2. Upload the JSON file in the sidebar.
    3. Complete the browser-based authentication using the generated link and code.
    4. Enter your Google Drive folder URL and click "Load Files".
    
    👈 **Get started by selecting your source in the sidebar!**
    """)
    
else:
    # --- Slideshow Logic (Simplified) ---
    
    # Simple filtering (can be expanded later)
    filtered_files = st.session_state.files
    
    if not filtered_files:
        st.warning("⚠️ No files match your current filters.")
    else:
        # Ensure index is valid
        if st.session_state.current_idx >= len(filtered_files):
            st.session_state.current_idx = 0
        
        current_file = filtered_files[st.session_state.current_idx]
        
        st.markdown(
            f'<div class="file-counter">File {st.session_state.current_idx + 1} of {len(filtered_files)}: **{current_file["name"]}**</div>',
            unsafe_allow_html=True
        )
        
        # Navigation controls
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col2:
            if st.button("◀️ Prev", use_container_width=True):
                st.session_state.current_idx = (st.session_state.current_idx - 1) % len(filtered_files)
                st.rerun()
        
        with col4:
            if st.button("▶️ Next", use_container_width=True):
                st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
                st.rerun()

        st.divider()
        
        # Display the file
        if current_file['source'] == 'gdrive':
            st.info(f"Downloading: {current_file['name']}...")
            service = st.session_state.drive_service
            if service:
                file_content = download_gdrive_file(service, current_file['id'])
                if file_content:
                    if current_file['ext'] in IMAGE_EXT:
                        try:
                            image = Image.open(file_content)
                            st.image(image, caption=current_file['name'], use_column_width=True)
                        except Exception as e:
                            st.error(f"Could not display image: {e}")
                    elif current_file['ext'] in VIDEO_EXT:
                        # Streamlit does not directly support streaming video from BytesIO, 
                        # so we must save it to a temp file for the video player to work.
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=current_file['ext']) as tmp_file:
                                tmp_file.write(file_content.read())
                                temp_path = tmp_file.name
                            st.video(temp_path, format=current_file['mime_type'])
                            os.unlink(temp_path) # Clean up the temp file
                        except Exception as e:
                            st.error(f"Could not display video: {e}")
                    else:
                        st.warning(f"Unsupported file type: {current_file['ext']}")
            else:
                st.error("Google Drive service is not initialized.")
        
        elif current_file['source'] == 'local':
            # Local file display logic (from original code)
            file_path = current_file['path']
            if current_file['ext'] in IMAGE_EXT:
                st.image(str(file_path), caption=current_file['name'], use_column_width=True)
            elif current_file['ext'] in VIDEO_EXT:
                st.video(str(file_path))
            else:
                st.warning(f"Unsupported local file type: {current_file['ext']}")
