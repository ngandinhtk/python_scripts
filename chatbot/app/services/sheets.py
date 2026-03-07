"""
Google Sheets Service
- Đọc dữ liệu từ 3 sheet: Khách hàng, Sản phẩm, FAQ
- Tự động sync vào Chroma vector DB để chatbot có thể tìm kiếm
- Cache dữ liệu trong bộ nhớ để tránh gọi API liên tục
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional, Any
import json
import os
import asyncio
import uuid
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.logging import StructuredLogger
from functools import partial


SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

logger = StructuredLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self._client: Optional[gspread.Client] = None
        self._cache: Dict[str, dict] = {}          # {sheet_id: {data, synced_at}}
        self._sync_task: Optional[asyncio.Task] = None

    def _get_client(self) -> gspread.Client:
        """Khởi tạo gspread client từ Service Account file."""
        if self._client:
            return self._client

        # Ưu tiên lấy credentials từ biến môi trường (cho Railway/Heroku)
        creds_json_str = settings.GOOGLE_CREDENTIALS_JSON
        if creds_json_str:
            try:
                creds_info = json.loads(creds_json_str)
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
                self._client = gspread.authorize(creds)
                logger.info("sheets.auth.env_variable")
                return self._client
            except json.JSONDecodeError:
                raise ValueError("GOOGLE_CREDENTIALS_JSON không phải là một JSON hợp lệ.")
            except Exception as e:
                raise ValueError(f"Lỗi khi xác thực từ biến môi trường: {e}")

        # Fallback: đọc từ file (cho local development)
        creds_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
        if not os.path.exists(creds_file):
            raise FileNotFoundError(
                f"Không tìm thấy file credentials: '{creds_file}' và biến môi trường GOOGLE_CREDENTIALS_JSON cũng không được thiết lập."
            )
        
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        self._client = gspread.authorize(creds)
        logger.info("sheets.auth.file")
        return self._client

    def _get_sheet(self, sheet_id: str, sheet_name: str = "") -> Optional[gspread.Worksheet]:
        """Lấy đối tượng worksheet từ sheet ID."""
        if not sheet_id:
            logger.warning("sheets.get_sheet.no_id", detail="Sheet ID is not provided.")
            return None
        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(sheet_id)
            if sheet_name:
                return spreadsheet.worksheet(sheet_name)
            else:
                return spreadsheet.sheet1
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error("sheets.get_sheet.not_found", sheet_id=sheet_id)
            return None
        except gspread.exceptions.WorksheetNotFound:
            logger.error("sheets.get_sheet.worksheet_not_found", sheet_id=sheet_id, sheet_name=sheet_name)
            return None
        except Exception as e:
            logger.error("sheets.get_sheet.error", sheet_id=sheet_id, error=str(e))
            return None

    def _fetch_sheet(self, sheet_id: str, sheet_name: str = "") -> List[Dict]:
        """Đọc toàn bộ dữ liệu từ một Sheet (row đầu = header)."""
        sheet = self._get_sheet(sheet_id, sheet_name)
        if not sheet:
            return []
        rows = sheet.get_all_records()
        logger.info("sheets.fetched", sheet_id=sheet_id[:8], rows=len(rows))
        return rows

    def append_row(self, sheet_id: str, row_values: List[Any], sheet_name: str = ""):
        """Ghi thêm một dòng vào cuối sheet."""
        sheet = self._get_sheet(sheet_id, sheet_name)
        if not sheet:
            logger.error("sheets.append_row.failed", sheet_id=sheet_id, detail="Sheet not found or accessible.")
            return
        try:
            sheet.append_row(row_values, value_input_option='USER_ENTERED')
            logger.info("sheets.row_appended", sheet_id=sheet_id[:8])
        except Exception as e:
            logger.error("sheets.append_row.error", sheet_id=sheet_id, error=str(e))

    def update_row(self, sheet_id: str, row_index: int, row_values: List[Any], sheet_name: str = ""):
        """Cập nhật một dòng cụ thể trong sheet."""
        sheet = self._get_sheet(sheet_id, sheet_name)
        if not sheet:
            logger.error("sheets.update_row.failed", sheet_id=sheet_id, detail="Sheet not found or accessible.")
            return
        try:
            # gspread row indices are 1-based. We update the whole row.
            sheet.update(f'A{row_index}', [row_values], value_input_option='USER_ENTERED')
            logger.info("sheets.row_updated", sheet_id=sheet_id[:8], row=row_index)
        except Exception as e:
            logger.error("sheets.update_row.error", sheet_id=sheet_id, row=row_index, error=str(e))

    def _is_cache_valid(self, sheet_id: str) -> bool:
        if sheet_id not in self._cache:
            return False
        age = datetime.now() - self._cache[sheet_id]["synced_at"]
        return age < timedelta(seconds=getattr(settings, 'SHEETS_SYNC_INTERVAL', 300))

    async def get_customers(self) -> List[Dict]:
        """Lấy danh sách khách hàng từ cache hoặc Sheet."""
        sid = getattr(settings, 'SHEET_CUSTOMERS_ID', None)
        sname = getattr(settings, 'SHEET_CUSTOMERS_NAME', "")
        if not sid:
            return []
        if not self._is_cache_valid(sid):
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_sheet, sid, sname)
            self._cache[sid] = {"data": data, "synced_at": datetime.now()}
        return self._cache[sid]["data"]

    async def get_products(self) -> List[Dict]:
        """Lấy danh sách sản phẩm/dịch vụ."""
        sid = getattr(settings, 'SHEET_PRODUCTS_ID', None)
        sname = getattr(settings, 'SHEET_PRODUCTS_NAME', "")
        if not sid:
            return []
        if not self._is_cache_valid(sid):
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_sheet, sid, sname)
            self._cache[sid] = {"data": data, "synced_at": datetime.now()}
        return self._cache[sid]["data"]

    async def get_faq(self) -> List[Dict]:
        """Lấy danh sách câu hỏi thường gặp."""
        sid = getattr(settings, 'SHEET_FAQ_ID', None)
        sname = getattr(settings, 'SHEET_FAQ_NAME', "")
        if not sid:
            return []
        if not self._is_cache_valid(sid):
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_sheet, sid, sname)
            self._cache[sid] = {"data": data, "synced_at": datetime.now()}
        return self._cache[sid]["data"]

    async def find_customer(self, query: str) -> Optional[Dict]:
        """
        `Tìm khách hàng theo tên, email, hoặc số điện thoại. 
        Tìm kiếm case-insensitive, partial match.`
        """
        q = query.lower().strip()
        customers = await self.get_customers()
        for customer in customers:
            for value in customer.values():
                if q in str(value).lower():
                    return customer
        return None

    async def log_chat_message(self, session_id: str, role: str, content: str):
        """Lưu tin nhắn chat vào Google Sheet."""
        sheet_id = settings.SHEET_LOGS_ID
        sheet_name = getattr(settings, 'SHEET_LOGS_NAME', "") # Nếu bạn muốn cấu hình tên sheet logs
        if not sheet_id:
            return  # Không làm gì nếu không có sheet logs ID

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, session_id, role, content]

        # Chạy tác vụ I/O trong thread pool để không block event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.append_row, sheet_id, row, sheet_name)

    async def add_customer(self, customer_data: Dict[str, Any]):
        """Thêm hoặc cập nhật thông tin khách hàng dựa trên SĐT hoặc Email."""
        sheet_id = settings.SHEET_CUSTOMERS_ID
        sheet_name = getattr(settings, 'SHEET_CUSTOMERS_NAME', "")
        sheet = self._get_sheet(sheet_id, sheet_name)
        if not sheet:
            raise ValueError("Không thể truy cập sheet khách hàng.")

        loop = asyncio.get_event_loop()

        # Lấy header để đảm bảo đúng thứ tự cột
        headers = await loop.run_in_executor(None, sheet.row_values, 1)
        if not headers:
            raise ValueError("Không thể đọc header từ sheet khách hàng.")

        # Xác định các trường định danh duy nhất (ưu tiên SĐT, sau đó đến Email)
        identifier_key = None
        if "Số điện thoại" in customer_data and customer_data.get("Số điện thoại"):
            identifier_key = "Số điện thoại"
        elif "Email" in customer_data and customer_data.get("Email"):
            identifier_key = "Email"
        
        found_cell = None
        if identifier_key:
            identifier_value = customer_data.get(identifier_key)
            try:
                # Tìm cột chứa trường định danh
                col_index = headers.index(identifier_key) + 1
                # Tìm cell chứa giá trị định danh (Sử dụng partial để truyền keyword arg 'in_column')
                find_func = partial(sheet.find, str(identifier_value), in_column=col_index)
                found_cell = await loop.run_in_executor(None, find_func)
            except ValueError:
                logger.warning("sheets.update.identifier_not_in_header", key=identifier_key)
            except gspread.exceptions.CellNotFound:
                found_cell = None # Không tìm thấy, sẽ tạo mới
            except Exception as e:
                logger.error("sheets.find_customer.error", error=str(e))
                found_cell = None

        if found_cell:
            # --- CẬP NHẬT KHÁCH HÀNG ---
            row_index = found_cell.row
            existing_data_list = await loop.run_in_executor(None, sheet.row_values, row_index)
            
            # Đảm bảo danh sách dữ liệu có độ dài bằng header (gspread bỏ qua các cell rỗng cuối dòng)
            if len(existing_data_list) < len(headers):
                existing_data_list.extend([""] * (len(headers) - len(existing_data_list)))
                
            existing_data = dict(zip(headers, existing_data_list))
            
            for key, value in customer_data.items():
                if key in existing_data and value: # Chỉ cập nhật nếu có giá trị mới
                    existing_data[key] = value
            
            updated_row_values = [existing_data.get(header, "") for header in headers]
            await loop.run_in_executor(None, self.update_row, sheet_id, row_index, updated_row_values, sheet_name)
            logger.info("sheets.customer_updated", identifier=f"{identifier_key}={identifier_value}")
        else:
            # --- THÊM MỚI KHÁCH HÀNG ---
            # Tự động tạo Mã KH nếu có cột "Mã KH" trong header nhưng chưa có dữ liệu
            if "Mã KH" in headers and not customer_data.get("Mã KH"):
                # Tạo mã KH: KH + 6 ký tự random (ví dụ: KH1A2B3C)
                customer_data["Mã KH"] = f"KH{uuid.uuid4().hex[:6].upper()}"
            
            # Tự động thêm Ngày tạo nếu có cột này trong header
            if "Ngày tạo" in headers and not customer_data.get("Ngày tạo"):
                customer_data["Ngày tạo"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            new_row_values = [customer_data.get(header, "") for header in headers]
            await loop.run_in_executor(None, self.append_row, sheet_id, new_row_values, sheet_name)
            logger.info("sheets.customer_added", data=customer_data)
            
            # Gửi tin nhắn Zalo chào mừng (nếu có SĐT)
            if "Số điện thoại" in customer_data and customer_data["Số điện thoại"]:
                from app.services.zalo import zalo_service
                # Gửi tin nhắn ZNS
                cust_name = customer_data.get("Họ và Tên") or customer_data.get("Tên") or "Quý khách"
                await zalo_service.send_zns(customer_data["Số điện thoại"], cust_name, customer_data.get("Mã KH", ""))

        # Vô hiệu hóa cache để lần đọc tiếp theo sẽ lấy dữ liệu mới
        if sheet_id in self._cache:
            del self._cache[sheet_id]
            logger.info("sheets.cache_invalidated", sheet_id=sheet_id[:8])

    # --- Chuyển dữ liệu thành văn bản để nhúng vào vector DB ---

    async def customers_to_texts(self) -> List[str]:
        texts = []
        customers = await self.get_customers()
        for c in customers:
            parts = [f"{k}: {v}" for k, v in c.items() if v]
            if parts:
                texts.append("Khách hàng — " + " | ".join(parts))
        return texts

    async def products_to_texts(self) -> List[str]:
        texts = []
        products = await self.get_products()
        for p in products:
            parts = [f"{k}: {v}" for k, v in p.items() if v]
            if parts:
                texts.append("Sản phẩm/Dịch vụ — " + " | ".join(parts))
        return texts

    async def faq_to_texts(self) -> List[str]:
        texts = []
        faq = await self.get_faq()
        for f in faq:
            # Tự động detect cột "question" / "answer" hoặc dùng cột đầu tiên
            keys = list(f.keys())
            q_key = next((k for k in keys if "câu hỏi" in k.lower() or "question" in k.lower()), keys[0] if keys else None)
            a_key = next((k for k in keys if "trả lời" in k.lower() or "answer" in k.lower()), keys[1] if len(keys) > 1 else None)

            if q_key and a_key and f.get(q_key) and f.get(a_key):
                texts.append(f"FAQ — Hỏi: {f[q_key]} | Trả lời: {f[a_key]}")
        return texts

    async def sync_to_vector_db(self):
        """Đồng bộ toàn bộ dữ liệu Google Sheets vào Chroma."""
        from app.services.retrieval import retrieval_service

        all_texts = []
        all_meta = []

        try:
            # Khách hàng
            c_texts = await self.customers_to_texts()
            all_texts += c_texts
            all_meta += [{"source": "customers"} for _ in c_texts]

            # Sản phẩm
            p_texts = await self.products_to_texts()
            all_texts += p_texts
            all_meta += [{"source": "products"} for _ in p_texts]

            # FAQ
            f_texts = await self.faq_to_texts()
            all_texts += f_texts
            all_meta += [{"source": "faq"} for _ in f_texts]

            if all_texts:
                await retrieval_service.add_documents(all_texts, all_meta)
                logger.info("sheets.synced", total=len(all_texts),
                            customers=len(c_texts), products=len(p_texts), faq=len(f_texts))
            else:
                logger.warning("sheets.empty", detail="Không có dữ liệu để sync — kiểm tra SHEET_*_ID trong .env")

        except FileNotFoundError as e:
            logger.warning("sheets.no_credentials", error=str(e))
        except Exception as e:
            logger.error("sheets.sync_error", error=str(e))

    async def start_auto_sync(self):
        """Vòng lặp tự động sync theo SHEETS_SYNC_INTERVAL."""
        logger.info("sheets.auto_sync_started", interval=getattr(settings, 'SHEETS_SYNC_INTERVAL', 300))
        while True:
            await self.sync_to_vector_db()
            await asyncio.sleep(getattr(settings, 'SHEETS_SYNC_INTERVAL', 300))

sheets_service = GoogleSheetsService()
