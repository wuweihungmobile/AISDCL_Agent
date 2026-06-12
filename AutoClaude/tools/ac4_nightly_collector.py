"""SD_Improving_08 W2 T2-C2 — AC4 nightly metric collector。

對應 [SD_Improving_08.md §3 W2 + ADR-SD08-001 漸進式升級](../docs/04_planning/SD_Improving_08.md)。

職責：
    1. 解析 pg-e2e-nightly artifact（test_pgvector_real_recall.py）
    2. 提取 recall@10 / p95 latency / CircuitBreaker open 次數
    3. 累計寫入 .ac4_history.jsonl（git ignore；CI artifact 累計）

輸入來源（擇一）：
    --junit-xml PATH    從 pytest junit XML 萃取（CI 模式優先）
    --recall FLOAT      手動指定 recall@10
    --p95 FLOAT         手動指定 p95 latency (ms)
    --cb-open INT       手動指定 CircuitBreaker open 次數
    --status STR        pass / skip / fail
    --run-id STR        GitHub Actions run_id（CI 自動帶入；本地 fallback 為 "local"）

輸出：附加一筆 JSON 至 .ac4_history.jsonl，每筆欄位固定：
    timestamp / run_id / recall_at_10 / p95_ms / circuit_breaker_open_count / status

JSONL schema 鎖定 — tests/contract/test_ac4_progress_check.py 依賴。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_HISTORY = _REPO_ROOT / ".ac4_history.jsonl"

# SD_09 W0 zero-trust audit P1-3 修復：collector 必須在解析後套門檻判定，
# 不可只看 junit 是否標 failure；否則 p95=52ms 被測試環境變數放寬通過時會被誤判 pass。
# 門檻常數對齊 tools/ac4_progress_check.py（PM #2 拍板）。
#
# SD_09 W2 audit P0-AUDIT-08 修復（紀律 #6：採集 vs 升級必須分軌）：
#   - collector 用 AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS（採集寬鬆，預設 80ms）
#   - progress_check 用 AUTOCLAUDE_STRICT_P95_THRESHOLD_MS（升級嚴格，預設 50ms）
#   - 向後相容：若新 env 未設且 AUTOCLAUDE_TEST_P95_THRESHOLD_MS 有值則用舊 env
#
# 此前兩工具共用同一 env，「雙軌」只在 ps1 內 swap 模擬 → collector 標 pass 後
# progress_check 看的就是已被寬鬆標 pass 的歷史紀錄 → 升級條件假性達標。
RECALL_MIN = 0.95


def _resolve_p95_threshold() -> float:
    """採集寬鬆門檻：collector 專用 env > 舊共用 env > 預設 80ms。"""
    new_env = os.environ.get("AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS")
    if new_env:
        return float(new_env)
    legacy_env = os.environ.get("AUTOCLAUDE_TEST_P95_THRESHOLD_MS")
    if legacy_env:
        return float(legacy_env)
    return 80.0


P95_MAX_MS = _resolve_p95_threshold()
CB_OPEN_MAX = 0


def _parse_junit_xml(path: Path) -> dict[str, Any]:
    """從 pytest --junitxml 萃取 AC4 指標。

    test_pgvector_real_recall.py 三個 test class 透過 pytest <property> 上報 metric：
      - test_recall_at_10 → property name="recall_at_10"
      - test_p95_latency_under_50ms → property name="p95_ms"
      - test_bge_failure_minimax_fallback_under_60s → property name="cb_open_count"

    本檔尚未啟用真實 PG（W2 觀察期初期 nightly 仍 skip），萃取結果為 None；
    當未來 real PG 環境就位後，properties 自動帶入實測值。
    """
    if not path.exists():
        return {"recall_at_10": None, "p95_ms": None, "cb_open_count": 0, "status": "fail"}

    tree = ET.parse(path)
    root = tree.getroot()

    metrics: dict[str, Any] = {
        "recall_at_10": None,
        "p95_ms": None,
        "cb_open_count": 0,
        "status": "pass",  # 預設 pass；任一 testcase failure / skip 會降級
    }

    has_failure = False
    has_skip = False
    for testcase in root.iter("testcase"):
        for child in testcase:
            if child.tag == "failure" or child.tag == "error":
                has_failure = True
            elif child.tag == "skipped":
                has_skip = True
        for prop in testcase.iter("property"):
            name = prop.get("name", "")
            value = prop.get("value", "")
            if name == "recall_at_10":
                try:
                    metrics["recall_at_10"] = float(value)
                except (TypeError, ValueError):
                    pass
            elif name == "p95_ms":
                try:
                    metrics["p95_ms"] = float(value)
                except (TypeError, ValueError):
                    pass
            elif name == "cb_open_count":
                try:
                    metrics["cb_open_count"] = int(value)
                except (TypeError, ValueError):
                    pass

    if has_failure:
        metrics["status"] = "fail"
    elif has_skip and metrics["recall_at_10"] is None:
        metrics["status"] = "skip"

    # P1-3 修復：套真實門檻判定（覆寫上面的 pass / fail）。
    # 規則：任一指標 None / null → fail；任一指標超門檻 → fail。
    # 仍允許 has_skip + recall_at_10 is None → 維持 skip（pg-e2e 整體未跑）。
    # SD_09 W2 audit P1-AUDIT-19 修復：has_failure 已標 fail 時保留原 reason，
    # 不覆寫為門檻 reason（避免 threshold_fail_reasons 被門檻 reason 取代）。
    if has_failure:
        # 已是 fail，門檻檢查仍跑（補充 threshold_fail_reasons 提供完整資訊）
        pass
    if metrics["status"] != "skip":
        recall = metrics.get("recall_at_10")
        p95 = metrics.get("p95_ms")
        cb_open = metrics.get("cb_open_count")
        threshold_fail_reasons: list[str] = []
        if recall is None:
            threshold_fail_reasons.append("recall_at_10=None")
        elif recall < RECALL_MIN:
            threshold_fail_reasons.append(f"recall_at_10={recall:.4f}<{RECALL_MIN}")
        if p95 is None:
            threshold_fail_reasons.append("p95_ms=None")
        elif p95 > P95_MAX_MS:
            threshold_fail_reasons.append(f"p95_ms={p95:.2f}>{P95_MAX_MS}")
        if cb_open is None:
            threshold_fail_reasons.append("cb_open_count=None")
        elif cb_open > CB_OPEN_MAX:
            threshold_fail_reasons.append(f"cb_open_count={cb_open}>{CB_OPEN_MAX}")
        if threshold_fail_reasons:
            metrics["status"] = "fail"
            metrics["threshold_fail_reasons"] = threshold_fail_reasons
    return metrics


def _build_record(args: argparse.Namespace, parsed: dict[str, Any]) -> dict[str, Any]:
    timestamp = _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or "local"

    record = {
        "timestamp": timestamp,
        "run_id": str(run_id),
        "recall_at_10": args.recall if args.recall is not None else parsed.get("recall_at_10"),
        "p95_ms": args.p95 if args.p95 is not None else parsed.get("p95_ms"),
        "circuit_breaker_open_count": (
            args.cb_open if args.cb_open is not None else parsed.get("cb_open_count", 0)
        ),
        "status": args.status or parsed.get("status", "skip"),
    }
    return record


def _utc_date_of(record: dict[str, Any]) -> str | None:
    """擷取 record timestamp 的 UTC date（YYYY-MM-DD）；無 timestamp 則 None。"""
    ts = record.get("timestamp")
    if not ts:
        return None
    try:
        dt = _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(_dt.timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return None


def append_history(record: dict[str, Any], history_path: Path) -> None:
    """附加一筆紀錄至 JSONL（同 UTC date 已存在則覆寫該筆，否則 append）。

    SD_09 W0 zero-trust audit M-05 修復：同一 UTC date 重複寫入會偽造 14 天綠。
    修復後策略：以 UTC date 為鍵；同日已存在則覆寫該筆（保留最後一次的結果，
    對齊 nightly retry 語意），避免單日多 runs 累加假象觀察期長度。
    """
    history_path.parent.mkdir(parents=True, exist_ok=True)
    new_date = _utc_date_of(record)

    # 同日去重：讀現有所有 records，移除同日紀錄後重寫
    existing: list[dict[str, Any]] = []
    if history_path.exists():
        with history_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # 跳過同 UTC date 的舊紀錄
                if new_date and _utc_date_of(parsed) == new_date:
                    continue
                existing.append(parsed)

    existing.append(record)
    with history_path.open("w", encoding="utf-8") as f:
        for rec in existing:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AC4 nightly metric collector (SD_08 W2 T2-C2).")
    parser.add_argument("--junit-xml", type=Path, help="pytest junit XML 路徑")
    parser.add_argument("--recall", type=float, help="手動指定 recall@10")
    parser.add_argument("--p95", type=float, help="手動指定 p95 latency (ms)")
    parser.add_argument("--cb-open", type=int, help="手動指定 CircuitBreaker open 次數")
    parser.add_argument(
        "--status",
        choices=["pass", "skip", "fail"],
        help="本次 nightly 狀態",
    )
    parser.add_argument("--run-id", help="GitHub Actions run_id（預設由 env GITHUB_RUN_ID 取）")
    parser.add_argument(
        "--history",
        type=Path,
        default=_DEFAULT_HISTORY,
        help="JSONL 累計檔（預設 .ac4_history.jsonl）",
    )
    args = parser.parse_args(argv)

    parsed: dict[str, Any] = {}
    if args.junit_xml:
        parsed = _parse_junit_xml(args.junit_xml)

    record = _build_record(args, parsed)
    append_history(record, args.history)

    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
