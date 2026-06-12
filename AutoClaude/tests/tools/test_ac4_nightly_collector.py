"""tests/tools/test_ac4_nightly_collector.py — AC4 collector 門檻判定測試。

SD_09 W0 zero-trust audit P1-3 修復配套：
驗證 `_parse_junit_xml` 在所有 metric 進入後必須套真實門檻
（RECALL_MIN=0.95 / P95_MAX_MS env / CB_OPEN_MAX=0），
避免 junit 標 pass 但 p95 超門檻時被誤判 pass。

SD_09 W2 audit P0-AUDIT-08 修復配套：
collector 採集寬鬆門檻獨立 env `AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS`（預設 80ms）。
本檔測試使用 monkeypatch 強制 module-level P95_MAX_MS 以涵蓋雙軌語意。

涵蓋路徑：
  - fail (recall < 0.95)
  - fail (p95 > collector threshold)
  - fail (cb_open_count > 0)
  - fail (recall is None)
  - pass (全部達標)
  - skip (整體 skipped + recall is None)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import ac4_nightly_collector  # noqa: E402
from ac4_nightly_collector import _parse_junit_xml  # noqa: E402


@pytest.fixture(autouse=True)
def _strict_p95_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """SD_09 W2 audit P0-AUDIT-08：collector 預設改 80ms 後，
    既有測試需明確 patch 為 50ms 才能驗證偽陽性偵測（升級嚴格場景）。
    """
    monkeypatch.setattr(ac4_nightly_collector, "P95_MAX_MS", 50.0)


def _write_junit(
    tmp_path: Path,
    *,
    recall: str | None = "0.97",
    p95: str | None = "32.0",
    cb_open: str | None = "0",
    skipped: bool = False,
    failure: bool = False,
) -> Path:
    """產生最小 junit XML — 對應 test_pgvector_real_recall.py 三個 testcase 結構。"""
    parts: list[str] = ['<?xml version="1.0" encoding="utf-8"?>', '<testsuites name="pytest">']
    parts.append('<testsuite name="pytest" tests="3" failures="0" errors="0" skipped="0">')

    def _case(name: str, prop_name: str, prop_value: str | None) -> str:
        body = ""
        if failure:
            body += '<failure message="x">trace</failure>'
        if skipped:
            body += '<skipped type="pytest.skip" message="x">trace</skipped>'
        if prop_value is not None:
            body += f'<properties><property name="{prop_name}" value="{prop_value}" /></properties>'
        return f'<testcase classname="t" name="{name}">{body}</testcase>'

    parts.append(_case("test_recall_at_10", "recall_at_10", recall))
    parts.append(_case("test_p95_latency_under_50ms", "p95_ms", p95))
    parts.append(_case("test_bge_failure_minimax_fallback_under_60s", "cb_open_count", cb_open))
    parts.append("</testsuite>")
    parts.append("</testsuites>")

    p = tmp_path / "junit.xml"
    p.write_text("".join(parts), encoding="utf-8")
    return p


def test_pass_when_all_metrics_within_thresholds(tmp_path: Path) -> None:
    """recall=0.97 / p95=32 / cb=0 → pass。"""
    xml = _write_junit(tmp_path, recall="0.97", p95="32.0", cb_open="0")
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "pass"
    assert metrics["recall_at_10"] == pytest.approx(0.97)
    assert metrics["p95_ms"] == pytest.approx(32.0)
    assert metrics["cb_open_count"] == 0
    assert "threshold_fail_reasons" not in metrics


def test_fail_when_recall_below_threshold(tmp_path: Path) -> None:
    """recall=0.90 (<0.95) → fail。"""
    xml = _write_junit(tmp_path, recall="0.90", p95="32.0", cb_open="0")
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "fail"
    assert any("recall_at_10" in r for r in metrics["threshold_fail_reasons"])


def test_fail_when_p95_above_threshold(tmp_path: Path) -> None:
    """p95=52.36 (>50) → fail（對應實測 .ac4_junit.xml 偽陽性場景）。"""
    xml = _write_junit(tmp_path, recall="0.97", p95="52.36", cb_open="0")
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "fail"
    assert any("p95_ms" in r for r in metrics["threshold_fail_reasons"])


def test_fail_when_circuit_breaker_open(tmp_path: Path) -> None:
    """cb_open=1 (>0) → fail。"""
    xml = _write_junit(tmp_path, recall="0.97", p95="32.0", cb_open="1")
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "fail"
    assert any("cb_open_count" in r for r in metrics["threshold_fail_reasons"])


def test_fail_when_metric_is_none(tmp_path: Path) -> None:
    """recall 缺 property → None → fail（避免空值偽 pass）。"""
    xml = _write_junit(tmp_path, recall=None, p95="32.0", cb_open="0")
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "fail"
    assert metrics["recall_at_10"] is None
    assert any("recall_at_10=None" in r for r in metrics["threshold_fail_reasons"])


def test_skip_when_overall_skipped_and_recall_missing(tmp_path: Path) -> None:
    """全 skipped + recall None → skip（pg-e2e 整體未跑）。"""
    xml = _write_junit(tmp_path, recall=None, p95=None, cb_open=None, skipped=True)
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "skip"
    # skip 不套門檻，不應有 threshold_fail_reasons
    assert "threshold_fail_reasons" not in metrics


def test_fail_when_junit_has_explicit_failure(tmp_path: Path) -> None:
    """有 <failure> 元素時應直接 fail（不被門檻覆蓋為 pass）。"""
    xml = _write_junit(tmp_path, recall="0.97", p95="32.0", cb_open="0", failure=True)
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "fail"


def test_missing_file_returns_fail(tmp_path: Path) -> None:
    """junit XML 不存在 → fail 兜底。"""
    xml = tmp_path / "missing.xml"
    metrics = _parse_junit_xml(xml)

    assert metrics["status"] == "fail"
    assert metrics["recall_at_10"] is None
    assert metrics["p95_ms"] is None


def test_collector_lenient_p95_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SD_09 W2 audit P0-AUDIT-08 雙軌語意：採集寬鬆 80ms 場景。

    Windows + Docker overhead → collector 容忍 p95=60ms（< 80ms）標 pass，
    progress_check（嚴格 50ms）後續會在 _is_green 用嚴格門檻過濾真實達標。
    """
    monkeypatch.setattr(ac4_nightly_collector, "P95_MAX_MS", 80.0)
    xml = _write_junit(tmp_path, recall="0.97", p95="60.0", cb_open="0")
    metrics = _parse_junit_xml(xml)
    assert metrics["status"] == "pass"
    assert "threshold_fail_reasons" not in metrics


def test_collector_lenient_p95_still_fails_above_80ms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """採集寬鬆門檻 80ms 之上仍 fail（不會無上限放水）。"""
    monkeypatch.setattr(ac4_nightly_collector, "P95_MAX_MS", 80.0)
    xml = _write_junit(tmp_path, recall="0.97", p95="95.0", cb_open="0")
    metrics = _parse_junit_xml(xml)
    assert metrics["status"] == "fail"
    assert any("p95_ms" in r for r in metrics["threshold_fail_reasons"])


def test_resolve_p95_threshold_env_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """SD_09 W2 audit P0-AUDIT-08：env 優先級 collector > legacy > default。"""
    from ac4_nightly_collector import _resolve_p95_threshold
    monkeypatch.delenv("AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS", raising=False)
    monkeypatch.delenv("AUTOCLAUDE_TEST_P95_THRESHOLD_MS", raising=False)
    assert _resolve_p95_threshold() == 80.0

    monkeypatch.setenv("AUTOCLAUDE_TEST_P95_THRESHOLD_MS", "70")
    assert _resolve_p95_threshold() == 70.0

    monkeypatch.setenv("AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS", "90")
    assert _resolve_p95_threshold() == 90.0
