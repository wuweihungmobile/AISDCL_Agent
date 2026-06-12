"""tests/tools/test_observability_snapshot.py — D-16（SD_09 W0 三次 zero-trust audit 補建）。

對應 tools/observability_snapshot.py：
  1. test_basic_append          — 第一次跑必須寫入 1 筆
  2. test_same_day_deduplication — 同 UTC 日期跑兩次只保留 1 筆（覆寫該日）
  3. test_record_schema_alignment — 寫入的 record schema 對齊 (1a) ga_check 期望 4 keys
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.observability_snapshot import (
    append_snapshot,
    collect_snapshot,
    main,
)


def test_basic_append(tmp_path: Path) -> None:
    """首次寫入：jsonl 從無到有 → 1 筆 record。"""
    history = tmp_path / ".observability_history.jsonl"
    record = collect_snapshot()

    action = append_snapshot(history, record)

    assert action == "appended"
    assert history.exists()
    lines = [
        line for line in history.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["ts"] == record["ts"]


def test_same_day_deduplication(tmp_path: Path) -> None:
    """同 UTC 日期兩筆 → 第二筆覆寫第一筆，最終仍只有 1 筆。"""
    history = tmp_path / ".observability_history.jsonl"

    record1 = {
        "ts": "2026-05-21T01:00:00+00:00",
        "observability_emit_count": 10,
        "trace_id_continuity": True,
        "kb_metric_snapshot": {
            "hit_rate": 0.5,
            "query_p95_ms": 1.0,
            "strategy_rotation_count": 0,
            "cache_eviction_count": 0,
        },
    }
    record2 = {
        "ts": "2026-05-21T23:30:00+00:00",  # 同日後段
        "observability_emit_count": 99,
        "trace_id_continuity": True,
        "kb_metric_snapshot": {
            "hit_rate": 0.9,
            "query_p95_ms": 2.0,
            "strategy_rotation_count": 1,
            "cache_eviction_count": 0,
        },
    }
    # 不同日
    record3 = {
        "ts": "2026-05-22T05:00:00+00:00",
        "observability_emit_count": 100,
        "trace_id_continuity": True,
        "kb_metric_snapshot": record2["kb_metric_snapshot"],
    }

    assert append_snapshot(history, record1) == "appended"
    assert append_snapshot(history, record2) == "replaced"  # 同日去重
    assert append_snapshot(history, record3) == "appended"  # 不同日

    lines = [
        json.loads(line)
        for line in history.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 2
    # 同日去重後保留最後一筆 record2
    same_day = [l for l in lines if l["ts"].startswith("2026-05-21")]
    assert len(same_day) == 1
    assert same_day[0]["observability_emit_count"] == 99


def test_record_schema_alignment(tmp_path: Path) -> None:
    """寫入的 record schema 對齊 4 keys（observability_ga_check 期望讀取的欄位）。"""
    history = tmp_path / ".observability_history.jsonl"
    record = collect_snapshot()

    required_top_keys = {
        "ts",
        "observability_emit_count",
        "trace_id_continuity",
        "kb_metric_snapshot",
    }
    assert set(record.keys()) >= required_top_keys, (
        f"top-level schema 缺欄：{required_top_keys - set(record.keys())}"
    )

    # KB metric snapshot 必須至少包含 4 個 SLO 指標（ADR-SD08-004 §2.4；
    # 真實 snapshot 還包含 total_queries / total_hits 為計算來源，允許 superset）
    kb_keys = set(record["kb_metric_snapshot"].keys())
    expected_kb_keys = {
        "hit_rate",
        "query_p95_ms",
        "strategy_rotation_count",
        "cache_eviction_count",
    }
    assert expected_kb_keys.issubset(kb_keys), (
        f"KB snapshot 缺必要 SLO 鍵：{expected_kb_keys - kb_keys}"
    )

    # 寫入後可重新讀回（jsonl roundtrip 健康）
    append_snapshot(history, record)
    persisted = json.loads(history.read_text(encoding="utf-8").splitlines()[0])
    assert expected_kb_keys.issubset(set(persisted["kb_metric_snapshot"].keys()))


def test_main_cli_runs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI 入口 main() 可執行且 exit 0；--history 路徑生效。"""
    history = tmp_path / ".obs_test.jsonl"
    rc = main(["--history", str(history)])
    assert rc == 0
    assert history.exists()
    out = capsys.readouterr().out
    assert "observability-snapshot" in out


