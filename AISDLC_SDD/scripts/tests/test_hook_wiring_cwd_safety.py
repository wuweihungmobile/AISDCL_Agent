"""Hook wiring cwd 安全性 contract — 四方複審第四輪 P0 回歸鎖.

為何重要（Rule 9 / Rule 12 fail-loud）：三份 settings.json（monorepo 根 router、
AutoClaude、AISDLC_SDD LATEST 版）的 hook command 原為「裸 `python <相對路徑>`」，
hook 子行程的 cwd ≠ 對應專案根時（Agent SDK spawn 子 session、Bash 工具 cd 殘留），
python 找不到腳本的退出碼**恰為 2**＝Claude Code PreToolUse 的「deny」語意 →
matcher 涵蓋的全部工具（Write/Edit/Read/Bash/Task）被連鎖硬阻斷，session 完全癱瘓
（四方複審第四輪 SD P0 live 實證）。修法＝python -c shim：python 自行讀
CLAUDE_PROJECT_DIR 環境變數錨定專案根（不經 shell 變數展開，Windows cmd 亦可用），
缺檔 fail-open exit 0（恢復 ONBOARDING §4 文件宣稱的「靜默失效」語意）。

本鎖三道防線：
1. 行為鎖（缺檔情境）：每條 hook command 在「cwd=空目錄 + 無 CLAUDE_PROJECT_DIR」
   下執行必須 exit 0（絕不可為 2 = deny）。
2. 行為鎖（錨定情境）：根 router command 在「cwd=空目錄 + CLAUDE_PROJECT_DIR=根」
   下必須真正執行 router（stdout 出現 hookSpecificOutput）。
3. 結構鎖：每條 command 必須引用 CLAUDE_PROJECT_DIR（防止回退成裸相對路徑）。
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile

from scripts import router_hook_coverage_lint as lint


def _sdd_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _monorepo_root() -> str:
    return os.path.dirname(_sdd_root())


def _settings_paths() -> list[str]:
    """三份受 contract 保護的 settings.json：根 router、AutoClaude、SDD LATEST。"""
    paths = [
        os.path.join(_monorepo_root(), ".claude", "settings.json"),
        os.path.join(_monorepo_root(), "AutoClaude", ".claude", "settings.json"),
    ]
    latest = lint.analyze(_sdd_root()).get("latest")
    if latest:
        paths.append(os.path.join(_sdd_root(), latest, ".claude", "settings.json"))
    return paths


def _all_hook_commands(settings_path: str) -> list[str]:
    with open(settings_path, encoding="utf-8") as f:
        doc = json.load(f)
    commands: list[str] = []
    for event_blocks in doc.get("hooks", {}).values():
        for blk in event_blocks:
            for hook in blk.get("hooks", []):
                if hook.get("type") == "command":
                    commands.append(hook["command"])
    return commands


def _run(command: str, cwd: str, extra_env: dict[str, str] | None = None,
         stdin_payload: str = "") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    # 測試環境不啟 SDD 守門，確保 router 走休眠快路徑
    env.pop("SDD_ACTIVE_VERSION", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        command, shell=True, cwd=cwd, env=env,
        input=stdin_payload, capture_output=True, text=True, timeout=60,
    )


def test_missing_target_is_fail_open_not_deny():
    """cwd=空目錄且無 CLAUDE_PROJECT_DIR → 目標腳本缺檔，必須 exit 0（絕不可 2=deny）。"""
    with tempfile.TemporaryDirectory() as tmp:
        for settings in _settings_paths():
            for cmd in _all_hook_commands(settings):
                res = _run(cmd, cwd=tmp, stdin_payload="{}")
                assert res.returncode == 0, (
                    f"hook command 在 cwd≠專案根時未 fail-open（rc={res.returncode}，"
                    f"rc=2 會被 PreToolUse 視為 deny 而鎖死 session）：\n"
                    f"  settings: {settings}\n  command: {cmd}\n  stderr: {res.stderr[:400]}"
                )


def test_claude_project_dir_anchors_root_router():
    """cwd=空目錄但 CLAUDE_PROJECT_DIR=monorepo 根 → router 必須真正執行。"""
    root = _monorepo_root()
    settings = os.path.join(root, ".claude", "settings.json")
    commands = [c for c in _all_hook_commands(settings) if "sdd_hook_router" in c]
    assert commands, "根 settings.json 找不到 sdd_hook_router 佈線"
    with tempfile.TemporaryDirectory() as tmp:
        for cmd in commands:
            res = _run(cmd, cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": root},
                       stdin_payload='{"tool_name": "Bash", "tool_input": {}}')
            assert res.returncode == 0, (
                f"錨定情境下 router 執行失敗（rc={res.returncode}）：{cmd}\n{res.stderr[:400]}"
            )
            assert "hookSpecificOutput" in res.stdout, (
                f"錨定情境下 router 未真正執行（stdout 無 hookSpecificOutput）：{cmd}"
            )


def test_claude_project_dir_anchors_autoclaude_deny_semantics():
    """AutoClaude 錨定情境：enforce_docs_path 經 shim 仍真執行且保留 exit 2 阻斷語意。"""
    ac_root = os.path.join(_monorepo_root(), "AutoClaude")
    settings = os.path.join(ac_root, ".claude", "settings.json")
    with open(settings, encoding="utf-8") as f:
        doc = json.load(f)
    commands = [
        h["command"]
        for blk in doc["hooks"]["PreToolUse"]
        for h in blk["hooks"]
        if "enforce_docs_path" in h.get("command", "")
    ]
    assert commands, "AutoClaude settings.json 找不到 enforce_docs_path 佈線"
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "evil_probe.md", "content": "x"}}
    )
    with tempfile.TemporaryDirectory() as tmp:
        res = _run(commands[0], cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": ac_root},
                   stdin_payload=payload)
        assert res.returncode == 2, (
            f"錨定情境下 enforce_docs_path 未保留阻斷語意（rc={res.returncode}）——"
            f"shim 必須原樣傳遞目標腳本的 exit 2\n{res.stderr[:400]}"
        )


def test_claude_project_dir_anchors_latest_version_session_start():
    """SDD LATEST 版錨定情境：session_start 經 shim 真執行（stdout 出現 hookSpecificOutput）。"""
    latest = lint.analyze(_sdd_root()).get("latest")
    assert latest, "找不到最新演化版"
    v_root = os.path.join(_sdd_root(), latest)
    settings = os.path.join(v_root, ".claude", "settings.json")
    with open(settings, encoding="utf-8") as f:
        doc = json.load(f)
    commands = [
        h["command"]
        for blk in doc["hooks"]["SessionStart"]
        for h in blk["hooks"]
    ]
    assert commands, f"{latest} settings.json 找不到 SessionStart 佈線"
    with tempfile.TemporaryDirectory() as tmp:
        # SDD_HOOKS_DISABLE=1：disabled 分支仍輸出 hookSpecificOutput，足證 shim 真執行
        # 目標腳本，且不觸碰 v0.30 dogfooding FSM 狀態（bootstrap/reconcile 零副作用）
        res = _run(commands[0], cwd=tmp,
                   extra_env={"CLAUDE_PROJECT_DIR": v_root, "SDD_HOOKS_DISABLE": "1"})
        assert res.returncode == 0, (
            f"錨定情境下 {latest} session_start 執行失敗（rc={res.returncode}）\n{res.stderr[:400]}"
        )
        assert "hookSpecificOutput" in res.stdout, (
            f"錨定情境下 {latest} session_start 未真正執行（stdout 無 hookSpecificOutput）"
        )


def test_commands_are_project_dir_anchored():
    """結構鎖：每條 command 必須引用 CLAUDE_PROJECT_DIR（防回退成裸相對路徑）。"""
    for settings in _settings_paths():
        for cmd in _all_hook_commands(settings):
            assert "CLAUDE_PROJECT_DIR" in cmd, (
                f"hook command 未經 CLAUDE_PROJECT_DIR 錨定（回退成 cwd 相對路徑會復發 P0）：\n"
                f"  settings: {settings}\n  command: {cmd}"
            )
