#!/usr/bin/env python3
"""PRD §11.1 零 token 遙測驗證（回溯法，驗收補件）：找一段「有人在量、卻沒人花 token」的區間。"""
# WHY 用回溯法、以及它證明什麼
# --------------------------------
# §11.1 的原方法是「純遙測模式連跑 6 小時、不派任何工」。要在真機重跑它得空出 6 小時；回溯法
# 改問：**歷史上有沒有一段 ≥6 小時**同時滿足
#   (1) 讀數列覆蓋整段區間（落款檔 `quota_burn.jsonl` 在區間內的讀數，連同兩端點，相鄰間隔
#       都 ≤ 上限）——量的人一直在量；🔴 判在**區間本身**，不是判某個更長的讀數連續區段：
#       後者在上限放大時會放行一段區間內**一列讀數都沒有**的時段（實測 12 小時上限曾如此）；
#   (2) 本機 `~/.claude/projects/` 底下**任何**逐字稿都沒有 assistant usage 記錄落在區間內
#       ——沒有任何本機工作；
#   (3) 區間內 `session`／`five_hour` 軸的 pct 單調不增——量的動作本身沒有把用量推高。
# 三項全真＝「量測不花 token」在該段歷史上沒有被反駁。它是**不被反駁**的證據，不是證明：
# 同帳號在別台機器或網頁端的用量會讓 (3) 紅，而 (3) 紅不蘊含本機量測花了 token。
#
# 🔴 誠實劃界（四條，讀輸出前先讀）：
#   · 逐字稿會被 Claude Code 依檔案最後修改時間清掉（本機實測約 30 天）。**涵蓋起點＝逐字稿
#     目錄內最舊存活檔的 mtime**（≈清理線）；早於它的區間 (2) 結構上驗不了（沒有記錄 ≠ 沒有
#     用量），一律不納入候選——量不到不得讀成量到零。刻意**不**取「最早一筆 usage」：長壽
#     session 的早期記錄會活過清理線，而同期其他 session 的記錄已被清掉（實測差 4 天）。
#   · 本檔 glob 用 `rglob`（含 `<sid>/subagents/` 底下的子代理逐字稿），比「`*/*.jsonl`」寬：
#     子代理的 usage 也是本機工作，漏掉它會讓 (2) 假綠。
#   · 落款檔的寫入端是 `--pace`（`quota_gate.record_burn`），不是哨兵巡邏本身；讀數列「連續」
#     因此取決於當時有沒有人／排程在查——找不到區間常是 (1)∧(2) 互斥（有人在量就有人在用），
#     不是機制壞了。
#   · assistant usage 不含 harness 合成的撞線記錄（`<synthetic>`，沒有花 token）。
#
# 用法
# ----
#     python tools/probe/zero_token_telemetry_window.py
#     python tools/probe/zero_token_telemetry_window.py --min-hours 6 --max-gap-minutes 120
#     python tools/probe/zero_token_telemetry_window.py --selftest      # 合成資料自證判準
from __future__ import annotations

import argparse
import bisect
import contextlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import platform_utils  # noqa: E402
import quota_gate  # noqa: E402
import quota_limits  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）


def burn_rows(path: Path) -> list[tuple[datetime, dict]]:
    """落款檔 ⇒ 時間序 `[(時刻, pct dict)]`；壞列略過。"""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        with contextlib.suppress(KeyError, TypeError, ValueError, AttributeError):
            row = json.loads(line)
            rows.append((datetime.fromisoformat(row["ts"]), dict(row["pct"])))
    return sorted(rows, key=lambda r: r[0])


def usage_times(projects: Path) -> tuple[list[datetime], datetime | None]:
    """`(assistant usage 時刻升冪, 涵蓋起點＝最舊存活檔的 mtime)`；先子字串預篩再 parse。"""
    stamps, oldest = [], None
    for path in projects.rglob("*.jsonl"):
        with contextlib.suppress(OSError):
            mtime = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            oldest = mtime if oldest is None else min(oldest, mtime)
        with contextlib.suppress(OSError), path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"usage"' not in line or '"assistant"' not in line:
                    continue
                with contextlib.suppress(ValueError, AttributeError, TypeError):
                    rec = json.loads(line)
                    msg = rec.get("message") or {}
                    if (rec.get("type") == "assistant" and isinstance(msg.get("usage"), dict)
                            and msg.get("model") != quota_limits.SYNTHETIC_MODEL):
                        stamps.append(datetime.fromisoformat(
                            str(rec["timestamp"]).replace("Z", "+00:00")))
    return sorted(stamps), oldest


