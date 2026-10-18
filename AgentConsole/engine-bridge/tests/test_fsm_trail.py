"""DEF-AC-023：`restore_trail`（app/fsm_trail.py）的驗收測試，對應 TCS-FsmTrail-20261018。

五個 Unit AT 打純函式；兩個 Integration AT 經 `GET /sdd/fsm/{project}` 與共用的 `_state_view`。
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from app.fsm_trail import restore_trail
from app.routers.sdd import _state_view
from tests.fake_sdd import seed_state
from tests.sdd_run_support import FSM_REL

FAILED = {"source": "autoclaude_delegated_failed"}
EXIT = "autoclaude_delegated_exit"


def _loop(ts: str, trigger: Any = EXIT, **extra: Any) -> dict[str, Any]:
    return {"ts": ts, "from": "ESCALATION", "to": "ESCALATION", "reason": f"r-{ts}",
            "trigger": trigger, **extra}


def test_AT_001_1_1_restores_from_of_the_delegated_failure_entry() -> None:
    trace = [
        {"ts": "t1", "from": "IMPLEMENTATION", "to": "AUTOCLAUDE_DELEGATED",
         "reason": "console-run run=r1 start", "spec_refs": [], "agents_consulted": [],
         "trigger": "autoclaude_delegated_enter"},
        {"ts": "t2", "from": "ESCALATION", "to": "ESCALATION",
         "reason": "console-run run=r1 ENGINE-ESCALATION step=s1: x",
         "spec_refs": ["docs/a.md"], "agents_consulted": ["dev"], "trigger": EXIT},
    ]
    provenance = {"source": "autoclaude_delegated_failed", "reason": "r", "rule_id": "unknown",
                  "session_id": "unknown", "at": "2026-10-18T00:00:00+00:00"}
    snapshot = copy.deepcopy((trace, provenance))
    result = restore_trail(trace, provenance)
    assert isinstance(result, list) and result is not trace and len(result) == 2
    assert result[0] is trace[0] and "from_inferred" not in result[0]
    assert result[1] is not trace[1]
    assert result[1]["from"] == "AUTOCLAUDE_DELEGATED"
    assert result[1]["from_inferred"] is True
    assert result[1]["to"] == "ESCALATION"
    for key in ("ts", "reason", "spec_refs", "agents_consulted", "trigger"):
        assert result[1][key] == trace[1][key], key
    assert (trace, provenance) == snapshot
    assert trace[1]["from"] == "ESCALATION" and "from_inferred" not in trace[1]


def test_AT_001_2_1_only_matching_entries_are_rewritten() -> None:
    def row(ts: str, frm: str, to: str, trigger: Any = EXIT, *, has_trigger: bool = True
            ) -> dict[str, Any]:
        entry: dict[str, Any] = {"ts": ts, "from": frm, "to": to, "reason": f"r-{ts}"}
        if has_trigger:
            entry["trigger"] = trigger
        return entry

    trace = [
        row("0", "SPEC_DRAFTING", "SCG_VALIDATION"),
        row("1", "IMPLEMENTATION", "IMPLEMENTATION"),
        row("2", "SPEC_AUDIT", "ESCALATION"),
        row("3", "ESCALATION", "ESCALATION"),
        row("4", "ESCALATION", "IMPLEMENTATION"),
        row("5", "escalation", "escalation"),
        row("6", "ESCALATION", "ESCALATION", "retry_exhausted"),
        row("7", "ESCALATION", "ESCALATION", has_trigger=False),
        row("8", "ESCALATION", "ESCALATION", "AUTOCLAUDE_DELEGATED_EXIT"),
        row("9", "ESCALATION", "ESCALATION", None),
    ]
    result = restore_trail(trace, FAILED)
    assert len(result) == 10
    assert result[3] is not trace[3]
    assert result[3]["from"] == "AUTOCLAUDE_DELEGATED" and result[3]["from_inferred"] is True
    for i in (0, 1, 2, 4, 5, 6, 7, 8, 9):
        assert result[i] is trace[i], i
        assert "from_inferred" not in result[i], i

    trace2 = [_loop("a"), row("b", "ESCALATION", "IMPLEMENTATION"), _loop("c")]
    result2 = restore_trail(trace2, FAILED)
    assert len(result2) == 3
    assert result2[0]["from_inferred"] is True and result2[2]["from_inferred"] is True
    assert result2[1] is trace2[1]


def test_AT_001_3_1_provenance_gate_blocks_every_rewrite() -> None:
    trace = [{"ts": "t1", "from": "ESCALATION", "to": "ESCALATION", "reason": "x",
              "trigger": EXIT}]
    snapshot = copy.deepcopy(trace)
    bad_values: list[Any] = [
        None, {}, {"source": "other"}, {"source": "AUTOCLAUDE_DELEGATED_FAILED"},
        {"source": None}, "autoclaude_delegated_failed", ["autoclaude_delegated_failed"], 123]
    for provenance in bad_values:
        result = restore_trail(trace, provenance)
        assert isinstance(result, list) and result is not trace and len(result) == 1, provenance
        assert result[0] is trace[0], provenance
        assert result[0]["from"] == "ESCALATION" and "from_inferred" not in result[0], provenance
    assert trace == snapshot


def test_AT_001_4_1_non_list_trace_is_returned_as_is() -> None:
    as_dict = {"from": "ESCALATION", "to": "ESCALATION"}
    as_tuple = ({"from": "ESCALATION", "to": "ESCALATION"},)
    values: list[Any] = [None, 42, "abc", as_dict, as_tuple, set()]
    for value in values:
        assert restore_trail(value, FAILED) is value, value
    assert as_dict == {"from": "ESCALATION", "to": "ESCALATION"}
    assert as_tuple == ({"from": "ESCALATION", "to": "ESCALATION"},)


def test_AT_001_4_2_malformed_elements_pass_through() -> None:
    trace: list[Any] = [
        None, "x", 7, ["ESCALATION"], {},
        {"from": "ESCALATION", "trigger": EXIT},
        {"to": "ESCALATION", "trigger": EXIT},
        {"from": None, "to": None, "trigger": EXIT},
        {"from": ["ESCALATION"], "to": ["ESCALATION"], "trigger": EXIT},
        {"from": 1, "to": 1, "trigger": EXIT},
        {"ts": "t", "from": "ESCALATION", "to": "ESCALATION", "reason": "ok", "trigger": EXIT},
    ]
    snapshot = copy.deepcopy(trace)
    result = restore_trail(trace, FAILED)
    assert len(result) == 11
    for i in range(10):
        assert result[i] is trace[i], i
    assert result[10] is not trace[10]
    assert result[10]["from"] == "AUTOCLAUDE_DELEGATED" and result[10]["from_inferred"] is True
    for key in ("ts", "to", "reason", "trigger"):
        assert result[10][key] == trace[10][key], key
    assert trace == snapshot


def _seed_trace(n: int = 7) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"ts": f"t{i}", "from": f"S{i}", "to": f"S{i + 1}", "reason": f"reason-{i}",
         "spec_refs": [], "agents_consulted": [], "trigger": "step"}
        for i in range(1, n)]
    rows.append(_loop(f"t{n}", spec_refs=["docs/a.md"], agents_consulted=["dev"]))
    return rows


def test_AT_001_5_1_view_restores_the_delegated_failure_and_leaves_the_file_untouched(
        sdd_live, sdd_proj: Path, tmp_path: Path) -> None:
    seed = _seed_trace()
    provenance = {"session_id": "unknown", "at": "2026-10-18T00:00:00+00:00", "reason": "r",
                  "rule_id": "unknown", "source": "autoclaude_delegated_failed"}
    path = seed_state(sdd_proj / FSM_REL, "alpha", "ESCALATION",
                      decision_trace=copy.deepcopy(seed),
                      escalation_provenance=copy.deepcopy(provenance))
    before = path.read_bytes()
    resp = sdd_live.client.get("/sdd/fsm/alpha", params={"root": str(sdd_proj)})
    after = path.read_bytes()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    trail = body["decision_trace"]
    assert [d["ts"] for d in trail] == ["t3", "t4", "t5", "t6", "t7"]
    for got, want in zip(trail[:4], seed[2:6], strict=True):
        assert got == want and "from_inferred" not in got
    last = trail[-1]
    assert last["from"] == "AUTOCLAUDE_DELEGATED" and last["from_inferred"] is True
    assert last["to"] == "ESCALATION" and last["trigger"] == EXIT
    expected_last = {**seed[-1], "from": "AUTOCLAUDE_DELEGATED", "from_inferred": True}
    assert last == expected_last
    assert body["current_state"] == "ESCALATION"
    assert body["escalation_provenance"] == provenance
    assert body["fsm_project"] == "alpha"
    assert body["phase"]["name"] == "BLOCKED"
    assert after == before

    state = {"project": "alpha", "current_state": "ESCALATION",
             "decision_trace": copy.deepcopy(seed),
             "escalation_provenance": copy.deepcopy(provenance)}
    direct = _state_view(state, source="alpha.yaml", key="alpha", sdd_root=tmp_path,
                         fsm_dir=tmp_path)
    assert direct["decision_trace"] == trail
    assert direct["decision_trace"][-1]["from"] == "AUTOCLAUDE_DELEGATED"
    assert direct["decision_trace"][-1]["from_inferred"] is True


def test_AT_001_5_2_non_delegated_files_are_not_projected(sdd_live, sdd_proj: Path) -> None:
    def plain(n: int) -> list[dict[str, Any]]:
        return [{"ts": f"t{i}", "from": f"S{i}", "to": f"S{i + 1}", "reason": f"r{i}",
                 "spec_refs": [], "agents_consulted": [], "trigger": "step"}
                for i in range(1, n + 1)]

    fsm_dir = sdd_proj / FSM_REL
    alpha = plain(5) + [_loop("t6")]
    beta = plain(5) + [_loop("t6")]
    delta = plain(5) + [_loop("t6", trigger="retry_exhausted")]
    gamma = plain(6)
    seed_state(fsm_dir, "alpha", "ESCALATION", decision_trace=copy.deepcopy(alpha),
               escalation_provenance={"source": "other_source"})
    seed_state(fsm_dir, "beta", "ESCALATION", decision_trace=copy.deepcopy(beta))
    seed_state(fsm_dir, "delta", "ESCALATION", decision_trace=copy.deepcopy(delta),
               escalation_provenance={"source": "autoclaude_delegated_failed"})
    seed_state(fsm_dir, "gamma", "IMPLEMENTATION", decision_trace=copy.deepcopy(gamma))
    seeds = {"alpha": alpha, "beta": beta, "delta": delta, "gamma": gamma}
    for name, seed in seeds.items():
        resp = sdd_live.client.get(f"/sdd/fsm/{name}", params={"root": str(sdd_proj)})
        assert resp.status_code == 200, (name, resp.text)
        trail = resp.json()["decision_trace"]
        assert trail == seed[-5:], name
        assert all("from_inferred" not in d for d in trail), name
        if name != "gamma":
            assert trail[-1]["from"] == "ESCALATION", name
