import os
import sys
import time
import io
import requests
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Drive API utilities
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Fix encoding for Vietnamese text on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ================== CẤU HÌNH ==================
load_dotenv()  # Nếu dùng .env cho token

# Facebook
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN")

# Google Drive (optional) – thư mục gốc chứa các thư mục theo category
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID", "")

# Google Sheets
CREDENTIALS_JSON_PATH = os.getenv("CREDENTIALS_JSON_PATH", "service-account-key.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "Content_facebook")

DELAY_BETWEEN_POSTS = 600  # giây → 10 phút, chỉnh tùy ý (ví dụ 300 = 5 phút)

# ================== KẾT NỐI GOOGLE SHEETS ==================
def connect_to_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(
        CREDENTIALS_JSON_PATH,
        scopes=scopes
    )
    client = gspread.authorize(creds)
    
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    
    data = worksheet.get_all_records()  # list of dicts
    df = pd.DataFrame(data)

    # print(f"ggshet", data)
    # print(f"Đọc thành công {len(df)} dòng từ sheet '{WORKSHEET_NAME}'")
    # print(f"Các cột trong sheet: {list(df.columns)}")
    return df, worksheet  # trả về cả worksheet để cập nhật sau nếu cần

# ================== HÀM KIỂM TRA KẾT NỐI ==================
def check_facebook_connection():
    """Kiểm tra xem token và page ID có hợp lệ không"""
    url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}"
    
    params = {
        "access_token": FACEBOOK_ACCESS_TOKEN,
        "fields": "id,name,access_token"
    }
    
    try:
        response = requests.get(url, params=params)
        result = response.json()
        
        if "id" in result:
            print(f"✓ Kết nối thành công!")
            print(f"  Page ID: {result.get('id')}")
            print(f"  Page Name: {result.get('name')}")
            return True
        else:
            if "error" in result:
                error_code = result["error"].get("code", "N/A")
                error_msg = result["error"].get("message", "Unknown error")
                print(f"✗ Lỗi xác thực (Code {error_code}): {error_msg}")
            return False
    except Exception as e:
        print(f"✗ Lỗi khi kiểm tra kết nối: {e}")
        return False

# ================== HÀM ĐĂNG BÀI ==================
def upload_unpublished_photo(image_path):
    """Upload ảnh lên Facebook nhưng chưa đăng (published=False) để lấy ID"""
    url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/photos"
    payload = {
        "access_token": FACEBOOK_ACCESS_TOKEN,
        "published": False
    }
    
    try:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            payload["url"] = image_path
            response = requests.post(url, data=payload, timeout=60)
        else:
            if not os.path.exists(image_path):
                print(f"✗ File ảnh không tìm thấy: {image_path}")
                return None
            
            with open(image_path, "rb") as img_file:
                files = {"source": img_file}
                response = requests.post(url, data=payload, files=files, timeout=120)
        
        result = response.json()
        if "id" in result:
            return result["id"]
        else:
            print(f"✗ Lỗi upload ảnh tạm: {result}")
            return None
    except Exception as e:
        print(f"✗ Lỗi khi upload ảnh tạm: {e}")
        return None

def post_to_facebook(caption, product, image_paths, hashtag, link=None):
    # Đảm bảo image_paths là list
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    
    # Thêm hashtag vào caption nếu có
    if (hashtag and link) or product:
        caption = f"🔥 {product} \n\n {caption}\n\n👉 Click link xem ngay trước khi “cháy hàng”: {link}\n\n{hashtag}"
    

    # TRƯỜNG HỢP 1: ĐĂNG 1 ẢNH 
    if len(image_paths) == 1:
        image_path = image_paths[0]
        url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/photos"
        payload = {
            "access_token": FACEBOOK_ACCESS_TOKEN,
            "caption": caption,
            "published": True
        }
        
        # Kiểm tra URL hay File
        if image_path.startswith("http://") or image_path.startswith("https://"):
            payload["url"] = image_path
            try:
                response = requests.post(url, data=payload, timeout=60)
                result = response.json()
                print(f"[DEBUG] Single photo response (code {response.status_code}): {json.dumps(result, indent=2)}")
                if "id" in result:
                    print(f"✓ ĐĂNG THÀNH CÔNG (1 ảnh)!")
                    return True
                print(f"✗ Lỗi: {result}")
                return False
            except Exception as e:
                print(f"✗ Lỗi API: {e}")
                return False
        else:
            if not os.path.exists(image_path):
                print(f"✗ File không tồn tại: {image_path}")
                return False
            try:
                with open(image_path, "rb") as f:
                    files = {"source": f}
                    response = requests.post(url, data=payload, files=files, timeout=120)
                    result = response.json()
                    if "id" in result:
                        print(f"✓ ĐĂNG THÀNH CÔNG (1 ảnh)!")
                        return True
                    print(f"✗ Lỗi: {result}")
                    return False
            except Exception as e:
                print(f"✗ Lỗi upload: {e}")
                return False

    # TRƯỜNG HỢP 2: ĐĂNG NHIỀU ẢNH
    else:
        print(f"  Đang xử lý album {len(image_paths)} ảnh...")
        media_ids = []
        
        for img in image_paths:
            print(f"  -> Uploading: {img[:50]}...")
            pid = upload_unpublished_photo(img)
            if pid:
                media_ids.append({"media_fbid": pid})
            else:
                print("  -> Upload ảnh thất bại, bỏ qua ảnh này.")
        
        if not media_ids:
            print("✗ Không upload được ảnh nào thành công.")
            return False
            
        # Đăng bài viết kèm danh sách ảnh
        url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/feed"
        payload = {
            "access_token": FACEBOOK_ACCESS_TOKEN,
            "message": caption,
            "attached_media": json.dumps(media_ids),
            "published": True
        }
        
        try:
            response = requests.post(url, data=payload, timeout=60)
            result = response.json()
            print(f"[DEBUG] Album feed response (code {response.status_code}): {json.dumps(result, indent=2)}")
            
            if "id" in result:
                print(f"✓ ĐĂNG THÀNH CÔNG (Album {len(media_ids)} ảnh)!")
                return True
            else:
                print(f"✗ Lỗi đăng feed: {result}")
                return False
        except Exception as e:
            print(f"✗ Lỗi API Feed: {e}")
            return False