def quiet_intervals(lo: datetime, hi: datetime, stamps: list[datetime]) -> list:
    """`[lo, hi]` 內沒有任何 usage 時刻的極大子區間 `[(起, 迄)]`（端點＝usage 時刻或 lo／hi）。"""
    inside = stamps[bisect.bisect_right(stamps, lo):bisect.bisect_left(stamps, hi)]
    edges = [lo, *inside, hi]
    return list(zip(edges, edges[1:]))


def covered(rows: list, lo: datetime, hi: datetime, max_gap: timedelta) -> tuple[bool, int, float]:
    """(1)：區間內讀數連同兩端點、相鄰間隔都 ≤ `max_gap`；回 `(判決, 讀數列數, 最大間隔分鐘)`。"""
    times = [ts for ts, _pct in rows if lo <= ts <= hi]
    points = [lo, *times, hi]
    worst = max((b - a for a, b in zip(points, points[1:])), default=timedelta(0))
    return bool(times) and worst <= max_gap, len(times), worst.total_seconds() / 60


def monotone_non_increasing(rows: list, lo: datetime, hi: datetime) -> bool:
    """(3)：區間內 `session`／`five_hour` 兩軸各自的 pct 單調不增。"""
    inside = [pct for ts, pct in rows if lo <= ts <= hi]
    for kind in sorted(quota_gate._FIVE_HOUR_KINDS):  # noqa: SLF001 — 同一份 5h 軸判準的 SSOT
        series = [p[kind] for p in inside if isinstance(p.get(kind), (int, float))]
        if any(b > a for a, b in zip(series, series[1:])):
            return False
    return True


def search(rows: list, stamps: list, cover, *, min_hours: float, max_gap_min: float) -> dict:
    """找最佳區間（最長且 (1)(2)(3) 全真）；找不到時回候選統計，讓「為什麼沒有」可稽核。

    候選＝兩筆 assistant usage 之間（或涵蓋起點／最後一列讀數之間）的**無 usage 極大區間**，
    長度 ≥ `min_hours`；(2) 因此對候選本身恆真，鑑別力落在「有沒有這樣的區間」與 (1)(3)。
    """
    need, gap = timedelta(hours=min_hours), timedelta(minutes=max_gap_min)
    stats = {"quiet": 0, "covered": 0, "best": None, "partial": None, "detail": []}
    if not rows or cover is None:
        return stats
    lo, hi = max(cover, rows[0][0]), rows[-1][0]  # 涵蓋起點之前 (2) 驗不了：不納入
    for a, b in quiet_intervals(lo, hi, stamps) if lo < hi else []:
        if b - a < need:
            continue
        stats["quiet"] += 1
        ok1, n, worst = covered(rows, a, b, gap)
        ok3 = monotone_non_increasing(rows, a, b)
        cand = {"start": a, "end": b, "hours": (b - a).total_seconds() / 3600, "readings": n,
                "worst_gap_min": worst, "covered": ok1, "monotone": ok3}
        stats["detail"].append(cand)
        if not ok1:
            continue
        stats["covered"] += 1
        key = "best" if ok3 else "partial"
        if stats[key] is None or cand["hours"] > stats[key]["hours"]:
            stats[key] = cand
    return stats


def iso(moment: datetime) -> str:
    return moment.astimezone().isoformat(timespec="seconds")


