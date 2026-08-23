"""sdk_executor_adapter.py — IExecutor 實作：以 Claude Agent SDK 驅動 Claude Code。

improving_68 W-68-2（C/A 軌）。與 PtyExecutor **並存**；預設後端仍 pty（executor.backend
="pty"），本 adapter 為 opt-in（backend="sdk"，需 `pip install 'autoclaude[sdk]'`）。SDK 以
JSON-over-stdio spawn bundled Claude Code CLI，取代 PTY 文字流解析。

串流訊息映射（on_event）：
  AssistantMessage.TextBlock    → partial_output {"text": ...}（並累積為最終輸出）
  AssistantMessage.ToolUseBlock → tool_use {"tool": name, "args": input}
  ResultMessage                 → exit_code（is_error→1）
  get_context_usage().percentage→ token_pct {"pct": ...}
  完成                          → completion {"exit_code","completed","text_len"}

安全：
  - can_use_tool 接**注入的 allowlist predicate**（constructor 注入；不 import infra/plugins
    的安全閘實作），fail-closed（predicate 例外→deny）。
  - act-first（W-68-1）：執行期以 SDK get_context_usage() 的 maxTokens/autoCompactThreshold
    驗 verify_act_first_ordering；不安全則 fail-closed warn（保住 AutoClaude 形式化門檻權威）。

選配依賴隔離：claude_agent_sdk / anyio 僅在本模組被 import 時需要；main.py 對本模組採
lazy import（僅 backend="sdk" 時），故預設 pty 路徑完全不耦合 SDK/anyio。
"""
from __future__ import annotations

import itertools
import logging
import threading
from collections.abc import Callable
from typing import Any

import anyio

from ...core.ports.executor import (
    ExecutionEvent,
    ExecutionEventCallback,
    ExecutionEventKind,
    ExecutionOutput,
)
from ...core.ports.quota_meter import quota_refusal
from ...plugins.token_guard.thresholds import verify_act_first_ordering

logger = logging.getLogger(__name__)

# 注入式 allowlist predicate：同步 (tool_name, tool_input) -> bool（True=放行）
CanUseToolPredicate = Callable[[str, dict], bool]
# client factory：依 options kwargs 產生 SDK client（async context manager）
ClientFactory = Callable[..., Any]


class ActFirstOrderingError(RuntimeError):
    """improving_70 W-70-1：act-first 排序明確不安全時的 fail-closed 阻斷例外。

    當執行期判定 SDK autocompact 門檻可能搶先於 AutoClaude halt 觸發（形式化門檻權威
    恐被撞掉），不再僅 warn 而是 raise 本例外擋下執行（fail-loud）。無關閉鍵——使用者
    若要放行須調整 Token Guard 三槓桿（halt_pct / max_tokens / autocompact 門檻）使排序
    回到安全，而非繞過本檢查（沿 commit 76a710e「act-first 無需關閉鍵」設計）。
    """


def build_tool_allowlist_predicate(allowed_tools: list[str]) -> CanUseToolPredicate:
    """improving_69 W-69-2：由工具名 allowlist 建 production can_use_tool predicate。

    deny-by-default：僅 allowed_tools 內的工具名放行，其餘一律 deny（含空 list = 全 deny）。
    純函式、無副作用、不 import SDK；adapter 以 constructor 注入後由 _wrap_can_use_tool
    包成 SDK async hook（predicate 例外時 fail-closed deny）。policy 與 adapter 解耦：
    adapter 不知道也不硬編任何具體 allowlist，僅消費注入的 predicate。
    """
    allow_set = frozenset(allowed_tools)

    def _predicate(tool_name: str, _tool_input: dict) -> bool:
        return tool_name in allow_set

    return _predicate


def _default_client_factory(**options_kwargs: Any) -> Any:
    """預設 factory：lazy import claude_agent_sdk，組 ClaudeAgentOptions + ClaudeSDKClient。

    lazy import 使本模組在未安裝 [sdk] extra 時仍可被測試 import；僅實際以 sdk 後端
    execute 時才需套件存在。None 值的 option 不傳（讓 SDK 用自身預設）。
    """
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    opts = ClaudeAgentOptions(
        **{k: v for k, v in options_kwargs.items() if v is not None}
    )
    return ClaudeSDKClient(options=opts)


async def _maybe_await(value: Any) -> Any:
    """同時支援 mock 同步回傳與真實 async 回傳（get_context_usage / interrupt）。"""
    if hasattr(value, "__await__"):
        return await value
    return value


