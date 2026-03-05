"""Các endpoint cho việc trò chuyện."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.memory import memory_service
from app.services.retrieval import retrieval_service
from app.services.llm import llm_service
from app.core.config import settings
from app.core.logging import logger
import uuid

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
async def chat(message: Message):
    """Xử lý tin nhắn trò chuyện bằng API DeepSeek."""
    session_id = message.session_id or str(uuid.uuid4())
    user_query = message.content

    try:
        # 1. Tìm kiếm ngữ cảnh liên quan từ vector database
        context_docs = await retrieval_service.search(query=user_query, n_results=3)

        # 2. Thêm tin nhắn của người dùng vào bộ nhớ
        await memory_service.add_message(session_id, "user", user_query)

        # 3. Lấy lịch sử cuộc trò chuyện
        history = await memory_service.get_history(session_id)

        # 4. Xây dựng prompt với ngữ cảnh (nếu có)
        system_prompt = settings.SYSTEM_PROMPT
        if context_docs:
            context_str = "\n\n".join(context_docs)
            # Cải tiến prompt để hướng dẫn LLM sử dụng ngữ cảnh hiệu quả hơn.
            # Prompt này có cấu trúc rõ ràng và đưa ra quy tắc cụ thể.
            system_prompt = (
                "Bạn là một trợ lý AI chuyên nghiệp, luôn trả lời bằng tiếng Việt một cách thân thiện.\n\n"
                "Để trả lời câu hỏi của người dùng, hãy tuân thủ nghiêm ngặt các quy tắc sau:\n"
                "1. **Ưu tiên tuyệt đối và chỉ sử dụng thông tin trong phần `[Ngữ cảnh]` được cung cấp.** Không được tự ý suy diễn hay thêm thông tin không có trong ngữ cảnh.\n"
                "2. Nếu thông tin trong `[Ngữ cảnh]` không đủ hoặc không liên quan để trả lời, hãy lịch sự thông báo rằng bạn không tìm thấy thông tin trong tài liệu của công ty. Sau đó, bạn có thể trả lời dựa trên kiến thức chung của mình nếu câu hỏi mang tính tổng quát.\n"
                "3. Trình bày câu trả lời một cách rõ ràng, mạch lạc.\n\n"
                "--- [Ngữ cảnh] ---\n"
                f"{context_str}\n"
                "--- [Hết Ngữ cảnh] ---"
            )

        # Nếu không có ngữ cảnh, chatbot sẽ hoạt động như một trợ lý thông thường
        # với prompt hệ thống mặc định.
        messages = [{"role": "system", "content": system_prompt}] + [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]

        # 5. Lấy phản hồi từ DeepSeek
        response_content = await llm_service.chat(messages)

        # 6. Thêm phản hồi của trợ lý vào bộ nhớ
        await memory_service.add_message(session_id, "assistant", response_content)

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
