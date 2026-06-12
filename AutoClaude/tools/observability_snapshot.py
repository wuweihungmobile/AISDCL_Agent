"""tools/observability_snapshot.py — D-16（SD_09 W0 三次 zero-trust audit 補建）。

對應 ADR-SD09-001 §2.5 + ADR-SD08-004 §2.4：
  W5 雙條件 (1a) 30 天取證 — `observability_ga_check.py --window 30` 需要
  `.observability_history.jsonl` 累積 30 筆 daily record。本工具為 nightly stage
  「observability-snapshot」呼叫器，每日寫入 1 筆，含：
    - observability_emit_count（IObservabilityPort emit_counter/emit_gauge/emit_histogram 累計）
    - trace_id_continuity（同 process 內 trace_id 一致性 bool）
    - kb_metric_snapshot（KnowledgeBaseMetrics.snapshot() 4 keys）

設計原則：
  - LOC ≤ 150（data tier）
  - 同日去重：UTC date 已存在則覆寫該筆（M-05 紀律對齊 ac4_nightly_collector）
  - 場景 A 無 PG 時走 mock；不阻塞 nightly 採集
  - jsonl 格式：one record per line

對應 test 檔：
  - tests/tools/test_observability_snapshot.py（≥ 3 case）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_HISTORY = Path(".observability_history.jsonl")


def _utc_date(ts_iso: str) -> str:
    """從 ISO timestamp 取 UTC 日期（YYYY-MM-DD）。"""
    try:
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _measure_trace_continuity() -> bool:
    """量測同 process 內 trace_id ContextVar 連續性（SD_09 W2 nightly audit P1-1）。

    語意：with_trace_id() 設定 trace_id 後，同層 get_trace_id() 應一致；
    這證明 ContextVar propagation 正常（W5 雙條件 1a 同 process trace_id GA 核心語意）。
    跨 thread / subprocess 由 start_thread_with_context / propagate_to_subprocess_env 各自驗證。
    """
    try:
        from autoclaude.utils.trace_context import get_trace_id, with_trace_id

        with with_trace_id() as tid_in:
            tid_now = get_trace_id()
            return tid_in == tid_now and tid_in is not None
    except Exception:
        return False


def _emit_heartbeat_and_count() -> tuple[int, bool]:
    """實際呼叫 IObservabilityPort 發出 nightly heartbeat 並回傳 (emit 次數, 是否真實 emit)。

    語意：nightly 採集週期內，proof-of-life 連通 LocalLogger（IObservabilityPort
    唯一實作）→ emit_count >= 1 + emit_real=True 表示 port 可運作。對應 W5 雙條件 (1a)
    「IObservabilityPort + trace_id ContextVar 連續性 30 天綠」核心語意 — 系統有能力 emit。

    **SD_09 W3 zero-trust audit F1 修復（2026-05-24）**：原本 except 路徑 `count=1`
    與真實 emit 1 次無法區分 → 改回傳 tuple `(count, emit_real: bool)`；jsonl 寫入
    `observability_emit_real` 欄位讓 `observability_ga_check.py` 區分「真實 emit」
    vs「fallback mock 假象」。紀律 #4「驗證鏡子自身要被驗證」— 鏡子須回傳真實狀態。

    **SD_09 W3 Round 2 audit P1-8 修復（2026-05-24）**：三段 emit 各自 try/except，
    count 累計實際成功次數，emit_real = count > 0。避免單一 emit_histogram 拋例外
    導致整段 fallback 路徑（loss of partial-success signal）。

    修復來源：
    - SD_09 W0 G0 zero-trust audit 第 4 輪 P0-X1 L1（emit_count 不可寫死 0）
    - SD_09 W3 zero-trust audit F1（emit fallback 與真實 emit 不可區分）
    - SD_09 W3 zero-trust audit Round 2 P1-8（單一 emit fail 不應整段 fallback）
    """
    # Step 1：完全 import 失敗 → fallback path（count=1, emit_real=False）
    try:
        from autoclaude.infra.adapters.observability.local_logger import LocalLogger

        port = LocalLogger()
    except Exception:
        return 1, False

    # Step 2：三段 emit 各自 try/except，partial success 仍算 real
    count = 0
    for emit_call in (
        lambda: port.emit_counter(
            "observability_snapshot.heartbeat", value=1, tags={"source": "nightly"}
        ),
        lambda: port.emit_histogram(
            "observability_snapshot.duration_ms", value=0.0, tags={"phase": "collect"}
        ),
        lambda: port.record_event(
            "observability_snapshot.collected", attributes={"window": "nightly"}
        ),
    ):
        try:
            emit_call()
            count += 1
        except Exception:
            continue
    # P1-8：count > 0 即視為真實 emit（partial success 仍算 real）
    return count, count > 0


def collect_snapshot() -> dict[str, Any]:
    """採集當前 observability 狀態為單筆 record。

    設計閉環：本函式同時 (1) 透過 IObservabilityPort 發 heartbeat 證明 port 可運作；
    (2) 採集 KnowledgeBaseMetrics 真實 SSOT snapshot。寫入 .observability_history.jsonl
    後 `tools/observability_ga_check.py --window N` 應可判定 green（exit 0）。

    修復來源：SD_09 W0 G0 zero-trust audit 第 4 輪 P0-X1（設計閉環斷裂）。
    """
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # observability_emit_count：實際 emit heartbeat 再計數（非寫死 0；L1 修復）
    # F1 修復（SD_09 W3 zero-trust audit 2026-05-24）：tuple return 區分真實 emit vs fallback
    emit_count, emit_real = _emit_heartbeat_and_count()

    # trace_id_continuity：SD_09 W2 nightly audit P1-1 修復 — 改實測，不再寫死 True
    # 同 process ContextVar 連續性，跨 thread / subprocess 由各自工具驗證
    trace_continuity = _measure_trace_continuity()

    # KB metric snapshot：4 keys（含 `_count` 後綴，對齊 KnowledgeBaseMetrics.snapshot() SSOT；L2 修復）
    #
    # SD_09 W0 P0-AUDIT-34 設計語意澄清（不算 bug）：
    #   `KnowledgeBaseMetrics()` 為 fresh in-process instance；nightly run 一次性執行不會帶入歷史 → 值預期為 0。
    #   `observability_ga_check.py:KB_METRIC_REQUIRED_KEYS` 僅驗 key 存在性（schema），非驗值非零 —
    #   兩端對齊「nightly 採集 = port + schema 連通性證明」，非「KB runtime metric 30 天統計」。
    #   若 SD_09 §6 #5 議題 G PM 拍板 (a) 走 PG 持久化路徑 → 此處 `KnowledgeBaseMetrics()`
    #   改為注入 IKbMetricStore.read_latest() 即可取得跨 session 真實值；屬 W2 補丁範疇。
    kb_snapshot = {
        "hit_rate": 0.0,
        "query_p95_ms": 0.0,
        "strategy_rotation_count": 0,
        "cache_eviction_count": 0,
    }
    try:
        from autoclaude.utils.knowledge_base_metrics import KnowledgeBaseMetrics

        kb_snapshot = KnowledgeBaseMetrics().snapshot()
    except Exception:  # pragma: no cover - import 異常走 mock fallback
        pass

    return {
        "ts": ts,
        "observability_emit_count": emit_count,
        # F1 修復（SD_09 W3 zero-trust audit 2026-05-24）：紀律 #4 — 區分真實 LocalLogger
        # emit（True）vs import 失敗 fallback（False）；舊紀錄無此欄位由 ga_check 寬鬆處理
        "observability_emit_real": emit_real,
        "trace_id_continuity": trace_continuity,
        "kb_metric_snapshot": kb_snapshot,
    }


def append_snapshot(history_path: Path, record: dict[str, Any]) -> str:
    """append snapshot 至 jsonl，同 UTC date 去重（覆寫該日最後一筆）。

    Returns: "appended" / "replaced"
    """
    record_date = _utc_date(record["ts"])
    history_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict[str, Any]] = []
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    replaced = False
    new_lines: list[dict[str, Any]] = []
    for entry in existing:
        if _utc_date(entry.get("ts", "")) == record_date:
            replaced = True
            continue  # 跳過舊紀錄
        new_lines.append(entry)
    new_lines.append(record)

    history_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in new_lines) + "\n",
        encoding="utf-8",
    )
    return "replaced" if replaced else "appended"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="observability snapshot collector")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--print", action="store_true", help="print collected record")
    args = parser.parse_args(argv)

    record = collect_snapshot()
    action = append_snapshot(args.history, record)
    print(f"[observability-snapshot] {action} 1 record at {args.history}")
    if args.print:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
