# ai_agent_lead_qualifier/tools.py

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.tools.convert import tool
from typing import Dict, Any, List
import sqlite3
import json

# Import GSheet Handler for post-save response
from gsheet_handler import find_matching_response

# Khởi tạo hoặc kết nối đến cơ sở dữ liệu SQLite
DATABASE_NAME = "leads.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone_or_email TEXT NOT NULL,
            lead_type TEXT NOT NULL,
            details JSON,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Gọi hàm khởi tạo DB khi module được load
init_db()

# Định nghĩa Input Schema cho công cụ
class SaveLeadInput(BaseModel):
    name: str = Field(description="Tên đầy đủ của khách hàng tiềm năng.")
    phone_or_email: str = Field(description="Số điện thoại hoặc địa chỉ email của khách hàng tiềm năng.")
    lead_type: str = Field(description="Loại nhu cầu bất động sản (Mua, Bán, Thuê, Cho thuê).")
    details: Dict[str, Any] = Field(description="Các chi tiết bổ sung về nhu cầu bất động sản của khách hàng (ví dụ: khu vực, ngân sách, số phòng ngủ, v.v.).")

def save_lead_to_db(name: str, phone_or_email: str, lead_type: str, details: Dict[str, Any]) -> str:
    """
    Lưu thông tin chi tiết của một khách hàng tiềm năng đã được sàng lọc vào hệ thống.
    Công cụ này được gọi khi tất cả các thông tin cần thiết về khách hàng (tên, SĐT/email, loại nhu cầu, và chi tiết nhu cầu) đã được thu thập.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (name, phone_or_email, lead_type, details)
            VALUES (?, ?, ?, ?)
        """, (name, phone_or_email, lead_type, json.dumps(details))) # Chuyển dict details thành chuỗi JSON
        conn.commit()
        lead_id = cursor.lastrowid
        conn.close()

        print(f"\n--- Qualified Lead Saved to DB ---")
        print(f"Lead ID: {lead_id}")
        print(f"Name: {name}")
        print(f"Contact: {phone_or_email}")
        print(f"Type: {lead_type}")
        print(f"Details: {details}")
        print(f"--------------------------------\n")
        
        # Sau khi lưu lead, kiểm tra GSheet để lấy câu trả lời xác nhận
        # Sử dụng một từ khóa đặc biệt để tìm câu trả lời trong GSheet
        gsheet_confirmation_response = find_matching_response("lead_saved_confirmation")
        if gsheet_confirmation_response:
            return gsheet_confirmation_response
        else:
            return f"Thông tin khách hàng tiềm năng '{name}' đã được lưu vào cơ sở dữ liệu thành công với ID: {lead_id}. Mã lead: {lead_id}."
    except Exception as e:
        print(f"Lỗi khi lưu lead vào CSDL: {e}")
        return f"Đã xảy ra lỗi khi lưu thông tin khách hàng tiềm năng '{name}'. Vui lòng thử lại sau."

@tool(args_schema=SaveLeadInput)
def save_qualified_lead(name: str, phone_or_email: str, lead_type: str, details: Dict[str, Any]) -> str:
    """
    Lưu thông tin chi tiết của một khách hàng tiềm năng đã được sàng lọc vào hệ thống.
    Công cụ này được gọi khi tất cả các thông tin cần thiết về khách hàng (tên, SĐT/email, loại nhu cầu, và chi tiết nhu cầu) đã được thu thập.
    """
    return save_lead_to_db(name, phone_or_email, lead_type, details)

# Thêm một công cụ để xem các lead đã lưu (chỉ để kiểm tra)
class GetLeadsInput(BaseModel):
    limit: int = Field(default=10, description="Số lượng lead muốn lấy, mặc định là 10.")

def fetch_leads_from_db(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các khách hàng tiềm năng đã được lưu trữ trong hệ thống.
    Có thể giới hạn số lượng lead trả về.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone_or_email, lead_type, details, timestamp FROM leads ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    leads_list = []
    for row in rows:
        lead_dict = {
            "id": row[0],
            "name": row[1],
            "phone_or_email": row[2],
            "lead_type": row[3],
            "details": json.loads(row[4]), # Chuyển lại từ chuỗi JSON sang dict
            "timestamp": row[5]
        }
        leads_list.append(lead_dict)
    return leads_list

@tool(args_schema=GetLeadsInput)
def get_saved_leads(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Lấy danh sách các khách hàng tiềm năng đã được lưu trữ trong hệ thống.
    Có thể giới hạn số lượng lead trả về.
    """
    return fetch_leads_from_db(limit)

# Tập hợp tất cả các công cụ lại
def get_all_tools():
    return [
        save_qualified_lead,
        get_saved_leads, # Thêm công cụ mới vào đây
    ]
