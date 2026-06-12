"""
建構傳給 Minimax 的 System Prompt 與 User Message。
僅服務 Playbook 模式：步驟失敗時諮詢 Minimax，由其產出修正 prompt。
"""
from __future__ import annotations

import os
import re
import subprocess

from ..utils.trace_context import propagate_to_subprocess_env

CORRECTION_SYSTEM_PROMPT = """\
你是 AutoClaude 的 Playbook 修正大腦。
當某個步驟的評估失敗時，你負責產生一個修正 Prompt，讓 AutoClaude 重新傳給 Claude Code 進行修正。

## 輸出規則（強制）
只輸出一個 JSON 物件，不得加前綴、說明或 Markdown 代碼區塊。
JSON Schema：
{
  "correction_prompt": "<傳給 Claude Code 的修正指令，必須包含錯誤資訊與明確修正要求>",
  "reasoning": "<決策依據，不超過 100 字>",
  "task_goal_summary": "<任務核心目標的 30 字以內摘要，僅在 retry_count=0 時填寫，其餘為 null>"
}

## 撰寫 correction_prompt 的原則
1. 明確引用錯誤日誌中的關鍵訊息（例如行號、assert 訊息）。
2. 告訴 Claude Code「哪裡錯了」以及「應如何修正」。
3. 若有 expected_output_regex，要求 Claude Code 確保輸出符合該 pattern。
4. 保持簡潔，不超過 500 字。
"""

# Gap-011-B / Gap-012-A/B/C：步驟動態修正 schema（僅在 allow_step_mutation=True 時附加到 system prompt）
_MUTATION_SCHEMA_SECTION = """
## 步驟動態修正（選填，僅在步驟設計本身有問題時使用）
若確認是步驟 prompt 本身設計不佳（過於寬泛/含糊導致多次失敗），可填入 step_mutation。
支援五種類型：
1. REVISE_CURRENT — 修改當前步驟的 prompt 定義（完整替換）：
{
  "step_mutation": {
    "mutation_type": "REVISE_CURRENT",
    "revised_prompt": "<新的步驟 prompt，必須完整>",
    "reasoning": "<為何需要修改步驟定義>"
  }
}
2. INJECT_AFTER — 在當前步驟後插入新的輔助步驟（用於補充後置工作）：
{
  "step_mutation": {
    "mutation_type": "INJECT_AFTER",
    "new_step_id": "<例如 T02_FIX>",
    "new_step_name": "<新步驟名稱>",
    "new_step_prompt": "<新步驟的完整 prompt>",
    "new_step_evaluator_command": "<驗證注入步驟成功的 shell 指令，例如 pytest tests/test_foo.py>",
    "new_step_expected_regex": "<輸出應符合的 regex，選填>",
    "new_step_max_retries": null,
    "reasoning": "<為何需要插入輔助步驟>"
  }
}
3. INJECT_BEFORE — 在當前步驟「之前」插入前置步驟，並立即執行（用於解決前提條件缺失，例如缺少 requirements.txt、環境未初始化）：
{
  "step_mutation": {
    "mutation_type": "INJECT_BEFORE",
    "new_step_id": "<例如 T01_PRE>",
    "new_step_name": "<前置步驟名稱>",
    "new_step_prompt": "<前置步驟的完整 prompt>",
    "new_step_evaluator_command": "<驗證前置步驟成功的 shell 指令，例如 pip show fastapi>",
    "new_step_expected_regex": "<輸出應符合的 regex，選填>",
    "new_step_max_retries": null,
    "reasoning": "<為何需要前置步驟>"
  }
}
4. GOTO_STEP — 跳回指定步驟重新執行（用於發現前序步驟輸出有誤，只允許向後跳轉，含 3 次防護上限）：
{
  "step_mutation": {
    "mutation_type": "GOTO_STEP",
    "goto_step_id": "<要跳回的步驟 step_id，必須是已完成的前序步驟>",
    "reasoning": "<為何需要重新執行該步驟>"
  }
}
5. DELETE_STEP — 刪除後續已確定冗餘的步驟（只能刪除當前步驟之後的步驟，每次最多一個）：
{
  "step_mutation": {
    "mutation_type": "DELETE_STEP",
    "delete_step_id": "<要刪除的步驟 step_id>",
    "reasoning": "<為何該步驟已冗餘>"
  }
}
6. SKIP_TO — 向前跳轉至指定步驟（跳過當前步驟之後、目標之前的所有步驟）：
   條件：目標必須在當前步驟之後，每個 step_id 最多 1 次 SKIP_TO：
{
  "step_mutation": {
    "mutation_type": "SKIP_TO",
    "skip_to_step_id": "<目標步驟 step_id，必須在當前步驟之後>",
    "skip_reason": "<被跳過步驟已隱性完成的說明>",
    "reasoning": "<為何可安全跳過中間步驟>"
  }
}
7. CONDITIONAL — Gap-021：條件式分支突變（依 shell exit code 選擇分支，結合兩種突變的情境自適應）：
   僅支援單一突變（不可出現於 batch_mutations 中）：
{
  "step_mutation": {
    "mutation_type": "CONDITIONAL",
    "condition_evaluator": "<shell 指令，exit 0 = 條件成立，exit 非0 = 條件不成立>",
    "true_mutation": { <條件成立時執行的突變，支援除 CONDITIONAL 外所有類型> },
    "false_mutation": { <條件不成立時執行的突變，可為 null> },
    "reasoning": "<為何需要依條件分支>"
  }
}
若無需修改步驟，請將 step_mutation 設為 null 或省略此欄位。
"""


