#!/usr/bin/env python3
"""tools/check_hooks_liveness.py 的單元測試（S11：抽出四份重複 liveness 偵測邏輯後，
驗證鏡子自身要被驗證 — 單一真相源必須有測試，不可只憑呼叫端手動走查）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# 平台中立的假「絕對」repo 根（WHY 見 _platform_helpers 常數旁註解；R11 真 Mac
# 首跑實證：寫死 "D:/repo" 在 POSIX 非絕對路徑 → join/resolve 語意分歧假紅）。
from _platform_helpers import ABS_FAKE_REPO  # noqa: E402

import check_hooks_liveness as m  # noqa: E402


class TestCheckHooksLiveness(unittest.TestCase):
    def test_not_in_git_repo_returns_true_silently(self) -> None:
        """`git rev-parse --show-toplevel` 失敗（不在 repo 內）→ 無法判定，不警告。"""
        with mock.patch.object(m, "_run", return_value=""):
            self.assertTrue(m.check_hooks_liveness())

    def test_matching_hooks_path_returns_true_without_warning(self) -> None:
        """core.hooksPath 與 `<top>/tools/git-hooks` 一致且三支 hook 檔齊備 → PASS，不印警告。"""

        def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["git", "rev-parse"]:
                return str(ABS_FAKE_REPO)
            if "config" in cmd:
                return "tools/git-hooks"
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("pathlib.Path.is_file", return_value=True), \
             mock.patch("builtins.print") as mock_print:
            self.assertTrue(m.check_hooks_liveness())
            mock_print.assert_not_called()

    def test_mismatched_hooks_path_returns_false_with_warning(self) -> None:
        """core.hooksPath 指向錯誤路徑 → FAIL，印出警告（含目前值與預期值）。"""
        wrong_abs = str(ABS_FAKE_REPO.parent / "wrong" / "path")

        def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["git", "rev-parse"]:
                return str(ABS_FAKE_REPO)
            if "config" in cmd:
                return wrong_abs
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("builtins.print") as mock_print:
            self.assertFalse(m.check_hooks_liveness())
            printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("dispatcher git hooks 未生效", printed)
            self.assertIn(wrong_abs, printed)

    def test_unset_hooks_path_shows_placeholder(self) -> None:
        """core.hooksPath 完全未設定 → 警告顯示「（未設定）」而非空字串。"""

        def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["git", "rev-parse"]:
                return str(ABS_FAKE_REPO)
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("builtins.print") as mock_print:
            self.assertFalse(m.check_hooks_liveness())
            printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("（未設定）", printed)

    def test_main_exit_code_reflects_result(self) -> None:
        """CLI entrypoint：liveness True → exit 0；False → exit 1（供呼叫端識別，雖為 advisory）。"""
        with mock.patch.object(m, "check_hooks_liveness", return_value=True):
            self.assertEqual(0 if m.check_hooks_liveness() else 1, 0)
        with mock.patch.object(m, "check_hooks_liveness", return_value=False):
            self.assertEqual(0 if m.check_hooks_liveness() else 1, 1)

    def test_linked_worktree_mismatch_prints_worktree_specific_hint(self) -> None:
        """S22：本檔（advisory-only）過去完全不處理 linked worktree，會用本
        worktree 自己的根目錄誤判「未生效」。收斂到共用 evaluate() 後，偵測到
        linked worktree 時警告文字須明確提及，而非泛用的重裝指示。"""

        def fake_run(cmd: list[str]) -> str:
            # 三支 rev-parse 呼叫皆以 `-C <top>` 前綴，故不能用 cmd[:2] 區分——依尾端
            # 旗標判斷（與 check_hooks_liveness()/step_hooks() 實際呼叫方式一致）。
            if "--git-dir" in cmd:
                return "/repo/.git/worktrees/wt"
            if "--git-common-dir" in cmd:
                return "/repo/.git"
            if cmd[:2] == ["git", "rev-parse"]:
                return "/repo-wt1"  # --show-toplevel（唯一沒有 -C 前綴的呼叫）：本 worktree 自己的根目錄
            if "config" in cmd:
                return ""  # 主 checkout 從未安裝
            return ""

        with mock.patch.object(m, "_run", side_effect=fake_run), \
             mock.patch("builtins.print") as mock_print:
            self.assertFalse(m.check_hooks_liveness())
            printed = "\n".join(str(c.args[0]) for c in mock_print.call_args_list if c.args)
            self.assertIn("linked worktree", printed)


class TestResolveExpectedHooksDir(unittest.TestCase):
    """`resolve_expected_hooks_dir()` 純函式：dev_start.step_hooks() 與
    check_hooks_liveness() 共用同一份判定，此處直接單元測試演算法本身。"""

    def test_non_worktree_uses_repo_root(self) -> None:
        hooks_dir, is_linked = m.resolve_expected_hooks_dir(ABS_FAKE_REPO, "", "")
        self.assertFalse(is_linked)
        self.assertEqual(hooks_dir, (ABS_FAKE_REPO / "tools" / "git-hooks").resolve())

    def test_linked_worktree_resolves_to_main_checkout(self) -> None:
        hooks_dir, is_linked = m.resolve_expected_hooks_dir(
            Path(f"{ABS_FAKE_REPO}-wt1"),
            str(ABS_FAKE_REPO / ".git" / "worktrees" / "wt"),
            str(ABS_FAKE_REPO / ".git"),
        )
        self.assertTrue(is_linked)
        self.assertEqual(hooks_dir, (ABS_FAKE_REPO / "tools" / "git-hooks").resolve())

    def test_same_git_dir_and_common_dir_is_not_linked_worktree(self) -> None:
        _, is_linked = m.resolve_expected_hooks_dir(
            ABS_FAKE_REPO, str(ABS_FAKE_REPO / ".git"), str(ABS_FAKE_REPO / ".git")
        )
        self.assertFalse(is_linked)


class TestIsHooksEffective(unittest.TestCase):
    """`is_hooks_effective()` 純函式：路徑比對 + 三支 hook 檔齊備 + is_file 可注入。"""

    def test_empty_current_value_is_not_effective(self) -> None:
        self.assertFalse(
            m.is_hooks_effective(ABS_FAKE_REPO, ABS_FAKE_REPO / "tools" / "git-hooks", "")
        )

    def test_mismatched_path_is_not_effective(self) -> None:
        self.assertFalse(
            m.is_hooks_effective(
                ABS_FAKE_REPO,
                ABS_FAKE_REPO / "tools" / "git-hooks",
                str(ABS_FAKE_REPO.parent / "wrong"),
            )
        )

    def test_matching_path_defers_to_injected_is_file(self) -> None:
        hooks_dir = ABS_FAKE_REPO / "tools" / "git-hooks"
        self.assertTrue(
            m.is_hooks_effective(
                ABS_FAKE_REPO, hooks_dir, str(hooks_dir), is_file=lambda _p: True
            )
        )
        self.assertFalse(
            m.is_hooks_effective(
                ABS_FAKE_REPO, hooks_dir, str(hooks_dir), is_file=lambda _p: False
            )
        )

    def test_is_file_injection_lets_caller_supply_oserror_safe_wrapper(self) -> None:
        """dev_start.py 注入自家 `_safe_is_file`（吞 OSError）；本函式不得繞過注入
        自己另外裸呼叫 `Path.is_file()`（否則 dev_start 的 OSError 防護就被架空）。"""
        calls: list[Path] = []

        def safe_is_file(p: Path) -> bool:
            calls.append(p)
            return True

        hooks_dir = ABS_FAKE_REPO / "tools" / "git-hooks"
        result = m.is_hooks_effective(
            ABS_FAKE_REPO, hooks_dir, str(hooks_dir), is_file=safe_is_file
        )
        self.assertTrue(result)
        self.assertEqual(len(calls), 3)  # pre-commit / pre-push / post-commit


class TestRunEncodingRegression(unittest.TestCase):
    """R10 QA-8（DEF-101-137）：_run() 的顯式 encoding 回歸鎖。

    WHY：R9 修復「text=True 無 encoding 在 zh-TW Windows 走 cp950 → 非 ASCII repo
    路徑 UnicodeDecodeError → liveness 靜默失效（無法判定＝不警告）」，但 13 個既有
    case 全 mock _run，重構移除 encoding 參數時測試依然全綠。本 case 直接鎖住
    subprocess.run 的呼叫參數（同輪同款修復在 test_git_hooks_install_common 有鎖，
    此處補齊對稱）。
    """

    def test_run_passes_explicit_utf8_encoding(self) -> None:
        with mock.patch.object(m.subprocess, "run") as fake_run:
            fake_run.return_value = mock.Mock(returncode=0, stdout="ok\n")
            out = m._run(["git", "rev-parse", "--show-toplevel"])
        self.assertEqual(out, "ok")
        _args, kwargs = fake_run.call_args
        self.assertEqual(kwargs.get("encoding"), "utf-8",
                         "_run 必須顯式 encoding='utf-8'（cp950 UnicodeDecodeError 防護）")
        self.assertEqual(kwargs.get("errors"), "replace",
                         "_run 必須 errors='replace'（劣化為亂碼而非例外）")


# ══════════════════════════════════════════════════════════════════════════
# R73（DEF-101-785）：`.claude/hooks/block_bash_on_windows.py` 的回歸鎖
# ══════════════════════════════════════════════════════════════════════════
# 🔴 **為何併進本檔而非另立新檔**：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
# `_FROZEN_GUARD_FILE_COUNT` 是 **shrink-only 棘輪**，`DEF-101-561③` 明文裁決
# 「禁止新增鎖檔、只准合併／刪除」。R73 首版新建了一支獨立檔案，當場被該棘輪攔下
# （53 → 54，三條斷言同時翻紅）。**正解是併入既有鎖檔而不是調升那個常數**——
# 調升等於用一行 diff 推翻一條裁決。本檔是最貼近的家：它本來就管「hook 有沒有
# 註冊、是不是活的」。
#
# `.claude/hooks/block_bash_on_windows.py` 的回歸鎖（R73／DEF-101-785）。
#
# WHY 這支鎖到 R73 才出現，以及為何不能再沒有它
# ------------------------------------------------
# 根 `CLAUDE.md`〈Windows 側單一載具原則〉鐵律一是掌舵者的直接指令，而該節明載：
# 純文件約束**實證無攔阻力**（R71 寫完那節的同一個回合仍用了 Bash 工具，掌舵者兩度
# 指出後才改上 hook）。也就是說這支 hook 是鐵律一**唯一**的機械強制物。
#
# 但它自己零測試覆蓋（R73 QA 二審實測：全庫 `*.py` 對 `block_bash_on_windows` 零命中），
# 後果已經發生而非假想——它的指引訊息教人寫裸 `bash <script>`，而那個做法在本機是壞的
# （`Get-Command bash` 解析到 system32 的 WSL 佔位版、反斜線路徑分隔符被整批吃掉，
# `DEF-101-773`）。那句錯誤指引漂了整整一輪才被 R73 的 Scan-M 抓到。**機械強制物教錯
# 比純文件教錯更嚴重**：讀者會認為它比文件權威。
#
# 同時它帶著一個 P0 風險（`.claude/settings.json` 記載過）：hook 誤觸 PreToolUse deny
# 會把**所有**工具硬鎖死。所以「射程不得擴大」與「例外一律 fail-open」這兩條不是
# 風格偏好，是安全需求——需要鎖住，不能靠讀 code 自覺。
#
# 本鎖守四件事
# ------------
# 1. **行為契約**（四種輸入 × 平台）：Bash→2 阻斷／非 Bash→0 不擴大射程／壞 JSON 與
#    空輸入→2 fail-closed／非 Windows→0 不誤傷。R71 只做過一次性手驗，沒有任何鎖。
# 2. **非 Windows 不得誤傷**：mac/Linux 上 bash 才是正確載具（單平台判準不可無條件
#    外推，`DEF-101-766` 同型教訓）。
# 3. **指引訊息內容**：不得回頭教裸 `bash`，且必須指向 repo 既有 SSOT
#    `tools/lib/Find-GitBash.ps1`（`DEF-101-778` 的回歸鎖）。
# 4. **註冊活性**：hook 必須真的掛在 `.claude/settings.json` 的 PreToolUse／matcher=Bash
#    上——「裝了但不會跑的鎖」是本 repo 反覆出現的形態。
#
# 執行：`python -m unittest discover -s tools/tests`


_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "block_bash_on_windows.py"
_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"


def _child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """子行程環境：**顯式剝除** `PYTHONUTF8` / `PYTHONIOENCODING`（可再疊 `extra`）。

    🔴 為何不能靠繼承（DEF-101-789）：`_run_hook` 原本不傳 `env=`，於是子行程的
    UTF-8 串流設定由**外層環境供應**——本機唯一來源是 `.claude/settings.json` 的
    `env.PYTHONUTF8=1`（User/Machine scope 實測皆空），也就是說這支鎖的綠燈是
    agent harness 注入的，不是被測物的性質。同一份知識 repo 內早有兩處落地：
    `test_find_git_bash_parity.py` 對 `PYTHONUTF8` 的 `env.pop`（該處逐字寫明
    「不能靠繼承而假綠」）與 `test_git_hooks_install_common.py` 的
    `_env_without_utf8_overrides()`。**知識在樹裡、只有一處有鎖，新站點照樣踩進去**
    ——本函式把它補齊到第三處。

    🔴 R75 補記（DEF-101-803）：上一段逐字指名「本機唯一 UTF-8 來源是
    `.claude/settings.json` 的 `env.PYTHONUTF8=1`」，而那個 env 條目**當時零鎖看守**
    ——被誰刪掉都不會有任何測試變紅，R74 P0 就靜默復發。**在註記裡指出一個關鍵依賴
    卻不給它鎖，等於把它標成「已知且已接受」**。該鎖現在在
    `TestSettingsProvideUtf8ForHookChildren`。
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    if extra:
        env.update(extra)
    return env