# ================== GOOGLE DRIVE HELPERS ==================

def get_drive_service():
    """Build and return a Drive `service` object using the same service account creds."""
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_file(
        CREDENTIALS_JSON_PATH,
        scopes=scopes
    )
    return build("drive", "v3", credentials=creds)


def find_folder_id_by_name(name, parent_id=None):
    """Search for a folder with the given name. Optionally restrict to a parent folder.
    Returns the first match or None.
    """
    service = get_drive_service()
    query = "mimeType = 'application/vnd.google-apps.folder'"
    query += f" and name = '{name}'"
    query += " and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    resp = service.files().list(q=query, fields="files(id, name)").execute()
    items = resp.get("files", [])
    if items:
        return items[0]["id"]
    return None


def list_images_in_folder(folder_id):
    """Return a list of Drive file dicts for images inside the specified folder."""
    service = get_drive_service()
    query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    resp = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return resp.get("files", [])


def download_file(file_id, dest_path):
    """Download a Drive file to the given local path."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return dest_path


def get_images_for_category(category):
    """Given a category string, look for a folder with that name under the
    root folder (if configured) and download all image files.
    Returns a list of local file paths.
    """
    if not category:
        return []

    parent = DRIVE_ROOT_FOLDER_ID or None
    folder_id = find_folder_id_by_name(category, parent_id=parent)
    if not folder_id:
        print(f"⚠️ Không tìm thấy thư mục Drive cho category '{category}'")
        return []

    imgs = list_images_in_folder(folder_id)
    if not imgs:
        print(f"⚠️ Không tìm thấy ảnh nào trong thư mục '{category}'")
        return []

    local_paths = []
    base_dir = os.path.join("downloaded_images", category)
    os.makedirs(base_dir, exist_ok=True)
    for f in imgs:
        name = f["name"]
        fid = f["id"]
        dest = os.path.join(base_dir, name)
        # only download if missing to avoid repeated API calls
        if not os.path.exists(dest):
            print(f"    Tải về {name}...")
            try:
                download_file(fid, dest)
            except Exception as e:
                print(f"    ✗ Lỗi khi tải {name}: {e}")
                continue
        local_paths.append(dest)
    return local_paths


# ================== CHẠY CHÍNH ==================
def main():
    print("=" * 50)
    print("KIỂM TRA KẾT NỐI FACEBOOK")
    print("=" * 50)
    
    if not check_facebook_connection():
        print("\n✗ Không thể kết nối Facebook. Dừng chương trình.")
        return
    
    print("\n" + "=" * 50)
    print("LẤY DỮ LIỆU TỪ GOOGLE SHEETS")
    print("=" * 50 + "\n")
    
    df, worksheet = connect_to_sheet()
    
    required_cols = ["Caption", "ImagePath"]
    if not all(col in df.columns for col in required_cols):
        print("Sheet thiếu cột bắt buộc: Caption và ImagePath")
        return

    # Nếu có cột Trạng thái → chỉ xử lý "Inprocess"
    if "Trạng thái" in df.columns:
        df = df[df["Trạng thái"].str.contains("Inprocess", na=False, case=False)]
        print(f"Lọc còn {len(df)} bài 'Inprocess'")
    
    if df.empty:
        print("Không có bài nào cần đăng.")
        return
    
    for index, row in df.iterrows():
        caption = str(row["Caption"]).strip()
        image_raw = str(row.get("ImagePath", "")).strip()
        hashtag = str(row.get("Hashtags", "")).strip()
        link = str(row.get("Link", "")).strip()
        product = str(row.get("Product", "")).strip()
        category = str(row.get("Category", "")).strip()
        
        # nếu người dùng không cung cấp đường dẫn ảnh trực tiếp, thử lấy theo category
        image_paths = []
        if image_raw:
            # Tách nhiều ảnh bằng dấu phẩy hoặc xuống dòng
            image_paths = [x.strip() for x in image_raw.replace('\n', ',').split(',') if x.strip()]
        elif category:
            print(f"→ Không có ImagePath, lấy ảnh theo Category '{category}' từ Drive")
            image_paths = get_images_for_category(category)

        if not caption or not image_paths:
            print(f"Bỏ qua dòng {index + 2}: thiếu caption hoặc ảnh (category={category})")
            continue
        
        print(f"\nXử lý bài: {caption[:50]}...")
        
        success = post_to_facebook(caption, product, image_paths, hashtag, link)
        
        if success:
            # Cập nhật trạng thái lại sheet
            if "Trạng thái" in df.columns:
                row_index = index + 2  # vì header ở dòng 1
                worksheet.update_cell(row_index, df.columns.get_loc("Trạng thái") + 1, "Done")
                print(f"-> Đã cập nhật trạng thái bài post thành 'Done'")
        else:
            print("Đăng thất bại → tiếp tục bài sau")
        
        # Chờ giữa các bài (trừ bài cuối)
        if index < len(df) - 1:
            print(f"Chờ {DELAY_BETWEEN_POSTS // 60} phút...")
            time.sleep(DELAY_BETWEEN_POSTS)

if __name__ == "__main__":
    main()