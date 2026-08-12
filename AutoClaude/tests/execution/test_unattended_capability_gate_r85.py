"""R85 / AC-(a)：無人看管回合（`AUTOSDD_UNATTENDED=1`）的 AutoClaude 側能力閘回歸鎖。

AC-(a) 的裁決（R83）是「不要再嘗試自動變回真舵手，該做的是把 headless 代理的能力面
寫清楚」。R84 把它記成散文就結案了；本檔是那句話的機械面。

🔴 本鎖存在的**結構性理由**（不是「多一道保險」）：
    monorepo 根層的 PreToolUse 守衛只看得到 Claude Code 的 `tool_input.command`。
    無人看管回合送出的是**一條** `python -m autoclaude <playbook>`——本身完全無害、
    必然放行；其後 AutoClaude 自己以 `subprocess.Popen(shell=True)` 送出的每一條指令
    都在**另一棵行程樹**裡，結構上不產生任何 tool 呼叫 ⇒ 那六支守衛一次都不會被叫到。
    這一格只有 AutoClaude 自己補得起來，而失明是靜默的（rc／log／畫面與「有在守」相同）。

三組判準，各自守不同的失效方向：
  (a) 閘真的會擋（正面），且**兩個** `shell=True` 執行面都接上了——關掉一扇門只會讓人走另一扇。
  (b) 零附帶面（反面）：互動 session（無該環境變數）下一行行為都不變；讀取型 git 不受影響。
  (c) 射程普查：`autoclaude/` 內 `shell=True` 的站點數是**量測值**，新開一個沒接閘的
      執行面即紅。這一條是為了讓「下一個人新增第三個執行面」不會靜默逃掉。
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude.execution.evaluator import Evaluator, unattended_refusal

_ENV = "AUTOSDD_UNATTENDED"
_PKG = Path(__file__).resolve().parents[2] / "autoclaude"


@pytest.fixture
def unattended(monkeypatch):
    monkeypatch.setenv(_ENV, "1")


@pytest.fixture
def interactive(monkeypatch):
    monkeypatch.delenv(_ENV, raising=False)


#: 必擋：寫入遠端／歷史的動詞。含「藏在複合指令後半」的形態——真實的 evaluator_command
#: 幾乎都是複合指令，只判開頭那一個 token 等於沒判。
_MUST_DENY = [
    "git commit -m x",
    "git push",
    "git push --force origin main",
    "pytest -q && git commit -am wip",
    "make test; git push",
    "gh pr create --fill",
    "gh pr merge 12 --squash",
    "gh release create v1",
    "/usr/bin/git commit -m x",
    # 帶空白的 Windows 安裝路徑**必須加引號**才在殼上跑得起來；不加引號那一種
    # （`C:\Program Files\...\git.exe push`）在 cmd.exe 上會去找 `C:\Program`，
    # 本來就不是可行的逃逸口，故刻意不列進必擋組。
    r'"C:\Program Files\Git\bin\git.exe" push',  # platform-ok: 這是**待判定的指令字串語料**，不是本測試要 join 的路徑——判準吃的是整條 argv 文字，Windows 形態的 git 呼叫正是它必須擋下的形態之一，換成 POSIX 假路徑就測不到這一類  # noqa: E501
    "git -C /tmp/x commit -m y",
    "GIT_AUTHOR_NAME=a git commit -m b",     # POSIX 殼的環境賦值前綴
    "env GIT_DIR=/tmp/x git push",
    "sudo git push",
]

#: 必放行：evaluator_command 的**真實**樣貌（跑閘門）＋ 讀取型 git ＋ 字尾巧合。
#: 這一組是本閘能不能活下來的關鍵——repo 已判過「擋到讓人無法工作的守衛會被整個關掉」。
_MUST_ALLOW = [
    "pytest tests/test_auth.py -v",
    "python -m pytest tests -q",
    "pytest tests/test_git_commit_helper.py",   # 檔名含動詞，不是在 commit
    "git status --porcelain",
    "git rev-parse --show-toplevel",
    "git diff --stat",
    "git log --oneline -5",
    "git log --grep=commit",                    # 動詞是參數的值
    "legit commit",                             # 字尾巧合：指令不是 git
    "ruff check .",
    "npm test",
    "",
]


class TestTheGateActuallyBites:
    @pytest.mark.parametrize("cmd", _MUST_DENY)
    def test_write_verbs_are_refused_when_unattended(self, cmd, unattended):
        reason = unattended_refusal(cmd)
        assert reason is not None, f"未擋下：{cmd!r}"
        # 理由必須帶上原指令：只回「被擋了」會讓無人看管回合的 log 無法事後歸因。
        assert cmd in reason

    def test_evaluator_run_refuses_without_spawning_anything(self, unattended):
        """閘必須擋在 Popen **之前**——擋在之後等於沒擋。

        WHY 這一格不 patch `unattended_refusal` 而 patch `Popen`：前者只證明
        「有呼叫那個名字」，證不到「拒絕時真的沒有起子行程」，而後者才是危害本體。
        """
        with patch("autoclaude.execution.evaluator.subprocess.Popen") as popen:
            result = Evaluator(timeout=5).run("git push")
        popen.assert_not_called()
        assert result.success is False
        assert result.exit_code == -1
        assert "git push" in result.output

    def test_conditional_mutation_surface_is_gated_too(self, unattended):
        """第二個 `shell=True` 執行面（CONDITIONAL）也必須擋在 Popen 之前。

        WHY 獨立一格：兩個執行面是**各自**呼叫 Popen 的，只鎖 Evaluator 那一個時，
        把 `git push` 寫進 `condition_evaluator` 就整片繞過——而那一刻沒有任何東西轉紅。
        """
        from autoclaude.execution.mutation_applier import _conditional

        mutation = type("M", (), {"condition_evaluator": "git push"})()
        with patch.object(_conditional.subprocess, "Popen") as popen:
            _conditional.handle_conditional(object(), mutation, object())
        popen.assert_not_called()


class TestZeroCollateralWhenAHumanIsWatching:
    @pytest.mark.parametrize("cmd", _MUST_DENY + _MUST_ALLOW)
    def test_interactive_sessions_are_never_touched(self, cmd, interactive):
        """互動 session 沒有那個環境變數 ⇒ 本閘恆放行，附帶面為零。

        這是刻意的設計（同根層守衛）：掌舵者自己跑閘門那條路不能被這道鎖碰到。
        """
        assert unattended_refusal(cmd) is None

    @pytest.mark.parametrize("cmd", _MUST_ALLOW)
    def test_real_gate_commands_still_run_when_unattended(self, cmd, unattended):
        """無人看管回合仍必須跑得動閘門（R83 裁定「能做的：收斂、寫任務書、跑閘門」）。

        假紅的代價不是「比較嚴格」：擋掉 pytest 就等於擋掉那一跑唯一該做的事，
        而被擋到無法工作的守衛會被整個關掉——那比沒有守衛更糟。
        """
        assert unattended_refusal(cmd) is None


class TestEveryShellSurfaceIsAccountedFor:
    #: `autoclaude/` 內以 `shell=True` 起子行程的站點。**這是量測值不是設定值**：
    #: 新開第三個執行面時本鎖轉紅，逼人回答「它接閘了沒」。刻意存相對路徑而非計數——
    #: 只存數字的話，刪掉一個、新增一個就會靜默相等。
    GATED_SHELL_SITES = frozenset({
        "autoclaude/execution/evaluator.py",
        "autoclaude/execution/mutation_applier/_conditional.py",
    })

    def _shell_true_sites(self) -> set[str]:
        found: set[str] = set()
        for py in _PKG.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:                                   # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for kw in node.keywords:
                    if (kw.arg == "shell"
                            and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True):
                        found.add(py.relative_to(_PKG.parent).as_posix())
        return found

    def test_no_ungated_shell_surface_exists(self):
        assert self._shell_true_sites() == self.GATED_SHELL_SITES, (
            "autoclaude/ 的 shell=True 執行面與已接閘清單不符。"
            "新增執行面 ⇒ 先接 unattended_refusal() 再把它加進 GATED_SHELL_SITES；"
            "移除 ⇒ 同步移除。兩個方向都不准靜默。"
        )

    def test_the_scanner_itself_can_see_a_new_surface(self, tmp_path):
        """證偽探針：掃描器對「新開的 shell=True 站點」必須真的看得見。

        WHY：本類唯一的失效模式是掃描器回空集合而集合比對照樣綠（分母 0＝沒有東西
        可違反）。repo 已判過這種「有鎖在守假話」比沒有鎖更難看見。
        """
        probe = tmp_path / "probe.py"
        probe.write_text("import subprocess\nsubprocess.Popen('x', shell=True)\n",
                         encoding="utf-8")
        tree = ast.parse(probe.read_text(encoding="utf-8"))
        hits = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                for kw in n.keywords
                if kw.arg == "shell" and getattr(kw.value, "value", None) is True]
        assert hits, "掃描器連合成注入的 shell=True 都看不到，本類的綠是假的"


class TestTheDuplicationIsDeliberateNotAnAccident:
    def test_autoclaude_does_not_import_the_harness_guard(self):
        """本閘是**刻意的第二份實作**，理由是架構契約而不是疏忽。

        `.importlinter` 第 9 條（no-harness-import）禁止 autoclaude 匯入 monorepo 護欄層
        ⇒ 「統一成一份」的正確做法是改契約，不是偷偷 import。本格把這個理由釘住：
        哪天有人「順手收斂重複」而 import 過去，契約與本鎖會同時紅，不會只剩註解在講。
        """
        text = (_PKG / "execution" / "evaluator.py").read_text(encoding="utf-8")
        for forbidden in ("block_destructive_git", "lint_powershell_command",
                          "from tools", "import tools"):
            assert forbidden not in text, f"能力閘不得依賴護欄層：{forbidden}"

    def test_env_name_matches_the_injection_site_contract(self):
        """環境變數字面必須與注入端一致——拼錯時本閘恆放行，且完全靜默。"""
        assert unattended_refusal("git push") is None
        os.environ[_ENV] = "1"
        try:
            assert unattended_refusal("git push") is not None
        finally:
            os.environ.pop(_ENV, None)
