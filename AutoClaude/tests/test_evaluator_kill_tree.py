"""R68 回歸鎖：Evaluator / CONDITIONAL evaluator 逾時必須回收整棵行程樹。

缺陷（macOS 真機重現）：`subprocess.run(shell=True, timeout=)` 逾時時只 kill
直接子行程（/bin/sh、cmd.exe）；若該殼以 `a && b` 之類語法再 fork 出真正幹活的
孫行程，孫行程會變孤兒（PPID→1）繼續跑完並寫檔——即「已宣告逾時失敗」的工作
仍在背景產生副作用。對照組 perception/pty_wrapper.py close() 早已雙平台修好
（taskkill /T /F + killpg），evaluator 這條主線零對應防護。

三層鎖：
  1. 行為鎖（POSIX 真跑）：孫行程在逾時後不得寫出 marker。
  2. 平台鎖（Windows 分支，mac 上以 monkeypatch 驗證命令列組裝）：
     kill_process_tree 必須送出 `taskkill /T /F /PID`。
  3. 結構鎖（AST 全樹掃描）：autoclaude/ 內任何 `shell=True` 的 subprocess
     呼叫站點都必須落在已登記且具備 kill-tree 收殺路徑的模組內。
"""
from __future__ import annotations

import ast
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.execution.evaluator import Evaluator, kill_process_tree

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[1] / "autoclaude"

# 結構鎖 allowlist（shrink-only）：新增 shell=True 站點必須連同 kill-tree 收殺
# 路徑一起加，或在此明確登記豁免理由。清單只准縮不准無故擴。
_SHELL_TRUE_SITES = {
    "execution/evaluator.py",
    "execution/mutation_applier/_conditional.py",
}


# ──────────────────────────────────────────────
# 1. 行為鎖：POSIX 孤兒孫行程
# ──────────────────────────────────────────────

@pytest.mark.skipif(sys.platform == "win32", reason="POSIX killpg 專屬行為（Windows 見平台鎖）")
def test_timeout_kills_grandchild_spawned_via_shell_compound_command(tmp_path):
    marker = tmp_path / "orphan_marker.txt"
    # `&&` 讓 /bin/sh 無法 exec 自我取代 → python 成為 sh 的子行程（即
    # Evaluator 的孫行程）。修復前：sh 被 kill，python 變 PPID=1 孤兒，
    # 3 秒後照樣寫出 marker。
    cmd = (
        f"{sys.executable} -c \"import time,pathlib;time.sleep(3);"
        f"pathlib.Path(r'{marker}').write_text('x')\" && echo done"
    )
    result = Evaluator(timeout=1).run(cmd, timeout=1)
    assert result.success is False
    assert "逾時" in result.output
    time.sleep(4.5)
    assert not marker.exists(), (
        "逾時後孫行程仍存活並寫出 marker —— 行程樹未被回收（R68 缺陷復發）"
    )


# ──────────────────────────────────────────────
# 2. 平台鎖：Windows taskkill 分支
# ──────────────────────────────────────────────

class _FakeProc:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_kill_process_tree_uses_taskkill_tree_flag_on_windows():
    calls = []
    with patch("autoclaude.execution.evaluator.sys.platform", "win32"), \
         patch("autoclaude.execution.evaluator.subprocess.run",
               side_effect=lambda *a, **k: calls.append(a[0])):
        kill_process_tree(_FakeProc(4321))
    assert calls == [["taskkill", "/T", "/F", "/PID", "4321"]], (
        "Windows 側必須以 taskkill /T（整棵樹）/F（強制）回收，"
        "只殺直接子行程等同缺陷復發"
    )


def test_kill_process_tree_skips_non_int_pid():
    """測試常以 MagicMock 充當 proc，其 .pid 非 int——不得真的去殺東西。"""
    with patch("autoclaude.execution.evaluator.subprocess.run") as run:
        kill_process_tree(_FakeProc("not-a-pid"))  # type: ignore[arg-type]
    run.assert_not_called()


# ──────────────────────────────────────────────
# 3. 結構鎖：全樹 shell=True 站點必須有 kill-tree 收殺路徑
# ──────────────────────────────────────────────

def _shell_true_call_sites() -> set[str]:
    found: set[str] = set()
    for py in _AUTOCLAUDE_ROOT.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name not in ("run", "Popen", "call", "check_output", "check_call"):
                continue
            for kw in node.keywords:
                if (
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    found.add(py.relative_to(_AUTOCLAUDE_ROOT).as_posix())
    return found


def test_no_unregistered_shell_true_subprocess_sites():
    found = _shell_true_call_sites()
    assert found <= _SHELL_TRUE_SITES, (
        f"新增未登記的 shell=True subprocess 站點：{sorted(found - _SHELL_TRUE_SITES)}；"
        "shell 會 fork 出孫行程，逾時時必須走 kill_process_tree 回收整棵樹"
    )
    stale = _SHELL_TRUE_SITES - found
    assert not stale, f"allowlist 有殘留（站點已消失，請縮小清單）：{sorted(stale)}"


@pytest.mark.parametrize("rel", sorted(_SHELL_TRUE_SITES))
def test_registered_shell_true_sites_wire_kill_process_tree(rel):
    src = (_AUTOCLAUDE_ROOT / rel).read_text(encoding="utf-8")
    assert "kill_process_tree" in src, f"{rel} 有 shell=True 卻無 kill-tree 收殺路徑"
    assert "_NEW_SESSION_KWARGS" in src, (
        f"{rel} 未帶 start_new_session（POSIX 上沒有獨立 process group 就無從 killpg）"
    )


def test_kill_tree_call_sites_are_reachable_from_timeout_handling():
    """kill_process_tree 必須實際掛在 TimeoutExpired 處理路徑上，
    而非只是 import 進來擺著（防「有 import、無接線」的假修復）。"""
    for rel in sorted(_SHELL_TRUE_SITES):
        tree = ast.parse((_AUTOCLAUDE_ROOT / rel).read_text(encoding="utf-8"))
        wired = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if "TimeoutExpired" not in ast.dump(node.type or ast.Constant(None)):
                continue
            if "kill_process_tree" in ast.dump(ast.Module(body=node.body, type_ignores=[])):
                wired = True
        assert wired, f"{rel} 的 except TimeoutExpired 分支未呼叫 kill_process_tree"


def test_evaluator_uses_new_session_on_posix():
    from autoclaude.execution import evaluator as ev
    expected = {} if sys.platform == "win32" else {"start_new_session": True}
    assert ev._NEW_SESSION_KWARGS == expected


def test_evaluator_normal_path_still_returns_output_and_exit_code():
    """回收機制不得破壞正常路徑（stdout/stderr 合併、exit code 透傳）。"""
    ev = Evaluator(timeout=10)
    ok = ev.run(f"{sys.executable} -c \"print('hi')\"")
    assert ok.success is True and "hi" in ok.output and ok.exit_code == 0
    bad = ev.run(f"{sys.executable} -c \"import sys;sys.stderr.write('boom');sys.exit(3)\"")
    assert bad.success is False and bad.exit_code == 3 and "boom" in bad.output
    assert isinstance(subprocess.TimeoutExpired, type)
