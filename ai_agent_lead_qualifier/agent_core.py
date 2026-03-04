
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.memory.buffer import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents.agent import AgentExecutor
from langchain_classic.agents.tool_calling_agent.base import create_tool_calling_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing import List, Dict, Any

# Import tools from tools.py
from tools import get_all_tools, save_qualified_lead, get_saved_leads, get_lead_by_facebook_id

# Import GSheet Handler
from gsheet_handler import find_matching_response
from canned_responses import find_canned_response

# 1. Load environment variables
load_dotenv()

# 2. Get API Key from environment
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")

# 3. Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=google_api_key)

# Định nghĩa System Prompt cho Agent
system_prompt_template = """
Bạn là AIBot, trợ lý ảo chuyên nghiệp của Bất Động Sản AI, có nhiệm vụ sàng lọc khách hàng tiềm năng.
Tính cách: Thân thiện, chuyên nghiệp, đáng tin cậy, kiên nhẫn và luôn tập trung vào việc thu thập thông tin cần thiết.

QUY TRÌNH LÀM VIỆC (QUAN TRỌNG):
1.  **ƯU TIÊN SỐ 1: LẤY THÔNG TIN LIÊN HỆ TRƯỚC.**
    -   Ngay sau lời chào, hãy khéo léo hỏi tên và số điện thoại/email của khách hàng để tiện xưng hô và hỗ trợ.
    -   **NGAY KHI** khách hàng cung cấp Tên và SĐT/Email, bạn PHẢI gọi công cụ `save_qualified_lead` ĐỂ LƯU NGAY LẬP TỨC (dù chưa biết nhu cầu cụ thể).
        -   Lúc này, tham số `lead_type` để là "Đang tư vấn", `details` để trống, và `facebook_id` lấy từ ngữ cảnh hệ thống.

2.  **KHAI THÁC NHU CẦU (Sau khi đã lưu liên hệ):**
    -   Sau khi đã lưu xong liên hệ, hãy tiếp tục hỏi về nhu cầu cụ thể để làm rõ hồ sơ khách hàng.
    -   Các thông tin cần thu thập thêm:
        *   **Loại nhu cầu**: Mua, Bán, Thuê, hoặc Cho thuê.
        *   **Chi tiết nhu cầu (Cần ít nhất 3 ý)**:
    *   Nếu là "Mua/Thuê": Khu vực (ví dụ: Quận 1), Ngân sách (ví dụ: 5 tỷ), Số phòng ngủ (ví dụ: 2 phòng), Diện tích (ví dụ: 70m2), Hướng (ví dụ: Đông), Tiện ích đặc biệt (ví dụ: gần trường học).
    *   Nếu là "Bán/Cho thuê": Loại BĐS, Địa chỉ/Khu vực, Giá mong muốn (ví dụ: 5 tỷ), Tình trạng pháp lý (ví dụ: sổ hồng), Đặc điểm nổi bật (ví dụ: nhà mặt tiền, có sân vườn).
        *   **Thời gian biểu giao dịch**: (ví dụ: trong 3 tháng tới, không gấp).

3.  **CẬP NHẬT THÔNG TIN (Tùy chọn):**
    -   Nếu sau quá trình hỏi han, bạn thu thập đủ các chi tiết trên, bạn có thể gọi lại `save_qualified_lead` một lần nữa để hệ thống ghi nhận bản ghi đầy đủ hơn.

Luồng tương tác chính:
-   Bắt đầu bằng lời chào. Lưu ý không tự giới thiệu bản thân là AIBot.
-   Không bao giờ từ chối trả lời câu hỏi của khách hàng, luôn duy trì thái độ tích cực và hỗ trợ. 
-   Không bao giờ hỏi trực tiếp "Bạn có muốn mua/bán/thuê không?".
-   Luôn tập trung vào việc thu thập thông tin liên hệ TRƯỚC, sau đó mới đến các tiêu chí sàng lọc khác.
-   Có thể sử dụng công cụ 'get_saved_leads' để kiểm tra xem khách hàng đã tồn tại trong hệ thống chưa, dựa trên thông tin liên hệ họ cung cấp.

Không đưa ra lời khuyên tài chính, pháp lý hoặc cam kết vượt quá vai trò của một trợ lý ảo.

{user_context}
"""

# 4. Get all tools
tools = get_all_tools()

# 5. Create the Prompt Template for the Agent
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# 6. Function to get an AgentExecutor instance
def get_agent_executor_instance(current_chat_history: List[BaseMessage]):
    # Khởi tạo ConversationBufferMemory và nạp lịch sử trò chuyện từ client
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )
    # Nạp lịch sử trò chuyện đã được client gửi lên
    memory.chat_memory.add_messages(current_chat_history)

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True, # Đặt True để xem suy nghĩ của agent trong console server
        handle_parsing_errors=True,
    )
    return agent_executor


def _has_chat_history(current_chat_history: List[Dict[str, Any]] = None) -> bool:
    if not current_chat_history:
        return False
    return len(current_chat_history) > 0

