
from fastapi import FastAPI, HTTPException, Request, Query
from pydantic import BaseModel
import uvicorn
from typing import List, Dict, Any, Optional
import os
import httpx
import json

# Import the agent processing function and tools
from agent_core import process_chat_message
from tools import fetch_leads_from_db

app = FastAPI(title="Real Estate Lead Qualifier AIBot API")

# --- Cấu hình Facebook ---
# Trong thực tế, hãy để các biến này trong file .env
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "YOUR_PAGE_ACCESS_TOKEN")
FB_VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "YOUR_VERIFY_TOKEN")

# --- Bộ nhớ tạm cho Facebook Users (In-memory) ---
# Vì Facebook không gửi lịch sử chat, server phải tự lưu.
# Key: Facebook User ID (PSID), Value: List[Dict] (chat history)
facebook_chat_histories: Dict[str, List[Dict[str, Any]]] = {}

class Message(BaseModel):
    type: str # "human" or "ai"
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"
    chat_history: List[Message] = [] # Lịch sử trò chuyện từ client

class ChatResponse(BaseModel):
    response: str
    chat_history: List[Message] # Lịch sử trò chuyện đã cập nhật để gửi về client

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint để tương tác với AIBot.
    Gửi tin nhắn của người dùng và nhận lại phản hồi từ AIBot, cùng với lịch sử trò chuyện đã cập nhật.
    """
    try:
        # Chuyển đổi ChatHistory từ Pydantic models sang định dạng List[Dict[str, Any]]
        # (do process_chat_message đang mong đợi định dạng này)
        current_chat_history_for_agent = [{"type": msg.type, "content": msg.content} for msg in request.chat_history]

        result = await process_chat_message(
            user_message=request.message,
            session_id=request.session_id,
            current_chat_history=current_chat_history_for_agent
        )
        
        # Chuyển đổi lại lịch sử từ Dict sang Pydantic Message models
        response_chat_history = [Message(type=msg_data["type"], content=msg_data["content"]) for msg_data in result["chat_history"]]

        return ChatResponse(response=result["response"], chat_history=response_chat_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leads")
async def get_leads_endpoint(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Endpoint để lấy danh sách các lead đã được lưu.
    """
    try:
        leads = fetch_leads_from_db(limit)
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Facebook Webhook Endpoints ---

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge")
):
    """
    Endpoint để Facebook xác thực Webhook của bạn.
    """
    if mode == "subscribe" and token == FB_VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def facebook_webhook_handler(request: Request):
    """
    Endpoint nhận sự kiện từ Facebook (tin nhắn người dùng).
    """
    body = await request.json()
    
    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message = messaging_event.get("message", {})
                message_text = message.get("text")

                if sender_id and message_text:
                    # 1. Lấy lịch sử chat cũ của user này (nếu có)
                    current_history = facebook_chat_histories.get(sender_id, [])

                    # 2. Gọi AI Agent để xử lý
                    # Lưu ý: process_chat_message là hàm async
                    result = await process_chat_message(
                        user_message=message_text,
                        session_id=sender_id,
                        current_chat_history=current_history
                    )

                    ai_response_text = result["response"]
                    updated_history = result["chat_history"]

                    # 3. Cập nhật lại lịch sử chat vào bộ nhớ server
                    facebook_chat_histories[sender_id] = updated_history

                    # 4. Gửi phản hồi lại cho Facebook User
                    await send_facebook_message(sender_id, ai_response_text)

        return {"status": "ok"}
    
    raise HTTPException(status_code=404, detail="Not a page event")

async def send_facebook_message(recipient_id: str, message_text: str):
    """
    Gửi tin nhắn trả lời qua Facebook Graph API.
    """
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={FB_PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn Facebook: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
