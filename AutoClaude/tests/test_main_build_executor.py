"""main.build_executor 後端建構回歸測試（AutoSDD improving_71 DEF-71-001）。

Rule 9：此測編碼「main 的 executor 接線必須能用預設 config 建出 PtyExecutor 而不崩潰」
之意圖。原 `PtyExecutor(cfg)` 傳整個 AppConfig 又缺 loop_cfg → CLI 預設 pty 後端必崩
（TypeError），因建構未被任何測試覆蓋而長期潛伏（既有測試皆直接
`PtyExecutor(ClaudeConfig(), LoopConfig())`，繞過 main 接線）。本測直跑 main 接線，
business logic（傳 cfg.claude/cfg.loop）改錯即 TypeError → 紅。
"""
from __future__ import annotations

import pytest

from autoclaude.infra.adapters.pty_executor import PtyExecutor
from autoclaude.main import build_executor
from autoclaude.utils.config import AppConfig


def test_default_backend_builds_pty_executor_without_crash():
    """預設（pty）後端：build_executor 以預設 config 建出 PtyExecutor，不拋 TypeError。"""
    cfg = AppConfig()
    assert cfg.executor.backend == "pty"  # 預設即 pty
    executor = build_executor(cfg)
    assert isinstance(executor, PtyExecutor)


def test_pty_executor_receives_claude_and_loop_cfg():
    """接線正確性：PtyExecutor 收到 ClaudeConfig（非整個 AppConfig），證明傳的是 cfg.claude。"""
    from autoclaude.utils.config import ClaudeConfig

    executor = build_executor(AppConfig())
    # PtyExecutor 將 claude_cfg 存於 self._claude；型別應為 ClaudeConfig 而非 AppConfig
    assert isinstance(executor._claude, ClaudeConfig)
    from autoclaude.utils.config import LoopConfig
    assert isinstance(executor._loop, LoopConfig)


def test_sdk_backend_builds_sdk_adapter():
    """sdk 後端：build_executor 走 lazy-import 分支建出 SdkExecutorAdapter（需 anyio）。"""
    pytest.importorskip("anyio")
    from autoclaude.infra.adapters.sdk_executor_adapter import SdkExecutorAdapter

    cfg = AppConfig()
    cfg.executor.backend = "sdk"
    executor = build_executor(cfg)
    assert isinstance(executor, SdkExecutorAdapter)
