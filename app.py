# drive_utils.py
import pickle, io, os, tempfile, re, json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from pathlib import Path

IMAGE_EXT = [".jpg", ".jpeg", ".png", ".heic", ".gif", ".bmp", ".webp"]
VIDEO_EXT = [".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"]
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GDriveHelper:
    def __init__(self, credentials_content, token_pickle=None):
        self.credentials_content = credentials_content
        self.token_pickle = token_pickle
        self.creds = None
        self.service = None

    def authenticate(self, redirect_for_desktop=True):
        if self.token_pickle:
            try:
                self.creds = pickle.loads(self.token_pickle)
            except Exception:
                self.token_pickle = None

        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            self.token_pickle = pickle.dumps(self.creds)

        if not self.creds or not self.creds.valid:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_creds_file:
                temp_creds_file.write(self.credentials_content)
                temp_creds_path = temp_creds_file.name

            try:
                flow = Flow.from_client_secrets_file(
                    temp_creds_path,
                    scopes=SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob' if redirect_for_desktop else None
                )
                auth_url, _ = flow.authorization_url(prompt='consent')
                # return auth_url for browser login
                return auth_url, flow, temp_creds_path
            finally:
                os.unlink(temp_creds_path)
        else:
            self.service = build('drive', 'v3', credentials=self.creds)
            return self.service

    def build_service_after_auth(self, flow):
        self.creds = flow.credentials
        self.token_pickle = pickle.dumps(self.creds)
        self.service = build('drive', 'v3', credentials=self.creds)
        return self.service

    def extract_folder_id(self, url):
        if "id=" in url:
            match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        if "/folders/" in url:
            match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        return None

    def list_files(self, folder_id):
        files, page_token = [], None
        while True:
            query = f"'{folder_id}' in parents and trashed=false and (mimeType contains 'image/' or mimeType contains 'video/')"
            results = self.service.files().list(
                q=query, pageSize=50,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)", pageToken=page_token
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
                        'mime_type': item.get('mimeType', ''),
                        'created': item.get('createdTime', ''),
                        'modified': item.get('modifiedTime', ''),
                        'source': 'gdrive'
                    })
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        return files

    def download_file(self, file_id, ext):
        from googleapiclient.http import MediaIoBaseDownload
        request = self.service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        while True:
            status, done = downloader.next_chunk()
            if done:
                break
        file_content.seek(0)
        return file_content

