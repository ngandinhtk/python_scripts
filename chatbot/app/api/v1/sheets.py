"""Google Sheets management endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from app.services.sheets import sheets_service
from app.core.logging import StructuredLogger

router = APIRouter()
logger = StructuredLogger(__name__)


class NewCustomer(BaseModel):
    """Mô hình dữ liệu để tạo khách hàng mới."""
    Ten: Optional[str] = Field(None, alias="Họ và Tên", example="Trần Văn B")
    Ma_KH: Optional[str] = Field(None, alias="Mã KH", example="KH123456")
    Email: Optional[str] = Field(None, example="b.tran@example.com")
    So_dien_thoai: Optional[str] = Field(None, alias="Số điện thoại", example="0987654321")
    Dia_chi: Optional[str] = Field(None, alias="Địa chỉ", example="Đà Nẵng")
    Ghi_chu: Optional[str] = Field(None, alias="Ghi chú", example="Khách hàng tiềm năng")
    Ngay_tao: Optional[str] = Field(None, alias="Ngày tạo", example="2023-10-27 10:00:00")

    class Config:
        extra = 'allow'


@router.post("/customers")
async def add_customer(customer: NewCustomer, background_tasks: BackgroundTasks):
    """Thêm một khách hàng mới vào Google Sheet."""
    customer_data = customer.dict(by_alias=True)
    background_tasks.add_task(sheets_service.add_customer, customer_data)
    return {"message": "Yêu cầu thêm khách hàng đã được tiếp nhận.", "data": customer_data}


@router.get("/customers")
async def get_customers():
    """Get all customers."""
    try:
        customers = await sheets_service.get_customers()
        return {"customers": customers}
    except Exception as e:
        logger.error("sheets.customers_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
async def get_products():
    """Get all products."""
    try:
        products = await sheets_service.get_products()
        return {"products": products}
    except Exception as e:
        logger.error("sheets.products_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faq")
async def get_faq():
    """Get FAQ."""
    try:
        faq = await sheets_service.get_faq()
        return {"faq": faq}
    except Exception as e:
        logger.error("sheets.faq_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sheets/sync")
async def sync_sheets(background_tasks: BackgroundTasks):
    """Kích hoạt tác vụ nền để đồng bộ dữ liệu Google Sheets."""
    try:
        background_tasks.add_task(sheets_service.sync_to_vector_db)
        return {"message": "Yêu cầu đồng bộ đã được gửi và sẽ được xử lý trong nền."}
    except Exception as e:
        logger.error("sheets.sync_trigger_error", error=str(e))
        raise HTTPException(status_code=500, detail="Lỗi khi bắt đầu quá trình đồng bộ.")
