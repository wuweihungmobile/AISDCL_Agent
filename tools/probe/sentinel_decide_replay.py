#!/usr/bin/env python3
"""零 token 重放：同一份逐字稿＋halt 標記，在「舊判準（檔案 mtime）」與「新判準（對話記錄）」
下，哨兵 `sentinel_decide` 各判什麼（DEF-200-560／562）。只讀、不寫、不 spawn。"""
# 用法
# ----
#     python tools/probe/sentinel_decide_replay.py --sid <sid> [--now <ISO 8601，預設現在>]
#
# 設計全文＝ADR-XPLAT-004 §2.10。誠實劃界（本檔印出的每個數字都是量測值，不是常數）：
#   · 「舊判準」＝改前 `_sentinel_tick` 的算式 `now - mtime`，mtime 取**檔案現值**。歷史上每個
#     時刻的 mtime 不可重建，所以 `--now` 早於檔案最後寫入時舊判準的 idle 為負（＝「剛剛才更新
#     過」），判決仍是 patrol——與事故當晚 16 次巡邏同向，但數字不是當時的數字。
#   · 不重建 `superseded_by`（同專案他 session 在 `--now` 當時的活動不可重建），兩邊一律不帶。
#   · halt 標記走 planner 的唯讀路徑函式（不 `mkdir` 痕跡目錄），讀不到就當沒有。
from __future__ import annotations

import argparse
import json
import sys
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


def _halt_marker(sid: str) -> dict | None:
    try:
        return json.loads(planner._halt_marker_probe_path(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _say(label: str, decision: dict) -> None:
    print(f"{label} ⇒ {decision['action']}：{decision['reason']}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="哨兵判定重放（舊 mtime 判準 vs 新對話判準）")
    parser.add_argument("--sid", required=True, help="要重放的 session id")
    parser.add_argument("--now", help="重放時刻（ISO 8601，缺時區＝本機時區；預設現在）")
    args = parser.parse_args(argv)
    now = datetime.fromisoformat(args.now) if args.now else datetime.now()
    now = now.astimezone() if now.tzinfo is None else now
    transcript = planner.resolve_transcript(args.sid)
    if transcript is None:
        print(f"❌ 找不到 session {args.sid} 的逐字稿（resolve_transcript 回 None）",
              file=sys.stderr)
        return 2
    paths = limits.session_transcripts(transcript)
    mtime, conversation = limits.newest_activity_at(paths), activity.newest_conversation_at(paths)
    idle_old = now.timestamp() - mtime
    idle_new, grace = activity.conversation_view(transcript, now)
    marker, event = _halt_marker(args.sid), limits.unhandled_limit_event(transcript)
    print(f"sid={args.sid}  now={now.isoformat()}\n逐字稿={transcript}（掃描 {len(paths)} 支）")
    print(f"mtime 最新（檔案現值）={_stamp(mtime, now)}；對話最新={_stamp(conversation, now)}")
    print(f"idle：舊判準（mtime）={idle_old:.0f}s；新判準（對話）="
          f"{'None' if idle_new is None else f'{idle_new:.0f}s'}")
    print(f"halt 標記={json.dumps(marker, ensure_ascii=False) if marker else '（無）'}")
    print(f"未處理撞線事件={event['timestamp'] if event else '（無）'}")
    print(f"寬限訊號={json.dumps(activity.usage_limit_signals(transcript), ensure_ascii=False)}")
    print("未處理寬限提示="
          f"{json.dumps(grace, ensure_ascii=False, default=str) if grace else '（無）'}")
    _say("舊判準 sentinel_decide", planner.sentinel_decide(event, "", idle_old, now, halt=marker))
    _say("新判準 sentinel_decide", planner.sentinel_decide(
        event, "", idle_new, now, halt=marker, grace=grace))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