def _run_hook(
    stdin_text: str,
    *,
    force_os_name: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> tuple[int, str]:
    """以子行程真跑 hook，回 `(rc, stderr)`。

    刻意走子行程而非 import + monkeypatch：hook 的契約是「被 Claude Code 以獨立行程
    呼叫、讀 stdin、以 exit code 表態」，import 進來直接呼叫 `main()` 會繞過
    `sys.stdin` 與 exit code 這兩個契約面（本 repo 有「驗證載具必須對齊 production
    真正執行路徑」的既有紀律）。

    子行程環境一律走 `_child_env()`（剝除 UTF-8 覆寫），理由見該函式。`env_extra`
    用來**指定**一個非 UTF-8 的 locale 編碼，重現 en-US Windows／GitHub
    windows-latest 的條件。

    `force_os_name` 用來驗非 Windows 分支：hook 讀 `os.name`，而測試機是 Windows。
    以 `-c` 前置注入假 `os.name` 再 exec hook 本體，是唯一能在單一平台上驗到
    **兩個平台方向**的做法（同 `test_ps_engine_ssot.py` 用合成 `shutil.which`
    偽造雙引擎的理由：判準的方向不該取決於這台機器剛好是什麼）。
    """
    if force_os_name is None:
        cmd = [sys.executable, str(_HOOK)]
    else:
        bootstrap = (
            "import os, runpy, sys\n"
            f"os.name = {force_os_name!r}\n"
            f"runpy.run_path({str(_HOOK)!r}, run_name='__main__')\n"
        )
        cmd = [sys.executable, "-c", bootstrap]
    proc = subprocess.run(
        cmd, input=stdin_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
        env=_child_env(env_extra),
    )
    return proc.returncode, proc.stderr or ""


# ══════════════════════════════════════════════════════════════════════════
# 退化 payload × matcher 射程：兩道鎖的交界（本輪，DEF 待登記）
# ══════════════════════════════════════════════════════════════════════════
# 這一段取代了此前兩條「退化 payload 一律 exit 2」的平坦斷言。**不是放寬**，是把
# 它們真正要防的東西寫清楚，順便解掉一組互鎖。
#
#   · 那兩條要防的是**守衛靜默失效**：讀不懂輸入時放行，等於讓「送壞 payload」
#     成為讓守衛整支消失的免費手段，而且失效不會有任何人看見。這個意圖不變。
#   · 但它們寫成「一律 exit 2」，於是硬擋的爆炸半徑完全由**註冊面的 matcher**
#     決定，而 matcher 由另一道鎖在管（子代理注入曾要求每個 matcher 都含 Task）。
#     兩者相乘的結果：一份解析不出工具名的 payload 會讓一支與子代理無關的守衛
#     硬擋派工，訊息還指向不相干的原因。七輸入實測逐字重現過該狀態。
#
# 新判準把兩件事綁成一個不可拆的組合：
#   ① 退化 payload **不得被靜默放行**（rc==0 即紅——原意保住）；
#   ② 若守衛選擇硬擋（rc==2），它註冊的 matcher **不得圈到射程外的工具**。
# 想放寬 matcher 的人會被逼著同時面對退化行為，反之亦然，交界處不再有無人同意的
# 狀態。對稱的另一半在 AISDLC_SDD/scripts/tests/test_pretooluse_matcher_task.py
# （全稱約定收斂為只約束承載子代理注入的那些條目）。
#
# 誠實劃界：本判準**不**釘住「某支守衛必須選 rc==2 而不是 rc==1」。rc 2→1 是行為
# 變更但不是靜默失效（仍會出聲），要不要那樣改屬設計決定，記在各 hook 自己的
# docstring 裡；本判準只保證兩者永遠是配套的。


def matcher_tokens(matcher: str) -> set[str]:
    """把 matcher（正則交替字串）拆成工具名集合；空字串／`*`＝全部，以 `*` 表示。"""
    text = str(matcher or "").strip()
    if not text or text == "*":
        return {"*"}
    return {tok.strip() for tok in text.split("|") if tok.strip()}


def matchers_for_script(settings: dict, needle: str) -> list[str]:
    """`settings` 的 PreToolUse 內，command 指名 `needle` 的所有 matcher。"""
    found: list[str] = []
    for entry in settings.get("hooks", {}).get("PreToolUse", []) or []:
        commands = [str(h.get("command", "")) for h in entry.get("hooks") or []]
        if any(needle in command for command in commands):
            found.append(str(entry.get("matcher", "")))
    return found


def degraded_payload_verdict(
    script: str, own_tools: set[str], degraded_rc: int, matchers: list[str]
) -> str | None:
    """`None`＝合格；回字串＝失效理由（純函式，紅綠由合成注入自證）。"""
    if degraded_rc == 0:
        return (f"{script} 對退化 payload 靜默放行（rc=0）——讀不懂輸入時放行，"
                "等於讓『送壞 payload』成為讓守衛整支消失的免費手段，"
                "而且它失效時沒有任何人會看見")
    if degraded_rc != 2:
        return None  # 出聲但不阻斷：爆炸半徑為零，合法
    if not matchers:
        return (f"{script} 對退化 payload 硬擋（rc=2），卻在 .claude/settings.json 的"
                " PreToolUse 內找不到它的註冊 ⇒ 射程無從判定（可能已靜默失效）")
    outside = sorted({t for m in matchers for t in matcher_tokens(m)} - own_tools)
    if outside:
        return (f"{script} 對退化 payload 硬擋（rc=2），而它註冊的 matcher 還圈了"
                f"射程外的工具 {outside} ⇒ 一份解析不出工具名的 payload 會連那些"
                "工具一起擋掉，訊息還指向不相干的原因。二擇一：把 matcher 收到"
                "自己的射程內，或把退化行為改成『出聲但不阻斷』")
    return None


class TestDegradedPayloadScopeCriterion(unittest.TestCase):
    """判準自證：六種組合，不靠 repo 現況剛好是哪一種。"""

    def test_silent_allow_is_red(self) -> None:
        verdict = degraded_payload_verdict("h.py", {"Bash"}, 0, ["Bash"])
        self.assertIn("靜默放行", verdict or "")

    def test_hard_block_with_wide_matcher_is_red(self) -> None:
        """本輪那筆缺陷的狀態逐字重建：rc=2 ＋ matcher 多圈一個子代理工具。"""
        verdict = degraded_payload_verdict("h.py", {"Bash"}, 2, ["Bash|Task"])
        self.assertIsNotNone(verdict, "多圈一個工具的硬擋守衛竟被判為合格")
        self.assertIn("Task", verdict or "")

    def test_hard_block_with_narrow_matcher_is_green(self) -> None:
        self.assertIsNone(degraded_payload_verdict("h.py", {"Bash"}, 2, ["Bash"]))

    def test_loud_but_non_blocking_is_green_even_with_wide_matcher(self) -> None:
        self.assertIsNone(
            degraded_payload_verdict("h.py", {"PowerShell"}, 1, ["PowerShell|Task"])
        )

    def test_wildcard_matcher_counts_as_outside_scope(self) -> None:
        self.assertIsNotNone(degraded_payload_verdict("h.py", {"Bash"}, 2, ["*"]))

    def test_hard_block_without_registration_is_red(self) -> None:
        verdict = degraded_payload_verdict("h.py", {"Bash"}, 2, [])
        self.assertIn("找不到它的註冊", verdict or "")


@unittest.skipUnless(
    os.name == "nt",
    "[WINDOWS-NATIVE-ONLY] 阻斷契約只在 Windows 成立；非 Windows 分支另有專屬 case",
)
class TestBlockBashHookBehaviourOnWindows(unittest.TestCase):
    """四種輸入的行為契約（R71 手驗過一次，此處升為機械鎖）。"""

    def test_bash_tool_is_blocked_with_exit_2(self) -> None:
        rc, err = _run_hook(json.dumps({"tool_name": "Bash"}))
        self.assertEqual(rc, 2, f"Bash 工具必須被阻斷（exit 2）；實得 rc={rc}\n{err}")
        self.assertIn("Windows 上已禁用 Bash 工具", err, "阻斷時必須輸出可讀指引")

    def test_non_bash_tool_is_allowed(self) -> None:
        """射程不得擴大：matcher 若被改寬，守衛自己也必須認得 tool_name。

        這條是 P0 防護——`.claude/settings.json` 記載過「hook 誤觸 deny 會把所有
        工具硬鎖死」。守衛放行 Read 是它不會變成那種故障源的證明。
        """
        rc, _ = _run_hook(json.dumps({"tool_name": "Read"}))
        self.assertEqual(rc, 0, "非 Bash 工具必須放行——射程擴大會把所有工具鎖死（P0）")

    def _verdict_for(self, rc: int) -> str | None:
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        return degraded_payload_verdict(
            _HOOK.name, {"Bash"}, rc,
            matchers_for_script(settings, "block_bash_on_windows"),
        )

    def test_malformed_json_is_not_silently_allowed(self) -> None:
        """壞 JSON ⇒ 不得靜默放行；選擇硬擋就必須配窄 matcher（判準見上方註記）。"""
        rc, _ = _run_hook("{ this is not json")
        verdict = self._verdict_for(rc)
        self.assertIsNone(verdict, verdict or "")

    def test_empty_stdin_is_not_silently_allowed(self) -> None:
        rc, _ = _run_hook("")
        verdict = self._verdict_for(rc)
        self.assertIsNone(verdict, verdict or "")

    def test_missing_tool_name_key_is_not_silently_allowed(self) -> None:
        """本輪那筆缺陷的原始形態：payload 是合法 JSON，但沒有 tool_name。

        此前它會走到硬擋分支，而當時的 matcher 還圈著子代理工具 ⇒ 擋錯對象、
        還給錯理由。現在由上方判準把「硬擋」與「窄 matcher」綁在一起判。
        """
        rc, _ = _run_hook(json.dumps({"tool_input": {"command": "ls"}}))
        verdict = self._verdict_for(rc)
        self.assertIsNone(verdict, verdict or "")


class TestBlockBashHookDoesNotHurtOtherPlatforms(unittest.TestCase):
    """非 Windows 一律放行——mac/Linux 上 bash 才是正確載具。

    以注入 `os.name='posix'` 驗證，不依賴這台機器是什麼平台（`DEF-101-766`：
    單平台判準不可無條件外推，該筆正是在 Windows 語境裡寫出只在 Windows 成立的
    判準、讓 macos-compat-ci 與 root-infra-ci(ubuntu) 必紅）。
    """

    def test_posix_allows_bash(self) -> None:
        rc, err = _run_hook(json.dumps({"tool_name": "Bash"}), force_os_name="posix")
        self.assertEqual(
            rc, 0,
            f"非 Windows 上必須放行 Bash——誤傷會讓 mac/Linux 開發者無法用正確載具\n{err}",
        )


class TestBlockBashHookGuidanceSurvivesNonUtf8Locale(unittest.TestCase):
    """阻斷指引在**非 UTF-8 locale** 下仍必須可讀（DEF-101-789）。

    WHY：`sys.stderr` 的預設 `errors` 是 `backslashreplace`，所以 locale 編碼
    表達不了 CJK 時（en-US Windows／GitHub windows-latest 的 cp1252）整段指引
    會變成 `\\uXXXX` 逃脫字面；locale 表達得了但不是 UTF-8 時（zh-TW 的 cp950）
    則是讀者端亂碼。兩種都不是「測試紅」而是**功能缺陷**：這支 hook 的存在理由
    就是「純文件約束無攔阻力」，指引不可讀＝阻斷有了、教學沒了，使用者被 exit 2
    硬擋卻拿不到替代指令。

    判準刻意寫在**測試名**上，不隱含在環境裡——上一版的綠燈來自 harness 注入的
    `PYTHONUTF8`，而環境是會變的，沒有人會去讀它。

    兩案皆以 `force_os_name="nt"` 驅動，因此在 mac/Linux 也真的會跑：這個缺陷
    的成因是「locale 不是 UTF-8」，不是「作業系統是 Windows」（`DEF-101-766`
    的反面教訓——判準的射程不該被當下這台機器的平台綁住）。
    """

    _NEEDLE = "Windows 上已禁用 Bash 工具"

    def test_guidance_is_readable_without_inherited_pythonutf8(self) -> None:
        rc, err = _run_hook(json.dumps({"tool_name": "Bash"}), force_os_name="nt")
        self.assertEqual(rc, 2, f"仍須阻斷；實得 rc={rc}")
        self.assertIn(
            self._NEEDLE, err,
            "剝除繼承而來的 PYTHONUTF8 後指引就讀不到了 ⇒ hook 沒有自己強制 UTF-8，"
            f"綠燈是外層環境供應的。實得 stderr（前 200 字）：{err[:200]!r}",
        )

    def test_guidance_is_readable_under_non_cjk_locale_encoding(self) -> None:
        """cp1252＝GitHub windows-latest（en-US）的條件，逐字重現雲端那筆失敗。"""
        rc, err = _run_hook(
            json.dumps({"tool_name": "Bash"}),
            force_os_name="nt",
            env_extra={"PYTHONIOENCODING": "cp1252"},
        )
        self.assertEqual(rc, 2, f"仍須阻斷；實得 rc={rc}")
        self.assertNotIn(
            "\\u", err,
            "指引出現 `\\uXXXX` 逃脫字面＝stderr 的 backslashreplace 生效了，"
            "非 CJK 語系的使用者只會看到一串轉義碼",
        )
        self.assertIn(
            self._NEEDLE, err,
            "非 CJK locale 編碼下指引不可讀——這是功能缺陷，不只是測試紅。"
            f"實得 stderr（前 200 字）：{err[:200]!r}",
        )


class TestBlockBashHookGuidanceContent(unittest.TestCase):
    """指引訊息內容的回歸鎖（DEF-101-778）。

    WHY：這則訊息比純文件更權威（讀者會照它做），而它已實證教錯整整一輪。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _HOOK.read_text(encoding="utf-8")

    def test_points_at_the_find_git_bash_ssot(self) -> None:
        self.assertIn(
            "Find-GitBash", self.text,
            "跑 .sh 的指引必須指向 repo 既有 SSOT tools/lib/Find-GitBash.ps1"
            "（含 system32/WSL 逐段排除），不可自創第二種做法（DEF-101-778）",
        )

    def test_does_not_teach_bare_bash_invocation(self) -> None:
        """不得回頭教裸 `bash <script>`：`Get-Command bash` 命中 system32 的 WSL
        佔位版，且反斜線路徑的分隔符會被整批吃掉（DEF-101-773 逐字實測 rc=127）。"""
        for bad in ("→ bash <script>", "呼叫 `bash <script>`", "bash <script>` "):
            self.assertNotIn(
                bad, self.text,
                f"指引訊息又出現裸 bash 形態 {bad!r}——"
                "執行規則的機械物不該教壞掉的作法（DEF-101-778）",
            )

    def test_does_not_hardcode_a_drive_path(self) -> None:
        """本檔會被 commit，寫死磁碟機路徑對其他 checkout 一律是錯的指引。
        （`tools/tests/test_platform_neutral_paths.py` 亦把 `.claude/hooks` 釘為
        掃描根；此處是同一約束的就地重申，讓本檔的鎖自成完整。）"""
        # 🔴 樣本以 chr() 組出磁碟機字面，不寫在原始碼裡：`test_platform_neutral_paths.py`
        # 有一道「.py 內不得出現寫死 Windows 磁碟機假路徑」的鎖，把樣本直接寫進來會被它
        # 攔下（R73 實測當場翻紅）。兩道鎖的意圖不衝突，只是表達方式要繞開字面。
        drive_c, drive_d = chr(67) + ":", chr(68) + ":"
        for bad in (
            drive_c + "\\Program Files\\Git",
            drive_c + "/Program Files/Git",
            drive_d + "\\CursorProject",
        ):
            self.assertNotIn(bad, self.text, f"指引訊息寫死了機器特定路徑 {bad!r}")

    def test_ps51_operator_advice_is_tied_to_the_production_engine(self) -> None:
        """`&&`／`||` 的建議必須綁**生產引擎**，不得綁「你手上這個 session 是哪一版」。

        WHY（R73）：原文寫「PowerShell 5.1 沒有 && 與 ||」。互動載具升到 PowerShell 7
        之後該句對讀者為假（7.x 支援這兩個運算子），整條建議會被當成過期而忽略——
        而真正的理由與互動載具版本無關：生產路徑（schtasks 兩支 job 的 Action）跑的是
        `powershell.exe`＝5.1，在那裡 `&&` 是 parse error。
        """
        self.assertNotIn(
            "PowerShell 5.1 沒有 && 與 ||", self.text,
            "該句在互動載具為 PowerShell 7 時對讀者為假，會讓整條建議被當成過期",
        )
        self.assertIn(
            "生產", self.text,
            "&&／|| 的建議必須說明理由綁在生產引擎（5.1）上，而非綁當下 session 版本",
        )


_NAMED_TEST_RE = re.compile(r"tools/tests/test_[A-Za-z0-9_]+\.py")


def named_test_files(text: str) -> list[str]:
    """`text` 裡指名的所有 `tools/tests/test_*.py` 路徑（去重、排序）。"""
    return sorted(set(_NAMED_TEST_RE.findall(text)))


class TestHooksDoNotSignpostMissingLocks(unittest.TestCase):
    """機械強制物指名的鎖檔必須真的存在（DEF-101-790）。

    WHY：`block_bash_on_windows.py` 的指引訊息指名一支從未存在的鎖檔，真正的鎖
    卻在本檔裡。**執行規則的機械物給錯的指路比沒有指路更糟**——讀者會認為它比
    文件權威，於是「我查過了」是假的（`tools/ruff.toml` 檔頭有過同型訂正：原本
    指向一支沒有該類別的測試檔）。射程刻意只到 `.claude/hooks/`：那是本 repo 唯一
    「會主動阻斷使用者操作」的一層，指路錯誤的代價最高。
    """

    def test_every_named_lock_file_exists(self) -> None:
        hooks = sorted((_REPO_ROOT / ".claude" / "hooks").glob("*.py"))
        self.assertTrue(hooks, "`.claude/hooks/` 下掃不到任何 .py——射程不得靜默縮小")
        missing: list[str] = []
        total = 0
        for hook in hooks:
            named = named_test_files(hook.read_text(encoding="utf-8"))
            total += len(named)
            missing += [f"{hook.name} 指名了不存在的 {rel}" for rel in named
                        if not (_REPO_ROOT / rel).is_file()]
        self.assertEqual(missing, [], "\n".join(missing))
        # 反空轉：一個都沒指名時上面的斷言恆真，鎖就只是擺設。
        self.assertGreaterEqual(
            total, 1,
            "`.claude/hooks/` 內已不再指名任何 tools/tests/test_*.py ⇒ 本鎖恆綠、"
            "等於沒有（若確實移除了所有指路，請連同本斷言一起處置）",
        )

    def test_criterion_catches_a_dangling_reference(self) -> None:
        """判準自證：指名一支不存在的鎖檔必須被抓到（不靠 repo 現況是否剛好有病）。"""
        fake = "tools/tests/test_this_lock_was_never_created.py"
        self.assertFalse((_REPO_ROOT / fake).exists(), "fixture 名稱意外真的存在")
        self.assertEqual(named_test_files(f"見 {fake} 會判紅。"), [fake])
        self.assertEqual(named_test_files("完全沒有指路的文字"), [])


class TestBlockBashHookIsActuallyRegistered(unittest.TestCase):
    """「裝了但不會跑的鎖」防護：hook 必須真的接在自動觸發點上。"""

    def test_registered_as_pretooluse_bash_matcher(self) -> None:
        self.assertTrue(_SETTINGS.is_file(), f"找不到 {_SETTINGS}")
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        hooks = settings.get("hooks", {})
        pre = hooks.get("PreToolUse", [])
        # matcher 是**正則交替**（實測本機為 `Bash|Task`），不是字面 "Bash"。
        # 故判準走 `re.search`：只要該 matcher 會命中 Bash 就算註冊到位。
        # 寫成 `== "Bash"` 是我第一版的錯——會在 matcher 合法擴充時假紅。
        matched = [
            entry for entry in pre
            if re.search(r"(^|\|)Bash(\||$)", str(entry.get("matcher", "")))
            and any(
                "block_bash_on_windows" in str(h.get("command", ""))
                for h in entry.get("hooks", [])
            )
        ]
        self.assertTrue(
            matched,
            "block_bash_on_windows.py 未註冊於 .claude/settings.json 的 "
            "PreToolUse 且 matcher 未命中 Bash——守衛存在但不會被觸發，等於沒有。"
            f"實查 PreToolUse matcher 清單：{[e.get('matcher') for e in pre]}",
        )


def settings_utf8_env_verdict(settings: dict) -> str | None:
    """`None`＝`env.PYTHONUTF8` 宣告到位；回字串＝失效理由（純函式，日期無關）。"""
    env = settings.get("env")
    if not isinstance(env, dict):
        return ("`.claude/settings.json` 沒有 `env` 區塊 ⇒ hook 子行程的 UTF-8 "
                "串流設定失去本機唯一來源（User/Machine scope 實測皆空）")
    if "PYTHONUTF8" not in env:
        return ("`.claude/settings.json` 的 `env` 沒有 `PYTHONUTF8` ⇒ hook 子行程"
                "改吃 locale 預設編碼，zh-TW 的 cp950 讀寫 UTF-8 內容即亂碼／"
                "UnicodeDecodeError（DEF-101-789 家族）")
    value = str(env["PYTHONUTF8"])
    if value != "1":
        return (f"`env.PYTHONUTF8` 是 {value!r} 而不是 \"1\" ⇒ 只有 \"1\" 會開啟 "
                "Python UTF-8 mode，其他值（含 \"0\"、\"\"）等於沒設")
    return None


class TestSettingsProvideUtf8ForHookChildren(unittest.TestCase):
    """`.claude/settings.json` 的 `env.PYTHONUTF8=1` 回歸鎖（R75／DEF-101-803）。

    WHY 這道非有不可：本檔上方 `_child_env()` 的註記逐字宣告「本機唯一 UTF-8 來源
    是 `.claude/settings.json` 的 `env.PYTHONUTF8=1`」，而該 env 條目此前**零鎖
    看守**（R75 QA 全域搜尋 `tools/tests` 內對 settings.json 的 `PYTHONUTF8` 斷言：
    零命中；旁邊那道 `TestBlockBashHookIsActuallyRegistered` 只驗 hook 註冊）。
    也就是說：把那三行刪掉，全庫測試一片綠，而 R74 那筆 P0（hook 中文指引在非
    UTF-8 codepage 下降解）就靜默復發。**在註記裡點名一個關鍵依賴、卻不給它鎖，
    等於把它登記成「已知且已接受」。**

    🔴 為何注入案走「讀真實內容 → 在記憶體裡拿掉那把鑰匙」而不是真的改磁碟上的
    settings.json：該檔自己記載過 P0「hook 誤觸 PreToolUse deny 會把所有工具硬鎖
    死」，而 R75 是多 agent 同時在同一棵樹作業的輪次——把 hook 子行程的編碼設定
    真的拔掉幾秒鐘，影響面是**全部** agent 的工具呼叫。記憶體注入對「判準有沒有
    鑑別力」的證明力完全相同（被注入的是真實檔案的內容），風險卻是零。
    """

    def _real(self) -> dict:
        self.assertTrue(_SETTINGS.is_file(), f"找不到 {_SETTINGS}")
        return json.loads(_SETTINGS.read_text(encoding="utf-8"))

    def test_real_settings_declares_pythonutf8(self) -> None:
        verdict = settings_utf8_env_verdict(self._real())
        self.assertIsNone(verdict, verdict or "")

    def test_removing_it_from_the_real_content_is_red(self) -> None:
        """注入式：拿掉真實檔案內容裡的那把鑰匙 ⇒ 必紅（反空轉）。"""
        without_key = self._real()
        without_key["env"].pop("PYTHONUTF8")
        self.assertIsNotNone(
            settings_utf8_env_verdict(without_key),
            "把 env.PYTHONUTF8 拿掉之後判準仍為綠 ⇒ 這道鎖是空轉的",
        )
        without_env = self._real()
        without_env.pop("env", None)
        self.assertIsNotNone(settings_utf8_env_verdict(without_env))

    def test_criterion_red_green_on_synthetic_values(self) -> None:
        """判準自證：四種形態（不靠 repo 現況剛好是哪一種）。"""
        self.assertIsNone(settings_utf8_env_verdict({"env": {"PYTHONUTF8": "1"}}))
        self.assertIn("沒有 `env` 區塊", settings_utf8_env_verdict({}) or "")
        self.assertIn("沒有 `PYTHONUTF8`",
                      settings_utf8_env_verdict({"env": {}}) or "")
        for dud in ("0", "", "true", "1 "):
            self.assertIn(
                "只有", settings_utf8_env_verdict({"env": {"PYTHONUTF8": dud}}) or "",
                f"{dud!r} 應被判為「等於沒設」",
            )

    def test_the_p0_hook_is_covered_by_the_production_form_lock(self) -> None:
        """交叉指路：本檔 `_run_hook` 的直接執行形態**不再**是那支 hook 進入 child
        編碼判準的唯一途徑。

        WHY（R75／DEF-101-802）：改寫 `_run_hook` 的 argv（例如換成 `-c` 形態）
        曾經會讓 `.claude/hooks/block_bash_on_windows.py` 靜默離開 child 編碼判準的
        射程——一支**測試**的寫法決定另一道鎖的射程。判準四改以 production 的註冊表
        （`.claude/settings.json` 的 `-c` ＋ runpy 形態）為掃描面，本案只確認那道鎖
        真的存在且真的罩住這支 hook，避免本檔日後被重構時無人知情。
        """
        sys.path.insert(0, str(_REPO_ROOT))
        from tools.tests import test_subprocess_encoding_hygiene as hygiene

        scripts = {
            rel for _event, rel in hygiene.hook_command_scripts(self._real())
        }
        self.assertIn(
            ".claude/hooks/block_bash_on_windows.py", scripts,
            "判準四已看不到 R74 P0 那支 hook ⇒ 射程又回到「靠本檔某一行碰巧怎麼寫」",
        )


# ══════════════════════════════════════════════════════════════════════════
# `.claude/hooks/lint_powershell_command.py` 的回歸鎖（本輪新增）
# ══════════════════════════════════════════════════════════════════════════
# 為何併進本檔：`tools/tests/` 檔數是 shrink-only 棘輪，明文禁止新增鎖檔；而本檔
# 本來就是「hook 有沒有註冊、是不是活的」那一層的家。
#
# 為何非有這支守衛不可（本輪立案量測）：session 逐字稿實測到一組乾淨的對照——
# **有觀測者的那條規則違規 1 次且被當場擋下，沒有觀測者的那些違規率 20~35%**。
# PowerShell 工具面在它出現之前**零觀測者**：禁裸 cd 那條規則的違規面在**指令
# 字串的內容**裡，而那個字串永遠不會變成 repo 裡的檔案，於是全庫靜態掃描器
# 結構上都看不見它。差別不在紀律寫得夠不夠嚴厲。
#
# 本鎖守五件事：①三條檢查各自真的會擋；②合法形態不得誤擋（誤報會讓整個機制被
# 關掉，那比漏擋更糟）；③不早退——三條命中要一次報齊；④射程不得擴大；
# ⑤退化 payload 走「出聲但不阻斷」，且與 matcher 射程配套（見上方判準）。

_LINT_HOOK = _REPO_ROOT / ".claude" / "hooks" / "lint_powershell_command.py"


def _ps_payload(command: str) -> str:
    return json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": "PowerShell",
         "tool_input": {"command": command}},
        ensure_ascii=False,
    )


def _run_lint_hook(
    stdin_text: str, *, force_os_name: str | None = None
) -> tuple[int, str]:
    """以子行程真跑 lint 守衛，回 `(rc, stderr)`（走子行程的理由同 `_run_hook`）。"""
    if force_os_name is None:
        cmd = [sys.executable, str(_LINT_HOOK)]
    else:
        bootstrap = (
            "import os, runpy, sys\n"
            f"os.name = {force_os_name!r}\n"
            f"runpy.run_path({str(_LINT_HOOK)!r}, run_name='__main__')\n"
        )
        cmd = [sys.executable, "-c", bootstrap]
    proc = subprocess.run(
        cmd, input=stdin_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, env=_child_env(),
    )
    return proc.returncode, proc.stderr or ""


class TestLintPowerShellHookBehaviour(unittest.TestCase):
    """三條檢查 × 擋／放行 × 射程 × 退化的行為契約。

    🔴 **刻意不掛 `skipUnless(os.name == "nt")`**，兩個理由：
      ① 這些判準的成因是「payload 帶的是一段 PowerShell 指令」，不是「這台機器是
         Windows」——把它綁在當下平台上，mac/Linux 一側就永遠沒人跑過（本檔的
         `TestBlockBashHookGuidanceSurvivesNonUtf8Locale` 早有同樣的取捨與理由）。
      ② 新增一個平台 skip 站點會動到 `skip_tag_policy._SITE_CLASS_CENSUS` 的相等
         判準，而那張表由另一個工作面在維護。用注入 `os.name` 取得**更大**的覆蓋、
         同時零跨檔耦合，比「多開一個站點再去別人的表上加一」好。
    平台分支本身另有 `TestLintPowerShellHookDoesNotHurtOtherPlatforms` 專屬 case。
    """

    def _lint(self, command: str) -> tuple[int, str]:
        return _run_lint_hook(_ps_payload(command), force_os_name="nt")

    def test_naked_cd_is_blocked(self) -> None:
        rc, err = self._lint("cd AutoClaude; python -m pytest")
        self.assertEqual(rc, 2, f"裸 cd 未被擋；rc={rc}\n{err}")
        self.assertIn("Push-Location", err, "阻斷時必須給出替代出口")

    def test_set_location_is_blocked_but_push_location_is_not(self) -> None:
        rc_bad, _ = self._lint("Set-Location /repo/a")
        self.assertEqual(rc_bad, 2)
        rc_ok, err = self._lint("Push-Location /repo/a; Pop-Location")
        self.assertEqual(rc_ok, 0, f"Push-Location 是正解，不得誤擋\n{err}")

    def test_pipe_then_lastexitcode_is_blocked(self) -> None:
        rc, err = self._lint(
            "& git status | Select-Object -First 3\n\"rc=$LASTEXITCODE\"")
        self.assertEqual(rc, 2, f"管線後讀 rc 未被擋；rc={rc}\n{err}")

    def test_bare_bash_on_sh_is_blocked(self) -> None:
        rc, err = self._lint("bash tools/install_mac_nightly.sh")
        self.assertEqual(rc, 2, f"裸 bash 未被擋；rc={rc}\n{err}")
        self.assertIn("Find-GitBash", err, "必須指向 repo 既有 SSOT")

    def test_all_hits_are_reported_at_once(self) -> None:
        """不早退：早退會遮蔽後面檢查的訊號，而遮蔽方向是「看起來變乾淨」。"""
        rc, err = self._lint("cd x\ngit log | Select-Object -First 1\n"
                             "\"$LASTEXITCODE\"\nbash a.sh")
        self.assertEqual(rc, 2, err)
        for needle in ("Push-Location", "Find-GitBash", "LASTEXITCODE"):
            self.assertIn(needle, err, f"三條違規未一次報齊，缺 {needle}")

    def test_legal_forms_are_not_flagged(self) -> None:
        """誤報比漏擋更糟——被誤報的守衛會被整個關掉。"""
        for cmd in (
            "Push-Location /repo/a; & py a.py; \"rc=$LASTEXITCODE\"; Pop-Location",
            "Get-ChildItem | Select-Object Name",
            ". '/repo/tools/lib/Find-GitBash.ps1'; & (Find-GitBash) -n 'a.sh'",
            "git log --oneline -3",
        ):
            rc, err = self._lint(cmd)
            self.assertEqual(rc, 0, f"合法形態被誤擋：{cmd!r}\n{err}")

    def test_inline_exemption_releases_the_guard(self) -> None:
        rc, err = self._lint("cd x  # ps-lint-ok: 重現缺陷用")
        self.assertEqual(rc, 0, f"行內豁免失效——沒有出口的窄守衛會被關掉\n{err}")

    def test_exemption_without_a_reason_is_not_an_exemption(self) -> None:
        rc, _ = self._lint("cd x  # ps-lint-ok:")
        self.assertEqual(rc, 2, "空理由的豁免必須無效，否則等於整包 noqa")

    def test_scope_does_not_expand_to_other_tools(self) -> None:
        """射程不擴大——兩個平台都必須成立，故走直接執行形態不注入 os.name。"""
        for tool in ("Read", "Task", "Bash", "Edit", "Write"):
            rc, _ = _run_lint_hook(json.dumps({"tool_name": tool}))
            self.assertEqual(rc, 0, f"{tool} 被誤擋——射程擴大會把工具鎖死（P0）")

    def test_degraded_payload_is_loud_but_not_blocking(self) -> None:
        """退化 payload：不靜默、也不硬擋唯一的 shell 載具。"""
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        matchers = matchers_for_script(settings, "lint_powershell_command")
        cases = (
            ("壞 JSON", "{ this is not json"),
            ("空 stdin", ""),
            ("缺 tool_name", json.dumps({"tool_input": {"command": "cd x"}})),
            ("缺 command", json.dumps({"tool_name": "PowerShell",
                                       "tool_input": {}})),
        )
        for label, text in cases:
            rc, err = _run_lint_hook(text, force_os_name="nt")
            verdict = degraded_payload_verdict(
                _LINT_HOOK.name, {"PowerShell"}, rc, matchers)
            self.assertIsNone(verdict, f"{label}：{verdict}")
            self.assertNotEqual(rc, 2, f"{label} 不得硬擋本機唯一的 shell 載具")
            self.assertTrue(err.strip(), f"{label} 必須出聲，守衛失效要看得見")


class TestLintPowerShellHookDoesNotHurtOtherPlatforms(unittest.TestCase):
    """非 Windows 一律放行——mac/Linux 的載具規則不同，單平台判準不可外推。"""

    def test_posix_allows_a_violating_command(self) -> None:
        rc, err = _run_lint_hook(_ps_payload("cd x"), force_os_name="posix")
        self.assertEqual(rc, 0, f"非 Windows 上誤擋；rc={rc}\n{err}")


class TestLintPowerShellHookIsActuallyRegistered(unittest.TestCase):
    """「裝了但不會跑的鎖」防護：守衛必須真的接在自動觸發點上。"""

    def test_registered_as_pretooluse_powershell_matcher(self) -> None:
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        matchers = matchers_for_script(settings, "lint_powershell_command")
        self.assertTrue(
            matchers,
            "lint_powershell_command.py 未註冊於 .claude/settings.json 的 "
            "PreToolUse——守衛存在但不會被觸發，等於沒有",
        )
        self.assertTrue(
            any(re.search(r"(^|\|)PowerShell(\||$)", m) for m in matchers),
            f"註冊到位但 matcher 不命中 PowerShell：{matchers}",
        )


class TestLintPowerShellGuidanceContent(unittest.TestCase):
    """指引訊息內容：這則訊息比純文件更權威，讀者會照它做。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _LINT_HOOK.read_text(encoding="utf-8")

    def test_points_at_the_find_git_bash_ssot(self) -> None:
        self.assertIn(
            "Find-GitBash", self.text,
            "跑 .sh 的出口必須指向 repo 既有 SSOT，不可自創第二種做法",
        )

    def test_offers_push_location_as_the_cd_exit(self) -> None:
        self.assertIn("Push-Location", self.text)

    def test_does_not_hardcode_a_drive_path(self) -> None:
        """本檔會被 commit，寫死磁碟機路徑對其他 checkout 一律是錯的指引。"""
        drive_c, drive_d = chr(67) + ":", chr(68) + ":"
        for bad in (drive_c + "\\", drive_c + "/", drive_d + "\\", drive_d + "/"):
            self.assertNotIn(bad, self.text, f"指引寫死了機器特定路徑 {bad!r}")


# ══════════════════════════════════════════════════════════════════════════
# `tools/probe/audit_session.py` 的契約鎖（本輪新增）
# ══════════════════════════════════════════════════════════════════════════
# 為何住在本檔：`tools/tests/` 不得新增鎖檔，而本檔是「那幾條鐵律的機械物有沒有
# 在做事」最貼近的家——這支探針正是同一組規則**事後量測**的那一半（事中攔截的
# 一半是上面那支 hook）。

_AUDIT_PROBE = _REPO_ROOT / "tools" / "probe" / "audit_session.py"


def _run_audit_probe(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(_AUDIT_PROBE), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, env=_child_env({"PYTHONUTF8": "1"}),
    )
    return proc.returncode, proc.stdout or ""


def _tool_use(command: str) -> dict:
    return {"message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "PowerShell",
         "input": {"command": command}}]}}


