"""目標拆解：FakeBrain（IBrain，supports_decomposition=True）＋三道有界閘＋🔴 人工 signoff 硬閘。"""
from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from autoclaude.core.ports.brain import BrainCapabilities, RetryPolicy
from autoclaude.models.decision import DecompositionDecision, DecompositionStep

from app.models import PlaybookIn
from tests.conftest import TERMINAL


def step(i: int, deps: list[str] | None = None, prompt: str | None = None) -> DecompositionStep:
    return DecompositionStep(step_id=f"S{i:02d}", name=f"步驟 {i}", depends_on=deps or [],
                             prompt=f"請完成第 {i} 步" if prompt is None else prompt)


class FakeBrain:
    """最小的 IBrain 實作：只有拆解用得到的兩個方法有內容。"""

    def __init__(self, steps: list[DecompositionStep] | None, *, supports: bool = True):
        self._steps = steps
        self._supports = supports
        self.calls: list[tuple[str, str]] = []

    def capabilities(self) -> BrainCapabilities:
        return BrainCapabilities(max_context_tokens=1000, supports_streaming=False,
                                 retry_policy=RetryPolicy(), model_id="fake", dimension=8,
                                 supports_decomposition=self._supports)

    def decide_decomposition(self, *, goal: str, context: str = "") -> DecompositionDecision | None:
        self.calls.append((goal, context))
        if self._steps is None:
            return None
        return DecompositionDecision(steps=self._steps, reasoning="fake reasoning")


@pytest.fixture
def decomposer(make_bridge):
    def build(brain: FakeBrain):
        return make_bridge(brain_factory=lambda _cfg: brain)
    return build


def _decompose(live, **overrides) -> Any:
    body = {"goal": "做一個 todo CLI", "context": "Python 3.11", "project": "todo-cli"}
    body.update(overrides)
    return live.client.post("/autoclaude/decompose", json=body)


def test_a_three_step_dag_is_accepted_as_an_unsigned_draft(decomposer) -> None:
    brain = FakeBrain([step(1), step(2, ["S01"]), step(3, ["S02"])])
    live = decomposer(brain)
    resp = _decompose(live)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["signed_off"] is False
    assert str(uuid.UUID(body["draft_id"])) == body["draft_id"], "draft_id 是正規 UUID"
    assert body["goal_hash"] and body["reasoning"] == "fake reasoning"
    assert [t["step_id"] for t in body["playbook"]["tasks"]] == ["S01", "S02", "S03"]
    assert body["playbook"]["project"] == "todo-cli"
    assert brain.calls == [("做一個 todo CLI", "Python 3.11")]
    PlaybookIn.model_validate(body["playbook"])        # 拆解結果必須能原樣餵回 POST /runs


def test_topological_order_is_enforced_regardless_of_the_brains_order(decomposer) -> None:
    live = decomposer(FakeBrain([step(3, ["S02"]), step(1), step(2, ["S01"])]))
    tasks = _decompose(live).json()["playbook"]["tasks"]
    assert [t["step_id"] for t in tasks] == ["S01", "S02", "S03"]


@pytest.mark.parametrize(("steps", "gate"), [
    ([step(i) for i in range(1, 26)], "max_steps"),
    ([step(1, ["S02"]), step(2, ["S01"])], "cycle"),
    ([step(1, ["S01"])], "cycle"),
    ([step(1, ["S99"])], "cycle"),                       # 相依不存在：DAG 結構閘
    ([step(1), step(1)], "cycle"),                       # step_id 重複：DAG 結構閘
    ([step(1), step(2, prompt="   ")], "empty_prompt"),
    ([], "brain_failed"),
])
def test_bounded_gates_reject_with_a_structured_gate(decomposer, steps, gate) -> None:
    resp = _decompose(decomposer(FakeBrain(steps)))
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == 422
    assert body["gate"] == gate
    assert body["detail"], "必須帶人看得懂的原因，不靜默截斷"


def test_max_steps_can_be_lowered_but_never_raised(decomposer) -> None:
    six = [step(i) for i in range(1, 7)]
    lowered = _decompose(decomposer(FakeBrain(six)), max_steps=5)
    assert (lowered.status_code, lowered.json()["gate"]) == (422, "max_steps")
    raised = _decompose(decomposer(FakeBrain([step(i) for i in range(1, 26)])), max_steps=100)
    assert (raised.status_code, raised.json()["gate"]) == (422, "max_steps")
    exact = _decompose(decomposer(FakeBrain([step(i) for i in range(1, 25)])), max_steps=100)
    assert exact.status_code == 200, "剛好 24 步是允許的上限"


def test_empty_goal_and_unsupported_or_failing_brains(decomposer) -> None:
    assert _decompose(decomposer(FakeBrain([step(1)])), goal="  ").json()["gate"] == "empty_prompt"
    unsupported = _decompose(decomposer(FakeBrain([step(1)], supports=False)))
    assert (unsupported.status_code, unsupported.json()["gate"]) == (422, "brain_unsupported")
    failed = _decompose(decomposer(FakeBrain(None)))
    assert (failed.status_code, failed.json()["gate"]) == (422, "brain_failed")