def report(stats: dict, n_rows: int, n_usage: int, cover, args) -> int:
    hours = f"{args.min_hours:g}"
    print(f"落款讀數列 {n_rows} 筆；assistant usage 記錄 {n_usage} 筆"
          f"（涵蓋起點＝最舊存活逐字稿的 mtime {iso(cover) if cover else '無'}）")
    print(f"條件：區間 ≥{hours} 小時；讀數（連同區間兩端）相鄰間隔 ≤{args.max_gap_minutes:g} 分")
    print(f"涵蓋期內「無 assistant usage」且 ≥{hours}h 的區間 {stats['quiet']} 段；其中讀數覆蓋 "
          f"(1) 成立的 {stats['covered']} 段")
    for c in sorted(stats["detail"], key=lambda c: -c["hours"])[:5]:
        print(f"  {iso(c['start'])} ～ {iso(c['end'])}（{c['hours']:.1f}h）：區間內讀數 "
              f"{c['readings']} 列、最大間隔 {c['worst_gap_min']:.0f} 分 ⇒ (1) "
              f"{'PASS' if c['covered'] else 'FAIL'}、(3) {'PASS' if c['monotone'] else 'FAIL'}")
    best = stats["best"]
    if best is None:
        if not stats["quiet"]:
            why = f"涵蓋期內沒有任何 ≥{hours}h 的無 assistant usage 區間（(2) 不成立）"
        elif not stats["covered"]:
            why = "有無 usage 的區間，但區間內沒有足夠的讀數列（(1) 不成立；沒人在量）"
        else:
            why = "有被讀數覆蓋的無 usage 區間，但 session／five_hour 軸 pct 曾上升（(3) 不成立）"
        print(f"找不到同時滿足 (1)(2)(3) 的區間：{why}")
        return 1
    print(f"最佳區間：{iso(best['start'])} ～ {iso(best['end'])}（{best['hours']:.1f} 小時、"
          f"區間內讀數 {best['readings']} 列、最大間隔 {best['worst_gap_min']:.0f} 分）")
    print("  (1) 讀數列覆蓋整段區間  PASS")
    print("  (2) 區間內無任何 assistant usage 記錄  PASS")
    print("  (3) session／five_hour 軸 pct 單調不增  PASS")
    return 0


def selftest() -> int:
    """合成資料自證三項判準各自有鑑別力（正控一組、三種反控各一組）。"""
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    flat = [(t0 + timedelta(minutes=30 * i), {"session": 40.0, "five_hour": 40.0})
            for i in range(30)]
    rising = [(ts, {"session": 40.0 + i, "five_hour": 40.0 + i}) for i, (ts, _p) in enumerate(flat)]
    early = t0 - timedelta(days=1)
    busy = [t0 + timedelta(hours=4), t0 + timedelta(hours=9)]
    cases = (
        ("正控：量得到、無 usage、單調 ⇒ 找得到", flat, [], early, True),
        ("反控(1)：讀數稀疏（間隔 >上限）⇒ 找不到", flat[::6], [], early, False),
        ("反控(1)：區間內一列讀數都沒有 ⇒ 找不到", flat[:1] + flat[-1:], [], early, False),
        ("反控(2)：區間內兩筆 usage 把它切成 <6h 的三段 ⇒ 找不到", flat, busy, early, False),
        ("反控(3)：pct 上升 ⇒ 不是最佳（(3) 假）", rising, [], early, False),
        ("反控(涵蓋)：涵蓋起點晚於區間 ⇒ 不納入", flat, [], t0 + timedelta(days=1), False),
    )
    failed = 0
    for title, rows, stamps, cover, want in cases:
        found = search(rows, stamps, cover, min_hours=6, max_gap_min=120)["best"] is not None
        failed += found != want
        print(f"{'PASS' if found == want else 'FAIL'} {title}（found={found}）")
    print(f"自證：{len(cases) - failed}/{len(cases)} 項符合預期")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--burn-ledger", type=Path, default=None,
                        help="落款檔（預設＝生產路徑 quota_burn.jsonl）")
    parser.add_argument("--projects-dir", type=Path, default=None,
                        help="逐字稿根（預設＝claude_home()/projects）")
    parser.add_argument("--min-hours", type=float, default=6.0, help="區間下限（小時）")
    parser.add_argument("--max-gap-minutes", type=float, default=120.0,
                        help="讀數『連續』的相鄰間隔上限（分鐘）")
    parser.add_argument("--selftest", action="store_true", help="合成資料自證判準")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.max_gap_minutes >= args.min_hours * 60:
        parser.error("--max-gap-minutes 必須小於 --min-hours×60（否則零讀數的區間也會被判覆蓋）")
    rows = burn_rows(args.burn_ledger or quota_gate.burn_ledger_path())
    stamps, cover = usage_times(args.projects_dir or platform_utils.claude_home() / "projects")
    stats = search(rows, stamps, cover, min_hours=args.min_hours, max_gap_min=args.max_gap_minutes)
    return report(stats, len(rows), len(stamps), cover, args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
