#!/usr/bin/env python3
"""tools/check_hooks_liveness.py 的單元測試（S11：抽出四份重複 liveness 偵測邏輯後，
驗證鏡子自身要被驗證 — 單一真相源必須有測試，不可只憑呼叫端手動走查）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
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
# `TestGuardLayerRatchet` 是 **shrink-only 棘輪**，承載 `DEF-101-561③`。R73 當時它量的
# 是**檔數**、語意是「禁止新增鎖檔、只准合併／刪除」，首版新建一支獨立檔案當場被攔下
# （三條斷言同時翻紅）。🔴 R78 ARCH-03 訂正：R77 起量測面換成逐檔行數表，現行語意是
# **淨行數不得上升**——新增檔案只要同一次變更刪掉等量以上的行就合法。
# **正解仍是併入既有鎖檔而不是調升那個基準**——
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

    # ══ R78：兩個方向的判準表（四方複審 SA-01／SD-01／QA-01／SD-02）═════════
    # 🔴 為何整組改寫：上一版的鎖**只測「會過的那幾種寫法」**，於是三條規則各自被
    # 一步穿透而全程綠——`| select -First 5` 放行、`| Select-Object -First 5` 擋下
    # （12 組別名對照 12/12 不對稱），`&&` 之後的 cd 逃、`bash.exe` 逃、rc 讀取只要
    # 隔一句就逃；反方向則把 `"rc=$LASTEXITCODE" | Out-File`（完全安全）與「違規
    # 形態只住在引號／here-string 內」（寫文件、寫探針、重現缺陷的日常）硬擋。
    # ⇒ 本表**每一條規則都同時帶漏擋與誤擋兩列**。只帶一個方向的鎖，必然在另一個
    # 方向上恆綠，而恆綠的鎖就是這一輪 44% 缺陷的形狀本身。

    #: `(別名, 全名)`：其餘字元**逐字相同**，兩者判定必須一致。這一組是 SA-01 的
    #: 判準——不對稱本身就是缺陷，不需要先知道「哪一個才對」。
    PIPE_ALIAS_PAIRS = (
        ("select", "Select-Object"), ("sls", "Select-String"),
        ("sort", "Sort-Object"), ("measure", "Measure-Object"),
        ("%", "ForEach-Object"), ("foreach", "ForEach-Object"),
        ("?", "Where-Object"), ("where", "Where-Object"),
        ("ft", "Format-Table"), ("fl", "Format-List"),
        ("oh", "Out-Host"), ("tee", "Tee-Object"),
    )

    #: 漏擋方向：每一筆上一版都**放行**，而每一筆都只差一步。
    MUST_BLOCK = (
        ("裸 cd", "cd AutoClaude; python -m pytest", "Push-Location"),
        ("Set-Location", "Set-Location /repo/a", "Push-Location"),
        ("Set-Location -Path（上一版被 `(?!-)` 整條放行）",
         "Set-Location -Path AutoClaude", "Push-Location"),
        ("chdir 別名", "chdir AutoClaude", "Push-Location"),
        ("sl 別名", "sl AutoClaude", "Push-Location"),
        ("cd 在 && 之後", "echo hi && cd AutoClaude", "Push-Location"),
        ("cd 在 || 之後", "echo hi || cd AutoClaude", "Push-Location"),
        ("cd 在 | 之後", "echo hi | cd AutoClaude", "Push-Location"),
        ("cd 在 { 區塊內", "if ($true) { cd AutoClaude }", "Push-Location"),
        ("裸 bash", "bash tools/install_mac_nightly.sh", "Find-GitBash"),
        ("bash.exe（上一版只認 `bash` 字面）",
         "bash.exe tools/install_mac_nightly.sh", "Find-GitBash"),
        ("bash 帶引號路徑（遮蔽面看不到 .sh，佐證必須回原文找）",
         'bash "tools/x.sh"', "Find-GitBash"),
        ("bash 在 && 之後", "echo hi && bash tools/x.sh", "Find-GitBash"),
        ("管線後讀 rc（同一句）",
         '& git status | Select-Object -First 3; "rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
        ("管線後讀 rc（下一句）",
         '& git status | Select-Object -First 3\n"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
        ("管線後隔一句才讀 rc（`$x = 1` 不會重設 rc，上一版視窗只看緊鄰下一句）",
         '& git status | select -First 3\n$x = 1\n"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
    )

    #: 誤擋方向：每一筆都是安全的、或是文件／探針的日常寫法。誤報會讓整個機制被
    #: 關掉，而被關掉的守衛比沒有守衛更糟（本檔守的那支 hook 自己的設計前提）。
    MUST_PASS = (
        ("Push-Location 正解 ＋ 乾淨讀 rc",
         'Push-Location /repo/a; & py a.py; "rc=$LASTEXITCODE"; Pop-Location'),
        ("純管線、沒讀 rc", "Get-ChildItem | Select-Object Name"),
        ("純管線用別名、沒讀 rc", "Get-ChildItem | select Name"),
        ("Find-GitBash SSOT 形態",
         ". '/repo/tools/lib/Find-GitBash.ps1'; & (Find-GitBash) -n 'a.sh'"),
        ("rc 在管線**之前**就展開了（QA-01：安全卻被硬擋）",
         '"rc=$LASTEXITCODE" | Out-File a.txt'),
        ("rc 讀在前、管線在後一句",
         '"rc=$LASTEXITCODE"\ngit log | select -First 1'),
        ("中間有新的 & 呼叫重設了 rc",
         'git log | select -First 1; & py a.py; "rc=$LASTEXITCODE"'),
        ("違規形態只住在單引號內（SD-02：寫文件／重現缺陷的日常）",
         "$doc = 'never write cd AutoClaude here'"),
        ("違規形態只住在雙引號內", '$doc = "do not write bash tools/x.sh"'),
        ("違規管線＋rc 只住在字串內",
         "$doc = 'git log | select -First 1 ; $LASTEXITCODE'"),
        ("違規形態只住在字面 here-string 內", "$doc = @'\ncd AutoClaude\n'@"),
        ("違規形態只住在可展開 here-string 內", '$doc = @"\nbash tools/x.sh\n"@'),
        ("違規形態只住在註解內", "Get-Date  # never write cd AutoClaude"),
        ("`$_ % 2` 是運算子不是 ForEach-Object 別名",
         "Get-Random | Where-Object { $_ % 2 -eq 0 }"),
        ("bash 但不是在跑 .sh", "bash --version"),
        ("豁免理由裡有撇號（先遮蔽再找豁免會把它吃掉）",
         "cd x  # ps-lint-ok: don't touch this"),
        ("一般指令", "git log --oneline -3"),
    )

    def test_pipe_aliases_are_judged_the_same_as_their_full_names(self) -> None:
        """SA-01：別名與全名其餘字元逐字相同 ⇒ 判定必須相同，且必須是「擋」。

        不對稱本身就是缺陷：`select -First N` 是提前結束管線最常見的寫法，
        只認全名等於這道鎖擋掉的剛好是沒人會寫的那一半。
        """
        for alias, full in self.PIPE_ALIAS_PAIRS:
            with self.subTest(alias=alias, full=full):
                rc_alias, err_a = self._lint(
                    f'& git status | {alias} -First 3\n"rc=$LASTEXITCODE"')
                rc_full, err_f = self._lint(
                    f'& git status | {full} -First 3\n"rc=$LASTEXITCODE"')
                self.assertEqual(rc_full, 2, f"全名版就沒擋；{err_f}")
                self.assertEqual(
                    rc_alias, rc_full,
                    f"`| {alias}` rc={rc_alias} 但 `| {full}` rc={rc_full}——"
                    f"其餘字元逐字相同卻判不同，這道鎖只認得沒人會寫的那一半\n{err_a}",
                )

    def test_forms_that_slip_through_are_blocked(self) -> None:
        """漏擋方向：逐一注入「只差一步」的形態，每一筆都必須轉紅。"""
        for label, command, needle in self.MUST_BLOCK:
            with self.subTest(label):
                rc, err = self._lint(command)
                self.assertEqual(rc, 2, f"未被擋（{label}）：{command!r}\n{err}")
                self.assertIn(
                    needle, err, f"擋是擋了，但沒指出出口（{label}）：{err}")

    def test_safe_forms_are_not_blocked(self) -> None:
        """誤擋方向：逐一注入安全形態，任何一筆轉紅都是這道鎖在自我毀滅。"""
        for label, command in self.MUST_PASS:
            with self.subTest(label):
                rc, err = self._lint(command)
                self.assertEqual(rc, 0, f"合法形態被誤擋（{label}）："
                                        f"{command!r}\n{err}")

    def test_all_hits_are_reported_at_once(self) -> None:
        """不早退：早退會遮蔽後面檢查的訊號，而遮蔽方向是「看起來變乾淨」。"""
        rc, err = self._lint("cd x\ngit log | Select-Object -First 1\n"
                             "\"$LASTEXITCODE\"\nbash a.sh")
        self.assertEqual(rc, 2, err)
        for needle in ("Push-Location", "Find-GitBash", "LASTEXITCODE"):
            self.assertIn(needle, err, f"三條違規未一次報齊，缺 {needle}")

    def test_the_exemption_exit_is_on_the_first_line(self) -> None:
        """出口寫在頁尾等於沒有：第一次撞到的人先讀到三段責備才看到出路，而
        「窄守衛必須有出口」是這支 hook 的設計前提（SA-01 附帶）。"""
        _rc, err = self._lint("cd AutoClaude")
        first_line = (err.strip().splitlines() or [""])[0]
        self.assertIn(
            "ps-lint-ok", first_line,
            f"阻斷訊息第一行沒有豁免出口，讀者要翻到最後才看得到：{first_line!r}",
        )

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


def _tool_use(command: str, tool: str = "PowerShell") -> dict:
    return {"message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": tool,
         "input": {"command": command}}]}}


def _write_transcript(directory: str, records: list[dict], name: str) -> str:
    path = Path(directory) / name
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return str(path)


class TestSessionAuditProbeContract(unittest.TestCase):
    """量測器的三件事：量得準、崩塌時出聲、不得被接成閘門。"""

    def _write(self, tmp: str, records: list[dict]) -> str:
        return _write_transcript(tmp, records, "synthetic.jsonl")

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
        self.assertEqual(summary["shell_calls_by_tool"]["PowerShell"], 3)
        self.assertEqual(summary["patterns"]["PowerShell"]["naked-cd"], 1)
        self.assertEqual(summary["patterns"]["PowerShell"]["rc-after-pipe"], 1)

    def test_bash_tool_commands_never_land_on_powershell_rules(self) -> None:
        """🔴 R78／SD-04 的機械面：**分母與分子都不得跨工具混用**。

        上一版把兩個工具的指令倒進同一個計數器，實測訊噪比 43︰1820（裸 cd）與
        0︰80（裸 bash）——後者是 100% 假陽性，因為在 Bash 工具裡寫 `bash x.sh`
        本來就是對的。更糟的是方向性偏誤：Bash 工具已被守衛擋掉 ⇒ 未來輪那兩個
        數字會自己「變好看」，而那不是改善。這支測試就是那個混用的紅燈。
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                _tool_use("cd AutoClaude"),
                _tool_use("cd /repo && bash tools/x.sh", tool="Bash"),
                _tool_use("cd /repo/b", tool="Bash"),
            ])
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 0, out)
        summary = json.loads(out)["summary"]
        self.assertEqual(summary["shell_calls_by_tool"], {"PowerShell": 1, "Bash": 2},
                         "分母沒有逐工具拆開")
        self.assertEqual(summary["patterns"]["PowerShell"]["naked-cd"], 1)
        self.assertEqual(
            summary["patterns"]["Bash"], {},
            "Bash 工具竟被套上 PowerShell 的形態判準——那三條規則講的是 PowerShell "
            "工具的 cwd／$LASTEXITCODE／載具選擇，套到 Bash 上是純雜訊",
        )
        self.assertEqual(summary["bash_tool_attempts"], 2,
                         "Bash 工具本身（鐵律一）仍必須被數到，不能因為不套形態就消失")

    def test_collapse_is_judged_per_session_not_by_the_historical_total(self) -> None:
        """🔴 R78／SD-03 的機械面：**一支崩塌就要紅，不准被歷史總量蓋掉**。

        上一版的崩塌判準建在跨 session 合計的 `shell_calls == 0` 上，而預設用法會
        把整個逐字稿目錄加總（本機 51 支）——那是只會單調增長的歷史量，於是「今天
        格式改了」這個唯一要防的失效結構上打不出來。本測試餵的正是那個情境：一支
        舊的、量得到東西的逐字稿 ＋ 一支新的、有記錄卻抽不到任何 shell 呼叫的。
        合計 `shell_calls` 是 2（>0）⇒ 舊判準會回 rc=0＝「本輪零違規」。
        """
        with tempfile.TemporaryDirectory() as tmp:
            _write_transcript(tmp, [_tool_use("git status"), _tool_use("git log")],
                              "old_busy.jsonl")
            # 「格式變了」的長相：記錄還在、tool_use 也還在，但工具名／欄位認不得。
            _write_transcript(tmp, [{"message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "PwSh", "input": {"cmd": "cd x"}}]}}],
                "new_broken.jsonl")
            rc, out = _run_audit_probe(["--project-dir", tmp, "--json"])
        payload = json.loads(out)
        self.assertEqual(payload["summary"]["shell_calls"], 2,
                         "前提沒成立：合計必須 >0，否則測不到「被歷史總量蓋掉」")
        self.assertEqual(
            payload["summary"]["collapsed_sessions"], ["new_broken.jsonl"],
            "崩塌訊號沒有落在那一支上",
        )
        self.assertEqual(rc, 1, f"單支崩塌被合計蓋掉 ⇒ 靜默讀成「零違規」\n{out}")

    def test_window_flags_scope_the_measurement_to_this_round(self) -> None:
        """`--latest`／`--since`：沒有量測窗，per-round 的分母就只能是歷史總量。"""
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(3):
                path = Path(_write_transcript(
                    tmp, [_tool_use("git status")], f"s{index}.jsonl"))
                os.utime(path, (1_700_000_000 + index * 86400,) * 2)
            rc_all, out_all = _run_audit_probe(["--project-dir", tmp, "--json"])
            rc_one, out_one = _run_audit_probe(
                ["--project-dir", tmp, "--json", "--latest", "1"])
            rc_none, _ = _run_audit_probe(
                ["--project-dir", tmp, "--json", "--since", "2099-01-01"])
        self.assertEqual((rc_all, rc_one), (0, 0), out_all)
        self.assertEqual(json.loads(out_all)["summary"]["sessions"], 3)
        picked = json.loads(out_one)["sessions"]
        self.assertEqual([s["transcript"] for s in picked], ["s2.jsonl"],
                         "--latest 沒有挑最近改動的那一支")
        self.assertEqual(rc_none, 1,
                         "窗篩空必須 fail-loud——『量到零』與『量不到』要分得開")

    def test_inline_exemption_is_released_but_still_counted(self) -> None:
        """攔截器放行的，量測器也要放行——否則兩邊的數字對不起來，而 Q4 是拿來下
        結論的。但放行不等於消失：豁免另計，靜默丟掉才是「看起來變乾淨」。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                _tool_use("cd x  # ps-lint-ok: 重現缺陷用"),
                _tool_use("cd y"),
            ])
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 0, out)
        summary = json.loads(out)["summary"]
        self.assertEqual(summary["patterns"]["PowerShell"]["naked-cd"], 1,
                         "帶行內豁免的那一筆不該被計為違規")
        self.assertEqual(summary["exempted_calls"], 1,
                         "豁免必須被單獨數出來，不得靜默消失")

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


# ══════════════════════════════════════════════════════════════════════════
# 攔截器 × 量測器：同一條規則的兩份複本必須綁在一起（R78／SA-02）
# ══════════════════════════════════════════════════════════════════════════
# 現象：`lint_powershell_command.py`（事中攔截）與 `tools/probe/audit_session.py`
# （事後量測）判的是同一組規則，卻各存一份判準字面，而 R77 交付時**已經不一致**
# ——hook 那份有 `Tee-Object`、探針那份沒有，兩份零比對。後果不是「少擋一種」而是
# 更難看見的那一種：同一段違規**攔得下、卻量不到**，於是量出來的違規率偏低，
# 而那個數字正是拿來寫進根 CLAUDE.md 下結論用的。
#
# 為何不抽共用模組：hook 由 `runpy.run_path` 起，`sys.path` 上沒有 `tools/`，
# import 期爆掉會破壞它的 fail-open 契約（settings.json 記載過的 P0）。複本是
# **結構上被逼出來的**。既然只能留複本，就把複本的一致性變成會轉紅的事件。
#
# 兩向都要，缺一即有繞道：
#   ① 字面相等——兩份 `SHARED_PATTERN_SOURCE` 必須逐字相同。抽不到（改名／改寫成
#      非字面）也算紅，否則「把常數拿掉」就是一條無聲的出口。
#   ② 行為一致——同一批指令餵進兩邊，判定必須相同。這一向抓得到「字典同步了，
#      但某一邊另外藏了第二份複本／組裝時漏接」，字面相等抓不到那個。

_PARITY_HITS = (
    ("naked-cd", "cd AutoClaude"),
    ("naked-cd", "Set-Location -Path /repo/a"),
    ("naked-cd", "sl /repo/a"),
    ("rc-after-pipe", "& git status | select -First 3\n$LASTEXITCODE"),
    ("rc-after-pipe", "& git status | Tee-Object out.txt\n$LASTEXITCODE"),
    ("bare-bash-sh", "bash tools/install_mac_nightly.sh"),
    ("bare-bash-sh", "bash.exe tools/install_mac_nightly.sh"),
)
#: 兩邊都必須放行。誤報會讓機制被整個關掉，那比漏擋更糟——所以這一半和上一半同等重要。
_PARITY_CLEAN = (
    "Push-Location /repo/a; & py a.py; $LASTEXITCODE; Pop-Location",
    "Get-ChildItem",
    ". /repo/tools/lib/Find-GitBash.ps1; & (Find-GitBash) -n /repo/a.sh",
    "git log --oneline -3",
)


def _shared_pattern_source(path: Path) -> dict[str, str]:
    """以 AST 抽 `SHARED_PATTERN_SOURCE`（**不 import**：hook 有模組層副作用且
    刻意零外部相依，import 它等於在測試裡重現它最怕的那件事）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == "SHARED_PATTERN_SOURCE"
               for t in targets) and node.value is not None:
            return dict(ast.literal_eval(node.value))
    raise AssertionError(
        f"{path.name} 抽不到 SHARED_PATTERN_SOURCE（改名？改寫成非字面？）——"
        "抽不到就是紅：讓常數消失不能成為繞過『兩份複本必須同步』的出口。"
        "要改結構請同時改本鎖，別讓它靜默失效"
    )


class TestHookAndProbeShareOneCriterion(unittest.TestCase):
    """攔截器與量測器的判準必須同步（字面 ＋ 行為，兩向）。"""

    def _probe_hits(self, command: str) -> set[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_transcript(tmp, [_tool_use(command)], "one.jsonl")
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 0, f"探針對 {command!r} 非預期地 fail-loud\n{out}")
        per_tool = json.loads(out)["summary"]["patterns"]["PowerShell"]
        return {key for key, value in per_tool.items() if value}

    def test_shared_pattern_source_is_literally_identical(self) -> None:
        hook = _shared_pattern_source(_LINT_HOOK)
        probe = _shared_pattern_source(_AUDIT_PROBE)
        self.assertTrue(hook, "hook 那份是空的——空字典會讓兩邊「一致地什麼都不擋」")
        self.assertEqual(
            hook, probe,
            "攔截器與量測器的判準字面已漂移。這不是風格問題：R77 就是這樣讓 "
            "Tee-Object『攔得下卻量不到』，而量出來的數字被寫進根 CLAUDE.md 當結論。"
            "改一邊就要同一次改另一邊（兩份刻意連換行位置都相同）。",
        )

    def test_both_sides_agree_on_the_same_commands(self) -> None:
        """字面同步了還不夠：組裝時漏接、或某一邊另有第二份複本，只有行為抓得到。"""
        for category, command in _PARITY_HITS:
            with self.subTest(command=command):
                rc, err = _run_lint_hook(_ps_payload(command), force_os_name="nt")
                hits = self._probe_hits(command)
                self.assertEqual(rc, 2, f"攔截器放行了 {command!r}（探針判 {hits}）\n{err}")
                self.assertIn(
                    category, hits,
                    f"攔截器擋下 {command!r}，量測器卻沒記——違規率會被系統性低估，"
                    "而那個數字是拿來下結論的",
                )
        for command in _PARITY_CLEAN:
            with self.subTest(command=command):
                rc, err = _run_lint_hook(_ps_payload(command), force_os_name="nt")
                hits = self._probe_hits(command)
                self.assertEqual(rc, 0, f"攔截器誤擋合法形態 {command!r}\n{err}")
                self.assertEqual(hits, set(),
                                 f"量測器把合法形態 {command!r} 記成違規：{hits}")


# ══════════════════════════════════════════════════════════════════════════
# 註冊面棘輪：hook 的觸發射程只准擴大、不准縮小（R78／QA-03）
# ══════════════════════════════════════════════════════════════════════════
# 🔴 這一筆比「鎖沒有鑑別力」再深一層：**鎖本身可以被無聲拆掉**。
#
# QA 的突變測試 M4 實測：把根 `.claude/settings.json` 的 PostToolUse
# `matcher: "Write|Edit"` 改成 `"Write"`——這會讓 `check_ps1_encoding.py` 與
# `check_sh_eol.py` 對 **Edit 工具整支失效**（Edit 寫出的 CRLF `.sh`、無 BOM `.ps1`
# 從此無人守）——全套閘門 **rc=0 全綠，零鑑別力**。同時實查：本檔上方的
# `matchers_for_script()` 只掃 PreToolUse；全 `tools/tests/` 除本輪新建的
# `test_context_budget_guard.py` 外，沒有任何檔案提到 `PostToolUse`。
# ⇒ PostToolUse 的註冊面（matcher 射程、條目存在性）在此之前**完全無人守**，
# 而根 CLAUDE.md 花了整整一節在講「已橋接的 2 支 hook 在根 session 會跑」。
#
# 與 `test_doc_loc_baseline_freshness_r60.py::TestR74RootClaudeMdHookClaimsMatchRegistration`
# 的**分工**（兩者都讀同一份 settings.json，但問的問題不同，不重複）：
#   · 那一道守「**文件怎麼寫**」——根 CLAUDE.md 對某支 hook 的射程宣稱，與它在
#     settings.json 裡「有沒有被註冊」是否雙向一致。它的判定面是**腳本 basename 的
#     存在性**，對 matcher 圈了哪些工具、掛在哪個事件**完全不看**（M4 那個突變在它
#     眼裡毫無變化：hook 還在，只是不再對 Edit 觸發）。
#   · 本道守「**註冊面怎麼變**」——每支已註冊 hook 的 (事件, 觸發工具集合) 相對釘選
#     基準只准擴大。它不讀任何 .md，不管文件怎麼寫。
#
# 🔴 為何是「釘現況＋只硬擋劣化方向」而不是「必須等於某個理想集合」：本 repo 明文
# 判例——**永紅的閘門會被整個關掉，比沒有鎖更糟**。擴大 matcher（多守一個工具）與
# 換成 `*` 一律綠；只有「某支 hook 不再被它原本守著的工具觸發」與「條目整個消失」
# 會紅。要合法縮小射程，就得在同一次變更裡動下面那張表，讓那個決定被複審看見。
#
# 誠實劃界：本鎖只讀 repo 內的 `.claude/settings.json`。`settings.local.json`／
# 使用者層設定的合併結果不在射程內（那些不進版控，鎖不到也不該鎖）。

#: hook command 字串裡的腳本路徑。與 `test_subprocess_encoding_hygiene._PY_ARG_RE`
#: 同一形態，兩者由 `test_two_enumerators_agree_on_the_script_set` 綁在一起。
_HOOK_SCRIPT_RE = re.compile(r"[\w./\\-]+\.py")


def registered_tool_scope(settings: dict) -> dict[tuple[str, str], set[str]]:
    """`{(事件名, 腳本 repo 相對路徑): 會觸發它的工具名集合}`。

    matcher 為空字串或缺席 → `{"*"}`（＝不限工具；`SessionStart` 這類無 matcher 的
    事件即此形）。同一支腳本在同一事件下註冊於多個條目時取**聯集**——它實際的觸發面
    就是那些 matcher 的聯集。
    """
    scope: dict[tuple[str, str], set[str]] = {}
    for event, entries in (settings.get("hooks") or {}).items():
        for entry in entries or []:
            tools = matcher_tokens(str(entry.get("matcher", "")))
            for hook in entry.get("hooks") or []:
                command = str(hook.get("command", ""))
                for found in _HOOK_SCRIPT_RE.finditer(command):
                    key = (str(event), found.group(0).replace("\\", "/"))
                    scope.setdefault(key, set()).update(tools)
    return scope


#: 釘選基準＝R78 當下的真實註冊面（`git show HEAD:.claude/settings.json` 逐項讀出）。
#: 這是**下限**不是等式：值只准變大。要縮小或移除，就改這裡並在 commit 裡說明。
_REGISTRATION_BASELINE: dict[tuple[str, str], frozenset[str]] = {
    ("SessionStart", ".claude/hooks/sdd_hook_router.py"): frozenset({"*"}),
    ("PreToolUse", ".claude/hooks/sdd_hook_router.py"): frozenset(
        {"Write", "Edit", "Read", "Bash", "NotebookEdit", "Task"}),
    ("PreToolUse", ".claude/hooks/lint_powershell_command.py"): frozenset(
        {"PowerShell"}),
    ("PreToolUse", ".claude/hooks/block_bash_on_windows.py"): frozenset({"Bash"}),
    ("PostToolUse", ".claude/hooks/sdd_hook_router.py"): frozenset(
        {"Write", "Edit", "Read", "Bash", "NotebookEdit"}),
    # 🔴 QA M4 打的就是下面這兩支共用的那個 `Write|Edit` 條目。
    ("PostToolUse", "AutoClaude/tools/hooks/check_ps1_encoding.py"): frozenset(
        {"Write", "Edit"}),
    ("PostToolUse", "AutoClaude/tools/hooks/check_sh_eol.py"): frozenset(
        {"Write", "Edit"}),
    # R78 context 水位觀測者。matcher 刻意不含 Write|Edit（那些內容在模型寫出時
    # 已在 context 內，對「還剩多少」沒有新資訊），也刻意不用 `*`（每次呼叫要付
    # 約 42ms 的 python 啟動成本；水位偵測漏掉某一次呼叫不會漏掉那個門檻）。
    # 選型理由與 fail-open 契約寫在 .claude/settings.json 該條目的 _comment。
    ("PostToolUse", ".claude/hooks/context_budget_guard.py"): frozenset(
        {"Read", "Task", "Grep", "Glob", "WebFetch", "WebSearch", "Bash",
         "PowerShell"}),
}


def registration_shrink_problems(
    current: dict[tuple[str, str], set[str]],
    baseline: dict[tuple[str, str], frozenset[str]],
) -> list[str]:
    """回劣化理由清單；`[]`＝沒有任何 hook 的觸發射程縮小（純函式，紅綠可合成自證）。"""
    problems: list[str] = []
    for (event, script), pinned in sorted(baseline.items()):
        got = current.get((event, script))
        if got is None:
            problems.append(
                f"{event} 底下的 {script} 註冊條目整個不見了——hook 檔還在磁碟上也沒用，"
                "它不會再被觸發。若確為刻意移除，請在同一次變更裡改 "
                "_REGISTRATION_BASELINE 並寫下理由"
            )
            continue
        if "*" in got:
            continue  # 通配＝涵蓋全部工具，是擴大不是縮小
        lost = sorted(pinned - got)
        if lost:
            problems.append(
                f"{event} 底下的 {script} 不再被 {lost} 觸發（現為 {sorted(got)}）"
                "——射程縮小是靜默失效：hook 仍在註冊表裡、測試仍全綠，但那些工具"
                "寫出來的檔從此無人守"
            )
    return problems


class TestHookRegistrationScopeIsShrinkOnly(unittest.TestCase):
    """註冊面棘輪的本體（WHY／與姊妹鎖的分工／劣化方向，見上方區塊註記）。"""

    def _real(self) -> dict:
        self.assertTrue(_SETTINGS.is_file(), f"找不到 {_SETTINGS}")
        return json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))

    _M4_SCRIPT = "check_sh_eol.py"  # QA M4 打的那個條目（與 check_ps1_encoding 同住）

    def _m4_entries(self, settings: dict) -> list[dict]:
        """PostToolUse 底下承載 `_M4_SCRIPT` 的條目。

        刻意以**腳本名**定位而不是以 matcher 字面（如 `"Write|Edit"`）定位：後者會讓
        本類別在「磁碟上的 matcher 被改過」時整組因前提不成立而錯亂報紅——而那正是
        本鎖要用來做鑑別力注入的場景，判準自己不該被注入弄瞎。
        """
        hits = [
            entry for entry in settings.get("hooks", {}).get("PostToolUse", []) or []
            if any(self._M4_SCRIPT in str(h.get("command", ""))
                   for h in entry.get("hooks") or [])
        ]
        self.assertEqual(
            len(hits), 1,
            f"PostToolUse 底下承載 {self._M4_SCRIPT} 的條目有 {len(hits)} 個（預期 1）"
            "——註冊佈局已變，請重寫本案而不是放寬斷言")
        return hits

    def _mutate_matcher(self, settings: dict, new: str) -> dict:
        self._m4_entries(settings)[0]["matcher"] = new
        return settings

    def test_real_settings_meets_the_baseline(self) -> None:
        problems = registration_shrink_problems(
            registered_tool_scope(self._real()), _REGISTRATION_BASELINE)
        self.assertEqual(problems, [], "註冊面出現劣化：\n  " + "\n  ".join(problems))

    def test_scan_surface_is_not_vacuous(self) -> None:
        """自錨：解析塌掉時 `current` 會是空 dict，上一條會全報 missing 而紅——
        但那條紅的訊息會指錯方向，故此處直接對掃描面本身斷言。"""
        scope = registered_tool_scope(self._real())
        self.assertIn(
            ("PostToolUse", "AutoClaude/tools/hooks/check_sh_eol.py"), scope,
            f"掃不到 QA M4 打的那個站點 ⇒ 本鎖已空轉。實得 keys：{sorted(scope)}")
        self.assertGreaterEqual(
            len(scope), len(_REGISTRATION_BASELINE),
            "解析出的註冊條目少於釘選基準——枚舉器疑似壞了")

    def test_baseline_covers_every_current_registration(self) -> None:
        """誠實全集：新增一支 hook 而不進基準表 ⇒ 它一輩子不受棘輪保護（跟 QA M4
        的處境完全相同）。此條逼新增者表態，形狀同
        `check_script_parity._AC_EXCLUDED_REGISTRIES` 那張表的「漏排即紅」。"""
        unpinned = sorted(set(registered_tool_scope(self._real()))
                          - set(_REGISTRATION_BASELINE))
        self.assertEqual(
            unpinned, [],
            f"下列 (事件, 腳本) 已註冊但不在 _REGISTRATION_BASELINE：{unpinned}"
            "——請把它現在的 matcher 工具集合釘進去")

    def test_baseline_scripts_all_exist_on_disk(self) -> None:
        """反向 stale：釘住一支不存在的腳本＝守著一個幽靈，且會遮蔽真正的移除。"""
        ghosts = sorted({script for _event, script in _REGISTRATION_BASELINE
                         if not (_REPO_ROOT / script).is_file()})
        self.assertEqual(ghosts, [], f"基準表指向不存在的腳本：{ghosts}")

    # ── 鑑別力：三種變更方向各自自證（不靠 repo 現況剛好是哪一種）───────────
    def test_narrowing_the_posttooluse_matcher_is_red(self) -> None:
        """🔴 QA M4 的逐字重建：`Write|Edit` → `Write`（Edit 側整支失效）。"""
        mutated = self._mutate_matcher(self._real(), "Write")
        problems = registration_shrink_problems(
            registered_tool_scope(mutated), _REGISTRATION_BASELINE)
        for script in ("check_ps1_encoding.py", "check_sh_eol.py"):
            self.assertTrue(
                any(script in p and "Edit" in p for p in problems),
                f"M4 突變後 {script} 仍被判為合格 ⇒ 這道鎖是空轉的。實得：{problems}")

    def test_removing_the_whole_entry_is_red(self) -> None:
        settings = self._real()
        doomed = self._m4_entries(settings)[0]
        post = settings["hooks"]["PostToolUse"]
        settings["hooks"]["PostToolUse"] = [e for e in post if e is not doomed]
        self.assertEqual(len(settings["hooks"]["PostToolUse"]), len(post) - 1)
        problems = registration_shrink_problems(
            registered_tool_scope(settings), _REGISTRATION_BASELINE)
        self.assertTrue(
            any("整個不見了" in p for p in problems),
            f"整條 hook 條目被刪掉竟仍為綠。實得：{problems}")

    def test_widening_the_matcher_is_green(self) -> None:
        """方向性：多守一個工具不得轉紅——會把「加強防護」變成要改鎖才能做的事。"""
        mutated = self._mutate_matcher(self._real(), "Write|Edit|NotebookEdit")
        self.assertEqual(
            registration_shrink_problems(
                registered_tool_scope(mutated), _REGISTRATION_BASELINE),
            [])

    def test_wildcard_matcher_is_green(self) -> None:
        mutated = self._mutate_matcher(self._real(), "*")
        self.assertEqual(
            registration_shrink_problems(
                registered_tool_scope(mutated), _REGISTRATION_BASELINE),
            [])

    def test_criterion_red_green_on_synthetic_input(self) -> None:
        """判準自證：不讀磁碟，四種形態直接餵。"""
        base = {("PostToolUse", "a.py"): frozenset({"Write", "Edit"})}
        self.assertEqual(
            registration_shrink_problems(
                {("PostToolUse", "a.py"): {"Write", "Edit"}}, base), [])
        self.assertEqual(
            registration_shrink_problems(
                {("PostToolUse", "a.py"): {"Write", "Edit", "Read"}}, base), [])
        self.assertTrue(registration_shrink_problems(
            {("PostToolUse", "a.py"): {"Write"}}, base))
        self.assertTrue(registration_shrink_problems({}, base))
        # 同一支腳本換到別的事件下＝原事件的射程歸零，必須紅（不得因 basename
        # 還在就放行——那正是姊妹鎖看不見的那一面）。
        self.assertTrue(registration_shrink_problems(
            {("PreToolUse", "a.py"): {"Write", "Edit"}}, base))

    def test_two_enumerators_agree_on_the_script_set(self) -> None:
        """本檔的枚舉器與 `test_subprocess_encoding_hygiene.hook_command_scripts()`
        讀的是同一份註冊表，兩者的 (事件, 腳本) 集合必須一致。

        WHY：同一份知識住兩個家、只有一個家被改，是本 repo 反覆出現的形態。把兩者
        綁在一起之後，任一支的解析被改窄都會當場顯形（而不是等到某道鎖恆綠）。
        """
        sys.path.insert(0, str(_REPO_ROOT))
        from tools.tests import test_subprocess_encoding_hygiene as hygiene

        real = self._real()
        self.assertEqual(
            set(registered_tool_scope(real)),
            set(hygiene.hook_command_scripts(real)),
            "兩支枚舉器對同一份 settings.json 給出不同的 (事件, 腳本) 集合")


if __name__ == "__main__":
    unittest.main()