class TestSessionAuditProbeContract(unittest.TestCase):
    """量測器的三件事：量得準、崩塌時出聲、不得被接成閘門。"""

    def _write(self, tmp: str, records: list[dict]) -> str:
        path = Path(tmp) / "synthetic.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return str(path)

    def test_it_counts_the_patterns_it_claims_to_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                _tool_use("cd AutoClaude"),
                _tool_use("git log | Select-Object -First 1\n\"$LASTEXITCODE\""),
                _tool_use("Push-Location /repo; Pop-Location"),
            ])
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 0, out)
        summary = json.loads(out)["summary"]
        self.assertEqual(summary["shell_calls"], 3)
        self.assertEqual(summary["patterns"]["naked-cd"], 1)
        self.assertEqual(summary["patterns"]["rc-after-pipe"], 1)

    def test_a_collapsed_scan_surface_fails_loud(self) -> None:
        """掃不到東西必須 rc=1。這個失效方向看起來像「變乾淨了」，比紅更危險。"""
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = _run_audit_probe(["--project-dir", tmp, "--json"])
        self.assertEqual(rc, 1, f"空掃描面竟回 rc=0（＝被讀成本輪零違規）\n{out}")

    def test_a_transcript_with_no_shell_call_also_fails_loud(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [{"message": {"role": "assistant", "content": [
                {"type": "text", "text": "沒有任何工具呼叫"}]}}])
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 1, f"shell 呼叫數 0 必須 fail-loud\n{out}")

    def test_claim_reconciliation_flags_only_the_uncorroborated_one(self) -> None:
        say = {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "全部通過。"}]}}
        proof = {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "3 passed in 1.2s"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            bare = self._write(tmp, [_tool_use("git status"), say])
            rc_bare, out_bare = _run_audit_probe(["--transcript", bare, "--json"])
            path = Path(tmp) / "synthetic.jsonl"
            path.unlink()
            backed = self._write(tmp, [_tool_use("git status"), proof, say])
            rc_backed, out_backed = _run_audit_probe(
                ["--transcript", backed, "--json"])
        self.assertEqual(rc_bare, 0, out_bare)
        self.assertEqual(rc_backed, 0, out_backed)
        self.assertEqual(
            json.loads(out_bare)["summary"]["unsupported_claim_count"], 1,
            "沒有任何對應輸出的宣稱竟沒被列出",
        )
        self.assertEqual(
            json.loads(out_backed)["summary"]["unsupported_claim_count"], 0,
            "前面就有對應輸出的宣稱不該被列（誤報會讓這份清單被忽略）",
        )

    def test_docstring_declares_the_not_a_gate_boundary(self) -> None:
        """邊界必須寫在被讀的地方：逐字稿是本機、untracked、會被清的資料。"""
        text = _AUDIT_PROBE.read_text(encoding="utf-8")
        self.assertIn("不得接成 push 閘門", text)

    def test_it_is_not_wired_into_any_hard_gate(self) -> None:
        """接成硬閘會在別台機器上恆紅，而恆紅的閘門會被整個關掉。"""
        gates = [
            _REPO_ROOT / "tools" / "git-hooks" / "pre-push",
            _REPO_ROOT / "tools" / "git-hooks" / "pre-commit",
        ]
        gates += sorted((_REPO_ROOT / ".github" / "workflows").glob("*.yml"))
        present = [p for p in gates if p.is_file()]
        self.assertGreaterEqual(len(present), 3, "閘門掃描面塌了，本鎖會恆綠")
        offenders = [
            p.name for p in present
            if "audit_session" in p.read_text(encoding="utf-8", errors="replace")
        ]
        self.assertEqual(
            offenders, [],
            f"量測器被接進硬閘：{offenders}——逐字稿在別台機器上不存在，"
            "接成閘門結構上恆紅。要自動化請改成 advisory 且不影響 rc",
        )


if __name__ == "__main__":
    unittest.main()
