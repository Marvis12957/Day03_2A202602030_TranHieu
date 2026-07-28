"""
🤖 CẤP ĐỘ 2: LLM CHATBOT (Baseline Chatbot — có LLM nhưng KHÔNG có Tool)

Khác Cấp 1 ở đúng một điểm cốt lõi: câu trả lời do LLM THẬT sinh ra, nên diễn đạt
tự nhiên và hiểu được câu hỏi dù người dùng nói cách nào. Nhưng vẫn không thể tra
cứu dữ liệu riêng của phòng khám (lịch bác sĩ, slot trống) hay thực hiện đặt lịch.

Chạy:  python src/ai_levels/level2_llm_chatbot.py
       (cần cấu hình API key trong .env — xem .env.example)

👉 Điểm yếu cần quan sát: gặp câu cần dữ liệu thật, Chatbot chỉ có 2 lựa chọn —
   thú nhận không biết, hoặc bịa ra (ảo giác). Cả hai đều không giải quyết được
   nhu cầu của bệnh nhân.
"""

import os
import sys

# Cho phép import các module nằm ở thư mục src/ (cha của thư mục ai_levels/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from prompts import CHATBOT_BASELINE_PROMPT  # noqa: E402  (dùng chung prompt của Role 3)
from providers import get_llm_provider       # noqa: E402

load_dotenv()


def llm_chatbot(user_input: str, provider=None) -> str:
    """Gọi LLM thật để sinh câu trả lời — KHÔNG cấp cho nó công cụ nào."""
    provider = provider or get_llm_provider()
    return provider.generate(user_input, system_prompt=CHATBOT_BASELINE_PROMPT)


if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 2: LLM CHATBOT BASELINE (không Tool) ===\n")
    provider = get_llm_provider()
    print(f"🔌 Provider: {provider.__class__.__name__} "
          f"(Model: {getattr(provider, 'model_name', 'Mock')})\n")

    demo = [
        "Tôi bị đau ngực và khó thở, nên khám khoa nào?",          # LLM trả lời được
        "Sáng thứ 5 khoa Tim mạch còn bác sĩ nào trống lịch?",     # ❌ cần dữ liệu riêng
        "Đặt giúp tôi lịch khám sớm nhất và cho tôi mã lịch hẹn",  # ❌ cần hành động thật
    ]
    for q in demo:
        print(f"👤 User: {q}")
        print(f"🤖 Bot : {llm_chatbot(q, provider)}\n")

    print("💡 Nhận xét: câu 1 trả lời trôi chảy vì là kiến thức y khoa phổ thông.")
    print("   Câu 2 và 3 thì bó tay — Chatbot không có kết nối tới hệ thống phòng khám,")
    print("   và cũng không có khả năng THỰC HIỆN thao tác đặt lịch. Đó là lý do cần Cấp 3.")
