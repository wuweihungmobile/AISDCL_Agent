"""帳本主檔相對 git HEAD 是否有未 commit 修改的偵測（DEF-200-163）。

WHY：`current_round()`（`tools/check_defect_log_crossref.py`）現查帳本「發現情境」欄，
而自然工作順序「修 code → 跑閘門全綠 → 寫帳本 → commit」會在寫帳本這一步之後才把輪號
推到當前值——若收尾者在寫帳本後沒有**再跑一次**閘門就 commit，上一次的全綠結論其實是
對著修改前的帳本算的，可能已經過期（`current_round()` 本身、`orphan_backlog_problems()`、
`lagging_clock_notes()` 等吃它的判準皆受影響）。這是已知盲區，本模組的角色只是把它從
無聲變成有聲（advisory，不阻斷），不解決循環本身（那需要更大改動，非本輪範圍）。

刻意獨立成一支小檔：`tools/lib/defect_ledger_index.py` 與 `tools/lib/ledger_rotation.py`
兩份既有共用層都自陳「零 I/O、零全域狀態」，而本函式必須呼叫 `git status`（真 I/O）——
混進去會破壞那兩份模組自己宣告的不變式。
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def uncommitted_problems(ledger_path: Path, repo_root: Path) -> list[str]:
    """`ledger_path` 相對 `repo_root` 的 git HEAD 若有未 commit 修改（staged 或
    unstaged），回傳提醒訊息；問不出來（非 git repo／`git` 不可執行／逾時）一律回空
    清單——advisory 性質，問不出來不代表有問題。
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--", str(ledger_path)],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — advisory：git 不可用就不判，不是崩潰
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    return [f"{ledger_path.name} 相對 git HEAD 有未 commit 的修改（staged 或"
            " unstaged）——上一次跑本閘門的結論可能是對著修改前的帳本算的，"
            "`current_round()` 等判準吃的是磁碟現狀，建議在最後一次改帳本之後"
            "重跑本檢查（DEF-200-163）"]
