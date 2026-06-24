"""decide_correction 單次性能 baseline（SD_08 W5 / ADR-SD08-003 §2.2 場景 #3）。

採集環境：CI nightly（CPU-bound，Minimax stub）
SLA 目標：p95 < baseline × 1.15

SD_09 W0 Pre-W0 audit B-07 修復（2026-05-20）：
  - 移除玩具「5 字串 sha256」負載
  - 改為 100 次真實 MinimaxClient.decide_correction 呼叫
  - HTTP 層 stub（_call_with_retry → 固定 dict），避免外部依賴
  - 覆蓋 prompt build + Pydantic 驗證 + Hallucination Guard 完整流程

AutoSDD improving_64 修復（2026-06-25，DEF-64-001）：
  - 根因：B-07 的「真實呼叫」鏈含 `prompt_builder.build_file_state_snapshot`，
    其每次呼叫 spawn 一個 `git diff --name-only HEAD` 子行程（prompt_builder.py:135）。
    本 repo 為單一 monorepo（根單一 .git），從 AutoClaude/ 跑 git diff 會掃整個工作樹，
    隨 Copy-on-Evolve 凍結版（v0.07→v0.25）與 docs 累積而逐輪變慢 → 基線量到的 99.7%
    是 git 子行程 I/O，非 decide_correction 邏輯，造成「隨 monorepo 成長假退化」
    且對真正的邏輯退化失明（邏輯僅占 ~0.3%）。實證：含 snapshot p95≈2943ms、
    stub 後純邏輯 p95≈9.8ms（占比 99.7%）。
  - 修法：與既有 HTTP 層 stub 同精神，於 workload 一併 stub git 層
    （build_file_state_snapshot → ""），使基線量純 CPU-bound 邏輯、確定性、
    不隨 monorepo 成長漂移（對齊 Nightly Forensic Discipline「基線須確定性 CPU-bound」）。
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from autoclaude.decision import prompt_builder
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
        # improving_64（DEF-64-001）：併 stub git 層快照——與既有 HTTP 層 stub 同精神，
        # 避免基線量到 `git diff` 子行程 I/O（隨 monorepo 成長漂移、非 CPU-bound 邏輯）。
        with patch.object(
            client, "_call_with_retry", return_value=_MOCK_DECISION_PAYLOAD,
        ), patch.object(
            prompt_builder, "build_file_state_snapshot", return_value="",
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

    # improving_64（DEF-64-001）Rule-9 守衛：純邏輯 100 次呼叫 p95 應 << 500ms（實測 ~10ms）。
    # 若 build_file_state_snapshot 等子行程 I/O 被重新計入量測，p95 會躍升至數千 ms
    # （monorepo `git diff`），此斷言即 fail loud，防環境依賴假退化回歸。
    assert baseline.p95_ms < 500, (
        f"decide_correction 純邏輯基線 p95={baseline.p95_ms:.1f}ms 異常偏高，"
        "疑似 git/subprocess I/O 重新潛入量測（見 improving_64 / DEF-64-001）"
    )

    _record_baseline(baseline)


def _record_baseline(baseline) -> None:
    """SD_09 B-08：注入 module-level registry，供 conftest 收集。"""
    import sys

    mod = sys.modules.get("tests.perf.conftest")
    if mod is not None and hasattr(mod, "_PERF_RESULTS"):
        mod._PERF_RESULTS.append(baseline)
