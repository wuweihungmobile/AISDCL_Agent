"""tools/_backfill_emit_real.py — SD_09 W3 Round 2 audit P1-1 一次性 backfill 工具。

職責：
  讀 .observability_history.jsonl 對所有缺 `observability_emit_real` 欄位的舊紀錄
  寫入 `True`（向下相容寬鬆 baseline）。新紀錄已由 tools/observability_snapshot.py
  正確寫入；本 script 僅供首次升級時人工執行。

執行：
  python tools/_backfill_emit_real.py [--dry-run] [--history PATH]

設計原則：
  - 需 `--apply` 才實際寫入（預設 dry-run 印出影響筆數）
  - 寫入前 backup 至 `<history>.bak`
  - LOC ≤ 100（data tier）
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

DEFAULT_HISTORY = Path(".observability_history.jsonl")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill observability_emit_real=True (P1-1)")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument(
        "--apply", action="store_true", help="實際寫入（預設 dry-run 只統計）"
    )
    args = parser.parse_args(argv)

    if not args.history.exists():
        print(f"[backfill] history not found: {args.history}")
        return 1

    lines: list[dict] = []
    invalid: list[str] = []
    for line in args.history.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            invalid.append(line)

    missing_count = sum(1 for r in lines if "observability_emit_real" not in r)
    print(f"[backfill] total_records={len(lines)} missing_emit_real={missing_count} invalid={len(invalid)}")

    if missing_count == 0:
        print("[backfill] nothing to do")
        return 0

    if not args.apply:
        print("[backfill] DRY-RUN — pass --apply to actually write")
        return 0

    # backup
    backup = args.history.with_suffix(args.history.suffix + ".bak")
    shutil.copy2(args.history, backup)
    print(f"[backfill] backup written: {backup}")

    for r in lines:
        if "observability_emit_real" not in r:
            r["observability_emit_real"] = True

    args.history.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in lines) + "\n",
        encoding="utf-8",
    )
    print(f"[backfill] APPLIED — {missing_count} records updated; invalid lines preserved=NO (purged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
