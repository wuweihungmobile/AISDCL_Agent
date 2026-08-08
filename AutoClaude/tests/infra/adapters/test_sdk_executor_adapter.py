"""test_sdk_executor_adapter.py — improving_68 W-68-2 mock 單元測試。

驗證 SdkExecutorAdapter（IExecutor，以 Claude Agent SDK 驅動 Claude Code）：
  R-68-2 串流訊息映射為 on_event 五事件 + ExecutionOutput
  R-68-3 can_use_tool 接注入的 allowlist predicate（安全閘不繞過、fail-closed）
  R-68-4 send_interrupt 可達（訊息邊界中斷 → completed=False）
  R-68-1 / R-70-1 act-first：執行期以 get_context_usage 驗排序，明確不安全則 fail-closed
    raise 硬擋（W-70-1 由 warn 升級）；無法判定維持 best-effort 放行

紀律：本輪沙箱無外網，**不做活體 A/B**（R-68-7 PENDING）；此處全以 mock SDK client
驗結構正確性。事件映射以「同名輕量假類別」測（adapter 按 type(msg).__name__ 解耦），
不依賴 SDK 具體 constructor；僅 can_use_tool 結果型別斷言需真 SDK（importorskip）。
"""
from __future__ import annotations

import pytest

pytest.importorskip("anyio")  # adapter.execute 走 anyio.run；無 anyio 整檔 skip
import anyio  # noqa: E402

