import streamlit as st
import os
import io
import json
import tempfile
from pathlib import Path
from PIL import Image
from datetime import datetime
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Drive Slideshow (Service Account)")

IMAGE_EXT = [".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp"]
VIDEO_EXT = [".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"]

def extract_folder_id(url):
    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def build_drive_service(service_json_path):
    creds = service_account.Credentials.from_service_account_file(
        service_json_path,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build('drive', 'v3', credentials=creds)

def list_drive_files(service, folder_id):
    files = []
    page_token = None
    while True:
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)",
                pageToken=page_token
            ).execute()
            items = results.get('files', [])
            for item in items:
                ext = os.path.splitext(item['name'])[1].lower()
                if ext in IMAGE_EXT + VIDEO_EXT:
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
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
        except HttpError as e:
            st.error(f"Google Drive API Error: {e.content.decode()}")
            break
    return files

def download_drive_file(service, file_id):
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

# --- Sidebar UI ---
with st.sidebar:
    st.header("Google Drive Service Account Mode")
    st.write("""
        1. Download a Service Account JSON from Google Cloud.
        2. Share your Google Drive folder with the Service Account email (found in the JSON).
        3. Upload Service Account JSON below.
        4. Enter Drive folder URL and load.
    """)
    uploaded_json = st.file_uploader("Service Account JSON", type=["json"])
    drive_url = st.text_input("Google Drive Folder URL")
    duration = st.slider("Display Duration (sec)", 1, 30, 3)
    st.divider()
    st.session_state.loop_mode = st.checkbox("Loop Slideshow", value=True)

    if uploaded_json:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_json.read())
            service_json_path = tmp_file.name

        service = build_drive_service(service_json_path)
        folder_id = extract_folder_id(drive_url)
        st.session_state.files = []
        if folder_id and service:
            if st.button("Load Files"):
                st.session_state.files = list_drive_files(service, folder_id)
                st.session_state.current_idx = 0
                st.session_state.loaded = True
        else:
            st.info("Upload JSON and enter a valid Drive folder URL.")

# --- Slideshow Content ---
if not st.session_state.get('files', []):
    st.warning("No files loaded. Please configure sidebar and click Load Files.")
else:
    files = st.session_state['files']
    if 'current_idx' not in st.session_state:
        st.session_state['current_idx'] = 0
    idx = st.session_state['current_idx']
    file = files[idx]
    st.markdown(f"### File {idx + 1}/{len(files)}: {file['name']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◀️ Prev"):
            st.session_state['current_idx'] = (idx - 1) % len(files)
            st.experimental_rerun()
    with col3:
        if st.button("▶️ Next"):
            st.session_state['current_idx'] = (idx + 1) % len(files)
            st.experimental_rerun()

    # --- Display File ---
    service = build_drive_service(service_json_path)
    file_content = download_drive_file(service, file['id'])
    if file_content:
        if file['ext'] in IMAGE_EXT:
            image = Image.open(file_content)
            st.image(image, caption=file['name'], use_column_width=True)
        elif file['ext'] in VIDEO_EXT:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file['ext']) as tmp_video:
                tmp_video.write(file_content.read())
                temp_path = tmp_video.name
            st.video(temp_path)
            os.unlink(temp_path)