def test_ga_check_schema_self_alignment() -> None:
    """紀律 #4「驗證鏡子自身要被驗證」— snapshot 寫入 record 必須對齊
    observability_ga_check.KB_METRIC_REQUIRED_KEYS（避免兩端 schema 偏離 SSOT）。

    修復來源：SD_09 W0 G0 zero-trust audit 第 4 輪 P0-X1 L3（避免 ga_check 自定
    schema 與 KnowledgeBaseMetrics.snapshot() 真實 SSOT 漂移）。
    """
    from tools.observability_ga_check import KB_METRIC_REQUIRED_KEYS

    record = collect_snapshot()
    snapshot_keys = set(record["kb_metric_snapshot"].keys())
    missing = set(KB_METRIC_REQUIRED_KEYS) - snapshot_keys
    assert not missing, (
        f"ga_check.KB_METRIC_REQUIRED_KEYS 與 snapshot 寫入 schema 不對齊；"
        f"缺：{missing}；現有 keys：{snapshot_keys}"
    )


def test_emit_count_positive(tmp_path: Path) -> None:
    """L1 修復驗證 — emit_count 不可寫死 0；應 >= 1 表 IObservabilityPort 可運作。"""
    record = collect_snapshot()
    assert record["observability_emit_count"] > 0, (
        f"emit_count={record['observability_emit_count']}；"
        f"應透過 LocalLogger.emit_* 真實計數，不可寫死 0"
    )


def test_emit_real_true_on_success() -> None:
    """F1 修復驗證（SD_09 W3 zero-trust audit 2026-05-24）— 真實 LocalLogger emit 路徑
    `observability_emit_real` 必須為 True；區分 fallback mock 假象。"""
    record = collect_snapshot()
    assert record["observability_emit_real"] is True, (
        f"emit_real={record['observability_emit_real']}；"
        f"預設環境 LocalLogger 可 import 應走真實 emit 路徑回 True"
    )
    # 同時驗證 count == 3（3 個 emit 方法）為真實路徑特徵
    assert record["observability_emit_count"] == 3, (
        f"真實 emit 應為 3 次（counter + histogram + record_event）；"
        f"目前 count={record['observability_emit_count']}（疑為 fallback 路徑）"
    )


def test_emit_real_false_on_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """F1 修復驗證 — LocalLogger import 失敗時 emit_real 必須回 False（不可掩蓋成 True）。

    紀律 #4「驗證鏡子自身要被驗證」— fake-PASS 場景能被拒絕。
    """
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if "local_logger" in name:
            raise ImportError("simulated LocalLogger import failure")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from tools import observability_snapshot as obs

    count, emit_real = obs._emit_heartbeat_and_count()
    assert emit_real is False, "import 失敗 fallback 路徑必須回 emit_real=False"
    assert count == 1, "fallback 路徑保留 count=1 維持 schema 對齊"


