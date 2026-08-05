"""tools/drift_log_snapshot.py — SD_09 W2 nightly audit P1-5 補建。

對應 SD_Improving_09 §0.1 觀察期 #3「drift_log 30 天零非 info 事件」：
  原 run_local_nightly.ps1 stage 4 只把當日結果寫進 ps1 log，**沒有持久化累計** →
  下游無法計算「連續 N 天 zero drift」。本工具提供 jsonl 持久化（同 observability_snapshot
  模式），ps1 stage 4 在 PG 查詢後呼叫此工具寫 1 筆，30 天累計由 record line 數判定。

🔴 R76（掃描發現 R76-12）——`.drift_log_history.jsonl` 是**本機 SSOT，不入 git history**：
  它在 R76 之前是五本觀察期帳本裡唯一被 git 追蹤的一本，於是進帳會被 `git checkout -- .`
  ／`stash`／`reset --hard`／worktree 切換靜默回捲；已實測損失 UTC 2026-07-27 一整天
  （該日 nightly log 寫了、磁碟與所有 commit 都沒有那筆）。R76 起改與另外四本
  （`.observability_history.jsonl`／`.ac4_history.jsonl`／`.mutation_history.jsonl`／
  `.perf_history.jsonl`）一致，列入 `AutoClaude/.gitignore`。
  ⇒ **不要 commit 這個檔**；要看觀察期進度請跑 `python tools/drift_log_ga_check.py --json`，
  它才是權威判準（本檔只負責累計，不負責判定）。

設計原則：
  - LOC ≤ 100（data tier）
  - 同 UTC date 去重（覆寫該日最後一筆，對齊 observability_snapshot / ac4_nightly_collector）
  - 不直接連 PG（由 ps1 把計數結果以 --severity-count 傳入；避免重複 SQL 連線）
  - jsonl 格式：one record per line

對應 test：tests/tools/test_drift_log_snapshot.py（≥ 3 case）

R76 附帶清償：`datetime.UTC`（原 `datetime.timezone.utc`）——ruff UP017，py311 起的正名。
本檔在本輪被觸碰後由 AutoClaude pre-commit 的**整檔** ruff 當場攔下這 3 筆存量債；
該 leg 只掃「已暫存的 .py」，所以沒被碰過的檔會一直帶著債（見記憶
`precommit-ruff-wholefile-vs-loc-tier`）。純正名，零行為變化。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_HISTORY = Path(".drift_log_history.jsonl")


def _utc_date(ts_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def build_record(
    severity_non_info_count: int,
    table_exists: bool = True,
    ts: str | None = None,
) -> dict[str, Any]:
    """組裝 drift_log 當日 snapshot record。

    Args:
        severity_non_info_count: PG `SELECT COUNT(*) FROM drift_log WHERE severity != 'info'`
            的數值；ps1 在 PG 連得上時填入；連不上 → 由 caller 決定是否寫入。
        table_exists: drift_log 表是否存在（False 表 alembic 落後）。
        ts: ISO timestamp；None 時用 now。
    """
    return {
        "ts": ts or datetime.now(UTC).isoformat(timespec="seconds"),
        "drift_log_table_exists": bool(table_exists),
        "severity_non_info_count": int(severity_non_info_count),
        "passed": (bool(table_exists) and int(severity_non_info_count) == 0),
    }


def append_snapshot(history_path: Path, record: dict[str, Any]) -> str:
    """append snapshot 至 jsonl，同 UTC date 去重。

    SD_09 W3 Round 2 audit P0-3 修復（紀律 #9 跨 stage 一致性）：
      同 UTC date 已存在時，**優先保留 `drift_log_table_exists=True` 的紀錄**
      （= 真實取值；避免一日多跑 SKIP 覆寫真實結果）。
      語意：當日先跑真實取值 → 後續同日 SKIP 應視為「沒有新資訊」不覆寫；
      當日先 SKIP → 後續真實取值才能升級覆寫。

    Returns: "appended" / "replaced" / "kept_existing"
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

    # P0-3 修復：先掃描同日是否已有 table_exists=True 紀錄
    new_record_has_table = bool(record.get("drift_log_table_exists", True))
    new_lines: list[dict[str, Any]] = []
    same_day_exists = False
    same_day_kept_real = False
    for entry in existing:
        if _utc_date(entry.get("ts", "")) == record_date:
            same_day_exists = True
            entry_has_table = bool(entry.get("drift_log_table_exists", True))
            # 新紀錄 table_missing 但舊紀錄是真實取值 → 保留舊紀錄
            if entry_has_table and not new_record_has_table:
                new_lines.append(entry)
                same_day_kept_real = True
                continue
            # 其餘情況（兩者同型 / 新紀錄是真實取值）→ 跳過舊紀錄走 replace
            continue
        new_lines.append(entry)

    if same_day_kept_real:
        # 不寫新 record；保留舊真實紀錄
        history_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in new_lines) + "\n",
            encoding="utf-8",
        )
        return "kept_existing"

    new_lines.append(record)
    history_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in new_lines) + "\n",
        encoding="utf-8",
    )
    return "replaced" if same_day_exists else "appended"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="drift_log snapshot collector (P1-5)")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument(
        "--severity-count",
        type=int,
        required=True,
        help="PG drift_log severity!='info' rows count (ps1 stage 4 query result)",
    )
    parser.add_argument(
        "--table-missing",
        action="store_true",
        help="drift_log 表不存在（alembic 落後）→ 不視為觀察期一天",
    )
    parser.add_argument("--print", action="store_true")
    args = parser.parse_args(argv)

    record = build_record(
        severity_non_info_count=args.severity_count,
        table_exists=not args.table_missing,
    )
    action = append_snapshot(args.history, record)
    print(f"[drift_log-snapshot] {action} 1 record at {args.history}")
    if args.print:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
