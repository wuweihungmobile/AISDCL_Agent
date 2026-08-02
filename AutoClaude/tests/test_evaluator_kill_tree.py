"""R68 回歸鎖：Evaluator / CONDITIONAL evaluator 逾時必須回收整棵行程樹。

缺陷（macOS 真機重現）：`subprocess.run(shell=True, timeout=)` 逾時時只 kill
直接子行程（/bin/sh、cmd.exe）；若該殼以 `a && b` 之類語法再 fork 出真正幹活的
孫行程，孫行程會變孤兒（PPID→1）繼續跑完並寫檔——即「已宣告逾時失敗」的工作
仍在背景產生副作用。對照組 perception/pty_wrapper.py close() 早已雙平台修好
（taskkill /T /F + killpg），evaluator 這條主線零對應防護。

三層鎖：
  1. 行為鎖（POSIX 真跑）：孫行程在逾時後不得寫出 marker；且子行程必須真的
     落在**獨立 process group**（見 `test_*_child_runs_in_its_own_process_group`）。
  2. 平台鎖（Windows 分支，mac 上以 monkeypatch 驗證命令列組裝）：
     kill_process_tree 必須送出 `taskkill /T /F /PID`。
  3. 結構鎖（AST 全樹掃描）：autoclaude/ 內任何 `shell=True` 的 subprocess
     呼叫站點都必須落在已登記且具備 kill-tree 收殺路徑的模組內。

🔴 R69 假鎖修正（`DEF-101-732`）：本檔原本對 `start_new_session` 的唯一防護是
`assert "_NEW_SESSION_KWARGS" in src` 這個**字串比對**。實測把 evaluator.py
`Popen(...)` 的 `**_NEW_SESSION_KWARGS` 整行刪掉之後——常數的**定義行**還在，
字串照樣命中——`-k "not grandchild"` 全檔 **8 passed**；連 `_NEW_SESSION_KWARGS`
自身的值鎖 `test_evaluator_uses_new_session_on_posix` 也還是綠的（它驗的是常數，
不是呼叫站點）。而該退化的後果是自殺級：子行程與 AutoClaude 同 pgid，
`kill_process_tree()` 的 `killpg` 會打到 AutoClaude 自己所在的 process group。
（實測全檔跑：pytest 直接被 SIGTERM 帶走，`wait_status=15`、零輸出——在 CI 上
讀起來像 infra flake，不像鎖抓到了回歸。）故本輪補：POSIX pgid 真行為鎖、
兩個站點的 `**` 轉發鎖（哨兵，平台無關）、AST 版結構鎖。
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

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
# 1b. 行為鎖：子行程必須落在獨立 process group（R69 假鎖修正，`DEF-101-732`）
# ──────────────────────────────────────────────

#: 探針：把自己的 pgid 寫進檔案。刻意寫成**獨立檔案**而非 `python -c`，因為
#: `_conditional.py` 的 Gap-046 白名單 `_SAFE_COND_PATTERN` 擋掉 `(`/`;`/`,`，
#: inline 程式碼過不了那道；兩個站點共用同一支探針才能用同一組斷言。
_PGID_PROBE = "import os,pathlib,sys\npathlib.Path(sys.argv[1]).write_text(str(os.getpgid(0)))\n"


def _write_pgid_probe(tmp_path):
    probe = tmp_path / "pgid_probe.py"
    probe.write_text(_PGID_PROBE, encoding="utf-8")
    return probe, tmp_path / "pgid.txt"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process group 專屬（Windows 見平台鎖）")
def test_evaluator_child_runs_in_its_own_process_group(tmp_path):
    """🔴 本檔最關鍵的一道：`kill_process_tree()` 走的是 `killpg(os.getpgid(pid))`，
    所以「子行程有沒有自己的 process group」不是風格問題，而是決定那一發 SIGKILL
    打在誰身上。少了 `start_new_session`，子行程與 AutoClaude 同 pgid ⇒ 逾時回收
    ＝ **AutoClaude 殺自己**（實測 pytest 被自己的 killpg 帶走）。

    這道直接量測真實子行程的 pgid，不看原始碼字串——原本的字串比對鎖在該退化下
    是綠的（見模組 docstring 的實測）。
    """
    probe, out = _write_pgid_probe(tmp_path)
    result = Evaluator(timeout=30).run(f'"{sys.executable}" "{probe}" "{out}"')
    assert result.success is True, f"探針未正常執行：{result.output}"
    child_pgid = int(out.read_text().strip())
    assert child_pgid != os.getpgid(0), (
        f"子行程與本行程同 process group（pgid={child_pgid}）—— "
        "Popen 未帶 start_new_session。逾時回收的 killpg 會打在 AutoClaude 自己"
        "所在的 process group 上（自殺級退化；R69 假鎖修正，DEF-101-732）"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process group 專屬（Windows 見平台鎖）")
def test_conditional_evaluator_child_runs_in_its_own_process_group(tmp_path):
    """對稱鎖：`_conditional.py` 是第二個 `shell=True` 站點，共用同一條 killpg
    收殺路徑，因此同一個自殺級退化在它身上獨立成立，必須各鎖一道。"""
    from autoclaude.execution.mutation_applier import _conditional

    probe, out = _write_pgid_probe(tmp_path)
    ctx = MagicMock()
    ctx.runner._cfg.playbook.conditional_evaluator_timeout_seconds = 30
    mutation = MagicMock()
    mutation.condition_evaluator = f"{sys.executable} {probe} {out}"
    mutation.true_mutation = None
    mutation.false_mutation = None
    _conditional.handle_conditional(ctx, mutation, MagicMock())

    assert out.exists(), (
        "CONDITIONAL 探針未執行 —— 多半是被 Gap-046 `_SAFE_COND_PATTERN` 擋下"
        "（本測試的 tmp_path 含該白名單不允許的字元），此時本鎖無鑑別力，須修測試而非放寬白名單"
    )
    child_pgid = int(out.read_text().strip())
    assert child_pgid != os.getpgid(0), (
        f"CONDITIONAL 子行程與本行程同 process group（pgid={child_pgid}）——"
        "逾時回收會 killpg 到 AutoClaude 自己（自殺級退化；R69 假鎖修正）"
    )


@pytest.mark.parametrize(
    "modname",
    ["autoclaude.execution.evaluator",
     "autoclaude.execution.mutation_applier._conditional"],
)
def test_new_session_kwargs_are_actually_forwarded_to_popen(modname):
    """轉發鎖（平台無關，**含 Windows 路徑**）：`_NEW_SESSION_KWARGS` 必須真的被
    `**` splat 進 Popen，而不是只在模組裡被 import／定義著。

    手法：把該常數換成一顆**哨兵 kwarg**，再攔截 Popen 檢查哨兵有沒有到達。
    值本身驗不出東西（Windows 上它就是空 dict，刪掉 `**` 也還是空 dict），
    所以改驗「這個 dict 不論裝什麼都會被轉發」——這條性質在兩個平台都成立，
    因此 mac 上跑這道即等同驗到 Windows 分支的轉發行為（Windows 真機零台，
    此為刻意的模擬，非真跑）。
    """
    import importlib

    mod = importlib.import_module(modname)
    sentinel = object()
    seen: dict = {}

    def _fake_popen(*args, **kwargs):
        seen.update(kwargs)
        proc = MagicMock()
        proc.communicate.return_value = ("", "")
        proc.returncode = 0
        proc.pid = 424242
        return proc

    with patch.object(mod, "_NEW_SESSION_KWARGS", {"_probe_sentinel": sentinel}), \
         patch.object(mod.subprocess, "Popen", side_effect=_fake_popen):
        if modname.endswith("evaluator"):
            mod.Evaluator(timeout=5).run("echo hi")
        else:
            ctx = MagicMock()
            ctx.runner._cfg.playbook.conditional_evaluator_timeout_seconds = 5
            mutation = MagicMock()
            mutation.condition_evaluator = "echo hi"
            mutation.true_mutation = None
            mutation.false_mutation = None
            mod.handle_conditional(ctx, mutation, MagicMock())

    assert seen.get("_probe_sentinel") is sentinel, (
        f"{modname} 的 Popen 呼叫站點沒有 `**_NEW_SESSION_KWARGS` —— "
        "行程隔離設定被丟掉了（POSIX 上即 killpg 自殺級退化；"
        "此鎖不看原始碼字串，故 import 行殘留無法滿足它）"
    )


# ──────────────────────────────────────────────
# 2. 平台鎖：Windows taskkill 分支
# ──────────────────────────────────────────────

class _FakeProc:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_kill_process_tree_uses_taskkill_tree_flag_on_windows():
    calls = []
    with patch("autoclaude.utils.platform_caps.sys.platform", "win32"), \
         patch("autoclaude.utils.platform_caps.subprocess.run",
               side_effect=lambda *a, **k: calls.append(a[0])):
        kill_process_tree(_FakeProc(4321))
    assert calls == [["taskkill", "/T", "/F", "/PID", "4321"]], (
        "Windows 側必須以 taskkill /T（整棵樹）/F（強制）回收，"
        "只殺直接子行程等同缺陷復發"
    )


def test_kill_process_tree_skips_non_int_pid():
    """測試常以 MagicMock 充當 proc，其 .pid 非 int——不得真的去殺東西。"""
    with patch("autoclaude.utils.platform_caps.subprocess.run") as run:
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
    # 🔴 R69 假鎖修正：這裡原本是 `assert "_NEW_SESSION_KWARGS" in src`，而**常數的
    # import／定義行本身就能滿足字串比對** ⇒ 把 Popen 的 `**_NEW_SESSION_KWARGS`
    # 整行刪掉，本鎖仍綠。改為 AST：要求它確實以 `**` 出現在某個 shell=True 的
    # Popen 呼叫的 keyword(arg=None) 位置上。
    splatted = set()
    for node in ast.walk(ast.parse(src, filename=rel)):
        if not isinstance(node, ast.Call):
            continue
        if not any(kw.arg == "shell" and getattr(kw.value, "value", None) is True
                   for kw in node.keywords):
            continue
        for kw in node.keywords:
            if kw.arg is None and isinstance(kw.value, ast.Name):
                splatted.add(kw.value.id)
    assert "_NEW_SESSION_KWARGS" in splatted, (
        f"{rel} 的 shell=True 呼叫未 splat `**_NEW_SESSION_KWARGS`（POSIX 上沒有獨立"
        " process group，kill_process_tree 的 killpg 會打到 AutoClaude 自己所在的"
        f" process group）。實際 splat 到的：{sorted(splatted) or '（無）'}"
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


# ──────────────────────────────────────────────
# 4. 架構鎖（R69）：平台判斷 / 行程樹回收必須收斂在 utils/platform_caps.py
# ──────────────────────────────────────────────
#
# 缺陷（Architect REJECT 主因，DEF-101-706 同源）：`sys.platform` 比較散在
# execution / perception / utils 三層 4 檔 8 處，各自演化出「同一套行程樹回收
# 的兩份複製」（evaluator.kill_process_tree vs pty_wrapper.close()）——改一邊
# 忘另一邊即單平台退化，而根層 tools/lib/platform_utils.py 跨樹不可 import、
# 結構上無法共用。收斂後全樹只准 utils/platform_caps.py 一處做平台判斷與
# 行程樹收殺，其餘模組一律走該抽象層。
#
# 本鎖刻意用 AST（非字串 grep）：註解裡提到 sys.platform / taskkill 不算違規，
# 但真正的判斷式與呼叫一定會被抓到。

#: 平台能力抽象層自身 —— 全樹唯一允許出現裸平台判斷與收殺原語的模組。
_PLATFORM_CAPS_MODULE = "utils/platform_caps.py"

#: 例外白名單（🔴 **shrink-only 棘輪**，由下方 stale 斷言真實強制，非零強制宣告）。
#: 目前為空集合＝零例外。新增條目等同繞過抽象層，須先在 ADR-XPLAT-002 記錄理由。
_BARE_PLATFORM_CHECK_ALLOWLIST: frozenset[str] = frozenset()

#: 裸平台判斷的 AST 特徵：(模組名, 屬性名)。比對的是**解析後的真實模組**，不是原始碼
#: 裡的那個名字——見下方 `_module_alias_map` 的 R69 說明。
_PLATFORM_PROBES = {("sys", "platform"), ("os", "name"), ("platform", "system")}

#: 收殺原語的 AST 特徵：(模組名, 屬性名)。同上，走別名解析。
_REAPING_PROBES = {("os", "killpg")}

#: 需要追蹤別名的模組（本鎖全部探針的模組側）。
_TRACKED_MODULES = {mod for mod, _ in _PLATFORM_PROBES | _REAPING_PROBES}


def _iter_autoclaude_modules():
    for py in sorted(_AUTOCLAUDE_ROOT.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        rel = py.relative_to(_AUTOCLAUDE_ROOT).as_posix()
        yield rel, ast.parse(py.read_text(encoding="utf-8"), filename=rel)


def _module_alias_map(tree: ast.AST) -> dict[str, str]:
    """本地名 → 真實模組名（只收本鎖關心的那幾個模組）。

    🔴 R69 終審 P1：本鎖原本逐字比對 `ast.Name.id`，於是 `import sys as _s` 之後的
    `_s.platform` 對它完全不存在——**一行 `as` 就能整支繞過**，而 `ADR-XPLAT-003` §4
    當時還宣稱「真正的判斷式與呼叫一定會被抓到」。實測（macOS）：新增一支
    `autoclaude/_r69_alias_probe.py`，內容為 `import sys as _s` / `from os import name`
    / `import platform as _p` 三種形態各一次的裸平台判斷，本節 4 支鎖**全綠**。
    名字綁定不是語意——鎖必須先把別名解回真實模組再比對。
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                if al.name in _TRACKED_MODULES:
                    aliases[al.asname or al.name] = al.name
    return aliases


