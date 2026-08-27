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
import shutil
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
    """`settings` 的 PreToolUse 內，**實際會跑到** `needle` 的所有 matcher。

    🔴 R80：此前的判準是 `needle in command`，而 exec form（治 Windows 閃窗的形態）
    把腳本路徑從 `command` 搬進了 `args` ⇒ 那個寫法轉換後一律回空，於是
    `degraded_payload_verdict()` 會改走「找不到它的註冊」那條路。解析改問唯一真相源
    `tools/lib/hook_wiring.py`，兩種形態都認得。
    """
    return [
        str(entry.get("matcher", ""))
        for entry in _hook_wiring().entries_launching(settings, needle)
    ]


def _hook_wiring():
    """延後 import 唯一真相源（同本檔其他延後 import 的理由：不進 import 期路徑）。"""
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import hook_wiring  # noqa: PLC0415

    return hook_wiring


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
        # 🔴 R80：`"block_bash_on_windows" in h["command"]` 這種寫法在 exec form 下
        # 一律回空（腳本路徑搬進 args 了）。改問唯一真相源，兩種形態都認得。
        launching = _hook_wiring().entries_launching(settings, "block_bash_on_windows")
        matched = [
            entry for entry in launching
            if re.search(r"(^|\|)Bash(\||$)", str(entry.get("matcher", "")))
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


#: 無人看管訊號的字面。**刻意在測試裡再寫一次而不 import 被測物**：這條的兩端是
#: 「planner 注入什麼」與「hook 讀什麼」，鎖若從任一端 import 常數，兩端一起改名時
#: 它會跟著改而全程綠——那正是這道鎖要抓的失效。planner 那一端由
#: `tools/tests/test_context_budget_guard.py` 對同一個字面自證。
_UNATTENDED_ENV = "AUTOSDD_UNATTENDED"


def _run_lint_hook(
    stdin_text: str, *, force_os_name: str | None = None,
    env_extra: dict[str, str] | None = None,
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
    env = _child_env()
    # 🔴 顯式剝除，理由同 `_child_env` 對 `PYTHONUTF8` 的既有註記：「沒有訊號時放行」
    # 那幾條若讓外層環境供應綠燈，這道鎖量的就不是被測物的性質。
    env.pop(_UNATTENDED_ENV, None)
    env.update(env_extra or {})
    proc = subprocess.run(
        cmd, input=stdin_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, env=env,
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
        # ── R79：`_RC_RESET_RE` 的三個「提到 ≠ 執行」漏擋（端到端重現過真紅讀成綠）──
        ("管線後夾一句 2>&1（重導向的 `&` 不是呼叫運算子，上一版當成 rc 已重設）",
         '& git status | select -First 3\nGet-Content log.txt 2>&1\n'
         '"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
        ("管線後夾 Get-Command x.exe（只是查路徑，什麼都沒執行）",
         '& git status | select -First 3\nGet-Command python.exe\n'
         '"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
        ("管線後夾 Test-Path …/x.exe（`.exe` 在參數位置＝資料不是指令）",
         '& git status | select -First 3\nTest-Path /repo/x/cmd.exe\n'
         '"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
        # ── R79：不帶參數的 cd 家族（上一版尾巴硬性要求一個參數 ⇒ 整條放行）──
        ("裸 cd 不帶參數（切到 $HOME，之後每個相對路徑一次全錯）", "cd",
         "Push-Location"),
        ("裸 Set-Location 不帶參數", "Set-Location", "Push-Location"),
        ("裸 cd 後面還有別的指令", "cd; Get-ChildItem", "Push-Location"),
        ("裸 chdir 在換行前", "chdir\nGet-Date", "Push-Location"),
        # ── R79：豁免標記被「引述」在字串裡，不該關掉檢查 ──
        ("字串裡引述豁免標記，句尾那個 cd 仍是貨真價實的違規",
         "Write-Output 'never write # ps-lint-ok: like this'; cd AutoClaude",
         "Push-Location"),
        # ── R79：偏向擋的**代價**就地記錄（不是漏，是刻意）──
        # 裸原生指令（`git`）確實會重設 rc，但本判準只認呼叫運算子與「語句開頭是
        # 執行檔」，認不得它 ⇒ 這一條會被擋。全史 913 條真實指令實測只有 1 條落在
        # 這一格（0.11%），出口是行內豁免（阻斷訊息第一行就寫著）。
        # 🔴 若日後補上「裸原生指令也算重設」的判準，本列會轉紅——那是正確行為：
        # 取捨變了就必須有人重新決定，不能靜默改掉。
        ("偏向擋的代價：裸原生指令 git 其實會重設 rc，但本判準認不得（出口＝行內豁免）",
         'git status | Measure-Object -Line\ngit commit -m x 2>&1\n'
         '"rc=$LASTEXITCODE"',
         "LASTEXITCODE"),
    )

    #: `(夾在管線與 rc 讀取中間的那一句, 它是否真的重設了 rc)`——其餘字元逐字相同。
    #: 🔴 R79：這條軸上 R78 版**每一側只有一個樣本，而且都是教科書代表**（不重設側是
    #: `$x = 1`、重設側是一個乾淨的 `& py a.py`）。中間那片灰色地帶——**看起來像**在
    #: 呼叫、其實什麼都沒執行——一個樣本都沒有，於是一條真的會放行「真紅讀成綠」的
    #: 規則，在 75 支測試全綠的情況下交付了。體例照 `PIPE_ALIAS_PAIRS`：只差一個 token
    #: 的配對，不對稱本身就判紅，不必先知道哪一邊才對。
    RC_RESET_PAIRS = (
        ("$x = 1", False),
        ("Get-Content log.txt 2>&1", False),
        ("Get-Command python.exe", False),
        ("Test-Path /repo/x/cmd.exe", False),
        ("Write-Output 'py.exe'", False),          # `.exe` 只住在字串裡
        ("& py a.py", True),                        # 呼叫運算子
        ("/repo/v/python.exe a.py", True),          # 語句開頭就是執行檔
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
        ("中間那一句的開頭就是一支執行檔（真的跑了東西 ⇒ rc 已重設）",
         'git log | select -First 1; /repo/v/python.exe a.py; "rc=$LASTEXITCODE"'),
        ("`.exe` 只住在字串裡，不構成「已重設」也不構成違規",
         "$note = 'python.exe'"),
        ("行內豁免出現在真註解裡（理由含撇號），仍必須放行",
         "cd x  # ps-lint-ok: don't touch this either"),
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

    def test_only_a_real_invocation_clears_the_rc_contamination(self) -> None:
        """R79：污染的**解除**條件——「提到一支 exe」與「執行一支 exe」必須分得開。

        七條變體其餘字元逐字相同，只差夾在管線與 rc 讀取之間的那一句。這一格就是
        pwsh 7.6.4 真機量到的東西：`2>&1`／`Get-Command x.exe`／`Test-Path …x.exe`
        三種語句**一個都沒有**重設 `$LASTEXITCODE`，而上一版三種全當成已重設。
        """
        for middle, resets in self.RC_RESET_PAIRS:
            with self.subTest(middle=middle, resets=resets):
                command = ('& git status | select -First 3\n'
                           f'{middle}\n"rc=$LASTEXITCODE"')
                rc, err = self._lint(command)
                if resets:
                    self.assertEqual(
                        rc, 0,
                        f"`{middle}` 真的重設了 rc，之後讀 rc 是安全的卻被誤擋——"
                        f"誤擋會讓整個機制被關掉\n{err}")
                else:
                    self.assertEqual(
                        rc, 2,
                        f"`{middle}` 一行都沒執行、rc 仍是管線留下的髒值，卻被當成"
                        f"「已重設」而放行——放行的正是這條規則唯一要防的"
                        f"「真紅被讀成綠」\n{err}")

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


# ══════════════════════════════════════════════════════════════════════════
# R79 Auto Pilot：無人看管那一跑的 commit／push 阻斷
# ══════════════════════════════════════════════════════════════════════════
# 為何併進本檔：`tools/tests/` 檔數是 shrink-only 棘輪（禁新增鎖檔），而這條規則
# 住在本檔已經在守的那支 hook 裡。
#
# 立案：掌舵者 R79 逐字裁決「現在開，但禁止 commit/push」——開的是 planner 的
# `--allow-resume` 預設。條件不是建議，所以它必須有牙；而「那一跑要遵守任務書第 4 節」
# 是散文，本 repo 對散文的攔阻力已有三次實證（都是 0）。
#
# 本鎖守四件事，**每一件都帶反向**（只帶一個方向的鎖必然在另一個方向恆綠）：
#   ① 有訊號 × 會動 git 歷史 → 必須 exit 2；
#   ② **沒有訊號** × 同一條指令 → 必須 exit 0（互動 session 零附帶面。這一條若壞掉，
#      掌舵者自己的 commit 會被鎖死，而那會讓整個機制當場被關掉）；
#   ③ 有訊號 × 無關指令（`git status`／`git log`）→ 必須 exit 0；
#   ④ 行內豁免對本條**無效**（無人看管的那個回合可以自己寫豁免註解）。
class TestUnattendedCommitPushBlock(unittest.TestCase):
    """R79 Auto Pilot 的授權邊界（WHY 與四件事見上方區塊註記）。"""

    def _lint(self, command: str, *, unattended: bool) -> tuple[int, str]:
        return _run_lint_hook(
            _ps_payload(command), force_os_name="nt",
            env_extra={_UNATTENDED_ENV: "1"} if unattended else None)

    #: 有訊號時**必須擋**。每一筆都是那一跑真的可能寫出來的形態。
    MUST_BLOCK = (
        ("git commit", 'git commit -m "wip"'),
        ("git push", "git push origin main"),
        ("git -C <path> commit（不在 cwd 上動手）", 'git -C /repo commit -m x'),
        ("git -c 覆寫設定後 push", "git -c user.name=bot push"),
        ("git.exe（字面換一個就繞過的老形態）", "git.exe push"),
        ("帶路徑前綴的 git", "/tools/git/bin/git.exe commit -m x"),
        ("呼叫運算子", "& git push"),
        ("第二段指令（`;` 之後）", "Get-Date; git commit -m x"),
        ("第二段指令（換行之後）", "Get-Date\ngit push"),
        ("第二段指令（`&&` 之後）", "Get-Date && git push"),
        ("gh pr create（把改動送出去的另一條路）", "gh pr create --fill"),
        ("gh release create", "gh release create v1 --notes x"),
        ("行內豁免對授權邊界無效（那一跑自己寫得出這行註解）",
         "git push  # ps-lint-ok: 我覺得可以"),
    )

    #: 有訊號時**仍必須放行**。那一跑要做的事正是「把狀態寫下來然後停」，
    #: 擋到它讀 git、寫任務書、留稽核痕跡，等於逼它什麼都不留就死掉。
    MUST_PASS_UNATTENDED = (
        ("git status（讀，不是寫）", "git status --short"),
        ("git log", "git log --oneline -3"),
        ("git diff", "git diff --stat"),
        ("git rev-parse", "git rev-parse HEAD"),
        ("`push` 只是 grep 的樣式，不是子指令", "git log | Select-String push"),
        ("`commit` 出現在參數的值裡（`=` 後面沒有空白）", "git log --grep=commit"),
        ("在字串裡提到 commit（寫任務書／留痕的日常）",
         "$note = 'blocked: do not git commit here'"),
        ("在註解裡提到 push", "Get-Date  # never git push from here"),
        ("字尾巧合不算指令（`legit` 不是 `git`）", "legit commit -m x"),
        ("完全無關的指令", "Get-ChildItem | Select-Object Name"),
    )

    def test_the_signal_blocks_git_history_writes(self) -> None:
        for label, command in self.MUST_BLOCK:
            with self.subTest(label):
                rc, err = self._lint(command, unattended=True)
                self.assertEqual(rc, 2, f"未擋（{label}）：{command!r}\n{err}")
                self.assertIn(
                    _UNATTENDED_ENV, err,
                    f"擋了但沒說是哪個訊號造成的（{label}）——讀者無從得知怎麼關：{err}")

    def test_without_the_signal_the_same_commands_are_untouched(self) -> None:
        """🔴 反向：互動 session 必須零附帶面。這一條壞掉＝掌舵者的 commit 被鎖死。"""
        for label, command in self.MUST_BLOCK:
            with self.subTest(label):
                rc, err = self._lint(command, unattended=False)
                self.assertEqual(
                    rc, 0, f"沒有無人看管訊號卻被擋（{label}）：{command!r}\n{err}")

    def test_the_signal_does_not_block_unrelated_commands(self) -> None:
        for label, command in self.MUST_PASS_UNATTENDED:
            with self.subTest(label):
                rc, err = self._lint(command, unattended=True)
                self.assertEqual(rc, 0, f"誤擋（{label}）：{command!r}\n{err}")

    def test_degraded_payload_keeps_the_existing_contract(self) -> None:
        """退化 payload 的既有契約不因本條而改變（出聲、但不硬擋唯一的 shell 載具）。"""
        for label, text in (("壞 JSON", "{ nope"), ("空 stdin", "")):
            with self.subTest(label):
                rc, err = _run_lint_hook(text, force_os_name="nt",
                                         env_extra={_UNATTENDED_ENV: "1"})
                self.assertEqual(rc, 1, f"{label}：退化契約被本條改掉了\n{err}")
                self.assertTrue(err.strip(), f"{label} 必須出聲")

    def test_non_windows_keeps_the_platform_contract(self) -> None:
        """非 Windows 一律 exit 0——**但那不再代表 mac 上沒有這道鎖**（R85／P12 訂正）。

        本 docstring 的前一版寫「mac/Linux 開 Auto Pilot 時這道鎖必須另外補」，那句話
        自 R85 起已為假：mac 側補在 `.claude/hooks/block_destructive_git.py`
        （matcher `Bash|PowerShell`、平台中立），判準與訊息兩支共用
        `tools/lib/unattended_authz.py` 這一個家，回歸鎖是該檔的姊妹鎖
        `test_block_destructive_git_r83.TestUnattendedAuthzHasTeethOnEveryPlatform`。
        本條仍然成立、也仍然該守：它守的是**本支 hook 的射程不外溢**。
        """
        rc, err = _run_lint_hook(_ps_payload("git push"), force_os_name="posix",
                                 env_extra={_UNATTENDED_ENV: "1"})
        self.assertEqual(rc, 0, f"非 Windows 上誤擋；rc={rc}\n{err}")

    def test_the_message_names_the_boundary_not_just_the_rule(self) -> None:
        """訊息要讓那一跑知道**該做什麼**，不是只知道被擋。"""
        _rc, err = self._lint("git push", unattended=True)
        self.assertIn("ps-lint-ok", err, "必須明說行內豁免對本條無效")
        self.assertIn("工作樹", err, "必須告訴它替代動作（改動留著讓人回來收）")


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

    def test_the_two_loop_columns_are_separated(self) -> None:
        """🔴 R79：慣用管線投影與「現寫的控制流」必須分欄。

        上一版把兩者算進同一欄，實測那一欄三分之二的命中是 `| ForEach-Object { … }`
        這種一行投影——與註解宣稱要抓的「沒有任何測試看過的現寫控制流」不是同一種
        風險。混在同一個分子裡，那個百分比既不能解讀、也不能拿來判斷有沒有變好。
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                _tool_use("Get-ChildItem | ForEach-Object { $_.Name }"),
                _tool_use("Get-ChildItem | % { $_.Name }"),
                _tool_use("foreach ($f in $files) { Write-Output $f }"),
            ])
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 0, out)
        per_tool = json.loads(out)["summary"]["patterns"]["PowerShell"]
        self.assertEqual(
            per_tool["pipeline-foreach"], 2,
            f"慣用管線投影沒有被獨立記成一欄：{per_tool}（`| %` 的別名形態也要算）")
        self.assertEqual(
            per_tool["inline-loop-statement"], 1,
            f"真正的現寫控制流被稀釋掉了：{per_tool}")

    def test_an_unrelated_decoration_is_not_evidence_for_a_claim(self) -> None:
        """🔴 R79：佐證字樣曾包含 `✅` 與裸 `OK`／`ok`。

        純裝飾字元與英文常用詞零鑑別力，於是「前面任何一個 tool_result 出現過它們」
        就讓之後的宣稱自動獲得佐證 ⇒ 這個觀測者在本輪窗上判出率是 0%，而那個 0
        讀起來就是「這一輪沒有失實宣稱」——正是探針自己 docstring 警告的
        「看起來變乾淨」方向，比紅更危險，因為沒有人會去追一個 0。
        """
        deco = {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "✅ 完成 OK 了"}]}}
        real = {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "3 passed in 1.2s"}]}}
        say = {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "全部通過。"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            decorated = self._write(tmp, [_tool_use("git status"), deco, say])
            rc_deco, out_deco = _run_audit_probe(
                ["--transcript", decorated, "--json"])
            Path(decorated).unlink()
            backed = self._write(tmp, [_tool_use("git status"), real, say])
            rc_real, out_real = _run_audit_probe(["--transcript", backed, "--json"])
        self.assertEqual((rc_deco, rc_real), (0, 0), out_deco + out_real)
        self.assertEqual(
            json.loads(out_deco)["summary"]["unsupported_claim_count"], 1,
            "一個裝飾字元就替宣稱背書了——這條件近乎恆真，觀測者等於恆報乾淨")
        self.assertEqual(
            json.loads(out_real)["summary"]["unsupported_claim_count"], 0,
            "真的有執行輸出（`3 passed`）的宣稱不該被列，否則清單會被整份忽略")

    def test_the_claim_denominator_travels_with_the_numerator(self) -> None:
        """只印分子時，「CLAIM_RE 自己失效」與「真的零違規」印出來一模一樣。"""
        proof = {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "3 passed in 1.2s"}]}}
        backed = {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "全部通過。"}]}}
        bare = {"message": {"role": "assistant", "content": [
            {"type": "text", "text": "已驗證。"}]}}
        # 三筆與執行無關的 tool_result 把那次 `3 passed` 推出窗外——這正是「佐證必須
        # 是**這句話附近**那一次執行」的意思；沒有它，第二句宣稱會沿用前一次的證據。
        noise = {"message": {"role": "user", "content": [
            {"type": "tool_result", "content": "檔案第一行\n檔案第二行"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [_tool_use("git status"), proof, backed,
                                     _tool_use("git log"), noise, noise, noise,
                                     bare])
            rc, out = _run_audit_probe(["--transcript", path, "--json"])
        self.assertEqual(rc, 0, out)
        summary = json.loads(out)["summary"]
        self.assertEqual(summary["claim_sentences_total"], 2,
                         f"分母（命中 CLAIM_RE 的句子數）沒有被記：{summary}")
        self.assertEqual(summary["unsupported_claim_count"], 1, out)
        self.assertEqual(summary["claim_window"], 3,
                         "窗大小必須跟著數字走——換一個窗就是另一個百分比")

    def test_the_report_names_every_transcript_in_the_window(self) -> None:
        """🔴 R79：窗的定義本身是資料。

        `--latest N` 由 mtime 排序決定，而每一支同期跑的 agent 都在同一個目錄開一支新
        逐字稿 ⇒ **量測這個動作本身會改變下一次的量測值**（實測：同一條指令一小時內
        三組數字、rc 由 0 翻 1）。窗不印出來，帳本記的數字就沒有人能回查。
        """
        with tempfile.TemporaryDirectory() as tmp:
            _write_transcript(tmp, [_tool_use("git status")], "alpha.jsonl")
            _write_transcript(tmp, [_tool_use("git log")], "beta.jsonl")
            rc, out = _run_audit_probe(["--project-dir", tmp, "--json"])
        self.assertEqual(rc, 0, out)
        manifest = json.loads(out)["summary"]["window_manifest"]
        self.assertEqual(
            sorted(row["transcript"] for row in manifest),
            ["alpha.jsonl", "beta.jsonl"],
            f"量測窗清單沒有把納入的逐字稿逐支列出：{manifest}")
        for row in manifest:
            self.assertIn("mtime", row)
            self.assertEqual(row["powershell_calls"], 1,
                             f"清單沒有帶每一支自己的 PowerShell 呼叫數：{row}")

    def test_exclude_takes_a_transcript_out_of_the_window(self) -> None:
        """`--exclude` 必須在 `--latest` **之前**套用，否則被剔掉的那幾支仍會先把
        別人擠出窗外——那正是本輪實測到「真正在做事的那支被擠出去」的機制。"""
        with tempfile.TemporaryDirectory() as tmp:
            for index, name in enumerate(("keep.jsonl", "agent_a.jsonl",
                                          "agent_b.jsonl")):
                path = Path(_write_transcript(
                    tmp, [_tool_use("git status")], name))
                os.utime(path, (1_700_000_000 + index * 86400,) * 2)
            rc, out = _run_audit_probe(
                ["--project-dir", tmp, "--json", "--latest", "1",
                 "--exclude", "agent_"])
        self.assertEqual(rc, 0, out)
        picked = [s["transcript"] for s in json.loads(out)["sessions"]]
        self.assertEqual(
            picked, ["keep.jsonl"],
            "被 --exclude 點名的逐字稿仍然把該留下的那一支擠出了窗外（順序錯了）")

    def test_parity_mode_puts_both_ends_on_the_same_commands(self) -> None:
        """R78 宣稱兩端「判定分歧 0 例」，而守那句話的鎖餵的是十來條手寫短指令。

        `--parity` 讓那個宣稱變成可重跑的量測：語料是量測窗裡**真正出現過**的指令。
        這裡用的樣本正是上一版兩端會分歧的那一族（管線與 rc 隔 ≥1 句）。
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [
                _tool_use('& git status | select -First 3\n$x = 1\n'
                          '"rc=$LASTEXITCODE"'),
                _tool_use('& git status | select -First 3\n$x = 1\n$y = 2\n'
                          '"rc=$LASTEXITCODE"'),
                _tool_use('git log | select -First 1; & py a.py; '
                          '"rc=$LASTEXITCODE"'),
            ])
            rc, out = _run_audit_probe(["--transcript", path, "--json", "--parity"])
        self.assertEqual(rc, 0, f"兩端在真實形態上判定分歧\n{out}")
        payload = json.loads(out)
        self.assertEqual(payload["parity"], [], "分歧清單非空")
        self.assertEqual(payload["summary"]["parity_commands"], 3,
                         "對拍語料塌了——空語料會讓分歧數恆為 0")

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
# 失誤歸因分群器的契約鎖（R79 新增）
# ══════════════════════════════════════════════════════════════════════════
# 為何住在本檔：`tools/tests/` 不得新增鎖檔（DEF-101-561③），而這支分群器是同一組
# 觀測者的第三件——攔截（hook）／量測（probe）／歸因（本項）。
#
# 🔴 它要守的那件事很窄但很關鍵：根 CLAUDE.md 逐字要求「每輪重跑一次，分群腳本與桶的
# 判準要具名可重跑」，而 R77 那次分群**沒有留下任何產物**（來源清單不在 repo 內、
# 全庫零分群腳本）⇒ 那條要求結構上永遠滿足不了，於是那組百分比變成不可稽核的常數，
# 正是 R71 的 n=8 模型被當現行結論用五輪的同一個形態。

_ATTRIBUTION = _REPO_ROOT / "tools" / "probe" / "misstep_attribution.py"


class TestMisstepAttributionContract(unittest.TestCase):
    """歸因分群器：語料抓得到、桶判得準、判準性質自己說出來。"""

    def _run(self, args: list[str]) -> tuple[int, str]:
        proc = subprocess.run(
            [sys.executable, str(_ATTRIBUTION), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300, env=_child_env({"PYTHONUTF8": "1"}))
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def test_the_ledger_corpus_is_actually_extracted(self) -> None:
        """語料塌了必須 fail-loud：`n=0` 讀起來像「這一輪沒有失誤」。

        這是本檔反覆記載的「看起來變乾淨」方向——比紅更危險，因為沒有人會去追一個 0。
        帳本改格式／來源清單過期都會落在這裡。
        """
        rc, out = self._run(["--source", "ledger", "--json"])
        self.assertEqual(rc, 0, out)
        payload = json.loads(out)
        self.assertGreater(
            payload["n"], 100,
            "缺陷帳本抽不到列了（列的格式變了？來源清單過期？）——"
            f"抽到 {payload['n']} 筆；分群器的分母塌掉時，每一個桶都會是 0")

    def test_buckets_are_named_and_each_item_says_why_it_landed_there(self) -> None:
        rc, out = self._run(["--source", "ledger", "--json"])
        self.assertEqual(rc, 0, out)
        payload = json.loads(out)
        self.assertEqual(
            set(payload["counts"]),
            {"LOCKBLIND", "CARRIER", "CLAIM-FIRST", "BADPIPE", "OTHER"},
            "桶名變了——桶是判準本身，改名等於重新定義量測，歷史數字不再可比")
        classified = [i for i in payload["items"] if i["bucket"] != "OTHER"]
        self.assertTrue(classified, "沒有任何一筆被歸類 ⇒ 關鍵詞表失效")
        for item in classified[:50]:
            self.assertTrue(
                item["matched"],
                f"這一筆進了 {item['bucket']} 卻說不出是哪個關鍵詞讓它進去："
                f"{item['origin']}——說不出理由的歸屬無法逐筆覆核")

    def test_ties_and_misses_go_to_other_instead_of_a_preferred_bucket(self) -> None:
        """平手與零命中一律 OTHER。把 OTHER 藏起來會讓其餘桶虛胖，而虛胖的方向
        正好是「我們已經懂了」。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        try:
            import misstep_attribution as attribution
        finally:
            sys.path.pop(0)
        self.assertEqual(attribution.classify("今天天氣很好")[0], "OTHER")
        self.assertEqual(
            attribution.classify("這道鎖沒有鑑別力、射程也不對，恆綠")[0],
            "LOCKBLIND")
        self.assertEqual(
            attribution.classify("裸 bash 走到 WSL，載具選錯了")[0], "CARRIER")
        # 一邊一個關鍵詞＝平手 ⇒ 不准偏袒任何一桶
        self.assertEqual(attribution.classify("恆綠 而且 裸 bash")[0], "OTHER")

    def test_it_declares_its_own_heuristic_nature_in_the_output(self) -> None:
        """判準性質必須由**腳本自己印**，不能只寫在散文裡：引用數字的人看到的是
        輸出，不是原始碼註解。量級穩健、小數不穩健——這句話要跟著數字走。"""
        rc, out = self._run(["--source", "ledger"])
        self.assertEqual(rc, 0, out)
        for needle in ("關鍵詞啟發式", "量級穩健", "不得"):
            self.assertIn(needle, out, f"輸出沒有自陳判準性質，缺 {needle!r}")


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
    ("naked-cd", "cd"),  # R79：不帶參數，上一版兩邊都放行
    ("rc-after-pipe", "& git status | select -First 3\n$LASTEXITCODE"),
    ("rc-after-pipe", "& git status | Tee-Object out.txt\n$LASTEXITCODE"),
    ("bare-bash-sh", "bash tools/install_mac_nightly.sh"),
    ("bare-bash-sh", "bash.exe tools/install_mac_nightly.sh"),
)
#: 🔴 R79：這是 `_PARITY_HITS` 少掉的那一維。上面每一條 rc 樣本的管線與 rc 讀取之間
#: 都只隔**一個**換行，而兩端當時的視窗長度根本不同——攔截端的污染會一路延續到某句
#: 真的重設 rc 為止，量測端那條扁平正則只跨得過一個換行。於是「管線與 rc 之間隔 ≥1 行」
#: 的多行指令**整類**在量測端隱形，而那是本 repo 最常寫的形狀。手寫短樣本結構上看不到
#: 這件事，鎖因此永遠是綠的——這正是「鎖在、但沒有鑑別力」長在防它的機制上。
#: 對策是把樣本**參數化**：每一條 rc 樣本自動長出間隔 0~4 句的變體，兩端的視窗差在
#: 任何一格上都會轉紅。填充句刻意選不會重設 rc 的（`$x = 1`），否則測的就不是視窗了。
_PARITY_GAP_FILLER = "$x = 1"
_PARITY_GAP_RANGE = range(5)
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

    def test_both_sides_agree_across_statement_gaps(self) -> None:
        """R79：同一條 rc 樣本 × 間隔 0~4 句，兩端在**每一格**都必須判一樣。

        這一維是上一版鎖缺的那個：字面同步、行為在 gap 0 也一致，但兩邊的**視窗**
        長度不同 ⇒ gap≥1 的多行指令在量測端整類看不見。低報的方向看起來像「變乾淨」，
        而那個數字是拿來寫進根 CLAUDE.md 下結論的（沿革＝R89 收尾證據檔）。
        """
        for category, command in _PARITY_HITS:
            if category != "rc-after-pipe" or "\n" not in command:
                continue
            head, _, tail = command.partition("\n")
            for gap in _PARITY_GAP_RANGE:
                variant = "\n".join([head] + [_PARITY_GAP_FILLER] * gap + [tail])
                with self.subTest(gap=gap, command=command):
                    rc, err = _run_lint_hook(
                        _ps_payload(variant), force_os_name="nt")
                    hits = self._probe_hits(variant)
                    self.assertEqual(
                        rc, 2,
                        f"攔截器對間隔 {gap} 句的變體放行了：{variant!r}\n{err}")
                    self.assertIn(
                        category, hits,
                        f"間隔 {gap} 句時攔截器擋得下、量測器卻記不到 "
                        f"{variant!r}（量到 {hits}）——兩端的視窗長度不同，"
                        "違規率會被系統性低估",
                    )


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

    🔴 R80：解析面由「`command` 字串」改問唯一真相源 `tools/lib/hook_wiring.py`。
    exec form（治 Windows 閃窗的形態）把腳本路徑搬進 `args`，只讀 `command` 的舊寫法
    轉換後會回**空 dict** ⇒ `registration_shrink_problems()` 會把**每一支** hook 都
    報成「註冊條目整個不見了」。射程判準必須跟著形態走，否則它守的是字串不是事實。
    """
    wiring = _hook_wiring()
    scope: dict[tuple[str, str], set[str]] = {}
    for event, entries in (settings.get("hooks") or {}).items():
        for entry in entries or []:
            tools = matcher_tokens(str(entry.get("matcher", "")))
            for hook in entry.get("hooks") or []:
                for rel in wiring.hook_entry_targets(hook):
                    scope.setdefault((str(event), rel), set()).update(tools)
    return scope


#: 釘選基準＝R78 當下的真實註冊面（`git show HEAD:.claude/settings.json` 逐項讀出）。
#: 這是**下限**不是等式：值只准變大。要縮小或移除，就改這裡並在 commit 裡說明。
_REGISTRATION_BASELINE: dict[tuple[str, str], frozenset[str]] = {
    ("SessionStart", ".claude/hooks/sdd_hook_router.py"): frozenset({"*"}),
    # 🔴 R79 續航哨兵的**接電點**。為何非 SessionStart 不可：額度耗盡是 API 層失敗，
    # 不是工具呼叫失敗 ⇒ 它在 hook 體系裡**沒有任何觸發點**，「撞到才反應」結構上
    # 不可能成立，只能在還跑得動指令的最早時刻預防性武裝。本輪之前的續航協定是
    # 手動武裝的，而那一刻沒有人會去武裝它——同輪連撞兩次額度、協定零作用即為實證。
    # 契約（逐項見 .claude/settings.json 該條目的 _comment）：只在 Windows 動作／
    # `AUTOSDD_SENTINEL_OFF` 可單獨關掉（刻意不與 `AUTOSDD_CONTEXT_GUARD_OFF` 共用）／
    # 恆 exit 0 不出聲／detached 子行程故不阻塞開場／缺 planner 即 fail-open。
    ("SessionStart", ".claude/hooks/context_budget_guard.py"): frozenset({"*"}),
    ("PreToolUse", ".claude/hooks/sdd_hook_router.py"): frozenset(
        {"Write", "Edit", "Read", "Bash", "NotebookEdit", "Task"}),
    ("PreToolUse", ".claude/hooks/lint_powershell_command.py"): frozenset(
        {"PowerShell"}),
    ("PreToolUse", ".claude/hooks/block_bash_on_windows.py"): frozenset({"Bash"}),
    # 🔴 R83 新增：毀滅性 git 指令阻斷器的**註冊面回填**（由並行的另一個包新增條目，
    # `.claude/settings.json` 不在那個包的檔案所有權內時本表就會落後——同上方 R79 那格的
    # 既有紀律，收輪者負責讓帳對得上）。
    # 立案是本輪的真實事故：一個 subagent 在**六包並行共用的工作樹**上跑
    # `git stash -q -u --keep-index`，瞬間清空 16 個修改檔 + 4 個未追蹤檔（含其他包正在
    # 寫的檔），靠 `stash pop` 還原、未偵測到資料遺失——**但那是運氣不是設計**。
    # 任務書當時已寫「不要 git add / commit / push」⇒ **禁令沒涵蓋到的那個動詞就是被踩的
    # 那個**，而 R71 已實證純文件約束對「當下的模型」零攔阻力。
    # matcher 取 `{Bash, PowerShell}` 的依據是**逐字稿實查**而非推測：本機 60 份逐字稿、
    # 7,189 次 tool_use 中 Bash 4,083 次、PowerShell 0 次（Windows 側是另一個 project dir，
    # 且該平台依鐵律一禁用 Bash ⇒ 一律走 PowerShell）。兩者相加＝腳本自己的 OWN_TOOLS；
    # 🔴 R95 起 matcher＝OWN_TOOLS ∪ GOV_TOOLS（治理檔禁寫；下限同步升格，射程縮回即紅）。
    # 該守衛對退化 payload 走 rc=1（出聲不阻斷）故不受「rc==2 必須配窄 matcher」那條約束，
    # 但仍取窄 matcher；且腳本內**刻意沒有 `os.name` 閘**——照抄
    # `block_bash_on_windows.py` 的平台閘等於「在事故現場（macOS）把它關掉」。
    ("PreToolUse", ".claude/hooks/block_destructive_git.py"): frozenset(
        {"Bash", "PowerShell", "Write", "Edit", "NotebookEdit"}),
    ("PostToolUse", ".claude/hooks/sdd_hook_router.py"): frozenset(
        {"Write", "Edit", "Read", "Bash", "NotebookEdit"}),
    # 🔴 QA M4 打的就是下面這兩支共用的那個 `Write|Edit` 條目。
    ("PostToolUse", "AutoClaude/tools/hooks/check_ps1_encoding.py"): frozenset(
        {"Write", "Edit"}),
    ("PostToolUse", "AutoClaude/tools/hooks/check_sh_eol.py"): frozenset(
        {"Write", "Edit"}),
    # 🔴 R79 由**並行的另一個包**新增的 PreToolUse 條目（`.claude/settings.json` 不在
    # 本包的檔案所有權內，本包只負責讓帳對得上——同 `_SITE_CLASS_CENSUS` 的既有紀律）。
    # 語意是「動手**之前**先看水位」，圈的是三個會一次吃掉大量 context 的工具。
    # 收輪者請依當場實測重驗這一格：若那個包最後把條目撤掉，本列必須跟著撤，否則
    # 棘輪會對著一個不存在的註冊喊紅。
    ("PreToolUse", ".claude/hooks/context_budget_guard.py"): frozenset(
        {"Task", "WebFetch", "WebSearch"}),
    # R78 context 水位觀測者。matcher 刻意不含 Write|Edit（那些內容在模型寫出時
    # 已在 context 內，對「還剩多少」沒有新資訊），也刻意不用 `*`（每次呼叫要付
    # 約 42ms 的 python 啟動成本；水位偵測漏掉某一次呼叫不會漏掉那個門檻）。
    # 選型理由與 fail-open 契約寫在 .claude/settings.json 該條目的 _comment。
    ("PostToolUse", ".claude/hooks/context_budget_guard.py"): frozenset(
        {"Read", "Task", "Grep", "Glob", "WebFetch", "WebSearch", "Bash",
         "PowerShell"}),
    # 🔴 `DEF-200-103` 落地：「宣稱先於查證」最大失誤桶的**輸出面**觀測者（此前該桶零攔截器）。
    # Stop 事件無 matcher（它不是工具呼叫）⇒ 射程恆為 `*`，與兩支 SessionStart 同形。
    # 為何非 Stop 不可：該桶發生的平面是「宣稱本身」，永不變成 repo 檔案 ⇒ 靜態掃描器
    # 結構上看不見；而 Stop payload 是唯一同時給得到宣稱（`last_assistant_message`）與
    # 證據面（`transcript_path`）的地方（本批以拋棄式 dump hook 實測兩欄皆在）。
    # 契約（逐項見 `.claude/settings.json` 該條目的 _comment）：一律 exit 0**只出聲、
    # 永不阻斷**（不用 Stop 的 `decision:block`）／逃生口 `AUTOSDD_CLAIM_GUARD_OFF`
    # 刻意不與其他守衛共用／`AUTOSDD_UNATTENDED` 有設時抑制詞表縮到只認方括號標記／
    # payload 退化與任何例外 fail-open（截斷證據面偏向假紅，故超 byte cap 一律放行）。
    ("Stop", ".claude/hooks/check_claim_provenance.py"): frozenset({"*"}),
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
        # R80：定位面由 `command` 字串改問唯一真相源——exec form 把腳本路徑搬進
        # `args`，只讀 command 會讓本類別的**前提**（找得到那個條目）先垮掉，
        # 而它垮掉時的訊息會指向「註冊佈局已變」這個錯誤方向。
        hits = _hook_wiring().entries_launching(
            settings, self._M4_SCRIPT, event="PostToolUse")
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


# ══════════════════════════════════════════════════════════════════════════
# R80：hook 條目形態（exec form）與載具存在性的回歸鎖
# ══════════════════════════════════════════════════════════════════════════
# 病：Windows 上 shell form 的 hook 經 Git Bash 的 `bash.exe -c` 起，而 `bash.exe`
# 是 console 子系統程式 ⇒ **每觸發一次 hook 就閃一個 console 視窗**（實測：一個量測
# 視窗內 39 支 bash.exe、其中 22 支自帶 conhost＝22 次閃窗）。exec form（條目帶
# `args`）不經 shell、直接 spawn，指到 GUI 子系統的 `pythonw.exe` 即零視窗。
#
# 🔴 這道鎖真正在防的**不是**「有人把形態改回去」，是**修好與全毀的表徵相同**：
# exec form 的載具解析不到時 CC 只記一行 ERROR、工具照跑（**fail-open**），螢幕上
# 看起來就是「終於不閃窗了」。所以本節每一條判準的方向都是「少一半也要有人喊」，
# 而不是「壞了會紅」。
_LAUNCHER = _REPO_ROOT / ".claude" / "hooks" / "_hook_launcher.py"


def _same_path(a: str | os.PathLike[str], b: str | os.PathLike[str]) -> bool:
    """兩個路徑是否指向**同一個檔案系統實體**（比 inode，不比字面字串）。

    🔴 **為什麼不能比字面**（R83 於真 Mac 首跑抓到，判準本身是跨平台缺陷）：
    「我把 cwd 設成 X」與「子行程回報 cwd 是 X」之間隔著一層核心正規化，**兩個平台
    各有一種讓字面不等、語意相同的機制**，而且兩種都出現在測試最常用的暫存目錄上：

      · **macOS**：`/var` 是 `/private/var` 的 symlink。`tempfile.mkdtemp()` 回
        `/var/folders/.../T/xxx`（未解析），而 POSIX `getcwd(3)` 依規格回**已解析**
        的絕對路徑 ⇒ 子行程必然回 `/private/var/folders/.../T/xxx`。實測本機
        `os.path.samefile()` 為 True、字串比較為 False。
      · **Windows**：`%TEMP%` 在多數機器上是 `C:\\Users\\<user>\\AppData\\Local\\Temp`，
        使用者名稱超過 8 字元時 API 之間會混用 8.3 短檔名（`RUNNE~1`）；再加上
        NTFS 大小寫不敏感（`C:\\` vs `c:\\`）與 GitHub runner 的目錄 junction，
        同樣是「語意相同、字面不等」。

    ⇒ 本判準要問的事情從頭到尾都是**「是不是同一個目錄」**，那件事的平台中立量法
    只有一種：問檔案系統，不要問字串。`os.path.samefile()` 兩個平台都走
    `os.stat()` 的 `(st_dev, st_ino)`——POSIX 是 device+inode；**Windows 上 CPython
    的 `os.stat()` 走 `GetFileInformationByHandle`**，`st_ino` 是檔案索引、`st_dev`
    是磁碟區序號，兩者都是**開檔後由核心回報的實體身分**，所以 8.3 短檔名／大小寫／
    junction 三種變形全部自動被吃掉，不需要為 Windows 另寫一欄。

    🔴 **刻意不用 `Path.resolve()` 當正規化**：它在 Windows 上是「字串正規化 + 查詢」
    的混合體，行為隨版本與路徑是否存在而變（不存在的路徑會 fallback 成純字串處理）；
    而 `samefile` 的語意只有一種、且在路徑不存在時是**明確失敗**而不是悄悄退化——
    後者正是本 repo 反覆判過的「判準悄悄變成恆綠」形態。

    OSError（任一側不存在／權限不足）一律回 `False`＝**fail-closed**：測試寧可紅在
    「兩個路徑對不起來」，也不要因為量測失敗而放行。

    🔴 **`samefile` 唯一會 fail-OPEN 的那個縫，以及誰在守它**（獨立複驗 R83 補記）：
    上面「比 inode」的前提是**檔案系統真的給得出檔案 ID**。MSDN 對
    `BY_HANDLE_FILE_INFORMATION` 逐字載明「不支援 file ID 的檔案系統一律回 0」——
    FAT／部分 SMB 網路磁碟即屬此類 ⇒ 那種機器上 `st_ino` 兩邊同為 0、`st_dev` 又是
    同一個磁碟區序號，`samefile` 會把**兩個不同的檔案判成同一個**。方向是放行，
    不是誤擋，所以它不會自己叫出來（本輪只有 darwin，這一段是 MSDN 文件語意，
    **不是實測值**）。
    ⇒ 守它的是 `TestSamePathIsNotVacuous.test_two_different_directories_are_not_the_same`：
    那一格在**本機真正的暫存檔案系統**上建兩個貨真價實不同的目錄再問一次，
    檔案 ID 退化時它就地轉紅。**所以那一格不是可有可無的形式主義，刪掉它等於把
    Windows 側唯一的 fail-open 偵測器一起刪掉**（本 repo 反覆踩的「鎖還在、但沒人
    知道它在守什麼，於是下一輪被當成廢話刪掉」）。
    """
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _path_mismatch(reported: str, expected: str | os.PathLike[str]) -> str:
    """`_same_path()` 為 False 時的診斷字串：字面 ＋ realpath 兩層都印出來。

    只印字面會讓「symlink／短檔名造成的假紅」與「真的切錯目錄」長得一模一樣，
    下一個人得再花一輪才分得出是哪一種。
    """
    return (f"實得 {reported!r}（realpath={os.path.realpath(reported)!r}）"
            f" != 期望 {str(expected)!r}（realpath={os.path.realpath(expected)!r}）")


def _load_real_settings() -> dict:
    return json.loads(_SETTINGS.read_text(encoding="utf-8"))


def carrier_venv_dirs(carriers: set[str], placeholder: str) -> set[str]:
    """這些載具字串各自落在 repo 底下哪個**頂層目錄**（不含目錄的一律不計）。"""
    out: set[str] = set()
    for carrier in carriers:
        rel = carrier.replace(placeholder, "").lstrip("/")
        if "/" in rel:
            out.add(rel.split("/")[0])
    return out


class TestHookEntriesAreExecForm(unittest.TestCase):
    """判準 A~F（實作在 `tools/lib/hook_wiring.hook_form_problems`）。"""

    def test_real_settings_is_all_exec_form(self) -> None:
        problems = _hook_wiring().hook_form_problems(_load_real_settings())
        self.assertEqual(
            problems, [],
            "`.claude/settings.json` 的 hook 條目形態不合規（每筆都會讓某個平台閃窗"
            "或靜默失去 hook）：\n  " + "\n  ".join(problems))

    def test_the_shim_has_exactly_one_home(self) -> None:
        """十份 `python -c` shim 複本收成一支檔之後，不得有第二個家。

        🔴 取樣面刻意是**解析後的 argv**，不是整份檔案的文字。第一版寫成
        `assertNotIn("runpy.run_path", _SETTINGS.read_text(...))`，當場被
        `test_archive_defect_log.TestNoAssertionSamplesALiveDocumentWholesale` 抓到：
        該檔有 6 個 `_comment` 在**合法地**敘述舊 shim 的設計理由，只要有人在註解裡
        寫出那個字樣就假紅——而假紅的下場是有人回頭去改註解裡的歷史敘述（那正是
        Pkg-P12 實際發生過的事）。判準要看的是「**會被執行的東西**裡有沒有 shim」。
        """
        self.assertTrue(_LAUNCHER.is_file(), f"找不到啟動器 {_LAUNCHER}")
        wiring = _hook_wiring()
        offenders = [
            argv for _event, blocks in (_load_real_settings().get("hooks") or {}).items()
            for block in blocks or []
            for hook in block.get("hooks") or []
            for argv in [" ".join(wiring.hook_entry_argv(hook))]
            if "runpy.run_path" in argv or " -c " in argv
        ]
        self.assertEqual(
            offenders, [],
            "有 hook 條目的 argv 又內嵌了 shim 程式碼 ⇒ shim 有了第二個家（同一份知識"
            "住兩個家、只有一個家會被改，是本 repo 的頭號病），而且那種條目在 Windows "
            f"上會經 bash.exe 而閃視窗：{offenders}")

    # ── 合成注入自證：五種弄壞法逐一必紅，還原必綠 ────────────────────────────
    # WHY 用**真實 settings 的內容**在記憶體裡動手：合成 fixture 證明不了「這道判準
    # 對 repo 現況有牙」；而真的改磁碟上那支檔會影響同一棵樹上每個 agent 的每一次
    # 工具呼叫（該檔記載過 hook 誤觸 deny 把所有工具硬鎖死的 P0）。

    def _mutated(self):
        return json.loads(json.dumps(_load_real_settings()))

    def test_injection_1_a_single_entry_falling_back_to_shell_form_is_red(self) -> None:
        bad = self._mutated()
        entry = bad["hooks"]["SessionStart"][0]["hooks"][0]
        entry.pop("args")
        entry["command"] = 'python -c "import runpy" .claude/hooks/sdd_hook_router.py'
        self.assertTrue(_hook_wiring().hook_form_problems(bad),
                        "一條退回 shell form（＝那條每次觸發都閃窗）竟被放行")

    def test_injection_2_a_hardcoded_drive_path_is_red(self) -> None:
        bad = self._mutated()
        bad["hooks"]["SessionStart"][0]["hooks"][0]["args"][0] = (
            chr(68) + ":/CursorProject/AISDCL_Agent/.claude/hooks/_hook_launcher.py")
        self.assertTrue(_hook_wiring().hook_form_problems(bad),
                        "寫死磁碟機路徑竟被放行（DEF-101-778 判例）")

    def test_injection_3_dropping_the_posix_half_is_red(self) -> None:
        """🔴 本鎖的核心：少一邊**不會有任何東西轉紅**，只會在該平台靜默失去 hook。"""
        bad = self._mutated()
        for entry in bad["hooks"]["PreToolUse"]:
            hooks = entry.get("hooks") or []
            if len(hooks) >= 2:
                del hooks[1]  # 砍掉 POSIX 那一條 ⇒ mac/Linux 上這支 hook 消失
                break
        problems = _hook_wiring().hook_form_problems(bad)
        self.assertTrue(problems, "載具配對被拆掉一半竟被放行")
        self.assertTrue(any("未成對" in p for p in problems), problems)

    def test_injection_4_a_command_with_whitespace_is_red(self) -> None:
        """V4 陷阱：`args` 存在時整串 command 會被當成**一個**執行檔路徑（實測 ENOENT）。"""
        bad = self._mutated()
        bad["hooks"]["SessionStart"][0]["hooks"][0]["command"] = "pythonw.exe -X utf8"
        self.assertTrue(_hook_wiring().hook_form_problems(bad),
                        "command 含空白竟被放行——它「看起來像對的」，正是危險所在")

    def test_injection_5_mixing_two_windows_carriers_is_red(self) -> None:
        """混用＝一部分 hook 在某些 session 消失；『加第二個當備援』則會讓 hook 跑兩次。"""
        bad = self._mutated()
        wiring = _hook_wiring()
        for entry in bad["hooks"]["SessionStart"]:
            for hook in entry.get("hooks") or []:
                if hook.get("command") == wiring.WIN_CARRIER_VENV:
                    hook["command"] = wiring.WIN_CARRIER_PATH
                    break
            break
        problems = wiring.hook_form_problems(bad)
        self.assertTrue(any("混用" in p for p in problems), problems)

    def test_injection_6_dropping_type_together_with_args_is_red(self) -> None:
        """🔴 R80 ARCH-02／SD-02：退回 shell form **並順手省掉 `type`** 的組合。

        判準此前寫成 `hook.get("type") != "command": continue`，而同檔 `hook_entry_argv`
        用的是 `get("type", "command")` 且旁註逐字禁止「把沒寫當成不是」。兩個慣例的
        差集就是一個**免費的逃逸口**：省掉一個欄位，A~F 六條（含它自稱的核心 E）一條
        都不會說話。這一格在修復前必失敗，那正是它該有的行為。
        """
        wiring = _hook_wiring()
        bad = self._mutated()
        entry = bad["hooks"]["SessionStart"][0]["hooks"][0]
        entry.pop("args")
        entry.pop("type")
        entry["command"] = 'python -c "import runpy" .claude/hooks/sdd_hook_router.py'
        self.assertTrue(
            any("shell form" in p for p in wiring.hook_form_problems(bad)),
            "省掉 type 就能讓整條條目在形態鎖前隱形（而它在 CC 眼中照跑）")
        self.assertTrue(
            wiring.hook_entry_targets(entry),
            "取數管道自證：解析器若也看不到這條，上面那句斷言就沒有意義")

    def test_the_type_convention_is_one_criterion_across_the_whole_file(self) -> None:
        """三個站點（argv 解析／形態鎖／載具宣告枚舉）必須用**同一個** type 判準。"""
        wiring = _hook_wiring()
        good = {"command": wiring.WIN_CARRIER_VENV,
                "args": [wiring.POSIX_CARRIER, ".claude/hooks/x.py"]}
        odd = dict(good, type="prompt")
        self.assertTrue(wiring.is_command_hook(good), "沒寫 type ＝ CC 的預設 command")
        self.assertFalse(wiring.is_command_hook(odd))
        for hook, argv, carriers in ((good, 3, {wiring.WIN_CARRIER_VENV}), (odd, 0, set())):
            wrapped = {"hooks": {"SessionStart": [{"hooks": [hook]}]}}
            self.assertEqual(len(wiring.hook_entry_argv(hook)), argv)
            self.assertEqual(wiring.declared_win_carriers(wrapped), carriers)
            # 形態鎖：沒寫 type 的那筆必須進入判準（此處缺 POSIX 對半 ⇒ 應紅）；
            # 明確標成別種 type 的那筆必須被排除（⇒ 應綠）。
            self.assertEqual(bool(wiring.hook_form_problems(wrapped)), hook is good)

    def test_restoring_the_real_content_is_green_again(self) -> None:
        """反空轉：上面六格若是因為判準恆紅而通過，這一格會抓到。"""
        self.assertEqual(_hook_wiring().hook_form_problems(self._mutated()), [])


class TestParsersSurviveTheExecFormConversion(unittest.TestCase):
    """🔴 轉換後**仍抓得到**的自證（本輪第一級交付）。

    WHY：exec form 把腳本路徑從 `command` 搬進 `args`，於是全部「讀 command 找腳本名」
    的解析器會掃出空集合 ⇒ 那些鎖**恆綠**，rc 與「正確地全部通過」一模一樣。
    所以「轉換後閘門 rc=0」證明不了任何事，必須證明「轉換後製造違規仍會轉紅」。
    """

    def test_matchers_for_script_still_resolves_every_guard(self) -> None:
        real = _load_real_settings()
        for needle, expected_tool in (
            ("block_bash_on_windows", "Bash"),
            ("lint_powershell_command", "PowerShell"),
            ("context_budget_guard", "Task"),
        ):
            with self.subTest(needle=needle):
                matchers = matchers_for_script(real, needle)
                self.assertTrue(
                    matchers,
                    f"{needle} 在轉換後的 settings 裡解析不到 matcher ⇒ "
                    "`degraded_payload_verdict()` 會改走「找不到它的註冊」那條路，"
                    "而那是靜默失效的樣子")
                self.assertIn(
                    expected_tool, {t for m in matchers for t in matcher_tokens(m)})

    def test_removing_a_registration_still_turns_it_red(self) -> None:
        """注入：把 Bash 守衛的註冊整條拿掉 ⇒ 解析器必須看得出來（不得仍回非空）。"""
        stripped = json.loads(json.dumps(_load_real_settings()))
        for entry in stripped["hooks"]["PreToolUse"]:
            entry["hooks"] = [
                h for h in entry.get("hooks") or []
                if "block_bash_on_windows" not in json.dumps(h, ensure_ascii=False)]
        self.assertEqual(
            matchers_for_script(stripped, "block_bash_on_windows"), [],
            "註冊被拿掉了解析器卻還說找得到 ⇒ 判準與事實脫鉤")
        self.assertTrue(
            registration_shrink_problems(
                registered_tool_scope(stripped), _REGISTRATION_BASELINE),
            "註冊被拿掉之後 shrink-only 棘輪竟然沒說話 ⇒ 它已經恆綠")

    def test_the_scope_enumerator_is_not_vacuous_after_conversion(self) -> None:
        """取數管道自證：枚舉器回空 dict 會讓上面每一條斷言結構上恆真。"""
        scope = registered_tool_scope(_load_real_settings())
        self.assertGreaterEqual(
            len(scope), len(_REGISTRATION_BASELINE),
            f"註冊面枚舉器只回 {len(scope)} 筆（基準 {len(_REGISTRATION_BASELINE)} 筆）"
            "——解析管道壞了，本節其餘判準全部失去意義")


def _make_directory_link(target: Path, link: Path) -> str:
    """在 `link` 建一個「走過去會抵達 `target` 同一個目錄」的連結，回傳所用機制名。

    🔴 **為什麼要分平台，而不是兩邊都 `os.symlink`**（鐵律三「這在另一個平台是什麼
    值？」）：`os.symlink` 在 Windows 上**存在**（不是 `AttributeError`），但底層的
    `CreateSymbolicLinkW` 需要開發者模式或 `SeCreateSymbolicLinkPrivilege`，一般
    Windows 機器與未開啟開發者模式的 runner 上必回 `OSError`（WinError 1314）。
    ⇒ 只寫 `os.symlink` 的話，Windows 側的結果**恆為 skip**——而 skip 不是覆蓋，
    它只是把「這台機器從來沒驗過」寫得比較好看（`DEF-101-343~345` 的形態：連續
    5+ 輪全 APPROVE、卻一次都沒在原生 Windows 上跑過）。

    Windows 上**不需要任何權限**、且語意等價的機制是**目錄 junction**：`_same_path`
    的 docstring 逐字點名「GitHub runner 的目錄 junction」是讓字面比較失效的三種
    Windows 變形之一 ⇒ junction 正是這一格要涵蓋的真實情境，不是為了繞過權限硬找的
    替代品。junction 沒有 `os` 公開 API（`_winapi.CreateJunction` 是私有的），標準
    建法是 cmd 內建的 `mklink /J`。

    🔴 **誠實劃界**：Windows 那一支在本輪的開發機（darwin）上**只驗到分派**（見
    `test_the_windows_branch_uses_a_junction_not_a_symlink`）；`mklink /J` 的實際 rc、
    以及 `samefile(junction, target)` 是否為 True，**未在原生 Windows 上實測**
    （junction 是 reparse point，開檔預設會跟隨 ⇒ `GetFileInformationByHandle` 應回
    目標的檔案索引，這是文件語意推論，不是量測值）。
    """
    if os.name == "nt":
        # `mklink` 是 cmd 的**內建**指令，不是獨立執行檔 ⇒ 必須經 `cmd /c`。
        # 診斷字串以 utf-8/replace 解：cmd 實際吐的是 OEM codepage（cp950 等），
        # 這裡只會讓例外訊息裡的中文降解，不影響 rc 判定（判準只讀 returncode）。
        proc = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60)
        if proc.returncode != 0:
            raise OSError(
                f"mklink /J rc={proc.returncode}: "
                f"{(proc.stderr or proc.stdout).strip()!r}")
        return "junction"
    os.symlink(target, link, target_is_directory=True)
    return "symlink"


class TestSamePathIsNotVacuous(unittest.TestCase):
    """`_same_path()` 是把「字面相等」放寬成「同一個實體」的那一層——**放寬最常見的
    失敗模式是寬過頭變成恆真**，所以它自己要有一組雙向判準。

    這幾格**兩個平台都跑得到、也都在量同一件事**（沒有任何 `skipUnless`）：連結是
    POSIX 與 Windows 都有的機制，只是**原語不同**——POSIX 是 symlink、Windows 是
    目錄 junction（原語選擇與 WHY 見 `_make_directory_link`）。此前這裡兩邊都寫
    `os.symlink`，於是 Windows 側恆為 skip；改成各走各的原語之後，Windows 不再需要
    開發者模式就有真覆蓋。殘留的那一個 skip 只剩「這台機器的檔案系統根本建不起
    連結」（FAT／某些網路磁碟）這一種機器能力問題，不是平台語意
    （`DEF-101-766`：單平台判準不可無條件外推，反之亦然）。
    """

    def setUp(self) -> None:
        self.box = Path(tempfile.mkdtemp(prefix="same_path_probe_"))
        self.addCleanup(shutil.rmtree, self.box, ignore_errors=True)

    def test_two_different_directories_are_not_the_same(self) -> None:
        """反恆真：兩個貨真價實不同的目錄必須回 False。

        🔴 **看起來像廢話，實際是 Windows 側唯一的 fail-open 偵測器**（勿刪，WHY 見
        `_same_path` docstring 末段）：`samefile` 比的是檔案 ID，而不支援 file ID 的
        檔案系統（FAT／部分 SMB）一律回 0 ⇒ 那種機器上任兩個檔都會被判成同一個。
        本格刻意在**本機真正的暫存檔案系統**上量，退化時就地轉紅。
        """
        (self.box / "a").mkdir()
        (self.box / "b").mkdir()
        self.assertFalse(_same_path(self.box / "a", self.box / "b"),
                         "不同目錄被判成同一個 ⇒ 判準已恆真，上面每一條斷言都失去意義")

    def test_a_link_to_the_same_directory_is_the_same(self) -> None:
        """正向：這正是 macOS `/var` → `/private/var`、以及 Windows runner 的目錄
        junction 讓字面比較假紅的那個機制。原語由 `_make_directory_link()` 依平台選，
        兩個平台**都真的建一個連結再問一次**，不是其中一邊靠 skip 混過去。"""
        (self.box / "real").mkdir()
        link = self.box / "link"
        try:
            mechanism = _make_directory_link(self.box / "real", link)
        except OSError as exc:  # 檔案系統本身建不起連結（FAT／部分網路磁碟）
            self.skipTest(f"本機檔案系統建不起目錄連結（機器能力，非平台語意）：{exc}")
        self.assertTrue(_same_path(link, self.box / "real"),
                        f"經{mechanism}抵達的同一個目錄被判成不同 ⇒ 判準回到了字面比較")

    def test_the_windows_branch_uses_a_junction_not_a_symlink(self) -> None:
        """🔴 這一格是「Windows 側真的有覆蓋」在 darwin 開發機上**唯一**的證據。

        沒有它，把 `_make_directory_link()` 的 junction 分支刪掉會完全無聲：mac 上
        每一格照樣綠（那條分支在 mac 上本來就不會執行），而 Windows 側悄悄退回
        「恆 skip」——測試檔在、判準在、rc 是 0，與修好完全相同。
        以注入 `os.name` 驗證而不是掛 `skipUnless`，是本檔既有慣例（見 `:481`／`:825`
        兩處的同一理由：注入取得的覆蓋比「只在對的機器上才跑」更大）。
        """
        real, link = self.box / "real", self.box / "link"
        real.mkdir()
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], **_kw: object) -> subprocess.CompletedProcess:
            calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with mock.patch.object(os, "name", "nt"), \
             mock.patch.object(os, "symlink", side_effect=AssertionError(
                 "Windows 分支呼叫了 os.symlink ⇒ 覆蓋又被押回開發者模式上")), \
             mock.patch.object(subprocess, "run", side_effect=fake_run):
            self.assertEqual(_make_directory_link(real, link), "junction")
        self.assertEqual(len(calls), 1, f"Windows 分支應恰好外呼一次；實得 {calls}")
        # 下一行的 `/c`／`/J` 是 **cmd 的參數開關**，不是路徑字面值 ⇒ 它們不由
        # `Path`／`os.fspath` 算出，Windows 上也不會被渲染成反斜線。
        #
        # 🔴 **為何要比整個 argv、而不只是前四位**（獨立複驗 R83 補上的缺口）：
        # `mklink` 的語法是 `/J <Link> <Target>`，而**順位寫反是只在 Windows 才成立的
        # 語意錯誤**——`mklink /J <已存在的 real> <不存在的 link>` 回非零 rc ⇒
        # `_make_directory_link` 拋 OSError ⇒ 呼叫端 skipTest，於是本包宣稱修掉的
        # 那個「Windows 側恆 skip」原封不動地回來，而 darwin 上永遠走不到那一行。
        # 缺口是實測的，不是設想：只比 `calls[0][:4]` 時把兩個位置對調，本類 4 格
        # **照樣全綠**。前四位是「有沒有選對機制」，後兩位是「有沒有用對」，兩者都只有
        # 這一格看得到（本檔既有慣例：注入取得的覆蓋 > 只在對的機器上才跑）。
        # 🔴 這份期望值刻意**留在 assertEqual 的引數位置內**、不抽成區域變數：抽出去之後
        # `/c`／`/J` 就不再是「assert 引數裡的字面值」，`scan_posix_abs_asserts` 整組看不到
        # 它，行尾豁免當場變 stale（實測轉紅一次）——那等於用重構繞過掃描器，比留著誤報糟。
        self.assertEqual(
            calls[0],
            ["cmd", "/c", "mklink", "/J",  # posix-abs-ok: cmd 開關非路徑
             str(link), str(real)],
            "junction 是 Windows 上唯一不需要提權的目錄連結機制，且 mklink 的順位必須是 "
            f"`/J <Link> <Target>`（寫反即回非零 rc ⇒ 退回恆 skip）；實得 {calls[0]}")

    def test_a_missing_path_is_fail_closed(self) -> None:
        """量不到時必須回 False（不得因為 stat 失敗就放行）。"""
        self.assertFalse(_same_path(self.box / "nope", self.box),
                         "路徑不存在時竟回 True ⇒ fail-open，判準會在最需要它的時候噤聲")


class TestHookLauncherContract(unittest.TestCase):
    """啟動器是**全部 hook 的唯一入口**，改壞它等於一次弄壞六支守衛。

    四種 payload 比 rc（形狀照本檔既有的 `_run_hook()`）：缺檔 fail-open／目標
    `exit 2` 不得被吞掉／沒給目標不得亂擋／正常目標的 argv 與 cwd 契約。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp(prefix="r80_launcher_lock_"))
        (cls.root / ".claude" / "hooks").mkdir(parents=True)
        (cls.root / ".claude" / "hooks" / "deny.py").write_text(
            "import sys\nsys.stderr.write('BLOCKED\\n')\nsys.exit(2)\n",
            encoding="utf-8", newline="\n")
        (cls.root / ".claude" / "hooks" / "ok.py").write_text(
            "import json, os, sys\n"
            "sys.stdout.write(json.dumps({'argv': sys.argv, 'cwd': os.getcwd(),\n"
            "    'stdin': sys.stdin.read()}))\n",
            encoding="utf-8", newline="\n")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.root, ignore_errors=True)

    def _launch(self, *args: str, stdin_text: str = "{}") -> tuple[int, str, str]:
        env = _child_env({"CLAUDE_PROJECT_DIR": str(self.root), "PYTHONUTF8": "1"})
        proc = subprocess.run(  # child-encoding-ok: 啟動器不是「會說話的那一層」——它只 runpy 目標腳本，輸出編碼由目標自己的 UTF-8 保護決定（判準四已逐支釘住六支目標）；本案的三支合成目標只印 ASCII
            [sys.executable, str(_LAUNCHER), *args], input=stdin_text,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, env=env, cwd=str(_REPO_ROOT))
        return proc.returncode, proc.stdout or "", proc.stderr or ""

    def test_missing_target_is_fail_open(self) -> None:
        """🔴 這條的方向是 P0：缺檔若回 2，PreToolUse 會把**所有工具**硬鎖死。"""
        rc, out, err = self._launch(".claude/hooks/NOT_THERE.py")
        self.assertEqual(rc, 0, f"缺檔必須 fail-open；實得 rc={rc} err={err[:200]!r}")
        self.assertEqual((out, err), ("", ""), "fail-open 時不得有任何輸出")

    def test_no_target_argument_never_denies(self) -> None:
        rc, _out, _err = self._launch()
        self.assertEqual(rc, 0, "沒給目標時絕不可回 2")

    def test_exit_2_is_propagated_verbatim(self) -> None:
        """deny 語意不能斷——六支守衛裡有三支靠 exit 2 硬擋。"""
        rc, _out, err = self._launch(".claude/hooks/deny.py")
        self.assertEqual(rc, 2, f"目標 exit 2 必須原樣傳遞；實得 rc={rc}")
        self.assertIn("BLOCKED", err, "目標的 stderr 必須回得來（那是使用者唯一看得到的指引）")

    def test_stdin_argv_and_cwd_match_the_old_shim(self) -> None:
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read"})
        rc, out, err = self._launch(".claude/hooks/ok.py", "extra1", stdin_text=payload)
        self.assertEqual(rc, 0, err[:300])
        got = json.loads(out)
        self.assertEqual(got["stdin"], payload, "stdin 的 hook JSON 必須原樣送達目標")
        # argv[0] 拆成兩問，各自問一件事（原本合併成一次字面相等，見 `_same_path` 的 WHY）：
        #   ①「是絕對路徑嗎」——這是契約本身（相對路徑會隨 hook 被呼叫時的 cwd 漂移）；
        #   ②「指到的是不是那支目標」——同一個檔案實體即可，字面不必逐字相同。
        self.assertTrue(
            os.path.isabs(got["argv"][0]),
            f"argv[0] 必須是絕對路徑（與舊 shim 逐項等價）；實得 {got['argv'][0]!r}")
        self.assertTrue(
            _same_path(got["argv"][0], self.root / ".claude" / "hooks" / "ok.py"),
            "argv[0] 必須指向目標腳本本身；"
            + _path_mismatch(got["argv"][0], self.root / ".claude" / "hooks" / "ok.py"))
        self.assertEqual(got["argv"][1:], ["extra1"], "其餘引數順位不得改變")
        self.assertTrue(
            _same_path(got["cwd"], self.root),
            "cwd 必須被切到 CLAUDE_PROJECT_DIR（DEF cwd≠專案根的 P0）；"
            + _path_mismatch(got["cwd"], self.root))

    def test_the_cwd_criterion_still_catches_a_launcher_that_never_chdirs(self) -> None:
        """反空轉自證：把 production 的 `os.chdir(root)` 拿掉，上一格的 cwd 判準必須轉紅。

        🔴 **為什麼這一格非有不可**：上一格剛從「字面相等」換成「同一個實體」，而
        放寬判準最常見的失敗模式就是**寬過頭變成恆真**。合成注入一支「忘記 chdir」
        的啟動器（那正是它要防的 P0：hook 在錯的 cwd 下跑，所有相對路徑判準全歪），
        證明新判準仍然說得出話。

        注入的是 production 檔的**副本**（`_LAUNCHER` 一個字都沒動），跑完即丟。
        """
        broken = self.root / "broken_launcher.py"
        src = _LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("os.chdir(root)", src,
                      "production 啟動器已不再 chdir？那本注入失去對照意義，判準要重寫")
        broken.write_text(src.replace("os.chdir(root)", "pass  # 注入：忘記 chdir"),
                          encoding="utf-8", newline="\n")

        env = _child_env({"CLAUDE_PROJECT_DIR": str(self.root), "PYTHONUTF8": "1"})
        # 這裡刻意**不加** `child-encoding-ok`：子行程是 tmp 裡的合成副本，不是 repo
        # 內的檔，編碼衛生掃描器解析不到它 ⇒ 加了會變成 stale 標記（實測當回合被
        # `test_subprocess_encoding_hygiene.py` 抓到）。編碼由下面的 `encoding=` 顯式指定。
        proc = subprocess.run(
            [sys.executable, str(broken), ".claude/hooks/ok.py"], input="{}",
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=60, env=env, cwd=str(_REPO_ROOT))
        self.assertEqual(proc.returncode, 0, proc.stderr[:300])
        got = json.loads(proc.stdout)
        self.assertFalse(
            _same_path(got["cwd"], self.root),
            "啟動器沒有 chdir，cwd 判準卻仍然說『對得上』⇒ 它已經恆綠。"
            f"實得 cwd={got['cwd']!r}")


class TestDeclaredWindowsCarrierExists(unittest.TestCase):
    """🔴 方案書 §4.3 自陳「連 `.venv` 都沒有仍無機械物看守」那個缺口的補丁。

    為什麼這個缺口比閃窗嚴重：載具解析不到 ⇒ 六支守衛**全部靜默失效**，而螢幕上的
    表徵就是「終於不閃窗了」。把缺口寫下來卻不給判準，等於把它登記成「已知且已接受」。

    判準的形狀是**宣告 ↔ 實況雙向綁定**（不是硬編一個路徑）：settings.json 宣告了
    venv 載具 ⇒ 那個路徑必須存在。這樣「有人把載具改成別的東西」也會被同一條守到。

    🔴 為何不用 `skipUnless`／不用「偵測到 CI 就跳過」：
      · 判準本體 `carrier_liveness_problems()` 自帶 `on_windows` 參數，兩個平台方向
        都在**同一台機器上**以注入驗到（`DEF-101-766`：單平台判準不可無條件外推）；
        用 `skipUnless` 反而會讓另一個方向永遠沒人跑過。
      · 非 Windows 不看 venv 載具是**語意上的**理由：`.venv/Scripts/pythonw.exe` 在
        mac/Linux 本來就不存在，那條在該平台是設計上的 fail-open，不是缺陷。
        （該平台自己那條載具另有 `TestPosixCarrierLiveness`。）
      · CI 的豁免同樣是語意的、且不由本測試負責：hook 只在「Claude Code 會跑的地方」
        有意義，CI 從不跑 hook——所以會出聲的那一層落在
        `tools/check_hooks_liveness.py`（開發機的閘門會跑、CI 由呼叫端整段跳過），
        本測試只負責證明那個判準有牙。

    🔴 **R80 ARCH-01：本類刻意不再有「這台機器上載具在不在」那一格**。原本那一格是
    `assertEqual(carrier_liveness_problems(real, repo_root), [])`，它量的是**機器狀態**
    而不是 repo 內容，於是在兩種完全正常的情境下必紅：
      · windows-compat-ci／windows-smoke：`python tools/run_root_unittests.py` 跑在
        `./tools/bootstrap.ps1` **之前**，那時 `.venv` 還不存在；而且該 workflow 稍後
        會把 `.venv` 更名為 `.venv-cache-windows`——所以「把測試挪到 bootstrap 之後」
        只是換一種方式再紅一次，不是修法。
      · 任何**尚未跑過 bootstrap 的全新 clone**（含開發者第一次 clone 後直接跑根層
        unittest）。複驗實測：project_dir 指向無 `.venv` 的暫存目錄 → problems len = 1。
    機器狀態的正確通報者是 `tools/check_hooks_liveness.py`（advisory：印警告、不阻擋，
    四個呼叫端在 `$CI` 有值時整段跳過）。判準本體**一個字都沒有放寬**——牙由下面三格
    注入自證；換上來的是一件機器無關、而且原本沒有任何人在守的事（見下一格）。
    """

    def test_the_declared_carrier_is_what_bootstrap_produces(self) -> None:
        """宣告的 venv 型載具必須落在 bootstrap **真的會建出來**的那個目錄下。

        這一格抓的是「宣告在每一台機器上都不可能成立」——例如寫成
        `.venv311/Scripts/pythonw.exe`：hook 會在**所有**機器上靜默死掉，而被換掉的
        那條舊判準只在「我這台剛好還沒 bootstrap」時才會出聲。SSOT 是
        `tools/bootstrap_core.VENV_DIR`，不是本檔複寫的一個字面。
        """
        import bootstrap_core  # noqa: PLC0415

        wiring = _hook_wiring()
        declared = wiring.declared_win_carriers(_load_real_settings())
        venv_declared = {c for c in declared if c != wiring.WIN_CARRIER_PATH}
        dirs = carrier_venv_dirs(venv_declared, wiring.PROJECT_DIR_PLACEHOLDER)
        self.assertTrue(
            dirs,
            "settings 未宣告任何 venv 型 Windows 載具 ⇒ 本判準與 carrier_liveness_"
            "problems() 一起變成空轉（PATH 載具的實況靜態看不到，是它自陳的盲區）。"
            f"實查宣告：{sorted(declared)}")
        self.assertEqual(
            dirs, {Path(bootstrap_core.VENV_DIR).name},
            f"宣告的載具落在 {sorted(dirs)}，而 bootstrap 建的是 "
            f"{Path(bootstrap_core.VENV_DIR).name} ⇒ 這個宣告在**每一台**機器上都不會成立，"
            "全部 hook 靜默失效而表徵與『修好了』相同")

    def test_the_bootstrap_binding_catches_a_carrier_that_is_never_produced(self) -> None:
        """判準自證：換成 bootstrap 產不出來的目錄必須看得出差異（反空轉）。"""
        placeholder = _hook_wiring().PROJECT_DIR_PLACEHOLDER
        self.assertEqual(
            carrier_venv_dirs({f"{placeholder}/.venv311/Scripts/pythonw.exe"}, placeholder),
            {".venv311"})
        self.assertEqual(carrier_venv_dirs({"pythonw.exe"}, placeholder), set())

    def test_a_missing_carrier_is_red_on_windows(self) -> None:
        """注入：同一份真實 settings ＋ 「那個檔不存在」的世界 ⇒ 必紅。"""
        problems = _hook_wiring().carrier_liveness_problems(
            _load_real_settings(), str(_REPO_ROOT),
            exists=lambda _p: False, on_windows=True)
        self.assertTrue(problems, "宣告了 venv 載具、實況卻不存在，判準竟不出聲")
        self.assertIn("全部 hook 都不會跑", problems[0])

    def test_the_windows_criterion_is_silent_on_posix(self) -> None:
        """反向：mac/Linux 上不得對 **Windows 載具**發言（誤報會讓整道守衛被關掉）。

        🔴 R80 SA-05 訂正本格的斷言對象：原文斷言整個回傳為空，而那把「這個平台沒有
        Windows 載具問題」寫成了「這個平台沒有載具問題」——POSIX 自己那條同樣是單點
        失效面。現在改斷言「訊息裡不得出現 Windows 載具」，原意（不誤報）保住，POSIX
        那半的牙由 `TestPosixCarrierLiveness` 承接。
        """
        problems = _hook_wiring().carrier_liveness_problems(
            _load_real_settings(), str(_REPO_ROOT),
            exists=lambda _p: False, on_windows=False,
            probe=lambda _p: ("/usr/bin/python3", (3, 12)))
        self.assertEqual(
            [p for p in problems if "pythonw.exe" in p], [],
            "POSIX 上對 Windows 專屬載具發言＝誤報（DEF-101-766 同型）")

    def test_changing_the_carrier_moves_the_criterion_with_it(self) -> None:
        """雙向綁定自證：把宣告換成 PATH 載具 ⇒ 本判準不再對 venv 路徑發言。"""
        wiring = _hook_wiring()
        swapped = json.loads(
            json.dumps(_load_real_settings()).replace(
                wiring.WIN_CARRIER_VENV, wiring.WIN_CARRIER_PATH))
        self.assertEqual(wiring.declared_win_carriers(swapped),
                         {wiring.WIN_CARRIER_PATH})
        self.assertEqual(
            wiring.carrier_liveness_problems(
                swapped, str(_REPO_ROOT), exists=lambda _p: False, on_windows=True),
            [], "PATH 載具的實況取決於 session 的 PATH，靜態判準不得擅自判死")


class TestPosixCarrierLiveness(unittest.TestCase):
    """POSIX 側載具的存在性判準（R80 SA-05）。

    🔴 立案理由（缺口與 Windows 側**不對稱**，所以不是「順手補對稱」）：Windows 條目
    釘死一個確定的檔案，POSIX 條目吃的是 **`PATH` 上任意一個 `python3`**——macOS 內建
    那支常年是 3.9，而本 repo 的 bootstrap 門檻是 3.11。此前 `carrier_liveness_problems()`
    在非 Windows **一律回空**，等於把「這個平台沒有 Windows 載具」寫成「這個平台沒有
    載具問題」。三種失效（檔不在／沒有執行位元／直譯器太舊）表徵完全相同：CC 只記一行
    ERROR 就放行，六支守衛一起消失，螢幕上就是「終於不閃窗了」。

    四格全部以注入驅動、`on_windows=False` 強制走 POSIX 分支——判準的方向不該取決於
    這台機器剛好是什麼（同本檔 `TestBlockBashHookDoesNotHurtOtherPlatforms` 的理由）。
    """

    def _posix(self, **kwargs) -> list[str]:
        base = {"exists": lambda _p: True, "is_exec": lambda _p: True,
                "probe": lambda _p: ("/usr/bin/python3", (3, 12))}
        base.update(kwargs)
        return _hook_wiring().carrier_liveness_problems(
            _load_real_settings(), str(_REPO_ROOT), on_windows=False, **base)

    def test_a_healthy_posix_world_is_silent(self) -> None:
        """反空轉：判準若恆紅，下面四格全部失去意義。"""
        self.assertEqual(self._posix(), [])

    def test_a_missing_launcher_is_red(self) -> None:
        problems = self._posix(exists=lambda _p: False)
        self.assertTrue(problems, "POSIX 載具不存在竟不出聲")
        self.assertIn("全部 hook 都不會跑", problems[0])

    def test_a_launcher_without_the_exec_bit_is_red(self) -> None:
        """`git index 100755` 被洗掉時 spawn 回 EACCES，而 EACCES 是 fail-open。"""
        problems = self._posix(is_exec=lambda _p: False)
        self.assertTrue(any("執行位元" in p for p in problems), problems)

    def test_an_unresolvable_shebang_is_red(self) -> None:
        problems = self._posix(probe=lambda _p: (None, None))
        self.assertTrue(any("shebang" in p for p in problems), problems)

    def test_an_interpreter_below_the_floor_is_red(self) -> None:
        """macOS 系統 python3 的**預設**狀態（3.9）——這不是假想情境。"""
        problems = self._posix(probe=lambda _p: ("/usr/bin/python3", (3, 9)))
        self.assertTrue(any("3.9" in p for p in problems), problems)
        self.assertTrue(any("bootstrap_core" in p for p in problems), problems)

    def test_the_floor_matches_the_bootstrap_ssot(self) -> None:
        """`POSIX_MIN_PY` 與 bootstrap 挑直譯器的門檻必須是同一個數字。

        兩處刻意各寫一份（`tools/lib/hook_wiring.py` 檔頭約定只依賴 stdlib，不 import
        bootstrap）——**同一份知識允許住兩個家的唯一條件就是有東西在對帳**，本格就是
        那個東西（R73 `Find-GitBash` 的教訓：兩個家、只有一個家被鎖）。
        """
        source = (_REPO_ROOT / "tools" / "bootstrap_core.py").read_text(encoding="utf-8")
        major, minor = _hook_wiring().POSIX_MIN_PY
        self.assertIn(
            f"version_info[:2]>=({major},{minor})", source.replace(" ", ""),
            f"hook_wiring.POSIX_MIN_PY={major}.{minor} 與 bootstrap_core 的門檻已脫鉤")

    def test_the_real_launcher_carries_a_resolvable_shebang(self) -> None:
        """機器無關的那一半：啟動器檔案本身必須帶 shebang（POSIX 直接 exec 的前提）。"""
        first = _LAUNCHER.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(first.startswith("#!"), f"啟動器首行不是 shebang：{first!r}")
        self.assertIn("python", first)


class TestExecFormConversionScope(unittest.TestCase):
    """exec form 轉換的**射程**——哪一份 settings 轉了、哪一份還沒（R80 QA-03）。

    🔴 立案理由（史實）：R80 只轉了**根層**那一份，根 `CLAUDE.md`〈鐵律一之二〉一度寫成
    通則。兩個後果：①AutoClaude 子專案 session 下閃窗一次都沒少；②「那 6 條退回 shell
    form」永遠不會轉紅。處置＝把「還沒轉的有幾條」變成**可查的量測值**：掃描面現查磁碟，
    判準是相等——多了＝退步、少了＝轉好了卻沒回來改表。凍結版（Copy-on-Evolve）具名排除。
    R81 已把 AutoClaude 那份轉完（普查表兩格皆 0）⇒ 本類職責由「登記還沒轉的」變成
    「不准有人退回去」。

    🔴 R84 訂正上一段那個「兩格皆 0」——**它是假的安心**（訴求 7「session 結束仍有彈跳
    視窗」窮舉出來的第一名）：`FROZEN_SETTINGS_PREFIX` 把 `AISDLC_SDD/AISDLC_SDD_v*` 這
    **30 份**全部結構性排除在掃描面之外，而其中一份是 **LATEST**——真的會被 Claude Code
    載入的活躍檔（框架 skills 掛在版本目錄下，以它為 cwd 開 session 是常態）。實測那 30
    份**全數仍是 shell form** ⇒ 對那種 session，R80／R81 的修法一次都沒生效，而普查表
    照樣兩格全綠。處置分兩半：LATEST 進掃描面（以**版本中性鍵**登記，不把版號寫成常數）、
    凍結歷史面登記成 shrink-only 的已知豁免（`TestFrozenShellFormIsAShrinkOnlyExemption`）。
    """

    def _counts(self) -> dict[str, int]:
        return _hook_wiring().census_counts(_REPO_ROOT)

    def test_the_census_matches_the_disk(self) -> None:
        problems = _hook_wiring().shell_form_census_problems(self._counts())
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_scan_face_is_not_vacuous(self) -> None:
        """取數管道自證：掃描面塌成空的話上面那格恆綠。"""
        wiring = _hook_wiring()
        found = wiring.discover_active_settings(_REPO_ROOT)
        self.assertIn(".claude/settings.json", found)
        self.assertIn("AutoClaude/.claude/settings.json", found)
        self.assertIn(wiring.LATEST_SETTINGS_KEY, self._counts(),
                      "LATEST 那一份沒進普查表 ⇒ 它退回／停在 shell form 不會有東西轉紅")

    def test_the_latest_sdd_settings_is_in_scope_under_its_real_path(self) -> None:
        """LATEST 的**實際路徑**必須在掃描面內，且版號不得寫死在任何判準裡。"""
        wiring = _hook_wiring()
        latest = wiring.latest_sdd_settings(_REPO_ROOT)
        self.assertIsNotNone(latest, "LATEST 解析不到 ⇒ 這一族的判準全部空轉")
        self.assertTrue((_REPO_ROOT / latest).is_file(), latest)
        self.assertIn(latest, wiring.discover_active_settings(_REPO_ROOT))
        self.assertEqual(wiring.census_key(latest, _REPO_ROOT), wiring.LATEST_SETTINGS_KEY)
        # 版號中性自證：普查表的鍵裡不得出現任何 `v<數字>.<數字>` 字面。
        self.assertEqual(
            [k for k in wiring.SHELL_FORM_CENSUS if re.search(r"_v\d+\.\d+", k)], [],
            "普查表把 LATEST 版號寫成常數 ⇒ Copy-on-Evolve 開新版時它就過期")

    def test_reverting_the_latest_one_to_shell_form_is_red(self) -> None:
        """🔴 本輪修法的紅綠自證（合成注入在**真實 LATEST 內容**上做）。

        修法前這一格由磁碟直接證實：LATEST 實測 3 條 shell form、基準 0 ⇒ 普查判準紅。
        轉成 exec form 之後磁碟造不出那個狀態，故改由記憶體注入驅動（牙不變）。
        """
        wiring = _hook_wiring()
        latest = wiring.latest_sdd_settings(_REPO_ROOT)
        settings = json.loads((_REPO_ROOT / latest).read_text(encoding="utf-8"))
        before = len(wiring.shell_form_entries(settings))
        hook = settings["hooks"]["SessionStart"][0]["hooks"][0]
        hook.pop("args", None)
        hook["command"] = 'python -c "import runpy" .claude/hooks/session_start.py'
        after = len(wiring.shell_form_entries(settings))
        self.assertEqual(after, before + 1, "注入本身沒生效 ⇒ 下面那句斷言沒有意義")
        counts = dict(self._counts(), **{wiring.LATEST_SETTINGS_KEY: after})
        problems = wiring.shell_form_census_problems(counts)
        self.assertTrue(any("退回 shell form" in p for p in problems), problems)

    def test_frozen_non_latest_versions_are_still_excluded(self) -> None:
        """凍結版（非 LATEST）**確實存在於磁碟上**，排除是刻意的、不是掃不到。"""
        wiring = _hook_wiring()
        latest = wiring.latest_sdd_settings(_REPO_ROOT)
        frozen = sorted(_REPO_ROOT.glob("AISDLC_SDD/AISDLC_SDD_v*/.claude/settings.json"))
        self.assertTrue(frozen, "凍結版一份都掃不到 ⇒ 這條排除規則已經無事可做")
        found = wiring.discover_active_settings(_REPO_ROOT)
        self.assertEqual(
            [rel for rel in found
             if rel.startswith(wiring.FROZEN_SETTINGS_PREFIX) and rel != latest], [],
            "非 LATEST 的凍結版跑進了活躍掃描面 ⇒ Copy-on-Evolve 的歷史快照會被追殺")

    def test_a_regression_to_shell_form_is_red(self) -> None:
        """注入：根層多一條 shell form ⇒ 必紅（那一份的閃窗回來了）。"""
        wiring = _hook_wiring()
        counts = self._counts()
        counts[".claude/settings.json"] += 1
        problems = wiring.shell_form_census_problems(counts)
        self.assertTrue(any("退回 shell form" in p for p in problems), problems)

    def test_converting_without_updating_the_census_is_also_red(self) -> None:
        """另一向：轉好了卻沒下修基準 ⇒ 餘裕＝日後無聲加回的破口。R81 把表歸零之後，
        磁碟上再也造不出 `counts < baseline`，故改由**合成基準**驅動（判準與牙不變）。"""
        problems = _hook_wiring().shell_form_census_problems(
            {"AutoClaude/.claude/settings.json": 0},
            {"AutoClaude/.claude/settings.json": 6})
        self.assertTrue(any("沒同步下修基準" in p for p in problems), problems)

    def test_an_unregistered_active_settings_file_is_red(self) -> None:
        """注入：新開一份活躍 settings 卻不入表 ⇒ 「這份轉了沒有」對所有機械物隱形。"""
        counts = dict(self._counts(), **{"ConsoleUI/.claude/settings.json": 3})
        problems = _hook_wiring().shell_form_census_problems(counts)
        self.assertTrue(any("必須顯式入表" in p for p in problems), problems)

    def test_every_active_settings_file_passes_the_form_criteria(self) -> None:
        """🔴 R84：形態判準 A~F 的掃描面由「只有根檔」擴到**每一份活躍 settings**。

        為何這一格此前不存在（而不是「不需要」）：`hook_form_problems()` 對
        `AutoClaude/.claude/settings.json` 實測回 **12 筆假紅**（B／E 兩條做字面比對，
        而那份檔的載具帶 `../`）⇒ 想擴面的人會先撞到一堵假牆，於是擴面一直沒發生，
        而 SDD LATEST 那份 shell form 就一直沒有任何形態判準看著。假紅先修（見
        `win_carrier_kind()`），再擴面——順序反了就會有人把判準關掉。
        """
        wiring = _hook_wiring()
        for rel in wiring.discover_active_settings(_REPO_ROOT):
            settings = json.loads((_REPO_ROOT / rel).read_text(encoding="utf-8"))
            problems = wiring.hook_form_problems(settings)
            self.assertEqual(problems, [], f"{rel}：\n  " + "\n  ".join(problems))

    def test_a_parent_relative_carrier_is_not_a_false_positive(self) -> None:
        """A2b 的正向自證：帶 `../` 的載具（子專案／SDD 各版唯一可行的寫法）必須放行。"""
        wiring = _hook_wiring()
        for depth in ("../", "../../"):
            launcher = f"${{CLAUDE_PROJECT_DIR}}/{depth}.claude/hooks/_hook_launcher.py"
            settings = {"hooks": {"SessionStart": [{"hooks": [
                {"type": "command",
                 "command": f"${{CLAUDE_PROJECT_DIR}}/{depth}.venv/Scripts/pythonw.exe",
                 "args": [launcher, ".claude/hooks/x.py"]},
                {"type": "command", "command": launcher, "args": [".claude/hooks/x.py"]},
            ]}]}}
            self.assertEqual(wiring.hook_form_problems(settings), [], depth)
            self.assertEqual(wiring.win_carrier_kind(
                f"${{CLAUDE_PROJECT_DIR}}/{depth}.venv/Scripts/pythonw.exe"), "venv")

    def test_a_bogus_carrier_is_still_red_after_the_normalisation(self) -> None:
        """反向自證：正規化不得寬到把任何 `pythonw.exe` 結尾的東西都當成載具。"""
        wiring = _hook_wiring()
        for bad in ("${CLAUDE_PROJECT_DIR}/../.venv/Scripts/python.exe",
                    "${CLAUDE_PROJECT_DIR}/../tools/pythonw.exe",
                    "/usr/bin/pythonw.exe"):
            self.assertIsNone(wiring.win_carrier_kind(bad), bad)

    def test_shell_form_entries_counts_the_type_less_ones_too(self) -> None:
        """與 ARCH-02 同一條 type 慣例：省掉 `type` 的 shell form 條目一樣要被數到。"""
        wiring = _hook_wiring()
        settings = {"hooks": {"PreToolUse": [{"hooks": [
            {"command": "python -c ... a.py"},
            {"type": "command", "command": "python -c ... b.py"},
            {"type": "prompt", "command": "not a command hook"},
        ]}]}}
        self.assertEqual(len(wiring.shell_form_entries(settings)), 2)


class TestFrozenShellFormIsAShrinkOnlyExemption(unittest.TestCase):
    """凍結歷史面（`AISDLC_SDD/AISDLC_SDD_v*` 裡**非 LATEST** 的那些）的 shell form 份數。

    🔴 立案（R84 訴求 7）：這一族此前是**結構性豁免**——`FROZEN_SETTINGS_PREFIX` 一句話
    就把 30 份全部踢出掃描面，於是「凍結面有沒有被人動過」與「LATEST 轉了沒有」兩件事
    同時失明。凍結面依 Copy-on-Evolve 政策不改寫，所以正解不是把它們也轉掉（那才是打破
    政策），而是把「還有幾份是 shell form」登記成**可查的量測值**、判準取相等、方向只准
    變小。新開一版**不會**讓它上升：新版由已是 exec form 的 LATEST 複製而來。
    """

    def test_the_frozen_ratchet_matches_the_disk(self) -> None:
        wiring = _hook_wiring()
        problems = wiring.frozen_shell_form_problems(
            wiring.frozen_shell_form_settings(_REPO_ROOT))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_scan_face_is_not_vacuous(self) -> None:
        """反空轉：這一族真的有東西在（份數塌成 0 時上一格會因基準不符而紅，不是恆綠）。"""
        wiring = _hook_wiring()
        found = wiring.frozen_shell_form_settings(_REPO_ROOT)
        self.assertTrue(found, "凍結面掃不到任何 shell form ⇒ 判準已空轉")
        latest = wiring.latest_sdd_settings(_REPO_ROOT)
        self.assertNotIn(latest, found, "LATEST 被算進凍結面 ⇒ 它會被那條豁免遮住")

    def test_touching_a_frozen_version_is_red(self) -> None:
        """注入：份數上升（＝有人真的改了凍結面，或 LATEST 解析壞了把活躍那份算進來）。"""
        wiring = _hook_wiring()
        found = wiring.frozen_shell_form_settings(_REPO_ROOT)
        problems = wiring.frozen_shell_form_problems(found + ["AISDLC_SDD/x/.claude/settings.json"])
        self.assertTrue(any("上升" in p for p in problems), problems)

    def test_shrinking_without_lowering_the_cap_is_also_red(self) -> None:
        """另一向：真的轉掉一份卻沒下修基準 ⇒ 餘裕＝日後無聲加回去的破口。"""
        wiring = _hook_wiring()
        found = wiring.frozen_shell_form_settings(_REPO_ROOT)
        problems = wiring.frozen_shell_form_problems(found[:-1])
        self.assertTrue(any("下降" in p for p in problems), problems)


#: 「hook 行程生出來的子行程不得配 console」判準的**第二個掃描面**。
#: 第一個是 `tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest`（掃
#: `.claude/hooks/`）；本組掃 `AutoClaude/tools/hooks/`——那一整棵樹先前一個判準都沒有。
_AC_HOOK_DIR = _REPO_ROOT / "AutoClaude" / "tools" / "hooks"
_SPAWN_ATTRS = ("run", "Popen", "call", "check_output", "check_call")


def _sdd_latest_hook_dir() -> Path | None:
    """SDD **LATEST** 的 hook 樹（第三個掃描面，R88／DEF-200-104）。

    版號一律現查 SSOT，不寫死：寫死會在下一次 Copy-on-Evolve 之後靜默指向凍結面
    （＝掃描面塌掉而判準照樣綠），那正是本面要防的失明形態本身。
    """
    try:
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
        from sdd_latest import resolve_latest_root  # type: ignore[import-not-found]

        return resolve_latest_root(_REPO_ROOT / "AISDLC_SDD") / ".claude" / "hooks"
    except Exception:  # noqa: BLE001 — 解不出來一律降級成 skip，不得假綠
        return None


def _console_spawn_offenders(hook_dir: Path | None = None) -> list[str]:
    """某一棵 hook 樹內**會配 console 視窗**的 spawn 站點（預設 `AutoClaude/tools/hooks/`）。

    判準只判「argv[0] 不是 `sys.executable`」那些：本目錄的 hook 由 exec form 的
    `pythonw.exe`（GUI 子系統、無 console）啟動，所以 `sys.executable` 本身也是
    `pythonw.exe` ⇒ 拿它去 spawn 不會配視窗；但外部 console 執行檔（`git.exe`）會被
    OS **配一個新 console**。刻意不判 `sys.executable` 那一族＝刻意不製造假紅。
    """
    offenders: list[str] = []
    for path in sorted((hook_dir or _AC_HOOK_DIR).glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                    and func.value.id == "subprocess" and func.attr in _SPAWN_ATTRS):
                continue
            argv = ast.unparse(node.args[0]) if node.args else ""
            if "sys.executable" in argv:
                continue
            if not any(kw.arg == "creationflags" for kw in node.keywords):
                offenders.append(f"{path.name}:{node.lineno} {func.attr}({argv[:60]})")
    return offenders


class TestAutoClaudeHookSpawnsAreConsoleFree(unittest.TestCase):
    """🔴 R84 訴求 7／C1：exec form 治掉載具的彈窗之後，**載具生的孫子還在彈**。

    立案事實：`AutoClaude/tools/hooks/check_sh_eol.py::_run_git` 對 `git.exe` 的
    `subprocess.run` 沒有 `CREATE_NO_WINDOW`。父行程是 `pythonw.exe`（GUI 子系統、
    **沒有 console**），Windows 在這種情況下會替 console 子系統的 child **配一個新
    console 視窗** ⇒ 每次 Write／Edit 到 `.sh` 就閃一次。`.claude/hooks/` 那一棵樹早有
    判準看著（`ConsoleFreeSpawnTest`），`AutoClaude/tools/hooks/` 這一棵**一個都沒有**。
    """

    def test_no_console_spawning_site_remains(self) -> None:
        offenders = _console_spawn_offenders()
        self.assertEqual(
            offenders, [],
            "這些 spawn 站點會在 Windows 上替 hook 配一個 console 視窗（父行程是 "
            "pythonw.exe、無 console）——請加 "
            "`creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)`"
            f"（POSIX 上兜底成 0，跨平台無副作用）：{offenders}")

    def test_the_scan_face_is_not_vacuous(self) -> None:
        """反空轉：掃描面塌成空的話上一格恆綠（R80 已實測過這個失明形態）。"""
        self.assertTrue(list(_AC_HOOK_DIR.glob("*.py")), f"{_AC_HOOK_DIR} 掃不到任何 .py")
        found = [
            f"{p.name}:{n.lineno}"
            for p in sorted(_AC_HOOK_DIR.glob("*.py"))
            for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
            and n.func.attr in _SPAWN_ATTRS
        ]
        self.assertTrue(found, "這棵樹一個 subprocess spawn 站點都掃不到 ⇒ 判準空轉")

    def test_the_sdd_latest_hook_tree_is_covered_too(self) -> None:
        """🔴 R88／DEF-200-104：**第三個掃描面**＝SDD LATEST 的 `.claude/hooks/`。

        立案（R85／P4 提出、R88 修）：前兩個掃描面是 `.claude/hooks/` 與
        `AutoClaude/tools/hooks/`，而 SDD LATEST 那一棵樹**一個判準都看不到**——當回合
        AST 實查有 3 個裸 `subprocess.check_output(["git", ...])`（`closure_evidence_
        verify.py` 1 個、`post_commit_drift.py` 2 個）。它們是真的會跑的：SDD 框架的
        hook 掛在版本目錄下，以 LATEST 為 cwd 開 session 是常態（同 R84 對
        `FROZEN_SETTINGS_PREFIX` 下過的判決——把活躍面排除在普查外＝假的安心）。

        🔴 LATEST 走 SSOT 現查（`tools/lib/sdd_latest.resolve_latest_root`），**不寫版號**：
        寫死版號會在下一次 Copy-on-Evolve 時靜默指向凍結面，而那正是本列要防的失明。
        """
        sdd_hooks = _sdd_latest_hook_dir()
        if sdd_hooks is None or not list(sdd_hooks.glob("*.py")):
            self.skipTest("[TOOL-ABSENCE] 解不出 SDD LATEST 或該樹無 hook ⇒ 量不到 ≠ 量到合格")
        self.assertEqual(
            _console_spawn_offenders(sdd_hooks), [],
            "SDD LATEST hook 樹有 spawn 站點會在 Windows 配 console 視窗——"
            "請加 `creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)`")

    def test_the_sdd_scan_face_is_not_vacuous(self) -> None:
        """反空轉：SDD 那一面塌成空的話上一格恆綠（同本檔既有慣例）。"""
        sdd_hooks = _sdd_latest_hook_dir()
        if sdd_hooks is None:
            self.skipTest("[TOOL-ABSENCE] 解不出 SDD LATEST")
        found = [
            f"{p.name}:{n.lineno}"
            for p in sorted(sdd_hooks.glob("*.py"))
            for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
            and n.func.attr in _SPAWN_ATTRS
        ]
        self.assertTrue(found, "SDD LATEST hook 樹一個 spawn 站點都掃不到 ⇒ 判準空轉")

    def test_removing_the_flag_turns_it_red(self) -> None:
        """合成注入（不動磁碟）：同一支判準函式餵一段拔掉 creationflags 的原始碼必紅。"""
        source = (
            "import subprocess\n"
            "def f(args):\n"
            "    return subprocess.run(['git', *args], capture_output=True)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe_hook.py"
            probe.write_text(source, encoding="utf-8")
            hits = [
                node.lineno
                for node in ast.walk(ast.parse(probe.read_text(encoding="utf-8")))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and node.func.attr in _SPAWN_ATTRS
                and not any(kw.arg == "creationflags" for kw in node.keywords)
            ]
            self.assertEqual(hits, [3], "判準對「拔掉旗標」這個形態沒有牙")
        # 綠向：加回旗標之後同一段程式碼不再命中。
        fixed = source.replace(
            "capture_output=True",
            "capture_output=True, creationflags=getattr(subprocess, 'X', 0)")
        self.assertEqual(
            [n.lineno for n in ast.walk(ast.parse(fixed))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
             and n.func.attr in _SPAWN_ATTRS
             and not any(kw.arg == "creationflags" for kw in n.keywords)], [])


_NIGHTLY_INSTALLER = _REPO_ROOT / "tools" / "install_windows_nightly.ps1"
#: schtasks Action 的載具行：`New-ScheduledTaskAction -Execute 'powershell.exe' … -Argument "…"`。
#: 反引號續行 ⇒ 判準以「整支檔」為單位切出每一個 Action 的 `-Argument` 字串。
_ACTION_RE = re.compile(
    r"New-ScheduledTaskAction\s+-Execute\s+'powershell\.exe'\s*`?\s*\n?\s*"
    r"-Argument\s+\"([^\"]*)\"")


class TestSentinelDriftCriterion(unittest.TestCase):
    """R84／C3-P5：`tools/check_scheduled_task_drift.py --sentinels` 的純函式判準。

    🔴 只判載具、`LogonType` 只回報不判紅——理由寫在 `sentinel_problems()` 的 docstring
    裡（S4U 需提權、哨兵武裝路徑一律非提權 ⇒ 判紅＝永紅閘門＝被整個關掉）。本類同時
    釘住「不判」這一半：把它判紅是一種很容易被當成「更嚴格」而加進來的退化。
    """

    @staticmethod
    def _drift():
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import check_scheduled_task_drift  # noqa: PLC0415 — 工具不在 import 面，隨用隨載
        return check_scheduled_task_drift

    def test_a_gui_carrier_passes(self) -> None:
        mod = self._drift()
        self.assertEqual(mod.sentinel_problems(
            {"Actions/Exec/Command": r"D:\repo\.venv\Scripts\pythonw.exe",  # platform-ok: XML 語料
             "Principals/Principal/LogonType": "InteractiveToken"}), [])

    def test_a_console_carrier_is_flagged(self) -> None:
        """注入①：載具退回 console 版 ⇒ 必紅（這正是彈窗的來源）。"""
        mod = self._drift()
        self.assertTrue(mod.sentinel_problems(
            {"Actions/Exec/Command": r"D:\repo\.venv\Scripts\python.exe"}))  # platform-ok: XML 語料

    def test_an_unreadable_carrier_is_not_read_as_ok(self) -> None:
        """注入②：欄位讀不到 ⇒ 必紅（量不到 ≠ 量到零）。"""
        self.assertTrue(self._drift().sentinel_problems({}))

    def test_an_interactive_logon_type_alone_is_never_a_failure(self) -> None:
        """🔴 反向釘：非提權回退是合法的，只要載具對就不准紅。"""
        mod = self._drift()
        for logon in ("InteractiveToken", "S4U", "Password"):
            with self.subTest(logon=logon):
                # 載具字串是 Task XML 的**內容**（Windows 產出、原樣比對），不是由
                # `Path` 算出來的路徑 ⇒ 這裡不會有「Windows 渲染成反斜線」那個問題。
                self.assertEqual(mod.sentinel_problems(  # posix-abs-ok: Task XML 語料
                    {"Actions/Exec/Command": "/x/.venv/Scripts/pythonw.exe",
                     "Principals/Principal/LogonType": logon}), [])


#: 全庫排程 Action 的載具行（`.ps1` 的 cmdlet 形態 ＋ `.py` 內插出那一行的字串形態）。
_ANY_ACTION_RE = re.compile(r"New-ScheduledTaskAction\s+-Execute\s+(\S+)")
#: 會**配置 console** 的載具。名單刻意只列這四個：它們是本 repo 真的會拿來當 Action 的
#: 那幾支，把「所有 .exe」一起判會製造要逐一辯護的假紅（本 repo 判過那種鎖活不過一輪）。
_CONSOLE_CARRIERS = ("powershell.exe", "pwsh.exe", "cmd.exe", "python.exe")
#: GUI 子系統載具的**字面**形態。非字面（內插）那一半由 `quiet_python` 這個符號認證，
#: 理由見 `test_the_repo_wide_criterion_knows_the_gui_carrier_symbol`。
_GUI_CARRIER_LITERAL = "pythonw.exe"
_GUI_CARRIER_SYMBOL = "quiet_python"
_ACTION_EXEMPT_RE = re.compile(r"#\s*no-window-ok:\s*(\S.*)$")
#: 掃描面：活躍的 `.ps1`／`.py`。`.md` 一律不掃——文件裡的指令是給人讀的說明，
#: 判它就是要求文件與程式碼用同一組判準，而那會把「說明一個危險形態」也判成違規。
_ACTION_SCAN_TREES = ("tools", ".claude", "AutoClaude/tools")
#: 🔴 `tools/tests/` 排除在外，理由是**鑑別力**不是方便：上面那幾條合成注入自證的
#: 語料本身就是「沒帶 Hidden 的 Action 字面」，把測試樹掃進來時本判準會抓到自己的
#: 語料（實測 3 筆，全部來自本檔的注入 fixture）——一支會對自己的語料轉紅的掃描器
#: 只有兩種下場：注入自證被拿掉，或整支鎖被關掉。同 `_decommented` 那一段的判例
#: （掃描器把說明文字當程式碼），只是這次那段文字是測試資料。
#: 誠實劃界：測試樹裡若真的有人寫出一個會註冊到真排程器的 console Action，本判準看不到；
#: 那一族由 `test_context_budget_guard.setUpModule`（整模組禁真排程器）擋，不是靠本鎖。
_ACTION_SCAN_EXCLUDE = ("tools/tests/",)


def _decommented(text: str, suffix: str) -> str:
    """把註解換成等長空白（行號與行結構不變，才對得回原始行）。

    `.ps1` 的 `<# … #>` 區塊與 `#` 行註解都要剝：`AutoClaude/tools/run_local_nightly.ps1`
    的 `.NOTES` 區塊裡就有一段**示範用**的 `schtasks /create`，不剝的話它是本判準唯一
    的假紅——而它是一段給人看的說明，不是會被執行的東西。
    """
    if suffix == ".ps1":
        text = re.sub(r"<#.*?#>", lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                      text, flags=re.S)
    return "\n".join(line.split("#", 1)[0] if line.lstrip().startswith("#") else line
                     for line in text.splitlines())


def scheduled_action_sites(sources: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """全庫的排程 Action 站點 → `[(檔名, 那一行原文)]`（註解內的不算）。"""
    if sources is None:
        sources = _action_scan_sources()   # 掃描面只有一個家，兩個各自 rglob 會漂
    out: list[tuple[str, str]] = []
    for rel, text in sources.items():
        suffix = ".ps1" if rel.endswith(".ps1") else ".py"
        scrubbed = _decommented(text, suffix)
        raw_lines = text.splitlines()
        for idx, line in enumerate(scrubbed.splitlines()):
            if _ANY_ACTION_RE.search(line):
                out.append((rel, raw_lines[idx] if idx < len(raw_lines) else line))
    return out


#: 內插載具裡那個變數名：`{python}`（f-string）／`$var`／`$($var)`（PowerShell）。
_CARRIER_NAME_RE = re.compile(r"[{$]\(?\$?\s*([A-Za-z_][A-Za-z0-9_]*)")


def _certified_carrier_names(text: str, suffix: str) -> set[str]:
    """該檔內**賦值來源含 `quiet_python`** 的變數名 ＝ 站點級白名單。

    🔴 R84／SD-05：舊判準是 `_GUI_CARRIER_SYMBOL in text` ——那是**整檔通行證**，只要
    檔案裡任何地方（連註解）出現過 `quiet_python` 這七個字，該檔所有內插載具一律放行。
    實測注入：只在**註解**提到它 ＋ 一個內插出 `powershell.exe` 的 Action ⇒ **0 筆命中**，
    而 `windowless_action_problems` 自己的 docstring 分支③ 逐字寫著「白名單不得變成
    萬用通行證」⇒ 宣稱射程 ≠ 實作射程。這比沒有鎖更難看見：檔案在、判準在、測試全綠。

    `.py` 走 AST：註解結構上不可能出現在 `ast.Assign.value` 裡 ⇒「註解不得認證」是
    **性質**，不是靠剝註解的正則去逼近（`_decommented` 對 `.py` 只剝整行註解，行尾註解
    照樣留著，用它會把同一個洞縮小而不是關掉）。`.ps1` 沒有現成 parser，退回「剝過註解
    的行首賦值」比對。
    誠實劃界：只追**一層**賦值——`x = _q(guard.quiet_python())` 認得，
    `a = quiet_python(); x = a` 不認得（會判紅）。今日全庫唯一的內插站點是前者；
    追賦值鏈要的是資料流分析，射程遠大於本輪，且假紅方向是安全的那一邊。
    """
    names: set[str] = set()
    if suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                    continue
                if _GUI_CARRIER_SYMBOL not in ast.unparse(node.value):
                    continue
                targets = (node.targets if isinstance(node, ast.Assign) else [node.target])
                names |= {t.id for t in targets if isinstance(t, ast.Name)}
            return names
    for line in _decommented(text, suffix).splitlines():
        assigned = re.match(r"\s*\$?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", line)
        if assigned and _GUI_CARRIER_SYMBOL in assigned.group(2):
            names.add(assigned.group(1))
    return names


def windowless_action_problems(sources: dict[str, str] | None = None) -> list[str]:
    """哪些排程 Action 起的是 console 載具卻沒有藏視窗。純函式判準。

    判準三分支：① console 載具 → 必須有 `-WindowStyle Hidden`（同一行或緊接的續行）；
    ② GUI 載具（字面 `pythonw.exe`，或內插自**該站點那個變數**、而它的賦值來源是
    `quiet_python()`）→ 放行；③ 其他內插／來路不明 → **判紅**（白名單不得變成萬用
    通行證——R84／SD-05 之前這句話只寫在這裡，實作放行的是整個檔案）。
    行尾 `# no-window-ok: <理由>` 是逃生口，理由留空無效。
    """
    if sources is None:
        sources = dict(_action_scan_sources())
    problems: list[str] = []
    for rel, text in sources.items():
        suffix = ".ps1" if rel.endswith(".ps1") else ".py"
        certified = _certified_carrier_names(text, suffix)
        scrubbed = _decommented(text, suffix).splitlines()
        raw = text.splitlines()
        for idx, line in enumerate(scrubbed):
            found = _ANY_ACTION_RE.search(line)
            if not found:
                continue
            # Action 常以反引號／字串串接跨行 ⇒ 判準看「這一行起算的 4 行」這個窗。
            window_raw = "\n".join(raw[idx:idx + 4])
            excused = _ACTION_EXEMPT_RE.search(window_raw)
            if excused:
                continue
            carrier = found.group(1)
            if any(name in carrier for name in _CONSOLE_CARRIERS):
                if "-WindowStyle Hidden" not in "\n".join(scrubbed[idx:idx + 4]):
                    problems.append(
                        f"{rel}:{idx + 1} 排程 Action 的載具是 console 的 {carrier}，"
                        "S4U 漂成 InteractiveToken 時會畫出視窗 ⇒ 請補 -WindowStyle Hidden "
                        "或行尾具名豁免 `# no-window-ok: <理由>`")
            else:
                # 站點級：這個載具是**哪個變數**內插出來的，那個變數的賦值來源才算數。
                interpolated = set(_CARRIER_NAME_RE.findall(carrier))
                if _GUI_CARRIER_LITERAL in carrier or (
                        interpolated and interpolated <= certified):
                    continue
                problems.append(
                    f"{rel}:{idx + 1} 排程 Action 的載具 {carrier} 既不是字面 "
                    f"{_GUI_CARRIER_LITERAL}、也不是由 {_GUI_CARRIER_SYMBOL}() 算出來的 ⇒ "
                    "無法判斷它會不會配置 console。請走載具 SSOT 或具名豁免")
    return problems


def _action_scan_sources() -> dict[str, str]:
    """掃描面的實體（與 `scheduled_action_sites` 共用同一份 tree 清單）。"""
    out: dict[str, str] = {}
    for tree in _ACTION_SCAN_TREES:
        base = _REPO_ROOT / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            rel = str(path.relative_to(_REPO_ROOT)).replace("\\", "/")
            if (path.suffix in (".ps1", ".py") and "__pycache__" not in path.parts
                    and not rel.startswith(_ACTION_SCAN_EXCLUDE)):
                out[rel] = path.read_text(encoding="utf-8", errors="replace")
    return out


class TestNightlyTaskActionsAreWindowless(unittest.TestCase):
    """🔴 R84 訴求 7／B1-B2：schtasks 的兩支 Action 是 console 的 `powershell.exe`。

    第一層防護是 `LogonType=S4U`（無互動桌面 ⇒ 本來就看不到），但那一層**已經被實測
    證明會漂**：`tools/scheduled_task_expectations.json` 的 `_why` 逐字記載 smoke 任務的
    LogonType 曾漂成 `InteractiveToken` **連三輪**，而漂掉的那三輪正是使用者會看到彈窗
    的那三輪。`-WindowStyle Hidden` 是與它獨立的第二層。

    🔴 誠實劃界：本輪**無 Windows 真機** ⇒ 本類守的是「這兩行寫進去了、而且不准有人拿
    掉」，**不是**「彈窗真的消失了」。後者要真機才驗得到。
    """

    def setUp(self) -> None:
        self.text = _NIGHTLY_INSTALLER.read_text(encoding="utf-8")
        self.actions = _ACTION_RE.findall(self.text)

    def test_the_scan_face_is_not_vacuous(self) -> None:
        self.assertEqual(len(self.actions), 2,
                         f"預期抓到 nightly／smoke 兩支 Action，實得 {self.actions}")

    def test_every_action_hides_its_window(self) -> None:
        missing = [a for a in self.actions if "-WindowStyle Hidden" not in a]
        self.assertEqual(
            missing, [],
            "schtasks Action 起的是 console 子系統的 powershell.exe，S4U 漂成 "
            f"InteractiveToken 時會畫出視窗（實測連三輪）——請補 -WindowStyle Hidden：{missing}")

    def test_the_criterion_catches_a_stripped_flag(self) -> None:
        """合成注入：把旗標拿掉 ⇒ 必紅（證明上一格不是因為 regex 抓不到而恆綠）。"""
        stripped = _ACTION_RE.findall(self.text.replace(" -WindowStyle Hidden", ""))
        self.assertEqual(len(stripped), 2, "注入後 regex 就抓不到了 ⇒ 判準沒有牙")
        self.assertEqual([a for a in stripped if "-WindowStyle Hidden" in a], [])

    # ── R84／C3-B：同一個性質，掃描面由「這一支安裝器」擴到全庫 ──────────────
    # 🔴 立案：上面三格守的是 `tools/install_windows_nightly.ps1` **這一個檔**，而排程
    # Action 是一個**任何人都可以再開一個**的東西——本輪就實測到第二個家
    # （`tools/session_resume_planner.py` 的哨兵註冊腳本）。射程由一份手寫路徑決定時，
    # 分母由記憶決定；這正是 R82 漏掉 `quota_meter.py` 的同一個形狀。
    def test_every_scheduled_task_action_in_the_repo_is_windowless(self) -> None:
        problems = windowless_action_problems()
        self.assertEqual(problems, [], "；".join(problems))

    def test_the_repo_wide_criterion_is_not_vacuous(self) -> None:
        """反空轉：掃描面必須真的抓到站點，否則上一格是恆綠的。"""
        self.assertGreaterEqual(len(scheduled_action_sites()), 3,
                                "全庫排程 Action 站點少於 3 個 ⇒ 掃描面塌掉了")

    def test_the_repo_wide_criterion_catches_a_console_carrier(self) -> None:
        """合成注入①：console 載具沒帶 Hidden ⇒ 必紅。"""
        bad = {"x.ps1": "$a = New-ScheduledTaskAction -Execute 'powershell.exe' "
                        "-Argument \"-NoProfile -File x.ps1\"\n"}
        self.assertTrue(windowless_action_problems(bad))
        good = {"x.ps1": "$a = New-ScheduledTaskAction -Execute 'powershell.exe' "
                         "-Argument \"-NoProfile -WindowStyle Hidden -File x.ps1\"\n"}
        self.assertEqual(windowless_action_problems(good), [])

    def test_the_repo_wide_criterion_knows_the_gui_carrier_symbol(self) -> None:
        """🔴 合成注入②：非字面載具（`'{python}'`）必須認得 `quiet_python()` 這個**符號**。

        只找字面 `pythonw.exe` 會讓 `tools/session_resume_planner.py` 成為**唯一一筆假紅**
        ——它的 `-Execute` 是內插出來的，值來自 `guard.quiet_python()`（載具那一層的唯一
        真相源）。而假紅不是「比較嚴格」：一筆要逐輪辯護的假紅足以讓這支鎖被關掉。
        同時**不放行**任何其他來路不明的內插——那才是真的失明。
        """
        via_symbol = {"p.py": "python = _q(guard.quiet_python())\n"
                              "s = f\"New-ScheduledTaskAction -Execute '{python}' \"\n"}
        self.assertEqual(windowless_action_problems(via_symbol), [])
        unknown = {"p.py": "s = f\"New-ScheduledTaskAction -Execute '{whatever}' \"\n"}
        self.assertTrue(windowless_action_problems(unknown),
                        "來路不明的內插載具被放行 ⇒ 白名單變成萬用通行證")

    def test_the_gui_whitelist_is_per_site_not_a_whole_file_pass(self) -> None:
        """🔴 R84／SD-05：白名單是**站點級**的——提到 `quiet_python` 不等於認證了它。

        修前的判準是 `_GUI_CARRIER_SYMBOL in text`（整檔），實測注入：只在**註解**裡提到
        它、另外寫一個內插出 `powershell.exe` 的 Action ⇒ **0 筆命中**。而 console 載具
        混在內插裡正是這一族最難看見的形態（第一分支的字面比對看不到它）。
        `.ps1` 一併驗：兩種副檔名走的是不同的認證路徑（AST／剝註解後的行首賦值），
        只驗一種等於另一種沒有人守。
        """
        for label, only_comment, certified in (
            (".py", {"p.py": "# 我們的做法是 quiet_python()\n"
                             "ps = 'powershell.exe'\n"
                             "s = f\"New-ScheduledTaskAction -Execute '{ps}' \"\n"},
             {"p.py": "ps = _q(guard.quiet_python())\n"
                      "s = f\"New-ScheduledTaskAction -Execute '{ps}' \"\n"}),
            (".ps1", {"x.ps1": "# quiet_python\n$exe = 'powershell.exe'\n"
                               "$a = New-ScheduledTaskAction -Execute $exe\n"},
             {"x.ps1": "$exe = quiet_python\n"
                       "$a = New-ScheduledTaskAction -Execute $exe\n"}),
        ):
            with self.subTest(kind=label):
                self.assertTrue(windowless_action_problems(only_comment),
                                "註解裡提一句就發了整檔通行證 ⇒ 宣稱射程 ≠ 實作射程")
                self.assertEqual(windowless_action_problems(certified), [],
                                 "真的由 quiet_python() 賦值的站點被判紅 ⇒ 這是假紅，"
                                 "而一筆要逐輪辯護的假紅足以讓整支鎖被關掉")

    def test_the_per_site_whitelist_does_not_manufacture_false_reds(self) -> None:
        """假紅實量：全庫現存的排程 Action 站點在收窄之後必須仍是 0 problems。

        收窄判準最貴的失敗方式不是漏抓，是把今天正確的東西判紅——本 repo 明文判過
        「擋到讓人無法工作的守衛會被整個關掉」。故這一格與上面那格必須成對存在。
        """
        self.assertEqual(windowless_action_problems(), [])
        self.assertGreaterEqual(len(scheduled_action_sites()), 3, "掃描面塌了 ⇒ 上一格恆綠")

    def test_the_repo_wide_criterion_honours_a_named_exemption(self) -> None:
        """行尾 `# no-window-ok: <理由>` 放行；**理由留空無效**（同 ConsoleFreeSpawn 體例）。"""
        excused = {"x.ps1": "New-ScheduledTaskAction -Execute 'cmd.exe' "
                            "-Argument \"/c z\"  # no-window-ok: 要給人看的 TUI\n"}
        self.assertEqual(windowless_action_problems(excused), [])
        bare = {"x.ps1": "New-ScheduledTaskAction -Execute 'cmd.exe' "
                         "-Argument \"/c z\"  # no-window-ok:\n"}
        self.assertTrue(windowless_action_problems(bare))


# ─────────────────────────────────────────────────────────────────────────────
# 執行期證據（本輪 M9）：靜態那三道看不到的那一格
# ─────────────────────────────────────────────────────────────────────────────

#: 本機全母體實測到的那 217 筆失敗的**逐字形狀**（去識別化：把家目錄換成假路徑）。
#: 它在本組裡當**綠色對照**用：跨平台配對刻意的 fail-open 必須判成「不是缺陷」，
#: 否則判準會在 mac 上每一次 hook 都響一次，而那是本 repo 判過的「永遠在響＝沒有警報」。
_ALIEN_CARRIER_ENOENT = {
    "type": "hook_non_blocking_error", "hookEvent": "Stop", "exitCode": 1,
    "stderr": "Failed with non-blocking status code: Error occurred while executing "
              "hook command: ENOENT: no such file or directory, posix_spawn "
              "'/fake/repo/.venv/Scripts/pythonw.exe'",
    "command": "${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe "
               "${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py "
               ".claude/hooks/check_claim_provenance.py",
}

#: 同一件事的**真**失效：本平台自己那條載具沒跑起來。這一筆與上面那筆在螢幕上的表徵
#: 完全相同（都是一行 ERROR、工具照跑），差別只在 `command` 指的是哪一種載具。
_NATIVE_CARRIER_EACCES = {
    "type": "hook_non_blocking_error", "hookEvent": "PreToolUse", "exitCode": 1,
    "stderr": "EACCES: permission denied, posix_spawn "
              "'/fake/repo/.claude/hooks/_hook_launcher.py'",
    "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py "
               ".claude/hooks/block_destructive_git.py",
}


class TestRuntimeCarrierEvidenceIsRead(unittest.TestCase):
    """🔴 **立案：這一格此前完全沒有人守，而它沉默了九天。**

    立案的普查數字與「三道既有機械物為何一條都沒說話」的逐條對號，**唯一真相源＝
    `tools/lib/hook_wiring.py` 的〈執行期證據〉區塊註解**（本檔刻意不複寫：那些數字是量測
    值，抄第二份就會漂移，而只有一份會被改）。現查：
    `grep -n hook_non_blocking_error tools/lib/hook_wiring.py`

    本組守的是**判準本體**（純函式、合成輸入、紅綠雙向）。**刻意不斷言機器狀態**：本機
    此刻有幾筆 by-design 失敗是量測值，寫進斷言會讓這道鎖在別台機器上假紅。真正會讀本機
    證據的是 `.claude/hooks/check_claim_provenance.py`（見下一組）。
    """

    def test_the_by_design_cross_platform_failure_is_not_reported_as_a_defect(self) -> None:
        """綠色對照：那 217 筆必須全部判成「不是缺陷」，只被**數**起來。"""
        wiring = _hook_wiring()
        problems, counts = wiring.runtime_carrier_verdict(
            [_ALIEN_CARRIER_ENOENT] * 19, on_windows=False)
        self.assertEqual(problems, [],
                         "跨平台配對的 fail-open 被判成缺陷 ⇒ 這道判準在 mac 上每次都響")
        self.assertEqual(counts["by_design_fail"], 19,
                         "噪音底線必須是**可數的**：九天沒人發現的機制就是它沒有數字")
        self.assertEqual(counts["native_fail"], 0)

    def test_the_native_carrier_failure_is_reported(self) -> None:
        """紅：同一種螢幕表徵，但失敗的是本平台自己那條 ⇒ 那個 hook 真的沒跑。"""
        wiring = _hook_wiring()
        problems, counts = wiring.runtime_carrier_verdict(
            [_ALIEN_CARRIER_ENOENT, _NATIVE_CARRIER_EACCES], on_windows=False)
        self.assertEqual(counts["native_fail"], 1)
        self.assertEqual(counts["by_design_fail"], 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("block_destructive_git.py", problems[0],
                      "必須指名是**哪一支守衛**沒跑，否則讀者無從行動")

    def test_the_same_evidence_flips_when_the_platform_flips(self) -> None:
        """同一份證據在 Windows 上判反過來——判準必須是平台的函式，不是硬編一條載具。

        沒有這一條，`native`／`by_design` 的分類可以靠「永遠把 pythonw 當外平台」通過，
        而那正是 `carrier_liveness_problems()` 只綁一半的病（DEF-101-766：單平台判準
        不可無條件外推）。
        """
        wiring = _hook_wiring()
        problems, counts = wiring.runtime_carrier_verdict(
            [_ALIEN_CARRIER_ENOENT, _NATIVE_CARRIER_EACCES], on_windows=True)
        self.assertEqual(counts["native_fail"], 1)
        self.assertIn("check_claim_provenance.py", problems[0],
                      "Windows 上該轉紅的是 pythonw 那條")

    def test_a_carrier_the_repo_does_not_recognise_is_also_a_defect(self) -> None:
        """有人把條目退回 `python -c …`／換了載具 ⇒ 形態判準看不到「實際跑的是別的東西」。"""
        wiring = _hook_wiring()
        problems, counts = wiring.runtime_carrier_verdict([{
            "type": "hook_non_blocking_error", "hookEvent": "PostToolUse",
            "command": "python -c import runpy .claude/hooks/x.py"}], on_windows=False)
        self.assertEqual(counts["alien_fail"], 1)
        self.assertTrue(problems)

    def test_successes_are_counted_but_never_treated_as_coverage(self) -> None:
        """🔴 `hook_success` **只有在 hook 真的印字時才落盤**（本機全母體 11,438 筆 success
        逐筆檢查，stdout／stderr 兩者皆空 **0 筆**；其中只有 14 筆屬於根層 hook，其餘全是
        會固定印字的 SDD 三支）⇒ 「某個目標零 success」**不能**當成「它沒跑起來」。

        這一條釘的就是那個界線：success 只准進計數欄，不准變成任何「缺席即紅」的判準——
        否則每一支安靜的守衛都會被判成沒跑，而那是假紅方向。
        """
        wiring = _hook_wiring()
        problems, counts = wiring.runtime_carrier_verdict([{
            "type": "hook_success", "hookEvent": "Stop", "exitCode": 0,
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/_hook_launcher.py "
                       ".claude/hooks/check_claim_provenance.py"}], on_windows=False)
        self.assertEqual(counts["success"], 1)
        self.assertEqual(problems, [])

    def test_only_hook_result_attachments_are_picked_up(self) -> None:
        """逐字稿裡絕大多數記錄與 hook 無關；挑錯了會把別的東西餵進判準。"""
        wiring = _hook_wiring()
        records = [{"type": "user", "message": {"role": "user"}},
                   {"type": "system", "attachment": {"type": "todo_changed"}},
                   {"type": "system", "attachment": _ALIEN_CARRIER_ENOENT}]
        self.assertEqual(wiring.hook_result_attachments(records),
                         [_ALIEN_CARRIER_ENOENT])
        self.assertEqual(wiring.hook_result_attachments([None, "x", 3]), [])


class TestTheStopGuardIsTheAutomaticReaderOfThatEvidence(unittest.TestCase):
    """M9 的另一半：判準有了，**還要有人自動去讀**，否則同樣不是機制。

    選 Stop 那支守衛當讀者不是順手：它是全 repo 唯一「每一則回覆都會跑、而且手上已經
    有逐字稿」的地方 ⇒ 讀這份證據對它是零額外成本。誠實劃界：它只出聲、不阻斷，也不會
    讓任何閘門轉紅。
    """

    # R100：真子行程無 on_windows 注入接縫，native／alien 隨真實 os.name 而定。
    _SPEAKS_FIXTURE, _SILENT_FIXTURE, _SPEAKS_TARGET = (
        (_ALIEN_CARRIER_ENOENT, _NATIVE_CARRIER_EACCES, "check_claim_provenance.py")
        if os.name == "nt" else
        (_NATIVE_CARRIER_EACCES, _ALIEN_CARRIER_ENOENT, "block_destructive_git.py"))

    def test_the_stop_guard_speaks_when_the_native_carrier_failed(self) -> None:
        hook = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "t.jsonl"
            transcript.write_text("\n".join(json.dumps(r) for r in [
                {"type": "system", "attachment": self._SPEAKS_FIXTURE},
                {"type": "system", "attachment": self._SILENT_FIXTURE}]) + "\n",
                encoding="utf-8")
            payload = json.dumps({"hook_event_name": "Stop", "stop_hook_active": False,
                                  "last_assistant_message": "收工。",
                                  "transcript_path": str(transcript)})
            done = subprocess.run([sys.executable, str(hook)], input=payload,
                                  capture_output=True, text=True, timeout=60,
                                  env={**os.environ, "AUTOSDD_TRACE_DIR": tmp},
                                  encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0, "本守衛永不阻斷")
        self.assertIn(self._SPEAKS_TARGET, done.stderr,
                      "本平台自己那條載具失敗，這支讀者沒說話 ⇒ 證據又回到零讀者狀態")
        self.assertIn("hookSpecificOutput", done.stdout,
                      "只寫 stderr 等於沒說（exit 0 的 stderr 不進模型 context）")

    def test_the_by_design_failure_alone_keeps_the_stop_guard_quiet(self) -> None:
        """紅綠自證的另一半：只有跨平台那條失敗時**必須完全安靜**。

        缺這一條，上一條可以靠「永遠出聲」通過，而那支守衛在 mac 上會對每一則回覆都響。
        """
        hook = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "t.jsonl"
            transcript.write_text(json.dumps(
                {"type": "system", "attachment": self._SILENT_FIXTURE}) + "\n",
                encoding="utf-8")
            payload = json.dumps({"hook_event_name": "Stop", "stop_hook_active": False,
                                  "last_assistant_message": "收工。",
                                  "transcript_path": str(transcript)})
            done = subprocess.run([sys.executable, str(hook)], input=payload,
                                  capture_output=True, text=True, timeout=60,
                                  env={**os.environ, "AUTOSDD_TRACE_DIR": tmp},
                                  encoding="utf-8", errors="replace")
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stderr.strip(), "",
                         "跨平台配對的 fail-open 讓守衛出聲了 ⇒ 它會變成每次都響的噪音")


if __name__ == "__main__":
    unittest.main()
