"""
🧠 CẤP ĐỘ 3: REACTIVE AGENT (ReAct — Thought → Action → Observation)

Agent tự quyết định gọi công cụ nào, đọc kết quả trả về (Observation) rồi suy luận
tiếp cho tới khi đủ thông tin trả lời.

File này KHÔNG viết lại vòng lặp — nó gọi thẳng `run_react_agent()` trong src/app.py,
tức là đúng con Agent mà nhóm nộp bài. Nhờ vậy demo luôn khớp với app thật, và không
có nguy cơ demo chạy đúng còn app chạy sai.

Chạy:  python src/ai_levels/level3_reactive_agent.py

👉 Điểm mạnh so với Cấp 2: đặt được lịch thật và trả về mã lịch hẹn có thật.
👉 Giới hạn còn lại: chỉ phản ứng với đúng câu hỏi được đưa vào, không tự chia nhỏ
   mục tiêu. Gặp yêu cầu dài (đặt lịch cho cả nhà) sẽ đụng trần MAX_ITERATIONS.
   Đó là lý do cần Cấp 4.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import get_llm_provider, run_react_agent  # noqa: E402
from prompts import MAX_ITERATIONS                 # noqa: E402

if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 3: REACTIVE AGENT (ReAct Loop thật) ===")
    provider = get_llm_provider()
    print(f"🔌 Provider: {provider.__class__.__name__} "
          f"(Model: {getattr(provider, 'model_name', 'Mock')}) | MAX_ITERATIONS = {MAX_ITERATIONS}")

    goal = ("Tôi tên Trần Văn Hiếu, bị đau ngực âm ỉ và hơi khó thở khi leo cầu thang. "
            "Bạn tư vấn giúp tôi nên khám khoa nào rồi đặt luôn lịch sớm nhất giúp tôi nhé.")
    run_react_agent(goal, provider)

    print("\n💡 Nhận xét: Agent đã tự đi qua chuỗi 3 công cụ phụ thuộc nhau —")
    print("   suggest_specialty ➔ check_doctor_schedule ➔ book_appointment,")
    print("   kết quả bước trước trở thành tham số bước sau. Chatbot Cấp 2 không làm được việc này.")