class SdkExecutorAdapter:
    """IExecutor：以 Claude Agent SDK（JSON-over-stdio）驅動 Claude Code。"""

    def __init__(
        self,
        cfg: Any,
        *,
        can_use_tool: CanUseToolPredicate | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self._cfg = cfg
        ec = getattr(cfg, "executor", None)
        self._permission_mode: str = getattr(ec, "permission_mode", "default")
        self._model: str | None = getattr(ec, "model", None)
        tg = getattr(cfg, "token_guard", None)
        self._halt_pct: float = float(getattr(tg, "halt_threshold_pct", 90.0))
        self._can_use_tool = can_use_tool
        self._client_factory: ClientFactory = client_factory or _default_client_factory
        # interrupt：threading.Event；execute 迴圈在訊息邊界檢查
        # （send_interrupt 由 Coordinator 呼叫）
        self._interrupt_event = threading.Event()
        self._running = False
        # 最近一次執行期 act-first 判定（None=未判定 / True=安全 / False=不安全已 warn）
        self._act_first_safe: bool | None = None

    # ── IExecutor 契約 ──────────────────────────────────────────────
    def execute(
        self,
        prompt: str,
        *,
        maintain_context: bool = True,
        timeout: int = 600,
        label: str = "",
        on_event: ExecutionEventCallback | None = None,
    ) -> ExecutionOutput:
        self._interrupt_event.clear()
        self._running = True
        try:
            return anyio.run(
                self._run_async, prompt, maintain_context, timeout, label, on_event
            )
        except Exception as exc:  # fail-loud：回 completed=False，不靜默吞例外
            logger.error("SdkExecutorAdapter.execute 失敗 (label=%s): %s", label, exc)
            return ExecutionOutput(text="", exit_code=1, completed=False)
        finally:
            self._running = False

    def send_interrupt(self, reason: str = "") -> bool:
        """請求中斷：設旗標；執行迴圈於下一訊息邊界呼叫 client.interrupt() 後結束。

        無執行中（_running=False）回 False（無可中斷者）。
        """
        if not self._running:
            return False
        self._interrupt_event.set()
        logger.info("SdkExecutorAdapter 收到中斷請求: %s", reason)
        return True

    # ── 內部 ────────────────────────────────────────────────────────
    async def _run_async(
        self,
        prompt: str,
        maintain_context: bool,
        timeout: int,
        label: str,
        on_event: ExecutionEventCallback | None,
    ) -> ExecutionOutput:
        seq = itertools.count(1)
        texts: list[str] = []
        exit_code = 0
        completed = True
        client = self._client_factory(
            can_use_tool=self._wrap_can_use_tool(),
            permission_mode=self._permission_mode,
            model=self._model,
            continue_conversation=bool(maintain_context),
        )
        async with client:
            await self._verify_act_first(client)
            await _maybe_await(client.query(prompt))
            with anyio.move_on_after(timeout) as scope:
                async for msg in client.receive_response():
                    if self._interrupt_event.is_set():
                        await _maybe_await(client.interrupt())
                        completed = False
                        break
                    mapped = self._map_message(msg, on_event, seq, texts)
                    if mapped is not None:
                        exit_code = mapped
            if scope.cancelled_caught:
                logger.warning("SdkExecutorAdapter 執行逾時 (%ss, label=%s)", timeout, label)
                completed = False
                exit_code = exit_code or 1
            await self._emit_token_pct(client, on_event, seq)
        text = "".join(texts)
        # R100 P2-C（PRD §8-1）：與 PtyExecutor 同一個洞——`completed` 只由 interrupt／
        # timeout 兩條路寫成 False，撞 429 的訊息會原樣進 text 而 completed 留在 True
        # （本檔既有測試 `assert out.completed is True  # 只是 is_error` 就是那個外觀）。
        # 修在兩個後端都要做：只修一邊等於「換 backend 就繞過」。判準同一個家。
        refusal = quota_refusal(text)
        if refusal:
            completed = False
            exit_code = exit_code or 1
            logger.error("SdkExecutorAdapter: %s（label=%s）", refusal, label or "untitled")
        self._emit(
            on_event,
            ExecutionEventKind.COMPLETION,
            {"exit_code": exit_code, "completed": completed, "text_len": len(text)},
            seq,
        )
        return ExecutionOutput(text=text, exit_code=exit_code, completed=completed,
                               quota_refusal=refusal)

    def _map_message(
        self,
        msg: Any,
        on_event: ExecutionEventCallback | None,
        seq: itertools.count[int],
        texts: list[str],
    ) -> int | None:
        """映射單一 SDK 訊息為 on_event 事件；ResultMessage 回 exit_code，否則 None。

        以 type(msg).__name__ 比對（與 SDK 具體 import 解耦，利於 mock 測試）。
        """
        cls = type(msg).__name__
        if cls == "AssistantMessage":
            for block in getattr(msg, "content", None) or []:
                bcls = type(block).__name__
                if bcls == "TextBlock":
                    t = getattr(block, "text", "")
                    texts.append(t)
                    self._emit(
                        on_event, ExecutionEventKind.PARTIAL_OUTPUT, {"text": t}, seq
                    )
                elif bcls == "ToolUseBlock":
                    self._emit(
                        on_event,
                        ExecutionEventKind.TOOL_USE,
                        {
                            "tool": getattr(block, "name", ""),
                            "args": getattr(block, "input", {}),
                        },
                        seq,
                    )
            return None
        if cls == "ResultMessage":
            return 1 if getattr(msg, "is_error", False) else 0
        return None

    async def _verify_act_first(self, client: Any) -> None:
        """act-first（W-68-1 守門／W-70-1 硬擋）：驗 AutoClaude halt 是否先於 SDK autocompact 觸發。

        明確判定不安全（safe=False）時 **fail-closed raise** `ActFirstOrderingError` 擋下執行
        （W-70-1：由 warn-only 升級為硬擋）；「無法判定」（取不到用量 / 非 dict / 缺
        threshold|max_tokens）維持 best-effort early-return 放行，不誤擋。
        """
        try:
            usage = await _maybe_await(client.get_context_usage())
        except Exception:  # 取不到用量不阻斷執行（best-effort 守門；無法判定≠不安全）
            return
        if not isinstance(usage, dict):
            return
        threshold = usage.get("autoCompactThreshold")
        max_tokens = usage.get("maxTokens")
        if not threshold or not max_tokens:
            return
        safe = verify_act_first_ordering(
            autocompact_threshold_tokens=int(threshold),
            max_tokens=int(max_tokens),
            halt_pct=self._halt_pct,
        )
        self._act_first_safe = safe
        if not safe:
            raise ActFirstOrderingError(
                f"act-first 排序不安全：SDK autocompact 門檻({threshold} tokens) 可能搶先於 "
                f"AutoClaude halt({self._halt_pct:.1f}% of {max_tokens}) 觸發；形式化門檻權威恐被"
                f"撞掉。請調整 Token Guard 三槓桿使排序回到安全（halt 換算 token 數須 < "
                f"autocompact 門檻），本檢查無關閉鍵。"
            )

    async def _emit_token_pct(
        self,
        client: Any,
        on_event: ExecutionEventCallback | None,
        seq: itertools.count[int],
    ) -> None:
        if on_event is None:
            return
        try:
            usage = await _maybe_await(client.get_context_usage())
        except Exception as exc:
            # W-82-3 / DEF-81-001 SDK 支：取用量例外不再純靜默 → fail-loud 標記訊號源未產出
            logger.warning(
                "SDK get_context_usage 取用量例外，token%% 訊號源未產出（DEF-81-001 SDK 支）：%s",
                exc,
            )
            return
        pct = usage.get("percentage") if isinstance(usage, dict) else None
        if pct is not None:
            self._emit(
                on_event,
                ExecutionEventKind.TOKEN_PCT,
                {"pct": float(pct)},
                seq,
            )
        else:
            # W-82-3 / DEF-81-001 SDK 支：盲區可觀測化——percentage 缺失時不再靜默跳過
            # （improving_76~81 真跑 SDK 支恆 0 的根因），改 fail-loud warn 使盲區在真跑可見。
            logger.warning(
                "SDK get_context_usage 無 percentage 欄，token%% 訊號源未產出"
                "（DEF-81-001 SDK 支）；usage keys=%s",
                sorted(usage.keys()) if isinstance(usage, dict) else type(usage).__name__,
            )

    def _wrap_can_use_tool(self) -> Callable | None:
        """把注入的 sync allowlist predicate 包成 SDK 的 async can_use_tool。"""
        pred = self._can_use_tool
        if pred is None:
            return None

        async def _hook(tool_name: str, tool_input: dict, context: Any):
            from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

            try:
                allowed = bool(pred(tool_name, tool_input))
            except Exception as exc:  # fail-closed：predicate 例外即拒絕
                logger.warning("can_use_tool predicate 例外，fail-closed deny: %s", exc)
                allowed = False
            if allowed:
                return PermissionResultAllow()
            return PermissionResultDeny(
                message=f"blocked by allowlist: {tool_name}", interrupt=False
            )

        return _hook

    @staticmethod
    def _emit(
        on_event: ExecutionEventCallback | None,
        kind: str,
        payload: dict,
        seq: itertools.count[int],
    ) -> None:
        if on_event is None:
            return
        try:
            on_event(ExecutionEvent(kind=kind, payload=payload, sequence=next(seq)))
        except Exception:  # callback 例外不可影響執行（與 DryRunExecutor 同紀律）
            pass