def build_correction_system_prompt(allow_step_mutation: bool = False) -> str:
    """Gap-011-B：根據是否允許步驟變異，回傳對應的 system prompt。"""
    if allow_step_mutation:
        return CORRECTION_SYSTEM_PROMPT + _MUTATION_SCHEMA_SECTION
    return CORRECTION_SYSTEM_PROMPT

# Gap-007-D：策略指令字典（對應 STRATEGY_TYPES）
STRATEGY_PROMPTS: dict[str, str] = {
    "PINPOINT":  "修正最具體的錯誤訊息所指向的程式碼位置，不要大範圍修改。",
    "REWRITE":   "重寫失敗測試所對應的整個函式，不要修補，直接重寫以確保正確性。",
    "ADD_TYPES": "為所有相關函式增加完整的 Python 型別標注（type hints）和前置條件 assert，讓型別錯誤在執行前就能被發現。",
    "SPLIT":     "將複雜函式拆分為 2-3 個單一責任的子函式，讓每個子函式可獨立測試。",
    "SIMPLIFY":  "移除所有邊界條件處理和特殊情況，先讓核心邏輯通過，再逐步加回邊界處理。",
}


def build_file_state_snapshot(working_dir: str = ".", max_files: int = 8) -> str:
    """
    Gap-007-C：列出最近被修改的非測試 Python 檔案，提供基本狀態資訊。
    僅傳函式簽名層級的快照（不傳完整內容），避免 Token 過大。
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=working_dir, timeout=10,
            env=propagate_to_subprocess_env(dict(os.environ)),
        )
        if result.returncode != 0:
            return ""
        changed_files = [
            f for f in result.stdout.splitlines()
            if f.endswith(".py") and not f.startswith("test")
            and "test_" not in f
        ][:max_files]

        if not changed_files:
            return ""

        snapshot_lines = ["## 已修改的實作檔案（git diff HEAD）"]
        for fpath in changed_files:
            try:
                with open(fpath, encoding="utf-8") as f:
                    lines = f.readlines()
                funcs = [ln.strip() for ln in lines if ln.strip().startswith("def ")][:5]
                snapshot_lines.append(
                    f"- `{fpath}` ({len(lines)} 行)"
                    + (f" 函式: {', '.join(f.split('(')[0].replace('def ', '') for f in funcs)}" if funcs else "")
                )
            except OSError:
                snapshot_lines.append(f"- `{fpath}` (無法讀取)")
        return "\n".join(snapshot_lines) + "\n\n"
    except Exception:
        return ""


def build_correction_message(
    step_id: str,
    task_name: str,
    task_prompt: str,
    expected_regex: str | None,
    failure_reason: str,
    eval_output: str,
    retry_count: int,
    history_summary: str = "",
    convergence_trend: str = "",
    convergence_reasoning: str = "",
    strategy_hint: str = "",
    error_class: str = "unknown",
    task_goal_summary: str | None = None,  # Gap-010-B: 高重試時取代完整 task_prompt
    global_goal: str | None = None,         # Gap-011-A: 自治系統總目標
    mutation_history: list[str] | None = None,  # Gap-013-D: 本步驟已執行的突變歷史
    mutation_pressure: int = 0,                # Gap-032: 突變壓力等級 0-3（無效 correction 累計次數）
    preferences_section: str = "",             # F-C1: 使用者偏好區段（PreferenceMemoryPlugin 產出）
) -> str:
    mutation_history = mutation_history or []
    key_lines = _extract_key_error_lines(eval_output, max_lines=20)
    key_lines_text = "".join(key_lines) if key_lines else eval_output[:800]

    # Gap-011-A：系統總目標（注入訊息頂端，讓修正決策對齊整體目標）
    goal_section = f"## 系統總目標\n{global_goal}\n\n" if global_goal else ""

    # Gap-013-D：突變歷史（讓 Minimax 知道本次執行已嘗試過哪些突變，避免重複提議）
    mutation_section = (
        "## 本次執行的突變歷史（含前序步驟）\n"
        + "\n".join(f"- {m}" for m in mutation_history) + "\n\n"
    ) if mutation_history else ""

    # Gap-032：突變壓力提示（無效 correction 累計後，強化 step_mutation 建議文字）
    mutation_pressure_section = ""
    if mutation_pressure >= 1:
        _pressure_labels = {
            1: "⚠️ 注意：已有 1 次 correction 無效，建議考慮 step_mutation。",
            2: "⚠️ 強烈建議：已有 2 次 correction 無效，請優先使用 INJECT_BEFORE 或 REVISE_CURRENT。",
            3: "🚨 緊急：已有 3+ 次 correction 無效，必須使用 step_mutation，禁止再次輸出純 correction_prompt。",
        }
        mutation_pressure_section = f"\n> {_pressure_labels[min(mutation_pressure, 3)]}\n\n"

    context_hint = ""
    if convergence_trend in ("stuck", "diverging", "oscillating", "worsening", "assertion_baseline_mismatch") and convergence_reasoning:
        context_hint = (
            f"\n> ⚠️ 收斂評估（{convergence_trend}）：{convergence_reasoning}\n"
            "請嘗試完全不同的修正策略。\n"
        )

    strategy_section = f"\n> 🔄 **策略切換指令**：{strategy_hint}\n" if strategy_hint else ""
    test_file_hint = _detect_test_file_error_hint(eval_output)
    assertion_hint = _detect_assertion_test_error_hint(eval_output, retry_count)  # Gap-008-C
    error_class_hint = _get_error_class_hint(error_class)
    history_section = f"{history_summary}\n\n" if history_summary else ""
    # Gap-007-C：注入當前檔案狀態快照（Minimax 對 Claude Code 行動的可見性）
    file_snapshot = build_file_state_snapshot()

    # Gap-010-B：高重試時漸進式壓縮 task_prompt（retry >= 3 且有摘要時改用摘要）
    if retry_count >= 3 and task_goal_summary:
        task_context = f"## 任務目標（摘要）\n{task_goal_summary}\n\n"
    else:
        task_context = f"## 原始 Prompt（前 600 字）\n{task_prompt[:600]}\n\n"

    return (
        f"{goal_section}"
        # F-C1：使用者偏好插於總目標後、失敗細節前（ADR-AGT-003 L3 唯讀注入）
        f"{preferences_section}"
        f"## 失敗步驟\n{step_id}: {task_name}\n\n"
        f"{task_context}"
        f"{file_snapshot}"
        f"## 期望輸出 Regex\n{expected_regex or '(無)'}\n\n"
        f"## 失敗原因\n{failure_reason}\n\n"
        f"## 關鍵錯誤行（萃取）\n{key_lines_text}\n\n"
        f"{test_file_hint}"
        f"{assertion_hint}"
        f"{error_class_hint}"
        f"{mutation_section}"
        f"{mutation_pressure_section}"
        f"{history_section}"
        f"{context_hint}"
        f"{strategy_section}"
        f"## 已重試次數\n{retry_count}\n\n"
        "請輸出修正 JSON。"
    )


def _get_error_class_hint(error_class: str) -> str:
    """根據錯誤語義分類，提供對應的 Minimax 修正提示。"""
    hints = {
        "syntax": "\n> 💡 錯誤類型：語法錯誤（SyntaxError/IndentationError）。請直接修正語法，不需要邏輯重構。\n\n",
        "import": "\n> 💡 錯誤類型：Import 錯誤。請優先檢查 requirements.txt 和 import 語句是否正確。\n\n",
        "type": "\n> 💡 錯誤類型：型別錯誤（TypeError/AttributeError）。請確認函式簽名和呼叫端參數是否匹配。\n\n",
        "environment": "\n> 💡 錯誤類型：環境錯誤（FileNotFoundError/PermissionError）。此類錯誤通常需要人工介入設定環境。\n\n",
    }
    return hints.get(error_class, "")


def _detect_test_file_error_hint(eval_output: str) -> str:
    """若輸出疑似測試檔錯誤（Attempt 0 早期警示），生成強調提示給 Minimax。

    雙模式偵測（Gap-006-C 修復）：
    - 模式 1：同行匹配（test_foo.py 和錯誤類型在同一行）
    - 模式 2：跨行匹配（ERROR collecting tests/test_foo.py\\n  SyntaxError）
    """
    same_line_pattern = re.compile(
        r'(?:test_\w+|\w+_test)\.py.*(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)',
        re.IGNORECASE,
    )
    test_file_pattern = re.compile(r'(?:test_\w+|\w+_test)\.py', re.IGNORECASE)
    error_type_pattern = re.compile(
        r'(?:SyntaxError|ImportError|NameError|ModuleNotFoundError)', re.IGNORECASE,
    )
    has_hint = bool(
        same_line_pattern.search(eval_output) or
        (test_file_pattern.search(eval_output) and error_type_pattern.search(eval_output))
    )
    if has_hint:
        return (
            "\n> ⚠️ **注意**：錯誤訊息指向測試檔（`test_*.py` 或 `*_test.py`）。"
            "請優先判斷：這是**測試檔本身的錯誤**（應修正測試檔）"
            "還是**被測程式的錯誤**（應修正實作檔）？"
            "在 correction_prompt 中明確說明你的判斷。\n\n"
        )
    return ""


def _detect_assertion_test_error_hint(eval_output: str, retry_count: int) -> str:
    """
    Gap-008-C：若 AssertionError 在 test_ 檔案中且已重試 >= 2 次，生成語意警告。
    要求 Minimax 在 correction_prompt 中明確聲明判斷：修實作 vs. 修測試期望值。
    """
    if retry_count < 2:
        return ""
    assertion_in_test = re.compile(
        r'(?:test_\w+|\w+_test)\.py.*AssertionError|AssertionError.*(?:test_\w+|\w+_test)\.py',
        re.IGNORECASE,
    )
    if not assertion_in_test.search(eval_output):
        return ""
    assert_values = re.compile(r'assert\s+(\S+)\s+==\s+(\S+)', re.IGNORECASE)
    m = assert_values.search(eval_output)
    values_hint = f"（比較：{m.group(1)} vs {m.group(2)}）" if m else ""
    return (
        f"\n> ⚠️ **語意測試警告** {values_hint}：已重試 {retry_count} 次，"
        "AssertionError 持續發生於測試檔中。\n"
        "請在 correction_prompt 中明確聲明你的判斷：\n"
        "A) **實作邏輯錯誤**（assert 的實際值 wrong）→ 修改實作\n"
        "B) **測試期望值錯誤**（assert 的期望值 wrong）→ 修改測試\n"
        "若判斷為 B，correction_prompt 必須包含修改測試檔的指令。\n\n"
    )


def _extract_key_error_lines(eval_output: str, max_lines: int = 20) -> list[str]:
    """
    從完整 eval_output 中萃取錯誤關鍵行（ERROR / FAILED / SyntaxError / assert 等）。
    當匹配行 > max_lines 時，保留前 5 行（整體概覽）+ 後 15 行（根因通常在末尾）。
    """
    pattern = re.compile(
        r'.*(ERROR|FAILED|SyntaxError|NameError|ImportError|AssertionError|'
        r'ModuleNotFoundError|TypeError|ValueError|assert|Traceback).*',
        re.IGNORECASE,
    )
    key = [ln + "\n" for ln in eval_output.splitlines() if pattern.search(ln)]
    if len(key) <= max_lines:
        return key
    # 保留前 5 行（整體概覽）+ 後 15 行（根因通常在末尾）
    head = key[:5]
    tail = key[-(max_lines - 5):]
    return head + ["  ... (中間部分省略) ...\n"] + tail


# ──────────────────────────────────────────────
# Gap-014-D：全局目標驗證 System Prompt
# ──────────────────────────────────────────────

GOAL_VALIDATION_SYSTEM_PROMPT = """\
你是 AutoClaude 的全局目標驗證大腦（Gap-014）。
當所有 Playbook 步驟執行完畢時，你負責判斷這些步驟的組合是否真正達成了系統總目標。

