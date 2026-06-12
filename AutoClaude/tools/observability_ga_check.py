"""SD_09 W0 T0-O1 — 30 天 nightly 全綠取證工具（QA-M4 修復項）。

讀取 ``.observability_history.jsonl`` 累計紀錄，驗證：
    - IObservabilityPort **proof-of-life heartbeat** 計數（``observability_emit_count > 0``；
      SD_09 W3 audit P0-OBS-1 語義澄清：本欄位為 nightly 採集時 3 次 heartbeat emit 證明
      port 可運作，**非** runtime cumulative counter — 詳見 tools/observability_snapshot.py
      ``_emit_heartbeat_and_count`` docstring）
    - trace_id ContextVar 連續性（``trace_id_continuity == true``）
    - KB metric 4 項 snapshot（hit_rate / query_p95_ms / strategy_rotation / cache_eviction）

通過：green_streak >= window（預設 30）→ exit 0
不通過：exit 1（含無紀錄檔；訊息「nightly 採集未啟動」）

對應：
    - ADR-SD09-001 §2.5/§2.6 — W5 db_only 切換 (1a)(1b) 雙條件唯一取證
    - SD09_Execution_Guide T0-O1
    - risk_log §15 R-SD09-O-1
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

# KB metric 4 項（PM 拍板）
# 注意：必須與 autoclaude.utils.knowledge_base_metrics.KnowledgeBaseMetrics.snapshot()
# 真實 SSOT 對齊 — strategy_rotation_count / cache_eviction_count 含 `_count` 後綴。
# 修復來源：SD_09 W0 G0 zero-trust audit 第 4 輪 P0-X1 L2（設計閉環 KB schema 對齊）。
KB_METRIC_REQUIRED_KEYS = (
    "hit_rate",
    "query_p95_ms",
    "strategy_rotation_count",
    "cache_eviction_count",
)

# SD_09 W3 Round 3 audit P1-2 修復：紀律 #10 引入 observability_emit_real 欄位的 cutoff 日期。
# - ts < cutoff 的紀錄：缺欄位寬鬆放行（保留歷史；不可 backfill 偽造，紀律 #10）
# - ts >= cutoff 的紀錄：缺欄位強制拒絕（新 nightly 必須寫入欄位）
# 取代 W3 Round 2 P1-1「最新 3 筆 strict」滑動窗口設計（語義不明確）。
EMIT_REAL_REQUIRED_FROM = _dt.datetime(2026, 5, 24, tzinfo=_dt.timezone.utc)


def _parse_ts(record: dict[str, Any]) -> _dt.datetime | None:
    """Parse record timestamp from ``ts`` / ``timestamp`` / ``date`` 欄位；None-safe。"""
    ts = record.get("ts") or record.get("timestamp") or record.get("date")
    if not isinstance(ts, str) or not ts:
        return None
    try:
        return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _load_history(path: Path) -> list[dict[str, Any]]:
    """讀取 JSONL，每行一筆 record；忽略空行 / 壞行。"""
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # 壞行視為不算 green 但不阻塞讀取
                records.append({"_invalid": True, "_raw": line})
    return records


def _is_green(record: dict[str, Any], *, strict_emit_real: bool = False) -> tuple[bool, str]:
    """判定單筆紀錄是否為「綠」。

    Args:
        record: jsonl record
        strict_emit_real: 若 True 則 observability_emit_real 缺欄位視為 fail
            （W3 Round 2 P1-1 滑動窗口語意；W3 Round 3 P1-2 起改由 _compute_green_streak
            依 ts 與 EMIT_REAL_REQUIRED_FROM cutoff 決定）

    Returns:
        (是否綠, 失敗原因說明)
    """
    if record.get("_invalid"):
        return False, "invalid_json_line"

    emit_count = record.get("observability_emit_count", 0)
    if not isinstance(emit_count, (int, float)) or emit_count <= 0:
        return False, f"observability_emit_count={emit_count!r} (need > 0)"

    # F1 修復（SD_09 W3 zero-trust audit 2026-05-24）：紀律 #4 — 區分真實 LocalLogger emit
    # vs import 失敗 fallback；舊紀錄無此欄位以 True 寬鬆處理避免歷史累計被打斷
    # Round 3 P1-2 修復：strict_emit_real 判定改由 ts cutoff 控制（_compute_green_streak 注入）：
    #   - ts < EMIT_REAL_REQUIRED_FROM (2026-05-24)：legacy 寬鬆放行 + warning
    #   - ts >= EMIT_REAL_REQUIRED_FROM：strict 模式，缺欄位 / 為 False 強制 fail
    # Round 4 P2-AUDIT-R3-2 修復：原 docstring 提及「最新 3 筆滑動窗口」為 Round 2 舊設計，
    # 已隨 Round 3 改為 cutoff-based；此處同步文字避免 reviewer 誤讀。
    if "observability_emit_real" not in record:
        if strict_emit_real:
            return False, "observability_emit_real missing (strict mode; ts >= EMIT_REAL_REQUIRED_FROM cutoff requires explicit field)"
    elif record.get("observability_emit_real") is False:
        return False, "observability_emit_real=False (LocalLogger fallback mock; not real emit)"

    if record.get("trace_id_continuity") is not True:
        return False, f"trace_id_continuity={record.get('trace_id_continuity')!r}"

    snapshot = record.get("kb_metric_snapshot")
    if not isinstance(snapshot, dict):
        return False, "kb_metric_snapshot missing or not object"
    missing = [k for k in KB_METRIC_REQUIRED_KEYS if k not in snapshot]
    if missing:
        return False, f"kb_metric_snapshot missing keys: {missing}"

    return True, ""


def _compute_green_streak(records: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    """從最後一筆往回算連續綠的天數。

    SD_09 W3 Round 3 audit P1-2 修復：strict_emit_real 改由 ts cutoff 決定（取代 Round 2
    最新 3 筆滑動窗口）：
        - ts < EMIT_REAL_REQUIRED_FROM (2026-05-24)：legacy 寬鬆，缺欄位通過 + 印 warning
        - ts >= EMIT_REAL_REQUIRED_FROM：strict，缺欄位強制拒絕
        - ts 無法 parse 或 None：fail-safe → strict（避免無 ts 紀錄繞過判定）

    Returns:
        (green_streak, per_record_judgement)
    """
    judgements: list[dict[str, Any]] = []
    legacy_lenient_count = 0
    for r in records:
        ts = _parse_ts(r)
        # ts 無法 parse / None → strict（fail-safe）
        if ts is None:
            strict = True
        else:
            strict = ts >= EMIT_REAL_REQUIRED_FROM

        # legacy 寬鬆紀錄統計（只在缺欄位時才印 warning）
        if not strict and "observability_emit_real" not in r:
            legacy_lenient_count += 1

        ok, reason = _is_green(r, strict_emit_real=strict)
        judgements.append({
            "date": r.get("date") or r.get("ts") or r.get("timestamp"),
            "green": ok,
            "reason": reason,
            "strict_mode": strict,
        })

    if legacy_lenient_count > 0:
        sys.stderr.write(
            f"[observability_ga_check] WARN: {legacy_lenient_count} legacy record(s) "
            f"before {EMIT_REAL_REQUIRED_FROM.date().isoformat()} missing "
            "observability_emit_real; strict disabled (lenient pass)\n"
        )

    streak = 0
    for j in reversed(judgements):
        if j["green"]:
            streak += 1
        else:
            break
    return streak, judgements


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SD_09 W5 雙條件可觀測性 GA 取證工具"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="連續綠天數門檻（預設 30 天）",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=Path(".observability_history.jsonl"),
        help="nightly 累計紀錄檔（每日一行 JSON record）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="輸出 JSON 格式（機器可讀；CI 用）",
    )
    args = parser.parse_args(argv)

    history_path: Path = args.history
    records = _load_history(history_path)

    if not records:
        msg = "nightly 採集未啟動：找不到 .observability_history.jsonl 或內容為空"
        result = {
            "status": "no_history",
            "green_streak": 0,
            "window": args.window,
            "history_path": str(history_path),
            "message": msg,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"[FAIL] {msg}", file=sys.stderr)
        return 1

    streak, judgements = _compute_green_streak(records)
    passed = streak >= args.window
    last_failure_reason = ""
    if not passed:
        # 找最後一筆非綠的原因
        for j in reversed(judgements):
            if not j["green"]:
                last_failure_reason = j["reason"]
                break

    result = {
        "status": "ready" if passed else "observing",
        "green_streak": streak,
        "window": args.window,
        "total_records": len(records),
        "history_path": str(history_path),
        "last_failure_reason": last_failure_reason,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if passed:
            print(
                f"[PASS] green_streak={streak} >= window={args.window} "
                f"(total {len(records)} records) → GA 取證通過"
            )
        else:
            print(
                f"[FAIL] green_streak={streak} < window={args.window} "
                f"(total {len(records)} records)",
                file=sys.stderr,
            )
            if last_failure_reason:
                print(f"        last_failure_reason: {last_failure_reason}", file=sys.stderr)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
