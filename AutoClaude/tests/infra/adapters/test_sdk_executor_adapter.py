"""test_sdk_executor_adapter.py — improving_68 W-68-2 mock 單元測試。

驗證 SdkExecutorAdapter（IExecutor，以 Claude Agent SDK 驅動 Claude Code）：
  R-68-2 串流訊息映射為 on_event 五事件 + ExecutionOutput
  R-68-3 can_use_tool 接注入的 allowlist predicate（安全閘不繞過、fail-closed）
  R-68-4 send_interrupt 可達（訊息邊界中斷 → completed=False）
  R-68-1 act-first：執行期以 get_context_usage 驗排序，不安全則 warn（fail-closed 不阻斷）

紀律：本輪沙箱無外網，**不做活體 A/B**（R-68-7 PENDING）；此處全以 mock SDK client
驗結構正確性。事件映射以「同名輕量假類別」測（adapter 按 type(msg).__name__ 解耦），
不依賴 SDK 具體 constructor；僅 can_use_tool 結果型別斷言需真 SDK（importorskip）。
"""
from __future__ import annotations

import pytest

pytest.importorskip("anyio")  # adapter.execute 走 anyio.run；無 anyio 整檔 skip

from autoclaude.core.ports.executor import ExecutionEventKind  # noqa: E402
from autoclaude.infra.adapters.sdk_executor_adapter import (  # noqa: E402
    SdkExecutorAdapter,
)
from autoclaude.utils.config import AppConfig  # noqa: E402


# ── 同名假 SDK 訊息（adapter 按 class name 映射，與真 SDK constructor 解耦）──
class TextBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class ToolUseBlock:
    def __init__(self, name: str, input: dict) -> None:  # noqa: A002 對齊 SDK 欄位名
        self.name = name
        self.input = input


class AssistantMessage:
    def __init__(self, content: list) -> None:
        self.content = content


class ResultMessage:
    def __init__(self, is_error: bool = False) -> None:
        self.is_error = is_error


class FakeSdkClient:
    """mock ClaudeSDKClient：async context manager + query/receive_response/
    get_context_usage/interrupt。"""

    def __init__(self, messages: list, *, context_usage: dict | None = None) -> None:
        self._messages = messages
        self._context_usage = context_usage or {}
        self.interrupt_called = False
        self.query_prompts: list[str] = []

    async def __aenter__(self) -> "FakeSdkClient":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def query(self, prompt: str) -> None:
        self.query_prompts.append(prompt)

    async def receive_response(self):
        for m in self._messages:
            yield m

    async def get_context_usage(self) -> dict:
        return dict(self._context_usage)

    async def interrupt(self) -> None:
        self.interrupt_called = True


def _make_factory(fake: FakeSdkClient, captured: dict | None = None):
    """回傳 client_factory：捕獲 options kwargs（供 can_use_tool wiring 斷言）。"""

    def _factory(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return fake

    return _factory


def _collect_events():
    events: list = []
    return events, (lambda e: events.append(e))


# ─────────────────────────────────────────────────────────────────────
# R-68-2：串流訊息映射
# ─────────────────────────────────────────────────────────────────────
def test_event_mapping_full_stream():
    fake = FakeSdkClient(
        messages=[
            AssistantMessage(
                content=[
                    TextBlock("hello "),
                    ToolUseBlock(name="Read", input={"path": "x.py"}),
                    TextBlock("world"),
                ]
            ),
            ResultMessage(is_error=False),
        ],
        context_usage={"percentage": 42.5, "maxTokens": 200000},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    events, on_event = _collect_events()

    out = adapter.execute("do it", label="T01", on_event=on_event)

    # ExecutionOutput
    assert out.text == "hello world"
    assert out.exit_code == 0
    assert out.completed is True
    assert fake.query_prompts == ["do it"]

    kinds = [e.kind for e in events]
    # partial_output（兩個 TextBlock）+ tool_use + token_pct + completion
    assert kinds.count(ExecutionEventKind.PARTIAL_OUTPUT) == 2
    assert ExecutionEventKind.TOOL_USE in kinds
    assert ExecutionEventKind.TOKEN_PCT in kinds
    assert kinds[-1] == ExecutionEventKind.COMPLETION

    tool_ev = next(e for e in events if e.kind == ExecutionEventKind.TOOL_USE)
    assert tool_ev.payload == {"tool": "Read", "args": {"path": "x.py"}}
    pct_ev = next(e for e in events if e.kind == ExecutionEventKind.TOKEN_PCT)
    assert pct_ev.payload == {"pct": 42.5}
    comp = events[-1]
    assert comp.payload["exit_code"] == 0
    assert comp.payload["completed"] is True
    assert comp.payload["text_len"] == len("hello world")


def test_result_message_is_error_maps_exit_code_1():
    fake = FakeSdkClient(messages=[ResultMessage(is_error=True)])
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    out = adapter.execute("x")
    assert out.exit_code == 1
    # completed 仍 True（正常收到終態，只是 is_error）；exit_code 才是錯誤訊號
    assert out.completed is True


# ─────────────────────────────────────────────────────────────────────
# R-68-3：can_use_tool 接注入 allowlist（安全閘不繞過、fail-closed）
# ─────────────────────────────────────────────────────────────────────
def test_can_use_tool_predicate_wired_and_consulted():
    pytest.importorskip("claude_agent_sdk")  # 需真 PermissionResult 型別
    consulted: list = []

    def predicate(tool_name: str, tool_input: dict) -> bool:
        consulted.append((tool_name, tool_input))
        return tool_name == "Read"  # 只放行 Read

    fake = FakeSdkClient(messages=[ResultMessage()])
    captured: dict = {}
    adapter = SdkExecutorAdapter(
        AppConfig(), can_use_tool=predicate, client_factory=_make_factory(fake, captured)
    )
    adapter.execute("x")  # 觸發 factory，捕獲 can_use_tool hook

    hook = captured.get("can_use_tool")
    assert hook is not None, "can_use_tool hook 未傳入 SDK options"

    import anyio
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    allow = anyio.run(hook, "Read", {"path": "a"}, None)
    deny = anyio.run(hook, "Bash", {"command": "rm -rf /"}, None)

    assert isinstance(allow, PermissionResultAllow)
    assert isinstance(deny, PermissionResultDeny)
    # predicate 確實被諮詢（兩次工具呼叫）
    assert consulted == [("Read", {"path": "a"}), ("Bash", {"command": "rm -rf /"})]


def test_can_use_tool_predicate_exception_fail_closed():
    pytest.importorskip("claude_agent_sdk")

    def boom(tool_name: str, tool_input: dict) -> bool:
        raise RuntimeError("predicate 故障")

    fake = FakeSdkClient(messages=[ResultMessage()])
    captured: dict = {}
    adapter = SdkExecutorAdapter(
        AppConfig(), can_use_tool=boom, client_factory=_make_factory(fake, captured)
    )
    adapter.execute("x")
    hook = captured["can_use_tool"]

    import anyio
    from claude_agent_sdk import PermissionResultDeny

    result = anyio.run(hook, "Read", {}, None)
    assert isinstance(result, PermissionResultDeny), "predicate 例外必須 fail-closed deny"


def test_no_predicate_means_no_hook_passed():
    fake = FakeSdkClient(messages=[ResultMessage()])
    captured: dict = {}
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake, captured))
    adapter.execute("x")
    # 未注入 predicate → can_use_tool=None（交由 SDK permission_mode 守門）
    assert captured.get("can_use_tool") is None


