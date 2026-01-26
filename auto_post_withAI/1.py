

import os
import sys
import time
import requests
import pandas as pd
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Fix encoding for Vietnamese text on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ================== CẤU HÌNH ==================
# load_dotenv()  # Nếu dùng .env cho token

# Facebook
FACEBOOK_PAGE_ID = "383742208160778"                 # ID Fanpage
FACEBOOK_ACCESS_TOKEN = "EAAJ1KgB05tMBQndtjVQPq4PIcvHZCxmXL2lZCtgrilO7VNbpuOWk6PrZATdAT7CVZCFKPshq1ZCZBQKSXNz0aclXqkhaO2lN9W4nd3fSrCwM9oFzLaq0tM6sov6eaIGH1WY4xIZCl2Byg4dJQ6eoZBZA9cqXYv51E08PXu96tdgbB8CZBSktwwEQr8FZC0Ip1P7SwGM4Exy"    # Page Access Token long-lived

# Google Sheets
CREDENTIALS_JSON_PATH = "service_account.json"      # Đường dẫn file JSON key
SPREADSHEET_ID = "1CGOPTz5futpJuenRrqoSaA7v8r7PNMNlsyS-Bl-gNQU"  # ID sheet
WORKSHEET_NAME = "Sheet4"                               # Tên tab

# Gemini AI
GEMINI_API_KEY = "AIzaSyApbTgbJrqcOhEZu5LgvxLBxSCaeKRDJk8"  # <-- Điền API Key của bạn vào đây

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
    
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    print(f"Đọc thành công {len(df)} dòng từ sheet '{WORKSHEET_NAME}'")
    return df, worksheet

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

# ================== HÀM GEMINI AI ==================
def generate_content_with_gemini(prompt_text):
    """Tạo nội dung caption bằng Gemini AI"""
    if not prompt_text:
        return ""
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-pro') # Đổi sang gemini-pro ổn định hơn
        
        # Prompt để AI viết hay hơn
        full_prompt = f"Viết một caption Facebook hấp dẫn, thu hút, có sử dụng emoji, dựa trên ý tưởng sau: {prompt_text}"
        
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"✗ Lỗi Gemini AI: {e}")
        # In danh sách model khả dụng để debug
        try:
            print("-> Danh sách model khả dụng:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"   - {m.name}")
        except: pass
        return prompt_text  # Fallback về caption gốc nếu lỗi

# ================== HÀM ĐĂNG BÀI ==================
def post_to_facebook(caption, image_path, hashtag):
    url = f"https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/photos"
    
    # Thêm hashtag vào caption nếu có
    if hashtag:
        caption = f"{caption}\n\n{hashtag}"
    
    # Kiểm tra xem image_path là URL hay đường dẫn file cục bộ
    if image_path.startswith("http://") or image_path.startswith("https://"):
        # URL công cộng - dùng phương pháp url parameter
        payload = {
            "access_token": FACEBOOK_ACCESS_TOKEN,
            "caption": caption,
            "url": image_path,
            "published": True
        }
        try:
            response = requests.post(url, data=payload)
            result = response.json()
            
            if "id" in result:
                print(f"✓ ĐĂNG THÀNH CÔNG!")
                print(f"  Caption: {caption[:100]}...")
                return True
            else:
                if "error" in result:
                    error_msg = result["error"].get("message", "Unknown error")
                    error_code = result["error"].get("code", "N/A")
                    print(f"✗ Lỗi từ Facebook (Code {error_code}): {error_msg}")
                else:
                    print(f"✗ Phản hồi không mong đợi: {result}")
                return False
        except Exception as e:
            print(f"✗ Lỗi khi gọi API: {e}")
            return False
    else:
        # Đường dẫn file cục bộ - upload ảnh từ file
        print(f"-> Đang upload ảnh từ máy tính: {image_path}")
        if not os.path.exists(image_path):
            print(f"✗ File ảnh không tìm thấy: {image_path}")
            return False
        
        try:
            with open(image_path, "rb") as img_file:
                files = {"source": img_file}
                payload = {
                    "access_token": FACEBOOK_ACCESS_TOKEN,
                    "caption": caption,
                    "published": True
                }
                
                response = requests.post(url, data=payload, files=files)
                result = response.json()
                
                if "id" in result:
                    print(f"✓ ĐĂNG THÀNH CÔNG! Post ID: {result['id']}")
                    print(f"  Caption: {caption[:100]}...")
                    return True
                else:
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        error_code = result["error"].get("code", "N/A")
                        print(f"✗ Lỗi từ Facebook (Code {error_code}): {error_msg}")
                    else:
                        print(f"✗ Phản hồi không mong đợi: {result}")
                    return False
        except Exception as e:
            print(f"✗ Lỗi khi upload ảnh: {e}")
            return False

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
        # Xóa dấu ngoặc kép nếu copy path từ Windows (Copy as path)
        image_url = str(row["ImagePath"]).strip().strip('"').strip("'")
        hashtag = str(row.get("Hashtag", "")).strip()
        
        if not caption or not image_url:
            print(f"Bỏ qua dòng {index + 2}: thiếu caption hoặc ảnh")
            continue
        
        print(f"\nXử lý bài: {caption[:50]}...")
        
        # Tạo nội dung bằng AI
        print("-> Đang gọi Gemini AI tạo nội dung...")
        ai_caption = generate_content_with_gemini(caption)
        print(f"-> Nội dung AI: {ai_caption[:50]}...")
        
        success = post_to_facebook(ai_caption, image_url, hashtag)
        
        if success:
            # Cập nhật trạng thái lại sheet
            if "Trạng thái" in df.columns:
                row_index = index + 2  # vì header ở dòng 1
                worksheet.update_cell(row_index, df.columns.get_loc("Trạng thái") + 1, "Done")
                print(f"-> Đã cập nhật trạng thái dòng {row_index} thành 'Done'")
        else:
            print("Đăng thất bại → tiếp tục bài sau")
        
        # Chờ giữa các bài (trừ bài cuối)
        if index < len(df) - 1:
            print(f"Chờ {DELAY_BETWEEN_POSTS // 60} phút...")
            time.sleep(DELAY_BETWEEN_POSTS)

if __name__ == "__main__":
    main()