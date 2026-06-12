"""TokenHalt 往返性能 baseline（SD_08 W5 / ADR-SD08-003 §2.2 場景 #2）。

採集環境：CI nightly（CPU-bound）
SLA 目標：p95 < baseline × 1.15

SD_09 W0 Pre-W0 audit B-07 修復（2026-05-20）：
  - 移除玩具「'x'*4096 切半 3 次」負載
  - 改為 TokenGuardPlugin 1000 次 token 估算 + 觸發 compact 1 次
  - 覆蓋 should_compact / should_halt / build_compact_prompt 完整路徑
"""
from __future__ import annotations

import pytest

from autoclaude.utils.perf_baseline import measure

pytestmark = pytest.mark.perf


def _make_workload():
    """B-07：TokenGuardPlugin 1000 次估算 + 1 次 compact prompt 組裝負載。"""
    from autoclaude.plugins.token_guard import TokenGuardPlugin
    from autoclaude.utils.config import TokenGuardConfig

    plugin = TokenGuardPlugin(token_guard_cfg=TokenGuardConfig())

    # 預先建立一個 task-like 物件供 build_compact_prompt 使用
    class _TaskStub:
        step_id = "PERF_T01"
        name = "perf token halt step"
        prompt = "perf prompt body for token halt round trip measurement"

    task = _TaskStub()

    def _workload() -> None:
        # 1000 次 token 估算 + threshold 判斷（70%~95% 變動）
        for i in range(1000):
            pct = 70.0 + (i % 30)  # 70.0~99.0 範圍
            _ = plugin.should_compact(
                token_pct=pct,
                attempt=i % 3,
                max_retries=3,
                in_correction_loop=(i % 5 == 0),
                correction_history_len=i % 4,
            )
            _ = plugin.should_halt(token_pct=pct)

        # 1 次 compact prompt 組裝（觸發 halt → /compact → resume 往返主路徑）
        compact_prompt = plugin.build_compact_prompt(
            task=task,
            attempt=1,
            failure_summary="perf baseline halt roundtrip",
            global_goal="perf baseline 場景 #2 token halt roundtrip",
        )
        assert compact_prompt  # noqa: S101

    return _workload


def test_token_halt_roundtrip_baseline_smoke():
    workload = _make_workload()
    # SD_09 W2-#1：samples=20 採集（ADR-SD08-003 v1.1 §2.3）— 解 samples=7 統計噪音
    baseline = measure("token_halt_roundtrip", workload, runs=20)

    assert baseline.scenario == "token_halt_roundtrip"
    assert baseline.samples == 20
    assert baseline.p95_ms >= baseline.p50_ms

    _record_baseline(baseline)


def _record_baseline(baseline) -> None:
    """SD_09 B-08：注入 module-level registry，供 conftest 收集。"""
    import sys

    mod = sys.modules.get("tests.perf.conftest")
    if mod is not None and hasattr(mod, "_PERF_RESULTS"):
        mod._PERF_RESULTS.append(baseline)
