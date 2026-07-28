"""
🤖 CẤP ĐỘ 1: RULE-BASED BOT (Bot dựa trên luật if/else cố định)

Khớp từ khoá với câu trả lời soạn sẵn. KHÔNG dùng LLM, KHÔNG có công cụ.
Chủ đề: Phòng khám — Trợ lý Đặt Lịch Khám Bệnh (đồng bộ với app chính của nhóm).

Chạy:  python src/ai_levels/level1_rule_based.py

👉 Điểm yếu cần quan sát: chỉ cần người dùng diễn đạt khác đi một chút là bot
   rơi ngay vào nhánh `else`. Nó không "hiểu" câu hỏi, chỉ dò chuỗi con.
"""


def rule_based_bot(user_input: str) -> str:
    text = user_input.lower()
    if any(k in text for k in ["chào", "hello", "hi "]):
        return "Xin chào! Tôi là Rule-Based Bot (Cấp 1) của phòng khám. Bạn cần hỗ trợ gì?"
    elif any(k in text for k in ["giá", "chi phí", "bao nhiêu tiền"]):
        return "Phí khám chuyên khoa: 300.000 VNĐ/lần."
    elif any(k in text for k in ["giờ", "mấy giờ", "mở cửa"]):
        return "Phòng khám mở cửa 07:00 - 18:00 tất cả các ngày trong tuần."
    elif any(k in text for k in ["địa chỉ", "ở đâu"]):
        return "Địa chỉ: Số 123 Đường Giải Phóng, Q. Hai Bà Trưng, Hà Nội."
    elif "đặt lịch" in text:
        return "Vui lòng gọi hotline 1900-1234 để được lễ tân đặt lịch giúp bạn."
    else:
        return "Xin lỗi, câu hỏi của bạn nằm ngoài tập luật (keywords) được cài sẵn!"


if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 1: RULE-BASED BOT ===\n")
    demo = [
        "Chào bạn",                                              # khớp luật
        "Khám hết bao nhiêu tiền?",                              # khớp luật
        "Tôi bị đau ngực và khó thở, nên khám khoa nào?",        # ❌ ngoài luật
        "Đặt giúp tôi lịch sớm nhất với bác sĩ Tim mạch",        # khớp nửa vời
    ]
    for q in demo:
        print(f"👤 User: {q}")
        print(f"🤖 Bot : {rule_based_bot(q)}\n")

    print("💡 Nhận xét: câu số 3 là nhu cầu thật của bệnh nhân nhưng bot không có luật nào khớp.")
    print("   Câu số 4 khớp từ 'đặt lịch' nhưng chỉ trả lời máy móc, bỏ qua hoàn toàn 'Tim mạch'.")
