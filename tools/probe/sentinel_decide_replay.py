#!/usr/bin/env python3
"""零 token 重放：同一份逐字稿＋halt 標記，在「舊判準」與「新判準」下，哨兵 `sentinel_decide`
各判什麼（DEF-200-560／562／564）。對來源檔只讀、不 spawn；`--now` 的「截到當時」複本寫在
系統暫存、結束即刪。"""
# 用法
# ----
#     python tools/probe/sentinel_decide_replay.py --sid <sid> [--now <ISO 8601，預設現在>]
#
# 設計全文＝ADR-XPLAT-004 §2.10（對話記錄判準）與 §2.11（雙駕駛）。誠實劃界（印出的每個數字
# 都是量測值，不是常數）：
#   · 「舊判準」＝改前的世界：idle 取檔案 mtime **現值**（歷史 mtime 不可重建，`--now` 早於檔案
#     最後寫入時舊 idle 為負）；未處理撞線事件在「丟掉 harness 續接記錄」的複本上算（改前的
#     `recovered_at` 只看成功回應，與「那些記錄不存在」等價）。
#   · 新判準的逐字稿視圖**截到 `--now` 為止**（as-of）：事故逐字稿在 `--now` 之後還有幾小時的
#     記錄，不截就看不到當時「續接記錄已寫、首則回應未落」的那一刻。
#   · 「D3 單獨」＝把事件還原成舊判準的事件、只靠「另一駕駛」閘（`live_driver`）——證明雙保險
#     各自都擋得住。
#   · 不重建 `superseded_by`（同專案他 session 在 `--now` 當時的活動不可重建），兩邊一律不帶；
#     寫於 `--now` 之後的 halt 標記視同當時不存在。
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_limits as limits  # noqa: E402
import transcript_activity as activity  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
import session_resume_planner as planner  # noqa: E402


def _stamp(epoch: float | None, now: datetime) -> str:
    return "（無）" if epoch is None else datetime.fromtimestamp(epoch, now.tzinfo).isoformat()


def _j(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str) if value else "（無）"


def _halt_marker(sid: str, now: datetime) -> dict | None:
    """唯讀取 halt 標記；寫於 `--now` 之後（as-of 當時還不存在）一律當沒有，免得重放被現值汙染。"""
    try:
        marker = json.loads(planner._halt_marker_probe_path(sid).read_text(encoding="utf-8"))
        return None if datetime.fromisoformat(str(marker["at"])) > now else marker
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _say(label: str, decision: dict) -> None:
    print(f"{label} ⇒ {decision['action']}：{decision['reason']}")


def _asof(paths: list[Path], dest: Path, now: datetime, *, drop_resume: bool) -> Path:
    """`paths`（主檔在最前）逐行截到 `now` 為止，寫成 `dest` 下的暫存複本；回主檔複本。
    `drop_resume`＝另丟 harness 續接記錄（重現改前看到的世界）。subagent 檔沿用相對位置。"""
    main, cut = paths[0], now.timestamp()
    for src in paths:
        rel = (Path(main.name) if src == main
               else Path(main.stem) / src.relative_to(main.with_suffix("")))
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        with src.open(encoding="utf-8", errors="replace") as fin, (dest / rel).open(
                "w", encoding="utf-8", newline="\n") as fout:
            for line in fin:
                try:
                    rec = json.loads(line) if '"timestamp"' in line else None
                except ValueError:
                    rec = None
                if isinstance(rec, dict) and (
                        (activity._epoch(rec.get("timestamp")) or 0.0) > cut
                        or (drop_resume and limits.is_resume_record(rec))):
                    continue
                fout.write(line.rstrip("\n") + "\n")
    return dest / main.name


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="哨兵判定重放（舊判準 vs 新判準；as-of --now）")
    parser.add_argument("--sid", required=True, help="要重放的 session id")
    parser.add_argument("--now", help="重放時刻（ISO 8601，缺時區＝本機時區；預設現在）")
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    now = now.astimezone() if now.tzinfo is None else now
    source = planner.resolve_transcript(args.sid)
    if source is None:
        print(f"❌ 找不到 session {args.sid} 的逐字稿（resolve_transcript 回 None）",
              file=sys.stderr)
        return 2
    paths = limits.session_transcripts(source)
    mtime, marker = limits.newest_activity_at(paths), _halt_marker(args.sid, now)
    idle_old = now.timestamp() - mtime
    with tempfile.TemporaryDirectory(prefix="decide_replay_") as tmp:
        view = _asof(paths, Path(tmp) / "asof", now, drop_resume=False)
        legacy = _asof(paths, Path(tmp) / "legacy", now, drop_resume=True)
        newest = activity.newest_conversation_at(limits.session_transcripts(view))
        idle_new, grace = activity.conversation_view(view, now)
        old, new = limits.unhandled_limit_event(legacy), limits.unhandled_limit_event(view)
        driver_new = activity.live_driver(view, now, new) if new else None
        driver_old = activity.live_driver(view, now, old) if old else None
        print(f"sid={args.sid}  now={now.isoformat()}")
        print(f"逐字稿={source}（掃描 {len(paths)} 支；新判準視圖截到 now）")
        print(f"mtime 最新（檔案現值）={_stamp(mtime, now)}；"
              f"對話最新（as-of now）={_stamp(newest, now)}")
        print(f"idle：舊判準（mtime）={idle_old:.0f}s；新判準（對話）="
              f"{'None' if idle_new is None else f'{idle_new:.0f}s'}")
        print(f"halt 標記={_j(marker)}")
        print(f"未處理撞線事件：舊判準（不認續接記錄）={(old or {}).get('timestamp', '（無）')}；"
              f"新判準={(new or {}).get('timestamp', '（無）')}")
        print(f"另一駕駛 live_driver：以新判準事件為界={_j(driver_new)}；"
              f"以舊判準事件為界={_j(driver_old)}")
        print(f"寬限訊號={_j(activity.usage_limit_signals(view))}")
        print(f"未處理寬限提示={_j(grace)}")
        _say("舊判準 sentinel_decide",
             planner.sentinel_decide(old, "", idle_old, now, halt=marker))
        _say("新判準 sentinel_decide", planner.sentinel_decide(
            new, "", idle_new, now, halt=marker, grace=grace, driver=driver_new))
        _say("D3 單獨（事件還原成舊判準的、只靠另一駕駛閘）", planner.sentinel_decide(
            old, "", idle_new, now, halt=marker, grace=grace, driver=driver_old))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
