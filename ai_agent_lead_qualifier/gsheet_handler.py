# ai_agent_lead_qualifier/gsheet_handler.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from typing import Optional
from thefuzz import fuzz

# Cấu hình
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "credentials.json" # Đảm bảo file này nằm cùng thư mục
SHEET_NAME = "real_estate_auto_reply_50_rows" # Tên file Google Sheet của bạn

# Biến toàn cục để cache dữ liệu, tránh gọi API Google quá nhiều lần
cached_qa_data = []

def connect_gsheet():
    """Kết nối đến Google Sheet"""
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Warning: Không tìm thấy file {CREDENTIALS_FILE}. Bỏ qua chế độ GSheet.")
        return None
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
        client = gspread.authorize(creds)
        # Mở sheet đầu tiên
        sheet = client.open(SHEET_NAME).sheet1 
        return sheet
    except Exception as e:
        print(f"Lỗi kết nối GSheet: {e}")
        return None

def load_qa_data():
    """Tải dữ liệu từ Sheet vào RAM"""
    global cached_qa_data
    sheet = connect_gsheet()
    if sheet:
        try:
            # Lấy tất cả các dòng (bỏ qua dòng tiêu đề nếu cần)
            records = sheet.get_all_values()
            # Giả sử dòng 1 là tiêu đề, bắt đầu lấy từ dòng 2
            if len(records) > 1:
                cached_qa_data = records[1:] 
            print("Đã tải dữ liệu mẫu câu trả lời từ GSheet.")
        except Exception as e:
            print(f"Lỗi khi đọc dữ liệu GSheet: {e}")

def find_matching_response(user_message: str) -> Optional[str]:
    """
    Tìm câu trả lời dựa trên từ khóa trong tin nhắn người dùng bằng fuzzy matching.
    """
    global cached_qa_data

    # Nếu chưa có dữ liệu thì tải lần đầu
    if not cached_qa_data:
        load_qa_data()

    user_message_lower = user_message.lower()
    MATCH_THRESHOLD = 85  # Ngưỡng độ chính xác (từ 0 đến 100)

    for row in cached_qa_data:
        # Giả sử Cột A (index 0) là Keywords (cách nhau bởi dấu phẩy), Cột B (index 1) là Answer
        if len(row) < 2:
            continue

        keywords_str = row[0]
        answer = row[1]

        # Tách các từ khóa
        keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]

        # Kiểm tra xem có từ khóa nào đạt ngưỡng fuzzy match không
        for keyword in keywords:
            # fuzz.partial_ratio cho phép khớp một phần chuỗi, rất hiệu quả
            # Ví dụ: "giá chung cư" sẽ khớp tốt với "báo giá chung cư quận 2"
            score = fuzz.partial_ratio(keyword, user_message_lower)

            if score >= MATCH_THRESHOLD:
                print(f"-> Fuzzy match found! Keyword: '{keyword}', Message: '{user_message}', Score: {score}%")
                return answer

    return None
