"""Kernel / Service factory — 供遷移後測試直接組裝 AutoResumeService + Kernel。

取代舊模式：
  runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=True)

新模式：
  service, plugins = make_service(outputs=["[DONE]"])
  result = service.run("playbook.yaml")

make_kernel() / make_service() 均回傳 (obj, plugins_dict)，
plugins_dict 供測試斷言 plugin 內部 state，例如：
  assert plugins["goto_counter"].goto_counter == {}
"""
from __future__ import annotations

from typing import Optional

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.core.wiring import wire_plugins_with_registry
from autoclaude.utils.config import AppConfig

from .fake_ports import FakeBrain, FakeEvaluator, FakeExecutor


def make_kernel(
    outputs: Optional[list[str]] = None,
    eval_pass: bool = True,
    eval_results: Optional[list[bool]] = None,
    config: Optional[AppConfig] = None,
) -> tuple[PlaybookKernel, dict]:
    """建立帶 Fake ports 的 PlaybookKernel。

    Args:
        outputs:      FakeExecutor 輸出列表；耗盡後回退為 "[DONE]"
        eval_pass:    FakeEvaluator 預設評估結果（True = 通過）
        eval_results: FakeEvaluator 逐步評估結果列表（優先於 eval_pass）
        config:       AppConfig；None 時使用預設值

    Returns:
        (kernel, plugins_dict)
        plugins_dict keys: pre_run_validator, cross_step_validator, token_guard,
          global_goal_anchor, notification, knowledge_base, goal_synthesis,
          convergence, evolution, goto_counter, checkpoint, mutation_service
    """
    cfg = config or AppConfig()
    executor = FakeExecutor(outputs=outputs or ["[DONE]"])
    evaluator = FakeEvaluator(always_pass=eval_pass, results=eval_results)
    brain = FakeBrain()

    bus = EventBus()
    plugins = wire_plugins_with_registry(bus, config=cfg)

    kernel = PlaybookKernel(
        executor=executor,
        evaluator=evaluator,
        bus=bus,
        brain=brain,
        mutation_service=plugins["mutation_service"],
    )
    return kernel, plugins


def make_service(
    outputs: Optional[list[str]] = None,
    eval_pass: bool = True,
    eval_results: Optional[list[bool]] = None,
    config: Optional[AppConfig] = None,
) -> tuple[AutoResumeService, dict]:
    """建立帶 Fake ports 的 AutoResumeService（含 Kernel）。

    Args:
        outputs:      同 make_kernel
        eval_pass:    同 make_kernel
        eval_results: 同 make_kernel
        config:       同 make_kernel

    Returns:
        (service, plugins_dict)
    """
    cfg = config or AppConfig()
    kernel, plugins = make_kernel(
        outputs=outputs,
        eval_pass=eval_pass,
        eval_results=eval_results,
        config=cfg,
    )
    service = AutoResumeService(kernel=kernel, config=cfg)
    return service, plugins
