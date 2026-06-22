"""monorepo 根層守衛式 hook router（整合層，非任何凍結 v0.0X 本體）。

問題背景
--------
Claude Code 的 hooks 只從「啟動時的專案根 .claude/settings.json（+ user/local/
enterprise）」載入，**不會遞迴子目錄**（官方：There is no recursive subdirectory
discovery of hook files）。因此從 monorepo 根啟動 session 時，
`AISDLC_SDD/AISDLC_SDD_v0.0X/.claude/settings.json` 內的 SDD 治理 hooks 全部靜默失效
（SessionStart 注入 FSM 狀態/規則、PreToolUse/PostToolUse 走 context_ledger）。

本 router 在根 .claude/settings.json 被 wire 為唯一進入點，以環境變數
`SDD_ACTIVE_VERSION` 為守衛，把控制權轉交「正確版本目錄下的實體 hook 檔」。
各實體 hook 以 `Path(__file__).resolve().parents[2]` 自我定位，故 router 只需用
正確路徑啟動之，版本路由即自動成立——不需傳 cwd、不改任何凍結版檔。

守衛語意
--------
- `SDD_ACTIVE_VERSION` 未設 → no-op（純 AutoClaude session 零污染）：
  PreToolUse/PostToolUse 完全靜默放行；SessionStart 印一行 dormant 提示
  （fail-loud，可用 `SDD_ROUTER_QUIET=1` 全靜音）。
- `SDD_ACTIVE_VERSION` 已設（如 `0.18` 或 `v0.18`）→ exec 該版實體 hook，
  原樣轉發 stdin / stdout / stderr / exit code。
- 版本目錄不存在 → 不讓 CC 崩潰：印 WARN（additionalContext）後 exit 0。

此檔屬整合層，刪除根 .claude/settings.json 即完全回退，不觸及任何凍結版本體
（合 Copy-on-Evolve）；屬「新增載入橋接讓 hooks 重新生效」而非停用 hooks
（合 Rule 9 絕對禁令 #2 之精神並補強之）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Windows zh-TW 主控台/pipe 預設 cp950：router 自身以 sys.stdout 寫中文（_emit 的休眠/
# WARN 訊息、轉發 child 輸出）時會被 cp950 編碼，CC 端以 UTF-8 讀回 → 亂碼（DEF-43-001
# 之 b：連 no-op 休眠訊息都亂碼）。對齊 sibling 腳本（sync_exposed_skills.py /
# framework_status_snapshot.py）強制自身串流為 UTF-8，確保整條鏈端到端 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# router 位於 <repo_root>/.claude/hooks/sdd_hook_router.py → parents[2] == repo_root。
# 優先採 CC 注入的 CLAUDE_PROJECT_DIR（最可靠），否則回退 __file__ 自我定位。
_ENV_ROOT = os.environ.get("CLAUDE_PROJECT_DIR")
REPO_ROOT = Path(_ENV_ROOT).resolve() if _ENV_ROOT else Path(__file__).resolve().parents[2]

# router hook 短名 → (實體 hook 檔名, Claude Code hookEventName)
_HOOK_MAP = {
    "session_start": ("session_start.py", "SessionStart"),
    "context_ledger_pre": ("context_ledger_pre.py", "PreToolUse"),
    "context_ledger_post": ("context_ledger_post.py", "PostToolUse"),
}


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def _noop(event_name: str) -> int:
    """守衛未啟用時的 no-op：放行、不改任何決策。"""
    if event_name == "SessionStart" and os.environ.get("SDD_ROUTER_QUIET") != "1":
        _emit({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    "[SDD-ROUTER] SDD 治理 hooks 休眠中（SDD_ACTIVE_VERSION 未設）。"
                    "若本 session 要對框架做 B 軌 dogfooding，請先設定 "
                    "SDD_ACTIVE_VERSION（例：0.18）以啟用 FSM/context-ledger 守門；"
                    "純 AutoClaude 工作可忽略此訊息（設 SDD_ROUTER_QUIET=1 可全靜音）。"
                ),
            }
        })
    else:
        # PreToolUse/PostToolUse：每次工具呼叫都觸發 → 必須完全靜默放行。
        _emit({"hookSpecificOutput": {"hookEventName": event_name}})
    return 0


def _warn(event_name: str, msg: str) -> int:
    """以 additionalContext 發警告但不阻擋（永不讓 CC 崩潰）。"""
    _emit({"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": msg}})
    return 0


def _normalize_version(raw: str) -> str:
    v = raw.strip()
    if v[:1] in ("v", "V"):
        v = v[1:]
    return v


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in _HOOK_MAP:
        # 設定錯誤：未知 hook 名。靜默放行（無法得知 event name 時印通用占位）。
        _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse"}})
        return 0
    script_name, event_name = _HOOK_MAP[argv[1]]

    raw_ver = os.environ.get("SDD_ACTIVE_VERSION", "")
    if not raw_ver.strip():
        return _noop(event_name)

    version = _normalize_version(raw_ver)
    target = REPO_ROOT / "AISDLC_SDD" / f"AISDLC_SDD_v{version}" / ".claude" / "hooks" / script_name
    if not target.is_file():
        return _warn(
            event_name,
            f"[SDD-ROUTER][WARN] SDD_ACTIVE_VERSION={raw_ver!r} 指向的 hook 不存在："
            f"{target}。請確認版本號（例：0.18）。本次放行、未套用 SDD 守門。",
        )

    # 轉交實體 hook：原樣轉發 stdin → child，child 的 stdout/stderr/exit code 原樣回傳。
    stdin_data = "" if sys.stdin.isatty() else sys.stdin.read()
    # Windows zh-TW 預設主控台/pipe 編碼為 cp950：SDD 實體 hook 未 reconfigure stdout 時
    # 會以 cp950 印中文，而本 router 以 encoding="utf-8" 解 child 輸出 → reader thread
    # 拋 UnicodeDecodeError(0xb7) 崩潰，方案 C 在 Windows 上整個失效（DEF-43-001）。
    # 修法：①強制 child 以 UTF-8 輸出（PYTHONUTF8/PYTHONIOENCODING），與本端解碼對齊；
    # ②errors="replace" 作後盾，即使 child 仍吐非 UTF-8 也絕不崩潰（守 router「永不讓 CC 崩潰」）。
    child_env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run(
            [sys.executable, str(target)],
            input=stdin_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            cwd=str(REPO_ROOT),
        )
    except Exception as exc:  # noqa: BLE001 — 永不讓 CC 崩潰
        return _warn(event_name, f"[SDD-ROUTER][WARN] 轉交 {script_name} 失敗：{exc!r}。本次放行。")

    if proc.stdout:
        sys.stdout.write(proc.stdout)
        sys.stdout.flush()
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
