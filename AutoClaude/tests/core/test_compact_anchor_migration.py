"""compact prompt memory-anchor 移植測試（improving_80 W-80-1 / DEF-78-001 收尾 / RTM-80-1/2/3）。

驗證意圖（Rule 9）：本輪把純函式 build_compact_prompt 從 plugin 上移為 core 共享 SSOT，
並讓 production Kernel compact 路徑帶 MEMORY ANCHOR。這組測試守的是——
  (1) 移位後 core 與 plugin 取得**同一函式**（單一 SSOT，非各持一份重複碼 → 防 DRY 漂移）；
  (2) Kernel compact 路徑送出的 /compact 真的帶 anchor（task/global_goal），否則壓縮後
      任務記憶會流失、token 失控時收斂韌性下降——這正是上輪 §8 明標的誠實限制本質；
  (3) 無 anchor 素材（task=None）時逐字退回基本保留策略（零退化 fallback）。
若這些斷言能在 anchor 邏輯被改回靜態常數時失敗，即證明測試咬住的是行為意圖而非實作細節。
"""
from __future__ import annotations

from typing import Optional

from autoclaude.core._compact_prompt import build_compact_prompt as core_build
from autoclaude.core._token_compactor import perform_compact
from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import (
    ExecutionEvent,
    ExecutionEventKind,
    ExecutionOutput,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.token_guard.compactor import build_compact_prompt as plugin_build
from autoclaude.plugins.token_guard.policy import TokenGuardPlugin

# task=None 時 build_compact_prompt 應逐字退回的基本保留策略 prompt（即上輪 core-local
# _COMPACT_PROMPT 常數內容）——零退化 fallback 的 golden 文字。
_BASE_PROMPT = (
    "/compact\n"
    "請在壓縮時優先保留：\n"
    "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
    "2. 測試案例的名稱與期望行為\n"
    "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
    "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。"
)


class _CapturingExecutor:
    """記錄 execute 的 prompt（驗 anchor 落地）；不發 token 事件。"""

    def __init__(self):
        self.prompts: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        self.prompts.append(prompt)
        return ExecutionOutput(text="[compacted]", exit_code=0, completed=True)

    def send_interrupt(self, reason: str = "") -> bool:
        return False


class _SequencedExecutor:
    """每次 execute 依序回放一筆 token% 事件並記錄 prompt（Kernel compact 整合用）。"""

    def __init__(self, pcts: list[Optional[float]]):
        self._pcts = pcts
        self._i = 0
        self.prompts: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        pct = self._pcts[self._i] if self._i < len(self._pcts) else None
        self._i += 1
        self.prompts.append(prompt)
        if on_event is not None and pct is not None:
            on_event(ExecutionEvent(
                kind=ExecutionEventKind.TOKEN_PCT, payload={"pct": pct}, sequence=1,
            ))
        return ExecutionOutput(text="OK")


class _PassEvaluator:
    def evaluate(self, task, output):
        return None, "", 0


# ── RTM-80-1：上移 + re-export 單一 SSOT ───────────────────────────────────────

def test_core_and_plugin_share_single_callable():
    """RTM-80-1：plugin compactor.build_compact_prompt 即 core._compact_prompt 的同一物件
    （非各自定義 → 單一 SSOT，杜絕 DRY 漂移）。"""
    assert plugin_build is core_build


def test_relocated_function_outputs_identical():
    """RTM-80-1：同參數下，無論從 core 或 plugin 取得，輸出逐字一致。"""
    task = PlaybookTask(step_id="T07", name="實作驗證模組", prompt="do",
                        expected_output_regex=r"\[DONE\]")
    kwargs = dict(task=task, attempt=2, failure_summary="AssertionError x", global_goal="建立 API")
    assert core_build(**kwargs) == plugin_build(**kwargs)


# ── RTM-80-2：perform_compact 帶 anchor / 無 anchor fallback ─────────────────────

def test_perform_compact_with_task_carries_anchor():
    """RTM-80-2：給 task/global_goal → /compact prompt 含 MEMORY ANCHOR + [ACTIVE_TASK]
    + [SUCCESS_CONDITION] + [GLOBAL_GOAL]，壓縮後任務記憶得以存活。"""
    exec_ = _CapturingExecutor()
    task = PlaybookTask(step_id="T03", name="實作驗證模組", prompt="do",
                        expected_output_regex=r"\[DONE\]")
    perform_compact(exec_, step_id="T03", peak_pct=85.0,
                    task=task, attempt=1, global_goal="建立通過所有單元測試的 FastAPI 驗證模組")
    prompt = exec_.prompts[0]
    assert "=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===" in prompt
    assert "[ACTIVE_TASK] T03: 實作驗證模組" in prompt
    assert r"[SUCCESS_CONDITION] output must match: \[DONE\]" in prompt
    assert "[GLOBAL_GOAL] 建立通過所有單元測試的 FastAPI 驗證模組" in prompt


def test_perform_compact_threads_last_failure():
    """RTM-80-2：failure_summary 給定 → anchor 含 [LAST_FAILURE]（前次失敗背景隨壓縮存活）。"""
    exec_ = _CapturingExecutor()
    task = PlaybookTask(step_id="T05", name="step", prompt="do")
    perform_compact(exec_, step_id="T05", peak_pct=83.0, task=task,
                    failure_summary="line 1\nSyntaxError: invalid syntax at foo.py:12")
    prompt = exec_.prompts[0]
    assert "[LAST_FAILURE] SyntaxError: invalid syntax at foo.py:12" in prompt


def test_perform_compact_without_task_is_byte_identical_fallback():
    """RTM-80-2 零退化：task=None → 無 anchor、逐字等價上輪 core-local _COMPACT_PROMPT。"""
    exec_ = _CapturingExecutor()
    perform_compact(exec_, step_id="T01", peak_pct=80.0)
    assert exec_.prompts[0] == _BASE_PROMPT
    assert "MEMORY ANCHOR" not in exec_.prompts[0]


# ── RTM-80-3：Kernel production compact 路徑帶 anchor ───────────────────────────

def test_kernel_compact_path_sends_anchor_with_global_goal():
    """RTM-80-3：production Kernel ≥80% compact 觸發時，送出的 /compact 真的帶 anchor，
    且 [GLOBAL_GOAL] 取自 playbook.global_goal、[ACTIVE_TASK] 取自當前 task。"""
    executor = _SequencedExecutor(pcts=[85.0, 50.0])  # 步驟 85% 觸發 compact；compact 後 50%
    bus = EventBus()
    bus.register(TokenGuardPlugin())  # 真 plugin（compact=80 / halt=90）
    kernel = PlaybookKernel(executor, _PassEvaluator(), bus=bus)
    pb = Playbook(
        version="1.0", project="anchor-test",
        global_goal="建立通過所有單元測試的 FastAPI 驗證模組",
        global_invariants=GlobalInvariants(max_retries_per_step=2),
        tasks=[PlaybookTask(step_id="T01", name="實作 API", prompt="do",
                            expected_output_regex=r"\[DONE\]")],
    )
    result = kernel.run(pb)
    assert result.success is True
    # prompts[0]=步驟、prompts[1]=/compact（帶 anchor）
    assert len(executor.prompts) == 2
    compact_prompt = executor.prompts[1]
    assert compact_prompt.startswith("/compact")
    assert "=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===" in compact_prompt
    assert "[ACTIVE_TASK] T01: 實作 API" in compact_prompt
    assert "[GLOBAL_GOAL] 建立通過所有單元測試的 FastAPI 驗證模組" in compact_prompt
