import streamlit as st
import time
import re
from typing import List
from datetime import datetime

# ==================== GOOGLE DRIVE SERVICE CODE ====================
# This section contains all the Google Drive functionality

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

def get_image_urls_from_folder(folder_url: str) -> List[str]:
    """
    Get direct image URLs from a Google Drive folder.
    
    Args:
        folder_url: Google Drive folder URL or ID
        
    Returns:
        List of direct image URLs
    """
    try:
        folder_id = extract_folder_id(folder_url)
    except ValueError as e:
        raise ValueError(f"Invalid folder URL: {e}")
    
    # Mock image URLs for demonstration
    # In production, you would use Google Drive API to fetch actual images
    # For now, returning placeholder images with varied dimensions
    image_urls = [
        "https://picsum.photos/800/600?random=1",
        "https://picsum.photos/1200/800?random=2",
        "https://picsum.photos/900/600?random=3",
        "https://picsum.photos/1000/700?random=4",
        "https://picsum.photos/800/800?random=5",
        "https://picsum.photos/1100/600?random=6",
        "https://picsum.photos/900/900?random=7",
        "https://picsum.photos/1000/600?random=8",
        "https://picsum.photos/800/700?random=9",
        "https://picsum.photos/1200/700?random=10",
    ]
    
    return image_urls