def test_trace_continuity_measured(monkeypatch: pytest.MonkeyPatch) -> None:
    """SD_09 W2 nightly audit P1-1 修復驗證 — trace_continuity 必須實測，不可寫死 True。

    紀律 #4「驗證鏡子自身要被驗證」：本 case 透過 monkeypatch with_trace_id 模擬
    斷鏈場景，驗證實測能正確回傳 False；對應 PASS 場景靠 collect_snapshot() 預設行為。
    """
    from tools import observability_snapshot as obs

    # 1) 正常路徑（無 patch）— 同 process 內 trace_id 必須連續
    assert obs._measure_trace_continuity() is True, (
        "預設 with_trace_id() / get_trace_id() 同一上下文必須回傳一致 trace_id"
    )

    # 2) 模擬斷鏈：patch with_trace_id 拋例外 → 實測應回 False
    from contextlib import contextmanager

    @contextmanager
    def broken_with_trace_id(tid=None):  # noqa: ANN001
        raise RuntimeError("simulated trace_id propagation failure")
        yield  # pragma: no cover

    monkeypatch.setattr(
        "autoclaude.utils.trace_context.with_trace_id", broken_with_trace_id
    )
    assert obs._measure_trace_continuity() is False, (
        "with_trace_id() 拋例外時，實測應回 False（不可寫死 True 掩蓋）"
    )

    # 3) collect_snapshot 整合：呼叫後 record 必須帶 bool（非寫死）
    record = obs.collect_snapshot()
    assert isinstance(record["trace_id_continuity"], bool)


def test_emit_partial_success_returns_real_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """SD_09 W3 Round 2 audit P1-8：三段 emit 中一段失敗 → count=2 + emit_real=True。

    紀律 #4「驗證鏡子自身要被驗證」— partial success 不應整段 fallback；
    強制讓 emit_histogram 拋例外，counter + record_event 仍成功 → 應回 (2, True)。
    """
    from autoclaude.infra.adapters.observability import local_logger as ll_mod
    from tools import observability_snapshot as obs

    orig_class = ll_mod.LocalLogger

    class PartialFailLogger(orig_class):  # type: ignore[misc, valid-type]
        def emit_histogram(self, *args, **kwargs):  # noqa: ANN001, ANN201
            raise RuntimeError("simulated emit_histogram failure")

    monkeypatch.setattr(ll_mod, "LocalLogger", PartialFailLogger)
    # 同時 monkeypatch tools.observability_snapshot 內已 import 路徑
    count, emit_real = obs._emit_heartbeat_and_count()
    assert count == 2, "三段中 emit_histogram 失敗 → count=2 (counter + record_event)"
    assert emit_real is True, "partial success 仍視為 real emit（不全段 fallback）"


def test_emit_all_fail_returns_real_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """P1-8 邊界：三段都拋例外 → count=0 + emit_real=False。"""
    from autoclaude.infra.adapters.observability import local_logger as ll_mod
    from tools import observability_snapshot as obs

    orig_class = ll_mod.LocalLogger

    class AllFailLogger(orig_class):  # type: ignore[misc, valid-type]
        def emit_counter(self, *args, **kwargs):  # noqa: ANN001, ANN201
            raise RuntimeError("fail")

        def emit_histogram(self, *args, **kwargs):  # noqa: ANN001, ANN201
            raise RuntimeError("fail")

        def record_event(self, *args, **kwargs):  # noqa: ANN001, ANN201
            raise RuntimeError("fail")

    monkeypatch.setattr(ll_mod, "LocalLogger", AllFailLogger)
    count, emit_real = obs._emit_heartbeat_and_count()
    assert count == 0
    assert emit_real is False


def test_snapshot_to_ga_check_closure(tmp_path: Path) -> None:
    """設計閉環測試 — 寫 1 筆 snapshot 後 ga_check --window 1 必須 exit 0。

    這是 D-16 P0-X1 根本驗證：snapshot 與 ga_check 兩端 schema 對齊且
    emit_count >= 1，則 30 天觀察期可逐步累計綠標；否則 W5 db_only 永遠卡住。
    """
    from tools.observability_ga_check import main as ga_main

    history = tmp_path / ".closure_test.jsonl"
    record = collect_snapshot()
    append_snapshot(history, record)

    rc = ga_main(["--window", "1", "--history", str(history), "--json"])
    assert rc == 0, (
        f"設計閉環斷裂：snapshot 寫入後 ga_check --window 1 仍 exit {rc}；"
        f"應 exit 0（green_streak=1 >= 1）"
    )
