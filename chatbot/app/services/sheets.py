"""
Google Sheets Service
- Đọc dữ liệu từ 3 sheet: Khách hàng, Sản phẩm, FAQ
- Tự động sync vào Chroma vector DB để chatbot có thể tìm kiếm
- Cache dữ Ku trong bộ nhớ để tránh gọi API liên tục
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional, Any
import os
import asyncio
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.logging import logger


SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsService:
    def __init__(self):
        self._client: Optional[gspread.Client] = None
        self._cache: Dict[str, dict] = {}          # {sheet_id: {data, synced_at}}
        self._sync_task: Optional[asyncio.Task] = None

    def _get_client(self) -> gspread.Client:
        """Khởi tạo gspread client từ Service Account file."""
        """Khởi tạo gspread client từ biến môi trường hoặc file."""
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

    def _get_sheet(self, sheet_id: str) -> Optional[gspread.Worksheet]:
        """Lấy đối tượng worksheet từ sheet ID."""
        if not sheet_id:
            logger.warning("sheets.get_sheet.no_id", msg="Sheet ID is not provided.")
            return None
        try:
            client = self._get_client()
            sheet = client.open_by_key(sheet_id).sheet1
            return sheet
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error("sheets.get_sheet.not_found", sheet_id=sheet_id)
            return None
        except Exception as e:
            logger.error("sheets.get_sheet.error", sheet_id=sheet_id, error=str(e))
            return None

    def _fetch_sheet(self, sheet_id: str) -> List[Dict]:
        """Đọc toàn bộ dữ liệu từ một Sheet (row đầu = header)."""
        sheet = self._get_sheet(sheet_id)
        if not sheet:
            return []
        rows = sheet.get_all_records()
        logger.info("sheets.fetched", sheet_id=sheet_id[:8], rows=len(rows))
        return rows

    def append_row(self, sheet_id: str, row_values: List[Any]):
        """Ghi thêm một dòng vào cuối sheet."""
        sheet = self._get_sheet(sheet_id)
        if not sheet:
            logger.error("sheets.append_row.failed", sheet_id=sheet_id, msg="Sheet not found or accessible.")
            return
        try:
            sheet.append_row(row_values, value_input_option='USER_ENTERED')
            logger.info("sheets.row_appended", sheet_id=sheet_id[:8])
        except Exception as e:
            logger.error("sheets.append_row.error", sheet_id=sheet_id, error=str(e))

    def update_row(self, sheet_id: str, row_index: int, row_values: List[Any]):
        """Cập nhật một dòng cụ thể trong sheet."""
        sheet = self._get_sheet(sheet_id)
        if not sheet:
            logger.error("sheets.update_row.failed", sheet_id=sheet_id, msg="Sheet not found or accessible.")
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

    def get_customers(self) -> List[Dict]:
        """Lấy danh sách khách hàng từ cache hoặc Sheet."""
        sid = getattr(settings, 'SHEET_CUSTOMERS_ID', None)
        if not sid:
            return []
        if not self._is_cache_valid(sid):
            self._cache[sid] = {"data": self._fetch_sheet(sid), "synced_at": datetime.now()}
        return self._cache[sid]["data"]

    def get_products(self) -> List[Dict]:
        """Lấy danh sách sản phẩm/dịch vụ."""
        sid = getattr(settings, 'SHEET_PRODUCTS_ID', None)
        if not sid:
            return []
        if not self._is_cache_valid(sid):
            self._cache[sid] = {"data": self._fetch_sheet(sid), "synced_at": datetime.now()}
        return self._cache[sid]["data"]

    def get_faq(self) -> List[Dict]:
        """Lấy danh sách câu hỏi thường gặp."""
        sid = getattr(settings, 'SHEET_FAQ_ID', None)
        if not sid:
            return []
        if not self._is_cache_valid(sid):
            self._cache[sid] = {"data": self._fetch_sheet(sid), "synced_at": datetime.now()}
        return self._cache[sid]["data"]

    def find_customer(self, query: str) -> Optional[Dict]:
        """
        `Tìm khách hàng theo tên, email, hoặc số điện thoại. 
        Tìm kiếm case-insensitive, partial match.`
        """
        q = query.lower().strip()
        for customer in self.get_customers():
            for value in customer.values():
                if q in str(value).lower():
                    return customer
        return None

    async def log_chat_message(self, session_id: str, role: str, content: str):
        """Lưu tin nhắn chat vào Google Sheet."""
        sheet_id = settings.SHEET_LOGS_ID
        if not sheet_id:
            return  # Không làm gì nếu không có sheet logs ID

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, session_id, role, content]

        # Chạy tác vụ I/O trong thread pool để không block event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.append_row, sheet_id, row)

    async def add_customer(self, customer_data: Dict[str, Any]):
        """Thêm hoặc cập nhật thông tin khách hàng dựa trên SĐT hoặc Email."""
        sheet_id = settings.SHEET_CUSTOMERS_ID
        sheet = self._get_sheet(sheet_id)
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
                # Tìm cell chứa giá trị định danh
                found_cell = await loop.run_in_executor(None, sheet.find, str(identifier_value), in_column=col_index)
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
            existing_data = dict(zip(headers, existing_data_list))
            
            for key, value in customer_data.items():
                if key in existing_data and value: # Chỉ cập nhật nếu có giá trị mới
                    existing_data[key] = value
            
            updated_row_values = [existing_data.get(header, "") for header in headers]
            await loop.run_in_executor(None, self.update_row, sheet_id, row_index, updated_row_values)
            logger.info("sheets.customer_updated", identifier=f"{identifier_key}={identifier_value}")
        else:
            # --- THÊM MỚI KHÁCH HÀNG ---
            new_row_values = [customer_data.get(header, "") for header in headers]
            await loop.run_in_executor(None, self.append_row, sheet_id, new_row_values)
            logger.info("sheets.customer_added", data=customer_data)

        # Vô hiệu hóa cache để lần đọc tiếp theo sẽ lấy dữ liệu mới
        if sheet_id in self._cache:
            del self._cache[sheet_id]
            logger.info("sheets.cache_invalidated", sheet_id=sheet_id[:8])

    # --- Chuyển dữ liệu thành văn bản để nhúng vào vector DB ---

    def customers_to_texts(self) -> List[str]:
        texts = []
        for c in self.get_customers():
            parts = [f"{k}: {v}" for k, v in c.items() if v]
            if parts:
                texts.append("Khách hàng — " + " | ".join(parts))
        return texts

    def products_to_texts(self) -> List[str]:
        texts = []
        for p in self.get_products():
            parts = [f"{k}: {v}" for k, v in p.items() if v]
            if parts:
                texts.append("Sản phẩm/Dịch vụ — " + " | ".join(parts))
        return texts

    def faq_to_texts(self) -> List[str]:
        texts = []
        for f in self.get_faq():
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
            c_texts = self.customers_to_texts()
            all_texts += c_texts
            all_meta += [{"source": "customers"} for _ in c_texts]

            # Sản phẩm
            p_texts = self.products_to_texts()
            all_texts += p_texts
            all_meta += [{"source": "products"} for _ in p_texts]

            # FAQ
            f_texts = self.faq_to_texts()
            all_texts += f_texts
            all_meta += [{"source": "faq"} for _ in f_texts]

            if all_texts:
                await retrieval_service.add_documents(all_texts, all_meta)
                logger.info("sheets.synced", total=len(all_texts),
                            customers=len(c_texts), products=len(p_texts), faq=len(f_texts))
            else:
                logger.warning("sheets.empty", msg="Không có dữ liệu để sync — kiểm tra SHEET_*_ID trong .env")

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