## 輸出規則（強制）
只輸出一個 JSON 物件，不得加前綴、說明或 Markdown 代碼區塊。
JSON Schema：
{
  "is_achieved": <true 表示目標已達成，false 表示存在缺口>,
  "completion_prompt": "<未達成時，傳給 Claude Code 的補完指令（300 字以內）；達成時為空字串>",
  "gap_analysis": "<未達成時，分析具體缺口（不超過 100 字）；達成時為空字串>",
  "suggested_evaluator": "<未達成時，建議用於驗證補完步驟是否成功的 shell 指令，例如 pytest tests/integration/ -v；達成時為 null>"
}

## 判斷原則
1. 各步驟局部通過測試 ≠ 全局目標達成。要判斷各步驟產出的整合一致性。
2. 若步驟間存在介面不相容、依賴缺失、整合邏輯缺口，判斷為未達成。
3. 若所有步驟的產出已自洽且符合 global_goal 描述，判斷為達成。
4. 若信息不足以判斷（步驟記錄太少），傾向判斷為達成（避免假陽性阻斷）。
"""

EVOLUTION_SYSTEM_PROMPT = """\
你是 AutoClaude 的 Playbook 演化大腦（Gap-016）。
當一個步驟達到 ESCALATION 時，你負責分析失敗根因，提議最佳的 Playbook 結構演化策略。

