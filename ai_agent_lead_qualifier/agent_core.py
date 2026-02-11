
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
from tools import get_all_tools, save_qualified_lead, get_saved_leads

# Import GSheet Handler
from gsheet_handler import find_matching_response

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


Mục tiêu chính và tiêu chí sàng lọc khách hàng tiềm năng (qualified lead):
Một khách hàng tiềm năng được coi là "qualified" (đủ điều kiện) khi bạn đã thu thập được TẤT CẢ các thông tin sau:
1.  **Tên đầy đủ** của khách hàng.
2.  **Thông tin liên hệ** (Số điện thoại HOẶC Email) của khách hàng.
3.  **Loại nhu cầu bất động sản** rõ ràng (Mua, Bán, Thuê, hoặc Cho thuê).
4.  **Ít nhất BA (3) chi tiết cụ thể** về nhu cầu bất động sản của họ. Ví dụ:
    *   Nếu là "Mua/Thuê": Khu vực (ví dụ: Quận 1), Ngân sách (ví dụ: 5 tỷ), Số phòng ngủ (ví dụ: 2 phòng), Diện tích (ví dụ: 70m2), Hướng (ví dụ: Đông), Tiện ích đặc biệt (ví dụ: gần trường học).
    *   Nếu là "Bán/Cho thuê": Loại BĐS, Địa chỉ/Khu vực, Giá mong muốn (ví dụ: 5 tỷ), Tình trạng pháp lý (ví dụ: sổ hồng), Đặc điểm nổi bật (ví dụ: nhà mặt tiền, có sân vườn).
5.  **Thời gian biểu giao dịch** của khách hàng (ví dụ: trong 3 tháng tới, không gấp).

Luồng tương tác chính:
-   Bắt đầu bằng lời chào. Lưu ý không tự giới thiệu bản thân là AIBot.
-   Không bao giờ từ chối trả lời câu hỏi của khách hàng, luôn duy trì thái độ tích cực và hỗ trợ. 
-   Không bao giờ hỏi trực tiếp "Bạn có muốn mua/bán/thuê không?".
-   Luôn tập trung vào việc thu thập các tiêu chí sàng lọc khách, không trả lời các câu hỏi ngoài lề.
-   Có thể sử dụng công cụ 'get_saved_leads' để kiểm tra xem khách hàng đã tồn tại trong hệ thống chưa, dựa trên thông tin liên hệ họ cung cấp.
-   Theo dõi luồng câu hỏi để thu thập từng tiêu chí sàng lọc được liệt kê ở trên.
-   **KHI VÀ CHỈ KHI** bạn đã thu thập đủ TẤT CẢ 5 tiêu chí trên, bạn PHẢI sử dụng công cụ 'save_qualified_lead' để lưu thông tin và kết thúc cuộc trò chuyện một cách chuyên nghiệp.
-   Nếu thiếu bất kỳ thông tin nào trong 5 tiêu chí trên, bạn phải hỏi rõ ràng để bổ sung.

Không đưa ra lời khuyên tài chính, pháp lý hoặc cam kết vượt quá vai trò của một trợ lý ảo.
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

# Hàm để xử lý chat message
async def process_chat_message(user_message: str, session_id: str = "default_session", current_chat_history: List[Dict[str, Any]] = None):
    # --- BƯỚC 1: KIỂM TRA CÂU TRẢ LỜI MẪU TỪ GSHEET ---
    # Mục đích: Tiết kiệm token và trả lời nhanh các câu hỏi FAQ
    canned_response = find_matching_response(user_message)
    
    if canned_response:
        print(f"-> Tìm thấy câu trả lời mẫu từ GSheet cho: '{user_message}'")
        # Cập nhật lịch sử chat thủ công (vì không qua AgentExecutor)
        updated_history = []
        if current_chat_history:
            updated_history = current_chat_history.copy()
        
        updated_history.append({"type": "human", "content": user_message})
        updated_history.append({"type": "ai", "content": canned_response})
        
        return {"response": canned_response, "chat_history": updated_history}

    # --- BƯỚC 2: NẾU KHÔNG CÓ MẪU, DÙNG GEMINI AI ---
    # Chuyển đổi lịch sử trò chuyện từ dict sang đối tượng BaseMessage của LangChain
    langchain_chat_history = []
    if current_chat_history:
        for msg_data in current_chat_history:
            if msg_data["type"] == "human":
                langchain_chat_history.append(HumanMessage(content=msg_data["content"]))
            elif msg_data["type"] == "ai":
                langchain_chat_history.append(AIMessage(content=msg_data["content"]))

    agent_executor = get_agent_executor_instance(langchain_chat_history)

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
