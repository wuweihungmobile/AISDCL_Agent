"""DEF-101-051：checkpoint builder 三層 goal_task_id 接線直測。

驗證 `build_checkpoint_from_ctx`（hop 2）確實把當前 task 的 goal_task_id 帶進
PlaybookCheckpoint——這是「三層接線」的 plugin 層證據（repository 層由
tests/contract/test_pg_state_repository_contract.py 覆蓋，flatten 層由
tests/tools/test_three_tier_to_playbook.py 覆蓋）。
"""
from __future__ import annotations

from pathlib import Path

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.checkpoint._builder import build_checkpoint_from_ctx
from autoclaude.plugins.checkpoint._interrupt import save_interrupt_checkpoint_impl
from autoclaude.utils.checkpoint_manager import CheckpointManager


class _StubPlugin:
    """最小 plugin：_bus=None → builder 跳過 counter merge，直接組裝 checkpoint。"""
    _bus = None


def _ctx(task: PlaybookTask, payload: dict) -> HookContext:
    pb = Playbook(
        version="1.0", project="P", global_invariants=GlobalInvariants(), tasks=[task],
    )
    return HookContext(
        phase=KernelPhase.ON_TOKEN_USAGE, playbook=pb, task=task, step_idx=0, attempt=0,
        payload=payload,
    )


def test_builder_threads_task_goal_task_id() -> None:
    """task.goal_task_id 有值 → checkpoint.goal_task_id 帶入同值。"""
    task = PlaybookTask(step_id="T01", name="n", prompt="p", goal_task_id="GT-abc")
    payload = {"playbook_path": "x.yaml"}
    cp = build_checkpoint_from_ctx(_StubPlugin(), _ctx(task, payload), payload)
    assert cp is not None
    assert cp.goal_task_id == "GT-abc", "builder 應把 task.goal_task_id 帶進 checkpoint"


def test_builder_payload_goal_overrides_task() -> None:
    """payload['goal_task_id'] 優先於 task.goal_task_id（or 分支優先序）。"""
    task = PlaybookTask(step_id="T01", name="n", prompt="p", goal_task_id="GT-task")
    payload = {"playbook_path": "x.yaml", "goal_task_id": "GT-payload"}
    cp = build_checkpoint_from_ctx(_StubPlugin(), _ctx(task, payload), payload)
    assert cp.goal_task_id == "GT-payload"


def test_builder_none_when_no_goal() -> None:
    """standalone task（無 goal_task_id）→ checkpoint.goal_task_id 為 None。"""
    task = PlaybookTask(step_id="T01", name="n", prompt="p")
    payload = {"playbook_path": "x.yaml"}
    cp = build_checkpoint_from_ctx(_StubPlugin(), _ctx(task, payload), payload)
    assert cp.goal_task_id is None


class _MgrPlugin:
    """最小 plugin：持一個真實 CheckpointManager 供命令式落地路徑 save。"""
    def __init__(self, mgr: CheckpointManager):
        self._mgr = mgr


def test_imperative_interrupt_path_threads_goal_task_id(tmp_path: Path) -> None:
    """DEF-101-051：命令式落地路徑（此處以 _interrupt 為代表）確實把 task.goal_task_id
    帶進持久化 checkpoint——證明生產 runner 路徑（非僅休眠的 _builder）的接線。"""
    mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
    pb_path = str(tmp_path / "demo.yaml")
    task = PlaybookTask(step_id="T01", name="n", prompt="p", goal_task_id="GT-imp")
    pb = Playbook(version="1.0", project="P", global_invariants=GlobalInvariants(), tasks=[task])
    save_interrupt_checkpoint_impl(
        _MgrPlugin(mgr), pb, pb_path, task, step_idx=0, step_log=[], total=1,
    )
    loaded = mgr.load(pb_path)
    assert loaded is not None
    assert loaded.goal_task_id == "GT-imp", "命令式 interrupt 落地路徑應帶 task.goal_task_id"
