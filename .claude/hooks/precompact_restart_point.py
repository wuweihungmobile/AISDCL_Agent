#!/usr/bin/env python3
"""PreCompact：壓縮前先把「可重啟點任務書」落磁碟（PRD §4.3；R213 掌舵者核准）。  round-label-ok

為何需要：autocompact 會把對話前段摘要掉；「已驗證什麼／還沒做什麼／下一步指令」若只住在
對話裡，壓縮後只剩摘要的轉述（根 CLAUDE.md〈可重啟點四條件〉第 2 條要求任務書落磁碟）。
本 hook 在壓縮發生**之前**呼叫 planner 寫任務書骨架（零 token：只讀逐字稿），並在持久痕跡
目錄落一行壓縮事件（同 session 的壓縮次數與間隔可事後稽核＝PRD §4.3 最小間隔的觀測面）。

契約：
  · 恆 exit 0（PreCompact 不阻止壓縮；fail-open 是 P0——hook 失效的外觀不得像「壓縮壞了」）。
  · 同 session 距上次壓縮事件 < COMPACT_MIN_INTERVAL_SECONDS（出廠 600）時仍寫任務書，只在
    stderr 出聲「壓縮過密」並在事件列標 too_soon——這是觀測，不是阻斷。
  · 逃生口 AUTOSDD_PRECOMPACT_OFF=1（刻意不與其他守衛共用：關哪一支就只關哪一支）。
  · payload 讀取唯一家＝tools/lib/platform_utils.read_hook_payload()；子行程 argv[0] 一律
    sys.executable（零 console 視窗判準）。
回歸鎖：tools/tests/test_check_hooks_liveness.py::TestPreCompactRestartPointHook。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
sys.path.insert(0, str(_ROOT / "tools" / "lib"))
try:
    import endurance_env  # noqa: E402
    import platform_utils  # noqa: E402
except Exception as _exc:  # noqa: BLE001 — 載不到 tools/lib＝放行（恆 exit 0 是檔頭契約）
    print(f"[precompact] 放行：tools/lib 載入失敗（{type(_exc).__name__}: {_exc}）",
          file=sys.stderr)
    sys.exit(0)

OFF_ENV = "AUTOSDD_PRECOMPACT_OFF"
COMPACT_MIN_INTERVAL_SECONDS = 600
EVENTS_NAME = "autosdd_compact_events.jsonl"
PLANNER = _ROOT / "tools" / "session_resume_planner.py"
PLANNER_TIMEOUT_SECONDS = 20


def events_path() -> Path:
    return endurance_env.trace_dir() / EVENTS_NAME


def last_event_epoch(path: Path, session_id: str) -> float | None:
    """同 session 最近一筆壓縮事件的 epoch；沒有＝None。讀壞一行就跳過那一行。"""
    if not path.is_file():
        return None
    latest: float | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("session_id") == session_id:
            try:
                latest = float(row.get("at_epoch"))
            except (TypeError, ValueError):
                continue
    return latest


def plan_out_path(session_id: str, now_epoch: float) -> Path:
    """每次壓縮各寫一支 hook 專屬檔（SD-01）：planner 預設路會整檔重寫 per-session 任務書，
    而 94% 簡報叫模型去填那份骨架的 TODO——同一個檔被壓縮前重寫＝填好的內容被空骨架蓋掉
    （08-17 00:42 同型事故）。獨立檔名＝不碰模型正在填的那一份。"""
    stamp = (datetime.fromtimestamp(now_epoch, UTC).strftime("%Y%m%dT%H%M%S")
             + f"{int(now_epoch * 1000) % 1000:03d}Z")  # 毫秒：同秒兩次壓縮不互蓋
    return endurance_env.plan_dir() / f"autosdd_precompact_{session_id}_{stamp}.md"


def write_plan(transcript: str, out: Path) -> tuple[int, str]:
    """跑 planner 寫任務書骨架到 `out`（不走預設 per-session 檔）；回 (rc, 最後一行)。"""
    if not PLANNER.is_file():
        return 127, f"planner missing: {PLANNER}"
    argv = [sys.executable, str(PLANNER), "--transcript", transcript, "--out", str(out)]
    try:
        proc = subprocess.run(
            argv, capture_output=True, encoding="utf-8", errors="replace",
            timeout=PLANNER_TIMEOUT_SECONDS, cwd=str(_ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return 124, "planner timeout"
    tail = (proc.stdout.strip().splitlines() or proc.stderr.strip().splitlines() or [""])[-1]
    return proc.returncode, tail


def main() -> int:
    try:
        if os.environ.get(OFF_ENV):
            return 0
        payload = platform_utils.read_hook_payload()
        session_id = str(payload.get("session_id") or "").strip()
        transcript = str(payload.get("transcript_path") or "").strip()
        trigger = str(payload.get("trigger") or "")
        if not session_id or not transcript:
            return 0  # payload 退化＝放行（fail-open）
        now_epoch = time.time()
        prev = last_event_epoch(events_path(), session_id)
        since = None if prev is None else max(0.0, now_epoch - prev)
        too_soon = since is not None and since < COMPACT_MIN_INTERVAL_SECONDS
        out = plan_out_path(session_id, now_epoch)
        rc, tail = (write_plan(transcript, out) if Path(transcript).is_file()
                    else (2, "transcript missing"))
        row = {
            "schema": "autosdd.compact_event/1", "session_id": session_id, "trigger": trigger,
            "at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
            "at_epoch": round(now_epoch, 3), "since_last_seconds": since, "too_soon": too_soon,
            "plan_rc": rc, "plan_note": tail[:200], "plan_path": str(out),
        }
        path = events_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")
        if too_soon:
            print(f"[precompact] 壓縮過密：距上次 {since:.0f}s < {COMPACT_MIN_INTERVAL_SECONDS}s"
                  f"（session {session_id[:8]}；只出聲不阻止）", file=sys.stderr)
        if rc != 0:
            print(f"[precompact] 任務書骨架未寫成（rc={rc}：{tail[:120]}）；壓縮照常",
                  file=sys.stderr)
        return 0
    except Exception as exc:  # noqa: BLE001 — fail-open 是 P0，見檔頭契約
        print(f"[precompact] 例外放行：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
