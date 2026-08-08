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


def _all_hook_entries(settings_path: str) -> list[dict]:
    """三份 settings 內全部 `type=command` 的 hook 條目（原始 dict，不只 command 字串）。

    🔴 R80：本檔原本取的是 `hook["command"]` 字串、再以 `shell=True` 跑它。Claude Code
    的 hook 條目有兩種形態：shell form 的 `command` 本來就是要交給 shell 的一整串；
    **exec form**（帶 `args`；Windows 上不經 `bash.exe` 故不閃 console 視窗）的 `command`
    只是一個**執行檔路徑**、真正的引數在 `args` 裡。拿後者去 `shell=True` 會變成
    「跑一個叫 `${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe` 的指令」＝rc≠0，
    而本檔第一道防線正是在斷言 rc==0（fail-open）⇒ 形態一轉就會假紅。
    改成保留整個條目、交由 `_run()` 依形態決定怎麼起。
    """
    with open(settings_path, encoding="utf-8") as f:
        doc = json.load(f)
    entries: list[dict] = []
    for event_blocks in doc.get("hooks", {}).values():
        for blk in event_blocks:
            for hook in blk.get("hooks", []):
                if hook.get("type", "command") == "command":
                    entries.append(hook)
    return entries


def _describe(hook: dict) -> str:
    """給斷言訊息用的可讀描述（兩種形態都要看得懂它會跑什麼）。"""
    return " ".join(lint._hook_wiring().hook_entry_argv(hook))


