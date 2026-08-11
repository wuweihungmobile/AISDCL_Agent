"""F-A2 ToolInvocationPort + allowlist 安全閘測試（SRD_AGT_Phase3_Autonomy.md §4）。

驗收項對應：
  - allowlist 外呼叫被拒並留審計 log
  - allowlist 內呼叫放行 + 審計（audit_id 關聯）
  - send_message 經 notifier 委派（不開放任意端點、不 import plugin）
  - flag-off 零行為變更（enabled=False 不發任何外部 I/O）
"""
from __future__ import annotations

from autoclaude.core.ports.tool_invocation import (
    IToolInvocation,
    ToolRequest,
)
from autoclaude.infra.adapters.tool_invocation_adapter import ToolInvocationAdapter
from autoclaude.utils.config import AppConfig, ToolInvocationConfig


class _RecordingObs:
    """捕捉 record_event 的假 IObservabilityPort。"""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def emit_counter(self, name, value=1, tags=None):
        pass

    def emit_histogram(self, name, value, tags=None):
        pass

    def start_span(self, name, tags=None):
        raise NotImplementedError

    def record_event(self, name, attributes=None):
        self.events.append((name, dict(attributes or {})))


class _SpyNotifier:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def __call__(self, title, message, *a, **k):
        self.calls.append((title, message))


# ── config 預設 ─────────────────────────────────────────────
def test_config_default_deny():
    """ToolInvocationConfig 預設 enabled=False、allowlist 空。"""
    cfg = ToolInvocationConfig()
    assert cfg.enabled is False
    assert cfg.allowlist == []
    # 掛載於 AppConfig
    assert AppConfig().tool_invocation.enabled is False


def test_adapter_satisfies_protocol():
    assert isinstance(ToolInvocationAdapter(), IToolInvocation)


# ── 預設 deny / flag-off 零行為變更 ─────────────────────────
def test_flag_off_denies_and_no_io():
    """enabled=False → 全拒、不發任何外部 I/O（notifier 零呼叫）。"""
    obs, spy = _RecordingObs(), _SpyNotifier()
    adapter = ToolInvocationAdapter(
        enabled=False, allowlist=["example.com"], observability=obs, notifier=spy
    )
    res = adapter.invoke(ToolRequest("http_request", "https://example.com/api"))
    assert res.allowed is False and res.ok is False
    assert res.data["reason"] == "denied_by_allowlist"
    assert spy.calls == []  # 零外部 I/O


def test_empty_allowlist_denies_even_if_enabled():
    """enabled=True 但 allowlist 空 → 仍全拒。"""
    adapter = ToolInvocationAdapter(enabled=True, allowlist=[])
    res = adapter.invoke(ToolRequest("web_search", "https://example.com"))
    assert res.allowed is False


def test_enabled_must_be_strict_true():
    """非嚴格 True（如 truthy 物件）不應啟用（防 Mock truthy）。"""
    adapter = ToolInvocationAdapter(enabled=object(), allowlist=["example.com"])  # type: ignore[arg-type]
    res = adapter.invoke(ToolRequest("web_search", "https://example.com"))
    assert res.allowed is False


# ── allowlist 比對 ──────────────────────────────────────────
def test_not_in_allowlist_denied_with_audit():
    """不在 allowlist → 拒絕，且審計 log 落筆 allowed=False。"""
    obs = _RecordingObs()
    adapter = ToolInvocationAdapter(
        enabled=True, allowlist=["good.com"], observability=obs
    )
    res = adapter.invoke(ToolRequest("http_request", "https://evil.com/x"))
    assert res.allowed is False
    assert len(obs.events) == 1
    name, attrs = obs.events[0]
    assert name == "tool_invocation"
    assert attrs["allowed"] is False
    assert attrs["target"] == "https://evil.com/x"
    assert attrs["audit_id"] == res.audit_id  # 審計關聯


def test_in_allowlist_allowed_with_audit():
    """在 allowlist → 放行（web/http 預設 stub），審計 log allowed=True + audit_id 關聯。"""
    obs = _RecordingObs()
    adapter = ToolInvocationAdapter(
        enabled=True, allowlist=["example.com"], observability=obs
    )
    res = adapter.invoke(ToolRequest("web_search", "https://example.com/search?q=x"))
    assert res.allowed is True
    assert res.data.get("stub") is True  # 預設 no-op stub，無真實 I/O
    assert obs.events[0][1]["allowed"] is True
    assert obs.events[0][1]["audit_id"] == res.audit_id


def test_subdomain_match():
    """allowlist domain 命中子域（host 結尾於 .allow）。"""
    adapter = ToolInvocationAdapter(enabled=True, allowlist=["example.com"])
    res = adapter.invoke(ToolRequest("http_request", "https://api.example.com/v1"))
    assert res.allowed is True


def test_partial_domain_not_matched():
    """避免 'notexample.com' 誤命中 'example.com'。"""
    adapter = ToolInvocationAdapter(enabled=True, allowlist=["example.com"])
    res = adapter.invoke(ToolRequest("http_request", "https://notexample.com/x"))
    assert res.allowed is False


def test_unknown_kind_denied():
    adapter = ToolInvocationAdapter(enabled=True, allowlist=["example.com"])
    res = adapter.invoke(ToolRequest("rm_rf", "https://example.com"))
    assert res.allowed is False


