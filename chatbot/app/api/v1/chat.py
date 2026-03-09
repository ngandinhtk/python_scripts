"""Các endpoint cho việc trò chuyện."""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.memory import memory_service
from app.services.retrieval import retrieval_service
from app.services.llm import llm_service
from app.services.sheets import sheets_service
from app.core.config import settings
from app.core.logging import StructuredLogger
import uuid
import re
import json
import asyncio

router = APIRouter()
logger = StructuredLogger(__name__)

# --- CONSTANTS: PROMPTS ---
EXTRACTION_INSTRUCTION = (
    "\n\n--- HƯỚNG DẪN TRÍCH XUẤT THÔNG TIN ---\n"
    "Nếu người dùng cung cấp thông tin cá nhân (Họ và Tên, Số điện thoại, Email, Địa chỉ) hoặc có những yêu cầu quan trọng, hãy làm theo các bước sau:\n"
    "1. **QUAN TRỌNG**: Nếu khách hàng chỉ cung cấp Tên mà CHƯA có Số điện thoại, hãy khéo léo hỏi xin Số điện thoại để tiện liên hệ/tư vấn.\n"
    "2. Hãy trả lời họ một cách tự nhiên. Luôn luôn xưng bằng EM\n"
    "3. Ở CUỐI CÙNG của câu trả lời, hãy thêm một khối JSON đặc biệt theo định dạng sau để hệ thống ghi nhận:\n"
    "   <<<CUSTOMER_DATA: {\"Họ và Tên\": \"...\", \"Số điện thoại\": \"...\", \"Email\": \"...\", \"Địa chỉ\": \"...\", \"Ghi chú\": \"...\"}>>>\n"
    "   - **Ghi chú**: Tóm tắt các thông tin, yêu cầu quan trọng của khách hàng từ cuộc trò chuyện (ví dụ: 'quan tâm căn 2PN', 'muốn xem nhà cuối tuần', 'hỏi về chính sách vay').\n"
    "   - Hệ thống sẽ tự động dùng 'Số điện thoại' hoặc 'Email' để tìm và CẬP NHẬT nếu khách hàng đã tồn tại, hoặc TẠO MỚI nếu chưa có.\n"
    "   - Chỉ điền các trường có thông tin, bỏ qua nếu không có. Tên trường phải chính xác như ví dụ. \n"
    "4. Nếu không có thông tin nào được cung cấp, hoặc nếu khách hàng từ chối cung cấp, hãy trả về một khối JSON rỗng: <<<CUSTOMER_DATA: {}>>>\n"
    "5. Lưu ý không được sử dụng ký tự đặt biệt trong phần trả lời.\n"
    
)

RAG_SYSTEM_PROMPT_TEMPLATE = (
    "Bạn là một trợ lý Bất Động Sản chuyên nghiệp. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng bằng ngôn ngữ của khách hàng.\n\n"
    "Hãy tuân thủ nghiêm ngặt các quy tắc sau:\n"
    "1. **QUAN TRỌNG NHẤT: PHẢI CÓ THÔNG TIN TÊN VÀ SỐ ĐIỆN THOẠI CỦA KHÁCH HÀNG SAU KHI HỎI.**\n"
    "2. **Chỉ sử dụng thông tin trong phần `[Ngữ cảnh]` được cung cấp.** Không được tự ý suy diễn hay thêm thông tin không có trong ngữ cảnh.\n"
    "3. Nếu thông tin trong `[Ngữ cảnh]` không đủ hoặc không liên quan, hãy lịch sự thông báo rằng bạn không tìm thấy thông tin. Sau đó, bạn có thể trả lời dựa trên kiến thức chung của mình nếu phù hợp.\n"
    "4. Trình bày câu trả lời một cách rõ ràng, mạch lạc, thân thiện.\n\n"
    "5. Dưới đây là phần `[Ngữ cảnh]` chứa thông tin liên quan được trích xuất từ cơ sở dữ liệu của chúng tôi. Hãy sử dụng nó một cách thông minh để trả lời câu hỏi của người dùng:\n"
    "6. Nếu có nhiều đoạn ngữ cảnh, hãy tổng hợp chúng một cách logic để đưa ra câu trả lời tốt nhất.\n"
    "7. Nếu có mâu thuẫn trong ngữ cảnh, hãy ưu tiên thông tin mới nhất hoặc có liên quan nhất.\n"
    "8. Xưng hô với khách hàng một cách thân thiện, LUÔN XƯNG LÀ EM VÀ Phải gọi 'anh' hoặc 'chị' tùy ngữ cảnh.\n"
    "--- [Ngữ cảnh] ---\n" 
    "{context_str}\n"
    "--- [Hết Ngữ cảnh] ---"
)
# --------------------------


