#!/usr/bin/env python
"""`.claude/hooks/block_destructive_git.py` 的回歸鎖（R83）。

WHY 這支鎖存在：六包並行工作樹上的 `git stash` 真實事故——「禁令沒涵蓋到的那個
動詞，就是被踩的那個」。事故敘事原文＝CrossPlatform_R95_GovWrite_Evidence.md §6.1。

而這道守衛的價值**完全等於它判準的精準度**：repo 已判過「擋到讓人無法工作的守衛
會被整個關掉，而被關掉的守衛比沒有守衛更糟」。所以本檔的分量刻意壓在**放行面**：
`git stash create`（根 CLAUDE.md〈可重啟點四條件〉指定的保全手法）、
`git reset --soft`、純切分支、所有唯讀查詢——任何一條被擋到，這支鎖就要紅。

六個方向（交付要求逐條對應，缺一即不算紅綠自證）
------------------------------------------------
  ① 該擋的擋（`TestDestructiveFormsAreBlocked`）
  ② 不該擋的放行（`TestSafeFormsAreNotBlocked`／`TestQuotingAndHeredocAreInert`）
  ③ 退化 payload（`TestDegradedPayloadIsLoudButNotBlocking`）
  ④ 例外 fail-open（`TestUnexpectedExceptionFailsOpen`）
  ⑤ 逃生口（`TestEscapeHatches`）
  ⑥ 工具名在射程外就放行（`TestScopeIsNotWidened`）
另加註冊面（`TestHookIsActuallyRegistered`）——R80 的教訓：阻斷臂蓋好了卻圈到一組
這個 harness 不會發出的工具名，等於永遠不觸發，而所有單元測試照樣全綠。
"""

from __future__ import annotations

import ast
import json
import ntpath  # R96／B-8：Windows 路徑語意的**真實實作**，注入用（不是手捏的假貨）
import os
import posixpath  # DEF-200-238：posix 路徑語意的真實實作，注入用（同上，不是手捏的假貨）
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "block_destructive_git.py"
_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"

sys.path.insert(0, str(_HOOK.parent))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import block_destructive_git as G  # noqa: E402


def run_hook(payload: object, env: dict[str, str] | None = None,
             raw: str | None = None) -> subprocess.CompletedProcess[str]:
    """把 hook 當**真的 child 行程**起（不是 import 呼叫 main()）。

    刻意走 subprocess：production 路徑就是 `_hook_launcher.py` spawn 一支 python，
    而 rc 與 stderr 的可讀性（UTF-8 stdio 保護）只有在真的跨行程時才驗得到——
    import 呼叫會共用本測試行程已經設好的串流，那正是 DEF-101-789 漏掉的那一半。
    """
    stdin = raw if raw is not None else json.dumps(payload, ensure_ascii=False)
    child_env = dict(os.environ)
    # 逃生口是**繼承**來的：測試行程若剛好帶著它，被守的分支會整個不跑而恆綠。
    for key in (G.GUARD_OFF_ENV, G.UNATTENDED_ENV, G.GOVWRITE_OFF_ENV):
        child_env.pop(key, None)
    child_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=stdin, capture_output=True,
        text=True, encoding="utf-8", errors="replace", env=child_env,
        cwd=str(_REPO_ROOT), timeout=60)


def bash_payload(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# 🔴 模組級釘住：`is_foreign_tree()` 以 `CLAUDE_PROJECT_DIR`（缺席則 `os.getcwd()`）決定專案根；
# 呼叫者 cwd 落在 repo 外時 9 支同時變紅（本檔對 cwd 的隱含依賴，不是 hook 缺陷）。
# 史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§1。
_MODULE_ENV_PATCH = None


def setUpModule() -> None:
    global _MODULE_ENV_PATCH
    _MODULE_ENV_PATCH = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})
    _MODULE_ENV_PATCH.start()


def tearDownModule() -> None:
    if _MODULE_ENV_PATCH is not None:
        _MODULE_ENV_PATCH.stop()


# ── ① 該擋的擋 ─────────────────────────────────────────────────────────────
class TestDestructiveFormsAreBlocked(unittest.TestCase):
    """每一條都會**不可逆地改動工作樹內容**，一條都不許漏。"""

    #: 立案那一條逐字在列（`git stash -q -u --keep-index`）——鎖必須釘住真實事故形態，
    #: 而不是一個好寫測試的簡化版。
    BLOCKED = (
        "git stash",
        "git stash -q -u --keep-index",
        "git stash push -m wip",
        "git stash pop",
        "git stash apply stash@{0}",
        "git stash drop",
        "git stash clear",
        "git stash save wip",
        "git checkout -- tools/lib/quota_meter.py",
        "git checkout HEAD -- tools/lib/quota_meter.py",
        "git checkout .",
        "git restore tools/lib/quota_meter.py",
        "git restore --worktree tools/lib/quota_meter.py",
        "git restore --staged --worktree tools/lib/quota_meter.py",
        "git reset --hard",
        "git reset --hard HEAD~1",
        "git reset --merge",
        "git reset --keep",
        "git clean -fd",
        "git clean -fdx",
        "git clean",
        "git checkout -f main",
        "git switch -f main",
        "git switch --discard-changes main",
        # 🔴 R85／SD-B3：引號包住的執行檔絕對路徑，修前一條都不擋（立案敘事原文＝
        # GovWrite 證據檔 §6.9）。
        r"""& 'C:\Program Files\Git\bin\git.exe' stash""",  # platform-ok: 被測指令字面
        r"""& "C:\Program Files\Git\bin\git.exe" reset --hard""",  # platform-ok: 同上
        r"""'/usr/bin/git' stash""",          # mac 側同形（引號才是成因，不是碟符）
        r"""'/usr/local/bin/git' clean -fd""",
    )

    def test_every_destructive_form_is_blocked(self) -> None:
        for command in self.BLOCKED:
            with self.subTest(command=command):
                self.assertTrue(
                    G.destructive_git_hits(command),
                    f"{command!r} 會清掉工作樹內容卻被放行——這正是 R83 事故的形狀")

    def test_it_survives_command_composition(self) -> None:
        """真實指令不會是乾淨的單句：前面接 cd、包在 `$()` 裡、混在多句中。

        只看「段首第一個 token 是不是 git」的實作會全部漏掉，而漏掉的方向是靜默的。
        """
        for command in ("cd /tmp && git stash",
                        "sudo git stash",
                        "git -C /Users/x/repo stash",
                        "/usr/bin/git stash pop",
                        "git status; git stash",
                        "$(git stash)",
                        "git.exe reset --hard"):
            with self.subTest(command=command):
                self.assertTrue(G.destructive_git_hits(command), command)

    def test_end_to_end_child_process_returns_rc2_with_guidance(self) -> None:
        """端到端：真的起一支 child，rc 必須是 2（PreToolUse 的阻斷碼），且**要教**。

        只擋不教的守衛會被拔掉——訊息裡必須出現替代做法，否則被擋的人只能去關它。
        """
        proc = run_hook(bash_payload("git stash -q -u --keep-index"))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("git stash create", proc.stderr, "訊息沒給出替代做法")
        self.assertIn("git-guard-ok", proc.stderr, "訊息沒給出行內豁免出口")
        self.assertNotIn("\\u", proc.stderr,
                         "指引被逃脫成 \\uXXXX ⇒ UTF-8 stdio 保護沒生效（DEF-101-789）")

    def test_a_backslash_line_continuation_does_not_smuggle_it_past(self) -> None:
        """行接續（`\\` ＋ 換行）在 bash 是**行內空白**，判準必須先折回去才切段。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§2。"""
        for command in ("git \\\n  stash -q -u --keep-index",
                        "git checkout \\\n  -- tools/lib/quota_meter.py",
                        "git -C /Users/x/repo \\\n  stash pop",
                        "git reset \\\n  --hard HEAD~1"):
            with self.subTest(command=command):
                self.assertTrue(
                    G.destructive_git_hits(command),
                    f"{command!r} 換個換行位置就繞過守衛——立案指令本身就是這個形狀")

    def test_folding_continuations_does_not_swallow_a_following_statement(self) -> None:
        """折行接續**不得**把下一個語句併掉——那個方向是靜默漏擋，不是誤擋。

        反向自證：`\\` 只在真的位於行末時才是接續符；行末沒有它的多行指令，
        每一行仍必須各自被判。
        """
        self.assertTrue(G.destructive_git_hits("echo a \\\n  b\ngit stash pop"),
                        "上一行的接續把下一行的 `git stash pop` 吃掉了")

    def test_all_hits_are_reported_not_just_the_first(self) -> None:
        """不早退：早退會遮蔽後面的訊號，而遮蔽的方向是「看起來變乾淨」。"""
        hits = G.destructive_git_hits(
            "git restore --staged . ; git checkout -- . ; git clean -fd")
        self.assertEqual(len(hits), 2, f"應同時報 checkout 與 clean 兩筆，實得：{hits}")


# ── ② 不該擋的放行 ─────────────────────────────────────────────────────────
class TestSafeFormsAreNotBlocked(unittest.TestCase):
    """誤擋一條，這道鎖就會被整個關掉——本類是本檔最重要的一半。"""

    ALLOWED = (
        # 🔴 根 CLAUDE.md〈可重啟點四條件〉第 1 條**指定**的保全手法。擋掉它＝擋掉
        # 本 repo 自己的安全暫停 SOP，那會是這道鎖被拔掉的第一個理由。
        "git stash create",
        "git add -A && git stash create",
        "git stash list",
        "git stash show -p stash@{0}",
        # 不動工作樹內容的 reset 家族
        "git reset",
        "git reset --soft HEAD~1",
        "git reset HEAD tools/lib/quota_meter.py",
        "git reset -q HEAD tools/_ci_probe.sh",
        # 只動 index（取捨理由見 hook 模組 docstring）
        "git restore --staged tools/lib/quota_meter.py",
        # 純切分支／建分支
        "git checkout -b feature/x",
        "git checkout -b docs",          # `docs/` 真的存在，但 -b ⇒ 那是分支名
        "git checkout -B tools",
        "git switch -c docs",
        "git checkout main",
        "git switch -",
        # dry-run
        "git clean -n",
        "git clean --dry-run -d",
        # 唯讀查詢
        "git status --porcelain",
        "git diff --stat",
        "git log --oneline -5",
        "git log --grep=stash",
        "git show HEAD",
        "git ls-files | head -5",
        "git rev-parse --show-toplevel",
        "git worktree list",
        # 本 hook 射程外的寫入動作（另案，刻意不擋——射程撐大是誤擋的來源）
        "git add -A",
        "git commit -m x",
        "git push",
        "git tag R83-wip-preserved",
    )

    def test_every_safe_form_is_allowed(self) -> None:
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command), [],
                    f"{command!r} 不動工作樹內容卻被擋——誤擋會讓整支守衛被關掉")

    def test_lookalike_executables_are_not_git(self) -> None:
        """`legit stash`／`gitk` 這種字首字尾巧合不得命中（`_GIT_EXE_RE` 的邊界）。"""
        for command in ("legit stash", "gitk --all", "mygit reset --hard"):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command), [], command)

    def test_end_to_end_stash_create_really_passes(self) -> None:
        """端到端把最關鍵的那一條再驗一次（rc=0、零輸出）。"""
        proc = run_hook(bash_payload("git stash create && git tag R83-wip-preserved"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr.strip(), "")


class TestQuotingAndHeredocAreInert(unittest.TestCase):
    """把危險形態當**資料**寫出來（探針、文件、重現缺陷）是最常見的正當情境。

    修法是「先把不是可執行結構的區段拿掉再比對」——本類是那個修法在本檔的回歸鎖
    （上一代姊妹守衛在這裡誤擋過，實測＝R89 收尾證據檔）。
    """

    def test_quoted_text_is_not_a_command(self) -> None:
        for command in ("echo 'git stash' > /tmp/x",
                        'grep -rn "git reset --hard" docs/',
                        "python -c \"print('git clean -fd')\""):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command), [], command)

    def test_heredoc_body_is_data(self) -> None:
        """`python - <<'PY' … PY` 是寫探針的標準寫法，body 不是殼指令。

        誠實劃界：`bash <<'EOF'` 的 body **會**執行 ⇒ 這裡取的是「寧可漏擋、
        不要誤擋」那一邊，理由與代價都寫在 hook 的模組 docstring。
        """
        self.assertEqual(
            G.destructive_git_hits("python - <<'PY'\nprint('git stash')\nPY"), [])

    def test_comment_is_not_a_command(self) -> None:
        self.assertEqual(G.destructive_git_hits("ls   # 以前這裡寫 git stash"), [])


# ── ③ 退化 payload ─────────────────────────────────────────────────────────
class TestDegradedPayloadIsLoudButNotBlocking(unittest.TestCase):
    """壞 JSON／空 stdin／缺欄位 ⇒ rc=1（出聲但不阻斷），**不是** rc=0 也不是 rc=2。
    WHY：不硬擋（唯一的 shell 載具不能被讀不懂的輸入換掉）、不靜默（守衛失效必須看得見）。
    史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§3。"""

    def test_malformed_json(self) -> None:
        proc = run_hook(None, raw="{not json")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("block_destructive_git", proc.stderr)

    def test_empty_stdin(self) -> None:
        proc = run_hook(None, raw="")
        self.assertEqual(proc.returncode, 1, proc.stderr)

    def test_missing_tool_name(self) -> None:
        proc = run_hook({"tool_input": {"command": "git stash"}})
        self.assertEqual(proc.returncode, 1, proc.stderr)

    def test_missing_command_string(self) -> None:
        proc = run_hook({"tool_name": "Bash", "tool_input": {}})
        self.assertEqual(proc.returncode, 1, proc.stderr)

    def test_degraded_verdict_matches_the_shared_criterion(self) -> None:
        """與註冊面的交界：本檔走 rc=1 ⇒ 對 matcher 寬窄沒有硬約束；但仍要求
        matcher **恰好等於**自己的射程，零附帶面。判準本體借用姊妹鎖那一支。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "tests"))
        from test_check_hooks_liveness import (  # noqa: PLC0415
            degraded_payload_verdict,
            matchers_for_script,
        )

        settings = json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))
        matchers = matchers_for_script(settings, "block_destructive_git")
        self.assertTrue(matchers, "本 hook 沒有註冊在 PreToolUse ⇒ 它一次都不會被觸發")
        self.assertIsNone(
            degraded_payload_verdict("block_destructive_git.py", set(G.OWN_TOOLS),
                                     1, matchers))


# ── ④ 例外 fail-open ───────────────────────────────────────────────────────
class TestUnexpectedExceptionFailsOpen(unittest.TestCase):
    """任何非預期例外 → exit 0。

    WHY 這個方向是對的：`.claude/settings.json` description 記載過的 P0——hook 誤觸
    PreToolUse deny 會把**所有**工具硬鎖死。守衛自身絕不可成為那種故障源。
    """

    def test_hits_raising_is_swallowed(self) -> None:
        original = G.destructive_git_hits
        try:
            G.destructive_git_hits = lambda _c: (_ for _ in ()).throw(  # type: ignore[assignment]
                RuntimeError("boom"))
            sys.stdin = _FakeStdin(json.dumps(bash_payload("git stash")))
            self.assertEqual(G.main(), 0, "例外沒有 fail-open ⇒ 可能把所有工具鎖死")
        finally:
            G.destructive_git_hits = original  # type: ignore[assignment]
            sys.stdin = sys.__stdin__

    def test_path_probe_never_raises(self) -> None:
        """路徑啟發式解析不出來時一律回 False（＝放行），不得往上拋。"""
        self.assertFalse(G._looks_like_worktree_path("\x00bad"))


class _FakeStdin:
    def __init__(self, text: str) -> None:
        self._text = text
        self.buffer = None

    def read(self) -> str:
        return self._text


# ── ⑤ 逃生口 ───────────────────────────────────────────────────────────────
class TestEscapeHatches(unittest.TestCase):
    """兩個層級的出口，且刻意**不與既有變數共用**。"""

    def test_env_kill_switch_allows_everything(self) -> None:
        proc = run_hook(bash_payload("git reset --hard"),
                        env={G.GUARD_OFF_ENV: "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_the_kill_switch_is_not_shared_with_the_other_guards(self) -> None:
        """🔴 repo 明文：共用一個開關會讓「我只是想暫時別被擋」順手把別的保護一起
        關掉，而那件事沒有人會注意到。本條把「不共用」釘成事實。"""
        for foreign in ("AUTOSDD_CONTEXT_GUARD_OFF", "AUTOSDD_SENTINEL_OFF"):
            with self.subTest(env=foreign):
                proc = run_hook(bash_payload("git reset --hard"), env={foreign: "1"})
                self.assertEqual(proc.returncode, 2,
                                 f"{foreign} 竟然也能關掉本守衛")
        self.assertNotIn(G.GUARD_OFF_ENV,
                         {"AUTOSDD_CONTEXT_GUARD_OFF", "AUTOSDD_SENTINEL_OFF"})

    def test_inline_exemption_needs_a_written_reason(self) -> None:
        self.assertEqual(
            G.destructive_git_hits("git stash") and
            [] if G.has_exemption("git stash  # git-guard-ok: 事故還原") else ["x"],
            [])
        self.assertTrue(G.has_exemption("git stash  # git-guard-ok: 事故還原"))
        self.assertFalse(G.has_exemption("git stash  # git-guard-ok:"),
                         "空理由不算豁免——「刻意這樣寫」與「沒注意」必須分得開")
        self.assertFalse(G.has_exemption("git stash  # ps-lint-ok: 別的標記"),
                         "共用別支守衛的標記會讓一次豁免順手放行兩類危害")

    def test_exemption_must_live_in_a_real_comment(self) -> None:
        """標記住在引號裡（＝資料）不算豁免，否則寫一份文件就等於全域關掉。"""
        self.assertFalse(G.has_exemption("echo '# git-guard-ok: 這是文件內容'"))

    def test_end_to_end_exemption_passes(self) -> None:
        proc = run_hook(bash_payload("git stash pop  # git-guard-ok: R83 事故還原"))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_inline_exemption_is_void_when_unattended(self) -> None:
        """🔴 一個無人看管的模型回合可以自己寫出豁免註解 ⇒ 出口對它無效。

        順序本身就是判準的一部分（同 lint_powershell_command.py 對授權邊界的處置）。
        """
        proc = run_hook(bash_payload("git stash pop  # git-guard-ok: 我自己說可以"),
                        env={G.UNATTENDED_ENV: "1"})
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("無人看管", proc.stderr)

    def test_the_kill_switch_still_wins_when_unattended(self) -> None:
        """人設的環境變數優先於一切：那是唯一模型碰不到的出口，不能被無人看管旗標鎖死。"""
        proc = run_hook(bash_payload("git reset --hard"),
                        env={G.UNATTENDED_ENV: "1", G.GUARD_OFF_ENV: "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)


# ── ⑥ 射程 ─────────────────────────────────────────────────────────────────
class TestScopeIsNotWidened(unittest.TestCase):
    """matcher 若被改寬，守衛自己必須認得工具名（同 block_bash_on_windows.py 的第二道限縮）。"""

    def test_other_tools_pass_through(self) -> None:
        for tool in ("Read", "Write", "Edit", "Agent", "Workflow", "Grep"):
            with self.subTest(tool=tool):
                proc = run_hook({"tool_name": tool,
                                 "tool_input": {"command": "git reset --hard"}})
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_own_tools_are_the_ones_this_harness_actually_emits(self) -> None:
        """🔴 R80 的教訓：圈一組永遠不出現的工具名＝阻斷臂蓋好了卻永遠不觸發，
        而所有單元測試照樣全綠（`Task` 在 8,106 次 tool_use 裡出現 0 次）。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§4。"""
        self.assertEqual(set(G.OWN_TOOLS), {"Bash", "PowerShell"})

    def test_it_runs_on_every_platform(self) -> None:
        """🔴 姊妹檔 `block_bash_on_windows.py` 第一件事是 `os.name != 'nt' → exit 0`，
        因為它守的規則只在 Windows 成立。本檔**不可以**照抄那個平台閘：
        `git stash` 在 mac 上清掉的檔案和在 Windows 上一模一樣，而 R83 事故就發生在
        macOS。無條件外推單平台判準是 DEF-101-766，這裡要防的是它的鏡像版本。
        """
        source = _HOOK.read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith("#"))
        code = code.split('"""', 2)[-1]  # 去掉模組 docstring（裡面談過平台閘）
        self.assertNotIn("os.name", code,
                         "本守衛不得有平台閘——事故發生在 macOS，加上去就等於在事故現場關掉它")


