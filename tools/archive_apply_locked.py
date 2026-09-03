#!/usr/bin/env python3
"""序列化保護版的 `archive_defect_log.py --apply` 入口（DEF-200-222 判準②）。

## 為何另開一支檔而不是直接改 `archive_defect_log.py` 本體

`archive_defect_log.py` 已卡在 `AutoClaude/tools/check_loc_budget.py` 的
`SPECIAL_FILES` raw-line 棘輪頂格（現查 `python AutoClaude/tools/check_loc_budget.py
--json` 的 `special_files` 欄；落地當下該檔餘裕為 0）。往上調需要先在缺陷帳本具名
核准（見該常數旁的重釘慣例），而本包職責範圍不含帳本結案編修。故鎖以「呼叫外殼」
形態接線：本檔委派 `archive_defect_log.apply()`（零複本，判準與寫入邏輯仍只有一份），
只在委派前後多包一層鎖；`check_archive_required.py` 的導引訊息已改為指向本檔。

🔴 **誠實劃界**：本鎖只保護「經由本檔呼叫」的路徑。有人繞過本檔、直接
`python tools/archive_defect_log.py --apply ...` 執行仍不受本鎖保護——本檔與
`check_archive_required.py` 的導引訊息一致指向本檔，但語言層面的約定無法阻止有人
手動繞過直接呼叫底層工具。

用法：
  python3 tools/archive_apply_locked.py --archive-num 31 [--ack-handoff DEF-101-517,...]
      [--note "..."] [--only DEF-x,...] [--keep DEF-y,...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護
import archive_defect_log as _archiver  # noqa: E402
from lib import apply_lock as _lock  # noqa: E402

#: 鎖檔位置：帳本家族所在目錄下的隱藏檔（同一個目錄樹，避免落在不同磁碟/掛載點）。
_LOCK_PATH = _archiver._QUALITY_DIR / ".archive_apply.lock"
#: 排隊等鎖的逾時上限（秒）：一次 `--apply` 正常應在數秒內完成（純文字檔案讀寫），
#: 60 秒已遠高於正常耗時，逾時代表確有異常（例如持鎖行程真的卡住）。
_LOCK_TIMEOUT_SECONDS = 60.0
#: 陳舊鎖回收門檻（秒）：遠高於單次 `--apply` 的正常耗時，避免把「還在正常執行中」
#: 誤判為「持鎖行程已死」。
_LOCK_STALE_SECONDS = 300.0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="序列化保護的帳本歸檔 --apply 入口（DEF-200-222）"
    )
    ap.add_argument("--archive-num", type=int, required=True,
                    help="歸檔編號（同 archive_defect_log.py --apply 的同名旗標）")
    ap.add_argument("--ack-handoff", default="",
                    help="逗號分隔的 DEF-ID，具名承認搬遷帶交棒字樣的列")
    ap.add_argument("--note", default="（未填）", help="寫入 archive 標頭的操作備註")
    ap.add_argument("--only", default="", help="逗號分隔的 DEF-ID：只搬這幾筆")
    ap.add_argument("--keep", default="", help="逗號分隔的 DEF-ID：這幾筆不搬")
    a = ap.parse_args(argv)
    ack, only, keep = (frozenset(x.strip() for x in s.split(",") if x.strip())
                       for s in (a.ack_handoff, a.only, a.keep))
    try:
        with _lock.acquire(_LOCK_PATH, timeout=_LOCK_TIMEOUT_SECONDS,
                            stale_after=_LOCK_STALE_SECONDS):
            return _archiver.apply(a.archive_num, ack, a.note, only, keep)
    except _lock.LockBusyError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
