"""
🚀 CẤP ĐỘ 4: AUTONOMOUS AGENT (Planning + Memory)

Cấp 3 phản ứng với đúng câu hỏi được đưa vào. Cấp 4 bọc thêm 2 thứ quanh vòng lặp đó:

  1. PLANNING — trước khi chạy, LLM tự chia mục tiêu lớn thành các việc con
                (mỗi người trong gia đình là một việc con riêng).
  2. MEMORY   — mã lịch hẹn và chuyên khoa đã xác định ở việc con trước được ghi
                nhớ và bơm vào ngữ cảnh việc con sau, nên Agent không đặt trùng
                lịch và không phải tra cứu lại từ đầu.

File này gọi thẳng `run_autonomous_agent()` trong src/app.py — không viết lại logic.

Chạy:  python src/ai_levels/level4_autonomous_agent.py

👉 Đây là câu hỏi mà Cấp 3 THẤT BẠI: yêu cầu cần 12 lượt gọi công cụ (4 người × 3 tool)
   trong khi MAX_ITERATIONS chỉ cho 8 bước, nên Cấp 3 bị guardrail ngắt giữa chừng,
   không đặt được lịch nào. Cấp 4 chia nhỏ ra, MỖI việc con có ngân sách 8 bước riêng,
   nên hoàn tất trọn vẹn cả 4 người.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import get_llm_provider, run_autonomous_agent  # noqa: E402
from prompts import MAX_ITERATIONS, MAX_SUBTASKS        # noqa: E402

if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 4: AUTONOMOUS AGENT (Planning + Memory) ===")
    provider = get_llm_provider()
    print(f"🔌 Provider: {provider.__class__.__name__} "
          f"(Model: {getattr(provider, 'model_name', 'Mock')}) | "
          f"MAX_ITERATIONS = {MAX_ITERATIONS}/việc con | MAX_SUBTASKS = {MAX_SUBTASKS}")

    # Chính là test case #11 — case mà ReAct Agent Cấp 3 bị MAX_ITERATIONS ngắt
    goal = ("Tôi muốn đặt lịch khám cho cả gia đình 4 người trong cùng hôm nay. "
            "Bố tôi tên Trần Văn Bố bị đau ngực và khó thở. "
            "Mẹ tôi tên Trần Thị Mẹ bị đau dạ dày, ợ chua. "
            "Tôi tên Trương Công Thái Đức bị đau đầu và chóng mặt. "
            "Em tôi tên Trương Văn Em bị đau khớp, đau lưng. "
            "Với TỪNG người, hãy tra chuyên khoa phù hợp, kiểm tra lịch bác sĩ rồi đặt lịch luôn.")

    result = run_autonomous_agent(goal, provider)

    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ ĐỐI CHIẾU VỚI CẤP 3")
    print("=" * 70)
    print(f"   Số việc con Planner chia ra : {len(result['subtasks'])}")
    print(f"   Số lịch hẹn đặt thành công  : {len(result['memory'].bookings)}")
    for b in result["memory"].bookings:
        print(f"      • {b['code']} — {b['patient']} | khoa {b['specialty']} | {b['slot']}")
    print("\n   ReAct Cấp 3 với CÙNG câu hỏi này: dừng ở bước 8/8 do MAX_ITERATIONS,")
    print("   đặt được 0 lịch hẹn. Chạy src/ai_levels/level3_reactive_agent.py để đối chiếu.")
