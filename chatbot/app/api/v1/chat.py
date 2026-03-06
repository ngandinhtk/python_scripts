"""Các endpoint cho việc trò chuyện."""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.memory import memory_service
from app.services.retrieval import retrieval_service
from app.services.llm import llm_service
from app.services.sheets import sheets_service
from app.core.config import settings
from app.core.logging import logger
import uuid
import re
import json

router = APIRouter()


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

        # Prompt hướng dẫn trích xuất thông tin
        extraction_instruction = (
            "\n\n--- HƯỚNG DẪN TRÍCH XUẤT THÔNG TIN ---\n"
            "Nếu người dùng cung cấp thông tin cá nhân (Tên, Số điện thoại, Email, Địa chỉ) để liên hệ, mua hàng hoặc CẬP NHẬT thông tin:\n"
            "1. Hãy trả lời họ một cách tự nhiên.\n"
            "2. Ở CUỐI CÙNG của câu trả lời, hãy thêm một khối JSON đặc biệt theo định dạng sau để hệ thống ghi nhận:\n"
            "   <<<CUSTOMER_DATA: {\"Tên\": \"...\", \"Số điện thoại\": \"...\", \"Email\": \"...\", \"Địa chỉ\": \"...\"}>>>\n"
            "   - Hệ thống sẽ tự động dùng 'Số điện thoại' hoặc 'Email' để tìm và CẬP NHẬT nếu khách hàng đã tồn tại, hoặc TẠO MỚI nếu chưa có.\n"
            "   - Chỉ điền các trường có thông tin, bỏ qua nếu không có. Tên trường phải chính xác như ví dụ."
        )

        # 4. Xây dựng prompt với ngữ cảnh (nếu có)
        system_prompt = settings.SYSTEM_PROMPT
        if context_docs:
            context_str = "\n\n".join(context_docs)
            system_prompt = (
                "Bạn là một trợ lý Bất Động Sản chuyên nghiệp. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng bằng ngôn ngữ của khách hàng.\n\n"
                "Hãy tuân thủ nghiêm ngặt các quy tắc sau:\n"
                "1. **QUAN TRỌNG NHẤT: Toàn bộ câu trả lời của bạn PHẢI được viết bằng tiếng Việt.**\n"
                "2. **Chỉ sử dụng thông tin trong phần `[Ngữ cảnh]` được cung cấp.** Không được tự ý suy diễn hay thêm thông tin không có trong ngữ cảnh.\n"
                "3. Nếu thông tin trong `[Ngữ cảnh]` không đủ hoặc không liên quan, hãy lịch sự thông báo rằng bạn không tìm thấy thông tin. Sau đó, bạn có thể trả lời dựa trên kiến thức chung của mình nếu phù hợp.\n"
                "4. Trình bày câu trả lời một cách rõ ràng, mạch lạc, thân thiện.\n\n"
                "5. Dưới đây là phần `[Ngữ cảnh]` chứa thông tin liên quan được trích xuất từ cơ sở dữ liệu của chúng tôi. Hãy sử dụng nó một cách thông minh để trả lời câu hỏi của người dùng:\n"
                "--- [Ngữ cảnh] ---\n"
                f"{context_str}\n"
                "--- [Hết Ngữ cảnh] ---"
            )
        # Luôn thêm hướng dẫn trích xuất vào cuối prompt hệ thống
        system_prompt += extraction_instruction

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

                # Thêm một ghi chú nhỏ vào cuối câu trả lời để người dùng biết
                response_content += "\n\n*(Chúng tôi đã ghi nhận thông tin của bạn để tiện liên hệ lại.)*"
            except json.JSONDecodeError:
                logger.error("chat.json_parse_error", data=json_str)

        # 6. Thêm phản hồi của trợ lý vào bộ nhớ (cả DB và Sheet)
        # Lưu ý: Chỉ lưu phần text đã làm sạch vào lịch sử
        await memory_service.add_message(session_id, "assistant", response_content)
        background_tasks.add_task(sheets_service.log_chat_message, session_id, "assistant", response_content)

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
