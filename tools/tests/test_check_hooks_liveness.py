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


def _run_hook(stdin_text: str, *, force_os_name: str | None = None) -> tuple[int, str]:
    """以子行程真跑 hook，回 `(rc, stderr)`。

    刻意走子行程而非 import + monkeypatch：hook 的契約是「被 Claude Code 以獨立行程
    呼叫、讀 stdin、以 exit code 表態」，import 進來直接呼叫 `main()` 會繞過
    `sys.stdin` 與 exit code 這兩個契約面（本 repo 有「驗證載具必須對齊 production
    真正執行路徑」的既有紀律）。

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
    )
    return proc.returncode, proc.stderr or ""


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

    def test_malformed_json_fails_closed(self) -> None:
        """壞 JSON ⇒ 仍阻斷。fail-**closed** 是刻意方向：讀不懂輸入時，
        放行等於讓「送壞 payload」成為繞過守衛的免費手段。"""
        rc, _ = _run_hook("{ this is not json")
        self.assertEqual(rc, 2, "壞 JSON 必須 fail-closed（exit 2），不可放行")

    def test_empty_stdin_fails_closed(self) -> None:
        rc, _ = _run_hook("")
        self.assertEqual(rc, 2, "空 stdin 必須 fail-closed（exit 2）")


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


if __name__ == "__main__":
    unittest.main()
