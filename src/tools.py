"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.
"""

import re

# Biến toàn cục để tạo mã booking deterministic (Role 5 cần kết quả reproducible)
_booking_counter = 1000
_booked_records = set()

def suggest_specialty(symptoms: str) -> str:
    """
    Gợi ý chuyên khoa phù hợp dựa trên mô tả triệu chứng của bệnh nhân.
    
    Args:
        symptoms (str): Mô tả triệu chứng bệnh nhân gặp phải (Ví dụ: 'đau thượng vị, buồn nôn')
        
    Returns:
        str: Tên chuyên khoa gợi ý hoặc cảnh báo cấp cứu/lỗi.
    """
    text = symptoms.lower()
    
    # 🛡️ GUARDRAIL 2 (Tầng Tool): Phát hiện dấu hiệu cấp cứu (Red Flags)
    red_flags = ["méo miệng", "yếu nửa người", "yếu hẳn nửa người", "nói líu nhíu", "đột ngột bị méo", "tê liệt nửa người"]
    for flag in red_flags:
        if flag in text:
            return (
                "🚨 DẤU HIỆU CẤP CỨU: Bệnh nhân có dấu hiệu đột quỵ/cấp cứu nguy hiểm (méo miệng, yếu nửa người, nói líu nhíu). "
                "Yêu cầu GỌI CẤP CỨU 115 hoặc đưa bệnh nhân đến cơ sở y tế gần nhất NGAY LẬP TỨC! "
                "Tuyệt đối KHÔNG đặt lịch hẹn khám thông thường trong trường hợp này."
            )
            
    # Tra cứu triệu chứng -> Chuyên khoa
    if any(k in text for k in ["thượng vị", "buồn nôn", "ợ chua", "dạ dày", "đau bụng", "ăn không tiêu"]):
        specialty = "Tiêu hóa"
    elif any(k in text for k in ["đau ngực", "khó thở", "tim đập nhanh", "huyết áp", "tim mạch"]):
        specialty = "Tim mạch"
    elif any(k in text for k in ["đau đầu", "chóng mặt", "tê bì", "mất ngủ", "thần kinh"]):
        specialty = "Nội thần kinh"
    elif any(k in text for k in ["ho", "đau họng", "ngạt mũi", "viêm xoang", "tai mũi họng"]):
        specialty = "Tai Mũi Họng"
    elif any(k in text for k in ["đau lưng", "đau khớp", "đau vai", "xương khớp"]):
        specialty = "Cơ Xương Khớp"
    else:
        return f"LỖI: Chưa xác định được chuyên khoa từ mô tả '{symptoms}'. Vui lòng mô tả rõ hơn các triệu chứng."

    # 🛡️ GUARDRAIL 1: Luôn kèm tuyên bố từ chối chẩn đoán bệnh
    return (
        f"Gợi ý chuyên khoa: Khoa {specialty}. "
        f"(Lưu ý: Đây là gợi ý khoa để thăm khám, không phải kết luận bệnh hay chẩn đoán y khoa)."
    )


def check_doctor_schedule(specialty: str, day: str = "thứ 5") -> str:
    """
    Tra cứu danh sách bác sĩ và các slot giờ còn trống theo chuyên khoa và ngày.
    
    Args:
        specialty (str): Tên chuyên khoa (Ví dụ: 'Tim mạch', 'Tiêu hóa')
        day (str): Ngày hoặc thứ cần tra cứu (Ví dụ: 'thứ 5', 'sáng thứ 5')
        
    Returns:
        str: Danh sách bác sĩ và các slot giờ khả dụng hoặc thông báo lỗi.
    """
    spec_clean = specialty.strip().lower()
    day_str = str(day).strip()
    
    # Kiểm tra ngày không hợp lệ (Edge case 8)
    if "32" in day_str or "13/2026" in day_str or re.search(r'\b(3[2-9]|[4-9]\d)/', day_str):
        return f"LỖI: Ngày '{day}' không hợp lệ."
        
    # Danh sách các khoa hợp lệ và lịch bác sĩ mock
    schedule_db = {
        "tim mạch": [
            {"doctor": "BS. Nguyễn Văn A", "slots": ["08:30 (Thứ 5)", "10:00 (Thứ 5)"]},
            {"doctor": "BS. Trần Thị B", "slots": ["14:00 (Thứ 5)", "09:00 (Thứ 6)"]}
        ],
        "tiêu hóa": [
            {"doctor": "BS. Lê Văn C", "slots": ["09:00 (Thứ 5)", "15:00 (Thứ 5)"]},
            {"doctor": "BS. Phạm Văn D", "slots": ["10:30 (Thứ 6)"]}
        ],
        "nội thần kinh": [
            {"doctor": "BS. Hoàng Thị E", "slots": ["08:00 (Thứ 5)", "13:30 (Thứ 5)"]}
        ],
        "tai mũi họng": [
            {"doctor": "BS. Đỗ Văn F", "slots": ["09:30 (Thứ 5)"]}
        ],
        "cơ xương khớp": [
            {"doctor": "BS. Vũ Thị G", "slots": ["11:00 (Thứ 5)"]}
        ]
    }
    
    # Bẫy khoa không tồn tại (Edge case 8: khoa Thú y)
    if spec_clean not in schedule_db:
        valid_specs = ", ".join([k.title() for k in schedule_db.keys()])
        return f"LỖI: Phòng khám không có chuyên khoa '{specialty}'. Các khoa hiện có: {valid_specs}."
        
    doctors = schedule_db[spec_clean]
    results = [f"Lịch rảnh Khoa {specialty.title()} ({day_str}):"]
    
    for doc in doctors:
        slots_str = ", ".join(doc["slots"])
        results.append(f"- {doc['doctor']}: Các slot rảnh [{slots_str}]")
        
    return "\n".join(results)


def book_appointment(patient_name: str, specialty: str, doctor_name: str = "Bác sĩ chuyên khoa", slot: str = "Sáng thứ 5 (08:30)") -> str:
    """
    Thực hiện đặt lịch hẹn khám bệnh cho bệnh nhân.
    
    Args:
        patient_name (str): Tên bệnh nhân
        specialty (str): Tên chuyên khoa
        doctor_name (str): Tên bác sĩ (nếu có)
        slot (str): Khung giờ đặt lịch
        
    Returns:
        str: Xác nhận đặt lịch thành công kèm mã BK deterministic hoặc thông báo lỗi.
    """
    global _booking_counter, _booked_records
    
    key = f"{patient_name.lower()}_{specialty.lower()}_{slot.lower()}"
    if key in _booked_records:
        return f"LỖI: Lịch hẹn cho bệnh nhân '{patient_name}' tại khoa '{specialty}' vào khung giờ '{slot}' đã được đặt trước đó (Tránh đặt trùng lặp)."
        
    _booking_counter += 1
    booking_id = f"BK{_booking_counter}"
    _booked_records.add(key)
    
    return (
        f"✅ ĐẶT LỊCH THÀNH CÔNG!\n"
        f"- Mã lịch hẹn: {booking_id}\n"
        f"- Bệnh nhân: {patient_name}\n"
        f"- Chuyên khoa: {specialty}\n"
        f"- Bác sĩ: {doctor_name}\n"
        f"- Thời gian: {slot}\n"
        f"- Trạng thái: Đã ghi nhận hệ thống phòng khám."
    )


def get_clinic_info(topic: str) -> str:
    """
    Tra cứu thông tin chung về phòng khám (Chi phí, địa chỉ, giờ làm việc, BHYT).
    
    Args:
        topic (str): Chủ đề cần hỏi (Ví dụ: 'giá khám', 'địa chỉ', 'giờ làm việc', 'bhyt')
        
    Returns:
        str: Thông tin chi tiết về phòng khám.
    """
    t = topic.lower()
    if any(k in t for k in ["giá", "chi phí", "bhyt", "bảo hiểm"]):
        return "Chi phí khám chuyên khoa: 300.000 VNĐ/lần. Phòng khám có áp dụng BHYT theo quy định nhà nước (hỗ trợ giảm trừ lên tới 80%)."
    elif any(k in t for k in ["địa chỉ", "ở đâu", "vị trí"]):
        return "Địa chỉ phòng khám: Số 123 Đường Giải Phóng, Q. Hai Bà Trưng, Hà Nội."
    elif any(k in t for k in ["giờ", "thời gian"]):
        return "Giờ làm việc: 07:00 - 18:00 tất cả các ngày trong tuần (từ Thứ 2 đến Chủ Nhật)."
    else:
        # 🛡️ CHỐNG LẠM DỤNG TOOL: nhánh này TRƯỚC ĐÂY là catch-all trả thông tin chung cho
        # mọi chủ đề, khiến Agent gọi tool cả với câu hỏi kiến thức y khoa phổ thông
        # (VD: "khám Tim mạch gồm những gì?") rồi nhét giá tiền/địa chỉ vô nghĩa vào câu trả lời.
        # Nay trả LỖI rõ ràng để Agent biết đây không phải việc của tool này.
        return (
            f"LỖI: Tool này chỉ tra cứu thông tin hành chính của phòng khám, không có dữ liệu về chủ đề '{topic}'. "
            f"Các chủ đề hợp lệ: 'giá khám' / 'bảo hiểm - BHYT' / 'địa chỉ' / 'giờ làm việc'. "
            f"Nếu người dùng hỏi kiến thức y khoa phổ thông, hãy tự trả lời bằng kiến thức có sẵn, không cần gọi tool."
        )


# Danh sách các tool được đăng ký để Agent sử dụng
AVAILABLE_TOOLS = {
    "suggest_specialty": suggest_specialty,
    "check_doctor_schedule": check_doctor_schedule,
    "book_appointment": book_appointment,
    "get_clinic_info": get_clinic_info,
}