from autoclaude.core.ports.executor import ExecutionEventKind  # noqa: E402
from autoclaude.infra.adapters.sdk_executor_adapter import (  # noqa: E402
    ActFirstOrderingError,
    SdkExecutorAdapter,
    build_tool_allowlist_predicate,
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

    async def __aenter__(self) -> FakeSdkClient:
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


def test_emit_token_pct_warns_when_percentage_missing(caplog):
    """W-82-3 / RTM-82-9 / DEF-81-001 SDK 支：percentage 缺失 → 不 emit TOKEN_PCT 但
    fail-loud warn（盲區可見，不再靜默跳過）。"""
    fake = FakeSdkClient(
        messages=[ResultMessage(is_error=False)],
        context_usage={"maxTokens": 200000},  # 無 percentage 欄（模擬 SDK 支盲區）
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    events, on_event = _collect_events()
    with caplog.at_level("WARNING", logger="autoclaude.infra.adapters.sdk_executor_adapter"):
        adapter.execute("x", on_event=on_event)
    assert ExecutionEventKind.TOKEN_PCT not in [e.kind for e in events]
    assert any("訊號源未產出" in r.getMessage() for r in caplog.records)


def test_emit_token_pct_emitted_when_percentage_present():
    """RTM-82-10：percentage 有值 → 照常 emit（零退化）。"""
    fake = FakeSdkClient(
        messages=[ResultMessage(is_error=False)],
        context_usage={"percentage": 33.0},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    events, on_event = _collect_events()
    adapter.execute("x", on_event=on_event)
    pct_evs = [e for e in events if e.kind == ExecutionEventKind.TOKEN_PCT]
    assert len(pct_evs) == 1 and pct_evs[0].payload == {"pct": 33.0}


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
# 🔴 R80 包 A（S3-05）：下面三支需要**真** `PermissionResult` 型別，故無法以假物件替代
# （用假型別就等於不驗那個 isinstance 斷言，而那正是它們的全部價值）。
# 它們此前用裸 `pytest.importorskip("claude_agent_sdk")`，產出的 skip 理由是 pytest 自動
# 生成的 `could not import 'claude_agent_sdk': …` ⇒ **不帶任何標籤**，落進 `untagged` 群，
# 而 `untagged` 的意思是「還沒有人說得出這支為什麼不跑」。實際上說得出來，而且說得很精確：
# 這個套件住在 `[sdk]` extra 裡，而 `tools/bootstrap_core.py` 的安裝 target 逐字是
# `.[dev,notifications,lint]` ⇒ **走 bootstrap 建立的環境結構上永遠拿不到它**，
# 不是「這台機器剛好沒裝」。改成具名 skipif ＋ `[TOOL-ABSENCE]` 標籤 ＋ 可直接複製的
# 安裝指令：分群從 untagged 移到 tool-absence（可歸零的那一半），理由本身也變成配方。
# 🔴 載具刻意仍是 `pytest.importorskip`（帶 `reason=`）而**不是**改寫成 `skipif` 裝飾器：
# 後者在 `skip_tag_policy._SITE_CLASS_CENSUS` 那張站點普查表上是**新的一個站點**
# （tool-absence 16→17），而那張表住在本包持有面之外的檔案裡 ⇒ 一個純粹的訊息改善會
# 連帶要求改別人的檔，並在改到之前讓根層閘門紅。`importorskip(..., reason=…)` 拿到
# 一模一樣的 runtime 效果、站點形態零變動——**選載具時要先問它會不會動到別人的判準面**。
_SDK_SKIP_REASON = (
    "[TOOL-ABSENCE] 需要 claude-agent-sdk（選配 `[sdk]` extra；本測試要真的 "
    "PermissionResultAllow／Deny 型別，換成假物件等於不驗那個 isinstance 斷言）。"
    "🔴 這不是「這台機器剛好沒裝」——tools/bootstrap_core.py 的安裝 target 是 "
    "`.[dev,notifications,lint]`，不含 sdk ⇒ 走 bootstrap 的環境一律拿不到。"
    "跑法：在 AutoClaude/ 執行 `uv pip install -e '.[sdk]'` 後重跑本檔"
)


def _require_sdk() -> None:
    pytest.importorskip("claude_agent_sdk", reason=_SDK_SKIP_REASON)


def test_can_use_tool_predicate_wired_and_consulted():
    _require_sdk()
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
    _require_sdk()

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
# W-69-2：build_tool_allowlist_predicate（config 驅動泛型 allowlist，deny-by-default）
# ─────────────────────────────────────────────────────────────────────
def test_sdk_tool_allowlist_defaults_to_none():
    # 零退化邊界：預設不設 allowlist → main.py 注入 can_use_tool=None（permission_mode 守門）
    assert AppConfig().executor.sdk_tool_allowlist is None


def test_build_predicate_allows_listed_denies_others():
    pred = build_tool_allowlist_predicate(["Read", "Grep"])
    assert pred("Read", {"path": "a"}) is True
    assert pred("Grep", {"pattern": "x"}) is True
    # deny-by-default：清單外工具一律不放行
    assert pred("Bash", {"command": "rm -rf /"}) is False
    assert pred("Write", {"path": "a"}) is False


def test_build_predicate_empty_list_denies_all():
    # 空 allowlist = 最嚴格（全 deny），含常見工具
    pred = build_tool_allowlist_predicate([])
    for name in ("Read", "Bash", "Write", "WebFetch"):
        assert pred(name, {}) is False


def test_build_predicate_injected_denies_unlisted_via_sdk_hook():
    """整合：注入 builder 產的 predicate → SDK hook 對清單外工具回 Deny（fail-closed 一致）。"""
    _require_sdk()
    pred = build_tool_allowlist_predicate(["Read"])  # 僅放行 Read
    fake = FakeSdkClient(messages=[ResultMessage()])
    captured: dict = {}
    adapter = SdkExecutorAdapter(
        AppConfig(), can_use_tool=pred, client_factory=_make_factory(fake, captured)
    )
    adapter.execute("x")
    hook = captured["can_use_tool"]

    import anyio
    from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

    assert isinstance(anyio.run(hook, "Read", {}, None), PermissionResultAllow)
    assert isinstance(anyio.run(hook, "Bash", {"command": "x"}, None), PermissionResultDeny)


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
# R-68-1 / R-70-1：act-first 執行期守門
#   W-70-1 升級：明確判定不安全 → fail-closed RAISE 硬擋（非僅 warn）；
#   安全 → 不擋正常完成；「無法判定」→ best-effort 放行不誤擋。
# ─────────────────────────────────────────────────────────────────────
def test_act_first_unsafe_raises_actfirst_error():
    # halt 90% * 200000 = 180000 ≥ autocompact 100000 → 不安全
    # 直接驗 _verify_act_first 拋 ActFirstOrderingError（突變核心：raise 改回 pass 即轉紅）
    fake = FakeSdkClient(
        messages=[ResultMessage()],
        context_usage={"maxTokens": 200000, "autoCompactThreshold": 100000},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    with pytest.raises(ActFirstOrderingError):
        anyio.run(adapter._verify_act_first, fake)
    assert adapter._act_first_safe is False


def test_act_first_unsafe_fails_closed_via_execute():
    # 端對端：不安全設定 → execute() fail-loud 回 completed=False / exit_code=1（不靜默完成）
    fake = FakeSdkClient(
        messages=[ResultMessage()],
        context_usage={"maxTokens": 200000, "autoCompactThreshold": 100000},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))

    out = adapter.execute("x")
    assert out.completed is False
    assert out.exit_code == 1
    assert adapter._act_first_safe is False
    # query 不應被送出（守門在 query 之前；硬擋阻止任務啟動）
    assert fake.query_prompts == []


def test_act_first_safe_does_not_raise():
    # halt 90% * 200000 = 180000 < autocompact 190000 → 安全 → 不擋，正常完成
    fake = FakeSdkClient(
        messages=[ResultMessage()],
        context_usage={"maxTokens": 200000, "autoCompactThreshold": 190000},
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))

    out = adapter.execute("x")
    assert adapter._act_first_safe is True
    assert out.completed is True
    assert fake.query_prompts == ["x"]


def test_act_first_missing_fields_does_not_raise():
    # 無 autocompact 門檻欄位 → 無法判定（_act_first_safe 維持 None）→ best-effort 放行不誤擋
    fake = FakeSdkClient(
        messages=[ResultMessage()], context_usage={"percentage": 10.0}
    )
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    out = adapter.execute("x")
    assert adapter._act_first_safe is None
    assert out.completed is True
    assert fake.query_prompts == ["x"]


def test_act_first_usage_exception_does_not_raise():
    # get_context_usage() 本身拋例外 → 無法判定（best-effort）→ 不誤擋，正常完成
    class _BoomClient(FakeSdkClient):
        async def get_context_usage(self) -> dict:
            raise RuntimeError("SDK context lookup failure")

    fake = _BoomClient(messages=[ResultMessage()])
    adapter = SdkExecutorAdapter(AppConfig(), client_factory=_make_factory(fake))
    out = adapter.execute("x")
    assert adapter._act_first_safe is None
    assert out.completed is True
    assert fake.query_prompts == ["x"]


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
