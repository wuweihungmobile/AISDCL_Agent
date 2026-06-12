"""tools/drift_log_ga_check.py — SD_09 W3 Round 2 audit P0-3 補建。

對應 SD_Improving_09 §0.1 觀察期 #3「drift_log 30 天零非 info 事件」：
  `.drift_log_history.jsonl` 由 `tools/drift_log_snapshot.py` 累計；本工具
  讀取後計算 green_streak（連續 `passed=True` 天數）並輸出 GA 取證狀態。
  仿 `tools/observability_ga_check.py` 設計，紀律 #4「驗證鏡子自身要被驗證」。

通過：green_streak >= window（預設 30）→ exit 0
不通過：exit 1（含無紀錄檔；訊息「nightly 採集未啟動」）

對應：
    - ADR-SD09 §0.1 觀察期 #3
    - SD09_Execution_Guide T0-D3
    - risk_log §15 R-SD09-D-1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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
                records.append({"_invalid": True, "_raw": line})
    return records


def _is_green(record: dict[str, Any]) -> tuple[bool, str]:
    """判定單筆紀錄是否為「綠」。

    Returns:
        (是否綠, 失敗原因說明)
    """
    if record.get("_invalid"):
        return False, "invalid_json_line"

    # passed=True 是 drift_log_snapshot.build_record 的權威欄位
    # (table_exists=True AND severity_non_info_count == 0)
    passed = record.get("passed")
    if passed is True:
        return True, ""

    # 紀錄已標示不通過：解析具體原因供 last_failure_reason 使用
    if record.get("drift_log_table_exists") is False:
        return False, "drift_log_table_exists=False (alembic head 落後)"
    cnt = record.get("severity_non_info_count")
    if isinstance(cnt, (int, float)) and cnt > 0:
        return False, f"severity_non_info_count={cnt} (>0, 觀察期 #3 違反)"
    return False, f"passed={passed!r} (need True)"


def _compute_green_streak(records: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    """從最後一筆往回算連續綠的天數。"""
    judgements: list[dict[str, Any]] = []
    for r in records:
        ok, reason = _is_green(r)
        judgements.append({
            "date": r.get("ts") or r.get("date") or r.get("timestamp"),
            "green": ok,
            "reason": reason,
        })

    streak = 0
    for j in reversed(judgements):
        if j["green"]:
            streak += 1
        else:
            break
    return streak, judgements


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SD_09 W3 Round 2 audit P0-3 — drift_log 30 天零事件 GA 取證工具"
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
        default=Path(".drift_log_history.jsonl"),
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
        msg = "nightly 採集未啟動：找不到 .drift_log_history.jsonl 或內容為空"
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
                f"(total {len(records)} records) → drift_log 30 天零事件 GA 取證通過"
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
