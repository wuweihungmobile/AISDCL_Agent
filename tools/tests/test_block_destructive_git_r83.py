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

import json
import ntpath  # R96／B-8：Windows 路徑語意的**真實實作**，注入用（不是手捏的假貨）
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

        WHY 這條值得一支具名測試：`_SEP_RE` 把 `\\n` 當語句邊界，所以在折回去之前，
        立案的那條指令只要在 `git` 後面換行就整條漏擋——**繞過方式不需要任何巧思，
        把長指令排版一下就會自然發生**。獨立驗證輪實測：本機 60 份逐字稿的 4,087 條
        shell 指令裡有 30 條用了行接續、其中 17 條是 git 指令，不是假想形態。
        這一向壞掉時是靜默的（守衛照跑、照回 0），故不能只靠 BLOCKED 那張單行清單守。
        """
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

    WHY 不硬擋：Bash（mac）／PowerShell（Windows）是這台機器上唯一的 shell 載具，
    對一份根本讀不出內容的 payload 硬擋它，等於用一個讀不懂的輸入換掉整個工作面。
    WHY 不靜默：守衛失效必須看得見——靜默放行是本 repo 一再判紅的那個方向。
    （`tools/tests/test_check_hooks_liveness.py::degraded_payload_verdict` 是同一條
      判準的通用版；本檔負責證明**這一支**真的落在它允許的那一格。）
    """

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

        本條刻意**不**去掃逐字稿（那是機器狀態、CI 上不存在，會讓全新 clone 必紅），
        改釘「兩個平台各自的 shell 載具都在射程內」這個結構事實：mac 送指令的工具是
        `Bash`，Windows 因鐵律一禁用 Bash ⇒ 一律走 `PowerShell`。少任一個，就有一整個
        平台不受守。
        """
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
        """R80 起 hook 條目一律 exec form，且每個邏輯 hook 兩條（Windows + POSIX 載具），
        各平台恰好一條成立、另一條 spawn 失敗（fail-open）。退回 shell form 會讓
        Windows 每觸發一次就閃一個 console 視窗。"""
        wiring = self._wiring()
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8-sig"))
        entry = wiring.entries_launching(settings, "block_destructive_git",
                                         event="PreToolUse")[0]
        mine = [h for h in entry["hooks"]
                if any("block_destructive_git" in a
                       for a in wiring.hook_entry_argv(h))]
        self.assertEqual(len(mine), 2, f"跨平台配對不是兩條：{mine}")
        self.assertTrue(all(wiring.is_exec_form(h) for h in mine),
                        "有條目退回 shell form")
        commands = {str(h.get("command", "")) for h in mine}
        self.assertTrue(commands & set(wiring.WIN_CARRIERS), "缺 Windows 載具")
        self.assertTrue(any(wiring.is_posix_carrier(c) for c in commands),
                        "缺 POSIX 載具")

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
    R89 收尾證據檔）。
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
        """🔴 反向包含的**邊界格**，獨立驗證輪實測出來的漏擋（不是想像的形態）。

        它躲得過上一支測試的機制、以及當時 `cd / && git clean -fdx` 被放行的實測，
        逐字＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。

        判準本身刻意不寫死 `/`：用 `os.path.abspath(os.sep)` 取當前平台的根
        （Windows 上是磁碟機根），否則這支鎖在另一個平台上量的是別的東西。
        """
        fs_root = os.path.abspath(os.sep)
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

        這一支的存在理由與上面三支不同：它守的不是「判準會不會恆真」，而是
        「**已知會漏的那個寫法不准回來**」（舊寫法下的實測 rc＝R89 收尾證據檔）。
        """
        fs_root = os.path.abspath(os.sep)
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
#: 該擋的：三條判準各自的真實形態。前兩筆逐字取自 R83 收輪的實帳指令。
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

    WHY 這一族值得一道阻斷臂：失敗的表徵與「還在正常進行」**完全相同**——R83 收輪實帳
    00:39 → 01:27 共 48 分鐘零工作，靠掌舵者來問才發現。而 `until ! pgrep -f <字面>`
    的兄弟互匹在**單支試跑下永遠是綠的**（`man pgrep` 只排除自己與祖先），所以它連
    「試一次就知道」都做不到。
    """

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

        🔴 探針選擇是本輪實測訂正過的：第一版拿 SD-02 那條唯一假陽性
        （`nohup true; python … & BGPID=$!; wait $BGPID`）當探針，結果注入後**仍然放行**
        ⇒ 那條假陽性其實是被**切段**收掉的，不是被 `wait` 豁免收掉的。兩道收窄各救哪一族
        不能用直覺分配——注入測試當場把它量了出來（同 SD-02「需兩道收窄」的兩道各自成立）。
        """
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
        """`&&`／`2>&1`／`&>`／`|&` 四種排除各自都是實測會製造假紅的寫法。"""
        for good in ("nohup make a && make b", "nohup python x.py 2>&1 | tee log",
                     "nohup bash x.sh &> /tmp/log"):
            with self.subTest(good=good):
                self.assertEqual(G.waitform_hits(good), [])
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

        🔴 探針同樣是實測訂正過的：第一版拿 `pgrep … | while read p` 當探針，注入後仍
        放行——因為那條救它的是**位置順序**（pgrep 在 `while` 之前，本來就不在掃描區間內），
        不是條件邊界。真正只有邊界救得了的是「pgrep 在 `do` **之後**」這一族。
        """
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
    """🔴 鐵律六那一族是加在**既有** hook 上的，而該檔的 tier 餘裕本來就窄。

    立案理由：本包落地時該檔 `count_loc` 距 `guardrail_cli` tier 只剩兩位數餘裕。
    把「還在預算內」寫成散文等於沒寫——下一個往這支 hook 加判準的人需要的是一個會紅的東西。
    判準本身**不複寫預算數字**（現查 `check_loc_budget` 的 SSOT，同 CLAUDE.md 的既有政策）。
    """

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

        拿掉它，一張**命令字串表**會被整串攤平成一段假指令而命中。逐字用普查裡真的
        撞到的那一筆（一支探針在列舉 `-p` 家族要不要擋），不是好寫測試的簡化版。

        🔴 注入形態是**收窄前的實作本體**，不是去戳 `_GIT_EXE_RE`：那個 regex 同時是
        `git_invocations()` 找執行檔用的（改它會連掃描器一起弄壞，於是注入後反而不命中
        ——本輪第一版就是這樣寫的，測試紅了才發現注的不是同一個零件）。
        """
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
    """🔴 誠實劃界要求的另一半：擋不到的必須**看得見**。

    判準刻意只看 `refs/stash`：它**只會**因 stash push／pop／drop／clear 而變。
    本守衛結構上碰不到的那四條路、以及第一版為何不看 `logs/HEAD`，逐字＝
    `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
    """

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

        ack **不是**子字串判定，也**不含**「被擋」與 `stash create` 兩種（前者根本不會跑、
        後者一個字節都不動那個 ref ⇒ 都解釋不了任何變動）；被訂正掉的兩處假事實逐字＝
        `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
        判準與紅綠自證見 `TestR84SentinelAckIsNotASubstring`。"""
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

    def test_end_to_end_the_note_is_loud_but_never_blocking(self) -> None:
        """🔴 rc **必須是 1 不是 2**：它是偵測不是攔截。把它做成阻斷，等於用一個
        「事後才知道」的訊號去擋一條與它無關的工具呼叫——那種守衛會被整個關掉。"""
        self.ref.write_text("aaaaaaaaaaaa\n", encoding="utf-8")
        payload = {"tool_name": "Bash", "cwd": str(self.root),
                   "tool_input": {"command": "echo hi"}}
        self.assertEqual(run_hook(payload).returncode, 0)
        self.ref.write_text("bbbbbbbbbbbb\n", encoding="utf-8")
        proc = run_hook(payload)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("refs/stash", proc.stderr)

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

        `-c` 的 operand 住在引號裡 ⇒ 在殼文字那個遮蔽面上整段是空白，`_RELAX_KILLER_RE`
        看不到它裡面的子殼括號。於是 `sh -c '(cd /wt); git clean -fdx'` 會被判成「落在
        /wt」而**放行**——實際上 `)` 已經結束了 cd 的作用域、git 落在共用工作樹。
        修法：放寬殺手在兩個平面上各跑一次。兩向都驗：老實的 `cd` 該放行、子殼該擋。
        """
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
        """把 Windows 的兩個前提顯式注入：`os.path.normcase` 與 `os.path.realpath`。

        🔴 P0-1：識別邏輯搬到 `tools/lib/worktree_paths.py`
        （`is_under_disposable_worktree()`）後，正規化不再只靠 `normcase`——`realpath`
        才是解掉 `..` 那一半（見該模組測試 `test_worktree_paths.py`）。兩者都要注入
        `ntpath` 語意才能讓 mac／Linux 也真的走進混合分隔符／大小寫這兩格：
        `ntpath.realpath` 在沒有 `nt` 模組時（POSIX）退化成純字面 `normpath`／
        `abspath`，不摸磁碟（CPython `ntpath.py` 原始碼確認），所以在假造的
        Windows 語意下兩平台結果一致。
        """
        return (mock.patch.object(G.os.path, "normcase", ntpath.normcase),
                mock.patch.object(G.os.path, "realpath", ntpath.realpath))

    def test_the_mixed_separator_shape_is_judged_on_every_platform(self) -> None:
        """🔴 R96 收尾／B-8：混合分隔符那條放行路必須在**兩個平台**都真的走得進去。

        此前唯一在守它的是上一支放行清單裡那一行
        `f"…{_REPO_ROOT}/.claude/worktrees/agent-ac3ed"`——只有在 `_REPO_ROOT` 渲染成
        反斜線（Windows）時才合成得出混合分隔符；macOS／Linux 上 `_REPO_ROOT` 是純正
        斜線 ⇒ 混合形態**結構上造不出來** ⇒ 把正規化整個刪掉，mac 全綠。也就是說，R96
        對「單平台專屬判準在對面平台失效」的修法，它自己的回歸鎖犯了同一個錯。
        修法＝顯式注入 Windows 語意（`ntpath.normcase`／`ntpath.realpath` 就是 Windows
        上真正在跑的那份實作），於是 mac 上也真的比到同一條判準。
        """
        victim = str(_REPO_ROOT).replace("/", "\\") + "/.claude/worktrees/agent-ac3ed"
        command = f"git worktree remove --force {victim}"
        normcase_patch, realpath_patch = self._as_windows()
        with normcase_patch, realpath_patch:
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

        NTFS 大小寫不敏感 ⇒ `…\\.CLAUDE\\WORKTREES\\agent-x` 與小寫寫法指的是**同一棵
        樹**，而 `.replace("/", os.sep)` 版本比不到 ⇒ 同一類 routine teardown 只要換個
        大小寫寫法就又被誤擋。改用 `normcase` 之後兩種寫法同判——「改了沒人守」是本
        repo 反覆判過的形態，所以這一支與換法同輪落地。
        """
        victim = str(_REPO_ROOT).replace("/", "\\") + "\\.CLAUDE\\WORKTREES\\agent-ac3ed"
        command = f"git worktree remove --force {victim}"
        normcase_patch, realpath_patch = self._as_windows()
        with normcase_patch, realpath_patch:
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

        R96 版判準是 `_DISPOSABLE_WT in normcase(victim)`，不解析 `..` ⇒
        `.claude/worktrees/../../AutoClaude` 字面上仍帶著 `.claude\\worktrees\\` 這段
        子字串而被誤判放行；同一招甚至能繞出 `.claude/worktrees/../..`＝repo 根自己。
        兩例當回合唯讀實測見 P0-1 修復前的 `_worktree_hit()` 註解（已隨修復移除）。
        """
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
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("refs/stash", proc.stderr,
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


class TestR84TheWaitformDocstringIsTheSingleHome(unittest.TestCase):
    """QA-03：同一份知識三個家、三種內容（hook docstring 說三條、CLAUDE.md 鐵律六說兩條、
    帳本的③ 又是第三種東西）。**SSOT ＝ `waitform_hits()` 的 docstring**（實作所在）。

    這一條把「docstring 與實作逐字相符」做成機械物：docstring 自陳幾條，就必須真的有
    幾條判準各自能單獨命中。只斷言「docstring 裡有 ① ② ③」會恆綠——那正是本 repo
    反覆判紅的「鎖存在但沒有鑑別力」。
    """

    def test_the_docstring_declares_three_and_all_three_can_fire_alone(self) -> None:
        doc = G.waitform_hits.__doc__ or ""
        self.assertIn("**三條**判準", doc, "docstring 沒有明說幾條 ⇒ 讀者只能去猜")
        for marker in ("· ①", "· ②", "· ③"):
            self.assertIn(marker, doc)
        # ①：nohup ＋ 背景 &（前景呼叫，旗標為 False）
        self.assertTrue(G.waitform_hits("nohup python x.py > log 2>&1 &"))
        # ②：until 條件內的裸 pgrep -f
        self.assertTrue(G.waitform_hits("until ! pgrep -f 'run_root_unittests'; do :; done"))
        # ③：只有旗標為真時才成立（同一條指令在前景是放行的）
        self.assertEqual(G.waitform_hits("python x.py &"), [])
        self.assertTrue(G.waitform_hits("python x.py &", run_in_background=True))

    def test_the_wait_carve_out_asymmetry_is_documented_and_real(self) -> None:
        """docstring 宣稱 `wait` 豁免**只罩 ①③、不罩 ②** ⇒ 兩向都實測。"""
        self.assertIn("只罩 ①③、不罩 ②", G.waitform_hits.__doc__ or "")
        self.assertEqual(G.waitform_hits("nohup python x.py & wait"), [])
        self.assertTrue(
            G.waitform_hits("until ! pgrep -f 'run_root_unittests'; do :; done; wait"),
            "`wait` 竟然把判準② 也一起放行了 ⇒ docstring 的不對稱宣稱是假的")


# ── ⑧ 授權邊界：無人看管回合禁動 git 歷史（R85／P12，**mac 側先前零機械物**）──────
class TestUnattendedAuthzHasTeethOnEveryPlatform(unittest.TestCase):
    """R79 立的 Auto Pilot 條件，在 macOS 上到 R85 為止**一行都不會跑**。

    立案與假紅普查（母體＝transcripts，假陽性 0）原文＝GovWrite 證據檔 §6.7；數字一律現查。

    本類與姊妹鎖 `test_check_hooks_liveness.TestUnattendedCommitPushBlock` 守**同一條
    規則的另一個平台**，四件事逐一對齊（每一件都帶反向，只帶一個方向必在另一向恆綠）：
    ①有訊號×動 git 歷史→exit 2；②**沒有訊號**×同一批→exit 0（互動 session 零附帶面，
    這一條壞掉＝掌舵者自己的 commit 被鎖死）；③有訊號×無關指令→放行；④行內豁免無效。
    """

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

    六個方向對齊本檔既有慣例：①該擋的擋（無人值守 × 保護面 × 三種寫檔工具）；
    ②不該擋的放行（有人值守／保護面之外／專案根之外的同名檔）；③逃生口；
    ④開關不共用（**雙向**都驗）；⑤退化 payload fail-open；⑥判準本身可證偽。
    """

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

    def test_attended_is_loud_but_not_blocking(self) -> None:
        """主 session 每輪都要改這些檔——擋了，守衛就會被整個關掉（repo 判例）。"""
        proc = run_hook(self._payload(".claude/settings.json"), env=self._env())
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("治理檔", proc.stderr, "出聲面必須說明這是治理檔")

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
