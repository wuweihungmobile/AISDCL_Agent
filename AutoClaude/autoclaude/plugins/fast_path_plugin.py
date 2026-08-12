"""FastPathPlugin — Gap-007-B：測試檔語法快速路徑（PRE_ATTEMPT phase）。

SD_Improving_05 W4-2：從 `_runner_internals._fast_path_test_file_check` 搬移。

職責：
  - 在 `PRE_ATTEMPT` phase 檢視 payload 中的 ``eval_output``
  - 偵測 pytest 失敗輸出中是否包含 test_*.py / *_test.py 檔案路徑
  - 對偵測到的測試檔執行 ``python -m py_compile`` 驗證語法
  - 若語法錯誤 → 回傳 ``PromptInjectionResult``，注入「硬性約束」prefix
    告知 Claude Code 必須直接修復測試檔語法（不得修改實作檔）

設計原則：
  - 為 Layer 2 純度，subprocess 透過注入 ``compiler`` callable 執行
    （預設 ``_default_compiler`` 使用 subprocess.run）
  - 僅在 ``attempt == 0`` 且 ``payload["eval_output"]`` 非空時觸發
  - regex 失敗 / py_compile 通過 / 無 eval_output 時回傳 None（不注入）

行數預算：本檔 ≤ 90 行。
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from collections.abc import Callable

from ..core.hookspec import (
    HookContext,
    KernelPhase,
    PromptInjectionResult,
)

logger = logging.getLogger(__name__)

_PRIMARY_PATTERN = re.compile(
    r'(?:ERROR collecting|FAILED)\s+'
    r'((?:tests?|src)[/\\](?:[a-zA-Z0-9_\-]+[/\\])*(?:test_\w+|\w+_test)\.py)',
    re.IGNORECASE,
)
_FALLBACK_PATTERN = re.compile(
    r'((?:[/\\]?[\w\-]+[/\\])+(?:test_\w+|\w+_test)\.py)',
    re.IGNORECASE,
)
_DEFAULT_COMPILE_TIMEOUT = 10


def _default_compiler(test_file: str, timeout: int) -> tuple[int, str]:
    """以 subprocess 執行 ``python -m py_compile``，回傳 (returncode, stderr)。

    SD_05 W4 SD-M3 修復：假陰性風險明示
      - FileNotFoundError / TimeoutExpired / OSError 視為 (0, "")（plugin 解讀為通過）
      - 但會 logger.warning，便於監控偵測「fast path 失效」的隱性故障
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", test_file],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
            # R85（訴求 2）：原為本檔私有 helper `_propagate_trace_env()`，函式體就是
            # `return dict(os.environ)`——名字說「傳遞 trace」，實際什麼都沒傳（真正會寫
            # TRACEPARENT 的是 utils.trace_context.propagate_to_subprocess_env，而 plugin
            # 受 importlinter Rule 7 禁止直接 import 它）。留著一個與名字不符的空殼、又在
            # token_guard/git_verifier.py 有一份逐字副本，是「同一份知識住兩個家」的形態。
            # 就地展開為它真正的語意，零行為變更；git_verifier 那份因有 mutation 測試綁定
            # 未動，已列入交棒。
            env=dict(os.environ),
        )
        return result.returncode, result.stderr or ""
    except FileNotFoundError as exc:
        logger.warning(
            "FastPathPlugin | python 不在 PATH，fast path 失效（假陰性風險）: %s",
            exc,
        )
        return 0, ""
    except subprocess.TimeoutExpired as exc:
        logger.warning(
            "FastPathPlugin | py_compile 超時 %ds（假陰性風險）: %s",
            timeout, exc,
        )
        return 0, ""
    except (OSError, PermissionError) as exc:
        logger.warning(
            "FastPathPlugin | py_compile OS/Permission 錯誤（假陰性風險）: %s", exc,
        )
        return 0, ""


class FastPathPlugin:
    """SD_05 W4-2：PRE_ATTEMPT phase 快速路徑（測試檔語法）。"""

    PRIORITY = 50

    def __init__(
        self,
        compiler: Callable[[str, int], tuple[int, str]] | None = None,
        timeout_seconds: int = _DEFAULT_COMPILE_TIMEOUT,
    ):
        self._compile = compiler or _default_compiler
        self._timeout = timeout_seconds

    def name(self) -> str:
        return "fast_path"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.PRE_ATTEMPT]

    def on_event(self, ctx: HookContext) -> PromptInjectionResult | None:
        if ctx.phase is not KernelPhase.PRE_ATTEMPT:
            return None
        # 僅在 attempt == 0 觸發（首次嘗試前，後續由 strategy 路徑接手）
        if ctx.attempt is not None and ctx.attempt != 0:
            return None
        eval_output: str = (ctx.payload or {}).get("eval_output", "") or ""
        if not eval_output:
            return None
        hint = self._check(eval_output)
        if hint is None:
            return None
        return PromptInjectionResult(
            contributor=self.name(), prefix=hint, position="top",
        )

    def _check(self, eval_output: str) -> str | None:
        m = _PRIMARY_PATTERN.search(eval_output) or _FALLBACK_PATTERN.search(eval_output)
        if not m:
            return None
        test_file = m.group(1).replace("\\", "/")
        rc, stderr = self._compile(test_file, self._timeout)
        if rc == 0:
            return None
        return (
            f"🚫 硬性約束：{test_file} 存在語法錯誤（py_compile 驗證失敗）。"
            f"修正指令必須直接修復 {test_file} 的語法，不得修改任何實作檔。"
            f"\n語法錯誤詳情：{stderr[:200]}"
        )
