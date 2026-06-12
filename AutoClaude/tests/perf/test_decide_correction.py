"""decide_correction 單次性能 baseline（SD_08 W5 / ADR-SD08-003 §2.2 場景 #3）。

採集環境：CI nightly（CPU-bound，Minimax stub）
SLA 目標：p95 < baseline × 1.15

SD_09 W0 Pre-W0 audit B-07 修復（2026-05-20）：
  - 移除玩具「5 字串 sha256」負載
  - 改為 100 次真實 MinimaxClient.decide_correction 呼叫
  - HTTP 層 stub（_call_with_retry → 固定 dict），避免外部依賴
  - 覆蓋 prompt build + Pydantic 驗證 + Hallucination Guard 完整流程
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from autoclaude.utils.perf_baseline import measure

pytestmark = pytest.mark.perf


_MOCK_DECISION_PAYLOAD = {
    "correction_prompt": (
        "請修正 tests/test_foo.py:42 的 SyntaxError：函式 def calc 缺少冒號；"
        "並補回 assert result == 42 確保斷言通過。"
    ),
    "reasoning": "step1 evaluator stderr 顯示 SyntaxError on line 42",
    "task_goal_summary": "perf baseline 場景 #3 — decide_correction mock",
    "step_mutation": None,
}


def _build_minimax_client():
    """建立 MinimaxClient 並 stub _call_with_retry 為固定 dict（避免 HTTP）。"""
    from autoclaude.decision.minimax_client import MinimaxClient

    client = MinimaxClient(
        api_key="perf-baseline-stub",
        base_url="https://stub.invalid",
        model="stub",
        timeout=1.0,
    )
    return client


def _make_workload():
    """B-07：100 次 mock decide_correction 呼叫（含 prompt build + 驗證）。"""
    client = _build_minimax_client()

    def _workload() -> None:
        with patch.object(
            client, "_call_with_retry", return_value=_MOCK_DECISION_PAYLOAD,
        ):
            for i in range(100):
                decision = client.decide_correction(
                    step_id=f"P{i:03d}",
                    task_name=f"perf step {i}",
                    task_prompt="prompt body for perf baseline measurement",
                    expected_regex="DONE",
                    failure_reason="SyntaxError on line 42",
                    eval_output="tests/test_foo.py:42 SyntaxError: invalid syntax",
                    retry_count=1,
                    history_summary="",
                    convergence_trend="",
                    error_class="syntax",
                )
                assert decision.correction_prompt  # noqa: S101

    return _workload


def test_decide_correction_baseline_smoke():
    workload = _make_workload()
    # SD_09 W2-#1：samples=20 採集（ADR-SD08-003 v1.1 §2.3）— 解 samples=7 統計噪音
    baseline = measure("decide_correction", workload, runs=20)

    assert baseline.scenario == "decide_correction"
    assert baseline.samples == 20
    assert baseline.p95_ms >= baseline.p50_ms

    _record_baseline(baseline)


def _record_baseline(baseline) -> None:
    """SD_09 B-08：注入 module-level registry，供 conftest 收集。"""
    import sys

    mod = sys.modules.get("tests.perf.conftest")
    if mod is not None and hasattr(mod, "_PERF_RESULTS"):
        mod._PERF_RESULTS.append(baseline)
