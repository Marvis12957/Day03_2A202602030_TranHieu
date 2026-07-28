"""
🖥️ GIAO DIỆN STREAMLIT — CHATBOT (Cấp 2) vs REACT AGENT (Cấp 3)

Chạy:  streamlit run src/streamlit_app.py

File này CHỈ làm phần trình bày. Toàn bộ logic nghiệp vụ vẫn nằm nguyên ở:
  - src/app.py      (Role 4) — vòng lặp ReAct, parse Action, guardrails
  - src/tools.py    (Role 2) — 4 công cụ của phòng khám
  - src/prompts.py  (Role 3) — system prompt & guardrails
  - config/test_cases.json (Role 1) — 11 test case
Không nhân đôi logic ở đây, tránh CLI và UI lệch nhau về sau.

2 tab:
  ⚖️  So sánh 1 lượt      — cùng câu hỏi, Chatbot vs Agent song song (dùng để chấm rubric)
  💬  Hội thoại nhiều lượt — Agent hỏi lại thông tin còn thiếu rồi hoàn tất ở lượt sau
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


def event_to_markdown(ev: dict) -> str:
    """Đổi 1 sự kiện của vòng lặp ReAct thành 1 dòng markdown."""
    t = ev["type"]
    if t == "step":
        return f"\n**🔄 Bước {ev['step']}/{ev['max_steps']}**"
    if t == "thought":
        return f"🧠 **Thought:** {ev['text']}"
    if t == "action":
        args = ", ".join(f"`{a}`" for a in ev["args"]) or "*(không tham số)*"
        return f"🛠️ **Action:** `{ev['tool']}` ← {args}"
    if t == "observation":
        icon = "⚠️" if ev.get("is_error") else "👁️"
        return f"{icon} **Observation:** {ev['text']}"
    if t == "malformed":
        return f"⚠️ **Sai định dạng ReAct** — App nhắc lại cú pháp rồi thử tiếp: {ev['text']}"
    if t == "guardrail":
        return f"🛡️ **GUARDRAIL KÍCH HOẠT** ({ev['kind']}): {ev['text']}"
    return ""


def render_event_live(container, ev: dict):
    """Vẽ sự kiện lên UI ngay khi nó vừa xảy ra (dùng ở tab So sánh)."""
    t = ev["type"]
    if t == "observation":
        (container.warning if ev.get("is_error") else container.info)(
            f"👁️ **Observation:** {ev['text']}")
    elif t == "guardrail":
        container.error(event_to_markdown(ev))
    elif t == "malformed":
        container.warning(event_to_markdown(ev))
    else:
        md = event_to_markdown(ev)
        if md:
            container.markdown(md)


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
    st.subheader("🛡️ Guardrails")
    st.markdown(
        "1. Không chẩn đoán / kê thuốc\n"
        "2. Dấu hiệu cấp cứu → gọi 115\n"
        "3. Chống ảo giác (lấy tên khoa từ tool)\n"
        "4. Hỏi lại tên trước khi đặt lịch\n"
        "5. Chống injection & bảo vệ PII\n"
        "6. `MAX_ITERATIONS` chặn loop"
    )

st.title("🏥 Trợ lý Đặt Lịch Khám Bệnh & Tư vấn Chuyên khoa")
st.caption("Bài Lab 3 — So sánh **Chatbot (Cấp 2)** với **ReAct Agent (Cấp 3)**.")

tab_compare, tab_chat = st.tabs(["⚖️ So sánh 1 lượt", "💬 Hội thoại nhiều lượt"])

# ═══════════════════════════ TAB 1: SO SÁNH 1 LƯỢT ═══════════════════════════
with tab_compare:
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
            st.markdown("**Tool kỳ vọng:** "
                        + (", ".join(f"`{t}`" for t in selected["expected_tools"]) or "*không gọi tool*"))
            st.markdown(f"**Hành vi mong đợi:** {selected['expected_behavior']}")
            st.markdown(f"**Guardrail cần kiểm:** {selected['guardrail_check']}")

    col_run, col_mode = st.columns([1, 3])
    run = col_run.button("▶️ Chạy so sánh", type="primary", use_container_width=True)
    mode = col_mode.radio("Chạy bên nào", ["Cả hai (so sánh)", "Chỉ Chatbot", "Chỉ ReAct Agent"],
                          horizontal=True, label_visibility="collapsed")

    st.divider()

    if run and not question.strip():
        st.warning("Bạn chưa nhập câu hỏi.")
    elif run:
        left, right = st.columns(2, gap="large")

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
                st.caption("🔎 Quan sát: Chatbot có bịa số liệu / bịa lịch bác sĩ, "
                           "hay thừa nhận không truy cập được hệ thống?")

        with right:
            st.subheader("🧠 ReAct Agent · Cấp 3")
            st.caption("Suy luận Thought → Action → Observation và gọi công cụ thật.")
            if mode == "Chỉ Chatbot":
                st.info("Đã bỏ qua ở chế độ này.")
            else:
                trace_box = st.container()
                stats = {"tools": [], "guardrails": [], "steps": 0}

                def on_event(ev):
                    render_event_live(trace_box, ev)
                    if ev["type"] == "action":
                        stats["tools"].append(ev["tool"])
                    elif ev["type"] == "guardrail":
                        stats["guardrails"].append(ev["kind"])
                    elif ev["type"] == "step":
                        stats["steps"] = ev["step"]

                with st.spinner("Agent đang suy luận..."):
                    try:
                        final = core.run_react_agent(question, provider, on_event=on_event)
                    except Exception as e:
                        final = f"❌ Lỗi khi chạy Agent: {type(e).__name__}: {e}"

                st.divider()
                st.markdown("**🏁 Final Answer:**")
                st.success(final)

                m1, m2, m3 = st.columns(3)
                m1.metric("Số bước", f"{stats['steps']}/{MAX_ITERATIONS}")
                m2.metric("Lượt gọi tool", len(stats["tools"]))
                m3.metric("Guardrail", len(stats["guardrails"]) or "—")

                if selected is not None:
                    expected = sorted(set(selected["expected_tools"]))
                    actual = sorted(set(stats["tools"]))
                    if expected == actual:
                        st.success(f"✅ Khớp kỳ vọng — tool gọi: {actual or 'không gọi tool'}")
                    else:
                        st.warning(f"⚠️ Lệch kỳ vọng\n\n- Kỳ vọng: `{expected or 'không gọi tool'}`\n"
                                   f"- Thực tế: `{actual or 'không gọi tool'}`\n\n"
                                   "Lệch không hẳn là sai — Agent có thể chủ động gọi thêm tool hữu ích.")
    else:
        st.info("Chọn một test case rồi bấm **▶️ Chạy so sánh**.")
        st.markdown(
            "**Case đáng chiếu khi thuyết trình:**\n"
            "- `#5` — chuỗi 3 tool phụ thuộc nhau, Agent trả về mã lịch hẹn thật\n"
            "- `#10` — hỏi giá khám & BHYT: Chatbot phải bịa số, Agent tra ra số thật\n"
            "- `#1` vs `#10` — cùng nói về khoa Tim mạch, một câu KHÔNG cần tool, một câu BẮT BUỘC tool\n"
            "- `#7` — dấu hiệu đột quỵ: Agent phải khuyên gọi 115 chứ không đặt lịch\n"
            "- `#11` — đặt lịch 4 người: cố tình vượt ngân sách để `MAX_ITERATIONS` lộ diện"
        )

# ═══════════════════════════ TAB 2: HỘI THOẠI NHIỀU LƯỢT ═══════════════════════════
with tab_chat:
    st.caption("Agent nhớ ngữ cảnh các lượt trước. Guardrail buộc nó **hỏi lại tên bệnh nhân** "
               "trước khi đặt lịch — trả lời ở lượt sau để thấy nó dùng lại thông tin đã có.")

    c1, c2 = st.columns([3, 1])
    c1.info("💡 Thử: **“Tôi bị đau dạ dày, ợ chua. Đặt giúp tôi lịch khám sớm nhất.”** "
            "→ Agent sẽ hỏi tên. Lượt sau trả lời: **“Tôi tên Trần Văn A, chọn 09:00 thứ 5.”**")
    if c2.button("🗑️ Xoá hội thoại", use_container_width=True):
        st.session_state.chat = []
        st.rerun()

    if "chat" not in st.session_state:
        st.session_state.chat = []

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("trace"):
                with st.expander(f"🔍 Trace ReAct ({msg.get('steps', '?')} bước, "
                                 f"{msg.get('n_tools', 0)} lượt gọi tool)"):
                    st.markdown(msg["trace"])

    if user_msg := st.chat_input("Nhập tin nhắn cho trợ lý..."):
        st.session_state.chat.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        # Lịch sử các lượt TRƯỚC lượt hiện tại (bỏ chính tin nhắn vừa gửi)
        history = [{"role": m["role"], "content": m["content"]}
                   for m in st.session_state.chat[:-1]]

        trace_lines, stats = [], {"tools": [], "steps": 0}

        def collect(ev):
            md = event_to_markdown(ev)
            if md:
                trace_lines.append(md)
            if ev["type"] == "action":
                stats["tools"].append(ev["tool"])
            elif ev["type"] == "step":
                stats["steps"] = ev["step"]

        with st.chat_message("assistant"):
            with st.spinner("Agent đang suy luận..."):
                try:
                    reply = core.run_react_agent(user_msg, provider,
                                                 on_event=collect, history=history)
                except Exception as e:
                    reply = f"❌ Lỗi khi chạy Agent: {type(e).__name__}: {e}"
            st.markdown(reply)
            if trace_lines:
                with st.expander(f"🔍 Trace ReAct ({stats['steps']} bước, "
                                 f"{len(stats['tools'])} lượt gọi tool)"):
                    st.markdown("\n\n".join(trace_lines))

        st.session_state.chat.append({
            "role": "assistant", "content": reply,
            "trace": "\n\n".join(trace_lines),
            "steps": stats["steps"], "n_tools": len(stats["tools"]),
        })