# ─────────────────────────────────────────────────────────────────────
# R-68-4：send_interrupt 可達
# ─────────────────────────────────────────────────────────────────────
def test_send_interrupt_when_not_running_returns_false():
    fake = FakeSdkClient(messages=[ResultMessage()])
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    assert adapter.send_interrupt("no-op") is False  # 無執行中


def test_interrupt_at_message_boundary_sets_completed_false():
    fake = FakeSdkClient(
        messages=[
            AssistantMessage(content=[TextBlock("partial")]),  # 第 1 則：觸發中斷請求
            AssistantMessage(content=[TextBlock("should-not-arrive")]),
            ResultMessage(),
        ]
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))

    def on_event(e):
        # 收到第一個 partial_output 後請求中斷（模擬 Coordinator 跨步呼叫）
        if e.kind == ExecutionEventKind.PARTIAL_OUTPUT and not fake.interrupt_called:
            assert adapter.send_interrupt("token halt") is True

    out = adapter.execute("x", on_event=on_event)
    assert fake.interrupt_called is True
    assert out.completed is False
    # 第二則 TextBlock 不應被累積（中斷在其邊界生效）
    assert "should-not-arrive" not in out.text
    assert out.text == "partial"


# ─────────────────────────────────────────────────────────────────────
# R-68-1：act-first 執行期守門（不安全 warn、安全靜默；皆不阻斷執行）
# ─────────────────────────────────────────────────────────────────────
def test_act_first_unsafe_warns(caplog):
    # halt 90% * 200000 = 180000 ≥ autocompact 100000 → 不安全
    fake = FakeSdkClient(
        messages=[ResultMessage()],
        context_usage={"maxTokens": 200000, "autoCompactThreshold": 100000},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    import logging

    with caplog.at_level(logging.WARNING):
        adapter.execute("x")
    assert adapter._act_first_safe is False
    assert any("act-first" in r.message for r in caplog.records)


def test_act_first_safe_no_warn(caplog):
    # halt 90% * 200000 = 180000 < autocompact 190000 → 安全
    fake = FakeSdkClient(
        messages=[ResultMessage()],
        context_usage={"maxTokens": 200000, "autoCompactThreshold": 190000},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    import logging

    with caplog.at_level(logging.WARNING):
        adapter.execute("x")
    assert adapter._act_first_safe is True
    assert not any("act-first" in r.message for r in caplog.records)


def test_act_first_skipped_when_usage_missing_fields():
    # 無 autocompact 門檻欄位 → 不判定（_act_first_safe 維持 None），不誤報
    fake = FakeSdkClient(
        messages=[ResultMessage()], context_usage={"percentage": 10.0}
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    adapter.execute("x")
    assert adapter._act_first_safe is None


# ─────────────────────────────────────────────────────────────────────
# R-68-5：後端切換預設 pty，零行為變更
# ─────────────────────────────────────────────────────────────────────
def test_executor_config_defaults_to_pty():
    assert AppConfig().executor.backend == "pty"


def test_both_executors_structurally_satisfy_iexecutor():
    # SdkExecutorAdapter 與 PtyExecutor 同樣具備 IExecutor 契約方法（execute/send_interrupt）
    from autoclaude.infra.adapters.pty_executor import PtyExecutor

    for cls in (SdkExecutorAdapter, PtyExecutor):
        assert callable(getattr(cls, "execute", None))
        assert callable(getattr(cls, "send_interrupt", None))
