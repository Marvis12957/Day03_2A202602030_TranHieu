# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*
*Đề tài nhóm: **Đặt Lịch Khám Bệnh & Tư Vấn Chuyên Khoa***

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí | Điểm (1-5) | Lý do đánh giá |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `5/5` | Test case #5: từ triệu chứng ("đau ngực âm ỉ, khó thở khi leo cầu thang") phải suy luận ra chuyên khoa, rồi tìm bác sĩ trống lịch, rồi mới đặt lịch — 3 bước suy luận nối tiếp, không thể trả lời chỉ bằng 1 lần gọi LLM. |
| 🛠️ **Tool Interaction** | `5/5` | Bắt buộc cần dữ liệu thời gian thực từ hệ thống phòng khám: danh mục chuyên khoa (`suggest_specialty`), lịch trống bác sĩ theo ngày (`check_doctor_schedule`), và ghi nhận lịch hẹn (`book_appointment`). Chatbot thuần không có các dữ liệu này nên chỉ đoán mò. |
| 🔀 **Dynamic Decision** | `5/5` | Test case #5 là minh chứng rõ nhất: kết quả `suggest_specialty` → `"Tim mạch"` trở thành tham số đầu vào của `check_doctor_schedule('Tim mạch')`; slot trống trả về ở bước 2 lại trở thành tham số của `book_appointment`. Bước sau phụ thuộc hoàn toàn vào Observation của bước trước. |
| ⏳ **Long Horizon** | `3/5` | Đa số case chỉ cần 1 tool (case #3, #4); case phức tạp nhất cần chuỗi 3 tool phụ thuộc nhau (case #5). Không phải quy trình rất dài (5+ bước), nhưng đủ dài để bắt buộc phải giữ trạng thái (state) giữa các bước. |
| **TỔNG ĐIỂM FIT** | **18/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT.** Ngoài lý do dữ liệu thời gian thực, đề tài y tế còn đòi hỏi 4 lớp Guardrail an toàn (không chẩn đoán bệnh, ưu tiên cấp cứu, tool fail an toàn, chống prompt injection/rò rỉ PII) mà một Chatbot 1-lần-gọi không thể tự đảm bảo. |

*Căn cứ đánh giá: 9 test case trong [config/test_cases.json](../config/test_cases.json) do Role 1 soạn (2 câu đơn giản, 3 câu multi-step, 4 câu bẫy an toàn/edge case).*

---

## 🔍 2. SO SÁNH PHẢN HỒI: CHATBOT BASELINE vs REACT AGENT

> ⏳ **Trạng thái: CHỜ DỮ LIỆU.** Mục này cần chạy `python src/app.py` với `run_baseline_chatbot()` và `run_react_agent()` đã được Role 4 lắp ráp cho đúng bộ tool khám bệnh (`suggest_specialty`, `check_doctor_schedule`, `book_appointment`). Hiện `src/tools.py` / `src/prompts.py` / `src/app.py` vẫn là bản mẫu demo thời tiết — Role 2/3/4 cần push code thật trước khi mục này điền được.

Khung điền sẵn cho từng test case (điền sau khi có code thật):

| # | Câu hỏi (rút gọn) | Phản hồi Chatbot Baseline | Phân loại | Phản hồi ReAct Agent | Phân loại |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | Khám Tim mạch gồm gì? | *(điền sau)* | ⬜ correct / ⬜ safe fallback / ⬜ hallucinated | *(điền sau)* | ⬜ correct / ⬜ safe fallback / ⬜ hallucinated |
| 2 | Chuẩn bị gì trước khám tổng quát? | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 3 | Đau thượng vị, buồn nôn → khoa nào? | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 4 | Sáng thứ 5 khoa Tim mạch còn trống không? | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 5 | Đau ngực + khó thở → tư vấn + đặt lịch | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 6 | Đau đầu 2 tuần, đòi kê thuốc | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 7 | Dấu hiệu đột quỵ, đòi đặt lịch tuần sau | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 8 | Khoa/bác sĩ/ngày không hợp lệ | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |
| 9 | Prompt injection đòi hồ sơ bệnh nhân | *(điền sau)* | ⬜ | *(điền sau)* | ⬜ |

**Chú giải phân loại**: *correct* = đúng và có bằng chứng; *safe fallback* = từ chối lịch sự đúng lúc (không có data thì không bịa); *hallucinated* = bịa thông tin không có thật (VD: tự bịa tên bác sĩ, giờ trống, hoặc chẩn đoán bệnh).

---

## 🧵 3. TRACE LOG REACT AGENT (Thought → Action → Observation)

> ⏳ **Trạng thái: CHỜ DỮ LIỆU.** Dán log thật sau khi chạy `python src/app.py` với ReAct loop đã lắp cho đề tài khám bệnh. Ưu tiên dán trace của **test case #5** (chuỗi 3 tool phụ thuộc nhau) vì đây là case thể hiện rõ nhất Dynamic Decision.

```text
(Dán log Thought -> Action -> Observation -> ... -> Final Answer tại đây)
```

---

## 🩺 4. FAILED TRACE → ROOT CAUSE ANALYSIS (Before / After Agent V2)

> ⏳ **Trạng thái: CHỜ DỮ LIỆU.** Chọn 1 trong các câu bẫy (test case #6, #7, #8 hoặc #9) làm câu ép lỗi có chủ đích, chạy Agent V1, ghi lại lỗi, rồi so sánh sau khi Role 3/4 nâng cấp Agent V2.

| Mục | Nội dung |
| :--- | :--- |
| Test case dùng để ép lỗi | *(VD: #8 — khoa Thú y / bác sĩ không tồn tại / ngày 32/13/2026)* |
| Biểu hiện lỗi (Before) | *(điền sau: VD Agent lặp vô hạn / tool crash / bịa tên bác sĩ...)* |
| Failure Mode | ⬜ Unknown Tool ⬜ Malformed Args ⬜ Repeated Action ⬜ Khác |
| Root Cause | *(điền sau)* |
| Cách Agent V2 khắc phục | *(điền sau: VD MAX_ITERATIONS chặn loop, tool trả string lỗi kèm danh sách khoa hợp lệ...)* |
| Kết quả sau khi sửa (After) | *(điền sau)* |

---

## ✅ Checklist tiến độ Role 5

- [x] Mốc 1: Điền Scoring Matrix cho đúng đề tài "Đặt lịch khám bệnh".
- [ ] Mốc 2: Ghi phản hồi Chatbot Baseline cho 9 test case (chờ Role 4 lắp `run_baseline_chatbot()` cho đề tài thật).
- [ ] Mốc 3: Dán trace `Thought -> Action -> Observation` của ReAct Agent (chờ Role 2/3/4 hoàn thiện tool + prompt + loop cho đề tài thật).
- [ ] Mốc 3.5: Phân tích 1 Failed Trace (Root Cause Analysis) trước/sau khi nâng cấp Agent V2.
- [ ] Mốc 4: (Role 5B nếu tách vai) Vẽ `docs/hybrid_flowchart.mermaid`.
