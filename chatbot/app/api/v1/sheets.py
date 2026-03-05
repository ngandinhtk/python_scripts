"""Google Sheets management endpoints."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.sheets import sheets_service
from app.core.logging import logger

router = APIRouter()


@router.get("/customers")
async def get_customers():
    """Get all customers."""
    try:
        customers = sheets_service.get_customers()
        return {"customers": customers}
    except Exception as e:
        logger.error("sheets.customers_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products")
async def get_products():
    """Get all products."""
    try:
        products = sheets_service.get_products()
        return {"products": products}
    except Exception as e:
        logger.error("sheets.products_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faq")
async def get_faq():
    """Get FAQ."""
    try:
        faq = sheets_service.get_faq()
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