# ── 註冊面 ─────────────────────────────────────────────────────────────────
class TestHookIsActuallyRegistered(unittest.TestCase):
    """機制蓋好沒接電是本 repo 反覆復發的病（R77 PKG-GUARD 第三次復發）。"""

    def _wiring(self):
        import hook_wiring  # noqa: PLC0415
        return hook_wiring

    def test_registered_as_pretooluse_on_both_shell_carriers(self) -> None:
        wiring = self._wiring()
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))
        entries = wiring.entries_launching(settings, "block_destructive_git",
                                           event="PreToolUse")
        self.assertEqual(len(entries), 1,
                         f"PreToolUse 底下承載本 hook 的條目有 {len(entries)} 個（預期 1）")
        matcher = str(entries[0].get("matcher", ""))
        # 🔴 R95 起本 hook 承載兩族判準：shell 指令面（OWN_TOOLS）＋治理面唯讀
        # （GOV_TOOLS）。matcher 仍必須**恰好等於**兩族聯集——多圈一個工具就是附帶面。
        self.assertEqual(set(matcher.split("|")), set(G.OWN_TOOLS) | set(G.GOV_TOOLS),
                         f"matcher 與腳本射程不一致：{matcher}")

    def test_it_is_exec_form_with_both_platform_carriers(self) -> None:
        """R80 起 hook 條目一律 exec form，且每個邏輯 hook**恰好一條**（單一 symlink
        形態載具，方案 B／DEF-200-316 起），兩平台共用同一條 command，差異只在
        POSIX 上 symlink 指向的實體。退回 shell form 會讓 Windows 每觸發一次就閃
        一個 console 視窗。"""
        wiring = self._wiring()
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))
        entry = wiring.entries_launching(settings, "block_destructive_git",
                                         event="PreToolUse")[0]
        mine = [h for h in entry["hooks"]
                if any("block_destructive_git" in a
                       for a in wiring.hook_entry_argv(h))]
        self.assertEqual(len(mine), 1, f"單一載具形態下不是恰好一條：{mine}")
        self.assertTrue(all(wiring.is_exec_form(h) for h in mine),
                        "有條目退回 shell form")
        commands = {str(h.get("command", "")) for h in mine}
        self.assertTrue(commands & set(wiring.WIN_CARRIERS), "缺 Windows 載具")

    def test_the_whole_settings_file_has_no_form_problems(self) -> None:
        """本次新增不得把既有的形態判準弄壞（A~F 全體）。"""
        wiring = self._wiring()
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))
        self.assertEqual(wiring.hook_form_problems(settings), [])

    def test_the_hook_is_named_in_root_claude_md(self) -> None:
        """已註冊卻沒被文件點名的 hook，下一輪很可能被再蓋一支（R73 `Find-GitBash` 的病）。
        通用判準住 `test_doc_loc_baseline_freshness_r60.py`；此處只釘自己這一支。"""
        text = (_REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8-sig")
        self.assertIn("block_destructive_git.py", text)


# ── ⑦ 動詞感知的換樹放寬（R83 誤攔訂正）─────────────────────────────────────
class _ForeignTreeCase(unittest.TestCase):
    """共用夾具：一個**真的存在、且與專案根互不包含**的目錄，模擬拋棄式 worktree。

    刻意用 `tempfile.mkdtemp()` 而不是寫死某台機器的 scratchpad 路徑：判準讀的是
    「這個目錄存不存在、與專案根的包含關係」，那兩件事在任何機器與 CI 上都成立，
    而寫死路徑會讓這支鎖在別的 checkout 上恆綠（`DEF-101-778` 的形狀）。
    """

    def setUp(self) -> None:
        self.foreign = tempfile.mkdtemp(prefix="w3-foreign-tree-")
        self.addCleanup(shutil.rmtree, self.foreign, ignore_errors=True)
        # `is_foreign_tree()` 以 `CLAUDE_PROJECT_DIR` 當共用工作樹的定義；測試行程的
        # 環境與 cwd 都不可靠，故明文釘住，否則本類的結論會變成機器狀態的函數。
        patcher = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def hits(self, command: str) -> list[str]:
        """一律以**共用工作樹**當起點 cwd——那是 production 實測的值（見下一個類別）。"""
        return G.destructive_git_hits(command, start_dir=str(_REPO_ROOT))


class TestWorktreeConfinedVerbsRelaxOutsideTheSharedTree(_ForeignTreeCase):
    """危害只限當前工作樹的動詞，落在非共用樹時必須**放行**。

    WHY（誤擋是這道鎖的**存亡問題**——擋到讓人無法工作的守衛會被整個關掉，repo
    判例）：真誤擋立案與合成 repo 實測原文＝GovWrite 證據檔 §6.2。
    """

    def test_each_confined_verb_is_allowed_in_a_foreign_tree(self) -> None:
        for tail in ("git checkout -- b.txt",
                     "git checkout HEAD -- b.txt",
                     "git checkout .",
                     "git restore b.txt",
                     "git restore --worktree --staged b.txt",
                     "git reset --hard",
                     "git reset --hard HEAD~1",
                     "git clean -fdx",
                     "git checkout -f main",
                     "git switch --discard-changes main"):
            command = f"cd {self.foreign} && {tail}"
            with self.subTest(command=command):
                self.assertEqual(
                    self.hits(command), [],
                    "拋棄式樹內的 worktree-confined 動詞被誤擋 ⇒ 這道鎖會被整個關掉")

    def test_git_dash_c_names_the_tree_just_as_well_as_cd(self) -> None:
        """`git -C <拋棄式樹>` 與 `cd <拋棄式樹> &&` 是同一件事，兩種寫法都要放行。"""
        self.assertEqual(self.hits(f"git -C {self.foreign} checkout -- b.txt"), [])
        self.assertEqual(self.hits(f"git -C {self.foreign} clean -fdx"), [])

    def test_powershell_set_location_counts_as_changing_the_tree(self) -> None:
        """Windows 側鐵律一禁 Bash ⇒ 指令走 PowerShell，切目錄動詞是 `Set-Location`。
        只認 bash 的 `cd` 會讓整個 Windows 側繼續誤擋（單平台判準不可外推）。"""
        self.assertEqual(self.hits(f"Set-Location {self.foreign}; git clean -fdx"), [])
        self.assertEqual(self.hits(f"Push-Location {self.foreign}; git reset --hard"), [])


class TestStashIsBlockedInEveryTree(_ForeignTreeCase):
    """🔴 `stash` 全家**不論在哪一棵樹都擋**——換樹不會讓它變安全。

    「只看樹就整條放行」漏掉的恰好是**立案那一條指令**：`refs/stash` 是 repo 級不是
    工作樹級（合成 repo 實測原文＝GovWrite 證據檔 §6.3）。
    """

    def test_the_accident_command_is_still_blocked_in_a_throwaway_worktree(self) -> None:
        for form in ("cd {d} && git stash -q -u --keep-index",
                     "git -C {d} stash -q -u --keep-index",
                     "cd {d} && git stash",
                     "cd {d} && git stash pop",
                     "cd {d} && git stash drop",
                     "cd {d} && git stash clear"):
            command = form.format(d=self.foreign)
            with self.subTest(command=command):
                self.assertTrue(
                    self.hits(command),
                    "stash 溢出到共用 `.git`，換一棵樹放行它就是把事故原指令放回來")

    def test_the_block_message_explains_the_spill(self) -> None:
        """只擋不教會被拔掉；而這一條的「為什麼換樹沒用」必須說出來。"""
        hit = self.hits(f"cd {self.foreign} && git stash")[0]
        self.assertIn("refs/stash", hit)

    def test_stash_create_is_still_allowed_everywhere(self) -> None:
        """放行面不得被本次改動波及（安全暫停 SOP 指定的手法）。"""
        self.assertEqual(self.hits(f"cd {self.foreign} && git stash create"), [])
        self.assertEqual(self.hits("git stash create"), [])


class TestTheRelaxationOpensNoNewHoles(_ForeignTreeCase):
    """換樹放寬的四道前提，每一條都對應一個**實測過**的漏擋形態（複審者的警告逐字＝
    R89 收尾證據檔）。受測對象：`.claude/hooks/block_destructive_git.py` 的
    `is_foreign_tree()` 換樹放寬邏輯。
    """

    def test_dash_c_pointing_back_at_the_shared_tree_wins_over_cd(self) -> None:
        """實測：cwd 在 lab 之外時 `git -C <主樹> checkout -- b.txt` rc=0、主樹改動消失
        ⇒ `-C` 必須被當成落腳目錄，不能因為前面 `cd` 去了別處就放行。"""
        self.assertTrue(self.hits(
            f"cd {self.foreign} && git -C {_REPO_ROOT} checkout -- CLAUDE.md"))

    def test_work_tree_and_git_dir_can_redirect_the_damage_anywhere(self) -> None:
        """實測：在 wt 內 `git --git-dir=<主樹/.git> --work-tree=<主樹> checkout -- b.txt`
        rc=0、主樹改動當場消失。git 自己不攔，所以本檔必須不放寬。"""
        self.assertTrue(self.hits(
            f"cd {self.foreign} && git --git-dir={_REPO_ROOT}/.git "
            f"--work-tree={_REPO_ROOT} checkout -- CLAUDE.md"))
        self.assertTrue(self.hits(
            f"cd {self.foreign} && git --work-tree={_REPO_ROOT} clean -fdx"))

    def test_a_cd_that_will_fail_leaves_git_in_the_shared_tree(self) -> None:
        """🔴 最陰險的一個：`cd /不存在; git clean -fdx` 的 `cd` 會失敗，而 `;` 沒有
        `&&` 的保護 ⇒ `git` 落在**原來的 cwd（共用工作樹）**。所以目標必須 `isdir()`。"""
        self.assertTrue(self.hits(f"cd {self.foreign}-no-such-dir; git clean -fdx"))
        self.assertTrue(self.hits("cd /w3-definitely-not-here; git reset --hard"))

    def test_a_directory_that_contains_the_project_is_not_foreign(self) -> None:
        """反向包含：`cd <專案根上一層> && git clean -fdx` 會把整個專案目錄當未追蹤
        內容刪掉。只判「不在專案根底下」這一向的話，這條會被放行。"""
        self.assertTrue(self.hits(f"cd {_REPO_ROOT.parent} && git clean -fdx"))
        self.assertTrue(self.hits(f"git -C {_REPO_ROOT.parent} clean -fdx"))

    def test_the_filesystem_root_contains_the_project_too(self) -> None:
        """🔴 反向包含的**邊界格**，獨立驗證輪實測出來的漏擋；判準刻意不寫死 `/`，
        改用當前平台的根（Windows 上是磁碟機根），否則這支鎖在另一個平台上量的是
        別的東西（史料見 CrossPlatform_DEF200275_Context_Metering_Evidence.md
        〈第七輪 史料搬遷〉）。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§5。"""
        fs_root = _REPO_ROOT.anchor
        self.assertTrue(self.hits(f"cd {fs_root} && git clean -fdx"),
                        "檔案系統根含著專案根 ⇒ 不得放寬")
        self.assertTrue(self.hits(f"git -C {fs_root} clean -fdx"))
        self.assertFalse(G.is_foreign_tree(fs_root),
                         "`is_foreign_tree()` 對檔案系統根必須回 False")

    def test_somewhere_inside_the_project_is_not_foreign(self) -> None:
        self.assertTrue(self.hits(f"cd {_REPO_ROOT}/tools && git checkout -- lib"))
        self.assertTrue(self.hits("cd tools && git checkout -- lib"))
        self.assertTrue(self.hits(f"cd {_REPO_ROOT} && git reset --hard"))

    def test_a_subshell_ends_the_cd_scope_at_the_closing_paren(self) -> None:
        """`(cd /wt); git clean -fdx` 的 `cd` 只作用在子殼內。順序掃描會把後面那條
        誤判成落在 `/wt`——方向是**放行共用工作樹**，所以整族關掉放寬。"""
        self.assertTrue(self.hits(f"(cd {self.foreign}); git clean -fdx"))
        self.assertTrue(self.hits(f"popd; cd {self.foreign}; git clean -fdx"))

    def test_a_shell_variable_is_not_a_directory_this_guard_can_see(self) -> None:
        """`cd \"$WT\"` 的值住在殼裡，`mask_inert()` 會把它抹成空白 ⇒ 推導不出 ⇒ 不放寬。
        方向刻意是 fail-closed；使用者要放寬就把絕對路徑寫出來（訊息裡有教）。"""
        self.assertTrue(self.hits('cd "$WT" && git clean -fdx'))
        self.assertTrue(self.hits("cd $WT && git clean -fdx"))

    def test_no_cd_at_all_means_the_shared_tree(self) -> None:
        self.assertTrue(self.hits("git checkout -- CLAUDE.md"))
        self.assertTrue(self.hits("git clean -fdx"))
        self.assertTrue(self.hits("cd - && git reset --hard"))

    def test_the_default_is_fail_closed_when_no_start_dir_is_known(self) -> None:
        """直接呼叫（不給 `start_dir`）時，相對 `cd` 解析不出基準 ⇒ 不放寬。"""
        self.assertTrue(G.destructive_git_hits("cd wt && git clean -fdx"))


class TestTheGuardDoesNotAskGitWhereItIs(unittest.TestCase):
    """🔴 為什麼判準不是複審者建議的 `git rev-parse --show-toplevel`。

    立案量測（payload cwd 三值恆等於專案根 ⇒ 該判準恆假、而程式碼看起來修好了——
    「鎖存在但沒有鑑別力」）原文＝GovWrite 證據檔 §6.4。本條把「不去問 git」釘成契約：
    想改 subprocess 的人先面對那個量測；順帶守住阻斷路徑不長子行程（PreToolUse 每呼叫都跑）。
    """

    def test_the_hook_spawns_no_subprocess(self) -> None:
        source = _HOOK.read_text(encoding="utf-8")
        code = source.split('"""', 2)[-1]
        for forbidden in ("import subprocess", "os.popen", "os.system", "--show-toplevel"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_payload_cwd_is_only_a_starting_point_not_the_answer(self) -> None:
        """指令字串一律贏過 payload 的 `cwd`：起點是專案根，`cd` 出去要能放行，
        `-C` 指回來要能擋下。兩向都在這一條裡。"""
        with tempfile.TemporaryDirectory(prefix="w3-start-point-") as foreign, \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertEqual(
                G.destructive_git_hits(f"cd {foreign} && git clean -fdx",
                                       start_dir=str(_REPO_ROOT)), [])
            self.assertTrue(
                G.destructive_git_hits(f"git -C {_REPO_ROOT} clean -fdx",
                                       start_dir=foreign))


class TestEndToEndWithProductionShapedPayload(unittest.TestCase):
    """端到端：payload 帶 `cwd`（＝production 的形狀），兩向都真的起 child 行程量 rc。"""

    def _payload(self, command: str) -> dict:
        return {"tool_name": "Bash", "cwd": str(_REPO_ROOT),
                "tool_input": {"command": command}}

    def test_confined_verb_in_a_foreign_tree_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w3-e2e-") as foreign:
            proc = run_hook(self._payload(f"cd {foreign} && git checkout -- b.txt"),
                            env={"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stderr.strip(), "")

    def test_the_accident_command_in_a_foreign_tree_still_exits_two(self) -> None:
        with tempfile.TemporaryDirectory(prefix="w3-e2e-") as foreign:
            proc = run_hook(
                self._payload(f"cd {foreign} && git stash -q -u --keep-index"),
                env={"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("refs/stash", proc.stderr, "沒說明為什麼換樹也不行")

    def test_the_guidance_teaches_the_form_that_would_be_allowed(self) -> None:
        """被擋的人要能從訊息知道「怎麼寫才會過」，否則唯一的出路是關掉守衛。"""
        proc = run_hook(self._payload("git clean -fdx"),
                        env={"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("git -C", proc.stderr)
        self.assertIn("git-guard-ok", proc.stderr)


# ── 判準本身的紅綠自證（合成注入）───────────────────────────────────────────
class TestTheCriterionItselfCanFail(unittest.TestCase):
    """反 vacuity：判準塌掉時上面每一條都會靜默變綠，所以要直接對判準注入。

    形狀取自本 repo 既有慣例——「解析器回空集合 ⇒ 比較恆真通過 ⇒ 靜默失效」。
    受測對象：`.claude/hooks/block_destructive_git.py` 的 `destructive_git_hits()`。
    """

    def test_masking_everything_would_break_the_block_side(self) -> None:
        original = G.mask_inert
        try:
            G.mask_inert = lambda text, **_kw: " " * len(text)  # type: ignore[assignment]
            self.assertEqual(G.destructive_git_hits("git stash"), [],
                             "遮蔽器全遮時竟仍命中 ⇒ 判準沒有真的讀遮蔽結果")
        finally:
            G.mask_inert = original  # type: ignore[assignment]
        self.assertTrue(G.destructive_git_hits("git stash"), "還原後應恢復命中")

    def test_the_verb_scope_split_is_load_bearing(self) -> None:
        """🔴 反 vacuity 的核心一條：如果 `stash` 不在「會溢出」那一格，換樹放寬就會把
        **立案那條指令**放回來。把該格清空，事故原指令必須當場變成放行——那證明擋住它
        的真的是動詞分類，不是別的東西恰好也擋了它。"""
        with tempfile.TemporaryDirectory(prefix="w3-vacuity-") as foreign, \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            command = f"cd {foreign} && git stash -q -u --keep-index"
            self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))
            original_shared, original_wt = G._SHARED_SCOPED, G._WORKTREE_SCOPED
            try:
                G._SHARED_SCOPED = frozenset()  # type: ignore[assignment]
                G._WORKTREE_SCOPED = original_wt | {"stash"}  # type: ignore[assignment]
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                    "把 stash 移進 worktree-confined 那一格竟仍擋下 ⇒ 分類沒有被真的讀")
            finally:
                G._SHARED_SCOPED = original_shared  # type: ignore[assignment]
                G._WORKTREE_SCOPED = original_wt  # type: ignore[assignment]
            self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))

    def test_the_relaxation_blockers_are_load_bearing(self) -> None:
        """把「放寬殺手」表拿掉，`--work-tree` 指回主樹那條必須從擋下變成放行
        ⇒ 證明擋住它的是那張表，不是碰巧。"""
        with tempfile.TemporaryDirectory(prefix="w3-vacuity-") as foreign, \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            command = (f"cd {foreign} && git --work-tree={_REPO_ROOT} "
                       "checkout -- CLAUDE.md")
            self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))
            with mock.patch.object(G, "relaxation_blockers", lambda _c: []):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                    "殺手表被清空後仍擋下 ⇒ 那張表沒有被真的讀，判準是恆真的")

    def test_the_foreign_tree_probe_is_load_bearing(self) -> None:
        """讓 `is_foreign_tree()` 恆假（＝退回修訂前的行為），放行面必須全部塌回擋下。
        這一條同時是「修訂前 rc=2 / 修訂後 rc=0」那組實測的 in-process 版本。"""
        with tempfile.TemporaryDirectory(prefix="w3-vacuity-") as foreign, \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            command = f"cd {foreign} && git checkout -- b.txt"
            self.assertEqual(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [])
            with mock.patch.object(G, "is_foreign_tree", lambda _p: False):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                    "換樹判準恆假時竟仍放行 ⇒ 放行不是那個判準造成的")

    def test_the_root_boundary_fix_is_load_bearing(self) -> None:
        """把 `_dir_prefix()` 換回修訂前那個寫法（`p + os.sep`），檔案系統根那一格
        必須當場變成放行——那證明擋住它的真的是這次的訂正，不是別的判準恰好也擋了它。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§6。"""
        fs_root = _REPO_ROOT.anchor
        command = f"cd {fs_root} && git clean -fdx"
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))
            with mock.patch.object(G, "_dir_prefix", lambda p: p + os.sep):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                    "退回 `p + os.sep` 竟仍擋下 ⇒ 擋住檔案系統根的不是 `_dir_prefix()`，"
                    "本次訂正沒有承重")
            self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))

    def test_dropping_the_stash_allowlist_would_break_the_allow_side(self) -> None:
        original = G._STASH_SAFE
        try:
            G._STASH_SAFE = frozenset()  # type: ignore[assignment]
            self.assertTrue(G.destructive_git_hits("git stash create"),
                            "允許清單被清空後仍放行 ⇒ 放行面不是靠那張表判的")
        finally:
            G._STASH_SAFE = original  # type: ignore[assignment]
        self.assertEqual(G.destructive_git_hits("git stash create"), [])


# ══════════════════════════════════════════════════════════════════════════════
# 鐵律六（R84／`DEF-200-044`／`045`）— `waitform_hits()` 的回歸鎖
# ══════════════════════════════════════════════════════════════════════════════
#: 該擋的：判準①②③各自的真實形態（④ 另見 `_RCPIPE_BLOCK`）。
#: 前兩筆逐字取自 R83 收輪的實帳指令。
_WAITFORM_BLOCK: tuple[tuple[str, bool], ...] = (
    # 判準①：立案那條 nightly（實帳 00:39 → 01:27 共 48 分鐘零工作）
    ("nohup bash AutoClaude/tools/run_local_nightly.sh --force > /tmp/n.log 2>&1 &", False),
    ("cd /Users/wuweihong/Antigravity/AISDCL_Agent; nohup .venv/bin/python "
     "tools/run_root_unittests.py > /tmp/ru3.log 2>&1 & echo started", False),
    ("setsid ./a.sh &", False),
    ("./long_job.sh & disown", False),
    # 判準②：兄弟互匹的四種寫法（引號／裸／雙引號正則／組合旗標）
    ("until ! pgrep -f 'run_root_unittests'; do sleep 5; done", False),
    ("until ! pgrep -f run_root_unittests; do sleep 5; done", False),
    ('while pgrep -f "python.*run_root_unittests"; do sleep 3; done', False),
    ("until ! pgrep -af 'sync_onboarding'; do sleep 10; done", False),
    # 判準③：`run_in_background` 搭一個自己就會立刻返回的指令
    ("python heavy.py &", True),
    ("./a.sh & disown", True),
)

#: 不該擋的。每一筆都對應一個**實測到的**假紅來源或一個 CLAUDE.md 鐵律六 ✅ 的形態。
_WAITFORM_ALLOW: tuple[tuple[str, bool], ...] = (
    # SD-02 逐筆判讀出的唯一假陽性：`wait` 與 `nohup` **不同段**，而它是正確形態
    ("nohup true; python heavy.py & BGPID=$!; wait $BGPID", False),
    ("nohup ./a.sh > log 2>&1 & wait", False),
    # CLAUDE.md 鐵律六 ✅：字元類自我否定（本判準的放行面）
    ("until ! pgrep -f 'run_root[_]unittests'; do sleep 20; done", False),
    ("until ! pgrep -f '[p]ython.*X'; do sleep 3; done", False),
    # 逐字稿實測的真實 pgrep 用法：一次性檢查、`&&`／`||`、管線餵 while-read
    ("pgrep -f run_root_unittests >/dev/null && echo running || echo done", False),
    ("pgrep -f run_root_unittests | while read p; do ps -o command= -p $p; done", False),
    ("pgrep -fl 'run_root_unittests' | head -3", False),
    # `&` 的三種非背景用法（每一種都是實測會製造假紅的寫法）
    ("make -j4 a && make b", False),
    ("python x.py 2>&1 | tee /tmp/log", False),
    ("bash tools/x.sh &> /tmp/log", False),
    # 前景阻塞＋`run_in_background`＝鐵律六 ✅ 的第一格，絕不可擋
    ("/Users/wuweihong/Antigravity/AISDCL_Agent/.venv/bin/python tools/run_root_unittests.py",
     True),
    ("python -m pytest tests/ -q > /tmp/p.log 2>&1; echo rc=$?", True),
    # 惰性區段：字串／註解裡的壞形態不是指令
    ("echo 'nohup foo &' >> notes.md", False),
    ("# nohup foo &\necho hi", False),
    # while 的其他用途（條件內沒有 pgrep）
    ("while read -r line; do echo $line; done < f", False),
    ("until pg_isready -h localhost; do sleep 1; done", False),
)


