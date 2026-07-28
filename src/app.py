"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import re
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import (CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, PLANNER_PROMPT,
                     MAX_ITERATIONS, MAX_SUBTASKS)
from providers import get_llm_provider

load_dotenv()

def load_test_cases(filename: str = "test_cases.json"):
    """Đọc bộ test cases từ config/<filename> (mặc định test_cases.json của Role 1)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", filename)

    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = filename

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")

    # Gọi LLM Provider thực hiện sinh câu trả lời
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


# Regex tách dòng Action: ten_tool[tham_so_1, 'tham số 2'] (chấp nhận cả ngoặc tròn nếu LLM lỡ dùng).
# Không neo "$" ở cuối để chịu được trường hợp LLM lỡ chèn thêm chú thích sau dấu đóng ngoặc
# (VD: "book_appointment[...]  # hoặc chọn slot khác") — nhờ ".*" tham lam nên vẫn khớp đúng
# dấu đóng ngoặc CUỐI CÙNG của lời gọi tool, phần chú thích phía sau bị bỏ qua thay vì bị coi là lỗi.
_ACTION_LINE_RE = re.compile(r"^(\w+)[\[\(](.*)[\]\)]")
# Regex tách tham số, tôn trọng dấu nháy để không vỡ khi tham số có dấu phẩy bên trong
_ARGS_RE = re.compile(r"""\s*'([^']*)'|\s*"([^"]*)"|\s*([^,]+)""")


def parse_args(args_str: str) -> list:
    """Tách chuỗi tham số thô trong Action[...] thành list, giữ nguyên dấu phẩy trong chuỗi có nháy."""
    args = []
    for a, b, c in _ARGS_RE.findall(args_str):
        value = (a or b or c).strip()
        if value:
            args.append(value)
    return args


def parse_agent_response(response_text: str) -> dict:
    """
    Đọc phản hồi thô từ LLM và trích ra đúng 1 bước hành động kế tiếp
    (Thought + Action, hoặc Thought + Final Answer). Nếu LLM lỡ sinh thêm
    Observation/step giả sau Action thì bỏ qua phần đó — Observation thật
    chỉ được phép đến từ việc App tự gọi Tool.
    """
    lines = response_text.strip().splitlines()
    thought = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("Thought:") and thought is None:
            thought = stripped[len("Thought:"):].strip()

        if stripped.startswith("Final Answer:"):
            final_text = stripped[len("Final Answer:"):].strip()
            extra_lines = []
            for l in lines[i + 1:]:
                # Chỉ dừng khi gặp mốc ReAct kế tiếp. TRƯỚC ĐÂY còn dừng ở cả dòng trống,
                # khiến Final Answer nhiều đoạn bị cắt cụt: khi LLM trả lời dạng
                # "Khám Tim mạch gồm:" + (dòng trống) + danh sách gạch đầu dòng thì
                # toàn bộ danh sách bị mất, chỉ còn lại câu mở đầu.
                if l.strip().startswith(("Thought:", "Action:", "Observation:")):
                    break
                extra_lines.append(l.rstrip())
            while extra_lines and not extra_lines[-1].strip():
                extra_lines.pop()
            if extra_lines:
                final_text = (final_text + "\n" + "\n".join(extra_lines)).strip()
            return {"type": "final", "thought": thought, "final_answer": final_text}

        if stripped.startswith("Action:"):
            action_str = stripped[len("Action:"):].strip()
            match = _ACTION_LINE_RE.match(action_str)
            if not match:
                return {"type": "malformed", "thought": thought, "raw": action_str}
            tool_name = match.group(1)
            args = parse_args(match.group(2))
            return {"type": "action", "thought": thought, "tool": tool_name, "args": args}

    return {"type": "malformed", "thought": thought, "raw": response_text.strip()}


def execute_tool(tool_name: str, args: list) -> str:
    """Thực thi Tool an toàn: lỗi nghiệp vụ hay sai tham số đều trả về chuỗi lỗi, không crash Agent."""
    tool_fn = AVAILABLE_TOOLS.get(tool_name)
    if tool_fn is None:
        available = ", ".join(AVAILABLE_TOOLS.keys())
        return f"LỖI: Tool '{tool_name}' không tồn tại. Các tool hợp lệ: [{available}]"
    try:
        return tool_fn(*args)
    except TypeError as e:
        return f"LỖI: Gọi tool '{tool_name}' sai số lượng/kiểu tham số ({e}). Hãy kiểm tra lại cú pháp Action."
    except Exception as e:
        return f"LỖI: Tool '{tool_name}' gặp sự cố khi thực thi: {e}"