def _run(hook: dict, cwd: str, extra_env: dict[str, str] | None = None,
         stdin_payload: str = "") -> subprocess.CompletedProcess:
    """依條目形態起它：shell form 走 `shell=True`；exec form 走 argv list（不經 shell）。

    exec form 的 `${CLAUDE_PROJECT_DIR}` 由 CC 展開，測試環境沒有 CC ⇒ 這裡自己展開成
    `extra_env` 給的值（未給時展開成 cwd，重現「cwd≠專案根」那個 P0 情境）。
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    # 測試環境不啟 SDD 守門，確保 router 走休眠快路徑
    env.pop("SDD_ACTIVE_VERSION", None)
    if extra_env:
        env.update(extra_env)
    wiring = lint._hook_wiring()
    common = {
        "cwd": cwd, "env": env, "input": stdin_payload, "capture_output": True,
        "text": True, "encoding": "utf-8", "errors": "replace", "timeout": 60,
    }
    argv = wiring.hook_entry_argv(hook)
    if not wiring.is_exec_form(hook):
        return subprocess.run(argv[0], shell=True, **common)
    project_dir = env.get("CLAUDE_PROJECT_DIR", cwd)
    return subprocess.run(wiring.expand_tokens(argv, project_dir), **common)


def _viable(hook: dict, project_dir: str) -> bool:
    """本平台上這個條目的載具跑不跑得起來（跨平台配對的另一半是刻意 fail-open）。"""
    return lint._hook_wiring().carrier_available(hook, project_dir)


def test_missing_target_is_fail_open_not_deny():
    """cwd=空目錄且無 CLAUDE_PROJECT_DIR → 目標腳本缺檔，必須 exit 0（絕不可 2=deny）。"""
    with tempfile.TemporaryDirectory() as tmp:
        checked = 0
        for settings in _settings_paths():
            for hook in _all_hook_entries(settings):
                if not _viable(hook, tmp):
                    continue  # 跨平台配對的另一半：CC 對 spawn 失敗是 fail-open
                res = _run(hook, cwd=tmp, stdin_payload="{}")
                checked += 1
                assert res.returncode == 0, (
                    f"hook 條目在 cwd≠專案根時未 fail-open（rc={res.returncode}，"
                    f"rc=2 會被 PreToolUse 視為 deny 而鎖死 session）：\n"
                    f"  settings: {settings}\n  entry: {_describe(hook)}\n"
                    f"  stderr: {res.stderr[:400]}"
                )
        # 反空轉：全部條目都被判成「本平台不可跑」時上面的迴圈一次都沒跑，
        # 而那與「全部通過」在 rc 上無法區分（R80 exec form 轉換的失明形態）。
        assert checked >= 3, f"本平台可跑的 hook 條目只有 {checked} 條 ⇒ 本鎖已近乎空轉"


def test_claude_project_dir_anchors_root_router():
    """cwd=空目錄但 CLAUDE_PROJECT_DIR=monorepo 根 → router 必須真正執行。"""
    root = _monorepo_root()
    settings = os.path.join(root, ".claude", "settings.json")
    wiring = lint._hook_wiring()
    hooks = [
        h for h in _all_hook_entries(settings)
        if any("sdd_hook_router" in rel
               for rel in wiring.hook_entry_targets(h, include_launcher=True))
    ]
    assert hooks, "根 settings.json 找不到 sdd_hook_router 佈線"
    runnable = [h for h in hooks if _viable(h, root)]
    assert runnable, (
        "根 settings.json 有 sdd_hook_router 佈線，但**本平台一條都跑不起來** ⇒ "
        f"router 在這台機器上整支靜默失效。條目：{[_describe(h) for h in hooks]}"
    )
    with tempfile.TemporaryDirectory() as tmp:
        for hook in runnable:
            res = _run(hook, cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": root},
                       stdin_payload='{"tool_name": "Bash", "tool_input": {}}')
            assert res.returncode == 0, (
                f"錨定情境下 router 執行失敗（rc={res.returncode}）："
                f"{_describe(hook)}\n{res.stderr[:400]}"
            )
            assert "hookSpecificOutput" in res.stdout, (
                f"錨定情境下 router 未真正執行（stdout 無 hookSpecificOutput）："
                f"{_describe(hook)}"
            )


def test_claude_project_dir_anchors_autoclaude_deny_semantics():
    """AutoClaude 錨定情境：enforce_docs_path 經 shim 仍真執行且保留 exit 2 阻斷語意。"""
    ac_root = os.path.join(_monorepo_root(), "AutoClaude")
    settings = os.path.join(ac_root, ".claude", "settings.json")
    with open(settings, encoding="utf-8") as f:
        doc = json.load(f)
    wiring = lint._hook_wiring()
    hooks = [
        h
        for blk in doc["hooks"]["PreToolUse"]
        for h in blk["hooks"]
        if any("enforce_docs_path" in rel
               for rel in wiring.hook_entry_targets(h, include_launcher=True))
    ]
    assert hooks, "AutoClaude settings.json 找不到 enforce_docs_path 佈線"
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "evil_probe.md", "content": "x"}}
    )
    with tempfile.TemporaryDirectory() as tmp:
        res = _run(hooks[0], cwd=tmp, extra_env={"CLAUDE_PROJECT_DIR": ac_root},
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
    hooks = [h for blk in doc["hooks"]["SessionStart"] for h in blk["hooks"]]
    assert hooks, f"{latest} settings.json 找不到 SessionStart 佈線"
    with tempfile.TemporaryDirectory() as tmp:
        # SDD_HOOKS_DISABLE=1：disabled 分支仍輸出 hookSpecificOutput，足證 shim 真執行
        # 目標腳本，且不觸碰 v0.30 dogfooding FSM 狀態（bootstrap/reconcile 零副作用）
        res = _run(hooks[0], cwd=tmp,
                   extra_env={"CLAUDE_PROJECT_DIR": v_root, "SDD_HOOKS_DISABLE": "1"})
        assert res.returncode == 0, (
            f"錨定情境下 {latest} session_start 執行失敗（rc={res.returncode}）\n{res.stderr[:400]}"
        )
        assert "hookSpecificOutput" in res.stdout, (
            f"錨定情境下 {latest} session_start 未真正執行（stdout 無 hookSpecificOutput）"
        )


def test_commands_are_project_dir_anchored():
    """結構鎖：每個條目必須引用 CLAUDE_PROJECT_DIR（防回退成裸相對路徑）。

    R80：判斷面由「`command` 字串」擴成「`command` ＋ `args` 整串」——exec form 的錨定
    可能寫在 `args` 元素裡（實測 `${CLAUDE_PROJECT_DIR}` 在兩處都會被 CC 展開），
    只看 `command` 會把已錨定的條目誤判成未錨定。
    """
    for settings in _settings_paths():
        for hook in _all_hook_entries(settings):
            joined = _describe(hook)
            assert "CLAUDE_PROJECT_DIR" in joined, (
                f"hook 條目未經 CLAUDE_PROJECT_DIR 錨定（回退成 cwd 相對路徑會復發 P0）：\n"
                f"  settings: {settings}\n  entry: {joined}"
            )
