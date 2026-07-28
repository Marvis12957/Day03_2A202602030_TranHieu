"""
🖥️ STREAMLIT DEMO GUI (Giao diện Web cho Bài Lab 3)
Chạy bằng lệnh: python3 -m streamlit run src/gui.py
"""

import streamlit as st
import time
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đã sửa thành providers thay vì multi_provider
from providers import get_llm_provider 
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS

# --- THIẾT LẬP TRANG ---
st.set_page_config(page_title="Demo Lab 3: Chatbot vs ReAct Agent", page_icon="🏥", layout="wide")
st.title("🏥 Trợ Lý Y Tế Ảo - VinUni Lab 3")

# Khởi tạo LLM Provider
@st.cache_resource
def load_llm():
    return get_llm_provider()

provider = load_llm()

# --- SIDEBAR CẤU HÌNH ---
with st.sidebar:
    st.header("⚙️ Cấu hình Hệ thống")
    mode = st.radio("Chọn cấp độ AI:", 
                    ("🤖 Cấp 2: Baseline Chatbot", "🧠 Cấp 3: ReAct Agent"),
                    help="Cấp 2 chỉ dùng kiến thức tĩnh. Cấp 3 biết suy nghĩ và dùng Tools.")
    
    st.markdown("---")
    st.subheader("💡 Câu hỏi test nhanh:")
    sample_queries = [
        "Khám khoa Tim mạch thường khám những gì?",
        "Tôi hay bị đau đầu, chóng mặt. Tôi nên khám khoa nào?",
        "Sáng thứ 5 khoa Tim mạch còn bác sĩ nào rảnh không?",
        "Đặt lịch cho tôi tên Trần Văn Hiếu khám Tim mạch với BS Nguyễn Văn A vào sáng thứ 5 (08:30) nhé."
    ]
    selected_sample = st.selectbox("Chọn câu hỏi bẫy:", sample_queries)
    if st.button("Điền vào khung chat"):
        st.session_state.demo_input = selected_sample

# Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Tôi có thể giúp gì cho bạn hôm nay?", "type": "final"}]

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖" if "Chatbot" in mode else "🧠"):
            if msg.get("type") == "final":
                st.markdown(msg["content"])
            elif msg.get("type") == "thought":
                with st.expander("Bấm để xem quá trình AI suy nghĩ (ReAct Loop)"):
                    st.code(msg["content"], language="text")

# --- HÀM XỬ LÝ REACT LOOP CHO GIAO DIỆN ---
def parse_action(llm_response: str):
    action_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", llm_response)
    if action_match:
        tool_name = action_match.group(1).strip()
        params_str = action_match.group(2)
        raw_params = [p.strip().strip("'").strip('"') for p in params_str.split(',') if p.strip()]
        return tool_name, raw_params
    return None, []

def execute_tool(tool_name: str, *args):
    if tool_name not in AVAILABLE_TOOLS:
        return f"LỖI: Tool '{tool_name}' không tồn tại."
    try:
        return str(AVAILABLE_TOOLS[tool_name](*args))
    except Exception as e:
        return f"LỖI KHI CHẠY TOOL: {str(e)}"

# --- KHUNG NHẬP CHAT ---
user_input = st.chat_input("Nhập câu hỏi của bạn tại đây...")

# Nếu người dùng bấm nút "Điền vào khung chat" từ sidebar
if "demo_input" in st.session_state and st.session_state.demo_input:
    user_input = st.session_state.demo_input
    del st.session_state.demo_input

if user_input:
    # 1. In câu hỏi của user
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_input)

    # 2. Xử lý câu trả lời
    with st.chat_message("assistant", avatar="🤖" if "Chatbot" in mode else "🧠"):
        
        # PHÂN NHÁNH: BASELINE CHATBOT
        if "Cấp 2" in mode:
            with st.spinner("Đang trả lời dựa trên kiến thức tĩnh..."):
                response = provider.generate(user_input, system_prompt=CHATBOT_BASELINE_PROMPT)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response, "type": "final"})
                
        # PHÂN NHÁNH: REACT AGENT
        else:
            conversation_history = f"User: {user_input}\n"
            step_logs = "" # Lưu log để nhét vào expander
            final_answer = ""
            
            # Giao diện hiển thị loading đẹp mắt
            status_container = st.status("🧠 Agent đang suy luận...", expanded=True)
            
            for step in range(1, MAX_ITERATIONS + 1):
                status_container.update(label=f"🧠 Agent đang suy luận (Bước {step}/{MAX_ITERATIONS})...")
                
                # Gọi LLM
                llm_response = provider.generate(prompt=conversation_history, system_prompt=REACT_SYSTEM_PROMPT)
                conversation_history += f"{llm_response}\n"
                step_logs += f"\n--- VÒNG LẶP {step} ---\n{llm_response}\n"
                
                # Kiểm tra Final Answer
                if "Final Answer:" in llm_response:
                    final_answer = llm_response.split("Final Answer:")[-1].strip()
                    status_container.update(label="✅ Đã tìm ra câu trả lời!", state="complete", expanded=False)
                    break
                    
                # Trích xuất Action
                tool_name, tool_params = parse_action(llm_response)
                if tool_name:
                    status_container.write(f"🛠️ **Gọi tool:** `{tool_name}({', '.join(tool_params)})`")
                    obs = execute_tool(tool_name, *tool_params)
                    status_container.write(f"👁️ **Kết quả:** {obs}")
                    
                    conversation_history += f"Observation: {obs}\n"
                    step_logs += f"Observation: {obs}\n"
                    time.sleep(1)
                else:
                    warning = "LỖI HỆ THỐNG: LLM không tuân thủ định dạng. Ép buộc dừng."
                    final_answer = "Xin lỗi, tôi gặp sự cố trong quá trình tư duy (Sai định dạng ReAct)."
                    status_container.update(label="❌ Lỗi suy luận", state="error", expanded=True)
                    break

            if not final_answer:
                final_answer = "🚨 Vượt quá số vòng lặp tối đa. Agent đã bị phanh lại an toàn!"
                status_container.update(label="🛡️ Guardrail Triggered", state="error", expanded=True)
                
            # In ra màn hình và lưu lịch sử
            st.markdown(final_answer)
            st.session_state.messages.append({"role": "assistant", "content": step_logs, "type": "thought"})
            st.session_state.messages.append({"role": "assistant", "content": final_answer, "type": "final"})