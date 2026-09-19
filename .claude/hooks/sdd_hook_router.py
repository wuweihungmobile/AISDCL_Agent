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

⚠️ **已知限制（S10，worktree × 非 LATEST 版）**：本 router 只負責路由 `.claude/hooks/`
（SessionStart / PreToolUse / PostToolUse）。若在 `SDD_ACTIVE_VERSION` 指向非 LATEST 的
凍結版本（如 `0.18`）下，於 **linked git worktree** 內另外執行該版
`tools/install_hooks/install_post_commit.{sh,ps1}`，該腳本在 v0.01～v0.29 仍是舊寫法
`REPO_ROOT="$(git rev-parse --show-toplevel)"` + `"$REPO_ROOT/.git/hooks/post-commit"`
（worktree 下 `<worktree>/.git` 是純文字檔而非目錄，寫入會失敗）——只有 LATEST（目前
v0.30）已修復為 `--git-common-dir` 寫法並有回歸鎖
（`tools/fsm_runtime/tests/test_install_post_commit_worktree.py`）。此為已知且刻意
不回填的歷史快照限制（Copy-on-Evolve：舊版目錄視為凍結時間點，不逐版位元對位打補丁），
非本 router 的職責範圍。若需在 worktree 內對非 LATEST 版本安裝 PostCommit advisory
hook，請改在**主 checkout**（非 worktree）執行，或直接使用 LATEST 版的等效腳本。

此檔屬整合層，刪除根 .claude/settings.json 即完全回退，不觸及任何凍結版本體
（合 Copy-on-Evolve）；屬「新增載入橋接讓 hooks 重新生效」而非停用 hooks
（合 Rule 9 絕對禁令 #2 之精神並補強之）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows zh-TW 主控台/pipe 預設 cp950：router 自身以 sys.stdout 寫中文（_emit 的休眠/
# WARN 訊息、轉發 child 輸出）時會被 cp950 編碼，CC 端以 UTF-8 讀回 → 亂碼（DEF-43-001
# 之 b：連 no-op 休眠訊息都亂碼）。對齊 sibling 腳本（sync_exposed_skills.py /
# framework_status_snapshot.py）強制自身串流為 UTF-8，確保整條鏈端到端 UTF-8。
# stdin 亦須納入：CC 送入的 UTF-8 JSON payload 含中文時，cp950 解碼會使
# sys.stdin.read() 拋 UnicodeDecodeError → router 崩潰、SDD 守門 fail-open。
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        pass  # 非 TextIOWrapper（如測試替身）或串流已關閉 → 維持原樣，不讓 router 崩潰

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

# DEF-43-005：對 child 實體 hook 設「略小於外層 settings.json timeout」的硬上限。
# 外層 settings.json 對 router 設 SessionStart=30s、Pre/Post=10s；那是 CC 對「router」
# 的逾時，不是 router 對「child」的逾時。若實體 hook 卡住（如 session_start 注入 FSM
# 時讀大量 R-*.yaml），CC 砍 router 時 child subprocess 可能變孤兒。改由 router 自己
# 先 timeout 並讓 subprocess.run 回收 child（其 docstring：逾時會 kill 並 wait child），
# 留約 5s/2s 餘裕讓 router 在被外層砍掉前印出 fail-safe 放行 JSON。
_CHILD_TIMEOUT = {"SessionStart": 25.0, "PreToolUse": 8.0, "PostToolUse": 8.0}


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


def _disk_latest_version() -> str | None:
    """掃 ``<root>/AISDLC_SDD/`` 取磁碟最高版（(major,minor) 數值，對齊 sort -V）。

    DEF-43-003 後同步支援 v1.x。永不拋例外（fail-safe，回 None 即略過漂移告警）。
    """
    import re as _re

    base = REPO_ROOT / "AISDLC_SDD"
    pat = _re.compile(r"AISDLC_SDD_v(\d+)\.(\d+)$")
    best: tuple[int, int] | None = None
    best_name: str | None = None
    try:
        for child in base.iterdir():
            m = pat.match(child.name)
            if m and child.is_dir():
                key = (int(m.group(1)), int(m.group(2)))
                if best is None or key > best:
                    best, best_name = key, f"{m.group(1)}.{m.group(2)}"
    except Exception:  # noqa: BLE001 — fail-safe：漂移告警僅為 advisory，絕不影響路由
        return None
    return best_name