## 輸出規則（強制）
只輸出一個 JSON 物件，不得加前綴、說明或 Markdown 代碼區塊。
JSON Schema：
{
  "evolution_type": "<INJECT_STEP | SPLIT_STEP | REVISE_EVALUATOR>",
  "reasoning": "<演化策略選擇理由，不超過 100 字>",
  "new_step_id": "<INJECT_STEP 必填：新步驟 ID，例如 T01_PRE>",
  "new_step_name": "<INJECT_STEP 必填：新步驟名稱>",
  "new_step_prompt": "<INJECT_STEP 必填：新步驟的完整 prompt（明確、可執行）>",
  "split_context_bridge": "<SPLIT_STEP 必填：Part B 的前置 context 摘要（說明 Part A 已完成了什麼）>",
  "revised_evaluator": "<REVISE_EVALUATOR 必填：修改後的 evaluator_command>"
}

## 演化策略選擇原則
- INJECT_STEP：適合「缺少前提條件（環境、依賴）」或「測試檔本身有問題」的情況
- SPLIT_STEP：適合「步驟 prompt 過長/複雜導致 Claude Code 無法同時處理所有要求」的情況
- REVISE_EVALUATOR：適合「evaluator_command 本身設計不佳（誤報失敗）」的情況
"""


def build_goal_validation_message(
    global_goal: str,
    step_summary: str,
    playbook_project: str,
    code_state_snapshot: str = "",  # Gap-023-A：程式碼檔案狀態快照（語意正確性輔助判斷）
) -> str:
    """Gap-014-D / Gap-023-A：組裝全局目標驗證的 user message（含程式碼快照）。"""
    code_section = f"## 當前程式碼狀態快照\n{code_state_snapshot}\n\n" if code_state_snapshot else ""
    return (
        f"## 專案\n{playbook_project}\n\n"
        f"## 系統總目標\n{global_goal}\n\n"
        f"## 已完成的步驟記錄（最近 20 筆）\n{step_summary}\n\n"
        f"{code_section}"
        "請判斷以上步驟的組合是否真正達成了系統總目標，輸出驗證 JSON。"
    )


def build_evolution_message(
    step_id: str,
    step_name: str,
    step_prompt: str,
    failure_summary: str,
    escalation_reasoning: str,
    global_goal: str | None = None,  # Gap-022-A：注入總目標，防止演化步驟語意漂移
) -> str:
    """Gap-016 / Gap-022-A：組裝 AI 驅動演化提議的 user message（含 global_goal 約束）。"""
    goal_section = f"## 系統總目標（演化提議必須對齊此目標）\n{global_goal}\n\n" if global_goal else ""
    return (
        f"{goal_section}"
        f"## 失敗步驟\n{step_id}: {step_name}\n\n"
        f"## 步驟 Prompt（前 600 字）\n{step_prompt[:600]}\n\n"
        f"## ESCALATION 分析\n{escalation_reasoning}\n\n"
        f"## 失敗歷史摘要\n{failure_summary}\n\n"
        "請分析失敗根因，提議最佳的 Playbook 演化策略，輸出演化 JSON。"
    )