def run_react_agent(user_query: str, provider, on_event=None):
    """
    Dựng vòng lặp ReAct Agent thật: gọi LLM sinh Thought -> Action, App tự thực thi
    Tool lấy Observation thật rồi đưa lại vào ngữ cảnh cho vòng suy luận kế tiếp.
    Có Guardrails: MAX_ITERATIONS chặn lặp vô hạn, chặn Repeated Action.

    Args:
        on_event (callable | None): Callback tuỳ chọn, gọi sau mỗi sự kiện trong vòng lặp
            với 1 dict {"type": "step"|"thought"|"action"|"observation"|"final"|
            "malformed"|"guardrail", ...}. Để None thì hàm chạy y hệt như cũ (chỉ in ra
            terminal) — giao diện Streamlit truyền callback vào để vẽ trace trực tiếp
            mà không phải viết lại logic vòng lặp ở nơi khác.
    """
    def emit(**payload):
        if on_event:
            on_event(payload)

    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    scratchpad = f"Câu hỏi của bệnh nhân: {user_query}\n"
    last_action_signature = None
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        emit(type="step", step=step, max_steps=MAX_ITERATIONS)

        raw_response = provider.generate(scratchpad, system_prompt=REACT_SYSTEM_PROMPT)
        parsed = parse_agent_response(raw_response)

        if parsed["thought"]:
            print(f"🧠 Thought: {parsed['thought']}")
            emit(type="thought", text=parsed["thought"])

        if parsed["type"] == "final":
            print(f"🏁 Final Answer: {parsed['final_answer']}")
            emit(type="final", text=parsed["final_answer"], steps=step)
            return parsed["final_answer"]

        if parsed["type"] == "malformed":
            print(f"⚠️ Phản hồi không đúng định dạng ReAct (Thought/Action/Final Answer): {parsed['raw'][:200]}")
            emit(type="malformed", text=parsed["raw"][:200])
            scratchpad += (
                "Observation: LỖI ĐỊNH DẠNG - Phản hồi trước không đúng cú pháp. "
                "Bắt buộc trả lời theo đúng định dạng 'Thought: ...' rồi 'Action: ten_tool[tham_so]' "
                "hoặc 'Thought: ...' rồi 'Final Answer: ...'.\n"
            )
            continue

        # parsed["type"] == "action"
        tool_name, args = parsed["tool"], parsed["args"]
        print(f"🛠️ Action: {tool_name}{args}")
        emit(type="action", tool=tool_name, args=args)

        action_signature = (tool_name, tuple(args))
        if action_signature == last_action_signature:
            print("🛡️ GUARDRAIL TRIGGERED (Repeated Action): Agent lặp lại đúng 1 Action liên tiếp — ngắt an toàn.")
            fallback = (
                "Xin lỗi, tôi chưa thể xử lý trọn vẹn yêu cầu này với dữ liệu hiện có của phòng khám. "
                "Bạn vui lòng thử mô tả rõ hơn hoặc liên hệ trực tiếp lễ tân để được hỗ trợ."
            )
            print(f"🏁 Final Answer (Safe Fallback): {fallback}")
            emit(type="guardrail", kind="repeated_action",
                 text=f"Agent lặp lại đúng 1 Action liên tiếp ({tool_name}) — ngắt an toàn.")
            emit(type="final", text=fallback, steps=step, fallback=True)
            return fallback
        last_action_signature = action_signature

        obs = execute_tool(tool_name, args)
        print(f"👁️ Observation: {obs}")
        emit(type="observation", text=obs, is_error=obs.startswith("LỖI"))

        scratchpad += (
            f"Thought: {parsed['thought'] or ''}\n"
            f"Action: {tool_name}{args}\n"
            f"Observation: {obs}\n"
        )

    print(f"🛡️ GUARDRAIL TRIGGERED (MAX_ITERATIONS): Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")
    fallback = (
        "Xin lỗi, tôi chưa thể hoàn tất yêu cầu này trong giới hạn xử lý cho phép. "
        "Bạn vui lòng thử lại với câu hỏi cụ thể hơn hoặc liên hệ trực tiếp phòng khám."
    )
    print(f"🏁 Final Answer (Safe Fallback): {fallback}")
    emit(type="guardrail", kind="max_iterations",
         text=f"Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")
    emit(type="final", text=fallback, steps=MAX_ITERATIONS, fallback=True)
    return fallback


