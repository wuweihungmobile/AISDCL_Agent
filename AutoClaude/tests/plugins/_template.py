"""SD_Improving_05 W0 T0-5 — Plugin 單元測試標準模板。

供 W4 新建 FastPathPlugin / PlaybookPersistencePlugin 與 W2/W3 既有 Plugin
重寫使用。模板涵蓋：

  - FakePorts v2：BrainPort / EvaluatorPort / ExecutorPort / MemoryStorePort
    完整 fake 實作（dataclass 記錄呼叫參數，方便斷言）
  - FakeEventBus：可繞過 wiring，直接以 emit() 注入 HookContext，斷言 result
  - sample_playbook() / sample_task() / sample_state()：常用 fixture
  - HookContext 工廠 + payload 預設值

使用範例：
    from tests.plugins._template import (
        FakeEventBus, FakePorts, sample_playbook, make_ctx,
    )

    def test_my_plugin_emits_resource_request():
        bus = FakeEventBus()
        plugin = MyPlugin(...)
        bus.register(plugin)
        ctx = make_ctx(phase=KernelPhase.ON_TOKEN_USAGE,
                       payload={"token_pct": 85.0})
        result = bus.emit(ctx)
        assert result.request_compact is True

注意：本模板**不是**測試本身（檔名以 `_` 開頭，pytest 不會 collect），
僅供其他測試檔 import 使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.kernel_state import KernelResult
from autoclaude.models.playbook import (
    GlobalInvariants,
    Playbook,
    PlaybookTask,
)


# ─────────────────────────────────────────────────────────────
# 1. Sample factory functions
# ─────────────────────────────────────────────────────────────
def sample_task(step_id: str = "T01", name: str = "sample step",
                prompt: str = "do something") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name=name, prompt=prompt)


def sample_playbook(*, project: str = "TEST", n_tasks: int = 3,
                    global_goal: Optional[str] = None) -> Playbook:
    tasks = [sample_task(f"T{i:02d}", f"step {i}", f"prompt {i}")
             for i in range(1, n_tasks + 1)]
    return Playbook(
        version="1.0",
        project=project,
        global_goal=global_goal,
        global_invariants=GlobalInvariants(),
        tasks=tasks,
    )


def make_ctx(*, phase: KernelPhase, playbook: Optional[Playbook] = None,
             task: Optional[PlaybookTask] = None,
             step_idx: Optional[int] = None, attempt: Optional[int] = None,
             payload: Optional[dict] = None) -> HookContext:
    """HookContext 工廠，提供 sensible defaults。"""
    return HookContext(
        phase=phase,
        playbook=playbook or sample_playbook(),
        task=task or sample_task(),
        step_idx=step_idx if step_idx is not None else 0,
        attempt=attempt if attempt is not None else 1,
        payload=payload or {},
    )


# ─────────────────────────────────────────────────────────────
# 2. FakePorts v2 — 完整 4 個 port fake
# ─────────────────────────────────────────────────────────────
@dataclass
class _Call:
    name: str
    args: tuple
    kwargs: dict


@dataclass
class FakeBrain:
    """IBrain fake — 對齊 autoclaude.core.ports.brain.IBrain.decide_correction。

    SD_05 W0 三方審查 SD-M8：方法名與 port 對齊（原 propose() 為錯誤命名）。
    """
    next_decisions: list = field(default_factory=list)
    calls: list[_Call] = field(default_factory=list)

    def decide_correction(self, **kwargs):
        self.calls.append(_Call("decide_correction", (), kwargs))
        return self.next_decisions.pop(0) if self.next_decisions else None


@dataclass
class FakeEvaluator:
    """IEvaluator fake — 對齊 evaluate(task, output) -> (reason, output, exit_code)。

    SD_05 W0 SD-M8：回傳 tuple 符合 IEvaluator 契約。
    """
    next_results: list[tuple] = field(default_factory=list)
    calls: list[_Call] = field(default_factory=list)

    def evaluate(self, task, output):
        self.calls.append(_Call("evaluate", (task, output), {}))
        if self.next_results:
            return self.next_results.pop(0)
        return (None, "", 0)  # 預設成功


@dataclass
class FakeExecutor:
    """IExecutor fake — 對齊 execute(prompt, *, maintain_context, timeout, label) -> ExecutionOutput。

    SD_05 W0 SD-M8：回傳 ExecutionOutput dataclass 而非裸字串。
    """
    default_text: str = "[DONE]\n"
    default_exit_code: int = 0
    default_completed: bool = True
    next_outputs: list = field(default_factory=list)
    calls: list[_Call] = field(default_factory=list)

    def execute(self, prompt: str, *, maintain_context: bool = True,
                timeout: int = 600, label: str = "", on_event=None):
        from autoclaude.core.ports.executor import ExecutionOutput
        self.calls.append(_Call(
            "execute", (prompt,),
            {"maintain_context": maintain_context, "timeout": timeout, "label": label},
        ))
        if self.next_outputs:
            return self.next_outputs.pop(0)
        return ExecutionOutput(
            text=self.default_text,
            exit_code=self.default_exit_code,
            completed=self.default_completed,
        )


@dataclass
class FakeMemoryStore:
    """IMemoryStore fake — 對齊 query/query_semantic/query_strategy_priority/
    record_success/record_escalation/stats_by_error_class 6 方法。

    SD_05 W0 SD-M8：補齊原本缺失的 query_semantic / record_success /
    record_escalation / stats_by_error_class。
    """
    query_results: dict = field(default_factory=dict)
    semantic_results: list = field(default_factory=list)
    strategy_priority: list[str] = field(default_factory=list)
    successes: list = field(default_factory=list)
    escalations: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    calls: list[_Call] = field(default_factory=list)

    def query(self, error_signature: str):
        self.calls.append(_Call("query", (error_signature,), {}))
        return self.query_results.get(error_signature)

    def query_semantic(self, embedding, top_k=5, threshold=0.8):
        self.calls.append(_Call(
            "query_semantic", (embedding,),
            {"top_k": top_k, "threshold": threshold},
        ))
        return list(self.semantic_results)

    def query_strategy_priority(self, error_class: str):
        self.calls.append(_Call("query_strategy_priority", (error_class,), {}))
        return list(self.strategy_priority)

    def record_success(self, error_signature, strategy, step_id,
                       error_class="unknown", embedding=None):
        self.calls.append(_Call(
            "record_success", (error_signature, strategy, step_id),
            {"error_class": error_class, "embedding": embedding},
        ))
        self.successes.append((error_signature, strategy, step_id, error_class))

    def record_escalation(self, error_signature, tried_strategies, step_id):
        self.calls.append(_Call(
            "record_escalation", (error_signature, tried_strategies, step_id), {},
        ))
        self.escalations.append((error_signature, tried_strategies, step_id))

    def stats_by_error_class(self):
        self.calls.append(_Call("stats_by_error_class", (), {}))
        return dict(self.stats)


@dataclass
class FakePorts:
    """v2 — 4 個 port 一次性 fake，供 Plugin 建構式注入。

    使用方式：
        ports = FakePorts()
        plugin = MyPlugin(brain=ports.brain, evaluator=ports.evaluator)
    """
    brain: FakeBrain = field(default_factory=FakeBrain)
    evaluator: FakeEvaluator = field(default_factory=FakeEvaluator)
    executor: FakeExecutor = field(default_factory=FakeExecutor)
    memory_store: FakeMemoryStore = field(default_factory=FakeMemoryStore)


# ─────────────────────────────────────────────────────────────
# 3. FakeEventBus — 繼承 EventBus，增加測試輔助
# ─────────────────────────────────────────────────────────────
class FakeEventBus(EventBus):
    """測試用 EventBus — 額外記錄每次 emit 的 (phase, trace_id, result)。"""

    def __init__(self, policy=None):
        super().__init__(policy=policy)
        self.emit_history: list[tuple[KernelPhase, str, Any]] = []

    def emit(self, ctx: HookContext):
        result = super().emit(ctx)
        trace_id = ctx.payload.get("_trace_id", "")
        self.emit_history.append((ctx.phase, trace_id, result))
        return result

    def emitted_phases(self) -> list[KernelPhase]:
        return [phase for phase, _, _ in self.emit_history]

    def last_result(self):
        return self.emit_history[-1][2] if self.emit_history else None


# ─────────────────────────────────────────────────────────────
# 4. KernelResult fixture（給 AutoResumeService / 收尾 wave 使用）
# ─────────────────────────────────────────────────────────────
def sample_kernel_result(
    *, success: bool = True, completed_steps: int = 3,
    total_steps: int = 3, halted: bool = False,
    scheduled_resume_at: Optional[str] = None,
) -> KernelResult:
    return KernelResult(
        success=success,
        completed_steps=completed_steps,
        total_steps=total_steps,
        reason="" if success else "failure",
        halted=halted,
        scheduled_resume_at=scheduled_resume_at,
    )
