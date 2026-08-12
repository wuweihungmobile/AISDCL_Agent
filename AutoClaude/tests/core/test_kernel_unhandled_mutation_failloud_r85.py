"""R85 F3 / ARCH-03 階段 0：Kernel 未處理的突變型別必須**大聲失敗**。

立案事實（本輪逐項真跑，不是引述複審意見）：
  · `main.py` → `AutoResumeService` → `PlaybookKernel`。Kernel 的 `_apply_mutation`
    只認 GOTO_STEP／INJECT_BEFORE／INJECT_AFTER／REVISE_CURRENT 四種。
  · `DELETE_STEP`／`SKIP_TO`／`CONDITIONAL` 三種走到這裡在本輪之前是**完全靜默**地
    被丟掉——實測（logging 開到 DEBUG）：三種型別各跑一次，零 log 行、playbook 零變化、
    回傳 None。⇒ 失效表徵與「突變已成功套用」完全相同。
  · 那三種的完整實作住在 `execution/mutation_applier/`（PlaybookRunner 路徑）與
    `core/services/mutation/`（MutationApplyService 路徑），而兩條路徑的入口
    `PlaybookRunner` 今天**零 production 建構點**（見下方普查，附對照組）。

本檔守三件事，缺一都會讓這個發現在下一輪變回散文：
  (a) 「Kernel 只認哪幾種」是**現查出來的量測值**，不是這段 docstring 說的；
  (b) 未處理型別真的會出聲（且訊息點名是哪一種）；
  (c) 正控：四種已處理型別**不得**出聲——會對正常路徑製造噪音的守衛活不過一輪。

🔴 本檔**不主張**該刪那 275 行不可達實作。刪除是不可逆的架構決策（且需 `git rm`
   跨包），本輪只把「它今天不可達」變成可被機械複驗的事實，交收尾窗口裁決。
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest

from autoclaude.core.kernel import PlaybookKernel
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutation, StepMutationType

_AUTOCLAUDE = Path(__file__).resolve().parents[2]
_PKG = _AUTOCLAUDE / "autoclaude"

#: Kernel 路徑今天真的會套用的型別（下方 (a) 以 AST 現查釘住這個集合）。
_KERNEL_HANDLED = frozenset({
    StepMutationType.GOTO_STEP, StepMutationType.INJECT_BEFORE,
    StepMutationType.INJECT_AFTER, StepMutationType.REVISE_CURRENT,
})
_KERNEL_DROPPED = frozenset(StepMutationType) - _KERNEL_HANDLED


def _kernel_named_mutation_types() -> set[StepMutationType]:
    """AST 現查：`_apply_mutation` 函式體內逐字點名了哪幾個 StepMutationType 成員。"""
    tree = ast.parse((_PKG / "core" / "kernel.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_apply_mutation")
    names = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    return {m for m in StepMutationType if m.name in names}


def construction_sites(target: str, root: Path) -> list[str]:
    """AST 普查：`target` 這個名字在 `root` 底下被**呼叫**（＝建構）的位置。"""
    hits: list[str] = []
    for py in sorted(root.rglob("*.py")):
        if any(p in py.parts for p in (".venv", "__pycache__", ".git", "node_modules")):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:                                        # pragma: no cover
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                f = n.func
                if (getattr(f, "id", None) or getattr(f, "attr", None)) == target:
                    hits.append(f"{py.relative_to(root).as_posix()}:{n.lineno}")
    return hits


def _bare_kernel() -> PlaybookKernel:
    # `_apply_mutation` 不碰任何 port ⇒ 刻意不建整套依賴（建了才是把測試耦合到 wiring）。
    return PlaybookKernel.__new__(PlaybookKernel)


def _two_step_playbook() -> Playbook:
    return Playbook(version="1.0", project="p", tasks=[
        PlaybookTask(step_id="T01", name="a", prompt="ORIG"),
        PlaybookTask(step_id="T02", name="b", prompt="y"),
    ])


class TestWhichTypesTheKernelActuallyHandles:
    """(a) 「只認四種」必須是現查值。有人補上第五種 ⇒ 本格紅，逼他同步這裡與報告結論。"""

    def test_the_handled_set_is_measured_from_source(self):
        assert _kernel_named_mutation_types() == _KERNEL_HANDLED

    def test_the_dropped_set_is_not_empty(self):
        """取數管道自證：補集為空時，下方 (b) 整組會變成分母 0 的假綠。"""
        assert _KERNEL_DROPPED == {
            StepMutationType.DELETE_STEP, StepMutationType.SKIP_TO,
            StepMutationType.CONDITIONAL,
        }


class TestTheUnreachableImplementationsAreReallyUnreachable:
    """P11 的「production 零建構點」宣稱——本輪獨立複驗，並附**已知會命中的對照組**。

    只驗「PlaybookRunner 零命中」是不可信的：掃描器整個壞掉時它也是零。
    """

    def test_playbook_runner_has_no_production_construction_site(self):
        prod = [h for h in construction_sites("PlaybookRunner", _AUTOCLAUDE)
                if not h.startswith("tests/")]
        assert prod == [], f"PlaybookRunner 出現 production 建構點，本檔結論需重新檢視：{prod}"

    def test_the_scanner_can_see_production_sites_at_all(self):
        """對照組：同一支掃描器對 `PlaybookTask` 必須抓得到 production 建構點。"""
        prod = [h for h in construction_sites("PlaybookTask", _AUTOCLAUDE)
                if not h.startswith("tests/")]
        assert len(prod) >= 10, f"對照組只抓到 {len(prod)} 筆，掃描器可能壞了"

    def test_the_conditional_implementations_are_only_reachable_through_it(self):
        """兩份 CONDITIONAL 實作的唯一入口都在 PlaybookRunner 之下 ⇒ 隨它一起不可達。

        · `core/services/mutation/` → `MutationApplyService.apply`
        · `execution/mutation_applier/_conditional.py` → `_apply_single_mutation`
        """
        callers = {h.rsplit(":", 1)[0] for h in construction_sites("apply", _PKG)}
        service_callers = {c for c in callers if "mutation" not in c}
        assert service_callers <= {"execution/playbook_runner.py"}, service_callers


class TestUnhandledMutationsAreLoud:
    """(b) 未處理型別必須出聲，且訊息要點名是哪一種——只說「有問題」等於沒說。"""

    @pytest.mark.parametrize("mt", sorted(_KERNEL_DROPPED, key=lambda m: m.name))
    def test_it_says_which_type_it_dropped(self, mt, caplog):
        mut = StepMutation(mutation_type=mt, delete_step_id="T02", skip_to_step_id="T02",
                           condition_evaluator="exit 0")
        pb = _two_step_playbook()
        with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
            PlaybookKernel._apply_mutation(_bare_kernel(), pb, pb.tasks[0], 0, mut, 0)
        errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
        assert errors, f"{mt.name} 被靜默丟棄——失效表徵與『已套用』完全相同"
        assert any(mt.name in m for m in errors), errors

    def test_it_does_not_change_control_flow(self):
        """階段 0 只出聲：回傳值與 playbook 內容都必須與出聲之前一模一樣。

        改成 raise 會把「模型提了 Kernel 不支援的突變」升級成整輪中止＝行為變更，
        需另案裁決；本格擋住那個改動被順手做掉。
        """
        pb = _two_step_playbook()
        mut = StepMutation(mutation_type=StepMutationType.DELETE_STEP, delete_step_id="T02")
        out = PlaybookKernel._apply_mutation(_bare_kernel(), pb, pb.tasks[0], 0, mut, 0)
        assert out is None
        assert [t.step_id for t in pb.tasks] == ["T01", "T02"]
        assert pb.tasks[0].prompt == "ORIG"

    def test_a_missing_payload_on_a_handled_type_is_also_loud(self, caplog):
        """型別對、payload 缺（例：GOTO 沒給 goto_step_id）同樣什麼都不會發生 ⇒ 也要出聲。"""
        pb = _two_step_playbook()
        mut = StepMutation(mutation_type=StepMutationType.GOTO_STEP)
        with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
            PlaybookKernel._apply_mutation(_bare_kernel(), pb, pb.tasks[0], 0, mut, 0)
        assert [r for r in caplog.records if r.levelno >= logging.ERROR]


class TestTheHandledPathStaysQuiet:
    """(c) 正控。會對正常路徑製造噪音的守衛會被整個關掉，而被關掉的守衛比沒有更糟。"""

    @pytest.mark.parametrize("mut", [
        StepMutation(mutation_type=StepMutationType.REVISE_CURRENT, revised_prompt="NEW"),
        StepMutation(mutation_type=StepMutationType.INJECT_AFTER, new_step_prompt="p"),
        StepMutation(mutation_type=StepMutationType.INJECT_BEFORE, new_step_prompt="p"),
        StepMutation(mutation_type=StepMutationType.GOTO_STEP, goto_step_id="T01"),
    ], ids=lambda m: m.mutation_type.name)
    def test_no_error_for_an_applied_mutation(self, mut, caplog):
        pb = _two_step_playbook()
        with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
            PlaybookKernel._apply_mutation(_bare_kernel(), pb, pb.tasks[1], 1, mut, 0)
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


class TestARegisteredDefectNotADesiredBehaviour:
    """🔴 本輪順帶量到的第二筆靜默丟棄——**登記，不是背書**。

    Kernel 的 INJECT_AFTER／INJECT_BEFORE 建 `PlaybookTask` 時**沒有帶
    `evaluator_command`** ⇒ 模型依 schema 產出的 `new_step_evaluator_command`
    在 production 路徑上被整欄丟掉，注入步驟因此只剩 regex 驗證（Gap-036 當初正是
    為了「防假陽性通過」才加這一欄）。它與本檔主題同源：**丟東西不出聲**。
    這裡把它釘成可見的事實；修法（補上該欄）會讓本格轉紅，那時請把本類刪掉。
    """

    @pytest.mark.parametrize("mt", [StepMutationType.INJECT_AFTER,
                                    StepMutationType.INJECT_BEFORE],
                             ids=lambda m: m.name)
    def test_the_injected_step_currently_loses_its_evaluator_command(self, mt):
        pb = _two_step_playbook()
        mut = StepMutation(mutation_type=mt, new_step_prompt="p", new_step_id="NEW",
                           new_step_evaluator_command="pytest -q")
        PlaybookKernel._apply_mutation(_bare_kernel(), pb, pb.tasks[0], 0, mut, 0)
        injected = next(t for t in pb.tasks if t.step_id == "NEW")
        assert injected.evaluator_command is None