class Message(BaseModel):
    """Mô hình tin nhắn trò chuyện."""
    content: str
    session_id: str = None


class ChatResponse(BaseModel):
    """Mô hình phản hồi trò chuyện."""
    session_id: str
    role: str
    content: str


@router.post("/chat", response_model=ChatResponse)
async def chat(message: Message, background_tasks: BackgroundTasks):
    """Xử lý tin nhắn trò chuyện bằng API DeepSeek."""
    session_id = message.session_id or str(uuid.uuid4())
    user_query = message.content

    try:
        # 1. Tìm kiếm ngữ cảnh liên quan từ vector database
        context_docs = await retrieval_service.search(query=user_query, n_results=3)

        # 2. Thêm tin nhắn của người dùng vào bộ nhớ (cả DB và Sheet)
        await memory_service.add_message(session_id, "user", user_query)
        background_tasks.add_task(sheets_service.log_chat_message, session_id, "user", user_query)

        # 3. Lấy lịch sử cuộc trò chuyện
        history = await memory_service.get_history(session_id)

        # 4. Xây dựng prompt với ngữ cảnh (nếu có)
        system_prompt = settings.SYSTEM_PROMPT
        if context_docs:
            context_str = "\n\n".join(context_docs)
            system_prompt = RAG_SYSTEM_PROMPT_TEMPLATE.format(context_str=context_str)
            
        # Luôn thêm hướng dẫn trích xuất vào cuối prompt hệ thống
        system_prompt += EXTRACTION_INSTRUCTION

        # Nếu không có ngữ cảnh, chatbot sẽ hoạt động như một trợ lý thông thường
        # với prompt hệ thống mặc định.
        messages = [{"role": "system", "content": system_prompt}] + [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]

        # 5. Lấy phản hồi từ DeepSeek
        response_content = await llm_service.chat(messages)
        
        # Xử lý tách JSON data nếu có
        # Regex tìm chuỗi nằm giữa <<<CUSTOMER_DATA: và >>>
        match = re.search(r'<<<CUSTOMER_DATA:\s*({.*?})\s*>>>', response_content, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                customer_data = json.loads(json_str)
                # Tự động lưu thông tin khách hàng vào Google Sheet trong nền
                background_tasks.add_task(sheets_service.add_customer, customer_data)

                # Xóa phần data khỏi nội dung hiển thị cho người dùng
                response_content = response_content.replace(match.group(0), "").strip()
            except json.JSONDecodeError:
                logger.error("chat.json_parse_error", data=json_str)

        # 6. Thêm phản hồi của trợ lý vào bộ nhớ (cả DB và Sheet)
        # Lưu ý: Chỉ lưu phần text đã làm sạch vào lịch sử
        await memory_service.add_message(session_id, "assistant", response_content)
        background_tasks.add_task(sheets_service.log_chat_message, session_id, "assistant", response_content)

        # Thêm độ trễ 3 giây trước khi gửi phản hồi
        # await asyncio.sleep(3)

        return ChatResponse(
            session_id=session_id,
            role="assistant",
            content=response_content
        )

    except ValueError as e:
        logger.error("chat.deepseek_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("chat.error", error=str(e))
        raise HTTPException(status_code=500, detail="Lỗi máy chủ nội bộ")


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Lấy lịch sử trò chuyện cho một phiên."""
    try:
        history = await memory_service.get_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        logger.error("history.error", error=str(e))
        raise HTTPException(status_code=500, detail="Không thể lấy lịch sử trò chuyện.")


@router.delete("/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(session_id: str):
    """Xóa lịch sử trò chuyện cho một phiên."""
    try:
        await memory_service.clear(session_id)
    except Exception as e:
        logger.error("history.delete.error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Lỗi khi xoá lịch sử trò chuyện.")


@router.get("/history")
async def list_sessions():
    """Lấy danh sách tất cả các phiên trò chuyện."""
    try:
        sessions = await memory_service.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error("history.list_sessions.error", error=str(e))
        raise HTTPException(status_code=500, detail="Không thể lấy danh sách phiên.")
