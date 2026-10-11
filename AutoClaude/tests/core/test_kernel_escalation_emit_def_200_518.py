"""DEF-200-518：Kernel（唯一正式路徑）的失敗型 ESCALATION 必須發布
ON_ESCALATION_DUMP_REQUEST → ON_ESCALATION。

驗證意圖（Rule 9）：守的是「機制蓋好沒接電」——checkpoint／notification／knowledge_base／
evolution 四個訂閱者從 SD_01 起就在等 ON_ESCALATION，而 kernel.py 自首次入庫從未 emit；
於是真跑 ESCALATION 後 checkpoints/ 空、零通知、零演化提案（F-SBR-001 的 C4 實測）。
同時守三條邊界，任一條被拿掉本檔必紅：
  (1) 只有兩條「失敗型」升級（收斂判 escalate／重試耗盡）走善後——與舊 steps_orchestrator
      同語意；PRE_STEP／PRE_ATTEMPT veto 與 Brain 故障不走（舊路徑對它們亦無 dump）。
  (2) 善後 fail-soft：EventBus.emit 會把 plugin 例外原樣往外拋，不攔就把乾淨的 escalated
      結果變成未捕捉例外（main.py 無 try/except，連 KernelResult 都沒有）。兩段 emit 各自
      攔：DUMP 段失敗時 ON_ESCALATION 仍以 dump_path="" 發出，不連坐通知與演化提案。
  (3) 演化提案只出聲、不套用：AutoResumeService 的演化重載迴圈沒有 DEF-13-004 核可閘，
      任何把 MutationProposal 落成 evolved_playbook_path 的改動都會繞過 require_evolution_signoff。
"""
from __future__ import annotations

import logging

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import (
    EscalationDumpedResult,
    KernelPhase,
    MutationProposal,
    ResourceRequest,
    VetoResult,
)
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutation, StepMutationType

_AFTERMATH = (KernelPhase.ON_ESCALATION_DUMP_REQUEST, KernelPhase.ON_ESCALATION)


class _Exec:
    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        return ExecutionOutput(text="done")


class _AlwaysFail:
    """每次回不同的 eval_output；本檔 bus 不掛 ConvergencePlugin，升級只來自 retry 用盡。"""

    def __init__(self):
        self.n = 0

    def evaluate(self, task, output):
        self.n += 1
        return f"fail#{self.n}", f"out#{self.n}", 1


class _Pass:
    def evaluate(self, task, output):
        return None, "", 0


class _FailOnStep:
    """只有指定 step 一律失敗（每次簽名不同），其餘步驟通過——多步驟 playbook 用。"""

    def __init__(self, step_id):
        self.step_id, self.n = step_id, 0

    def evaluate(self, task, output):
        if task.step_id != self.step_id:
            return None, "", 0
        self.n += 1
        return f"fail#{self.n}", f"out#{self.n}", 1


class _Spy:
    def __init__(self, phases, responder=None, name="spy"):
        self._phases, self._responder, self._name = list(phases), responder, name
        self.ctxs = []

    def name(self):
        return self._name

    def priority(self):
        return 999

    def subscribed_phases(self):
        return self._phases

    def on_event(self, ctx):
        self.ctxs.append(ctx)
        return self._responder(ctx) if self._responder else None

    def phases(self):
        return [c.phase for c in self.ctxs]


def _pb(max_retries=1) -> Playbook:
    return Playbook(
        version="1.0", project="esc-test",
        global_invariants=GlobalInvariants(max_retries_per_step=max_retries),
        tasks=[PlaybookTask(step_id="T01", name="step", prompt="do")],
    )


def _run(*, phases=_AFTERMATH, responder=None, extra=(), max_retries=1,
         evaluator=None, brain=None, pb=None):
    bus = EventBus()
    spy = _Spy(phases, responder)
    bus.register(spy)
    for p in extra:
        bus.register(p)
    kernel = PlaybookKernel(_Exec(), evaluator or _AlwaysFail(), bus=bus, brain=brain)
    return kernel.run(pb or _pb(max_retries)), spy


