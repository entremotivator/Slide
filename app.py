import streamlit as st
import os
import time
from pathlib import Path
from PIL import Image
import io
import tempfile
from datetime import datetime

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
    }
    .file-counter {
        text-align: center;
        font-size: 1.5rem;
        margin: 1rem 0;
        color: #555;
    }
    .status-text {
        text-align: center;
        font-size: 1.2rem;
        padding: 1rem;
        background: #f0f2f6;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎬 Live Photos & Video Slideshow</div>', unsafe_allow_html=True)

# Extract folder ID from Drive URL
def extract_folder_id(url):
    try:
        from urllib.parse import urlparse, parse_qs
        if "id=" in url:
            return parse_qs(urlparse(url).query).get("id", [None])[0]
        parts = url.split("/")
        if "folders" in parts:
            idx = parts.index("folders")
            if idx + 1 < len(parts):
                folder_id = parts[idx + 1].split('?')[0]
                return folder_id
        # Handle drive.google.com/drive/folders/ID format
        if "/folders/" in url:
            folder_id = url.split("/folders/")[1].split("?")[0].split("/")[0]
            return folder_id
    except Exception as e:
        st.error(f"Error parsing URL: {e}")
    return None

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Settings")
    
    source_type = st.radio("Choose Source:", ["Local Folder", "Google Drive"])
    
    if source_type == "Google Drive":
        st.info("📌 Share your Google Drive folder publicly and paste the URL")
        gdrive_url = st.text_input("Google Drive Folder URL:", 
                                   value="https://drive.google.com/drive/folders/1LfSwuD7WxbS0ZdDeGo0hpiviUx6vMhqs",
                                   placeholder="https://drive.google.com/drive/folders/...")
        
        if st.button("🔗 Load from Google Drive", type="primary"):
            folder_id = extract_folder_id(gdrive_url)
            if folder_id:
                with st.spinner("Connecting to Google Drive..."):
                    try:
                        from pydrive.auth import GoogleAuth
                        from pydrive.drive import GoogleDrive
                        
                        gauth = GoogleAuth()
                        gauth.LocalWebserverAuth()
                        drive = GoogleDrive(gauth)
                        
                        query = f"'{folder_id}' in parents and trashed=false"
                        file_list = drive.ListFile({'q': query}).GetList()
                        
                        temp_files = []
                        for f in file_list:
                            ext = os.path.splitext(f['title'])[1].lower()
                            if ext in IMAGE_EXT + VIDEO_EXT:
                                temp_files.append({
                                    'name': f['title'],
                                    'id': f['id'],
                                    'ext': ext,
                                    'file_obj': f
                                })
                        
                        st.session_state.files = temp_files
                        st.session_state.current_idx = 0
                        st.success(f"✅ Loaded {len(temp_files)} files from Google Drive!")
                    except Exception as e:
                        st.error(f"Error accessing Google Drive: {e}")
                        st.info("💡 Make sure PyDrive is installed: pip install PyDrive")
            else:
                st.error("Invalid Google Drive URL")
    
    else:  # Local Folder
        folder_path = st.text_input("Folder Path:", placeholder="/path/to/your/media")
        
        if st.button("📁 Load Local Files", type="primary"):
            p = Path(folder_path)
            if not p.exists():
                st.error("❌ Folder not found")
            else:
                files = [f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT + VIDEO_EXT]
                st.session_state.files = [{'path': f, 'ext': f.suffix.lower()} for f in files]
                st.session_state.current_idx = 0
                st.success(f"✅ Loaded {len(files)} files!")
    
    st.divider()
    
    # Playback settings
    st.subheader("⏱️ Playback")
    duration = st.slider("Display Duration (seconds):", 1, 30, 3)
    st.session_state.loop_mode = st.checkbox("Loop Slideshow", value=True)
    
    # Sorting
    st.subheader("🔤 Sorting")
    sort_option = st.selectbox("Sort by:", ["Name", "Date (newest first)", "Date (oldest first)", "Random"])
    
    if sort_option != st.session_state.sort_order:
        st.session_state.sort_order = sort_option
        if st.session_state.files:
            if sort_option == "Name":
                st.session_state.files.sort(key=lambda x: x.get('name', x.get('path', '').name))
            elif sort_option == "Random":
                import random
                random.shuffle(st.session_state.files)
    
    st.divider()
    
    # Filters
    st.subheader("🎨 Filters")
    show_images = st.checkbox("Show Images", value=True)
    show_videos = st.checkbox("Show Videos", value=True)
    
    st.divider()
    
    # Info
    if st.session_state.files:
        st.metric("Total Files", len(st.session_state.files))
        images = sum(1 for f in st.session_state.files if f['ext'] in IMAGE_EXT)
        videos = sum(1 for f in st.session_state.files if f['ext'] in VIDEO_EXT)
        st.metric("Images", images)
        st.metric("Videos", videos)

# Main content area
if not st.session_state.files:
    st.info("👈 Select a source and load your media files from the sidebar to begin")
    st.markdown("""
    ### Features:
    - 📁 Local folder or Google Drive support
    - ⏯️ Auto-play with customizable duration
    - 🔀 Multiple sorting options
    - 🎯 Image and video filtering
    - ⏭️ Manual navigation controls
    - 🔄 Loop mode
    - 📊 File statistics
    """)
else:
    # Filter files based on settings
    filtered_files = []
    for f in st.session_state.files:
        if f['ext'] in IMAGE_EXT and show_images:
            filtered_files.append(f)
        elif f['ext'] in VIDEO_EXT and show_videos:
            filtered_files.append(f)
    
    if not filtered_files:
        st.warning("No files match your current filters")
    else:
        # Ensure index is valid
        if st.session_state.current_idx >= len(filtered_files):
            st.session_state.current_idx = 0
        
        # Display current file counter
        st.markdown(f'<div class="file-counter">File {st.session_state.current_idx + 1} of {len(filtered_files)}</div>', 
                   unsafe_allow_html=True)
        
        # Navigation controls
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ First", use_container_width=True):
                st.session_state.current_idx = 0
                st.rerun()
        
        with col2:
            if st.button("◀️ Previous", use_container_width=True):
                st.session_state.current_idx = (st.session_state.current_idx - 1) % len(filtered_files)
                st.rerun()
        
        with col3:
            if st.session_state.is_playing:
                if st.button("⏸️ Pause", use_container_width=True, type="primary"):
                    st.session_state.is_playing = False
                    st.rerun()
            else:
                if st.button("▶️ Play", use_container_width=True, type="primary"):
                    st.session_state.is_playing = True
                    st.rerun()
        
        with col4:
            if st.button("▶️ Next", use_container_width=True):
                st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
                st.rerun()
        
        with col5:
            if st.button("⏭️ Last", use_container_width=True):
                st.session_state.current_idx = len(filtered_files) - 1
                st.rerun()
        
        # Display current file
        current_file = filtered_files[st.session_state.current_idx]
        
        st.divider()
        
        # File info
        file_name = current_file.get('name', current_file.get('path', 'Unknown').name)
        st.markdown(f"**📄 Current File:** {file_name}")
        
        # Display placeholder
        placeholder = st.empty()
        
        try:
            if current_file['ext'] in IMAGE_EXT:
                # Handle image display
                if 'path' in current_file:
                    img = Image.open(current_file['path'])
                    placeholder.image(img, use_container_width=True)
                else:
                    # Google Drive file
                    file_obj = current_file['file_obj']
                    file_obj.GetContentFile(f"temp_{current_file['id']}{current_file['ext']}")
                    img = Image.open(f"temp_{current_file['id']}{current_file['ext']}")
                    placeholder.image(img, use_container_width=True)
                    os.remove(f"temp_{current_file['id']}{current_file['ext']}")
            
            elif current_file['ext'] in VIDEO_EXT:
                # Handle video display
                if 'path' in current_file:
                    placeholder.video(str(current_file['path']))
                else:
                    # Google Drive file
                    file_obj = current_file['file_obj']
                    temp_path = f"temp_{current_file['id']}{current_file['ext']}"
                    file_obj.GetContentFile(temp_path)
                    placeholder.video(temp_path)
                    # Note: Can't delete immediately as video needs to stream
        
        except Exception as e:
            placeholder.error(f"Error displaying file: {e}")
        
        # Auto-advance if playing
        if st.session_state.is_playing:
            time.sleep(duration)
            st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
            
            # Check if we should stop (end of slideshow without loop)
            if not st.session_state.loop_mode and st.session_state.current_idx == 0:
                st.session_state.is_playing = False
                st.success("✅ Slideshow completed!")
            
            st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; padding: 2rem;'>
    Made with ❤️ using Streamlit | Supports images and videos from local folders or Google Drive
</div>
""", unsafe_allow_html=True)