# ==========================================================================
# 🚀 CẤP ĐỘ 4: AUTONOMOUS AGENT (Planning + Memory)
# --------------------------------------------------------------------------
# Cấp 3 ở trên phản ứng từng bước với đúng câu hỏi được đưa vào. Cấp 4 bọc thêm
# 2 thứ quanh vòng lặp đó:
#   1. PLANNING — trước khi chạy, LLM tự chia mục tiêu lớn thành các việc con.
#   2. MEMORY   — kết quả của việc con trước (mã lịch hẹn, khoa đã xác định)
#                 được ghi nhớ và bơm vào ngữ cảnh của việc con sau, nên Agent
#                 không đặt trùng lịch và không hỏi lại thông tin đã biết.
# Nhờ tách nhỏ, mỗi việc con có riêng ngân sách MAX_ITERATIONS — đây chính là
# cách Cấp 4 giải được test case #11 (đặt lịch 4 người) mà Cấp 3 bó tay.
# ==========================================================================

# Bắt mã lịch hẹn + thông tin đi kèm từ Observation của tool book_appointment
_BOOKING_RE = re.compile(
    r"Mã lịch hẹn:\s*(?P<code>\w+).*?"
    r"Bệnh nhân:\s*(?P<patient>[^\n]+).*?"
    r"Chuyên khoa:\s*(?P<specialty>[^\n]+).*?"
    r"Thời gian:\s*(?P<slot>[^\n]+)",
    re.S,
)
_SPECIALTY_RE = re.compile(r"Gợi ý chuyên khoa:\s*(?:Khoa\s*)?([^.]+)\.")


class AgentMemory:
    """
    Bộ nhớ dùng chung giữa các việc con của Autonomous Agent.

    Khác với `scratchpad` (chỉ sống trong 1 vòng lặp ReAct rồi mất), Memory sống
    xuyên suốt cả phiên: việc con số 3 vẫn đọc được mã lịch hẹn mà việc con số 1
    vừa đặt. Đây là điểm phân biệt Cấp 4 với Cấp 3.
    """

    def __init__(self):
        self.bookings = []   # [{"code","patient","specialty","slot"}]
        self.facts = []      # các dữ kiện ngắn Agent đã xác lập được

    def observe(self, observation: str):
        """Tự trích dữ kiện đáng nhớ từ một Observation bất kỳ."""
        m = _BOOKING_RE.search(observation)
        if m:
            booking = {k: v.strip() for k, v in m.groupdict().items()}
            if booking["code"] not in [b["code"] for b in self.bookings]:
                self.bookings.append(booking)
                return f"Đã ghi nhớ lịch hẹn {booking['code']} cho {booking['patient']}"

        m = _SPECIALTY_RE.search(observation)
        if m:
            fact = f"Chuyên khoa phù hợp đã xác định: {m.group(1).strip()}"
            if fact not in self.facts:
                self.facts.append(fact)
                return f"Đã ghi nhớ: {fact}"
        return None

    def as_context(self) -> str:
        """Kết xuất bộ nhớ thành đoạn văn bản để bơm vào đầu việc con kế tiếp."""
        if not self.bookings and not self.facts:
            return ""
        lines = ["[BỘ NHỚ CỦA PHIÊN LÀM VIỆC — dữ liệu đã xác lập ở các bước trước, "
                 "hãy dùng lại thay vì tra cứu/hỏi lại từ đầu]"]
        for b in self.bookings:
            lines.append(f"- Đã đặt lịch: mã {b['code']} | {b['patient']} | "
                         f"khoa {b['specialty']} | {b['slot']}")
        for f in self.facts:
            lines.append(f"- {f}")
        return "\n".join(lines) + "\n"

    def summary(self) -> str:
        if not self.bookings:
            return "Chưa đặt được lịch hẹn nào."
        return "; ".join(f"{b['code']} ({b['patient']} — khoa {b['specialty']}, {b['slot']})"
                         for b in self.bookings)


def plan_goal(user_query: str, provider) -> list:
    """
    Bước PLANNING: nhờ LLM chia mục tiêu lớn thành danh sách việc con.
    Trả về list các chuỗi việc con; nếu Planner lỗi thì trả về chính câu hỏi gốc
    (thoái lui an toàn về hành vi Cấp 3).
    """
    raw = provider.generate(user_query, system_prompt=PLANNER_PROMPT)
    subtasks = []
    for line in raw.splitlines():
        line = line.strip()
        m = re.match(r"^\d+[.)]\s*(.+)$", line)
        if m and len(m.group(1)) > 10:
            subtasks.append(m.group(1).strip())
    if not subtasks:
        return [user_query]
    return subtasks[:MAX_SUBTASKS]   # 🛡️ Guardrail: chặn Planner đẻ ra quá nhiều việc con