def test_retries_exhausted_emits_dump_request_then_escalation():
    def responder(ctx):
        if ctx.phase == KernelPhase.ON_ESCALATION_DUMP_REQUEST:
            return EscalationDumpedResult(
                contributor="spy", dump_path="/x/dump.md", dump="DUMP-OBJ")
        return None

    result, spy = _run(responder=responder, max_retries=1)

    assert result.escalated is True and "max_retries_exhausted" in result.reason
    # 順序是契約的一部分：先 dump（取回路徑與物件），後廣播（通知要帶路徑、演化要吃物件）
    assert spy.phases() == [KernelPhase.ON_ESCALATION_DUMP_REQUEST, KernelPhase.ON_ESCALATION]
    req, esc = spy.ctxs
    assert req.task.step_id == "T01" and req.step_idx == 0
    assert req.payload["trigger"] == "max_retries_exhausted"
    assert len(req.payload["failure_history"]) == 2          # max_retries=1 → 2 次 attempt
    assert req.payload["final_eval_output"] == "out#2"
    assert "max_retries_exhausted" in req.payload["human_hint"]
    # 發布者把 dump 的路徑與物件轉交下游；各訂閱者各取所需的 key（見備忘錄 §3.2）
    assert esc.payload["dump_path"] == "/x/dump.md"
    assert esc.payload["escalation_dump"] == "DUMP-OBJ"
    assert esc.payload["escalation_history"] == []
    assert esc.payload["trigger"] == "max_retries_exhausted"
    assert esc.payload["attempts_used"] == 2
    assert "T01" in esc.payload["title"] and "T01" in esc.payload["message"]


def test_request_escalation_path_emits_with_its_own_trigger():
    """C4 形態：升級來自 POST_ATTEMPT 的 request_escalation（收斂 plugin），遠早於 max_retries。"""
    result, spy = _run(extra=(_asker(),), max_retries=5)

    assert result.escalated is True and result.reason.startswith("[T01] ")
    assert spy.phases() == [KernelPhase.ON_ESCALATION_DUMP_REQUEST, KernelPhase.ON_ESCALATION]
    assert spy.ctxs[1].payload["trigger"] == "request_escalation"
    assert spy.ctxs[1].payload["attempts_used"] == 1


class _DeadBrain:
    def decide_correction(self, **kw):
        return None


def _veto(phase):
    return _Spy([phase], lambda c: VetoResult(contributor="gate", reason="blocked"), name="gate")


def _asker():
    return _Spy([KernelPhase.POST_ATTEMPT],
                lambda c: ResourceRequest(contributor="convergence", request_escalation=True),
                name="convergence")


def _scenario(label):
    """五種 Kernel 升級出口 → (extra plugins, brain, max_retries)。"""
    return {
        "retries_exhausted": ((), None, 1),
        "request_escalation": ((_asker(),), None, 5),
        "pre_step_veto": ((_veto(KernelPhase.PRE_STEP),), None, 2),
        "pre_attempt_veto": ((_veto(KernelPhase.PRE_ATTEMPT),), None, 2),
        "brain_outage": ((), _DeadBrain(), 2),
    }[label]


@pytest.mark.parametrize("label", ["pre_step_veto", "pre_attempt_veto", "brain_outage"])
def test_non_failure_escalations_do_not_run_the_aftermath(label):
    """與舊路徑同語意：治理 veto／使用者中斷／Brain 故障的升級沒有 dump、通知、演化提案。"""
    extra, brain, retries = _scenario(label)
    result, spy = _run(extra=extra, brain=brain, max_retries=retries)
    assert result.escalated is True, label
    assert spy.phases() == [], f"{label}: 不該發布 {spy.phases()}"


@pytest.mark.parametrize("label", [
    "retries_exhausted", "request_escalation", "pre_step_veto", "pre_attempt_veto", "brain_outage",
])
def test_every_escalation_exit_leaves_a_log_marker(label, caplog):
    """C4 §10：修前 log 完全沒有升級原因。五個出口一律留一行（含沒有善後的三種）。"""
    extra, brain, retries = _scenario(label)
    with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
        result, _ = _run(extra=extra, brain=brain, max_retries=retries)
    assert result.escalated is True
    assert "=== STATE: ESCALATION | step=T01 |" in caplog.text, label


