"""tools/drift_log_ga_check.py — SD_09 W3 Round 2 audit P0-3 補建。

對應 SD_Improving_09 §0.1 觀察期 #3「drift_log 30 天零非 info 事件」：
  `.drift_log_history.jsonl` 由 `tools/drift_log_snapshot.py` 累計；本工具
  讀取後計算 green_streak（連續 `passed=True` 天數）並輸出 GA 取證狀態。
  仿 `tools/observability_ga_check.py` 設計，紀律 #4「驗證鏡子自身要被驗證」。

通過：green_streak >= window **且** 證據新鮮 **且** 窗內連續 → exit 0
不通過：exit 1（含無紀錄檔；訊息「nightly 採集未啟動」）

🔴 R76（掃描發現 R76-13）——window 量的是**紀錄筆數**，不是日曆天數：
  原判準只有 `green_streak >= window` 一條，於是「30 筆」被當成「30 天」宣告 GA 通過，
  而兩者只在「每天都真的有跑」時才相等。實測 observability 那本以「30 筆橫跨 58 個
  日曆天、窗內含一段 12 天全黑」宣告「30 天零事件取證通過」；drift 這本同期 span 65 天、
  10 個 >1 日 gap。**筆數判準對「整段沒跑」零偵測**——採集器停擺時它不會退步，只會停住，
  而停住看起來跟「還在觀察」一模一樣。
  修法刻意**沿用 tools/ac4_progress_check.py 已存在的欄位語意**（該檔 ADR-SD09-012 L-7
  已經解過同一題），不另發明第三套：
    ① `staleness_days`＝最後一筆距今 UTC 天數，超過 `STALENESS_MAX_DAYS` ⇒ status='stale'。
    ② 窗內連續性＝last-window 的 (最後一筆日 − 第一筆日 + 1) ≤ window × 係數，
       超過 ⇒ status='sparse'。
  兩者都 rc≠0。`.drift_log_history.jsonl` 是本機 SSOT（見 drift_log_snapshot.py 檔頭）。

對應：
    - ADR-SD09 §0.1 觀察期 #3
    - SD09_Execution_Guide T0-D3
    - risk_log §15 R-SD09-D-1
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

# 🔴 兩種載入方式各走一條路，且**同一個 process 內只會走到其中一條**——這一點是刻意的：
# 若兩條路都可能成立，`tools.ga_window` 與 `ga_window` 會是兩個不同的 module 物件，
# 共用層就退化成「同一份原始碼的兩個實例」，parity 鎖的 `is` 也會假紅（實測踩過）。
#   · `from tools.drift_log_ga_check import …`（pytest／其他模組）⇒ AutoClaude 在 path 上
#     ⇒ 走 `from tools import ga_window`；
#   · `python tools/drift_log_ga_check.py`（nightly 載具）⇒ sys.path[0] 是 tools/、
#     AutoClaude **不在** path 上 ⇒ 上一行 ImportError ⇒ 走裸 `import ga_window`。
try:
    from tools import ga_window as _ga_window
except ImportError:  # pragma: no cover - 以腳本形態執行時才會走到
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ga_window as _ga_window  # noqa: E402

# ── R76：兩個「時間」面的門檻。🔴 **值與 WHY 的唯一的家是 `tools/ga_window.py`**
# （R76 四方複審 SD-04：原本兩支 checker 各存一份，實測單邊改一個常數、兩支公然不一致
# 而三支測試檔仍 108 passed rc=0——沒有任何東西會叫）。此處只做 re-export 讓既有
# 消費者（測試、`--json` 輸出、姊妹檔文件引用）的匯入路徑不變。
STALENESS_MAX_DAYS = _ga_window.STALENESS_MAX_DAYS
WINDOW_SPAN_MAX_FACTOR = _ga_window.WINDOW_SPAN_MAX_FACTOR


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


# 🔴 以下四個名字全部 **re-export 自 `tools/ga_window.py`**，不在本檔另寫一份
# （R76 四方複審 SD-04）：R76 落地首版與 `observability_ga_check.py` 有一整塊 112 行
# 逐字相同的複本、零 parity 鎖，而且**在同一輪就已經走岔**（obs 的 `_parse_ts` 沒做
# tz 正規化 ⇒ 同一筆 naive 時戳，這邊回 ready、那邊 TypeError 當場炸）。
# 先例＝`tools/archive_defect_log.ACTIVE_STATUS_RE = _ledger_index.ACTIVE_STATUS_RE`；
# 「是同一個物件」由 `tests/tools/test_drift_log_ga_check.py` 尾端那組鎖以 `is` 綁住。
_parse_ts = _ga_window.parse_ts
_staleness_days = _ga_window.staleness_days
_window_calendar_span = _ga_window.window_calendar_span


def evaluate(
    records: list[dict[str, Any]],
    *,
    window: int,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """純函式判定；判準本體見 `tools/ga_window.evaluate`（兩支 checker 共用同一份）。

    本檔唯一不共用的是 `_compute_green_streak`——drift 的綠判準看
    `drift_log_table_exists`／`severity_non_info_count`，與 obs 的 legacy/strict ts cutoff
    是兩件不同的事，硬合併會變成一個帶旗標的四不像。故它以參數注入。
    """
    return _ga_window.evaluate(
        records, window=window, streak_fn=_compute_green_streak, now=now)


def main(argv: list[str] | None = None) -> int:
    # DEF-82-001/DEF-101-070 家族慣例：報表含中文/非 ASCII 符號，Windows cp950 console
    # 直接 print 會 UnicodeEncodeError 中斷；stdout + stderr 皆強制 utf-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(
        description="SD_09 W3 Round 2 audit P0-3 — drift_log 30 天零事件 GA 取證工具"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help=(
            "連續綠**紀錄筆數**門檻（預設 30 筆）。R76 訂正：本值的單位是筆數不是日曆天"
            "——日曆天由 staleness_days 與 window_span_days 兩個獨立判準各自把關"
        ),
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

    result = evaluate(records, window=args.window)
    result["history_path"] = str(history_path)
    passed = result["status"] == "ready"
    # 三個量在 PASS／FAIL 兩向都印：R76 之前 PASS 訊息只有筆數，於是「30 筆橫跨 58 天」
    # 這個事實在人看得到的那一行上完全不存在。
    span = (
        f"span={result['window_span_days']}/{result['window_span_max_days']}d "
        f"max_gap={result['window_max_gap_days']}d "
        f"stale={result['staleness_days']}/{result['staleness_max_days']}d"
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif passed:
        print(
            f"[PASS] green_streak={result['green_streak']} >= window={args.window} "
            f"(total {len(records)} records; {span}) → drift_log 觀察期 GA 取證通過"
        )
    else:
        print(
            f"[FAIL] status={result['status']} green_streak={result['green_streak']}"
            f"/{args.window} (total {len(records)} records; {span})",
            file=sys.stderr,
        )
        if result["last_failure_reason"]:
            print(
                f"        last_failure_reason: {result['last_failure_reason']}",
                file=sys.stderr,
            )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