def run_autonomous_agent(user_query: str, provider, on_event=None):
    """
    Vòng đời Cấp 4: Plan ➔ (lặp) giải từng việc con bằng ReAct Loop ➔ tổng hợp.

    Args:
        on_event: cùng giao diện callback với run_react_agent, có thêm 2 loại sự kiện
            {"type": "plan", "subtasks": [...]} và {"type": "subtask", "index", "total", "text"}
            cùng {"type": "memory", "text": ...} khi bộ nhớ ghi nhận dữ kiện mới.
    Returns:
        dict: {"subtasks", "answers", "memory"}
    """
    def emit(**payload):
        if on_event:
            on_event(payload)

    print(f"\n🚀 [AUTONOMOUS AGENT] Mục tiêu: {user_query}")

    print("\n📋 --- GIAI ĐOẠN 1: PLANNING ---")
    subtasks = plan_goal(user_query, provider)
    for i, s in enumerate(subtasks, 1):
        print(f"   {i}. {s}")
    emit(type="plan", subtasks=subtasks)

    memory = AgentMemory()
    answers = []

    print("\n⚙️ --- GIAI ĐOẠN 2: THỰC THI TỪNG VIỆC CON (mỗi việc có ngân sách ReAct riêng) ---")
    for i, task in enumerate(subtasks, 1):
        print(f"\n╔══ Việc con {i}/{len(subtasks)}: {task}")
        emit(type="subtask", index=i, total=len(subtasks), text=task)

        # 💾 Bơm bộ nhớ vào đầu việc con — đây là chỗ Cấp 4 khác Cấp 3
        context = memory.as_context()
        scoped_query = f"{context}\nYêu cầu cần xử lý: {task}" if context else task

        def relay(ev):
            """Chuyển tiếp sự kiện của ReAct loop ra ngoài, đồng thời nhặt dữ kiện vào Memory."""
            if ev["type"] == "observation":
                noted = memory.observe(ev["text"])
                if noted:
                    print(f"💾 Memory: {noted}")
                    emit(type="memory", text=noted)
            emit(**ev)

        answer = run_react_agent(scoped_query, provider, on_event=relay)
        answers.append({"task": task, "answer": answer})

    print("\n🎯 --- GIAI ĐOẠN 3: TỔNG HỢP & TỰ ĐÁNH GIÁ ---")
    print(f"   Đã xử lý {len(subtasks)}/{len(subtasks)} việc con.")
    print(f"   💾 Bộ nhớ cuối phiên: {memory.summary()}")
    emit(type="done", subtasks=subtasks, answers=answers, memory_summary=memory.summary())

    return {"subtasks": subtasks, "answers": answers, "memory": memory}


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    # Cách chạy:
    #   python src/app.py                  -> chạy Test Case #3 trong test_cases.json (mặc định, demo nhanh)
    #   python src/app.py 5                -> chạy đúng Test Case có "id" = 5 trong test_cases.json
    #   python src/app.py all              -> chạy toàn bộ test_cases.json (dùng để gom log cho docs/trace_eval.md)
    #   python src/app.py all extra        -> chạy toàn bộ config/test_cases_extra.json (bộ 12 test bổ sung)
    #   python src/app.py 15 extra         -> chạy đúng Test Case "id" = 15 trong test_cases_extra.json
    dataset_arg = sys.argv[2] if len(sys.argv) > 2 else None
    dataset_file = "test_cases_extra.json" if dataset_arg == "extra" else "test_cases.json"

    tests = load_test_cases(dataset_file)
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/{dataset_file}\n")

    arg = sys.argv[1] if len(sys.argv) > 1 else None

    default_id = 3 if dataset_file == "test_cases.json" else tests[0]["id"]

    if arg == "all":
        selected_tests = tests
    else:
        try:
            test_id = int(arg) if arg else default_id
        except ValueError:
            test_id = default_id
        selected_tests = [t for t in tests if t["id"] == test_id] or [tests[0]]

    for test in selected_tests:
        print("\n" + "=" * 60)
        print(f"📌 TEST CASE #{test['id']} — {test['category']}")
        print("=" * 60)

        print("\n--- CHẠY TRÊN CHATBOT BASELINE ---")
        run_baseline_chatbot(test["question"], provider)

        print("\n--- CHẠY TRÊN REACT AGENT ---")
        run_react_agent(test["question"], provider)
