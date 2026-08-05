"""SD_09 W0 T0-O1 — 30 天 nightly 全綠取證工具（QA-M4 修復項）。

讀取 ``.observability_history.jsonl`` 累計紀錄，驗證：
    - IObservabilityPort **proof-of-life heartbeat** 計數（``observability_emit_count > 0``；
      SD_09 W3 audit P0-OBS-1 語義澄清：本欄位為 nightly 採集時 3 次 heartbeat emit 證明
      port 可運作，**非** runtime cumulative counter — 詳見 tools/observability_snapshot.py
      ``_emit_heartbeat_and_count`` docstring）
    - trace_id ContextVar 連續性（``trace_id_continuity == true``）
    - KB metric 4 項 snapshot（hit_rate / query_p95_ms / strategy_rotation / cache_eviction）

通過：green_streak >= window **且** 證據新鮮 **且** 窗內連續 → exit 0
不通過：exit 1（含無紀錄檔；訊息「nightly 採集未啟動」）

🔴 R76（掃描發現 R76-13）——window 量的是**紀錄筆數**，不是日曆天數：
  本工具此前唯一的判準是 `green_streak >= window`，於是「30 筆」被當成「30 天」。
  實測（2026-08-05）：last-30 筆橫跨 **58 個日曆天**、窗內 9 個 >1 日 gap、最大一段
  `2026-06-29 -> 2026-07-11 = 12 天全黑`，而工具照樣印
  `[PASS] green_streak=44 >= window=30 → GA 取證通過`。**筆數判準對「整段沒跑」零偵測**
  ——採集器停擺時它不會退步，只會停住，而停住看起來跟「還在觀察」一模一樣。
  修法沿用 tools/ac4_progress_check.py 已有的欄位語意（ADR-SD09-012 L-7 解過同一題），
  不另發明第三套：①`staleness_days` 超標 ⇒ status='stale'；②last-window 日曆跨度
  超過 window×係數 ⇒ status='sparse'。兩者 rc≠0。
  與 tools/drift_log_ga_check.py **刻意逐段同構**（兩支工具的 rc↔status 契約相同，
  run_local_nightly.ps1 的兩支 helper 也是逐行同構的複本）。

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

# 🔴 兩種載入方式各走一條路，且同一個 process 內只會走到其中一條——理由與姊妹檔
# `tools/drift_log_ga_check.py` 同位置那段完全相同（兩條都成立會產生兩個 module 物件，
# 共用層退化成「同一份原始碼的兩個實例」）。
try:
    from tools import ga_window as _ga_window
except ImportError:  # pragma: no cover - 以腳本形態執行時才會走到
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ga_window as _ga_window  # noqa: E402

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
EMIT_REAL_REQUIRED_FROM = _dt.datetime(2026, 5, 24, tzinfo=_dt.UTC)

# ── R76：兩個「時間」面的門檻。🔴 **值與 WHY 的唯一的家是 `tools/ga_window.py`**
# （R76 四方複審 SD-04：原本與 `drift_log_ga_check.py` 各存一份、逐字相同 112 行、零
# parity 鎖，實測單邊改一個常數兩支公然不一致而三支測試檔仍 108 passed rc=0）。
# 此處只做 re-export 讓既有消費者的匯入路徑不變。
STALENESS_MAX_DAYS = _ga_window.STALENESS_MAX_DAYS
WINDOW_SPAN_MAX_FACTOR = _ga_window.WINDOW_SPAN_MAX_FACTOR

# 🔴 `_parse_ts` 同樣改為共用（R76 複審 SD-04 的核心證據）：本檔原有的版本**不做 tz
# 正規化**，而 R76 新貼進來的 `_staleness_days`／`_window_calendar_span`（自 drift 複製）
# 消費的正是它 ⇒ 兩支「逐字相同」的 evaluate 餵同一筆 naive 時戳，drift 回 ready、
# 本檔 `TypeError: can't compare offset-naive and offset-aware datetimes`。
# 本檔的 `_compute_green_streak` 拿 `ts >= EMIT_REAL_REQUIRED_FROM`（aware）比較，
# 也是同一個地雷的第二個引信。共用版一律補 UTC。
_parse_ts = _ga_window.parse_ts


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
            return False, (
                "observability_emit_real missing (strict mode; "
                "ts >= EMIT_REAL_REQUIRED_FROM cutoff requires explicit field)"
            )
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


# 🔴 兩支同樣 re-export 自 `tools/ga_window.py`（R76 複審 SD-04），理由見 `_parse_ts` 上方。
_staleness_days = _ga_window.staleness_days
_window_calendar_span = _ga_window.window_calendar_span


def evaluate(
    records: list[dict[str, Any]],
    *,
    window: int,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """純函式判定；判準本體見 `tools/ga_window.evaluate`（兩支 checker 共用同一份）。

    本檔唯一不共用的是 `_compute_green_streak`——它帶 legacy／strict 的 ts cutoff，
    與 drift 的 `drift_log_table_exists` 判準是兩件不同的事，故以參數注入。
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
        description="SD_09 W5 雙條件可觀測性 GA 取證工具"
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
            f"(total {len(records)} records; {span}) → GA 取證通過"
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