def _direct_symbol_import_sites(tree: ast.AST, probes: set[tuple[str, str]]) -> bool:
    """`from sys import platform` / `from os import killpg as _k` 這一族。

    這種形態根本沒有 `ast.Attribute` 節點（用起來是裸 `ast.Name`），比別名更難抓，
    故直接把 **import 陳述式本身**判為違規站點——把探針符號拉進自己的命名空間，
    語意上就是「本模組自己做平台判斷／自己收殺」，正是本鎖要禁的事。
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _TRACKED_MODULES:
            for al in node.names:
                if (node.module, al.name) in probes:
                    return True
    return False


def _tree_hits(tree: ast.AST, probes: set[tuple[str, str]]) -> bool:
    """單一模組是否命中探針：屬性存取（經別名解析）＋ from-import 直取符號。"""
    if _direct_symbol_import_sites(tree, probes):
        return True
    aliases = _module_alias_map(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        # 未登記別名者退回「名字即模組名」（＝修復前的行為，對無 `as` 的
        # `import sys` 完全等價），登記過的則解析為真實模組。
        if (aliases.get(node.value.id, node.value.id), node.attr) in probes:
            return True
    return False


def _probe_hit_sites(probes: set[tuple[str, str]]) -> set[str]:
    """全樹掃描（`_tree_hits` 的逐檔套用；合成自證測試走的是同一條路徑）。"""
    return {
        rel
        for rel, tree in _iter_autoclaude_modules()
        if rel != _PLATFORM_CAPS_MODULE and _tree_hits(tree, probes)
    }


def _bare_platform_check_sites() -> set[str]:
    return _probe_hit_sites(_PLATFORM_PROBES)


def test_platform_checks_are_confined_to_platform_caps_module():
    found = _bare_platform_check_sites()
    assert found <= _BARE_PLATFORM_CHECK_ALLOWLIST, (
        f"下列模組直接做平台判斷而未經 {_PLATFORM_CAPS_MODULE}："
        f"{sorted(found - _BARE_PLATFORM_CHECK_ALLOWLIST)}；"
        "平台判斷分散即無法保證各平台分支同步演化（R69 Architect REJECT 主因）。"
        "請改用 platform_caps.is_windows() / is_macos() / new_session_kwargs()"
    )


@pytest.mark.parametrize(
    "label,src",
    [
        ("裸 import（修復前唯一抓得到的形態）", "import sys\nX = sys.platform == 'win32'\n"),
        ("import ... as（R69 實測整支繞過）", "import sys as _s\nX = _s.platform == 'win32'\n"),
        ("os 別名", "import os as _o\nX = _o.name == 'nt'\n"),
        ("platform 別名", "import platform as _p\nX = _p.system() == 'Windows'\n"),
        ("from ... import 直取符號", "from sys import platform\nX = platform == 'win32'\n"),
        ("from ... import ... as", "from os import name as _n\nX = _n == 'nt'\n"),
    ],
)
def test_platform_probe_sees_through_import_aliases(label, src):
    """鑑別力自證（R69 終審 P1）：名字綁定不是語意。

    修復前 `_bare_platform_check_sites()` 逐字比對 `ast.Name.id`，於是上表除第一列
    以外**全部不命中**——一行 `as` 就整支繞過，而 `ADR-XPLAT-003` §4 當時宣稱
    「真正的判斷式與呼叫一定會被抓到」。本表把「解析別名」這件事本身鎖成不變式：
    未來若有人把解析器改回逐字比對，這裡會紅，而不是等到某個生產碼模組偷渡成功。
    """
    assert _tree_hits(ast.parse(src), _PLATFORM_PROBES), f"探針對「{label}」失明"


def test_platform_probe_does_not_flag_unrelated_names():
    """對照組：同名的**區域變數**不得誤報（別名表只收真的 import 進來的模組）。"""
    assert not _tree_hits(
        ast.parse("class C:\n    platform = 'x'\n\ndef f(c):\n    return c.platform\n"),
        _PLATFORM_PROBES,
    )


def test_reaping_probe_sees_through_import_aliases():
    """收殺原語同樣走別名解析（`import os as _o` / `from os import killpg`）。"""
    for src in (
        "import os as _o, signal\ndef k(p):\n    _o.killpg(p, signal.SIGKILL)\n",
        "from os import killpg as _k\nimport signal\ndef k(p):\n    _k(p, signal.SIGKILL)\n",
    ):
        assert _tree_hits(ast.parse(src), _REAPING_PROBES), src


def test_platform_check_allowlist_is_shrink_only():
    """棘輪的牙：清單只准縮不准留殘留條目（否則白名單會退化成裝飾）。"""
    stale = _BARE_PLATFORM_CHECK_ALLOWLIST - _bare_platform_check_sites()
    assert not stale, (
        f"白名單有殘留（該模組已不再裸判平台，請把條目刪掉）：{sorted(stale)}"
    )


def _reaping_primitive_sites() -> set[str]:
    """收殺原語（os.killpg / taskkill 命令）的出現位置（AST，註解不算）。

    `os.killpg` 一側與平台探針共用同一套別名解析（R69：`import os as _o` 原本同樣
    整支繞過）；`"taskkill"` 是字串常數，本來就無別名可言。
    """
    found: set[str] = _probe_hit_sites(_REAPING_PROBES)
    for rel, tree in _iter_autoclaude_modules():
        if rel == _PLATFORM_CAPS_MODULE:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "taskkill":
                found.add(rel)
    return found


def test_process_tree_reaping_has_exactly_one_implementation():
    """DEF-101-706：kill_process_tree() 與 pty_wrapper.close() 曾是同一套行程樹
    回收的兩份複製（POSIX killpg + Windows taskkill 各寫一遍）。兩份實作 = 修一邊
    忘另一邊 = 單平台靜默退化，這在 Windows 零真機的情況下不會被任何測試抓到。"""
    offenders = _reaping_primitive_sites()
    assert not offenders, (
        f"下列模組自行實作行程樹收殺：{sorted(offenders)}；"
        f"唯一實作必須在 {_PLATFORM_CAPS_MODULE}，呼叫端一律用 kill_process_tree()"
    )


def test_both_reaping_call_sites_route_to_the_shared_implementation():
    """身分鎖：evaluator 與 pty_wrapper 必須綁到**同一顆**函式物件。
    僅靠上面的「不得自行實作」還可能出現「各自 import 自己的複製品」。"""
    from autoclaude.execution import evaluator as ev
    from autoclaude.perception import pty_wrapper as pw
    from autoclaude.utils import platform_caps

    assert ev.kill_process_tree is platform_caps.kill_process_tree
    assert pw.kill_process_tree is platform_caps.kill_process_tree