class TestIronLaw6BadFormsAreBlocked(unittest.TestCase):
    """鐵律六：**等待／確認的機制自己靜默壞掉 ⇒ 無做工空轉**（`DEF-200-044`）。
    史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§7。"""

    def test_every_bad_form_is_blocked(self) -> None:
        for command, background in _WAITFORM_BLOCK:
            with self.subTest(command=command[:70]):
                self.assertTrue(
                    G.waitform_hits(command, run_in_background=background),
                    "鐵律六壞形態未被擋下")

    def test_every_good_form_is_allowed(self) -> None:
        """假紅是這道鎖的生死線：擋到讓人無法工作的守衛會被整個關掉。"""
        for command, background in _WAITFORM_ALLOW:
            with self.subTest(command=command[:70]):
                self.assertEqual(
                    G.waitform_hits(command, run_in_background=background), [],
                    "鐵律六判準誤擋了一個正確形態")

    def test_all_three_criteria_report_separately(self) -> None:
        """一條指令同時犯兩條時兩條都要列出來（不早退——早退的方向是「看起來變乾淨」）。"""
        hits = G.waitform_hits(
            "nohup ./a.sh & until ! pgrep -f 'a.sh'; do sleep 1; done")
        self.assertGreaterEqual(len(hits), 2, hits)


class TestIronLaw6EndToEnd(unittest.TestCase):
    """真的起 child 行程量 rc ＋ 驗指引可讀（同本檔既有的 end-to-end 紀律）。"""

    def test_the_accident_form_exits_two_with_guidance(self) -> None:
        proc = run_hook(bash_payload(
            "nohup bash AutoClaude/tools/run_local_nightly.sh > /tmp/n.log 2>&1 &"))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("48 分鐘零工作", proc.stderr)
        self.assertIn("waitform-ok", proc.stderr)

    def test_run_in_background_flag_is_read_from_the_payload(self) -> None:
        """🔴 本輪**實測**過這個欄位（臨時 probe）：前景呼叫整個 key 不存在，
        `run_in_background: true` 的呼叫帶得到 ⇒ 判準③ 不是靜態推論。"""
        payload = {"tool_name": "Bash",
                   "tool_input": {"command": "python heavy.py &",
                                  "run_in_background": True}}
        self.assertEqual(run_hook(payload).returncode, 2)
        # 同一條指令、旗標不在 ⇒ 判準③不成立（判準①也不成立：沒有 nohup／disown）
        self.assertEqual(
            run_hook(bash_payload("python heavy.py &")).returncode, 0)

    def test_the_blocking_foreground_form_really_passes(self) -> None:
        proc = run_hook({"tool_name": "Bash",
                         "tool_input": {"command": "python tools/run_root_unittests.py",
                                        "run_in_background": True}})
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_pgrep_loop_exits_two(self) -> None:
        proc = run_hook(bash_payload(
            "until ! pgrep -f 'run_root_unittests'; do sleep 5; done"))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("兄弟", proc.stderr)


class TestIronLaw6ExemptionIsItsOwnHatch(unittest.TestCase):
    """兩族的逃生口**刻意不同字樣**：共用一個會讓「為了放行一個等待形態而寫的豁免」
    順手把毀滅性 git 一起放行（同本檔既有的兩層逃生口論述）。"""

    _BAD = "nohup ./a.sh > log 2>&1 &"

    def test_waitform_exemption_needs_a_written_reason(self) -> None:
        self.assertTrue(G.has_waitform_exemption(f"{self._BAD}  # waitform-ok: 探針"))
        self.assertFalse(G.has_waitform_exemption(f"{self._BAD}  # waitform-ok:"))

    def test_exemption_must_live_in_a_real_comment(self) -> None:
        self.assertFalse(G.has_waitform_exemption(f"echo '# waitform-ok: 假的'; {self._BAD}"))

    def test_the_two_families_do_not_share_a_hatch(self) -> None:
        """🔴 交叉放行是這一條在守的東西，兩個方向都要成立。"""
        self.assertEqual(
            run_hook(bash_payload(f"{self._BAD}  # git-guard-ok: 不該放行等待形態"))
            .returncode, 2)
        self.assertEqual(
            run_hook(bash_payload("git stash  # waitform-ok: 不該放行毀滅性 git"))
            .returncode, 2)

    def test_end_to_end_exemption_passes(self) -> None:
        self.assertEqual(
            run_hook(bash_payload(f"{self._BAD}  # waitform-ok: 刻意重現缺陷"))
            .returncode, 0)

    def test_exemption_is_void_when_unattended(self) -> None:
        proc = run_hook(bash_payload(f"{self._BAD}  # waitform-ok: 刻意"),
                        env={G.UNATTENDED_ENV: "1"})
        self.assertEqual(proc.returncode, 2)
        self.assertIn("無人看管", proc.stderr)


class TestIronLaw6CriteriaHaveTeeth(unittest.TestCase):
    """🔴 合成注入：每一個載重零件被拿掉時**判準必須失去鑑別力**。

    這一族的存在理由是 R84 獨立驗證輪的實測（SD-01／SD-02）：兩條判準的第一版各自
    「鎖存在、綠燈、零鑑別力」。所以本類逐一注入那些失效，並斷言它們真的會讓判準壞掉——
    沒有這幾條，上面那兩張表只能證明「今天恰好對」，不能證明「是靠哪個零件對的」。
    """

    def test_taking_the_operand_from_the_masked_string_kills_criterion_two(self) -> None:
        """SD-01 的缺陷逐字重現：判準②若建在 `mask_inert()` 之上，**好壞兩種形態都放行**。

        原因是結構性的：判準②要判的東西（自我否定字元類 `run_root[_]unittests`）
        **正好住在被遮掉的那個引號字串裡** ⇒ 遮蔽面上兩者完全同形。
        """
        bad = "until ! pgrep -f 'run_root_unittests'; do sleep 5; done"
        good = "until ! pgrep -f 'run_root[_]unittests'; do sleep 5; done"
        # 現行實作（operand 從**原字串**同 offset 取）：一擋一放，有鑑別力
        self.assertTrue(G.waitform_hits(bad))
        self.assertEqual(G.waitform_hits(good), [])
        # 注入：把 operand 也從遮蔽字串取 ⇒ 兩邊都拿到空白 ⇒ 兩邊都放行（零鑑別力）
        original = G._pgrep_full_operand
        try:
            G._pgrep_full_operand = (  # type: ignore[assignment]
                lambda rest: original(G.mask_inert(rest)))
            self.assertEqual(G.waitform_hits(bad), [],
                             "遮蔽面版本竟然還擋得住 ⇒ 這條注入沒有重現 SD-01")
            self.assertEqual(G.waitform_hits(good), [])
        finally:
            G._pgrep_full_operand = original  # type: ignore[assignment]
        self.assertTrue(G.waitform_hits(bad), "注入沒有復原")

    def test_the_char_class_allowance_is_load_bearing(self) -> None:
        good = "until ! pgrep -f 'run_root[_]unittests'; do sleep 5; done"
        original = G._self_negating
        try:
            G._self_negating = lambda pattern: False  # type: ignore[assignment]
            self.assertTrue(G.waitform_hits(good),
                            "拿掉自我否定判準後 ✅ 形態仍被放行 ⇒ 放行面不是靠它判的")
        finally:
            G._self_negating = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits(good), [])

    def test_the_wait_carve_out_is_load_bearing(self) -> None:
        """`wait` 豁免救的是**同一段**裡 nohup ＋ `&` ＋ `wait` 的形態。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§8。"""
        good = "nohup ./a.sh > /tmp/log 2>&1 & wait"
        original = G._WAIT_RE
        try:
            G._WAIT_RE = re.compile(r"(?!x)x")  # type: ignore[assignment] — 永不匹配
            self.assertTrue(G.waitform_hits(good),
                            "拿掉 wait 豁免後這條仍被放行 ⇒ 那個假陽性不是靠豁免消掉的")
        finally:
            G._WAIT_RE = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits(good), [])

    def test_the_statement_split_is_load_bearing(self) -> None:
        """SD-02 的第二道收窄：`nohup` 與背景 `&` 必須在**同一個** statement。"""
        good = "nohup make -v; python heavy.py > /tmp/x.log 2>/dev/null & BG=$!"
        # 兩者不同段 ⇒ 現行放行
        self.assertEqual(G.waitform_hits(good), [])
        original = G._STMT_SEP_RE
        try:
            G._STMT_SEP_RE = re.compile(r"(?!x)x")  # type: ignore[assignment] — 不切段
            self.assertTrue(G.waitform_hits(good),
                            "不切段之後仍放行 ⇒ 同段判準不是載重件")
        finally:
            G._STMT_SEP_RE = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits(good), [])

    def test_the_background_amp_exclusions_are_load_bearing(self) -> None:
        """`&&`／`2>&1`／`&>`／`|&` 四種排除各自都是實測會製造假紅的寫法。

        DEF-200-158：段首 `&`（PowerShell call operator，呼叫帶空白絕對路徑的執行檔時常見）
        曾因 `if i and …` 對 `i==0` falsy 短路而被誤判成背景 `&`；`run_in_background=True`
        時會誤觸「自己就會立刻返回」判準。
        """
        for good in ("nohup make a && make b", "nohup python x.py 2>&1 | tee log",
                     "nohup bash x.sh &> /tmp/log",
                     "exec 3<&0",              # `<&`：fd 複製（複審補格：四種排除此前只列三種）
                     "nohup make |& tee log"):  # `|&`：管線含 stderr，同上
            with self.subTest(good=good):
                self.assertEqual(G.waitform_hits(good), [])
        self.assertEqual(
            G.waitform_hits("& 'C:\\Program Files\\Git\\bin\\git.exe' stash list",  # platform-ok:
                             run_in_background=True), [])
        original = G._background_amps
        try:
            G._background_amps = lambda segment: "&" in segment  # type: ignore[assignment]
            self.assertTrue(G.waitform_hits("nohup make a && make b"),
                            "天真版 `'&' in seg` 竟未誤擋 ⇒ 排除清單不是載重件")
        finally:
            G._background_amps = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits("nohup make a && make b"), [])

    def test_the_loop_condition_boundary_is_load_bearing(self) -> None:
        """`pgrep` 必須在**條件內**才算——迴圈**體**裡的 pgrep 每一輪都會重跑並結束，
        不是那個永不成立的退出條件。
        史料搬至 CrossPlatform_Guard_Line_History_2.md〈R190 收尾棒〉§1。 round-label-ok"""
        good = "while read -r line; do pgrep -f run_root_unittests; done < hosts.txt"
        self.assertEqual(G.waitform_hits(good), [])
        original = G._COND_END_RE
        try:
            G._COND_END_RE = re.compile(r"(?!x)x")  # type: ignore[assignment] — 條件無邊界
            self.assertTrue(G.waitform_hits(good),
                            "條件邊界拿掉後仍放行 ⇒ 那個邊界不是載重件")
        finally:
            G._COND_END_RE = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits(good), [])


def _rib_payload(command: str, tool: str = "PowerShell", background: bool = True) -> dict:
    """前景呼叫整個 `run_in_background` key 不存在（上面 `TestIronLaw6EndToEnd` 實測過）。"""
    tool_input: dict = {"command": command}
    if background:
        tool_input["run_in_background"] = True
    return {"tool_name": tool, "tool_input": tool_input}


#: 主控本場真的被擋下的那條（路徑與 `ARMED_AT` 表達式是還原的；承載判準的只有結構）。
_DEF429_ARMED = (
    "$py='D:\\p\\python.exe'; $out='D:\\s\\f.jsonl'; "  # platform-ok: 還原被擋指令
    "\"ARMED_AT=$(Get-Date -Format o)\"; "
    "& $py D:\\p\\tools\\probe\\flash_watch.py --seconds 3300 --out $out; "
    "\"FLASH1_RC=$LASTEXITCODE\""
)
#: 修前必紅（HEAD 只放行 index 0）、修後必放行：`&` 之前沒有命令可背景化的各種位置。
_DEF429_CALL_OPERATOR = (
    _DEF429_ARMED,
    '"x"; & $py y.py',                          # 第 2+ 個 statement
    "$py = 'a'\n  & $py y.py",                   # 多行＋縮排（不縮排時 HEAD 本來就過）
    "$r = & git rev-parse HEAD",                # 賦值右值
    "Push-Location x; & $py y.py; Pop-Location",  # 鐵律二的官方成對形態
    '. "$(git rev-parse --show-toplevel)/tools/lib/Find-GitBash.ps1"; '
    "& (Find-GitBash) 'tools/x.sh'",            # 根 CLAUDE.md 鐵律一 `.sh` 官方形態
    "if ($ok) { & $py y.py }", "Write-Output $(& $py y.py)", "Get-Date | & $tool",
)
#: 修前修後都必擋：**後綴** `&`（前文以命令字元收尾），含引號包住的命令（遮蔽後前文全空白）。
_DEF429_STILL_BACKGROUND = (
    ("PowerShell", "python y.py &"), ("Bash", "python y.py &"),
    ("Bash", "nohup python y.py > log 2>&1 &"), ("PowerShell", "Start-Process x; python y.py &"),
    ("PowerShell", '"./job.sh" &'), ("PowerShell", "& $py y.py &"),
)