def test_escalation_names_the_failing_step_not_the_first_one(caplog):
    """T01 過、T02 敗：marker 與兩段善後 ctx 都必須指向 T02（step_idx==1），不是第一步。

    WHY：其餘測試全是單步驟 playbook，`tasks[0]` 與 `tasks[step_idx]` 在那裡恆等——marker
    若寫成第一步（把人導去查一個其實通過的步驟），沒有任何測試會紅（QA 突變 Q10）。
    """
    pb = Playbook(
        version="1.0", project="esc-test-multi",
        global_invariants=GlobalInvariants(max_retries_per_step=1),
        tasks=[PlaybookTask(step_id="T01", name="first", prompt="do1"),
               PlaybookTask(step_id="T02", name="second", prompt="do2")],
    )
    with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
        result, spy = _run(evaluator=_FailOnStep("T02"), pb=pb)

    assert result.escalated is True and result.completed_step_ids == ["T01"]
    markers = [r.getMessage() for r in caplog.records if "STATE: ESCALATION" in r.getMessage()]
    assert len(markers) == 1 and "| step=T02 |" in markers[0], markers
    assert spy.phases() == [KernelPhase.ON_ESCALATION_DUMP_REQUEST, KernelPhase.ON_ESCALATION]
    for ctx in spy.ctxs:
        assert ctx.task.step_id == "T02" and ctx.step_idx == 1, ctx.phase
        assert ctx.payload["step_id"] == "T02", ctx.phase
    assert len(spy.ctxs[0].payload["failure_history"]) == 2   # 只含 T02 的兩次 attempt


def test_plugin_exception_in_aftermath_is_logged_not_raised(caplog):
    def boom(ctx):
        raise RuntimeError("notify backend exploded")

    with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
        result, spy = _run(phases=[KernelPhase.ON_ESCALATION], responder=boom)

    assert spy.phases() == [KernelPhase.ON_ESCALATION]       # 真的被叫到（修前根本沒發布）
    assert result.escalated is True and "max_retries_exhausted" in result.reason
    assert "ESCALATION 善後失敗" in caplog.text


def test_dump_phase_failure_does_not_swallow_the_escalation_broadcast(caplog):
    """DUMP 段拋例外 ⇒ ON_ESCALATION 仍要發，且 dump_path 為空字串、dump 物件為 None。

    WHY：善後曾是單一 try，DUMP 段一拋就連坐跳過 ON_ESCALATION——通知與演化提案跟著消失，
    使用者只剩一行 log。dump 檔是「附帶證據」，不該成為通知的單點故障（QA 探針實證）。
    刻意丟 OSError 而非 RuntimeError：except 若被縮窄成 RuntimeError，它會外洩成
    kernel.run() 的未捕捉例外（QA 突變 Q12 的 DUMP 段版）。
    """
    def boom_on_dump(ctx):
        if ctx.phase == KernelPhase.ON_ESCALATION_DUMP_REQUEST:
            raise OSError("disk exploded while assembling the dump")
        return None

    with caplog.at_level(logging.ERROR, logger="autoclaude.core.kernel"):
        result, spy = _run(responder=boom_on_dump)

    assert result.escalated is True and "max_retries_exhausted" in result.reason
    assert spy.phases() == [KernelPhase.ON_ESCALATION_DUMP_REQUEST, KernelPhase.ON_ESCALATION]
    esc = spy.ctxs[1]
    assert esc.payload["dump_path"] == "" and esc.payload["escalation_dump"] is None
    assert esc.payload["trigger"] == "max_retries_exhausted" and "T01" in esc.payload["message"]
    assert "ESCALATION 善後失敗" in caplog.text


def test_successful_run_emits_nothing():
    result, spy = _run(evaluator=_Pass())
    assert result.success is True and spy.phases() == []


def test_proposal_is_logged_but_never_applied(caplog):
    mut = StepMutation(
        mutation_type=StepMutationType.INJECT_BEFORE, new_step_id="T01_PRE",
        new_step_name="pre", new_step_prompt="fix the test file", reasoning="測試檔有語法錯誤",
    )

    def responder(ctx):
        if ctx.phase == KernelPhase.ON_ESCALATION:
            return MutationProposal(contributor="evolution", mutation=mut, rationale="r")
        return None

    pb = _pb(1)
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        result, _ = _run(responder=responder, pb=pb)

    assert "=== EVOLUTION PROPOSAL | [T01] type=INJECT_BEFORE" in caplog.text
    # 只提案不套用：playbook 原封不動、沒有演化版路徑（否則繞過 AutoResumeService 缺的核可閘）
    assert [t.step_id for t in pb.tasks] == ["T01"]
    assert result.evolved_playbook_path is None and result.escalated is True
