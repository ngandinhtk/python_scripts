import os
import sys
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Nếu thay đổi scope → xóa file token.json để auth lại
SCOPES = ['https://www.googleapis.com/auth/drive.file']  # Chỉ cho phép app tạo/upload file riêng, an toàn nhất
# Hoặc dùng 'https://www.googleapis.com/auth/drive' nếu cần full quyền

# Fix encoding for Vietnamese text on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def get_drive_service():
    """Authenticate và trả về service Drive"""
    creds = None
    # token.json lưu token sau lần auth đầu
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)  # Mở browser để bạn login Google
        # Lưu token cho lần sau
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)


def upload_folder_images(local_folder_path, drive_folder_name=None):
    """
    Upload tất cả ảnh từ local_folder_path lên Google Drive.
    - Tạo folder drive_folder_name nếu chỉ định.
    - Hỗ trợ resumable upload.
    """
    service = get_drive_service()
    
    # Tạo thư mục trên Drive nếu cần
    parent_id = None
    if drive_folder_name:
        # Tìm hoặc tạo folder
        query = f"name='{drive_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, fields="files(id, name)").execute()
        folders = response.get('files', [])
        
        if folders:
            parent_id = folders[0]['id']
            # print(f"Đã tìm thấy folder '{drive_folder_name}' (ID: {parent_id})")
            print(f"Found existing folder '{drive_folder_name}' (ID: {parent_id})")
        else:
            folder_metadata = {
                'name': drive_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            parent_id = folder.get('id')
            # print(f"Đã tạo folder '{drive_folder_name}' (ID: {parent_id})")
            print(f"Created folder '{drive_folder_name}' (ID: {parent_id})")
    
    # Duyệt folder local
    supported_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp')
    uploaded_count = 0
    
    for file_name in os.listdir(local_folder_path):
        if file_name.lower().endswith(supported_extensions):
            file_path = os.path.join(local_folder_path, file_name)
            
            # Kiểm tra xem file đã tồn tại trên Drive chưa (dựa trên tên, trong folder nếu có)
            if parent_id:
                query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            else:
                query = f"name='{file_name}' and trashed=false"
            
            response = service.files().list(q=query, fields="files(id)").execute()
            if response.get('files'):
                # print(f"Skip: {file_name} đã tồn tại trên Drive.")
                print( f"Skipped: {file_name} already exists on Drive.")
                continue
            
            # Metadata
            file_metadata = {'name': file_name}
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            # Upload với resumable (tốt cho file lớn)
            media = MediaFileUpload(file_path, resumable=True)
            
            try:
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"Uploaded: {file_name} ID: {file.get('id')}")
                uploaded_count += 1
            except HttpError as error:
                print(f"Error uploading {file_name}: {error}")
    
    print(f"Done! Uploaded {uploaded_count} images.")


# ================= SỬ DỤNG =================
if __name__ == '__main__':
    LOCAL_FOLDER = r"C:\Users\KNgan\Pictures\apartments"  
    
    # Tên folder trên Drive (nếu để None thì upload vào root)
    DRIVE_FOLDER_NAME = "LANDMARD 810 Apartments"
    
    upload_folder_images(LOCAL_FOLDER, DRIVE_FOLDER_NAME)