class TestDef200429CallOperatorIsNotABackgroundAmp(unittest.TestCase):
    """DEF-200-429（DEF-200-158 殘餘；受測：`.claude/hooks/block_destructive_git.py` 的
    `_background_amps()`／`_fold(quoted=)`／`waitform_hits()`）：判準③ 只放行 index 0 ⇒
    `; & $py x`／縮排／`$r = & exe`／`| & exe` 誤判為背景。兩向鎖：放行 `& exe`、仍擋 `cmd &`。"""

    def test_call_operator_positions_are_not_background(self) -> None:
        for command in _DEF429_CALL_OPERATOR:
            with self.subTest(command=command[:60]):
                self.assertEqual(G.waitform_hits(command, run_in_background=True), [])

    def test_a_suffix_amp_is_still_background_in_every_shell(self) -> None:
        for tool, command in _DEF429_STILL_BACKGROUND:
            with self.subTest(tool=tool, command=command[:60]):
                self.assertTrue(G.waitform_hits(command, run_in_background=True))
                self.assertEqual(run_hook(_rib_payload(command, tool)).returncode, 2)

    def test_the_quoted_view_is_what_keeps_a_quoted_command_blocked(self) -> None:
        command = '"./job.sh" &'
        self.assertFalse(G._background_amps(G._fold(command)), "遮蔽視圖前文全空白，看不到命令")
        self.assertTrue(G._background_amps(G._fold(command, quoted=True)))

    def test_both_views_split_into_the_same_segments(self) -> None:
        """`waitform_hits()` 以 `zip` 並排兩個視圖；長度或分隔符錯位時 `zip` 只會靜默截斷。"""
        command = "echo 'a;b'; \"x\ny\" ; & $py z.py\n  & $py w.py \\\n  --k"
        plain, quoted = G._fold(command), G._fold(command, quoted=True)
        self.assertEqual(len(plain), len(quoted))
        self.assertEqual([m.span() for m in G._STMT_SEP_RE.finditer(plain)],
                         [m.span() for m in G._STMT_SEP_RE.finditer(quoted)])

    def test_the_census_probe_reads_the_real_flag_from_the_transcript(self) -> None:
        """探針此前把旗標寫死 False ⇒ 判準③ 從未被真實母體量過（本缺陷躲這麼久的結構原因）。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import shell_command_corpus as C  # noqa: PLC0415
        events = [{"message": {"content": [{"type": "tool_use", "name": "PowerShell",
                   "input": {"command": "python y.py &", **flag}}]}}
                  for flag in ({"run_in_background": True}, {})]
        with tempfile.TemporaryDirectory(prefix="def429-corpus-") as tmp:
            (Path(tmp) / "slug").mkdir()
            (Path(tmp) / "slug" / "s.jsonl").write_text(
                "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
            rows = C.transcript_commands(Path(tmp))
        self.assertEqual([r[3] for r in rows], [True, False])
        with mock.patch.object(C, "transcript_commands", return_value=rows):
            recs = C.build(["transcripts"], "waitform")   # 同一字串、旗標不同 ⇒ 不得去重
        self.assertEqual({(r["background"], bool(r["hits"]["waitform"])) for r in recs},
                         {(True, True), (False, False)})

    def test_end_to_end_stdin_json_and_the_hatches(self) -> None:
        self.assertEqual(run_hook(_rib_payload(_DEF429_ARMED)).returncode, 0)
        blocked = run_hook(_rib_payload("python y.py &"))
        self.assertEqual(blocked.returncode, 2, blocked.stderr)
        self.assertIn("DEF-200-429", blocked.stderr)
        # 對照：前景呼叫不由判準③管（判準①也不成立：沒有 nohup／disown／setsid）
        self.assertEqual(G.waitform_hits("python y.py &"), [])
        self.assertEqual(run_hook(_rib_payload("python y.py &", background=False)).returncode, 0)
        # 行內豁免的既有行為不變：擋得住的形態靠它放行；本來就放行的形態加上它也照放
        for command in ("python y.py &", _DEF429_ARMED):
            self.assertEqual(run_hook(_rib_payload(
                f"{command}  # waitform-ok: call operator")).returncode, 0)


# ══════════════════════════════════════════════════════════════════════════════
# 鐵律六判準④（DEF-200-086）— 管線尾節是 rc 遮蔽型濾器，其後緊接著讀 `$?`
# ══════════════════════════════════════════════════════════════════════════════
#: 該擋的。第一筆逐字取自缺陷帳本的立案形態（修前 `waitform_hits()` 回 `[]`）。
_RCPIPE_BLOCK: tuple[str, ...] = (
    "sh -c 'exit 7' | tail -1; echo $?",  # 立案逐字：印 0，真 rc 是 7
    'make 2>&1 | head -5; echo "rc=$?"',  # 雙引號內的 `$?` 照樣會展開
    "python run.py 2>&1 | tee /tmp/o.log\necho $?",  # 多行形態
    "cmd | tail -1; rc=$?",  # 賦值形
    "pytest -q |& tail -3; RC=$?; echo $RC",  # `|&` ＋ 大寫賦值
    "(cmd | tail -1); echo ${?}",  # 子殼 ＋ `${?}`
    "out=$(cmd | wc -l); echo $?",  # 命令替換
    "cmd | sort | uniq -c; [ $? -eq 0 ] && echo ok",  # 多節管線 ＋ test
    "FOO=1 cmd | LC_ALL=C sort; echo $?",  # env 前綴
    'cmd | head -1 && echo "rc=$?"',  # `&&` 接續
    "cmd | grep x | tail -1; echo $?",  # 只看尾節：grep 在中間不豁免
    "cmd | tail -1 2>&1; echo $?",  # 尾節自帶重導
    "cmd |\n  tail -1\necho $?",  # 管線運算子結尾換行
    "bash <<'EOF'\ncmd | tail -1; echo $?\nEOF",  # 殼擁有的 heredoc body 會執行
)

#: 不該擋的。每一筆都是合法形態，或「讀到的 `$?` 不是管線 rc」的形態。
_RCPIPE_ALLOW: tuple[str, ...] = (
    "ls | grep x; echo $?",  # grep 的 rc 有語意（匹配與否）
    "cmd | rg foo; echo $?",
    "cmd | jq .a; echo $?",
    "cmd | tail -1 | grep ok; echo $?",  # 尾節是 grep
    "cmd | tail -1; echo ${PIPESTATUS[0]}",  # bash 正解
    "cmd | tail -1; echo ${pipestatus[1]}",  # zsh 正解
    "set -o pipefail; cmd | tail -1; echo $?",
    "set -euo pipefail\ncmd | tail -1; echo $?",
    "setopt pipefail; cmd | tail -1; echo $?",
    "cmd | tail -1",  # 沒讀 rc
    "cmd | tail -1; echo done",
    "cmd > f; echo $?",  # 沒有管線
    "cmd > /tmp/o.log 2>&1; echo rc=$?; tail -5 /tmp/o.log",  # 正解：先導檔再讀 rc
    "cmd 2>&1 > /tmp/o; echo $?",  # `2>&1` 的 `&` 不是管線
    "cmd || tail -1; echo $?",  # `||` 不是管線
    "cmd | tail -1; echo '$?'",  # 單引號內不展開
    "cmd | tail -1; echo \\$?",  # 反斜線逃脫
    "cmd | tail -1; echo done; echo $?",  # `$?` 屬於 echo，不屬於管線
    "echo 'cmd | tail -1; echo $?'",  # 引號內的管線是資料
    'git commit -m "x | tail -1; echo $?"',  # 同上（雙引號）
    "cat > run.sh <<'EOF'\ncmd | tail -1; echo $?\nEOF",  # 非殼的 heredoc＝寫檔資料
    "cmd | tail -1  # echo $?",  # 註解
    "diff <(a | sort) <(b | sort); echo $?",  # 行程替換內的管線：`$?` 是 diff 的
    "read x < <(cmd | head -1); echo $?",  # 同上：`$?` 是 read 的
)


class TestIronLaw6RcMaskedByPipe(unittest.TestCase):
    """DEF-200-086（受測：`.claude/hooks/block_destructive_git.py` 的 `waitform_hits()`
    判準④）。
    史料搬至 CrossPlatform_R190_FixRound_Evidence.md〈九-F〉§47。"""

    def test_every_masked_pipe_read_is_blocked(self) -> None:
        for command in _RCPIPE_BLOCK:
            with self.subTest(command=command[:60]):
                self.assertTrue(G.waitform_hits(command), "遮蔽 rc 的讀法未被擋下")

    def test_every_legitimate_form_is_allowed(self) -> None:
        """假紅是這道鎖的生死線：擋到讓人無法工作的守衛會被整個關掉。"""
        for command in _RCPIPE_ALLOW:
            with self.subTest(command=command[:60]):
                self.assertEqual(G.waitform_hits(command), [], "判準④誤擋了一個正確形態")

    def test_powershell_is_out_of_range(self) -> None:
        """PowerShell 側的 `$LASTEXITCODE` 另由 `lint_powershell_command.py` 守。"""
        for command in _RCPIPE_BLOCK:
            with self.subTest(command=command[:60]):
                self.assertEqual(G.waitform_hits(command, tool="PowerShell"), [])

    def test_the_hit_names_the_filter_and_teaches_the_fix(self) -> None:
        hits = G.waitform_hits("sh -c 'exit 7' | tail -1; echo $?")
        self.assertEqual(len(hits), 1, hits)
        for needle in ("tail", "DEF-200-086", "先導檔", "PIPESTATUS", "pipestatus"):
            self.assertIn(needle, hits[0])

    def test_the_read_must_be_the_very_next_command(self) -> None:
        """`$?` 永遠是**上一個**指令的 rc：隔了別的指令，讀到的就不是管線的 rc。"""
        self.assertTrue(G.waitform_hits("cmd | tail -1; echo $?"))
        self.assertEqual(G.waitform_hits("cmd | tail -1; true; echo $?"), [])

    def test_wait_does_not_exempt_criterion_four(self) -> None:
        """`waitform_hits()` docstring：`wait` 豁免只罩 ①③、不罩 ②④（DEF-200-086）。"""
        self.assertTrue(G.waitform_hits("sh -c 'exit 7' | tail -1; echo $?; wait"))

    def test_the_census_probe_replays_criterion_four(self) -> None:
        """普查探針以預設 `tool` 呼叫判準；預設若改走別處，④ 的假紅普查會靜默失明。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import shell_command_corpus as C  # noqa: PLC0415
        hits = C._predicate_hits("sh -c 'exit 7' | tail -1; echo $?", "waitform")
        self.assertTrue(hits["waitform"])

    def test_the_census_probe_judges_a_powershell_row_like_the_hook(self) -> None:
        """普查探針必須把逐字稿的**工具名**帶進判準：hook 對 PowerShell 不判④（那一側由
        `lint_powershell_command.py` 守），母體若一律以預設 Bash 重放，含 PowerShell 的
        母體（Windows 機）會多報假紅——假紅普查的數字就對不上 hook 真正會擋的集合。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import shell_command_corpus as C  # noqa: PLC0415
        bad = "sh -c 'exit 7' | tail -1; echo $?"
        events = [{"message": {"content": [{"type": "tool_use", "name": name,
                   "input": {"command": bad}}]}} for name in ("Bash", "PowerShell")]
        with tempfile.TemporaryDirectory(prefix="def086-corpus-") as tmp:
            (Path(tmp) / "slug").mkdir()
            (Path(tmp) / "slug" / "s.jsonl").write_text(
                "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
            rows = C.transcript_commands(Path(tmp))
        with mock.patch.object(C, "transcript_commands", return_value=rows):
            recs = C.build(["transcripts"], "waitform")
        self.assertEqual({(r["tool"], bool(r["hits"]["waitform"])) for r in recs},
                         {("Bash", True), ("PowerShell", False)})

    #: 白名單內濾器以 `exit` 傳**有語意的 rc** 的合法用法：判準看不出差別，會被擋
    #: （誤擋方向）。
    _KNOWN_FALSE_POSITIVES = ("cmd | sort -c; echo $?",
                              "cmd | awk '{exit 3}'; echo $?",
                              "cmd | sed '/x/q1'; echo $?")

    def test_the_documented_false_positives_are_hit_and_each_has_an_exit(self) -> None:
        """`waitform_hits()` docstring 的誤擋方向劃界：這三種形態會命中（判準不懂濾器自
        己的 rc 語意），出口是行內 `# waitform-ok: <WHY>`。劃界與行為一起鎖：docstring
        說會擋、實際卻放行（或反之），下一個讀它的人就會信錯方向。"""
        doc = G.waitform_hits.__doc__ or ""
        for needle in ("sort -c", "awk", "sed", "waitform-ok"):
            self.assertIn(needle, doc, f"docstring 沒有劃出誤擋方向：{needle}")
        for command in self._KNOWN_FALSE_POSITIVES:
            with self.subTest(command=command):
                self.assertTrue(G.waitform_hits(command), "劃界說會擋，實際卻放行")
                exempt = run_hook(bash_payload(f"{command}  # waitform-ok: exit 有語意"))
                self.assertEqual(exempt.returncode, 0, exempt.stderr)

    def test_the_shared_helpers_name_all_four_criteria(self) -> None:
        """`_fold`／`has_waitform_exemption` 的 docstring 此前停在「判準①②③」，④ 也走同
        一個遮蔽面與同一個行內豁免——讀它的人會以為 ④ 另有一套。"""
        for fn in (G._fold, G.has_waitform_exemption):
            doc = fn.__doc__ or ""
            self.assertIn("①～④", doc, fn.__name__)
            self.assertNotIn("①②③", doc, fn.__name__)


class TestIronLaw6RcMaskedByPipeScalesLinearly(unittest.TestCase):
    """DEF-200-086：判準④的成本必須與管線數成線性，否則守衛自己就是繞行面。切片版
    （`parts[i + 1:]`）實測 8 萬條管線 19.5～19.8 秒，超過 PreToolUse 的 10 秒逾時＝整支
    hook 被殺＝fail-open，**連毀滅性 git 守衛一併失效**。判準用**比值**不用絕對秒數：慢 CI
    比開發機慢 2～3 倍、再加多 worker 擁擠，固定上界會假紅；比值與機器速度無關（線性約
    8、擁擠下 6.8～11、平方版約 59，門檻 24 兩側各離 2 倍以上）。絕對上限只當逾時保險。"""

    @staticmethod
    def _best_of_three(pipelines: int) -> tuple[float, list]:
        command = "a | tail -1; " * pipelines + "echo $?"
        runs = []
        for _ in range(3):                                    # 取最快一次，避開 GC 抖動
            began = time.perf_counter()
            hits = G.waitform_hits(command)
            runs.append(time.perf_counter() - began)
        return min(runs), hits

    def test_cost_scales_linearly_and_stays_inside_the_hook_timeout(self) -> None:
        small, small_hits = self._best_of_three(10_000)
        large, large_hits = self._best_of_three(80_000)       # 約 1MB
        self.assertTrue(small_hits and large_hits, "大輸入下尾端的真陽沒被判到")
        self.assertLess(large / small, 24,
                        f"輸入放大 8 倍、成本放大 {large / small:.1f} 倍：非線性（平方版約 59）")
        self.assertLess(large, 10.0, f"8 萬條管線 {large:.2f}s：逼近 hook 逾時＝fail-open")


class TestIronLaw6RcMaskedByPipeEndToEnd(unittest.TestCase):
    """真的起 child 行程量 rc ＋ 驗指引可讀（同本檔既有的 end-to-end 紀律）。"""

    _BAD = "sh -c 'exit 7' | tail -1; echo $?"

    def test_exits_two_with_guidance(self) -> None:
        proc = run_hook(bash_payload(self._BAD))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        for needle in ("DEF-200-086", "先導檔", "PIPESTATUS", "pipestatus",
                       "waitform-ok"):
            self.assertIn(needle, proc.stderr)
        self.assertNotIn("until ! pgrep", proc.stderr, "④ 單獨命中不該附等待機制指引")

    def test_the_one_line_fix_leads_the_message(self) -> None:
        """SA-01：正解曾埋在第三段。④ 單獨命中時 stderr 首行就是解法；混合命中仍以
        總綱標頭開頭（兩邊的解法都在，見 `test_mixed_hits_keep_both_fixes`）。"""
        first = run_hook(bash_payload(self._BAD)).stderr.splitlines()[0]
        for needle in ("正解", "echo rc=$?", "DEF-200-086"):
            self.assertIn(needle, first)
        mixed = run_hook(bash_payload(f"nohup ./a.sh > log 2>&1 &\n{self._BAD}")).stderr
        self.assertNotIn("正解", mixed.splitlines()[0])

    def test_the_powershell_tool_passes_the_same_string(self) -> None:
        proc = run_hook({"tool_name": "PowerShell", "tool_input": {"command": self._BAD}})
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_the_correct_forms_pass(self) -> None:
        for command in (
                "sh -c 'exit 7' > /tmp/o.log 2>&1; echo rc=$?; tail -1 /tmp/o.log",
                "sh -c 'exit 7' | tail -1; echo ${pipestatus[1]}"):
            with self.subTest(command=command):
                proc = run_hook(bash_payload(command))
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_exemption_is_its_own_hatch(self) -> None:
        exempt = run_hook(bash_payload(f"{self._BAD}  # waitform-ok: 刻意重現"))
        self.assertEqual(exempt.returncode, 0, exempt.stderr)
        other = run_hook(bash_payload(f"{self._BAD}  # git-guard-ok: 不該放行"))
        self.assertEqual(other.returncode, 2, other.stderr)

    def test_exemption_is_void_when_unattended(self) -> None:
        proc = run_hook(bash_payload(f"{self._BAD}  # waitform-ok: 刻意"),
                        env={G.UNATTENDED_ENV: "1"})
        self.assertEqual(proc.returncode, 2)
        self.assertIn("無人看管", proc.stderr)

    def test_mixed_hits_keep_both_fixes(self) -> None:
        proc = run_hook(bash_payload(f"nohup ./a.sh > log 2>&1 &\n{self._BAD}"))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("DEF-200-086", proc.stderr)
        self.assertIn("until ! pgrep", proc.stderr, "混合命中時等待機制指引不得消失")


class TestIronLaw6RcMaskedByPipeHasTeeth(unittest.TestCase):
    """🔴 合成注入：每個載重零件被拿掉時，判準必須失去鑑別力。
    （同 `TestIronLaw6CriteriaHaveTeeth`）"""

    def test_the_filter_whitelist_is_what_keeps_grep_out(self) -> None:
        good = "ls | grep x; echo $?"
        self.assertEqual(G.waitform_hits(good), [])
        original = G._RCMASK_FILTERS
        try:
            G._RCMASK_FILTERS = original | {"grep"}  # type: ignore[assignment]
            self.assertTrue(G.waitform_hits(good), "白名單加入 grep 後仍放行 ⇒ 不靠它判")
        finally:
            G._RCMASK_FILTERS = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits(good), [])

    def test_keeping_status_inside_double_quotes_is_load_bearing(self) -> None:
        """`echo "rc=$?"` 是最常見的寫法，而雙引號內容預設被遮成空白 ⇒ 讀取整個看不見。"""
        bad = 'make 2>&1 | head -5; echo "rc=$?"'
        self.assertTrue(G.waitform_hits(bad))
        original = G._fold
        try:
            G._fold = lambda command, **kw: original(  # type: ignore[assignment]
                command, **{k: v for k, v in kw.items() if k != "keep_status"})
            self.assertEqual(G.waitform_hits(bad), [],
                             "不保留雙引號內的 `$?` 仍擋得住 ⇒ keep_status 不是載重件")
        finally:
            G._fold = original  # type: ignore[assignment]
        self.assertTrue(G.waitform_hits(bad))

    def test_the_safe_marker_is_load_bearing(self) -> None:
        good = "set -o pipefail; cmd | tail -1; echo $?"
        self.assertEqual(G.waitform_hits(good), [])
        original = G._RCMASK_SAFE_RE
        try:
            G._RCMASK_SAFE_RE = re.compile(r"(?!x)x")  # type: ignore[assignment]
            self.assertTrue(G.waitform_hits(good), "拿掉豁免標記後仍放行 ⇒ 不靠它判")
        finally:
            G._RCMASK_SAFE_RE = original  # type: ignore[assignment]
        self.assertEqual(G.waitform_hits(good), [])

    def test_the_operator_split_is_load_bearing(self) -> None:
        """`2>&1` 的 `&` 不是邊界、`||` 不是兩根管線：天真切法兩個方向各錯一個。"""
        redirect_bad = "cmd | tail -1 2>&1; echo $?"
        or_good = "cmd || tail -1; echo $?"
        self.assertTrue(G.waitform_hits(redirect_bad))
        self.assertEqual(G.waitform_hits(or_good), [])
        original = G._PIPE_OPS_RE
        try:
            G._PIPE_OPS_RE = re.compile(r"([|;&\n()`])")  # type: ignore[assignment]
            self.assertEqual(G.waitform_hits(redirect_bad), [],
                             "天真切法竟仍擋得住 ⇒ 重導的 `&` 辨識不是載重件")
            self.assertTrue(G.waitform_hits(or_good),
                            "天真切法竟未誤擋 `||` ⇒ 兩字元運算子優先序不是載重件")
        finally:
            G._PIPE_OPS_RE = original  # type: ignore[assignment]
        self.assertTrue(G.waitform_hits(redirect_bad))
        self.assertEqual(G.waitform_hits(or_good), [])


class TestTheFalsePositiveCensusIsRerunnable(unittest.TestCase):
    """🔴 假紅普查必須留下**可重跑**的產物（`DEF-200-046`／SD-04）。

    立案事實：根 CLAUDE.md 鐵律五自陳做過一次「假陽性 0」的普查，而 repo 裡**一支產物
    都沒有** ⇒ 交棒書要求後人「用同樣的方法」結構上做不到（沒有共同母體、沒有去重規則、
    沒有逐筆歸屬理由）。逐筆數字＝R89 收尾證據檔。
    """

    _PROBE = _REPO_ROOT / "tools" / "probe" / "shell_command_corpus.py"

    def test_the_corpus_extractor_exists_and_is_importable(self) -> None:
        self.assertTrue(self._PROBE.is_file(), f"{self._PROBE} 不存在")
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import shell_command_corpus as C  # noqa: PLC0415 — 刻意在測試內 import
        for name in ("tracked_fragments", "transcript_commands", "build"):
            self.assertTrue(callable(getattr(C, name, None)), name)

    def test_the_anchor_covers_every_criterion_trigger_token(self) -> None:
        """🔴 本輪自己踩過的假綠：第一版的 tracked 面錨**只有 git token**，於是
        `waitform` 在那一面恆為 0 命中——而**零命中與「這一面很乾淨」在輸出上完全同形**。
        判準集合長大時錨沒跟著長，普查就會靜默地量錯東西。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import shell_command_corpus as C  # noqa: PLC0415
        for token in ("git", "nohup", "disown", "setsid", "pgrep"):
            with self.subTest(token=token):
                self.assertTrue(C._ANCHOR_RE.search(f"foo {token} bar"),
                                f"語料抽取器的錨看不到 `{token}` ⇒ 該判準的普查會恆為 0 命中")

    def test_the_census_surface_is_the_transcripts_not_tracked_files(self) -> None:
        """SD-02：R83 教的「tracked 檔普查」對鐵律六是**錯的量測面**。

        tracked 面上 `waitform` 的命中全部落在 `.md` 散文，而 hook 結構上讀不到 `.md`
        ⇒ 照 tracked 面判會得到「全是假紅」的錯誤結論並否決一個好判準（逐筆實測＝
        R89 收尾證據檔）。本條把那個知識釘進程式碼。
        """
        # 🔴 讀**原始碼**而不是 `__doc__`：那段 WHY 刻意住在 `#` 註解裡而不是 docstring，
        # 因為 `count_loc` 排除純 `#` 行而計入 docstring ⇒ 同一份 WHY 寫成註解是 0 行成本。
        # 🔴 誠實劃界：根層 `tools/` 是**獨立帳**（`check_loc_budget.py` 逐字寫「不進 total／
        # baseline cap」）⇒ 全庫 total 的餘裕與本檔無關，真正咬人的是 tier。
        source = self._PROBE.read_text(encoding="utf-8")
        self.assertIn("假紅普查一律以", source)
        self.assertIn("transcripts", source)

    def test_the_transcript_extractor_reads_the_same_field_the_hook_reads(self) -> None:
        """合成一份逐字稿，證明抽取器取的是 `tool_use` 的 `input.command`。

        這是本檔唯一需要「真的抽一次」的地方，故用**合成語料**而不是掃全機逐字稿：
        後者是分鐘級、且結果隨機器而異，那種測試在 CI 上不是綠就是慢，兩者都沒有鑑別力。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools" / "probe"))
        import shell_command_corpus as C  # noqa: PLC0415
        with tempfile.TemporaryDirectory(prefix="w8-corpus-") as tmp:
            proj = Path(tmp) / "slug"
            proj.mkdir()
            events = [
                {"message": {"content": [
                    {"type": "tool_use", "name": "Bash",
                     "input": {"command": "nohup ./a.sh & echo x"}}]}},
                {"message": {"content": [
                    {"type": "tool_use", "name": "Read",
                     "input": {"file_path": "/x"}}]}},   # 非 shell 工具 ⇒ 不進語料
                "{ 這一列是壞 JSON",                      # 尾列半截是常態，必須靜默跳過
            ]
            (proj / "s.jsonl").write_text(
                "".join((e if isinstance(e, str) else
                         json.dumps(e, ensure_ascii=False)) + "\n" for e in events),
                encoding="utf-8")
            rows = C.transcript_commands(Path(tmp))
        self.assertEqual([r[0] for r in rows], ["nohup ./a.sh & echo x"])
        self.assertIn("tool_input.command", rows[0][2])   # 逐筆歸屬理由必須寫出欄位來源


class TestTheHookStaysInsideItsLocTier(unittest.TestCase):
    """🔴 鐵律六那一族是加在**既有** hook 上的，而該檔一直是這一層最靠近上限的檔之一。
    史料搬至 CrossPlatform_R190_FixRound_Evidence.md〈九-F〉§48。"""

    def test_the_hook_is_within_its_root_tools_tier(self) -> None:
        sys.path.insert(0, str(_REPO_ROOT / "AutoClaude" / "tools"))
        import check_loc_budget as B  # noqa: PLC0415
        loc = B.count_loc(_HOOK)
        budget = B.ROOT_TOOLS_TIERS["guardrail_cli"]["budget"]
        self.assertLessEqual(
            loc, budget,
            f"{_HOOK.name} count_loc={loc} 超出 guardrail_cli tier {budget}。"
            f"修法不是調高預算（本 repo 明文禁止放寬既有門檻），而是把判準族抽到 "
            f"tools/lib/ 的共用模組")


# ══════════════════════════════════════════════════════════════════════════════
# R84：兩條**已知**缺口的第一個真實命中 — Python 層 git 呼叫 ＋ 殼 heredoc body
# ══════════════════════════════════════════════════════════════════════════════
# 立案事實與「已知並劃界＝結案」教訓（DEF-101-757 判例）——
# 原文＝GovWrite 證據檔 §6.5；下兩張表＝劃界的到期日。
_CULPRIT = (
    "cd /Users/wuweihong/Antigravity/AISDCL_Agent; .venv/bin/python - <<'PY'\n"
    "import sys, pathlib, subprocess, tempfile, os\n"
    'sys.path.insert(0,"tools")\n'
    "print(type(cur), len(cur))\n"
    "# find which are not in HEAD\n"
    'head = subprocess.run(["git","stash"],capture_output=True)  # NO\n'
    "PY"
)

#: 鑑識當回合對**修訂前**的 hook 餵真 payload 量到的五種形態（exit 2＝擋、0＝放行）。
#: 「修訂前」那一欄刻意留在表裡：它是這道鎖存在的理由，不是歷史註記——A/E/G 三種
#: **各自單獨**就足以把工作樹清空，而三者當時全部放行。
_FIVE_FORMS: tuple[tuple[str, str], ...] = (
    ("A 原凶逐字（heredoc 內 argv-list）", _CULPRIT),
    ("B 裸 git stash", "git stash"),
    ("E heredoc 內以 os 模組 system() 起殼",
     "python - <<'PY'\nimport os\nos.system('git stash')\nPY"),
    ("G 無 heredoc、argv-list",
     "python -c \"import subprocess; subprocess.run(['git','stash'])\""),
    ("H 純 shell", "git stash push -u"),
)


class TestR84BothGapsAreClosed(unittest.TestCase):
    """🔴 五種形態**全部**要擋——修訂前 A/E/G 是 0（放行）、B/H 是 2。

    WHY 要五種一起釘、不能只釘原凶：鑑識實測 **兩條缺口各自單獨就足以放行**
    （#6 heredoc body 被 `mask_inert()` 當資料遮掉；#1 不經殼的 Python 呼叫）
    ⇒ 只補一條的修法會在另一條上靜默地繼續漏，而漏的表徵與修好完全相同（rc=0）。
    """

    def test_all_five_forensic_forms_are_blocked(self) -> None:
        for name, command in _FIVE_FORMS:
            with self.subTest(form=name):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                    f"{name} 被放行——這正是 2026-08-12 那次清空工作樹的形狀")

    def test_end_to_end_the_culprit_exits_two(self) -> None:
        proc = run_hook({"tool_name": "Bash", "cwd": str(_REPO_ROOT),
                         "tool_input": {"command": _CULPRIT}})
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("git stash create", proc.stderr, "只擋不教的守衛會被拔掉")

    def test_a_shell_fed_heredoc_body_really_executes_so_it_is_judged(self) -> None:
        """`bash <<'EOF'` 的 body **會**執行 ⇒ 它是可執行結構，不是資料。"""
        for command in ("bash <<'EOF'\ngit stash\nEOF",
                        "/bin/bash <<EOF\ngit reset --hard\nEOF",
                        "ssh host bash <<'EOF'\ngit clean -fdx\nEOF"):
            with self.subTest(command=command):
                self.assertTrue(G.destructive_git_hits(command,
                                                       start_dir=str(_REPO_ROOT)))

    def test_a_python_fed_heredoc_body_is_still_data(self) -> None:
        """🔴 放行面：`python - <<'PY'` 是寫探針的標準寫法。整族判成可執行結構就是
        一整類誤擋，而誤擋是這道鎖被關掉的路徑（repo 判例）。"""
        for command in ("python - <<'PY'\nprint('git stash')\nPY",
                        "cat <<'EOF' > /tmp/n.md\n執行 git stash 會清空工作樹\nEOF",
                        "cat <<EOF\ngit reset --hard 很危險\nEOF"):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command,
                                                        start_dir=str(_REPO_ROOT)), [])


class TestR84TheArgvPlaneDoesNotOverBlock(unittest.TestCase):
    """假紅是這道鎖的生死線。本類逐條釘住普查裡**實測到**的假紅來源。

    普查母體＝逐字稿的 `tool_use` 指令字串（可重跑，見 `shell_command_corpus.py`）；
    逐筆數字與判讀＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
    """

    ALLOWED = (
        # 🔴 收窄前實測的 3 筆假紅：一串**命令字串**的 tuple（探針表），不是 argv
        '("git checkout -p","git checkout -p -- tools/","git restore -p")',
        'CASES = {"A": "git stash", "B": "git reset --hard"}',
        'probes = [("行接續", "git stash -q -u"), ("清乾淨", "git clean -fdx")]',
        # 具名呼叫者的錨：沒有它，下面兩條會變成假紅
        "python -c \"print('git clean -fd')\"",
        'python -c "print([1,2,3]); print(\'git reset --hard\')"',
        # 殼陣列沒有逗號 ⇒ 不是 Python 序列字面
        'FILES=("git" "stash"); echo ${FILES[@]}',
        # 唯讀 git 的 argv-list 一樣要放行（射程是**動詞**不是「出現 git」）
        'subprocess.run(["git","status","--porcelain"])',
        "python -c \"import subprocess; subprocess.run(['git','stash','list'])\"",
        # 安全暫停 SOP 的 argv 形態
        'subprocess.run(["git","stash","create"])',
    )

    def test_none_of_the_measured_false_positive_shapes_is_blocked(self) -> None:
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                    f"{command!r} 被誤擋——擋到讓人無法工作的守衛會被整個關掉")

    def test_the_destructive_argv_forms_are_blocked(self) -> None:
        for command in ('subprocess.run(["git","stash"])',
                        "subprocess.run(['git','stash','pop'])",
                        'subprocess.check_call(["git","reset","--hard","HEAD~1"])',
                        'Popen(["git","clean","-fdx"])',
                        'subprocess.run(["/usr/bin/git","checkout","--","CLAUDE.md"])',
                        "os.system('git reset --hard')",
                        'os.popen("git clean -fdx")'):
            with self.subTest(command=command):
                self.assertTrue(G.destructive_git_hits(command,
                                                       start_dir=str(_REPO_ROOT)), command)

    def test_the_argv_plane_is_fail_closed_about_where_it_lands(self) -> None:
        """`cwd=` kwarg 本守衛看不見 ⇒ argv 面一律不套用換樹放寬（方向是 fail-closed）。"""
        with tempfile.TemporaryDirectory(prefix="w-argv-") as foreign, \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertTrue(G.destructive_git_hits(
                f'subprocess.run(["git","clean","-fdx"], cwd="{foreign}")',
                start_dir=str(_REPO_ROOT)))


class TestR84TheNewCriteriaHaveTeeth(unittest.TestCase):
    """🔴 合成注入：每個新零件被拿掉時，判準必須**當場失去鑑別力**。

    反 vacuity 是本檔既有紀律（見 `TestTheCriterionItselfCanFail`）——沒有這幾條，
    上面兩張表只能證明「今天恰好對」，不能證明「是靠哪個零件對的」。
    """

    def test_the_argv_plane_is_load_bearing(self) -> None:
        """把 argv 正規化面關掉 ⇒ **原凶當場變回放行**（＝修訂前逐字的行為）。"""
        self.assertTrue(G.destructive_git_hits(_CULPRIT, start_dir=str(_REPO_ROOT)))
        with mock.patch.object(G, "argv_git_fragments", lambda _c: ""):
            self.assertEqual(
                G.destructive_git_hits(_CULPRIT, start_dir=str(_REPO_ROOT)), [],
                "argv 面關掉後竟仍擋下 ⇒ 擋住原凶的不是這次的修法")
        self.assertTrue(G.destructive_git_hits(_CULPRIT, start_dir=str(_REPO_ROOT)))

    def test_masking_the_heredoc_body_is_what_hid_it(self) -> None:
        """🔴 這一條把「兩條缺口各自單獨就足以放行」釘成事實。

        單獨修 heredoc（＝讓 body 可見）對原凶**沒有用**：body 裡是 Python 的
        argv list，不是殼形態。鑑識實測逐字「對原凶 body 單獨判 → 無命中」。
        """
        body = ('import sys, pathlib, subprocess, tempfile, os\n'
                'head = subprocess.run(["git","stash"],capture_output=True)  # NO\n')
        with mock.patch.object(G, "argv_git_fragments", lambda _c: ""):
            self.assertEqual(
                G.destructive_git_hits(body, start_dir=str(_REPO_ROOT)), [],
                "只靠殼形態判準就擋得住 body ⇒ 那 A 修法單獨可行，本註記是假的")

    def test_the_shell_owner_test_is_load_bearing(self) -> None:
        """把 heredoc 擁有者判準弄成恆假 ⇒ `bash <<EOF` 的 body 回到「當資料遮掉」。"""
        command = "bash <<'EOF'\ngit reset --hard\nEOF"
        self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))
        original = G._SHELL_EXE_RE
        try:
            G._SHELL_EXE_RE = re.compile(r"(?!x)x")  # type: ignore[assignment]
            self.assertEqual(
                G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                "擁有者判準恆假時仍擋下 ⇒ 擋住殼 heredoc 的不是它")
        finally:
            G._SHELL_EXE_RE = original  # type: ignore[assignment]
        self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))

    def test_the_owner_test_must_not_be_widened_to_every_heredoc(self) -> None:
        """反向：擁有者判準恆**真**時，`cat <<EOF` 的散文會變成假紅（實測 2 筆）。"""
        prose = "cat <<'EOF' > /tmp/n.md\n執行 git reset --hard 會清空工作樹\nEOF"
        self.assertEqual(G.destructive_git_hits(prose, start_dir=str(_REPO_ROOT)), [])
        original = G._SHELL_EXE_RE
        try:
            G._SHELL_EXE_RE = re.compile(r"")  # type: ignore[assignment] — 恆真
            self.assertTrue(
                G.destructive_git_hits(prose, start_dir=str(_REPO_ROOT)),
                "擁有者判準恆真竟沒有製造假紅 ⇒ 這條收窄沒有在守任何東西")
        finally:
            G._SHELL_EXE_RE = original  # type: ignore[assignment]

    def test_the_first_literal_must_be_git_check_is_load_bearing(self) -> None:
        """🔴 收窄「序列的第一個字面必須是 git 執行檔」——全語料實測它收掉 3 筆假紅。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§10。"""
        table = '("git checkout -p","git checkout -p -- tools/","git restore -p")'
        self.assertEqual(G.destructive_git_hits(table, start_dir=str(_REPO_ROOT)), [])

        def unnarrowed(command: str) -> str:      # 收窄前逐字的實作
            return ";".join(
                " ".join(t for _q, t in G._ARGV_LIT_RE.findall(m.group(0)))
                for m in G._ARGV_SEQ_RE.finditer(command))

        with mock.patch.object(G, "argv_git_fragments", unnarrowed):
            self.assertTrue(
                G.destructive_git_hits(table, start_dir=str(_REPO_ROOT)),
                "收窄前的實作竟沒有製造那筆假紅 ⇒ 這條收窄沒有承重")
        self.assertEqual(G.destructive_git_hits(table, start_dir=str(_REPO_ROOT)), [])


# ══════════════════════════════════════════════════════════════════════════════
# R84 偵測層：攔截器**結構上**接不到的那一半
# ══════════════════════════════════════════════════════════════════════════════
class TestR84StashRefSentinel(unittest.TestCase):
    """🔴 誠實劃界要求的另一半：擋不到的必須**看得見**。判準刻意只看 `refs/stash`（只會因 stash
    push／pop／drop／clear 而變）；被測端＝`.claude/hooks/block_destructive_git.py` 的
    `stash_ref_sentinel`。結構上碰不到的四條路與第一版為何不看 `logs/HEAD`，逐字＝
    `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。"""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="w-sentinel-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / ".git" / "refs").mkdir(parents=True)
        self.ref = self.root / ".git" / "refs" / "stash"

    def test_the_first_call_only_records_a_baseline(self) -> None:
        """沒有基線就不可能有「變了」——第一次一律靜默（否則每個新 clone 都會噴一次）。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        self.assertIsNone(G.stash_ref_sentinel(str(self.root)))

    def test_a_change_nobody_declared_is_reported(self) -> None:
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root))
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        note = G.stash_ref_sentinel(str(self.root))
        self.assertIsNotNone(note)
        self.assertIn("refs/stash", note or "")

    def test_a_stash_the_guard_already_saw_is_not_reported(self) -> None:
        """🔴 假紅面為零就靠這個 ack 位元：上一次呼叫**真的帶著一次會改 `refs/stash` 的
        呼叫、而且那次呼叫沒有被本守衛擋下** ⇒ 那次變動**不是隱形的路**。
        史料搬至 CrossPlatform_Guard_Line_History_2.md〈R190 收尾棒〉§2。 round-label-ok"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root), ack=True)
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        self.assertIsNone(G.stash_ref_sentinel(str(self.root)))

    def test_no_change_is_silent(self) -> None:
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root))
        self.assertIsNone(G.stash_ref_sentinel(str(self.root)))

    def test_a_dropped_stash_counts_as_a_change(self) -> None:
        """`git stash drop`／`clear` 會讓整個 ref 消失——那一向同樣是「有人動了它」。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root))
        self.ref.unlink()
        self.assertIsNotNone(G.stash_ref_sentinel(str(self.root)))

    def test_it_never_raises_on_a_missing_or_unwritable_git_dir(self) -> None:
        """fail-open 是本檔的 P0：守衛自身絕不可成為故障源。"""
        with tempfile.TemporaryDirectory(prefix="w-no-git-") as empty:
            self.assertIsNone(G.stash_ref_sentinel(empty))

    def test_end_to_end_the_note_is_an_advisory_not_an_error(self) -> None:
        """🔴 rc 必須是 0：偵測不是攔截（2 會擋無關工具呼叫；1 被 CC 標成 hook error，
        DEF-200-440 同族）。提醒走 `emit_to_model`＝stdout 單一 JSON，stderr 必須空。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        payload = {"tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "echo hi"}}
        first = run_hook(payload)
        self.assertEqual((first.returncode, first.stdout, first.stderr), (0, "", ""))
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        proc = run_hook(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "", "提醒走 stdout JSON，stderr 必須空")
        hso = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertIn("refs/stash", hso["additionalContext"])

    def test_a_note_riding_a_blocked_call_stays_in_stderr_exactly_once(self) -> None:
        """要阻斷時 note 照舊併進 stderr（rc=2 不變）；不得再 emit 一份造成重複。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        payload = {"tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "echo hi"}}
        run_hook(payload)  # 記基線
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        proc = run_hook({**payload, "tool_input": {"command": "git stash push -u"}})
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(proc.stderr.count("🔴 refs/stash"), 1, proc.stderr)
        self.assertEqual(proc.stdout, "", "阻斷路徑不得再送 additionalContext")

    def test_the_state_file_lives_next_to_the_thing_it_watches(self) -> None:
        """狀態檔住 `.git/`（不是 tempdir）⇒ 天生逐 repo 隔離，兩個 checkout 不互相汙染。
        寫進共用 tempdir 的版本會讓「換一個 repo 工作」每次都噴一則假警報。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root))
        self.assertTrue((self.root / ".git" / "autosdd_stash_sentinel").is_file())


# ══════════════════════════════════════════════════════════════════════════════
# R84 四方複審抓到的「載具類」漏擋（SD-01／02／04／06／07／08）— 每一條都是當回合實測
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 共同形態＝「同一件事，只因換了一個載具就一擋一放」（敘事原文＝GovWrite 證據檔
# §6.8）⇒ 下面每一張表都刻意用**同一個毀滅性子指令**跑過所有載具。
_D_SUBS = ("git stash", "git reset --hard", "git clean -fdx", "git checkout -- CLAUDE.md")


class TestR84TheDashCCarrierIsJudged(unittest.TestCase):
    """SD-01（blocking）：`sh -c '<毀滅性 git>'` 修訂前實測 exit 0，而**同一件事**寫成
    `bash <<'EOF'` 是 exit 2。成因與 heredoc 完全同構——`mask_inert()` 把引號內容當資料
    遮掉 ⇒ `git_invocations("sh -c '…'")` 回 `[]`。修法也同構：operand 當獨立平面遞迴
    餵回 `git_invocations()`，**不開第二套子指令判準**。"""

    def test_every_shell_carrier_x_every_destructive_sub_is_blocked(self) -> None:
        for carrier in ("sh -c '{}'", 'bash -c "{}"', "zsh -c '{}'", "ksh -c '{}'",
                        'dash -c "{}"', "/bin/bash -c '{}'", "bash -lc '{}'",
                        'pwsh -Command "{}"', 'eval "{}"', "eval '{}'",
                        "xargs -I@ sh -c '{} @'"):
            for sub in _D_SUBS:
                command = carrier.format(sub)
                with self.subTest(command=command):
                    self.assertTrue(
                        G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                        f"{command!r} 被放行——換一個載具就繞過守衛")

    def test_a_nested_carrier_is_still_reached(self) -> None:
        """`sh -c "…sh -c '…'"`：operand 自己再包一層 ⇒ 遞迴必須跟得上。"""
        self.assertTrue(G.destructive_git_hits(
            """sh -c "cd /tmp && sh -c 'git stash pop'" """, start_dir=str(_REPO_ROOT)))

    def test_the_carrier_plane_does_not_over_block(self) -> None:
        """🔴 放行面：載具本身不是罪名，operand 的**動詞**才是。"""
        for command in ("bash -c 'git status --porcelain'",
                        "sh -c 'git stash create'",
                        'bash -c "git stash list"',
                        "sh -c 'git checkout -b feature/x'",
                        "bash -c 'git clean -n'",
                        "sh -c 'echo hi && ls'",
                        # 非殼的 `-c` 不是本判準的錨（`python -c` 走 argv 面，見既有表）
                        "python -c \"print('git clean -fd')\"",
                        # 字內巧合不得命中（`_SHELLS` 兩側的字元邊界）
                        "install_bash_helpers -c 'git stash'",
                        "foo.sh -c 'git stash'"):
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                    f"{command!r} 被誤擋——誤擋是這道鎖被整個關掉的路徑")

    def test_end_to_end_the_carrier_exits_two(self) -> None:
        proc = run_hook({"tool_name": "Bash", "cwd": str(_REPO_ROOT),
                         "tool_input": {"command": "sh -c 'git stash -q -u --keep-index'"}})
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("git stash create", proc.stderr, "只擋不教的守衛會被拔掉")

    def test_the_carrier_plane_is_load_bearing(self) -> None:
        """合成注入：把 `-c` 平面關掉 ⇒ 當場變回修訂前逐字的行為（exit 0）。"""
        command = "sh -c 'git reset --hard'"
        self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))
        original = G._CARRIER_RE
        try:
            G._CARRIER_RE = re.compile(r"(?!x)x")  # type: ignore[assignment]
            self.assertEqual(
                G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                "`-c` 平面關掉後仍擋下 ⇒ 擋住它的不是這次的修法")
        finally:
            G._CARRIER_RE = original  # type: ignore[assignment]
        self.assertTrue(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)))

    def test_the_relaxation_killers_also_run_on_the_carrier_plane(self) -> None:
        """🔴 這一條是落地當回合**自測抓到的洞**，不是事後補的裝飾。
        史料搬至 CrossPlatform_R190_FixRound_Evidence.md〈九-F〉§49。"""
        with tempfile.TemporaryDirectory(prefix="w-carrier-") as foreign, \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertEqual(
                G.destructive_git_hits(f"sh -c 'cd {foreign} && git clean -fdx'",
                                       start_dir=str(_REPO_ROOT)), [],
                "operand 內老實的 `cd` 到外樹被誤擋（那是真的會落在外樹）")
            self.assertTrue(
                G.destructive_git_hits(f"sh -c '(cd {foreign}); git clean -fdx'",
                                       start_dir=str(_REPO_ROOT)),
                "子殼括號讓 cd 的作用域在 `)` 就結束，git 其實落在共用工作樹 ⇒ 必須擋")


class TestR84ATrailingCommaDoesNotSmuggleItPast(unittest.TestCase):
    """SD-02（blocking）：`argv_git_fragments('x=([ "git","stash", ])')` 修訂前回 `''`。

    🔴 嚴重性不在「少擋一種怪寫法」，而在 **`black` 的多行格式預設就會產生尾逗號** ⇒
    R84 才剛關上的那條 P0（原凶 argv-list）**只要被格式化成多行就自動逃掉**。
    """

    def test_the_one_character_that_undid_the_p0(self) -> None:
        self.assertEqual(G.argv_git_fragments('x=([ "git","stash" ])'), "git stash")
        self.assertEqual(G.argv_git_fragments('x=([ "git","stash", ])'), "git stash")

    def test_black_multiline_formatting_of_the_culprit_is_blocked(self) -> None:
        """逐字用 `black` 會排出來的樣子（每個元素一行、尾逗號、右括號另起一行）。"""
        formatted = (
            "python - <<'PY'\n"
            "head = subprocess.run(\n"
            "    [\n"
            '        "git",\n'
            '        "stash",\n'
            "    ],\n"
            "    capture_output=True,\n"
            ")\n"
            "PY")
        self.assertTrue(G.destructive_git_hits(formatted, start_dir=str(_REPO_ROOT)),
                        "原凶被 black 排一下就逃掉了")

    def test_the_optional_last_element_is_load_bearing(self) -> None:
        """合成注入＝收窄前逐字的 regex（末元素必填）⇒ 尾逗號那條當場放行。"""
        with_comma = 'subprocess.run(["git","stash",])'
        self.assertTrue(G.destructive_git_hits(with_comma, start_dir=str(_REPO_ROOT)))
        original = G._ARGV_SEQ_RE
        try:
            G._ARGV_SEQ_RE = re.compile(  # type: ignore[assignment] — 修訂前逐字
                r"""[\[(]\s*(?:(['"])[^'"]*\1\s*,\s*)+(['"])[^'"]*\2\s*[\])]"""
                r"""|(?:os\.(?:system|popen)|subprocess\.\w+|Popen)\s*\(\s*(['"])\s*"""
                r"""(?:[^\s'"\\/]*[\\/])?git(?:\.exe)?\s[^'"]*\3""")
            self.assertEqual(
                G.destructive_git_hits(with_comma, start_dir=str(_REPO_ROOT)), [],
                "修訂前的 regex 竟仍擋下 ⇒ 這條修法沒有承重")
        finally:
            G._ARGV_SEQ_RE = original  # type: ignore[assignment]

    def test_it_does_not_widen_the_false_positive_surface(self) -> None:
        """尾逗號放寬**不得**把既有那三筆假紅（命令字串表）換回來。"""
        for command in ('("git checkout -p","git checkout -p -- tools/","git restore -p",)',
                        'CASES = {"A": "git stash", "B": "git reset --hard",}',
                        'FILES=("git" "stash"); echo ${FILES[@]}'):
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [], command)


class TestR84TheHeredocOwnerIsTheNearestExecutable(unittest.TestCase):
    """SD-06（medium）：擁有者判定掃「整行」⇒ 路徑裡一個 `/sh` 就把 python heredoc 判成殼。

    🔴 方向是**誤擋**，而誤擋正是本 repo 明文說會讓守衛被整個拔掉的那一類——而且被擋死的
    正好是「寫探針的人」，也就是修這道鎖的人自己。
    """

    def test_a_path_containing_sh_does_not_make_python_a_shell(self) -> None:
        body = "cd {} && python - <<'PY'\nprint('x')\ngit reset --hard\nPY"
        for prefix in ("/tmp/sh", "/opt/sh", "/private/tmp/sh"):
            with self.subTest(prefix=prefix):
                self.assertEqual(
                    G.destructive_git_hits(body.format(prefix), start_dir=str(_REPO_ROOT)),
                    [], f"{prefix} 讓 python 的 heredoc 被當成殼結構 ⇒ 誤擋")

    def test_an_unrelated_mention_of_a_shell_name_does_not_either(self) -> None:
        for command in ("grep -rn bash docs/ && python - <<'PY'\ngit clean -fdx\nPY",
                        "echo zsh; cat <<'EOF' > /tmp/n.md\ngit reset --hard 很危險\nEOF"):
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [], command)

    def test_the_nearest_token_rule_still_finds_the_real_shell(self) -> None:
        """由右往左找**最近的非旗標 token**，所以前綴／遠端包裝都還是判得出來。"""
        for command in ("ssh host bash <<'EOF'\ngit clean -fdx\nEOF",
                        "sudo bash <<'EOF'\ngit reset --hard\nEOF",
                        "env FOO=1 bash <<'EOF'\ngit stash\nEOF",
                        "/bin/bash -s <<EOF\ngit reset --hard\nEOF",
                        "cat /tmp/x | bash <<'EOF'\ngit stash pop\nEOF"):
            with self.subTest(command=command):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), command)

    def test_scanning_the_whole_line_is_what_caused_the_over_block(self) -> None:
        """合成注入＝修訂前逐字的「整行 search」⇒ 上面那條 python heredoc 當場變假紅。"""
        command = "cd /tmp/sh && python - <<'PY'\ngit reset --hard\nPY"
        self.assertEqual(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [])
        original = G.mask_inert
        old_owner = re.compile(
            r"(?<![\w.-])(?:sh|bash|zsh|ksh|dash|pwsh|powershell)(?![\w.-])", re.IGNORECASE)

        def old_mask(text: str, *, keep_comments: bool = False) -> str:
            # 修訂前的行為：擁有者＝「`<<` 所在那一行有沒有出現殼的名字」
            with mock.patch.object(
                    G, "_SHELL_EXE_RE",
                    re.compile(r"") if old_owner.search(text) else re.compile(r"(?!x)x")):
                return original(text, keep_comments=keep_comments)

        with mock.patch.object(G, "mask_inert", old_mask):
            self.assertTrue(
                G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                "整行 search 竟沒有製造那筆誤擋 ⇒ 這條收窄沒有在守任何東西")
        self.assertEqual(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [])


class TestR84WorktreeRemoveForce(unittest.TestCase):
    """SD-07（medium）：`git worktree remove --force` 修訂前實測 exit 0。

    🔴 判準是**量出來的**（全語料新舊對跑：新增命中逐筆判讀全是「拆自己的拋棄式樹」
    ⇒ 收窄成「被拆的是誰」，舊擋新放 0 種）：普查數字原文＝GovWrite 證據檔 §6.6。
    """

    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_removing_a_tree_this_guard_cannot_vouch_for_is_blocked(self) -> None:
        for command in ("git worktree remove --force /tmp/nope-wt",
                        "git worktree remove -f /tmp/nope-wt",
                        "git worktree remove /tmp/nope-wt --force",
                        "sh -c 'git worktree remove --force /tmp/nope-wt'"):
            with self.subTest(command=command):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), command)

    def test_the_measured_routine_teardown_shapes_are_allowed(self) -> None:
        """🔴 放行面＝語料裡真的撞到的那三類，逐字重建（不是好寫測試的簡化版）。"""
        with tempfile.TemporaryDirectory(prefix="w-wt-") as foreign:
            cases = (
                f"git worktree remove --force {foreign}",
                f"cd {os.path.dirname(foreign)} && "
                f"git worktree remove --force {os.path.basename(foreign)}",
                f"git worktree remove --force {_REPO_ROOT}/.claude/worktrees/agent-ac3ed",
                f"git worktree remove {foreign}",          # 不帶 --force：git 自己會拒絕
                "git worktree list",
                f"git worktree add -q {foreign}/x HEAD",
                "git worktree prune",
            )
            for command in cases:
                with self.subTest(command=command):
                    self.assertEqual(
                        G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                        f"{command!r} 被誤擋——全語料實測這一類佔新增命中的 100%")

    def _as_windows(self) -> tuple:
        """把 Windows 的路徑語意**整包**顯式注入：`os.path` → `ntpath`。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§11。"""
        return mock.patch.object(G.os, "path", ntpath)

    def test_the_mixed_separator_shape_is_judged_on_every_platform(self) -> None:
        """🔴 R96 收尾／B-8：混合分隔符那條放行路必須在**兩個平台**都真的走得進去。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§12。"""
        victim = str(_REPO_ROOT).replace("/", "\\") + "/.claude/worktrees/agent-ac3ed"
        command = f"git worktree remove --force {victim}"
        with self._as_windows():
            self.assertEqual(
                G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                "混合分隔符的拋棄式樹被誤擋 ⇒ 正規化那一格在本平台失明；"
                "普查明載這一類佔新增命中的 100%，而誤擋是這道鎖被整個關掉的路徑")
            # 紅綠自證：識別函式若判不出這是拋棄式樹，同一條指令當場改判擋下。
            with mock.patch.object(G, "is_under_disposable_worktree", lambda _p: False):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                    "識別函式拿掉後竟仍放行 ⇒ 這條鎖沒有承重")

    def test_the_windows_case_insensitive_shape_is_judged(self) -> None:
        """🔴 R96 收尾／B-8 的配套鎖（`normcase` 換法一併治好的第二個 Windows 失明）。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§13。"""
        victim = str(_REPO_ROOT).replace("/", "\\") + "\\.CLAUDE\\WORKTREES\\agent-ac3ed"
        command = f"git worktree remove --force {victim}"
        with self._as_windows():
            self.assertEqual(
                G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                "大小寫不同的同一棵拋棄式樹被誤擋（NTFS 不區分大小寫）")
            # 紅綠自證：識別函式若判不出這是拋棄式樹，同一條指令當場改判擋下。
            with mock.patch.object(G, "is_under_disposable_worktree", lambda _p: False):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                    "識別函式拿掉後竟仍放行 ⇒ 大小寫那一半沒有承重")

    def test_the_relaxation_is_load_bearing_in_both_directions(self) -> None:
        """紅綠自證：拿掉放行條件 ⇒ 那三類 routine teardown 當場全變假紅。"""
        with tempfile.TemporaryDirectory(prefix="w-wt2-") as foreign:
            command = f"git worktree remove --force {foreign}"
            self.assertEqual(G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [])
            with mock.patch.object(G, "is_foreign_tree", lambda _p: False), \
                    mock.patch.object(G, "is_under_disposable_worktree", lambda _p: False):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                    "放行條件拿掉後竟仍放行 ⇒ 這條收窄沒有承重")

    def test_dotdot_traversal_disguised_as_disposable_worktree_is_blocked(self) -> None:
        """P0-1：字面上帶著拋棄式樹前綴、`..` 解開後其實落在樹外（甚至是 repo 根自己）的
        `git worktree remove --force`，不得被舊版的純字串包含判準放行。
        史料搬至 CrossPlatform_R189_SessionGate_Family_Lock_Audit_Evidence.md〈九-F〉§14。"""
        for suffix in (r"\.claude\worktrees\..\..\AutoClaude", r"\.claude\worktrees\..\.."):
            victim = str(_REPO_ROOT) + suffix
            command = f"git worktree remove --force {victim}"
            with self.subTest(command=command):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)),
                    f"{victim!r} 的 `..` 穿越竟被放行——realpath 後它不在拋棄式樹底下")

    def test_checkout_index_force_is_in_scope_but_apply_reverse_is_not(self) -> None:
        """同族的另外兩個動詞，判斷結果與理由都釘在這裡（不是漏看）。

        · `git checkout-index -f`：用 index 強制覆寫工作樹 ⇒ 收。全語料命中 0 ⇒ 假紅面為零。
        · `git apply -R`：把剛套上的 patch **退回去**的正當手法，而且可逆（再套一次就回來）
          ⇒ **刻意不收**。擋它是製造誤擋，方向與本檔的設計約束相反。
        """
        self.assertTrue(G.destructive_git_hits("git checkout-index -f -a",
                                               start_dir=str(_REPO_ROOT)))
        for allowed in ("git checkout-index -a", "git apply -R /tmp/p.patch",
                        "git apply /tmp/p.patch"):
            with self.subTest(command=allowed):
                self.assertEqual(
                    G.destructive_git_hits(allowed, start_dir=str(_REPO_ROOT)), [], allowed)


class TestR84ArgvExecPrefix(unittest.TestCase):
    """SD-08（low）：argv 序列的**第 0 格不一定是執行檔**。"""

    def test_literal_prefixes_are_skipped(self) -> None:
        for command in ('subprocess.run(["sudo","git","stash"])',
                        'subprocess.run(["env","git","clean","-fdx"])',
                        'subprocess.run(["env","GIT_DIR=/tmp/x","git","reset","--hard"])',
                        'subprocess.run(["timeout","30","git","stash","pop"])'):
            with self.subTest(command=command):
                self.assertTrue(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), command)

    def test_the_narrowing_that_keeps_the_false_positives_out_still_holds(self) -> None:
        """跳過前綴**不得**把「命令字串表」那三筆假紅換回來（第 0 格仍必須是 git）。"""
        for command in ('("git checkout -p","git checkout -p -- tools/","git restore -p")',
                        'subprocess.run(["git","status","--porcelain"])',
                        'subprocess.run(["sudo","apt","install","git"])'):
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [], command)

    def test_the_boundary_is_recorded_not_pretended_closed(self) -> None:
        """🔴 誠實劃界＝**機械記錄**，不是散文：元素是變數／`$(which git)` 擋不住。

        寫成會紅的斷言，是為了讓「哪天有人真的關掉了它」是可偵測的——而不是讓下一輪
        的人以為這一族已經修好。對應 hook 檔頭〈誠實劃界〉的同一段。
        """
        for command in ('subprocess.run([GIT,"stash"])',
                        'subprocess.run(["git","-C",wt,"stash"])',
                        "$(which git) stash"):
            with self.subTest(command=command):
                self.assertEqual(
                    G.destructive_git_hits(command, start_dir=str(_REPO_ROOT)), [],
                    f"{command!r} 竟被擋下 ⇒ 檔頭的誠實劃界該改了（這是好消息，但要同步）")


class TestR84SentinelAckIsNotASubstring(unittest.TestCase):
    """SD-04（blocking）：ack 位元用**子字串**判 ⇒ 該出聲時不出聲，而且是**永久**的。

    修訂前 `main()` 傳的是 `"stash" in command`：前一條指令只要「提到」stash
    （`grep -rn stash docs/`、`ls .git/autosdd_stash_sentinel`）就把 ack 點亮 ⇒ 下一次
    真 drift 靜默；而同一次已把 state 改寫成新 SHA ⇒ **之後再也不會報**，不是延後。
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="w-ack-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / ".git" / "refs").mkdir(parents=True)
        self.ref = self.root / ".git" / "refs" / "stash"

    def test_merely_mentioning_stash_is_not_an_acknowledgement(self) -> None:
        for command in ("grep -rn stash docs/",
                        "ls .git/autosdd_stash_sentinel",
                        "echo 'git stash' > /tmp/x",
                        "cat .claude/hooks/block_destructive_git.py | grep stash"):
            with self.subTest(command=command):
                self.assertFalse(G.stash_writer_seen(command),
                                 f"{command!r} 點亮了 ack ⇒ 下一次真 drift 會被永久吞掉")

    def test_only_the_subcommands_that_really_move_the_ref_acknowledge(self) -> None:
        for command in ("git stash", "git stash push -u", "git stash pop",
                        "git stash drop", "git stash clear", "git stash save wip",
                        "sh -c 'git stash pop'",                  # 走 `-c` 平面
                        'subprocess.run(["git","stash"])'):       # 走 argv 平面
            with self.subTest(command=command):
                self.assertTrue(G.stash_writer_seen(command), command)
        for command in ("git stash create", "git stash list", "git stash show -p",
                        "git stash apply stash@{0}", "git status"):
            with self.subTest(command=command):
                self.assertFalse(
                    G.stash_writer_seen(command),
                    f"{command!r} 一個字節都不動 refs/stash，不該解釋任何變動")

    def test_a_bogus_ack_would_swallow_the_next_real_drift_forever(self) -> None:
        """🔴 紅綠自證：把 ack 換回子字串判定 ⇒ 真 drift 被吞，而且**下一輪也不會報**。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root), ack="stash" in "grep -rn stash docs/")
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        self.assertIsNone(G.stash_ref_sentinel(str(self.root)), "子字串 ack 沒有吞掉？")
        self.assertIsNone(G.stash_ref_sentinel(str(self.root)),
                          "吞掉是**永久**的（head 已被改寫）——這一條把嚴重性釘住")

    def test_with_the_fix_the_same_drift_is_reported(self) -> None:
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        G.stash_ref_sentinel(str(self.root), ack=G.stash_writer_seen("grep -rn stash docs/"))
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        note = G.stash_ref_sentinel(str(self.root))
        self.assertIsNotNone(note)
        self.assertIn("refs/stash", note or "")

    def test_a_blocked_command_never_acknowledges(self) -> None:
        """🔴 被擋下的指令**根本不會跑** ⇒ 它解釋不了任何 ref 變動。端到端量 rc。

        `main()` 現在在**豁免判定之後**才算 ack，所以「擋下」與「放行」兩向都對得上：
        擋下 ⇒ ack=False（下一輪的隱形變動仍會被報）；帶豁免放行 ⇒ ack=True。
        """
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        blocked = {"tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "git stash push -u"}}
        self.assertEqual(run_hook(blocked).returncode, 2)
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        proc = run_hook({"tool_name": "Bash", "cwd": str(self.root),
                         "tool_input": {"command": "echo hi"}})
        self.assertEqual(proc.returncode, 0, proc.stderr)  # DEF-200-440：提醒不再佔 rc=1
        self.assertIn("refs/stash", proc.stdout,
                      "被擋下的那條指令替一個它沒有造成的變動背了書")

    def test_an_exempted_stash_does_acknowledge(self) -> None:
        """反向：帶行內豁免而**真的會跑**的 stash ⇒ ack=True ⇒ 下一輪不吵。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        allowed = {"tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "git stash pop  # git-guard-ok: 還原事故"}}
        self.assertEqual(run_hook(allowed).returncode, 0)
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        proc = run_hook({"tool_name": "Bash", "cwd": str(self.root),
                         "tool_input": {"command": "echo hi"}})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "", "提醒不再佔 rc=1 ⇒ rc=0 不再證明靜默，stdout 才是")


class TestR84TheWaitformDocstringIsTheSingleHome(unittest.TestCase):
    """QA-03：同一份知識三個家、三種內容（hook docstring 說四條、CLAUDE.md 鐵律六說兩條、
    帳本的③ 又是第三種東西）。**SSOT ＝ `waitform_hits()` 的 docstring**（實作所在）。
    史料搬至 CrossPlatform_Guard_Line_History_2.md〈R190 收尾棒〉§3。 round-label-ok"""

    def test_the_docstring_declares_four_and_all_four_can_fire_alone(self) -> None:
        doc = G.waitform_hits.__doc__ or ""
        self.assertIn("**四條**判準", doc, "docstring 沒有明說幾條 ⇒ 讀者只能去猜")
        for marker in ("· ①", "· ②", "· ③", "· ④"):
            self.assertIn(marker, doc)
        # ①：nohup ＋ 背景 &（前景呼叫，旗標為 False）
        self.assertTrue(G.waitform_hits("nohup python x.py > log 2>&1 &"))
        # ②：until 條件內的裸 pgrep -f
        self.assertTrue(G.waitform_hits("until ! pgrep -f 'run_root_unittests'; do :; done"))
        # ③：只有旗標為真時才成立（同一條指令在前景是放行的）
        self.assertEqual(G.waitform_hits("python x.py &"), [])
        self.assertTrue(G.waitform_hits("python x.py &", run_in_background=True))
        # ④：只有 Bash 工具才成立（同一條指令在 PowerShell 是放行的；DEF-200-086）
        four = "sh -c 'exit 7' | tail -1; echo $?"
        self.assertTrue(G.waitform_hits(four))
        self.assertEqual(G.waitform_hits(four, tool="PowerShell"), [])

    def test_the_wait_carve_out_asymmetry_is_documented_and_real(self) -> None:
        """docstring 宣稱 `wait` 豁免**只罩 ①③、不罩 ②④** ⇒ 兩向都實測。"""
        self.assertIn("只罩 ①③、不罩 ②④", G.waitform_hits.__doc__ or "")
        self.assertEqual(G.waitform_hits("nohup python x.py & wait"), [])
        self.assertTrue(
            G.waitform_hits("until ! pgrep -f 'run_root_unittests'; do :; done; wait"),
            "`wait` 竟然把判準② 也一起放行了 ⇒ docstring 的不對稱宣稱是假的")


# ── ⑧ 授權邊界：無人看管回合禁動 git 歷史（R85／P12，**mac 側先前零機械物**）──────
class TestUnattendedAuthzHasTeethOnEveryPlatform(unittest.TestCase):
    """R79 立的 Auto Pilot 條件，在 macOS 上到 R85 為止**一行都不會跑**。
    史料搬至 CrossPlatform_R190_FixRound_Evidence.md〈九-F〉§50。"""

    #: 有訊號時**必須擋**。前 5 筆是 mac 專有形態（Windows 那支姊妹鎖沒有的）。
    MUST_BLOCK = (
        ("sudo 前綴", "sudo git push"),
        ("殼 -c operand（字串內，殼文字看不到）", "bash -c 'git push origin main'"),
        ("argv 序列（不經殼）", 'python -c \'subprocess.run(["git","push"])\''),
        ("帶路徑前綴的 git", "/usr/bin/git commit -m x"),
        ("第二段指令（換行之後）", "date\ngit push"),
        ("git commit", 'git commit -m "wip"'),
        ("git push", "git push origin main"),
        ("git -C <path> commit（不在 cwd 上動手）", "git -C /repo commit -m x"),
        ("git -c 覆寫設定後 push", "git -c user.name=bot push"),
        ("gh pr create", "gh pr create --fill"),
        ("gh release create", "gh release create v1 --notes x"),
        ("行內豁免對授權邊界無效（那一跑自己寫得出這行）",
         "git push  # git-guard-ok: 我覺得可以"),
        # 🔴 R85／SD-B3：鐵律二**明訂**的 Windows 寫法（絕對路徑外呼），修前不擋。
        ("引號包住的 Windows 絕對路徑（鐵律二明訂形態）",
         r"""& 'C:\Program Files\Git\bin\git.exe' push"""),  # platform-ok: 被測指令字面
        ("同上但雙引號",
         r"""& "C:\Program Files\Git\bin\git.exe" commit -m x"""),  # platform-ok: 同上
        ("引號包住的 POSIX 絕對路徑（引號才是成因，不是碟符）", "& '/usr/bin/git' push"),
        ("引號包住的 gh（另一條把改動送出去的路）",
         r"""& 'C:\tools\gh.exe' pr create"""),  # platform-ok: 被測指令字面
    )

    #: 有訊號時**仍必須放行**。那一跑要做的事正是「把狀態寫下來然後停」，
    #: 擋到它讀 git、寫任務書、留稽核痕跡，等於逼它什麼都不留就死掉。
    MUST_PASS = (
        ("git status（讀，不是寫）", "git status --short"),
        ("git log", "git log --oneline -3"),
        ("git diff", "git diff --stat"),
        ("`push` 只是 grep 的樣式", "git log | grep push"),
        ("`commit` 出現在參數的值裡", "git log --grep=commit"),
        ("在字串裡提到 commit（寫任務書／留痕的日常）",
         "echo 'blocked: do not git commit here'"),
        ("在註解裡提到 push", "date  # never git push from here"),
        ("字尾巧合不算指令（`legit` 不是 `git`）", "legit commit -m x"),
        ("🔴 `git stash create`＝〈可重啟點四條件〉第 1 條指定的保全手法",
         "git stash create"),
        # 🔴 R85／SD-B3 的另一半：假紅同樣是缺陷（敘事原文＝GovWrite 證據檔 §6.9）。
        ("設定鍵以子指令名開頭的唯讀查詢", "git config push.default"),
        ("同上，帶 --get", "git config --get push.default"),
        ("`-c` 覆寫設定但實際動作是 status", "git -c push.default=simple status"),
        ("`push` 是 `&&` 之後另一個指令的參數", "git log && echo push"),
        ("引號裡的路徑是被當資料用的（pgrep 的樣式）", "pgrep -f '/usr/bin/git'"),
    )

    def test_the_signal_blocks_git_history_writes(self) -> None:
        for label, command in self.MUST_BLOCK:
            with self.subTest(label):
                proc = run_hook(bash_payload(command), env={G.UNATTENDED_ENV: "1"})
                self.assertEqual(proc.returncode, 2, f"未擋（{label}）\n{proc.stderr}")
                self.assertIn(G.UNATTENDED_ENV, proc.stderr,
                              f"擋了卻沒說是哪個訊號造成的（{label}）——讀者無從得知怎麼關")

    def test_without_the_signal_the_same_commands_are_untouched(self) -> None:
        """🔴 反向：互動 session 零附帶面。壞掉＝掌舵者自己的 commit 被鎖死。"""
        for label, command in self.MUST_BLOCK:
            with self.subTest(label):
                self.assertIn(
                    run_hook(bash_payload(command)).returncode, (0, 1),
                    f"沒有無人看管訊號卻被擋（{label}）：{command!r}")

    def test_the_signal_does_not_block_what_that_run_still_needs(self) -> None:
        for label, command in self.MUST_PASS:
            with self.subTest(label):
                proc = run_hook(bash_payload(command), env={G.UNATTENDED_ENV: "1"})
                self.assertIn(proc.returncode, (0, 1), f"誤擋（{label}）\n{proc.stderr}")

    def test_the_message_names_the_boundary_not_just_the_rule(self) -> None:
        """訊息要讓那一跑知道**該做什麼**，不是只知道被擋（同姊妹鎖的第四件事）。"""
        err = run_hook(bash_payload("git push"), env={G.UNATTENDED_ENV: "1"}).stderr
        self.assertIn("git-guard-ok", err, "必須明說行內豁免對本條無效")
        self.assertIn("工作樹", err, "必須告訴它替代動作（改動留著讓人回來收）")

    def test_the_criterion_lives_in_exactly_one_home(self) -> None:
        """🔴 兩支 hook 必須讀同一份判準——本 repo 的頭號病是同一份知識住兩個家。"""
        import unattended_authz as A
        self.assertIs(G.authz_hits, A.authz_hits)
        self.assertEqual(G.UNATTENDED_ENV, A.UNATTENDED_ENV)
        for name in ("_GIT_WRITE_RE", "_GH_WRITE_RE"):
            self.assertFalse(hasattr(G, name), f"{name} 在 hook 內長出了第二份")


# ══════════════════════════════════════════════════════════════════════════════
# R95／Pkg-B：PRD §15.5 紅線 10「治理檔在無人值守下唯讀」— govwrite 一族的回歸鎖
# ══════════════════════════════════════════════════════════════════════════════
class TestGovernanceFilesAreReadOnlyWhenUnattended(unittest.TestCase):
    """立案（R87 實帳：繞過 halt 改取數層 ⇒ 13 agent 全滅）與設計取捨、實測 rc 逐字＝
    docs/06_quality/CrossPlatform_R95_GovWrite_Evidence.md §1~§3；本類是其紅綠自證。
    史料搬至 CrossPlatform_Guard_Line_History_2.md〈R190 收尾棒〉§4。 round-label-ok"""

    #: 保護面全集（與 hook 內 SSOT `_GOV_EXACT` ∪ `.claude/hooks/*.py` 逐筆對齊；
    #: 這裡刻意逐字重抄一份當**期望值**——期望值引用 SSOT 本身會讓測試恆真）。
    PROTECTED = (
        ".env",
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/hooks/block_destructive_git.py",
        ".claude/hooks/context_budget_guard.py",
        "tools/lib/quota_meter.py",
        "tools/lib/quota_gate.py",
        "tools/lib/quota_policy.py",
        "tools/lib/quota_pace.py",
        "tools/lib/quota_limits.py",
        "tools/lib/pace_contract.py",
        "tools/lib/sentinel_lifecycle.py",
        "tools/lib/schedule_backend.py",
        "tools/lib/quota_messages.py", "tools/lib/quota_escalation.py",
        "tools/lib/platform_utils.py", "tools/session_resume_planner.py",
        # R115 新增二檔（PRD_Amendment_R113_WakeChain_LastMile.md §3(a) L3）：  round-label-ok
        # 見 `test_the_r115_l3_additions_are_protected_when_unattended` 的專屬紅綠自證。
        ".claude/settings.unattended.json",
        "tools/tests/test_adr_xplat001_c1c2_lock.py",
    )
    #: 誤擋是守衛被整個關掉的路徑——放行面與擋下面同等重要。
    NOT_PROTECTED = (
        "docs/06_quality/CrossPlatform_R95_GovWrite_Evidence.md",
        "tools/lib/git_paths.py",            # tools/lib 不是整目錄保護，是字面清單
        "tools/tests/test_block_destructive_git_r83.py",
        ".claude/hooks/README.md",           # hooks 目錄只保護 .py
        "AutoClaude/.claude/settings.json",  # 子專案同名檔不在保護面（另有子專案守衛）
    )

    def _env(self, **extra: str) -> dict[str, str]:
        return {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT), **extra}

    def _payload(self, path: str, tool: str = "Write") -> dict:
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        return {"tool_name": tool, "tool_input": {key: path}}

    def test_every_protected_file_is_blocked_when_unattended(self) -> None:
        for rel in self.PROTECTED:
            with self.subTest(rel=rel):
                proc = run_hook(self._payload(rel),
                                env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("唯讀", proc.stderr, "訊息沒說這是唯讀保護")
                self.assertIn("回報主控", proc.stderr, "訊息沒給出正確的出路")

    def test_unattended_write_to_dot_env_is_blocked(self) -> None:
        """M3：`.env`＝settings.json `env` 的同義繞行面 ⇒ rc=2（DEF-200-115 訂正；原文＝§6.10）。"""
        proc = run_hook(self._payload(".env"), env=self._env(**{G.UNATTENDED_ENV: "1"}))
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_the_autoclaude_prefix_is_pinned_before_the_directory_exists(self) -> None:
        """m4：`.autoclaude/`＝PRD 紅線 10 字面；目錄未建先釘判準
        （建立那天才發現沒人守＝靜默失效）。"""
        proc = run_hook(self._payload(".autoclaude/state.json"),
                        env=self._env(**{G.UNATTENDED_ENV: "1"}))
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_all_three_write_tools_are_in_scope(self) -> None:
        """Edit 與 NotebookEdit 走同一格——漏任一個，改治理檔只要換個工具就繞過。"""
        for tool in ("Edit", "NotebookEdit"):
            with self.subTest(tool=tool):
                proc = run_hook(self._payload(".claude/settings.json", tool),
                                env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_an_absolute_path_is_the_production_shape(self) -> None:
        """production 的 file_path 是絕對路徑——相對路徑那格只是防禦縱深。"""
        proc = run_hook(self._payload(str(_REPO_ROOT / ".claude" / "settings.json")),
                        env=self._env(**{G.UNATTENDED_ENV: "1"}))
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def _sandbox_env(self, **extra: str) -> dict[str, str]:
        """專案根導到暫存目錄（DEF-200-440）：目標檔不必存在，hook 也不寫任何檔。"""
        tmp = tempfile.TemporaryDirectory(prefix="def440-")
        self.addCleanup(tmp.cleanup)
        return {"CLAUDE_PROJECT_DIR": tmp.name, **extra}

    def test_attended_is_an_advisory_not_an_error(self) -> None:
        """主 session 每輪都要改這些檔，擋了守衛會被關掉。DEF-200-440：提醒不得用 CC 標成 hook
        error 的 rc（rc=1 像被擋）⇒ rc=0＋stdout 單一 JSON；Write／Edit／NotebookEdit 同格。"""
        for tool in sorted(G.GOV_TOOLS):
            with self.subTest(tool=tool):
                proc = run_hook(self._payload(".claude/settings.json", tool),
                                env=self._sandbox_env())
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stderr, "", "提醒走 stdout JSON，stderr 必須空")
                hso = json.loads(proc.stdout)["hookSpecificOutput"]
                self.assertEqual(hso["hookEventName"], "PreToolUse")
                for word in ("治理檔", "有人值守", "這只是提醒，這次寫入已放行"):
                    self.assertIn(word, hso["additionalContext"])

    def test_the_advisory_names_the_event_the_payload_names(self) -> None:
        """hookEventName 與實際事件不符時 CC 整份丟掉（`emit_to_model` 約束①）⇒ 取
        payload 原值不得寫死；缺席才退回本 hook 唯一註冊的事件。"""
        for event, want in (("PostToolUse", "PostToolUse"), (None, "PreToolUse")):
            with self.subTest(event=event):
                payload = {**self._payload(".claude/settings.json"),
                           **({"hook_event_name": event} if event else {})}
                proc = run_hook(payload, env=self._sandbox_env())
                self.assertEqual(proc.returncode, 0, proc.stderr)
                got = json.loads(proc.stdout)["hookSpecificOutput"]["hookEventName"]
                self.assertEqual(got, want)

    def test_the_only_nonzero_nonblocking_exit_is_the_degraded_payload(self) -> None:
        """DEF-200-440：治理面一族的 rc 只准 0（放行／提醒）或 2（真擋）；rc=1 專屬「讀不出
        payload」，不兼作提醒。無人值守仍真擋，阻斷路徑不再送 additionalContext。"""
        cases = (("attended", ".claude/settings.json", {}, 0),
                 ("unattended", ".claude/settings.json", {G.UNATTENDED_ENV: "1"}, 2),
                 ("escape-hatch", ".claude/settings.json", {G.GOVWRITE_OFF_ENV: "1"}, 0),
                 ("unprotected", "docs/notes.md", {}, 0))
        for tool in sorted(G.GOV_TOOLS):
            for label, path, extra, want in cases:
                with self.subTest(tool=tool, case=label):
                    proc = run_hook(self._payload(path, tool),
                                    env=self._sandbox_env(**extra))
                    self.assertEqual(proc.returncode, want, proc.stderr)
                    if want == 2:
                        self.assertEqual(proc.stdout, "", "阻斷路徑不得再送提醒")
            with self.subTest(tool=tool, case="undeterminable"):
                proc = run_hook({"tool_name": tool, "tool_input": {}},
                                env=self._sandbox_env())
                self.assertEqual(proc.returncode, 0, proc.stderr)
        for raw in ("", "{not json"):
            with self.subTest(raw=raw):
                self.assertEqual(run_hook(None, raw=raw).returncode, 1)

    def test_paths_off_the_protected_list_pass_even_when_unattended(self) -> None:
        for rel in self.NOT_PROTECTED:
            with self.subTest(rel=rel):
                proc = run_hook(self._payload(rel),
                                env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stderr.strip(), "")

    def test_a_same_named_file_outside_the_root_is_not_governance(self) -> None:
        """scratchpad／合成樹裡的 `.claude/settings.json` 不是治理檔——誤擋它等於
        擋掉「在沙盒重現缺陷」這個正當用途（同 git 族換樹放寬的方向）。"""
        with tempfile.TemporaryDirectory(prefix="w3-govwrite-") as foreign:
            proc = run_hook(
                self._payload(os.path.join(foreign, ".claude", "settings.json")),
                env=self._env(**{G.UNATTENDED_ENV: "1"}))
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_target_fails_open(self) -> None:
        """Write payload 沒有 file_path ⇒ 判不出目標 ⇒ 放行（fail-open 是 P0：hook
        誤觸 deny 會把所有工具硬鎖死）。"""
        proc = run_hook({"tool_name": "Write", "tool_input": {}},
                        env=self._env(**{G.UNATTENDED_ENV: "1"}))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_the_escape_hatch_works_and_is_not_shared(self) -> None:
        """③＋④：自己的開關關得掉自己；兩族的開關互相關不掉對方（**雙向**都要驗——
        共用開關會讓「我只是想暫時別被擋」順手把別的保護一起關掉，repo 明文禁止）。"""
        blocked = self._payload(".claude/settings.json")
        proc = run_hook(blocked, env=self._env(
            **{G.UNATTENDED_ENV: "1", G.GOVWRITE_OFF_ENV: "1"}))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = run_hook(blocked, env=self._env(
            **{G.UNATTENDED_ENV: "1", G.GUARD_OFF_ENV: "1"}))
        self.assertEqual(proc.returncode, 2,
                         f"{G.GUARD_OFF_ENV} 竟然也能關掉治理面唯讀\n{proc.stderr}")
        proc = run_hook(bash_payload("git stash"), env={G.GOVWRITE_OFF_ENV: "1"})
        self.assertEqual(proc.returncode, 2,
                         f"{G.GOVWRITE_OFF_ENV} 竟然也能關掉毀滅性 git 阻斷\n{proc.stderr}")

    def test_the_protected_list_is_load_bearing(self) -> None:
        """⑥反 vacuity：清空字面清單，settings.json 必須當場變成放行；hooks 目錄那一半
        不靠字面清單，必須仍然命中——證明兩半各自承重、判準不是恆真的。"""
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertEqual(G.govwrite_hit({"file_path": ".claude/settings.json"}),
                             ".claude/settings.json")
            with mock.patch.object(G, "_GOV_EXACT", frozenset()):
                self.assertIsNone(
                    G.govwrite_hit({"file_path": ".claude/settings.json"}),
                    "清單清空後仍命中 ⇒ 判準沒有真的讀那張表")
                self.assertEqual(G.govwrite_hit({"file_path": ".claude/hooks/foo.py"}),
                                 ".claude/hooks/foo.py")
                self.assertEqual(G.govwrite_hit({"file_path": ".autoclaude/x.json"}),
                                 ".autoclaude/x.json")

    def test_dot_dot_does_not_smuggle_a_write_past_the_check(self) -> None:
        """`..` 繞行由 realpath 收掉：路徑繞出去再繞回保護面，仍必須命中。"""
        sneaky = str(_REPO_ROOT / "docs" / os.pardir / ".claude" / "settings.json")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertEqual(G.govwrite_hit({"file_path": sneaky}),
                             ".claude/settings.json")

    def test_the_r115_l3_additions_are_protected_when_unattended(self) -> None:
        """R115／PRD_Amendment_R113_WakeChain_LastMile.md §3(a) L3  round-label-ok
        （`_GOV_EXACT` 新增二檔：無頭姿態 settings 載入面／護欄層淨額棘輪判準本身）——
        改任一個都能直接改變無人值守下的權限姿態或守衛自身行為，理應與既有保護面同判。
        專屬測試（不只靠 `PROTECTED` 元組裡的通用迴圈）是刻意的：紅綠自證要能單獨
        對這兩個新成員跑，不必牽動整個既有清單。
        """
        for rel in (".claude/settings.unattended.json",
                    "tools/tests/test_adr_xplat001_c1c2_lock.py"):
            with self.subTest(rel=rel):
                proc = run_hook(self._payload(rel), env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("唯讀", proc.stderr, "訊息沒說這是唯讀保護")

    # ══════════════════════════════════════════════════════════════════════
    # DEF-200-238：govwrite 對「尚不存在」保護面目標的 Windows 大小寫繞過
    # ══════════════════════════════════════════════════════════════════════
    def test_fold_gov_path_lowers_only_on_windows_and_is_identity_on_posix(self) -> None:
        """`_fold_gov_path()` 平台契約單測：用
        `mock.patch.object(os, "path", ntpath／posixpath)` 整包注入 Windows／posix
        語意（同 `tools/lib/worktree_paths.py` 模組頭的既有論證），不依賴實際跑測試
        的 host OS，兩個方向都能在同一台機器上驗到——這是本鎖「posix 不得加寬」
        這條要求的核心證據：`posixpath.normcase` 是逐位元組 identity。
        """
        with mock.patch.object(G.os, "path", ntpath):
            self.assertEqual(G._fold_gov_path(".AUTOCLAUDE/state.json"),
                              ".autoclaude/state.json")
            self.assertEqual(G._fold_gov_path(".claude/hooks/NEW_GUARD.PY"),
                              ".claude/hooks/new_guard.py")
        with mock.patch.object(G.os, "path", posixpath):
            self.assertEqual(G._fold_gov_path(".AUTOCLAUDE/state.json"),
                              ".AUTOCLAUDE/state.json")
            self.assertEqual(G._fold_gov_path(".claude/hooks/NEW_GUARD.PY"),
                              ".claude/hooks/NEW_GUARD.PY")

    def test_the_two_r114_bypass_shapes_are_blocked_on_windows(self) -> None:
        """紅綠自證：對**尚不存在**的保護面目標，Windows `realpath` 無檔可還原
        大小寫 ⇒ `.AUTOCLAUDE/state.json`（目錄前綴比對失手）與
        `.claude/hooks/NEW_GUARD.PY`（`endswith(".py")` 大小寫敏感）兩形態實測繞過
        （逐字取證＝docs/06_quality/CrossPlatform_R114_WakeChain_Review.md §4）。
        摺大小寫後 Windows 上應轉為擋下；posix 上 `normcase` 是 no-op，這兩個大寫
        變體字面上本來就是**不同**檔名（posix 大小寫敏感）——維持不擋是 posix 應有
        的行為，不是本鎖要收斂的範圍，不得因本次修法而改變。
        """
        expect_blocked = sys.platform == "win32"
        for rel in (".AUTOCLAUDE/state.json", ".claude/hooks/NEW_GUARD.PY"):
            with self.subTest(rel=rel):
                proc = run_hook(self._payload(rel), env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 2 if expect_blocked else 0, proc.stderr)

    def test_existing_file_case_variants_still_hit(self) -> None:
        """既存檔的大小寫變體必須全數命中（DEF-200-238 立案時已確認此面成立，不得
        因本次修法退化）——三個探針原始案例（逐字取證見
        docs/06_quality/CrossPlatform_R114_WakeChain_Review.md §3.2）：
        `.ENV`／`Tools/Lib/Quota_Gate.py`／`.claude/SETTINGS.JSON`。這個面只在
        Windows 上有意義：NTFS 大小寫不敏感，`realpath` 對已存在的檔會問磁碟還原
        正確大小寫；posix 上大小寫敏感，這些變體字面上是不同檔名，不受本次修法
        影響，維持不擋。
        """
        expect_blocked = sys.platform == "win32"
        for rel in (".ENV", "Tools/Lib/Quota_Gate.py", ".claude/SETTINGS.JSON"):
            with self.subTest(rel=rel):
                proc = run_hook(self._payload(rel), env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 2 if expect_blocked else 0, proc.stderr)

    def test_case_folding_does_not_widen_the_protected_set(self) -> None:
        """摺大小寫不得把「原本就不受保護」的檔案，因為換個大小寫寫法就變成受保護——
        這裡刻意選一個跟保護面字面**不同名**（不是同名不同大小寫）的檔案，任何大小寫
        寫法在任何平台上都不該命中。"""
        for rel in ("TOOLS/LIB/GIT_PATHS.PY", "tools/lib/git_paths.py",
                    "Tools/Lib/Git_Paths.py"):
            with self.subTest(rel=rel):
                proc = run_hook(self._payload(rel), env=self._env(**{G.UNATTENDED_ENV: "1"}))
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_the_fold_is_load_bearing_for_the_two_bypass_shapes(self) -> None:
        """反 vacuity：把 `_fold_gov_path` 換成 identity（＝修法前的等效狀態）後，
        `govwrite_hit()` 對這兩個繞過形態必須變回放行——證明擋下真的是摺大小寫在
        承重，不是巧合命中其他判準（在 posix 上這個斷言本來就恆成立，因為 posix
        本來就不摺——不影響本測試作為 Windows 承重證據的有效性）。
        """
        with mock.patch.object(G, "_fold_gov_path", lambda rel: rel), \
                mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)}):
            self.assertIsNone(G.govwrite_hit({"file_path": ".AUTOCLAUDE/state.json"}),
                               "拿掉摺疊後這個形態應該變回放行——否則摺疊沒有承重")
            self.assertIsNone(G.govwrite_hit({"file_path": ".claude/hooks/NEW_GUARD.PY"}),
                               "拿掉摺疊後這個形態應該變回放行——否則摺疊沒有承重")


# ── 家族結構鎖（DEF-200-440）：hook 的 exit code 只認 0 與 2 ──────────────────────────
_DEGRADED_MARK = re.compile(r"#\s*degraded-payload:\s*\S")
_EXIT_CALLEES = ("sys.exit", "exit", "quit", "SystemExit", "os._exit")


def _off_contract(expr: ast.AST) -> bool:
    """運算式可能是 0／2 以外的結束碼：整數（含負數）或字串等字面值（字串參數的 `sys.exit` 是
    rc 1）；`a if c else b` 兩支都看。`None`、bool、經變數或呼叫的值判不到（見類別 docstring）。"""
    if isinstance(expr, ast.IfExp):
        return _off_contract(expr.body) or _off_contract(expr.orelse)
    try:
        value = ast.literal_eval(expr)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    exempt = value is None or isinstance(value, bool) or (type(value) is int and value in (0, 2))
    return not exempt


def _own_returns(fn: ast.AST) -> list[ast.Return]:
    """`fn` 自己的 return 敘述（不進巢狀函式／lambda／class）。"""
    found: list[ast.Return] = []
    stack = list(ast.iter_child_nodes(fn))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return):
            found.append(node)
        elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))
    return found


def unmarked_off_contract_exit_sites(sources: dict[str, str]) -> list[str]:
    """結束碼在 0／2 之外卻沒有行內標記 `# degraded-payload: <理由>` 的站點（空＝通過；純函式，
    紅綠由注入自證）。站點＝①任何位置的 `sys.exit`／`exit`／`quit`／`SystemExit`／`os._exit` 帶
    0／2 以外的字面值；②出口函式（`main`、被 `sys.exit(f())` 直接餵的 `f`）自己的 `return
    <n>`。輔助函式的 `return 1` 不是 exit code（如 `fix_ps1_encoding`）⇒ 不判。"""
    problems: list[str] = []
    for rel, text in sorted(sources.items()):
        lines, tree = text.splitlines(), ast.parse(text)
        exits = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.args
                 and ast.unparse(n.func) in _EXIT_CALLEES]
        funnels = {"main"} | {c.args[0].func.id for c in exits
                              if isinstance(c.args[0], ast.Call)
                              and isinstance(c.args[0].func, ast.Name)}
        sites: list[ast.AST] = [c for c in exits if _off_contract(c.args[0])]
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef) and fn.name in funnels:
                sites += [r for r in _own_returns(fn) if r.value and _off_contract(r.value)]
        problems += [f"{rel}:{n.lineno} `{lines[n.lineno - 1].strip()}`"
                     for n in sites if not _DEGRADED_MARK.search(lines[n.lineno - 1])]
    return problems


def hook_script_population(root: Path) -> dict[str, str]:
    """`root` 底下會被 Claude Code 載入的 hook 腳本 → `{repo 相對路徑: 原始碼}`（導出，不手列）。

    ＝三份活躍 settings.json（`hook_wiring.discover_active_settings`＋`settings_targets`）註冊的
    腳本 ∪ `.claude/hooks/*.py`。🔴 `settings_targets` 回的是**相對各 settings 專案根**
    （`CLAUDE_PROJECT_DIR`＝settings 檔的上上層）的路徑：AutoClaude 回 `tools/hooks/x.py`，接到
    repo 根會解到不存在的 `<根>/tools/hooks/`，若對缺檔 `continue`，母體會靜默縮水而鎖仍綠 ⇒
    缺檔一律 fail-loud。只讀 JSON 與原始碼文字，不 import 任何 SDD 模組。"""
    import hook_wiring  # noqa: PLC0415 — tools/lib 已在本檔 sys.path
    paths = set((root / ".claude" / "hooks").glob("*.py"))
    for rel_settings in hook_wiring.discover_active_settings(root):
        settings_path = root / rel_settings
        settings = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        for _event, target in hook_wiring.settings_targets(settings):
            script = settings_path.parent.parent / target
            if not script.is_file():
                raise AssertionError(f"{rel_settings} 註冊了不存在的 {target}：母體會靜默縮水")
            paths.add(script)
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in sorted(paths)}


class TestHookExitCodesAreZeroOrTwoExceptDegradedPayload(unittest.TestCase):
    """🔴 CC 的 hook 契約只認 0（放行）與 2（阻斷），其他碼一律顯示成 hook error（DEF-200-440：
    提醒被誤用過兩次；DEF-200-447 在 AutoClaude 三支提醒型 hook 又找到六處）。⇒ 只想提醒必須
    rc=0＋`emit_to_model`／`systemMessage`；非 0／2 只留給**一種**真失效（payload 讀不出來、
    守衛這次沒檢查），並要求同一行帶 `# degraded-payload: <理由>`。射程＝三份活躍 settings.json
    註冊的全部 hook 腳本 ∪ `.claude/hooks/*.py`（`hook_script_population` 導出，不手列：手列
    白名單對 AutoClaude 三支結構性失明）。誠實劃界：看不到經變數／經呼叫的 rc（`rc = 3; return
    rc`）與 bool（`sys.exit(True)`）；輔助函式的 `return 1` 不是出口 ⇒ 三支 `main()` 一律只回
    字面量，行為由 `AutoClaude/tests/tools/hooks/test_def447_voice.py` 承重；標記語意靠複審。"""

    _MUST_COVER = (
        ".claude/hooks/block_destructive_git.py",
        "AutoClaude/tools/hooks/check_lang.py",
        "AutoClaude/tools/hooks/claude_md_freshness.py",
        "AutoClaude/tools/hooks/loc_budget_check.py",
        "AutoClaude/tools/hooks/check_ps1_encoding.py",
        "AutoClaude/tools/hooks/check_sh_eol.py",
    )

    def test_every_off_contract_exit_in_the_real_hooks_is_marked(self) -> None:
        sources = hook_script_population(_REPO_ROOT)
        for rel in self._MUST_COVER:
            self.assertIn(rel, sources, "掃描面縮水 ⇒ 本鎖恆綠")
        self.assertGreaterEqual(len(sources), 15, "母體塌縮 ⇒ 判準恆綠")
        self.assertEqual(unmarked_off_contract_exit_sites(sources), [])

    def test_population_follows_each_settings_own_project_root_and_fails_loud(self) -> None:
        """合成：子專案 settings 的相對路徑要接在**該 settings 的專案根**上；登記了缺檔就紅。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hook = root / "SUB" / "tools" / "hooks" / "x.py"
            hook.parent.mkdir(parents=True)
            hook.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
            launcher = "${CLAUDE_PROJECT_DIR}/../.claude/hooks/_hook_launcher.py"
            entry = {"type": "command", "command": "py", "args": [launcher, "tools/hooks/x.py"]}
            settings = root / "SUB" / ".claude" / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [entry]}]}}),
                                encoding="utf-8")
            self.assertEqual(set(hook_script_population(root)), {"SUB/tools/hooks/x.py"})
            hook.unlink()
            with self.assertRaises(AssertionError):
                hook_script_population(root)

    def test_red_every_unmarked_off_contract_exit_shape_is_caught(self) -> None:
        """合成注入（缺陷本體）：0／2 以外的每一種結束碼寫法，沒標記就必須紅。"""
        for src in ("def main():\n    return 1\n",
                    "def main():\n    return 1 if note else 0\n",
                    "import sys\nsys.exit(1)\n",
                    "exit(1)\n",
                    "raise SystemExit(1)\n",
                    "def main():\n    return 1  # degraded-payload:\n",  # 標記沒寫理由不算
                    "import sys\ndef run():\n    return 1\nsys.exit(run())\n",  # 被 exit 直接餵
                    # DEF-200-440 SF-1：原判準只認整數 1，下面六種同為非 0／2 的結束碼卻回報 0 站點
                    "import os\nos._exit(1)\n", "import sys\nsys.exit('msg')\n",  # 字串參數＝rc 1
                    "raise SystemExit('msg')\n", "def main():\n    return 3\n",
                    "import sys\nsys.exit(3)\n", "import sys\nsys.exit(-1)\n"):  # -1 是 UnaryOp
            with self.subTest(src=src):
                self.assertEqual(len(unmarked_off_contract_exit_sites({"fake.py": src})), 1)

    def test_green_marked_and_non_exit_shapes_pass(self) -> None:
        for src in ("def main():\n    return 1  # degraded-payload: payload 讀不出\n",
                    "def helper():\n    return 1\n\n\ndef main():\n    return 0\n",  # 非出口
                    "def main():\n    return True\n",                      # bool 不是 1
                    'def main():\n    """return 1／sys.exit(1) 只在 docstring"""\n    return 2\n',
                    "import sys\nsys.exit(0)\n",
                    "import os, sys\nsys.exit(2)\nos._exit(2)\nsys.exit(None)\n",  # 契約內的碼
                    "def main():\n    return -1  # degraded-payload: x\n"):  # 非 0／2 但明示
            with self.subTest(src=src):
                self.assertEqual(unmarked_off_contract_exit_sites({"fake.py": src}), [])


class TestResultDoesNotDriftWithCallerCwd(unittest.TestCase):
    """🔴 回歸鎖（本輪缺陷修復）：獨立驗證輪從非 repo 目錄（例如以
    `tools/run_root_unittests.py` 或 `Start-Job` 驅動、呼叫者 cwd 落在 repo 外）單獨
    跑本模組時，字面固定 9 支測試同時變紅——本檔多支測試直接呼叫
    `G.destructive_git_hits()`，而 `is_foreign_tree()` 對 `CLAUDE_PROJECT_DIR` 的
    fallback 是 `os.getcwd()`，呼叫者 cwd 一旦漂移出 repo，root 就解析錯，讓已知必須
    命中的形態靜默變成放行（詳見本檔 `setUpModule` 上方註記）。

    本鎖刻意**不**在測試本體內重新 patch `CLAUDE_PROJECT_DIR`：它要釘住的是模組級
    `setUpModule` 這道釘子本身有沒有在生效——若日後那道釘子被誤刪，本鎖必須是第一個
    重新變紅的測試，而不是靜默地跟著另外 9 支一起消失在「刻意分散」的假象裡。
    """

    def test_a_known_hit_survives_the_process_cwd_moving_outside_the_repo(self) -> None:
        outside = tempfile.mkdtemp(prefix="w-cwd-drift-")
        original_cwd = os.getcwd()
        try:
            os.chdir(outside)
            fs_root = _REPO_ROOT.anchor  # 錨定專案磁碟機，不用呼叫者 cwd 隱含推導
            self.assertTrue(
                G.destructive_git_hits(f"cd {fs_root} && git clean -fdx",
                                       start_dir=str(_REPO_ROOT)),
                "呼叫者 cwd 換到 repo 外後，檔案系統根形態從命中變成放行——"
                "`setUpModule` 的 CLAUDE_PROJECT_DIR 釘住失效了")
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(outside, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════
# SD-11：`mask_inert()` 引號失同步 ⇒ 其後的鐵律五／六判準全部看不見（fail-open）
# ══════════════════════════════════════════════════════════════════════════════
#: 修前會讓引號奇偶差一的形態：外層雙引號內的 `$(…)`，其內再有 `\"` 或「單引號夾雙引號」。
#: 最後一個 `"` 開出永不收尾的字串，把其後到結尾全遮成空白。S1～S4 是最小化形態，S6 取自
#: 真實逐字稿，J1／J2／J4 是 agent 抽 JSON 欄位的**自然寫法**。史料見本輪證據檔〈九〉。
_DESYNC_FORMS: tuple[tuple[str, str], ...] = (
    ("S1", 'echo "$(echo "\\"")"'),
    ("S2", 'echo "$(echo "a\\"b")"'),
    ("S3", 'x="$(printf "%s" "\\"q\\"")"'),
    ("S4", 'echo "$(grep -c -e "\\"x\\"" f)"'),
    ("S6", "echo \"$(grep -c 'bin/python\"' f)\""),
    ("J1", 'V="$(python3 -c "print(\\"hi\\")")"'),
    ("J2", 'echo "$(python3 -c "import json;print(json.load(open(\\"f\\"))[\\"a\\"])")"'),
    ("J4", 'echo "$(jq -r ".a \\| select(. == \\"x\\")" f)"'),
)
#: 負向對照：這幾條修前就正確（巢狀引號奇偶剛好對），修後必須維持原判決。
_DESYNC_CONTROLS: tuple[tuple[str, str], ...] = (
    ("N1", 'echo "path=$(dirname "$0")"'),
    ("N2", 'msg="$(git log -1 --format="%s")"'),
    ("N3", "sed \"s/\\\"/'/g\" f"),
    ("N4", 'python -c "print(\\"hi\\")"'),
    ("S5", "printf '%s' \"$(grep -c '\"type\": \"command\"' f)\""),
)
#: PowerShell 的跳脫字元是反引號：一個 `` `" `` 就讓奇偶差一，與 `$(…)` 遞迴無關。
_PS_FORM = 'Write-Host "Don`"t"'
_GIT_TAILS = ("git stash", "git reset --hard", "git clean -fd")
_BG_TAIL = "nohup sleep 5 > /dev/null 2>&1 &"
_RC_TAIL = 'git ls-files | head -3; echo "rc=$?"'


class TestMaskInertQuoteDesyncKeepsTheTailVisible(unittest.TestCase):
    """🔴 SD-11：外層雙引號內的 `$(…)` 帶巢狀引號時，修前 `mask_inert()` 引號奇偶差一，最後
    一個 `"` 開出永不收尾的字串、把其後到結尾**全遮成空白** ⇒ 鐵律五三個毀滅性動詞與鐵律六
    四條判準對那一段全部失明（守衛 fail-open，且同一支函式同時承載兩條鐵律）。"""

    def test_a_destructive_git_on_the_next_line_is_still_judged(self) -> None:
        for name, form in (*_DESYNC_FORMS, ("PS", _PS_FORM)):
            for tail in _GIT_TAILS:
                with self.subTest(form=name, tail=tail):
                    self.assertTrue(G.destructive_git_hits(f"{form}\n{tail}"),
                                    f"{form!r} 之後的 {tail!r} 被遮蔽器吞掉 ⇒ 鐵律五漏擋")

    def test_the_wait_criteria_still_see_the_next_line(self) -> None:
        for name, form in (*_DESYNC_FORMS, ("PS", _PS_FORM)):
            for tail in (_BG_TAIL, _RC_TAIL):
                with self.subTest(form=name, tail=tail[:24]):
                    self.assertTrue(G.waitform_hits(f"{form}\n{tail}"),
                                    f"{form!r} 之後的 {tail!r} 被遮蔽器吞掉 ⇒ 鐵律六漏判")

    def test_the_same_line_tail_is_judged_once_the_nesting_is_understood(self) -> None:
        """同一行的尾巴沒有「下一行」可退（第二視圖救不了）：只有把字串收尾判對才看得見。"""
        for name, form in _DESYNC_FORMS:
            for joiner in (" ; ", " && "):
                with self.subTest(form=name, joiner=joiner):
                    self.assertTrue(G.destructive_git_hits(f"{form}{joiner}git stash"))
                    self.assertTrue(G.waitform_hits(f"{form}{joiner}{_BG_TAIL}"))

    def test_the_forms_alone_are_inert_and_the_controls_keep_their_verdict(self) -> None:
        for name, form in (*_DESYNC_FORMS, *_DESYNC_CONTROLS, ("PS", _PS_FORM)):
            for command in (form, f"{form}\nls -la"):
                with self.subTest(form=name, command=command[-12:]):
                    self.assertEqual(G.destructive_git_hits(command), [])
                    self.assertEqual(G.waitform_hits(command), [])
        for name, form in _DESYNC_CONTROLS:
            with self.subTest(control=name):
                self.assertTrue(G.destructive_git_hits(f"{form}\ngit stash"))
                self.assertTrue(G.destructive_git_hits(f"{form} ; git stash"))

    def test_text_inside_the_string_stays_data(self) -> None:
        """修前的反向誤擋：`)` 之後同一個字串裡的 ` git stash` 被當成裸字、擋掉一條無害指令。"""
        for command in ('echo "$(echo "\\"") git stash"',
                        'echo "$(echo "\\""); git reset --hard"',
                        'echo "a $(echo "b\\"c") git clean -fd d"'):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command), [])

    def test_the_mask_keeps_its_length_and_hides_exactly_the_string(self) -> None:
        command = f"{_DESYNC_FORMS[0][1]}\ngit stash"
        masked = G.mask_inert(command)
        self.assertEqual(len(masked), len(command))
        self.assertEqual(masked.split("\n")[1], "git stash")
        self.assertEqual(masked.split("\n")[0].strip(), "echo")

    def test_an_inline_exemption_is_only_honoured_in_a_real_comment(self) -> None:
        form = _DESYNC_FORMS[3][1]
        self.assertTrue(G.has_exemption(f"{form} # git-guard-ok: probe\ngit stash"))
        self.assertFalse(G.has_exemption('echo "$(echo "\\"") # git-guard-ok: probe"'))


class TestMaskInertSecondViewOnlyRunsAfterADesync(unittest.TestCase):
    """fail-closed 網：任何引號掃描器看不懂而掃到 EOF 仍未收尾的字串，最多隱藏**同一行**的
    其餘部分，不得把 EOF 前全遮；而**沒有失同步時**多行字串的內部仍是資料（網不能常駐，否則
    每一則多行 commit message 都變成誤擋）。"""

    #: 掃描器看不懂的形態（ANSI-C、PowerShell 反引號與結尾反斜線、根本沒收尾）。
    UNFORESEEN = (
        ("PS backtick", _PS_FORM),
        ("ANSI-C", "echo $'it\\'s'"),
        ("unterminated", 'echo "abc'),
        ("PS path", 'Set-Location "C:\\dir\\"'),  # platform-ok: 守衛語料字面
    )

    def test_later_lines_stay_visible(self) -> None:
        for name, first in self.UNFORESEEN:
            for tail in _GIT_TAILS:
                with self.subTest(form=name, tail=tail):
                    self.assertTrue(G.destructive_git_hits(f"{first}\n{tail}"))
            for tail in (_BG_TAIL, _RC_TAIL):
                with self.subTest(form=name, tail=tail[:24]):
                    self.assertTrue(G.waitform_hits(f"{first}\n{tail}"))

    def test_a_well_formed_multiline_string_still_hides_its_interior(self) -> None:
        for command in ('git commit -m "first line\ngit stash is just text\nlast line"\nls',
                        "git commit -m 'one\ngit reset --hard is text\ntwo'\nls",
                        'echo "$(echo "x")" "a\ngit clean -fd\nb"'):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command), [])


class TestBackslashEscapedQuoteOutsideStringsIsNotAnOpener(unittest.TestCase):
    """引號外的反斜線跳過下一字元：`echo don\\'t` 的 `\\'` 是跳脫的撇號，不是單引號字串的開頭。
    修前它開出永不收尾的字串、把其後（含**同一行**）全遮；而且它與別的失同步互相抵銷時會讓
    漏擋被碰巧掩蓋（差分模糊測試：拿掉本規則，修前命中的指令有一批變成放行）。"""

    ESCAPED = ("echo don\\'t", 'echo \\"hi\\"', 'grep -E \\"a|b\\" f')

    def test_a_destructive_git_after_it_is_judged_on_the_same_and_the_next_line(self) -> None:
        for form in self.ESCAPED:
            for joiner in (" ; ", " && ", "\n"):
                with self.subTest(form=form, joiner=joiner):
                    self.assertTrue(G.destructive_git_hits(f"{form}{joiner}git stash"))
                    self.assertTrue(G.waitform_hits(f"{form}{joiner}{_BG_TAIL}"))

    def test_text_after_it_that_is_a_real_string_stays_data(self) -> None:
        for command in ("echo don\\'t \"git stash\"", "echo \\\"hi\\\" 'git reset --hard'",
                        "echo \\\\\"git stash\"", "echo a\\\\'git clean -fd'"):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command), [])

    def test_an_escaped_backslash_does_not_escape_the_quote_after_it(self) -> None:
        """`\\\\` 是一個字面反斜線，其後的引號照常開字串——跳過**兩個**字元而不是只認 `\\"`。"""
        self.assertTrue(G.destructive_git_hits('echo \\\\"x" ; git stash'))
        self.assertTrue(G.destructive_git_hits("echo a\\\\'b' ; git stash"))


class TestCommitHeredocIsOneStringWhateverItsBodyQuotes(unittest.TestCase):
    """`git commit -m "$(cat <<'EOF' … EOF` 換行 `)"` 是 agent 最常寫的形態：body 裡的引號、
    撇號、括號都不得影響字串在哪裡收尾（修前奇數個 `"` 會把 body 的行當成裸字而**誤擋**，
    也會把訊息之後的真指令吞掉而**漏擋**）。"""

    #: body 裡**提到**毀滅性指令（資料）：整則 commit 指令不得被擋。
    DATA_BODIES = (
        "fix: git stash create is safe",
        'intro "quoted\nfix: git stash removal',
        "don't (a) isn't b) c\nline: git reset --hard",
        'say "hi" and "bye"\ngit clean -fd is data',
        "don't isn't can't\ngit stash",
    )
    #: 只有奇怪的引號／括號、沒有任何毀滅性字樣：訊息**之後**的真指令才是唯一命中來源
    #: （body 含毀滅字樣時修前的誤擋會讓「之後有沒有被判」這一問失去鑑別力）。
    QUOTE_BODIES = (
        'intro "quoted\nplain text',
        "don't (a) isn't b) c\nplain",
        'say "hi" and "bye"\nplain',
        "don't isn't can't\nplain",
    )

    @staticmethod
    def _commit(body: str, after: str = "") -> str:
        return f"git commit -m \"$(cat <<'EOF'\n{body}\nEOF\n)\"{after}"

    def test_the_body_is_data(self) -> None:
        for body in self.DATA_BODIES:
            with self.subTest(body=body[:30]):
                self.assertEqual(G.destructive_git_hits(self._commit(body)), [])
                self.assertEqual(G.waitform_hits(self._commit(body)), [])

    def test_a_real_git_after_the_message_is_judged(self) -> None:
        for body in self.QUOTE_BODIES:
            self.assertEqual(G.destructive_git_hits(self._commit(body)), [], body)
            for after in (" && git stash", "\ngit reset --hard"):
                with self.subTest(body=body[:30], after=after):
                    self.assertTrue(G.destructive_git_hits(self._commit(body, after)))


class TestUnclosedHereStringIsNotAHereString(unittest.TestCase):
    """`@"` 後面找不到 `"@` 時它根本不是 PowerShell here-string（bash 的 `curl -d @"$f"`）：
    修前整段掃到 EOF 全遮。真正的 here-string 仍整段當資料。"""

    def test_curl_at_quote_does_not_swallow_the_rest(self) -> None:
        for tail in ("\ngit stash", " ; git stash", "\ngit reset --hard"):
            with self.subTest(tail=tail):
                self.assertTrue(G.destructive_git_hits(f'curl -d @"$f" http://x{tail}'))
        self.assertEqual(G.destructive_git_hits('curl -d @"$f" http://x'), [])

    def test_a_real_here_string_still_hides_its_body(self) -> None:
        for command in ('$x = @"\ngit stash\n"@', "$x = @'\ngit reset --hard\n'@"):
            with self.subTest(command=command):
                self.assertEqual(G.destructive_git_hits(command), [])
        self.assertTrue(G.destructive_git_hits('$x = @"\nfoo\n"@\ngit stash'))


class TestMaskInertDesyncEndToEnd(unittest.TestCase):
    """真的起 child 行程、餵 hook 入口 stdin（`CLAUDE_PROJECT_DIR` 指向 repo）；指令只是
    payload 字串，hook 從不執行它。修前 `X` 加換行加 `git stash` 是 rc=0。"""

    @staticmethod
    def _run(command: str) -> subprocess.CompletedProcess[str]:
        return run_hook(bash_payload(command), env={"CLAUDE_PROJECT_DIR": str(_REPO_ROOT)})

    def test_the_control_git_stash_alone_exits_two(self) -> None:
        proc = self._run("git stash")
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_a_destructive_git_after_the_form_exits_two(self) -> None:
        form = _DESYNC_FORMS[3][1]
        for tail in _GIT_TAILS:
            with self.subTest(tail=tail):
                proc = self._run(f"{form}\n{tail}")
                self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_the_wait_forms_after_the_form_exit_two(self) -> None:
        form = _DESYNC_FORMS[3][1]
        for tail in (_BG_TAIL, _RC_TAIL):
            with self.subTest(tail=tail[:24]):
                proc = self._run(f"{form}\n{tail}")
                self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_the_form_alone_exits_zero_silently(self) -> None:
        for _name, form in (*_DESYNC_FORMS[:2], *_DESYNC_CONTROLS[:1]):
            with self.subTest(form=form):
                proc = self._run(f"{form}\nls")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stderr.strip(), "")


class TestMaskInertDesyncFixHasTeeth(unittest.TestCase):
    """合成注入：三個載重零件各自被拿掉時，對應的形態必須**重新漏判**——證明擋住它的是
    那個零件，不是別的東西恰好也擋了。零件會互相補位（遞迴掃描、引號外的反斜線跳脫都讓字串
    收尾判對；第二個視圖兜住看不懂的形態），所以鑑別形態各選「其他零件救不了」的那一種。"""

    def test_without_the_nested_scan_the_same_line_tail_is_hidden_again(self) -> None:
        """鑑別形態取 S6（單引號夾雙引號）：`\\"` 類形態另有「引號外反斜線跳脫」兜著，關掉巢狀
        掃描後仍會被平掃碰巧收對；只有 S6 與 commit heredoc 必須靠 `$( … )` 內引號自成一格。"""
        commands = (f"{dict(_DESYNC_FORMS)['S6']} ; git stash",
                    "git commit -m \"$(cat <<'EOF'\nintro \"quoted\nplain\nEOF\n)\" && git stash")
        original = G._quote_close
        for command in commands:
            self.assertTrue(G.destructive_git_hits(command), command)
            try:
                G._quote_close = (  # type: ignore[assignment]
                    lambda text, i, lim, nest, depth=0: original(text, i, lim, False, depth))
                self.assertEqual(G.destructive_git_hits(command), [],
                                 "拿掉巢狀掃描後同行尾巴仍被擋 ⇒ 擋住它的不是遞迴掃描")
            finally:
                G._quote_close = original  # type: ignore[assignment]
            self.assertTrue(G.destructive_git_hits(command), "注入沒有復原")

    def test_without_the_outside_escape_the_same_line_tail_is_hidden_again(self) -> None:
        for command in ("echo don\\'t ; git stash", 'echo \\"hi\\" ; git stash'):
            self.assertTrue(G.destructive_git_hits(command), command)
            with mock.patch.object(G, "_SHELL_ESCAPE", "\0"):  # 永不匹配 ⇒ 規則被拿掉
                self.assertEqual(G.destructive_git_hits(command), [],
                                 "拿掉引號外跳脫規則後同行尾巴仍被擋 ⇒ 擋住它的不是該規則")
            self.assertTrue(G.destructive_git_hits(command), "注入沒有復原")

    def test_without_the_second_view_the_next_line_is_hidden_again(self) -> None:
        command = f"{_PS_FORM}\ngit stash"
        self.assertTrue(G.destructive_git_hits(command))
        original = G._mask_pass
        try:
            G._mask_pass = (  # type: ignore[assignment]
                lambda text, keep_comments, keep_status, loose:
                original(text, keep_comments, keep_status, False))
            self.assertEqual(G.destructive_git_hits(command), [],
                             "拿掉第二個視圖後下一行仍被擋 ⇒ 擋住它的不是失同步網")
        finally:
            G._mask_pass = original  # type: ignore[assignment]
        self.assertTrue(G.destructive_git_hits(command), "注入沒有復原")


class TestMaskInertNestedScanIsBounded(unittest.TestCase):
    """守衛自己不得成為故障源：巢狀掃描的遞迴深度有上限（否則病態輸入的 RecursionError 會
    被 `main()` 的 fail-open 吞掉＝整支守衛對那條指令失效），失敗退回平掃的成本與輸入成線性。"""

    def test_deep_nesting_neither_raises_nor_changes_the_length(self) -> None:
        for depth in (10, 17, 200, 3000):
            command = "echo " + '"$(' * depth + "x" + ')"' * depth + "\ngit stash"
            with self.subTest(depth=depth):
                self.assertEqual(len(G.mask_inert(command)), len(command))
                self.assertTrue(G.destructive_git_hits(command))

    def test_unbalanced_openers_cost_scales_linearly(self) -> None:
        def best(openers: int) -> float:
            command = 'echo "$(" ' * openers + "\ngit stash"
            runs = []
            for _ in range(3):
                began = time.perf_counter()
                G.mask_inert(command)
                runs.append(time.perf_counter() - began)
            return min(runs)

        small, large = best(500), best(4_000)
        self.assertLess(large / small, 24, f"輸入放大 8 倍、成本放大 {large / small:.1f} 倍")
        self.assertLess(large, 2.0, f"4,000 個未收尾開頭 {large:.2f}s：逼近 hook 逾時＝fail-open")


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
