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
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
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


# Regex tách dòng Action: ten_tool[tham_so_1, 'tham số 2'] (chấp nhận cả ngoặc tròn nếu LLM lỡ dùng)
_ACTION_LINE_RE = re.compile(r"^(\w+)[\[\(](.*)[\]\)]$")
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
                l_stripped = l.strip()
                if not l_stripped or l_stripped.startswith(("Thought:", "Action:", "Observation:")):
                    break
                extra_lines.append(l_stripped)
            if extra_lines:
                final_text = final_text + "\n" + "\n".join(extra_lines)
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


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent thật: gọi LLM sinh Thought -> Action, App tự thực thi
    Tool lấy Observation thật rồi đưa lại vào ngữ cảnh cho vòng suy luận kế tiếp.
    Có Guardrails: MAX_ITERATIONS chặn lặp vô hạn, chặn Repeated Action.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    scratchpad = f"Câu hỏi của bệnh nhân: {user_query}\n"
    last_action_signature = None
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")

        raw_response = provider.generate(scratchpad, system_prompt=REACT_SYSTEM_PROMPT)
        parsed = parse_agent_response(raw_response)

        if parsed["thought"]:
            print(f"🧠 Thought: {parsed['thought']}")

        if parsed["type"] == "final":
            print(f"🏁 Final Answer: {parsed['final_answer']}")
            return parsed["final_answer"]

        if parsed["type"] == "malformed":
            print(f"⚠️ Phản hồi không đúng định dạng ReAct (Thought/Action/Final Answer): {parsed['raw'][:200]}")
            scratchpad += (
                "Observation: LỖI ĐỊNH DẠNG - Phản hồi trước không đúng cú pháp. "
                "Bắt buộc trả lời theo đúng định dạng 'Thought: ...' rồi 'Action: ten_tool[tham_so]' "
                "hoặc 'Thought: ...' rồi 'Final Answer: ...'.\n"
            )
            continue

        # parsed["type"] == "action"
        tool_name, args = parsed["tool"], parsed["args"]
        print(f"🛠️ Action: {tool_name}{args}")

        action_signature = (tool_name, tuple(args))
        if action_signature == last_action_signature:
            print("🛡️ GUARDRAIL TRIGGERED (Repeated Action): Agent lặp lại đúng 1 Action liên tiếp — ngắt an toàn.")
            fallback = (
                "Xin lỗi, tôi chưa thể xử lý trọn vẹn yêu cầu này với dữ liệu hiện có của phòng khám. "
                "Bạn vui lòng thử mô tả rõ hơn hoặc liên hệ trực tiếp lễ tân để được hỗ trợ."
            )
            print(f"🏁 Final Answer (Safe Fallback): {fallback}")
            return fallback
        last_action_signature = action_signature

        obs = execute_tool(tool_name, args)
        print(f"👁️ Observation: {obs}")

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
    return fallback


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")

    # Cách chạy:
    #   python src/app.py         -> chạy Test Case #3 (mặc định, demo nhanh)
    #   python src/app.py 5       -> chạy đúng Test Case có "id" = 5
    #   python src/app.py all     -> chạy toàn bộ test suite (dùng để gom log cho docs/trace_eval.md)
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg == "all":
        selected_tests = tests
    else:
        try:
            test_id = int(arg) if arg else 3
        except ValueError:
            test_id = 3
        selected_tests = [t for t in tests if t["id"] == test_id] or [tests[2]]

    for test in selected_tests:
        print("\n" + "=" * 60)
        print(f"📌 TEST CASE #{test['id']} — {test['category']}")
        print("=" * 60)

        print("\n--- CHẠY TRÊN CHATBOT BASELINE ---")
        run_baseline_chatbot(test["question"], provider)

        print("\n--- CHẠY TRÊN REACT AGENT ---")
        run_react_agent(test["question"], provider)
