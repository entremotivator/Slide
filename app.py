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
if 'credentials_uploaded' not in st.session_state:
    st.session_state.credentials_uploaded = False

# Supported formats
IMAGE_EXT = [".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp"]
VIDEO_EXT = [".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"]

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
    .status-text {
        text-align: center;
        font-size: 1.2rem;
        padding: 1rem;
        background: #f0f2f6;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 2px solid #28a745;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border: 2px solid #17a2b8;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎬 Live Photos & Video Slideshow Pro</div>', unsafe_allow_html=True)

# Extract folder ID from Drive URL
def extract_folder_id(url):
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

# Initialize Google Drive service with uploaded credentials
def initialize_drive_service(credentials_content):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        import pickle
        
        # Save credentials to temporary file
        temp_creds_path = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_creds_path.write(credentials_content)
        temp_creds_path.close()
        
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        
        creds = None
        # Check if we have saved token
        if 'token_pickle' in st.session_state:
            creds = pickle.loads(st.session_state.token_pickle)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = Flow.from_client_secrets_file(
                    temp_creds_path.name,
                    scopes=SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                
                st.info("🔐 **Authentication Required**")
                st.markdown(f"1. [Click here to authorize]({auth_url})")
                st.markdown("2. Copy the authorization code")
                
                auth_code = st.text_input("3. Paste the authorization code here:", key="auth_code_input")
                
                if auth_code:
                    try:
                        flow.fetch_token(code=auth_code)
                        creds = flow.credentials
                        st.session_state.token_pickle = pickle.dumps(creds)
                        st.success("✅ Authentication successful!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {e}")
                        return None
                else:
                    return None
        
        # Build the service
        service = build('drive', 'v3', credentials=creds)
        os.unlink(temp_creds_path.name)
        return service
        
    except ImportError as e:
        st.error("❌ Required libraries not installed. Please install: `pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`")
        return None
    except Exception as e:
        st.error(f"Error initializing Drive service: {e}")
        return None

# Load files from Google Drive
def load_gdrive_files(service, folder_id):
    try:
        files = []
        page_token = None
        
        with st.spinner("📥 Loading files from Google Drive..."):
            while True:
                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)",
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    name = item['name']
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
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return []

# Download file from Google Drive
def download_gdrive_file(service, file_id):
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

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Settings & Controls")
    
    source_type = st.radio("📂 Choose Source:", ["Local Folder", "Google Drive (with Auth)"], 
                          help="Select where your media files are stored")
    
    st.divider()
    
    if source_type == "Google Drive (with Auth)":
        st.subheader("🔐 Google Drive Setup")
        
        with st.expander("📖 Setup Instructions", expanded=not st.session_state.credentials_uploaded):
            st.markdown("""
            **Step-by-step Guide:**
            
            1. **Go to Google Cloud Console**
               - Visit [console.cloud.google.com](https://console.cloud.google.com)
            
            2. **Create/Select Project**
               - Create a new project or select existing one
            
            3. **Enable Google Drive API**
               - Go to "APIs & Services" > "Library"
               - Search for "Google Drive API"
               - Click "Enable"
            
            4. **Create OAuth Credentials**
               - Go to "APIs & Services" > "Credentials"
               - Click "+ CREATE CREDENTIALS"
               - Select "OAuth client ID"
               - Choose "Desktop app" as application type
               - Name it (e.g., "Slideshow App")
            
            5. **Download JSON**
               - Click download icon next to your credential
               - Save as `client_secrets.json`
            
            6. **Upload Below**
               - Upload the downloaded JSON file
            """)
        
        # File uploader for credentials
        uploaded_creds = st.file_uploader(
            "Upload client_secrets.json",
            type=['json'],
            help="Upload your Google OAuth credentials file",
            key="creds_uploader"
        )
        
        if uploaded_creds:
            try:
                credentials_content = uploaded_creds.read().decode('utf-8')
                json.loads(credentials_content)  # Validate JSON
                st.session_state.credentials_content = credentials_content
                st.session_state.credentials_uploaded = True
                st.success("✅ Credentials file uploaded successfully!")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file. Please upload a valid client_secrets.json")
            except Exception as e:
                st.error(f"Error reading credentials: {e}")
        
        if st.session_state.credentials_uploaded:
            st.divider()
            
            # Initialize service if not done
            if st.session_state.drive_service is None:
                st.session_state.drive_service = initialize_drive_service(
                    st.session_state.credentials_content
                )
            
            if st.session_state.drive_service:
                st.success("🔗 Connected to Google Drive!")
                
                # Folder URL input
                gdrive_url = st.text_input(
                    "Google Drive Folder URL:",
                    value="https://drive.google.com/drive/folders/1LfSwuD7WxbS0ZdDeGo0hpiviUx6vMhqs",
                    help="Paste the URL of your Google Drive folder"
                )
                
                if st.button("📥 Load Files from Google Drive", type="primary", use_container_width=True):
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
                            st.warning("No media files found in the folder")
                    else:
                        st.error("Invalid Google Drive URL")
    
    else:  # Local Folder
        st.subheader("📁 Local Files")
        st.info("💡 Best for fast, offline access to your media")
        
        folder_path = st.text_input(
            "Folder Path:",
            placeholder="C:/Users/YourName/Pictures or /home/user/photos",
            help="Enter the full path to your media folder"
        )
        
        col1, col2 = st.columns(2)
        with col1:
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
        
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                if folder_path:
                    st.rerun()
    
    st.divider()
    
    # Playback settings
    st.subheader("⏱️ Playback Settings")
    duration = st.slider(
        "Display Duration:",
        min_value=1,
        max_value=30,
        value=3,
        step=1,
        format="%d sec",
        help="How long each file is displayed"
    )
    
    st.session_state.loop_mode = st.checkbox(
        "🔄 Loop Slideshow",
        value=True,
        help="Restart from beginning when reaching the end"
    )
    
    transition_effect = st.selectbox(
        "✨ Transition Effect:",
        ["None", "Fade", "Slide"],
        help="Visual effect between files (coming soon)"
    )
    
    st.divider()
    
    # Sorting
    st.subheader("🔤 Sorting & Filtering")
    
    sort_option = st.selectbox(
        "Sort by:",
        ["Name (A-Z)", "Name (Z-A)", "Date Modified (Newest)", "Date Modified (Oldest)", "Size (Largest)", "Size (Smallest)", "Random Shuffle"],
        help="Choose how to order your files"
    )
    
    if st.button("Apply Sort", use_container_width=True):
        if st.session_state.files:
            if sort_option == "Name (A-Z)":
                st.session_state.files.sort(key=lambda x: x['name'].lower())
            elif sort_option == "Name (Z-A)":
                st.session_state.files.sort(key=lambda x: x['name'].lower(), reverse=True)
            elif sort_option == "Date Modified (Newest)":
                st.session_state.files.sort(key=lambda x: x.get('modified', ''), reverse=True)
            elif sort_option == "Date Modified (Oldest)":
                st.session_state.files.sort(key=lambda x: x.get('modified', ''))
            elif sort_option == "Size (Largest)":
                st.session_state.files.sort(key=lambda x: int(x.get('size', 0)), reverse=True)
            elif sort_option == "Size (Smallest)":
                st.session_state.files.sort(key=lambda x: int(x.get('size', 0)))
            elif sort_option == "Random Shuffle":
                import random
                random.shuffle(st.session_state.files)
            st.session_state.current_idx = 0
            st.success("✅ Files sorted!")
            st.rerun()
    
    st.divider()
    
    # Filters
    show_images = st.checkbox("🖼️ Show Images", value=True)
    show_videos = st.checkbox("🎬 Show Videos", value=True)
    
    # File type filter
    if st.session_state.files:
        all_extensions = sorted(set(f['ext'] for f in st.session_state.files))
        selected_extensions = st.multiselect(
            "Filter by file type:",
            all_extensions,
            default=all_extensions,
            help="Show only specific file types"
        )
    
    st.divider()
    
    # Statistics
    if st.session_state.files:
        st.subheader("📊 Statistics")
        
        total_files = len(st.session_state.files)
        images = sum(1 for f in st.session_state.files if f['ext'] in IMAGE_EXT)
        videos = sum(1 for f in st.session_state.files if f['ext'] in VIDEO_EXT)
        total_size = sum(int(f.get('size', 0)) for f in st.session_state.files)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📁 Total Files", total_files)
            st.metric("🖼️ Images", images)
        with col2:
            st.metric("🎬 Videos", videos)
            st.metric("💾 Total Size", f"{total_size / (1024*1024):.1f} MB")
        
        # File type breakdown
        with st.expander("📋 File Type Breakdown"):
            ext_counts = {}
            for f in st.session_state.files:
                ext = f['ext']
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
            
            for ext, count in sorted(ext_counts.items()):
                st.text(f"{ext}: {count} files")

# Main content area
if not st.session_state.files:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("### 👋 Welcome to Live Photos & Video Slideshow Pro!")
    st.markdown("</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📁 **Local Folder Mode**
        
        **Best for:**
        - ⚡ Fast, instant access
        - 🔒 Privacy (no internet needed)
        - 💻 Local file collections
        
        **How to use:**
        1. Select "Local Folder" in sidebar
        2. Enter your folder path
        3. Click "Load Files"
        4. Start enjoying your slideshow!
        """)
    
    with col2:
        st.markdown("""
        ### ☁️ **Google Drive Mode**
        
        **Best for:**
        - 🌐 Cloud-stored collections
        - 📱 Access from anywhere
        - 🤝 Shared folders
        
        **How to use:**
        1. Select "Google Drive" in sidebar
        2. Upload your `client_secrets.json`
        3. Authenticate with Google
        4. Enter folder URL and load!
        """)
    
    st.divider()
    
    st.markdown("""
    ### ✨ **Premium Features:**
    
    | Feature | Description |
    |---------|-------------|
    | 🎮 **Full Playback Control** | Play, pause, navigate (previous/next/first/last) |
    | ⏱️ **Custom Timing** | Set display duration from 1-30 seconds |
    | 🔀 **Smart Sorting** | Sort by name, date, size, or random |
    | 🎯 **Advanced Filters** | Filter by media type and file extensions |
    | 🔄 **Loop Mode** | Continuous playback or single run |
    | 📊 **Statistics** | View detailed file information and breakdowns |
    | 🖼️ **Multi-Format** | Support for JPG, PNG, GIF, MP4, MOV, and more |
    | ☁️ **Cloud Integration** | Direct Google Drive access with OAuth |
    """)
    
    st.divider()
    
    st.info("👈 **Get started by selecting your source in the sidebar!**")
    
else:
    # Filter files based on settings
    filtered_files = []
    for f in st.session_state.files:
        type_match = (f['ext'] in IMAGE_EXT and show_images) or (f['ext'] in VIDEO_EXT and show_videos)
        ext_match = 'selected_extensions' not in locals() or f['ext'] in selected_extensions
        if type_match and ext_match:
            filtered_files.append(f)
    
    if not filtered_files:
        st.warning("⚠️ No files match your current filters. Try adjusting the filter settings in the sidebar.")
    else:
        # Ensure index is valid
        if st.session_state.current_idx >= len(filtered_files):
            st.session_state.current_idx = 0
        
        # Display current file counter
        current_file = filtered_files[st.session_state.current_idx]
        file_type_icon = "🖼️" if current_file['ext'] in IMAGE_EXT else "🎬"
        
        st.markdown(
            f'<div class="file-counter">{file_type_icon} File {st.session_state.current_idx + 1} of {len(filtered_files)}</div>',
            unsafe_allow_html=True
        )
        
        # Navigation controls
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 2, 1, 1, 1])
        
        with col1:
            if st.button("⏮️ First", use_container_width=True, help="Jump to first file"):
                st.session_state.current_idx = 0
                st.session_state.is_playing = False
                st.rerun()
        
        with col2:
            if st.button("◀️ Prev", use_container_width=True, help="Previous file"):
                st.session_state.current_idx = (st.session_state.current_idx - 1) % len(filtered_files)
                st.session_state.is_playing = False
                st.rerun()
        
        with col3:
            if st.session_state.is_playing:
                if st.button("⏸️ Pause Slideshow", use_container_width=True, type="primary"):
                    st.session_state.is_playing = False
                    st.rerun()
            else:
                if st.button("▶️ Play Slideshow", use_container_width=True, type="primary"):
                    st.session_state.is_playing = True
                    st.rerun()
        
        with col4:
            if st.button("▶️ Next", use_container_width=True, help="Next file"):
                st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
                st.session_state.is_playing = False
                st.rerun()
        
        with col5:
            if st.button("⏭️ Last", use_container_width=True, help="Jump to last file"):
                st.session_state.current_idx = len(filtered_files) - 1
                st.session_state.is_playing = False
                st.rerun()
        
        with col6:
            if st.button("🔀 Random", use_container_width=True, help="Jump to random file"):
                import random
                st.session_state.current_idx = random.randint(0, len(filtered_files) - 1)
                st.session_state.is_playing = False
                st.rerun()
        
        st.divider()
        
        # File information card
        file_size_mb = int(current_file.get('size', 0)) / (1024 * 1024)
        file_modified = current_file.get('modified', 'Unknown')
        if file_modified != 'Unknown':
            try:
                file_modified = datetime.fromisoformat(file_modified.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        info_col1, info_col2, info_col3 = st.columns([2, 1, 1])
        with info_col1:
            st.markdown(f"**📄 File:** `{current_file['name']}`")
        with info_col2:
            st.markdown(f"**💾 Size:** {file_size_mb:.2f} MB")
        with info_col3:
            st.markdown(f"**📅 Modified:** {file_modified}")
        
        # Display placeholder
        placeholder = st.empty()
        
        try:
            if current_file['ext'] in IMAGE_EXT:
                # Handle image display
                if current_file.get('source') == 'local':
                    img = Image.open(current_file['path'])
                    placeholder.image(img, use_container_width=True)
                elif current_file.get('source') == 'gdrive':
                    file_content = download_gdrive_file(st.session_state.drive_service, current_file['id'])
                    if file_content:
                        img = Image.open(file_content)
                        placeholder.image(img, use_container_width=True)
            
            elif current_file['ext'] in VIDEO_EXT:
                # Handle video display
                if current_file.get('source') == 'local':
                    placeholder.video(str(current_file['path']))
                elif current_file.get('source') == 'gdrive':
                    file_content = download_gdrive_file(st.session_state.drive_service, current_file['id'])
                    if file_content:
                        placeholder.video(file_content)
        
        except Exception as e:
            placeholder.error(f"❌ Error displaying file: {str(e)}")
        
        # Progress bar
        progress = (st.session_state.current_idx + 1) / len(filtered_files)
        st.progress(progress)
        
        # Auto-advance if playing
        if st.session_state.is_playing:
            time.sleep(duration)
            st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
            
            # Check if we should stop
            if not st.session_state.loop_mode and st.session_state.current_idx == 0:
                st.session_state.is_playing = False
                st.balloons()
                st.success("🎉 Slideshow completed!")
            
            st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; padding: 2rem;'>
    <strong>Live Photos & Video Slideshow Pro v2.0</strong><br>
    Made with ❤️ using Streamlit | Support for Local & Cloud Storage<br>
    <small>Features: OAuth2 Authentication • Multi-format Support • Advanced Sorting & Filtering</small>
</div>
""", unsafe_allow_html=True)
