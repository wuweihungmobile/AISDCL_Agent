"""`GET /sdd/fsm/{key}` 的投影新增同級鍵 `retry_gates`（AT-960-13-9；D-59(4)、API-RP-13）。

`retry_gates` 是各登記閘（SCG_VALIDATION、PR_REVIEW、RTM_VERIFY）的 `{current_count, entries}`；
既有的 `retry_history`（`{count, last}`）與其餘既有鍵逐值不變；壞形狀一律 200、記 0，不使投影失敗。
夾具沿既有 `tests/test_sdd_fsm.py` 的真實檔形狀（`_write`）。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from app.fsm_phase import phase_of
from app.research import fsm_ops
from app.settings import Settings
from tests.fake_sdd import make_fake_sdd
from tests.test_research_fsm_ops import fail_to_escalation, make_ctx, real_sdd_root, to_review
from tests.test_sdd_fsm import _D16_KEYS, _FSM_REL, _OLD_KEYS, _V15_KEYS, _write

KEY = "research-demo"
GATES = ("SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY")
ZERO = {"current_count": 0, "entries": 0}
ROWS = [
    {"attempt": 1, "date": "2026-11-01T01:00:00+00:00", "failure_reason": "r1", "scg_gate": None},
    {"attempt": 2, "date": "2026-11-01T03:00:00+00:00", "failure_reason": "r2", "scg_gate": None},
    {"attempt": 3, "date": "2026-11-01T02:00:00+00:00", "failure_reason": "r3", "scg_gate": None},
]
LATEST_ROW = {"gate": "SCG_VALIDATION", **ROWS[1]}     # date 最晚者（不是檔案順序的最後一筆）


def _history(current: Any = 0, rows: Any = None, **extra: Any) -> dict[str, Any]:
    return {"current_count": current, "max_limit": 3, "history": [] if rows is None else rows,
            **extra}


def _retry_history(**gates: Any) -> dict[str, Any]:
    base = {"SCG_VALIDATION": _history(), "PR_REVIEW": _history(), "RTM_VERIFY": _history()}
    return {**base, **gates}


@pytest.fixture
def sdd_tree(tmp_path: Path) -> Path:
    root = tmp_path / "AISDLC_SDD_v9.99"
    (root / _FSM_REL).mkdir(parents=True)
    return root


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_sdd(tmp_path / "sdd")


@pytest.fixture
def live(make_bridge: Callable[..., Any], settings: Settings, sdd_tree: Path) -> Any:
    return make_bridge(replace(settings, sdd_root=sdd_tree))


def _get(live: Any, key: str = KEY, **params: str) -> dict[str, Any]:
    resp = live.client.get(f"/sdd/fsm/{key}", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


# 甲：真實檔形狀；乙～己：壞形狀。每格＝(檔案的 retry_history, 預期 retry_gates, 預期 retry_history)
CASES: dict[str, tuple[Any, dict[str, Any], dict[str, Any]]] = {
    "A: SCG 2 of 3 with three rows": (
        _retry_history(SCG_VALIDATION=_history(2, ROWS)),
        {"SCG_VALIDATION": {"current_count": 2, "entries": 3}, "PR_REVIEW": ZERO,
         "RTM_VERIFY": ZERO},
        {"count": 3, "last": LATEST_ROW}),
    "A': an unregistered gate is counted by retry_history only": (
        _retry_history(SCG_VALIDATION=_history(2, ROWS), X_GATE=_history(1, [
            {"attempt": 1, "date": "2026-11-01T05:00:00+00:00", "failure_reason": "x"},
            {"attempt": 2, "date": "2026-11-01T04:00:00+00:00", "failure_reason": "y"}])),
        {"SCG_VALIDATION": {"current_count": 2, "entries": 3}, "PR_REVIEW": ZERO,
         "RTM_VERIFY": ZERO},
        {"count": 5, "last": {"gate": "X_GATE", "attempt": 1, "date": "2026-11-01T05:00:00+00:00",
                              "failure_reason": "x"}}),
    "B: retry_history is null": (None, {g: ZERO for g in GATES}, {"count": 0, "last": None}),
    "C: retry_history is an empty list": ([], {g: ZERO for g in GATES},
                                          {"count": 0, "last": None}),
    "C': retry_history is a plain list": ([{"x": 1}, {"x": 2}], {g: ZERO for g in GATES},
                                          {"count": 2, "last": {"x": 2}}),
    "D: a gate is missing and another history is not a list": (
        {"SCG_VALIDATION": _history(1, ROWS[:1]), "PR_REVIEW": _history(2, "x")},
        {"SCG_VALIDATION": {"current_count": 1, "entries": 1},
         "PR_REVIEW": {"current_count": 2, "entries": 0}, "RTM_VERIFY": ZERO},
        {"count": 1, "last": {"gate": "SCG_VALIDATION", **ROWS[0]}}),
    "E: current_count is a string": (
        _retry_history(SCG_VALIDATION=_history("2", ROWS[:2])),
        {"SCG_VALIDATION": {"current_count": 0, "entries": 2}, "PR_REVIEW": ZERO,
         "RTM_VERIFY": ZERO},
        {"count": 2, "last": {"gate": "SCG_VALIDATION", **ROWS[1]}}),
    "F: a gate value is a string": (
        {"SCG_VALIDATION": "nope"}, {g: ZERO for g in GATES}, {"count": 0, "last": None}),
    "G: negative, bool and float counts": (
        _retry_history(SCG_VALIDATION=_history(-1), PR_REVIEW=_history(True),
                       RTM_VERIFY=_history(1.5)),
        {g: ZERO for g in GATES}, {"count": 0, "last": None}),
}


@pytest.mark.parametrize(("stored", "gates", "history"), list(CASES.values()), ids=list(CASES))
def test_AT_960_13_9_the_projection_adds_retry_gates_and_leaves_retry_history_as_it_was(
        stored: Any, gates: dict[str, Any], history: dict[str, Any], live: Any,
        sdd_tree: Path) -> None:
    _write(sdd_tree / _FSM_REL, KEY, retry_history=stored, state="SCG_VALIDATION")
    body = _get(live)
    assert set(body) == _OLD_KEYS | _D16_KEYS | _V15_KEYS | {"retry_gates"}, \
        "回應鍵集合恰為既有鍵加 retry_gates"
    assert list(body["retry_gates"]) == list(GATES), "只列三個登記閘（登記外的閘不出現）"
    assert body["retry_gates"] == gates
    assert body["retry_history"] == history, "既有的 retry_history 逐值不變"
    assert body["current_state"] == "SCG_VALIDATION"
    assert body["phase"] == phase_of("SCG_VALIDATION")


def test_AT_960_13_9_every_bad_shape_still_answers_200_with_the_existing_keys_intact(
        live: Any, sdd_tree: Path) -> None:
    for name, (stored, _gates, _history_view) in CASES.items():
        key = "bad-" + name.split(":")[0].lower().replace("'", "p")
        _write(sdd_tree / _FSM_REL, key, retry_history=stored, state="IMPLEMENTATION")
        body = _get(live, key)
        assert body["current_state"] == "IMPLEMENTATION", name
        assert body["frozen_stages"] == [] and body["fsm_project"] == key, name


def test_AT_960_13_9_the_view_of_a_real_research_key_counts_three_fails(
        fake: Path, tmp_path: Path, make_bridge: Callable[..., Any], settings: Settings) -> None:
    """CLI 自己寫的狀態檔（假 CLI）：三次 FAIL 之後 SCG_VALIDATION 為 3 與 3，且帶 recovery。"""
    ws = tmp_path / "projects" / "research-ws"
    ctx = make_ctx(fake, ws / "build" / "reports" / "fsm", KEY)
    to_review(ctx, ws)
    fail_to_escalation(ctx)
    live = make_bridge(replace(settings, sdd_root=fake))
    body = _get(live, KEY, root=str(ws))
    assert body["retry_gates"] == {"SCG_VALIDATION": {"current_count": 3, "entries": 3},
                                   "PR_REVIEW": ZERO, "RTM_VERIFY": ZERO}
    assert body["retry_history"]["count"] == 3 and body["current_state"] == "ESCALATION"
    assert "recovery" in body and fsm_ops.snapshot(ctx)["state"] == "ESCALATION"


def test_AT_960_13_9_the_view_of_a_state_file_written_by_the_real_cli(
        tmp_path: Path, make_bridge: Callable[..., Any], settings: Settings) -> None:
    tree = real_sdd_root()
    ws = tmp_path / "projects" / "research-real"
    ctx = make_ctx(tree, ws / "build" / "reports" / "fsm", KEY)
    to_review(ctx, ws)
    fsm_ops.gate(ctx, gate="SCG_VALIDATION", result="FAIL", reason="first review failed")
    live = make_bridge(replace(settings, sdd_root=tree))
    body = _get(live, KEY, root=str(ws))
    assert body["retry_gates"] == {"SCG_VALIDATION": {"current_count": 1, "entries": 1},
                                   "PR_REVIEW": ZERO, "RTM_VERIFY": ZERO}
    assert body["retry_history"]["count"] == 1
    assert body["retry_history"]["last"]["gate"] == "SCG_VALIDATION"