# Hàm để xử lý chat message
async def process_chat_message(user_message: str, session_id: str = "default_session", current_chat_history: List[Dict[str, Any]] = None):
    # --- BƯỚC 1: KIỂM TRA KỊCH BẢN LOCAL ---
    # Mục đích: trả lời nhanh với chi phí gần như 0, không phụ thuộc dịch vụ ngoài.
    # --- BƯỚC 1: ƯU TIÊN KIỂM TRA KỊCH BẢN TRẢ LỜI NHANH TỪ `canned_responses.json` ---
    # Mục đích: Trả lời ngay lập tức các câu hỏi phổ biến từ file JSON cục bộ để tiết kiệm chi phí
    # và tăng tốc độ phản hồi, trước khi gọi đến GSheet hay Gemini API.
    canned_response = find_canned_response(user_message) if not _has_chat_history(current_chat_history) else None

    if canned_response:
        print(f"-> Tim thay cau tra loi san (local) cho: '{user_message}'")
        print(f"-> Tìm thấy câu trả lời có sẵn từ `canned_responses.json` cho: '{user_message}'")
        updated_history = []
        if current_chat_history:
            updated_history = current_chat_history.copy()

        updated_history.append({"type": "human", "content": user_message})
        updated_history.append({"type": "ai", "content": canned_response})

        return {"response": canned_response, "chat_history": updated_history}

    # --- BƯỚC 2: KIỂM TRA CÂU TRẢ LỜI MẪU TỪ GSHEET ---
    # Mục đích: Tiết kiệm token và trả lời nhanh các câu hỏi FAQ
    # --- BƯỚC 2: KIỂM TRA CÂU TRẢ LỜI MẪU TỪ GOOGLE SHEET ---
    # Nếu không có trong file local, kiểm tra GSheet cho các câu hỏi FAQ.
    canned_response = find_matching_response(user_message)
    
    if canned_response:
        print(f"-> Tìm thấy câu trả lời mẫu từ GSheet cho: '{user_message}'")
        print(f"-> Tìm thấy câu trả lời mẫu từ Google Sheet cho: '{user_message}'")
        # Cập nhật lịch sử chat thủ công (vì không qua AgentExecutor)
        updated_history = []
        if current_chat_history:
            updated_history = current_chat_history.copy()
        
        updated_history.append({"type": "human", "content": user_message})
        updated_history.append({"type": "ai", "content": canned_response})
        
        return {"response": canned_response, "chat_history": updated_history}

    # --- BƯỚC 3: NẾU KHÔNG CÓ MẪU, DÙNG GEMINI AI ---
    # --- BƯỚC 3: NẾU KHÔNG CÓ CÂU TRẢ LỜI SẴN, SỬ DỤNG GEMINI AI ---
    # Đây là bước cuối cùng, chỉ được thực hiện khi không tìm thấy câu trả lời nào trong các kịch bản có sẵn.
    # Chuyển đổi lịch sử trò chuyện từ dict sang đối tượng BaseMessage của LangChain
    
    # --- NHẬN DIỆN KHÁCH HÀNG CŨ ---
    user_context = f"LƯU Ý KỸ THUẬT: ID phiên làm việc hiện tại (facebook_id) là: '{session_id}'. Khi gọi tool `save_qualified_lead`, BẮT BUỘC phải truyền giá trị này vào trường `facebook_id`."
    
    existing_lead = get_lead_by_facebook_id(session_id)
    if existing_lead:
        print(f"-> Phát hiện khách hàng cũ: {existing_lead['name']}")
        user_context += f"\n\nTHÔNG TIN KHÁCH HÀNG CŨ (Đã từng chat):" \
                        f"\n- Tên: {existing_lead['name']}" \
                        f"\n- SĐT/Email: {existing_lead['phone_or_email']}" \
                        f"\n- Nhu cầu cũ: {existing_lead['lead_type']}" \
                        f"\n- Chi tiết cũ: {existing_lead['details']}" \
                        f"\n\nHÃY CHÀO MỪNG HỌ QUAY LẠI bằng tên riêng. Bạn KHÔNG CẦN hỏi lại Tên và SĐT nữa trừ khi họ muốn thay đổi. Hãy hỏi thăm về nhu cầu cũ hoặc nhu cầu mới."
    else:
        user_context += "\n\nĐây là khách hàng mới. Hãy làm theo quy trình chuẩn: Hỏi Tên và SĐT trước tiên."

    # Cập nhật System Prompt với ngữ cảnh người dùng
    langchain_chat_history = []
    if current_chat_history:
        for msg_data in current_chat_history:
            if msg_data["type"] == "human":
                langchain_chat_history.append(HumanMessage(content=msg_data["content"]))
            elif msg_data["type"] == "ai":
                langchain_chat_history.append(AIMessage(content=msg_data["content"]))

    # Tạo prompt mới với user_context đã được điền
    final_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt_template.format(user_context=user_context)),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent_executor = get_agent_executor_instance(langchain_chat_history)
    agent_executor.agent.runnable = create_tool_calling_agent(llm, tools, final_prompt) # Cập nhật prompt cho agent
    
    try:
        response = await agent_executor.ainvoke({"input": user_message})
        # Lấy lịch sử trò chuyện đã được agent_executor cập nhật
        updated_langchain_chat_history = agent_executor.memory.chat_memory.messages
        
        # Chuyển đổi lại lịch sử sang định dạng dict để gửi về client
        updated_chat_history_for_client = []
        for msg in updated_langchain_chat_history:
            if isinstance(msg, HumanMessage):
                updated_chat_history_for_client.append({"type": "human", "content": msg.content})
            elif isinstance(msg, AIMessage):
                updated_chat_history_for_client.append({"type": "ai", "content": msg.content})

        return {"response": response["output"], "chat_history": updated_chat_history_for_client}
    except Exception as e:
        # Trả về lịch sử cũ nếu có lỗi để không bị mất dữ liệu phía client
        return {"response": f"AIBot gặp lỗi: {e}", "chat_history": current_chat_history if current_chat_history else []}