def _target_writes_legacy_token_budget_critical(version: str) -> bool:
    """R158 P4（主控裁決 D3(b) 舊語意偵測）：純字面比對目標版 `context_ledger_pre.py` round-label-ok
    原始碼，不 import 該模組——router 受零相依契約約束，且該檔屬於另一個 SDD 版本，
    import 會連帶拉進其全部相依（PyYAML 等，router 本身 stdlib-only）。v0.23~v0.29 的
    `context_ledger_pre.py` 仍會寫專案級 `TOKEN_BUDGET_CRITICAL: cumulative=` 字面
    （v0.30 起改寫 session 級 deny，不再含此字面；CrossPlatform R158 FACTS F2 已 grep round-label-ok
    驗證）。讀檔失敗（檔案不存在／權限問題）一律回 False——advisory 只是提示，寧可漏報
    也不能讓這個判斷本身弄崩 router（fail-safe）。
    """
    hook_path = (
        REPO_ROOT / "AISDLC_SDD" / f"AISDLC_SDD_v{version}" / ".claude" / "hooks"
        / "context_ledger_pre.py"
    )
    try:
        text = hook_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "TOKEN_BUDGET_CRITICAL: cumulative=" in text


def _drift_advisory_text(active: str) -> str | None:
    """DEF-43-004（R158 P4 擴充）：漂移 advisory 的純文字組裝，**不做任何 I/O**。 round-label-ok

    無漂移（磁碟掃不到版本目錄，或與 active 相同）回 None。刻意拆成純函式：呼叫端
    （`main()` 的 SessionStart 分支）要等 child 執行完、看得到其 stdout 之後，才能決定
    這段文字該併進 child 的 `hookSpecificOutput.additionalContext`（優先，stdout on
    exit 0 才進得了模型 context）還是退回 stderr（原 DEF-43-004 行為，見
    `_merge_advisory_into_stdout`）。
    """
    latest = _disk_latest_version()
    if latest is None or latest == active:
        return None
    text = (
        f"[SDD-ROUTER][advisory] SDD_ACTIVE_VERSION=v{active} 非磁碟最高版 v{latest}。"
        f"若非刻意指定凍結版做 B 軌 dogfooding，請確認是否應改用 LATEST(v{latest})。"
    )
    if _target_writes_legacy_token_budget_critical(active):
        text += (
            f" 此版 hook（context_ledger_pre.py）仍寫專案級 TOKEN_BUDGET_CRITICAL，"
            f"新視窗可能一開場就被擋；請改設 SDD_ACTIVE_VERSION={latest}（LATEST）。"
        )
    return text