# ── send_message 委派 notification ──────────────────────────
def test_send_message_delegates_to_notifier():
    """放行的 send_message → 委派 notifier（延伸既有 notification 通道）。"""
    spy = _SpyNotifier()
    adapter = ToolInvocationAdapter(
        enabled=True, allowlist=["alerts"], notifier=spy
    )
    res = adapter.invoke(
        ToolRequest("send_message", "alerts", {"title": "T", "message": "M"})
    )
    assert res.allowed is True and res.ok is True
    assert spy.calls == [("T", "M")]


def test_send_message_denied_not_in_allowlist():
    """send_message 通道不在 allowlist → 拒絕、notifier 零呼叫。"""
    spy = _SpyNotifier()
    adapter = ToolInvocationAdapter(enabled=True, allowlist=["alerts"], notifier=spy)
    res = adapter.invoke(ToolRequest("send_message", "spam", {"message": "x"}))
    assert res.allowed is False
    assert spy.calls == []


def test_url_without_host_denied():
    """target 無 host（如 file:// / 空字串）→ 解析不出 domain → 拒絕（不誤放行）。"""
    adapter = ToolInvocationAdapter(enabled=True, allowlist=["example.com"])
    assert adapter.invoke(ToolRequest("http_request", "file:///etc/passwd")).allowed is False
    assert adapter.invoke(ToolRequest("web_search", "")).allowed is False


def test_send_message_notifier_raises_returns_ok_false():
    """notifier 拋例外 → ok=False，不向上拋（容錯）。"""
    def boom(*a, **k):
        raise RuntimeError("notify failed")

    adapter = ToolInvocationAdapter(enabled=True, allowlist=["alerts"], notifier=boom)
    res = adapter.invoke(ToolRequest("send_message", "alerts", {"message": "x"}))
    assert res.allowed is True and res.ok is False


def test_injected_handler_used_when_allowed():
    """放行的 web/http 若注入 handler → 走 handler（保留真實 I/O 擴充點）。"""
    def fake_http(req: ToolRequest):
        return True, {"status": 200, "url": req.target}

    adapter = ToolInvocationAdapter(
        enabled=True, allowlist=["example.com"], handlers={"http_request": fake_http}
    )
    res = adapter.invoke(ToolRequest("http_request", "https://example.com/ok"))
    assert res.allowed is True and res.ok is True
    assert res.data["status"] == 200


# ── R84（W9 交棒）：send_message 必須尊重 notification.enabled ──────────────
class _KwargSpyNotifier:
    """連 kwargs 一起記的 spy——`_SpyNotifier` 只收 `(title, message)`，

    對「有沒有傳 `enabled=`」結構上失明（漏傳時它照樣綠）。
    """

    def __init__(self):
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *a, **k):
        self.calls.append((a, k))


def test_send_message_forwards_notification_enabled_to_the_notifier():
    """`notification_enabled=False` 必須逐字傳到 notifier 的 `enabled=`。

    意圖（Rule 9）：`utils.notifier.notify` 的 `enabled` 預設 **True**，所以「不傳」與
    「傳 True」在型別與 rc 上完全一樣——漏傳的表徵就是使用者關掉了通知卻還是會彈窗，
    而沒有任何東西會說話。本支釘的是**那個 kwarg 真的被送出去**，不是 ok 旗標。
    """
    spy = _KwargSpyNotifier()
    adapter = ToolInvocationAdapter(
        enabled=True, allowlist=["alerts"], notifier=spy, notification_enabled=False
    )
    res = adapter.invoke(
        ToolRequest("send_message", "alerts", {"title": "T", "message": "M"})
    )
    assert res.allowed is True and res.ok is True
    assert len(spy.calls) == 1
    assert spy.calls[0][1].get("enabled") is False, (
        f"notifier 沒收到 enabled=False（實收 kwargs={spy.calls[0][1]}）"
        "——這條路徑會無視 config.notification.enabled"
    )


def test_send_message_forwards_enabled_true_when_notifications_are_on():
    """對稱控制組：開啟時必須傳 True，否則這道鎖鎖的是「永遠 False」而非「跟著 config」。"""
    spy = _KwargSpyNotifier()
    adapter = ToolInvocationAdapter(
        enabled=True, allowlist=["alerts"], notifier=spy, notification_enabled=True
    )
    adapter.invoke(ToolRequest("send_message", "alerts", {"message": "x"}))
    assert spy.calls[0][1].get("enabled") is True


def test_wiring_injects_notification_enabled_into_the_adapter():
    """站點級：wiring 不注入的話，adapter 的預設 True 會讓上面兩支恆綠而現實仍錯。

    意圖：缺陷的家在**組裝點**——adapter 收得到參數不代表有人給它。本支直接組一次
    真的 wiring，量 adapter 身上那個值是否等於 cfg 的值。
    """
    from autoclaude.core.wiring import build_goal_decomposer  # noqa: PLC0415

    cfg = AppConfig()
    cfg.notification.enabled = False
    cfg.tool_invocation = ToolInvocationConfig(enabled=True, allowlist=["alerts"])
    decomposer = build_goal_decomposer(cfg, brain=object())
    assert decomposer._tool._notification_enabled is False

    cfg.notification.enabled = True
    decomposer2 = build_goal_decomposer(cfg, brain=object())
    assert decomposer2._tool._notification_enabled is True