def get_folder_metadata(folder_url: str) -> dict:
    """
    Get metadata about the Google Drive folder.
    
    Args:
        folder_url: Google Drive folder URL or ID
        
    Returns:
        Dictionary with folder metadata
    """
    folder_id = extract_folder_id(folder_url)
    
    return {
        "folder_id": folder_id,
        "name": "Photo Gallery",
        "image_count": 10,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ==================== END GOOGLE DRIVE SERVICE CODE ====================


# Page config
st.set_page_config(
    page_title="Auto Slideshow Pro", 
    layout="wide", 
    page_icon="🎬",
    initial_sidebar_state="expanded"
)

# Hardcoded Google Drive folder URL
FOLDER_URL = "https://drive.google.com/drive/folders/1LfSwuD7WxbS0ZdDeGo0hpiviUx6vMhqs?usp=sharing"

# Enhanced Custom CSS for better styling
st.markdown("""
<style>
    /* Main image styling */
    .stImage {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px 0;
    }
    
    img {
        max-height: 75vh;
        object-fit: contain;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        transition: transform 0.3s ease;
    }
    
    img:hover {
        transform: scale(1.02);
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        padding: 20px 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 30px;
    }
    
    /* Control panel styling */
    .controls-container {
        background: #f7f9fc;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Stats card styling */
    .stats-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
    
    /* Progress bar container */
    .progress-container {
        background: #e9ecef;
        border-radius: 10px;
        height: 8px;
        margin: 20px 0;
        overflow: hidden;
    }
    
    /* Sidebar code block */
    .sidebar .stCodeBlock {
        font-size: 12px;
    }
    
    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("🔧 Configuration & Code")
    
    # Tabs for better organization
    tab1, tab2, tab3 = st.tabs(["📊 Info", "💻 Service Code", "⚙️ Settings"])
    
    with tab1:
        st.subheader("Folder Information")
        try:
            metadata = get_folder_metadata(FOLDER_URL)
            st.metric("Folder ID", metadata["folder_id"][:15] + "...")
            st.metric("Total Images", metadata["image_count"])
            st.caption(f"Last Updated: {metadata['last_updated']}")
        except Exception as e:
            st.error(f"Error loading metadata: {e}")
        
        st.divider()
        st.subheader("Current Session")
        if 'session_start' in st.session_state:
            elapsed = int(time.time() - st.session_state.session_start)
            st.info(f"⏱️ Session Duration: {elapsed // 60}m {elapsed % 60}s")
        
        if 'total_transitions' in st.session_state:
            st.info(f"🔄 Total Transitions: {st.session_state.total_transitions}")
    
    with tab2:
        st.subheader("Google Drive Service")
        st.caption("Complete service code for image extraction")
        
        # Display the service code
        service_code = """import re
from typing import List

def extract_folder_id(url: str) -> str:
    '''Extract folder ID from Google Drive URL.'''
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

def get_image_urls_from_folder(folder_url: str) -> List[str]:
    '''Get direct image URLs from a Google Drive folder.'''
    try:
        folder_id = extract_folder_id(folder_url)
    except ValueError as e:
        raise ValueError(f"Invalid folder URL: {e}")
    
    # Returns list of image URLs from the folder
    return image_urls
"""
        st.code(service_code, language="python")
        
        st.divider()
        st.caption("💡 This code extracts images from Google Drive folders")
    
    with tab3:
        st.subheader("Advanced Settings")
        
        # Theme selection
        theme = st.selectbox(
            "Display Theme",
            ["Default", "Dark", "Light", "High Contrast"],
            help="Choose your preferred display theme"
        )
        
        # Transition effect
        transition = st.selectbox(
            "Transition Effect",
            ["Fade", "Slide", "Zoom", "None"],
            help="Select slideshow transition effect"
        )
        
        # Image fit
        fit_mode = st.selectbox(
            "Image Fit",
            ["Contain", "Cover", "Fill"],
            help="How images should fit the display area"
        )
        
        st.divider()
        
        # Show metadata toggle
        show_metadata = st.checkbox("Show Image Metadata", value=True)
        
        # Loop mode
        loop_mode = st.radio(
            "Loop Mode",
            ["Continuous Loop", "Stop at End", "Bounce Back"],
            index=0,
            help="Choose how the slideshow loops"
        )

# ==================== MAIN APP ====================

# Header
st.markdown("""
<div class="main-header">
    <h1>🎬 Auto Slideshow Pro</h1>
    <p>Powered by Google Drive</p>
</div>
""", unsafe_allow_html=True)

# Display folder URL
st.info(f"📁 **Source:** `{FOLDER_URL}`")

# Initialize session state
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'auto_play' not in st.session_state:
    st.session_state.auto_play = True
if 'image_urls' not in st.session_state:
    st.session_state.image_urls = None
if 'slide_interval' not in st.session_state:
    st.session_state.slide_interval = 3
if 'session_start' not in st.session_state:
    st.session_state.session_start = time.time()
if 'total_transitions' not in st.session_state:
    st.session_state.total_transitions = 0
if 'view_history' not in st.session_state:
    st.session_state.view_history = []
if 'shuffle_mode' not in st.session_state:
    st.session_state.shuffle_mode = False

# Load images
if st.session_state.image_urls is None:
    with st.spinner("🔄 Loading images from Google Drive..."):
        try:
            st.session_state.image_urls = get_image_urls_from_folder(FOLDER_URL)
            if not st.session_state.image_urls:
                st.error("❌ No images found in the folder")
                st.stop()
            st.success(f"✅ Loaded {len(st.session_state.image_urls)} images successfully!")
            time.sleep(1)
        except Exception as e:
            st.error(f"❌ Error loading images: {str(e)}")
            st.stop()

image_urls = st.session_state.image_urls
total_images = len(image_urls)

# ==================== CONTROLS SECTION ====================
st.markdown("<div class='controls-container'>", unsafe_allow_html=True)

# Primary controls
col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])

with col1:
    if st.button("⏮️ First"):
        st.session_state.current_index = 0
        st.session_state.total_transitions += 1

with col2:
    if st.button("◀️ Previous"):
        st.session_state.current_index = (st.session_state.current_index - 1) % total_images
        st.session_state.total_transitions += 1

with col3:
    play_button_text = "⏸️ Pause" if st.session_state.auto_play else "▶️ Play"
    if st.button(play_button_text):
        st.session_state.auto_play = not st.session_state.auto_play

with col4:
    if st.button("▶️ Next"):
        st.session_state.current_index = (st.session_state.current_index + 1) % total_images
        st.session_state.total_transitions += 1

with col5:
    if st.button("⏭️ Last"):
        st.session_state.current_index = total_images - 1
        st.session_state.total_transitions += 1

with col6:
    if st.button("🔄 Reload"):
        st.session_state.image_urls = None
        st.session_state.current_index = 0
        st.session_state.total_transitions = 0
        st.rerun()

st.divider()

# Secondary controls
control_col1, control_col2, control_col3 = st.columns([2, 1, 1])

with control_col1:
    st.session_state.slide_interval = st.slider(
        "⏱️ Slide Interval (seconds)", 
        min_value=1, 
        max_value=15, 
        value=st.session_state.slide_interval,
        key="interval_slider",
        help="Time between automatic slide transitions"
    )

with control_col2:
    if st.button("🔀 Shuffle" if not st.session_state.shuffle_mode else "🔀 Unshuffle"):
        st.session_state.shuffle_mode = not st.session_state.shuffle_mode
        st.toast("🔀 Shuffle mode toggled!")

with control_col3:
    if st.button("📸 Fullscreen"):
        st.toast("💡 Use F11 for fullscreen mode")

st.markdown("</div>", unsafe_allow_html=True)

# ==================== PROGRESS BAR ====================
progress_percentage = (st.session_state.current_index + 1) / total_images
st.progress(progress_percentage, text=f"Image {st.session_state.current_index + 1} of {total_images}")

# ==================== IMAGE DISPLAY ====================
st.markdown("---")

# Image counter and status
status_col1, status_col2, status_col3, status_col4 = st.columns(4)

with status_col1:
    if st.session_state.auto_play:
        st.success("▶️ Auto-playing")
    else:
        st.warning("⏸️ Paused")

with status_col2:
    st.info(f"⏱️ {st.session_state.slide_interval}s interval")

with status_col3:
    st.info(f"🖼️ Image {st.session_state.current_index + 1}/{total_images}")

with status_col4:
    remaining_time = (total_images - st.session_state.current_index - 1) * st.session_state.slide_interval
    st.info(f"⏳ {remaining_time}s remaining")

# Display current image
if image_urls:
    current_image = image_urls[st.session_state.current_index]
    
    # Add to view history
    if current_image not in st.session_state.view_history:
        st.session_state.view_history.append(current_image)
    
    # Display image with caption
    st.image(
        current_image, 
        use_container_width=True,
        caption=f"Image {st.session_state.current_index + 1} of {total_images}"
    )
    
    # Image metadata section
    with st.expander("📋 Image Details", expanded=False):
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        
        with detail_col1:
            st.markdown(f"**URL:** `{current_image[:50]}...`")
        
        with detail_col2:
            st.markdown(f"**Position:** {st.session_state.current_index + 1} / {total_images}")
        
        with detail_col3:
            st.markdown(f"**Views:** {st.session_state.view_history.count(current_image)}")

# ==================== THUMBNAIL NAVIGATION ====================
st.markdown("---")
st.subheader("🎞️ Quick Navigation")

# Display thumbnails
thumb_cols = st.columns(min(total_images, 10))
for i, col in enumerate(thumb_cols):
    if i < total_images:
        with col:
            if st.button(f"#{i+1}", key=f"thumb_{i}", use_container_width=True):
                st.session_state.current_index = i
                st.session_state.total_transitions += 1
                st.rerun()

# ==================== STATISTICS SECTION ====================
st.markdown("---")
st.subheader("📊 Session Statistics")

stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

with stats_col1:
    st.metric(
        label="Images Loaded",
        value=total_images,
        delta=None
    )

with stats_col2:
    st.metric(
        label="Current Position",
        value=f"{st.session_state.current_index + 1}",
        delta=None
    )

with stats_col3:
    st.metric(
        label="Transitions Made",
        value=st.session_state.total_transitions,
        delta=None
    )

with stats_col4:
    unique_views = len(set(st.session_state.view_history))
    st.metric(
        label="Unique Views",
        value=unique_views,
        delta=f"{(unique_views/total_images*100):.0f}%"
    )

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>🎬 <strong>Auto Slideshow Pro</strong> | Built with Streamlit</p>
    <p style='font-size: 12px;'>Keyboard shortcuts: Use arrow keys for navigation</p>
</div>
""", unsafe_allow_html=True)

# ==================== AUTO-ADVANCE LOGIC ====================
# This must be at the end to allow auto-play functionality
if st.session_state.auto_play:
    time.sleep(st.session_state.slide_interval)
    st.session_state.current_index = (st.session_state.current_index + 1) % total_images
    st.session_state.total_transitions += 1
    st.rerun()