def _merge_advisory_into_stdout(stdout_text: str, advisory: str) -> tuple[str, bool]:
    """R158 P4：把 advisory 併進 child 的 `hookSpecificOutput.additionalContext`。 round-label-ok

    只在 child stdout 是合法 JSON 物件、`hookSpecificOutput` 是 dict、且其
    `additionalContext` 已經是字串時才合併，回傳 `(合併後字串, True)`；任何一步不符
    （非 JSON／非 dict／缺鍵／型別不對）一律 `(原樣 stdout_text, False)`——呼叫端據此
    退回 stderr，行為與本函式新增前的 DEF-43-004 逐字相同（見 A1 路徑 6：stderr on
    exit 0 可能從未被模型看到，是本輪要修的能見度缺口，但不能因為修不到就吞掉訊息）。
    """
    try:
        data = json.loads(stdout_text)
    except (json.JSONDecodeError, TypeError):
        return stdout_text, False
    if not isinstance(data, dict):
        return stdout_text, False
    hook_out = data.get("hookSpecificOutput")
    if not isinstance(hook_out, dict):
        return stdout_text, False
    existing_ctx = hook_out.get("additionalContext")
    if not isinstance(existing_ctx, str):
        return stdout_text, False
    hook_out["additionalContext"] = existing_ctx + "\n\n" + advisory
    return json.dumps(data, ensure_ascii=False), True


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
    # DEF-CLDREV-028（SA 鏡 F-01，P2 路徑注入→RCE）：`SDD_ACTIVE_VERSION` 原樣插值進
    # 路徑，`_normalize_version` 僅 strip + 去前導 v，**不擋 `../`／絕對路徑／路徑分隔符**。
    # 親驗：`SDD_ACTIVE_VERSION="0.19/../../../../Windows"` → resolve 成
    # `D:\Windows\.claude\hooks\session_start.py`，逃逸 AISLDC_SDD 樹；唯一閘門 is_file()
    # 通過後即 subprocess.run([python, target]) → 凡能控此 env 並於任意可達處植入
    # `<dir>/.claude/hooks/<script>` 者即達任意碼執行。縱深兩道修復：
    #   ① 語法白名單——版本須完整匹配 `\d+\.\d+`（對齊 _disk_latest_version 的
    #      AISLDC_SDD_v(\d+)\.(\d+) pattern），不符即放行不路由（`../`/分隔符天然被擋）。
    #   ② 邊界斷言——即使白名單未來被放寬，仍斷言 resolved target 落在 AISLDC_SDD 樹內。
    if not re.fullmatch(r"\d+\.\d+", version):
        return _warn(
            event_name,
            f"[SDD-ROUTER][WARN] SDD_ACTIVE_VERSION={raw_ver!r} 格式非法（須形如 0.19）。"
            f"本次放行、未套用 SDD 守門。",
        )
    target = REPO_ROOT / "AISDLC_SDD" / f"AISDLC_SDD_v{version}" / ".claude" / "hooks" / script_name
    sdd_base = (REPO_ROOT / "AISDLC_SDD").resolve()
    try:
        in_tree = target.resolve().is_relative_to(sdd_base)
    except (OSError, ValueError):  # noqa: BLE001 — fail-safe：解析異常即拒路由、放行
        in_tree = False
    if not in_tree:
        return _warn(
            event_name,
            f"[SDD-ROUTER][WARN] SDD_ACTIVE_VERSION={raw_ver!r} 解析逃逸 AISLDC_SDD 樹"
            f"（{target}）。本次放行、未套用 SDD 守門。",
        )
    if not target.is_file():
        return _warn(
            event_name,
            f"[SDD-ROUTER][WARN] SDD_ACTIVE_VERSION={raw_ver!r} 指向的 hook 不存在："
            f"{target}。請確認版本號（例：0.18）。本次放行、未套用 SDD 守門。",
        )

    # DEF-43-004（R158 P4 擴充）：僅 SessionStart 算一次 LATEST 漂移 advisory 文字。 round-label-ok
    # 先只算字串、不做 I/O——要等 child 執行完才知道能不能併進其 stdout JSON（見下方轉發段）；
    # 若 child 逾時／噴例外，仍在對應 except 分支寫 stderr，保留「advisory 一定會被印在
    # 某處」的原有保證。
    advisory_text = _drift_advisory_text(version) if event_name == "SessionStart" else None

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
            timeout=_CHILD_TIMEOUT.get(event_name, 8.0),  # DEF-43-005：child 硬上限，逾時 kill+放行
            # 🔴 R80：本 router 由 Claude Code 起，那個父行程**沒有 console**，而 child 是
            # console 子系統的 python.exe ⇒ 不帶這個旗標時每一次 SDD hook 轉交都會替使用者
            # 開一個視窗。旗標語意與實測表見 `.claude/hooks/context_budget_guard.py` 的
            # `NO_WINDOW`；此處**刻意內聯**而不 import 那支——本檔同受零相依契約（hook 由
            # `runpy.run_path` 起，`.claude/hooks/` 不在 `sys.path` 上）。內聯的是一個 stdlib
            # 常數名、不是判準；「hook 不得彈視窗」這條判準的唯一家是
            # `tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest`，它掃本目錄
            # 每一個 spawn 站點，所以漏掉任何一站都會紅，不靠人記得。
            # POSIX 上 `getattr` 取 0 ＝不加旗標（鐵律三）。
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        # R158 P4：child 沒能跑完，advisory 併不進任何 JSON——退回 stderr。 round-label-ok
        if advisory_text is not None:
            sys.stderr.write(advisory_text + "\n")
            sys.stderr.flush()
        # 實體 hook 卡住：subprocess.run 已 kill 並 wait child（不留孤兒），router 放行不擋。
        return _warn(
            event_name,
            f"[SDD-ROUTER][WARN] {script_name} 逾 {_CHILD_TIMEOUT.get(event_name, 8.0)}s 未回應，"
            f"已中止 child 並本次放行（未套用 SDD 守門）。",
        )
    except Exception as exc:  # noqa: BLE001 — 永不讓 CC 崩潰
        if advisory_text is not None:
            sys.stderr.write(advisory_text + "\n")
            sys.stderr.flush()
        return _warn(event_name, f"[SDD-ROUTER][WARN] 轉交 {script_name} 失敗：{exc!r}。本次放行。")

    stdout_text = proc.stdout or ""
    if advisory_text is not None:
        merged_text, merged = _merge_advisory_into_stdout(stdout_text, advisory_text)
        if merged:
            stdout_text = merged_text
        else:
            # R158 P4：併不進去（child 沒印合法 JSON／缺 additionalContext 字串）—— round-label-ok
            # 退回 stderr，維持 DEF-43-004 原行為（至少印在某處，不悄悄消失）。
            sys.stderr.write(advisory_text + "\n")
            sys.stderr.flush()
    if stdout_text:
        sys.stdout.write(stdout_text)
        sys.stdout.flush()
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