def test_the_real_brain_without_an_api_key_is_unsupported_not_a_crash(make_bridge) -> None:
    live = make_bridge()                                  # 預設 brain_factory＋沒有 MINIMAX_API_KEY
    resp = _decompose(live)
    assert resp.status_code == 422
    assert resp.json()["gate"] == "brain_unsupported"
    assert "api key" in resp.json()["detail"].lower() or "金鑰" in resp.json()["detail"]


def test_approve_requires_a_named_approver_and_records_who_and_when(decomposer) -> None:
    live = decomposer(FakeBrain([step(1), step(2, ["S01"])]))
    draft = _decompose(live).json()
    url = f"/autoclaude/decompose/{draft['draft_id']}:approve"

    for blank in ("", "   "):
        refused = live.client.post(url, json={"approver": blank})
        assert refused.status_code == 400, blank
        assert refused.json()["reason"] == "approver_required"
    assert live.client.post(url, json={}).status_code == 400

    signed = live.client.post(url, json={"approver": "掌舵者 koalawu"})
    assert signed.status_code == 200, signed.text
    out = signed.json()
    assert out["signed_off"] is True
    assert out["approver"] == "掌舵者 koalawu"
    assert out["approved_at"].endswith("+00:00")
    assert out["playbook"] == draft["playbook"]

    again = live.client.post(url, json={"approver": "掌舵者 koalawu"})
    assert again.status_code == 200 and again.json() == out, "同一人重送：冪等"
    other = live.client.post(url, json={"approver": "someone else"})
    assert other.status_code == 409
    assert other.json()["approver"] == "掌舵者 koalawu", "簽核紀錄不得被別人覆寫"


def test_approving_an_unknown_draft_is_404(decomposer) -> None:
    live = decomposer(FakeBrain([step(1)]))
    for bad in ("0" * 32, "not-a-draft", "A" * 40, "x.json"):
        resp = live.client.post(f"/autoclaude/decompose/{bad}:approve", json={"approver": "x"})
        assert resp.status_code == 404, bad
        assert resp.json()["reason"] == "draft_not_found"
    # 路徑穿越字樣：根本不會被路由到 handler（HTTP 層就正規化／拒絕），同樣是 404、不得讀到檔案。
    for sneaky in ("../../etc/passwd", "..%2F..%2Fetc%2Fpasswd"):
        resp = live.client.post(f"/autoclaude/decompose/{sneaky}:approve", json={"approver": "x"})
        assert resp.status_code == 404, sneaky


def test_a_draft_survives_a_bridge_restart(make_bridge) -> None:
    first = make_bridge(brain_factory=lambda _c: FakeBrain([step(1)]))
    draft = _decompose(first).json()
    first.stop()
    second = make_bridge()
    resp = second.client.post(f"/autoclaude/decompose/{draft['draft_id']}:approve",
                              json={"approver": "after-restart"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["playbook"] == draft["playbook"]


def test_decisions_are_audited(decomposer, settings) -> None:
    live = decomposer(FakeBrain([step(1)]))
    draft = _decompose(live).json()
    live.client.post(f"/autoclaude/decompose/{draft['draft_id']}:approve", json={"approver": "qa"})
    _decompose(decomposer(FakeBrain([step(i) for i in range(1, 26)])))
    events = [json.loads(x)["event"] for x in
              (settings.engine_workspace / "_audit.jsonl").read_text("utf-8").splitlines()]
    assert {"decomposition_accepted", "decomposition_signoff",
            "decomposition_rejected"} <= set(events)


def test_an_evil_brain_url_is_refused_before_any_call(decomposer) -> None:
    brain = FakeBrain([step(1)])
    live = decomposer(brain)
    resp = _decompose(live, config_overrides={"minimax": {"base_url": "http://evil.example/v1"}})
    assert resp.status_code == 422
    body = resp.json()
    assert body["violations"][0]["rule"] == "outbound_not_allowed"
    assert body["violations"][0]["host"] == "evil.example"
    assert brain.calls == [], "被拒絕的請求不得觸發任何 Brain 呼叫"
    ok = _decompose(live, config_overrides={
        "minimax": {"base_url": "http://localhost:9100/v1/chat/completions"}})
    assert ok.status_code == 200, ok.text


def test_decompose_approve_then_run_end_to_end(decomposer, run_body) -> None:
    live = decomposer(FakeBrain([step(1), step(2, ["S01"])]))
    draft = _decompose(live).json()
    signed = live.client.post(f"/autoclaude/decompose/{draft['draft_id']}:approve",
                              json={"approver": "e2e"}).json()
    body = run_body(playbook=signed["playbook"], delay="0.2")
    created = live.post_run(body)
    assert created.status_code == 201, created.text
    final = live.wait_status(body["run_id"], TERMINAL)
    assert final["status"] == "COMPLETED"
    assert final["completed_steps"] == 2
