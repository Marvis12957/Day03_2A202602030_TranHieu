# 🔀 Hybrid Flowchart — Đặt Lịch Khám Bệnh & Tư Vấn Chuyên Khoa

*Sơ đồ phân luồng: câu hỏi đơn giản đi Chatbot path, câu hỏi phức tạp/cần dữ liệu thời gian thực đi ReAct Agent path.*
*Nguồn mã Mermaid gốc: [docs/hybrid_flowchart.mermaid](hybrid_flowchart.mermaid) (file này chỉ nhúng lại để xem trực tiếp trên GitHub/VS Code).*

```mermaid
%%{init: {'theme': 'default'}}%%
flowchart TD
    U["🧑‍⚕️ Người dùng đặt câu hỏi"] --> R{"🔀 Router: Câu hỏi có cần<br/>dữ liệu thời gian thực của<br/>phòng khám không?"}

    %% ================= NHÁNH CHATBOT (đơn giản) =================
    R -- "Không cần data động<br/>(kiến thức y tế chung)<br/>VD: Test Case #1, #2" --> CB["💬 CHATBOT PATH<br/>(1 LLM call, 0 tool)"]
    CB --> CBP["CHATBOT_BASELINE_PROMPT<br/>(src/prompts.py)"]
    CBP --> CBA{"Bị hỏi tra lịch /<br/>đặt lịch / giá cụ thể?"}
    CBA -- "Có" --> CBFallback["⚠️ Safe Fallback:<br/>xin lỗi, không truy cập được<br/>hệ thống phòng khám thực tế"]
    CBA -- "Không" --> CBAnswer["✅ Trả lời từ kiến thức<br/>có sẵn của LLM"]
    CBFallback --> FINAL(["📤 Trả kết quả cho người dùng"])
    CBAnswer --> FINAL

    %% ================= NHÁNH REACT AGENT (phức tạp) =================
    R -- "Cần data động / multi-step<br/>VD: Test Case #3,#4,#5,#8,#10" --> AG["🤖 REACT AGENT PATH<br/>(REACT_SYSTEM_PROMPT)"]

    AG --> G1{"🛡️ G1: Yêu cầu chẩn đoán<br/>bệnh / kê đơn thuốc?<br/>(VD: Test Case #6)"}
    G1 -- "Có" --> RefuseDx["❌ TỪ CHỐI chẩn đoán/kê đơn<br/>→ chỉ gợi ý chuyên khoa qua<br/>suggest_specialty()"]
    RefuseDx --> FINAL

    G1 -- "Không" --> G2{"🚨 G2: Có dấu hiệu cấp cứu?<br/>(méo miệng, yếu nửa người,<br/>nói líu nhíu...)<br/>(VD: Test Case #7)"}
    G2 -- "Có" --> Emergency["🚨 ƯU TIÊN CẤP CỨU:<br/>khuyên gọi 115 NGAY,<br/>KHÔNG đặt lịch hẹn thường"]
    Emergency --> FINAL

    G2 -- "Không" --> G4{"🔒 G4: Yêu cầu ghi đè<br/>system prompt / lộ PII<br/>bệnh nhân khác?<br/>(VD: Test Case #9)"}
    G4 -- "Có" --> RefuseInj["❌ TỪ CHỐI ghi đè luật hệ thống<br/>+ TỪ CHỐI tiết lộ PII"]
    RefuseInj --> FINAL

    G4 -- "Không" --> THINK["🧠 Thought: LLM suy luận<br/>bước tiếp theo"]

    THINK --> RESP{"Phản hồi LLM là gì?"}

    RESP -- "Final Answer" --> ANSWER["🏁 Tổng hợp câu trả lời<br/>từ các Observation thật —<br/>KHÔNG tự bịa dữ liệu"]
    ANSWER --> FINAL

    RESP -- "Action: tool[tham_số]" --> PARSE{"Parse cú pháp<br/>Action hợp lệ?"}
    PARSE -- "Không (Malformed)" --> FMTERR["⚠️ Observation:<br/>LỖI ĐỊNH DẠNG<br/>(yêu cầu LLM sửa cú pháp)"]

    PARSE -- "Có" --> REPEAT{"🛡️ G-Loop: Action này<br/>giống hệt Action<br/>ngay bước trước?"}
    REPEAT -- "Có (Repeated Action)" --> SAFEFB["⚠️ SAFE FALLBACK:<br/>ngắt vòng lặp,<br/>xin lỗi lịch sự"]
    SAFEFB --> FINAL

    REPEAT -- "Không" --> TOOL["⚙️ execute_tool()<br/>gọi hàm thật trong src/tools.py<br/>(suggest_specialty, check_doctor_schedule,<br/>book_appointment, get_clinic_info)"]
    TOOL --> TOOLOK{"Tool chạy<br/>thành công?"}
    TOOLOK -- "Lỗi nghiệp vụ (khoa/ngày/<br/>bác sĩ không tồn tại)" --> OBSERR["👁️ Observation: chuỗi LỖI<br/>(không crash chương trình)"]
    TOOLOK -- "Thành công" --> OBSOK["👁️ Observation: dữ liệu thật<br/>(VD: mã BK1001, danh sách<br/>bác sĩ, giờ trống...)"]

    FMTERR --> ITER{"🛡️ G3: step <<br/>MAX_ITERATIONS (=8)?"}
    OBSERR --> ITER
    OBSOK --> ITER

    ITER -- "Còn budget" --> THINK
    ITER -- "Đạt giới hạn" --> MAXOUT["🛡️ GUARDRAIL MAX_ITERATIONS:<br/>Safe Fallback lịch sự,<br/>không lặp vô hạn"]
    MAXOUT --> FINAL

    style CB fill:#dbeafe,stroke:#2563eb,color:#1e293b
    style AG fill:#dcfce7,stroke:#16a34a,color:#1e293b
    style Emergency fill:#fecaca,stroke:#dc2626,color:#1e293b
    style RefuseDx fill:#fecaca,stroke:#dc2626,color:#1e293b
    style RefuseInj fill:#fecaca,stroke:#dc2626,color:#1e293b
    style MAXOUT fill:#fef08a,stroke:#ca8a04,color:#1e293b
    style SAFEFB fill:#fef08a,stroke:#ca8a04,color:#1e293b
    style FMTERR fill:#fef08a,stroke:#ca8a04,color:#1e293b
    style FINAL fill:#e9d5ff,stroke:#7e22ce,color:#1e293b
```

## Chú giải màu

| Màu | Ý nghĩa |
| :--- | :--- |
| 🔵 Xanh dương | Chatbot Path — 1 LLM call, không dùng tool |
| 🟢 Xanh lá | ReAct Agent Path — vòng lặp Thought → Action → Observation |
| 🔴 Đỏ | Guardrail từ chối / cảnh báo cấp cứu (G1, G2, G4) |
| 🟡 Vàng | Safe Fallback do lỗi định dạng, Repeated Action, hoặc chạm MAX_ITERATIONS |
| 🟣 Tím | Điểm trả kết quả cuối cùng cho người dùng |
