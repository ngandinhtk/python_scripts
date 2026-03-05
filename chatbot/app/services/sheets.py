"""
Google Sheets Service
- Đọc dữ liệu từ 3 sheet: Khách hàng, Sản phẩm, FAQ
- Tự động sync vào Chroma vector DB để chatbot có thể tìm kiếm
- Cache dữ liệu trong bộ nhớ để tránh gọi API liên tục
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional
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
        if self._client:
            return self._client

        creds_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
        if not os.path.exists(creds_file):
            raise FileNotFoundError(
                f"Không tìm thấy file credentials: '{creds_file}'\n"
                "Xem hướng dẫn tại: docs/google_sheets_setup.md"
            )

        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
        self._client = gspread.authorize(creds)
        return self._client

    def _fetch_sheet(self, sheet_id: str) -> List[Dict]:
        """Đọc toàn bộ dữ liệu từ một Sheet (row đầu = header)."""
        client = self._get_client()
        sheet = client.open_by_key(sheet_id).sheet1
        rows = sheet.get_all_records()
        logger.info("sheets.fetched", sheet_id=sheet_id[:8], rows=len(rows))
        return rows

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
        Tìm khách hàng theo tên, email, hoặc số điện thoại.
        Tìm kiếm case-insensitive, partial match.
        """
        q = query.lower().strip()
        for customer in self.get_customers():
            for value in customer.values():
                if q in str(value).lower():
                    return customer
        return None

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
