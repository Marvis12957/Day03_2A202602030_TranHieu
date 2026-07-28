"""
🖥️ GIAO DIỆN STREAMLIT — SO SÁNH CHATBOT (Cấp 2) vs REACT AGENT (Cấp 3)

Chạy:  streamlit run src/streamlit_app.py

File này CHỈ làm phần trình bày. Toàn bộ logic nghiệp vụ vẫn nằm nguyên ở:
  - src/app.py      (Role 4) — vòng lặp ReAct, parse Action, guardrails
  - src/tools.py    (Role 2) — 4 công cụ của phòng khám
  - src/prompts.py  (Role 3) — system prompt & guardrails
  - config/test_cases.json (Role 1) — 11 test case
Không nhân đôi logic ở đây, tránh CLI và UI lệch nhau về sau.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as core  # noqa: E402  (app.py có __main__ guard nên import an toàn)
from prompts import MAX_ITERATIONS  # noqa: E402

st.set_page_config(page_title="Chatbot vs ReAct Agent — Trợ lý Đặt Lịch Khám",
                   page_icon="🏥", layout="wide")

CATEGORY_ICON = {"🟢": "🟢 Đơn giản", "🟡": "🟡 Multi-step", "🔴": "🔴 Bẫy / Edge case"}


@st.cache_resource
def get_provider():
    """Khởi tạo provider 1 lần rồi tái sử dụng, tránh tạo client mới mỗi lần bấm nút."""
    return core.get_llm_provider()


@st.cache_data
def get_cases():
    return core.load_test_cases()


def render_trace_event(container, ev: dict):
    """Vẽ 1 sự kiện của vòng lặp ReAct lên UI ngay khi nó vừa xảy ra."""
    t = ev["type"]
    if t == "step":
        container.markdown(f"**🔄 Bước {ev['step']}/{ev['max_steps']}**")
    elif t == "thought":
        container.markdown(f"🧠 **Thought:** {ev['text']}")
    elif t == "action":
        args = ", ".join(f"`{a}`" for a in ev["args"]) or "*(không tham số)*"
        container.markdown(f"🛠️ **Action:** `{ev['tool']}` ← {args}")
    elif t == "observation":
        if ev.get("is_error"):
            container.warning(f"👁️ **Observation (lỗi):** {ev['text']}")
        else:
            container.info(f"👁️ **Observation:** {ev['text']}")
    elif t == "malformed":
        container.warning(f"⚠️ **Sai định dạng ReAct** — App nhắc lại cú pháp rồi thử tiếp:\n\n{ev['text']}")
    elif t == "guardrail":
        container.error(f"🛡️ **GUARDRAIL KÍCH HOẠT** ({ev['kind']}): {ev['text']}")


# ─────────────────────────────── Sidebar ───────────────────────────────
provider = get_provider()
cases = get_cases()

with st.sidebar:
    st.header("⚙️ Cấu hình")
    st.metric("LLM Provider", provider.__class__.__name__.replace("Provider", ""))
    st.caption(f"Model: `{getattr(provider, 'model_name', 'Mock')}`")
    st.metric("MAX_ITERATIONS", MAX_ITERATIONS)
    st.caption("Guardrail chặn vòng lặp vô tận")

    st.divider()
    st.subheader("🛠️ Công cụ Agent có")
    for name in core.AVAILABLE_TOOLS:
        st.markdown(f"- `{name}`")

    st.divider()
    st.subheader("🛡️ 4 Guardrails")
    st.markdown(
        "1. Không chẩn đoán / kê thuốc\n"
        "2. Dấu hiệu cấp cứu → gọi 115\n"
        "3. `MAX_ITERATIONS` chặn loop\n"
        "4. Chống injection & bảo vệ PII"
    )

# ─────────────────────────────── Header ───────────────────────────────
st.title("🏥 Trợ lý Đặt Lịch Khám Bệnh & Tư vấn Chuyên khoa")
st.caption("Bài Lab 3 — So sánh **Chatbot (Cấp 2)** với **ReAct Agent (Cấp 3)** trên cùng một câu hỏi.")

# ─────────────────────────── Chọn câu hỏi ───────────────────────────
labels = ["✍️ Tự gõ câu hỏi khác..."] + [
    f"#{c['id']} {CATEGORY_ICON.get(c['category'][0], '')} — {c['question'][:70]}"
    + ("..." if len(c["question"]) > 70 else "")
    for c in cases
]
choice = st.selectbox("Chọn test case có sẵn", labels, index=5)

if choice.startswith("✍️"):
    question = st.text_area("Câu hỏi của bệnh nhân", height=100,
                            placeholder="VD: Tôi bị đau ngực và khó thở, đặt giúp tôi lịch khám sớm nhất...")
    selected = None
else:
    selected = cases[labels.index(choice) - 1]
    question = st.text_area("Câu hỏi của bệnh nhân", value=selected["question"], height=100)
    with st.expander("📋 Kỳ vọng của test case này (Role 1 soạn)"):
        st.markdown(f"**Phân loại:** {selected['category']}")
        st.markdown(f"**Tool kỳ vọng:** "
                    + (", ".join(f"`{t}`" for t in selected["expected_tools"]) or "*không gọi tool*"))
        st.markdown(f"**Hành vi mong đợi:** {selected['expected_behavior']}")
        st.markdown(f"**Guardrail cần kiểm:** {selected['guardrail_check']}")

col_run, col_mode = st.columns([1, 3])
run = col_run.button("▶️ Chạy so sánh", type="primary", use_container_width=True)
mode = col_mode.radio("Chạy bên nào", ["Cả hai (so sánh)", "Chỉ Chatbot", "Chỉ ReAct Agent"],
                      horizontal=True, label_visibility="collapsed")

st.divider()

# ─────────────────────────────── Chạy ───────────────────────────────
if run:
    if not question.strip():
        st.warning("Bạn chưa nhập câu hỏi.")
        st.stop()

    left, right = st.columns(2, gap="large")

    # ---- Cột trái: Chatbot Baseline (Cấp 2) ----
    with left:
        st.subheader("🤖 Chatbot Baseline · Cấp 2")
        st.caption("Chỉ có kiến thức sẵn trong LLM — không công cụ, không truy cập dữ liệu phòng khám.")
        if mode == "Chỉ ReAct Agent":
            st.info("Đã bỏ qua ở chế độ này.")
        else:
            with st.spinner("Chatbot đang trả lời..."):
                try:
                    answer = core.run_baseline_chatbot(question, provider)
                except Exception as e:
                    answer = f"❌ Lỗi khi gọi LLM: {type(e).__name__}: {e}"
            st.markdown("**Câu trả lời:**")
            st.markdown(answer)
            st.caption("🔎 Điểm cần quan sát: Chatbot có bịa số liệu, bịa lịch bác sĩ, "
                       "hay thừa nhận không truy cập được hệ thống?")

    # ---- Cột phải: ReAct Agent (Cấp 3) ----
    with right:
        st.subheader("🧠 ReAct Agent · Cấp 3")
        st.caption("Suy luận Thought → Action → Observation và gọi công cụ thật.")
        if mode == "Chỉ Chatbot":
            st.info("Đã bỏ qua ở chế độ này.")
        else:
            trace_box = st.container()
            tools_used, guardrails_fired, steps_used = [], [], 0

            def on_event(ev):
                """Callback truyền vào core.run_react_agent — vẽ trace ngay khi sự kiện xảy ra."""
                global steps_used
                render_trace_event(trace_box, ev)
                if ev["type"] == "action":
                    tools_used.append(ev["tool"])
                elif ev["type"] == "guardrail":
                    guardrails_fired.append(ev["kind"])
                elif ev["type"] == "step":
                    steps_used = ev["step"]

            with st.spinner("Agent đang suy luận..."):
                try:
                    final = core.run_react_agent(question, provider, on_event=on_event)
                except Exception as e:
                    final = f"❌ Lỗi khi chạy Agent: {type(e).__name__}: {e}"

            st.divider()
            st.markdown("**🏁 Final Answer:**")
            st.success(final)

            m1, m2, m3 = st.columns(3)
            m1.metric("Số bước", f"{steps_used}/{MAX_ITERATIONS}")
            m2.metric("Lượt gọi tool", len(tools_used))
            m3.metric("Guardrail", len(guardrails_fired) or "—")

            if selected is not None:
                expected = sorted(set(selected["expected_tools"]))
                actual = sorted(set(tools_used))
                if expected == actual:
                    st.success(f"✅ Khớp kỳ vọng — tool gọi: {actual or 'không gọi tool'}")
                else:
                    st.warning(f"⚠️ Lệch kỳ vọng\n\n- Kỳ vọng: `{expected or 'không gọi tool'}`\n"
                               f"- Thực tế: `{actual or 'không gọi tool'}`\n\n"
                               "Lệch không hẳn là sai — Agent có thể chủ động gọi thêm tool hữu ích.")
else:
    st.info("Chọn một test case rồi bấm **▶️ Chạy so sánh**.")
    st.markdown(
        "**Gợi ý case đáng chiếu khi thuyết trình:**\n"
        "- `#5` — chuỗi 3 tool phụ thuộc nhau, Agent trả về mã lịch hẹn thật (Chatbot không làm được)\n"
        "- `#10` — hỏi giá khám & BHYT: Chatbot phải bịa số, Agent tra ra số thật\n"
        "- `#7` — dấu hiệu đột quỵ: Agent phải khuyên gọi 115 chứ không đặt lịch tuần sau\n"
        "- `#11` — đặt lịch cho 4 người: cố tình vượt ngân sách vòng lặp để `MAX_ITERATIONS` lộ diện"
    )
