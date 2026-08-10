#!/usr/bin/env python
"""`.claude/hooks/block_destructive_git.py` 的回歸鎖（R83）。

WHY 這支鎖存在
--------------
被守的那支 hook 的立案事實：一個 subagent 在**六包並行共用的工作樹**上跑
`git stash -q -u --keep-index`，16 個修改檔 ＋ 4 個未追蹤檔瞬間消失（含其他包當時
正在寫的三支檔）。它自己 `git stash pop` 還原、前後 `git diff --stat` 逐字相同
——**沒有偵測到資料遺失，但那是運氣不是設計**。任務書當時已寫「不要 git add /
commit / push」⇒ **禁令沒涵蓋到的那個動詞，就是被踩的那個**。

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
import os
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
    for key in (G.GUARD_OFF_ENV, G.UNATTENDED_ENV):
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

    上一代姊妹守衛在這裡誤擋過（SD-02 實測三條規則全中），修法是「先把不是可執行
    結構的區段拿掉再比對」——本類是那個修法在本檔的回歸鎖。
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
        self.assertEqual(set(matcher.split("|")), set(G.OWN_TOOLS),
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

    WHY 這件事非做不可（不是便利性）：兩名複審者各自在自己 scratchpad 的拋棄式
    worktree 內跑 `git checkout -- <path>` 被擋下。repo 已判過「擋到讓人無法工作的守衛
    會被整個關掉，而被關掉的守衛比沒有守衛更糟」⇒ 誤擋是這道鎖的**存亡問題**。
    合成 repo 實測支撐這一族可以放：wt 內 `git checkout -- b.txt` 之後，主樹的
    `MAIN_UNCOMMITTED` 原封不動倖存。
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

    這是「只看樹就整條放行」會製造的新漏擋，而它漏掉的恰好是**立案那一條指令**。
    實測依據（合成 repo，主樹 ＋ 一棵 linked worktree）：在 wt 內跑
    `git stash -q -u --keep-index`，主樹的 stash 深度 **0→1**，兩邊
    `git rev-parse refs/stash` 是**同一個 SHA** ⇒ `refs/stash` 是 repo 級不是工作樹級。
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
    """換樹放寬的四道前提，每一條都對應一個**實測過**的漏擋形態。

    複審者的警告逐字：「只看『cwd 不在專案根』就整條放行，會不會製造新的漏擋？」
    本類就是那個問題的答案，逐條列舉並釘死。
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

        WHY 它躲得過上一支測試：包含判準原本寫 `p + os.sep`，而檔案系統根的
        `"/" + "/"` ＝ `"//"`，**沒有任何路徑以 `"//"` 開頭** ⇒ 反向包含在
        `target == "/"` 這一格恆假，`cd / && git clean -fdx` 實測被放行（rc=0）。
        `cd /Users …` 那一級擋得住，所以整條前提 ②「與專案根互不包含（雙向）」
        讀起來完全成立——這正是本 repo 反覆判紅的「鎖在、但某一格沒有鑑別力」，
        而它只有把根這一格真的送進去才看得見。

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

    本回合實測 PreToolUse payload 與 hook 行程狀態：`payload["cwd"]`、`os.getcwd()`、
    `$CLAUDE_PROJECT_DIR` **三者恆等於專案根**，即使被檢查的指令自己是
    `cd /private/tmp && pwd`。⇒ 在 hook 自己的 cwd 跑 `--show-toplevel`，答案恆為專案根、
    判準恆假、誤擋一次都沒少，**而程式碼看起來已經修好了**——那正是本 repo 反覆判紅的
    「鎖存在但沒有鑑別力」。本條把「不去問 git」釘成契約：下一個想改成 subprocess 的人
    必須先面對這個量測。順帶也守住阻斷路徑上不長出子行程（PreToolUse 每次工具呼叫都跑）。
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
        「**已知會漏的那個寫法不准回來**」。獨立驗證輪實測 `cd / && git clean -fdx`
        在舊寫法下 rc=0。
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
