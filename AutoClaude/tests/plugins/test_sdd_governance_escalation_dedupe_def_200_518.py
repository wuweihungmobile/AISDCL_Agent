"""DEF-200-518：Kernel 開始發布 ON_ESCALATION 後，SddGovernancePlugin 對「同一次重試耗盡」
不得諮詢兩次（Kernel 先發 ON_FAILURE 再發 ON_ESCALATION，兩者都會進 _on_failure）。

驗證意圖（Rule 9）：諮詢是 advisory，但每次都會呼叫 Brain 並記一筆 sdd.escalation_consult 事件；
重複記帳會讓「一次升級」在稽核面看起來像兩次。收斂型升級（trigger=request_escalation）本來就
沒有 ON_FAILURE，必須仍然諮詢——兩個方向都要鎖。
"""
from __future__ import annotations

from autoclaude.core.hookspec import KernelPhase
from tests.plugins import test_sdd_governance as sg


def _saturated(tmp_path):
    brain = sg.TestEscalationConsult._SpyBrain()
    plugin, pb, _ = sg._activated_plugin(tmp_path, brain=brain, obs=sg._SpyObs())
    sg.TestEscalationConsult()._saturate(plugin, pb)
    return plugin, pb, brain


def test_exhaustion_is_consulted_once_not_twice(tmp_path):
    plugin, pb, brain = _saturated(tmp_path)
    task = pb.tasks[0]
    plugin.on_event(sg._ctx(KernelPhase.ON_FAILURE, pb, task=task))
    plugin.on_event(sg._ctx(KernelPhase.ON_ESCALATION, pb, task=task,
                            payload={"trigger": "max_retries_exhausted"}))
    assert len(brain.calls) == 1


def test_convergence_escalation_is_still_consulted(tmp_path):
    plugin, pb, brain = _saturated(tmp_path)
    plugin.on_event(sg._ctx(KernelPhase.ON_ESCALATION, pb, task=pb.tasks[0],
                            payload={"trigger": "request_escalation"}))
    assert len(brain.calls) == 1
