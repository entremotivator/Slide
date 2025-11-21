import streamlit as st
import os
import time
from pathlib import Path
from PIL import Image
import io
import requests
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

# Load files from public Google Drive folder (no auth required)
def load_public_gdrive_files(folder_id):
    try:
        # Use Google Drive API v3 to list files in public folder
        api_key = "AIzaSyDummy"  # For public folders, we can use the public API
        
        # Alternative: Use direct folder access
        # Get folder metadata and file list via web scraping the public share link
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        
        st.info(f"🔗 Accessing public folder: {folder_id}")
        
        # For public folders, we'll use the uc?export=download endpoint
        # First, let's try to get the file list using the Drive API without auth
        
        # Since we can't easily list files from public folder without API key,
        # we'll use a different approach - iframe embedding or direct links
        
        # For now, let's create a workaround using known file IDs
        # In production, you'd want to use proper Google Drive API with service account
        
        st.warning("⚠️ Direct public folder listing requires Google Drive API setup.")
        st.info("💡 **Alternative Solution**: Please use one of these methods:")
        st.markdown("""
        1. **Local Folder**: Download the files and use local folder option
        2. **Individual Links**: Share individual file links instead of folder
        3. **API Setup**: Set up Google Drive API credentials (see sidebar)
        """)
        
        return []
        
    except Exception as e:
        st.error(f"Error accessing folder: {e}")
        return []

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Settings")
    
    source_type = st.radio("Choose Source:", ["Google Drive (Public)", "Local Folder"])
    
    if source_type == "Google Drive (Public)":
        st.info("📌 Using pre-configured public Google Drive folder")
        gdrive_url = "https://drive.google.com/drive/folders/1LfSwuD7WxbS0ZdDeGo0hpiviUx6vMhqs"
        st.text_input("Google Drive Folder URL:", value=gdrive_url, disabled=True)
        
        st.divider()
        st.warning("⚠️ Public folder file listing limitations")
        st.markdown("""
        **To use Google Drive, you need to:**
        
        1. **Download the folder locally** and use "Local Folder" option, OR
        2. **Set up Google Drive API** (requires credentials)
        
        **Quick Setup for API:**
        - Go to [Google Cloud Console](https://console.cloud.google.com)
        - Enable Google Drive API
        - Create OAuth credentials
        - Download `client_secrets.json`
        - Place in same folder as this script
        """)
        
        st.divider()
        st.info("💡 **Recommended**: Download the Google Drive folder to your computer and use the 'Local Folder' option for instant access!")
        
    else:  # Local Folder
        st.success("✅ Best option for immediate use!")
        folder_path = st.text_input("Folder Path:", placeholder="/path/to/your/media")
        
        if st.button("📁 Load Local Files", type="primary"):
            p = Path(folder_path)
            if not p.exists():
                st.error("❌ Folder not found")
            else:
                files = [f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT + VIDEO_EXT]
                st.session_state.files = [{'path': f, 'ext': f.suffix.lower(), 'name': f.name} for f in sorted(files)]
                st.session_state.current_idx = 0
                st.session_state.loaded = True
                st.success(f"✅ Loaded {len(files)} files!")
                st.rerun()
    
    st.divider()
    
    # Playback settings
    st.subheader("⏱️ Playback")
    duration = st.slider("Display Duration (seconds):", 1, 30, 3)
    st.session_state.loop_mode = st.checkbox("Loop Slideshow", value=True)
    
    # Sorting
    st.subheader("🔤 Sorting")
    sort_option = st.selectbox("Sort by:", ["Name", "Random"])
    
    if sort_option != st.session_state.sort_order and st.session_state.files:
        st.session_state.sort_order = sort_option
        if sort_option == "Name":
            st.session_state.files.sort(key=lambda x: x.get('name', ''))
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
    st.info("👈 Select 'Local Folder' from the sidebar and load your media files to begin")
    
    st.markdown("""
    ### 📋 Quick Start Guide:
    
    #### **Option 1: Local Folder (Recommended)**
    1. Download the Google Drive folder to your computer
    2. Select "Local Folder" in the sidebar
    3. Enter the path to your downloaded folder
    4. Click "📁 Load Local Files"
    5. Enjoy your slideshow! 🎉
    
    #### **Option 2: Google Drive API**
    - Requires `client_secrets.json` configuration
    - See sidebar for setup instructions
    
    ---
    
    ### ✨ Features:
    - ⏯️ **Auto-play** with customizable duration
    - 🎮 **Manual navigation** (Previous/Next/First/Last)
    - 🔀 **Sorting options** (Name or Random)
    - 🎯 **Filters** (Toggle images/videos)
    - 🔄 **Loop mode** for continuous playback
    - 📊 **Statistics** dashboard
    - 🖼️ **Support** for images (JPG, PNG, GIF, WEBP, etc.)
    - 🎬 **Support** for videos (MP4, MOV, AVI, etc.)
    """)
    
    st.divider()
    
    st.markdown("""
    ### 💡 Tips:
    - Use keyboard shortcuts for navigation (coming soon!)
    - Adjust duration based on your content (3 seconds default)
    - Enable loop mode for continuous display
    - Filter by media type for focused viewing
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
        st.warning("No files match your current filters. Try enabling both images and videos in the sidebar.")
    else:
        # Ensure index is valid
        if st.session_state.current_idx >= len(filtered_files):
            st.session_state.current_idx = 0
        
        # Display current file counter
        st.markdown(f'<div class="file-counter">📸 File {st.session_state.current_idx + 1} of {len(filtered_files)}</div>', 
                   unsafe_allow_html=True)
        
        # Navigation controls
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ First", use_container_width=True):
                st.session_state.current_idx = 0
                st.session_state.is_playing = False
                st.rerun()
        
        with col2:
            if st.button("◀️ Previous", use_container_width=True):
                st.session_state.current_idx = (st.session_state.current_idx - 1) % len(filtered_files)
                st.session_state.is_playing = False
                st.rerun()
        
        with col3:
            if st.session_state.is_playing:
                if st.button("⏸️ Pause", use_container_width=True, type="primary"):
                    st.session_state.is_playing = False
                    st.rerun()
            else:
                if st.button("▶️ Play Slideshow", use_container_width=True, type="primary"):
                    st.session_state.is_playing = True
                    st.rerun()
        
        with col4:
            if st.button("▶️ Next", use_container_width=True):
                st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
                st.session_state.is_playing = False
                st.rerun()
        
        with col5:
            if st.button("⏭️ Last", use_container_width=True):
                st.session_state.current_idx = len(filtered_files) - 1
                st.session_state.is_playing = False
                st.rerun()
        
        # Display current file
        current_file = filtered_files[st.session_state.current_idx]
        
        st.divider()
        
        # File info
        file_name = current_file.get('name', 'Unknown')
        file_type = "🖼️ Image" if current_file['ext'] in IMAGE_EXT else "🎬 Video"
        st.markdown(f"**{file_type}:** `{file_name}`")
        
        # Display placeholder
        placeholder = st.empty()
        
        try:
            if current_file['ext'] in IMAGE_EXT:
                # Handle image display
                if 'path' in current_file:
                    img = Image.open(current_file['path'])
                    placeholder.image(img, use_container_width=True)
            
            elif current_file['ext'] in VIDEO_EXT:
                # Handle video display
                if 'path' in current_file:
                    placeholder.video(str(current_file['path']))
        
        except Exception as e:
            placeholder.error(f"❌ Error displaying file: {e}")
        
        # Auto-advance if playing
        if st.session_state.is_playing:
            time.sleep(duration)
            st.session_state.current_idx = (st.session_state.current_idx + 1) % len(filtered_files)
            
            # Check if we should stop (end of slideshow without loop)
            if not st.session_state.loop_mode and st.session_state.current_idx == 0:
                st.session_state.is_playing = False
                st.balloons()
                st.success("✅ Slideshow completed!")
            
            st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #888; padding: 2rem;'>
    Made with ❤️ using Streamlit | Perfect for viewing your photo and video collections
</div>
""", unsafe_allow_html=True)
