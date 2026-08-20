"""`run_root_unittests.py` 失敗明細的檔名（帶時間戳／HEAD 短碼）與輪替（DEF-200-162）。

WHY：失敗明細此前是固定檔名 `.last_failure.log`，每次執行覆寫，且被 `.gitignore` 排除
——下一次執行會把上一次的失敗證據抹掉，「兩次跑出同一組紅」這種取證動作結構上留不下
並排證物。修法＝檔名帶時間戳＋HEAD 短碼（同 SHA 同時刻不覆寫彼此），並只保留最近 N 份
避免無限增殖。獨立成模組的理由同 `worktree_paths.py`：`tools/run_root_unittests.py` 是
`SPECIAL_FILES` raw-line 零餘裕棘輪（見 `AutoClaude/tools/check_loc_budget.py`），新邏輯
須抽到別處才塞得進去。
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

#: 保留最近幾份失敗明細（形狀照 nightly log 14 天輪替，數字取較小值：失敗明細比 nightly
#: log 密集得多，N 太大會讓 `.claude/`／`tools/` 目錄被證據檔淹沒）。
KEEP_RECENT = 8


def failure_log_path(log_dir: Path, *, repo_root: Path | None = None,
                      when: float | None = None) -> Path:
    """算出這次失敗明細該落地的檔名（純函式，不碰磁碟）。"""
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(when))
    sha = _head_short_sha(repo_root) or "nogit"
    return log_dir / f".last_failure_{sha}_{ts}.log"


def _head_short_sha(repo_root: Path | None) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root or Path.cwd()), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — 診斷輔助不得因 git 不可用而崩潰
        return None
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def prune_old_failure_logs(log_dir: Path, keep: int = KEEP_RECENT) -> list[Path]:
    """只留最近 `keep` 份 `.last_failure_*.log`，回傳被刪的路徑（供測試驗證）。"""
    logs = sorted(log_dir.glob(".last_failure_*.log"), key=lambda p: p.stat().st_mtime)
    victims = logs[:-keep] if keep > 0 else logs
    removed: list[Path] = []
    for p in victims:
        try:
            p.unlink()
            removed.append(p)
        except OSError:
            pass
    return removed
