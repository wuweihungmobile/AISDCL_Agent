"""SD_06 W5-T5-2：ExecutionContext round-trip property-based test。

對應規格：
  - SD_Improving_06.md v1.2 §6.5 AC5-1（Hypothesis ≥ 50 example）
  - SD06_Execution_Guide.md W5 T5-2
  - autoclaude/execution/steps_orchestrator/_context.py ExecutionContext

驗證不變式：
  1. ctx.to_dict() → dict（純資料、JSON 可序列化）
  2. ExecutionContext.from_dict(ctx.to_dict()).to_dict() == ctx.to_dict()
  3. transient 欄位（step_trackers / resume_checkpoint）不出現在 to_dict 結果
  4. 巢狀資料（list / set / dict 內含 datetime / UUID / Enum）均正規化
  5. 未知欄位被忽略（前向相容）
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from autoclaude.execution.steps_orchestrator._context import ExecutionContext
from autoclaude.infra.services.state_normalize import (
    diff_normalized,
    normalize_dict,
    normalize_value,
)


# ──────────────────────────────────────────────
# Hypothesis strategies
# ──────────────────────────────────────────────
@st.composite
def execution_contexts(draw):
    step_idx = draw(st.integers(min_value=0, max_value=10_000))
    prev_step_idx = draw(st.integers(min_value=-1, max_value=step_idx))
    completed = draw(
        st.sets(
            st.text(min_size=1, max_size=12, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"),
            max_size=12,
        )
    )
    skip = draw(
        st.sets(
            st.text(min_size=1, max_size=12, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"),
            max_size=8,
        )
    )
    step_log = draw(st.lists(st.text(max_size=40), max_size=6))
    mutation_log = draw(st.lists(st.text(max_size=40), max_size=6))
    history = draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "pct": st.floats(min_value=0.0, max_value=100.0,
                                     allow_nan=False, allow_infinity=False),
                    "step": st.integers(min_value=0, max_value=1_000),
                }
            ),
            max_size=8,
        )
    )
    return ExecutionContext(
        step_idx=step_idx,
        prev_step_idx=prev_step_idx,
        is_first_prompt=draw(st.booleans()),
        step_log=step_log,
        mutation_log=mutation_log,
        completed_step_ids=completed,
        skip_completed_ids=skip,
        goal_synthesis_injected=draw(st.booleans()),
        cross_step_hint=draw(st.one_of(st.none(), st.text(max_size=20))),
        run_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=16))),
        goal_task_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=16))),
        token_usage_history=history,
    )


# ──────────────────────────────────────────────
# Property tests（Hypothesis ≥ 50 example，AC5-1）
# ──────────────────────────────────────────────
@settings(
    max_examples=80,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(ctx=execution_contexts())
def test_roundtrip_idempotent(ctx: ExecutionContext) -> None:
    """ctx.to_dict() → from_dict() → to_dict() 結果必須穩定（idempotent）。"""
    d1 = ctx.to_dict()
    restored = ExecutionContext.from_dict(d1)
    d2 = restored.to_dict()
    assert d1 == d2, f"round-trip drift: left={d1} right={d2}"


@settings(max_examples=60, deadline=None)
@given(ctx=execution_contexts())
def test_roundtrip_json_serializable(ctx: ExecutionContext) -> None:
    """to_dict() 結果必須能直接 json.dumps（純資料）。"""
    d = ctx.to_dict()
    blob = json.dumps(d, ensure_ascii=False, sort_keys=True)
    restored_dict = json.loads(blob)
    restored = ExecutionContext.from_dict(restored_dict)
    assert restored.to_dict() == d


@settings(max_examples=50, deadline=None)
@given(ctx=execution_contexts())
def test_roundtrip_preserves_set_semantics(ctx: ExecutionContext) -> None:
    """completed_step_ids / skip_completed_ids 需從 list 還原為 set，集合語意保留。"""
    d = ctx.to_dict()
    restored = ExecutionContext.from_dict(d)
    assert restored.completed_step_ids == ctx.completed_step_ids
    assert restored.skip_completed_ids == ctx.skip_completed_ids
    assert isinstance(restored.completed_step_ids, set)
    assert isinstance(restored.skip_completed_ids, set)


@settings(max_examples=50, deadline=None)
@given(ctx=execution_contexts())
def test_to_dict_excludes_transient_fields(ctx: ExecutionContext) -> None:
    """transient 欄位（step_trackers / resume_checkpoint）不可出現在 to_dict 結果。"""
    d = ctx.to_dict()
    assert "step_trackers" not in d
    assert "resume_checkpoint" not in d


# ──────────────────────────────────────────────
# normalize_value 邊界 case
# ──────────────────────────────────────────────
class _SampleEnum(Enum):
    A = "alpha"
    B = "beta"


def test_normalize_datetime_naive_treated_as_utc():
    dt = datetime(2026, 5, 17, 12, 30, 45)
    out = normalize_value(dt)
    assert out.endswith("Z")
    assert "2026-05-17T12:30:45" in out


def test_normalize_datetime_aware_converted_to_utc():
    from datetime import timedelta
    tz = timezone(timedelta(hours=8))
    dt = datetime(2026, 5, 17, 20, 30, 45, tzinfo=tz)
    out = normalize_value(dt)
    assert "2026-05-17T12:30:45" in out
    assert out.endswith("Z")


def test_normalize_uuid_to_str():
    u = uuid4()
    assert normalize_value(u) == str(u)
    assert isinstance(normalize_value(u), str)


def test_normalize_enum_to_value():
    assert normalize_value(_SampleEnum.A) == "alpha"
    assert normalize_value(_SampleEnum.B) == "beta"


def test_normalize_set_to_sorted_list():
    assert normalize_value({"c", "a", "b"}) == ["a", "b", "c"]
    assert normalize_value(frozenset({3, 1, 2})) == [1, 2, 3]


def test_normalize_nested_dict_with_datetime_uuid_enum():
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    u = uuid4()
    raw = {"t": dt, "id": u, "e": _SampleEnum.A, "list": [{"set": {"x", "y"}}]}
    out = normalize_value(raw)
    assert out["t"].endswith("Z")
    assert out["id"] == str(u)
    assert out["e"] == "alpha"
    assert out["list"] == [{"set": ["x", "y"]}]


def test_normalize_bytes_decoded():
    assert normalize_value(b"hello") == "hello"


def test_normalize_bytes_non_utf8_fallback_hex():
    raw = bytes([0xff, 0xfe, 0xfd])
    assert normalize_value(raw) == "fffefd"


def test_normalize_unknown_object_fallback_str():
    class Foo:
        def __str__(self):
            return "foo-repr"
    assert normalize_value(Foo()) == "foo-repr"


# ──────────────────────────────────────────────
# diff_normalized
# ──────────────────────────────────────────────
def test_diff_normalized_no_diff():
    a = {"step_idx": 1, "run_id": "r"}
    b = {"step_idx": 1, "run_id": "r"}
    assert diff_normalized(a, b) == {}


def test_diff_normalized_finds_step_idx_drift():
    a = {"step_idx": 1, "run_id": "r"}
    b = {"step_idx": 2, "run_id": "r"}
    drift = diff_normalized(a, b)
    assert "step_idx" in drift
    assert drift["step_idx"] == {"left": 1, "right": 2}


def test_diff_normalized_finds_missing_keys():
    a = {"step_idx": 1}
    b = {"step_idx": 1, "extra": "x"}
    drift = diff_normalized(a, b)
    assert "extra" in drift
    assert drift["extra"] == {"left": None, "right": "x"}


def test_diff_normalized_datetime_drift_in_utc():
    from datetime import timedelta
    tz = timezone(timedelta(hours=8))
    a = {"saved_at": datetime(2026, 5, 17, 20, 30, tzinfo=tz)}
    b = {"saved_at": datetime(2026, 5, 17, 12, 30, tzinfo=timezone.utc)}
    drift = diff_normalized(a, b)
    assert drift == {}, "同一 UTC 時刻不應視為 drift"


def test_diff_normalized_set_order_irrelevant():
    a = {"ids": {"c", "a", "b"}}
    b = {"ids": {"b", "a", "c"}}
    drift = diff_normalized(a, b)
    assert drift == {}


# ──────────────────────────────────────────────
# from_dict 前向相容
# ──────────────────────────────────────────────
def test_from_dict_ignores_unknown_fields():
    raw = {"step_idx": 5, "future_field": "x", "another_one": [1, 2]}
    ctx = ExecutionContext.from_dict(raw)
    assert ctx.step_idx == 5


def test_from_dict_partial_data_uses_defaults():
    ctx = ExecutionContext.from_dict({"step_idx": 3})
    assert ctx.step_idx == 3
    assert ctx.run_id is None
    assert ctx.goal_task_id is None
    assert ctx.completed_step_ids == set()
    assert ctx.token_usage_history == []


def test_from_dict_empty_returns_defaults():
    ctx = ExecutionContext.from_dict({})
    assert ctx.step_idx == 0
    assert ctx.prev_step_idx == -1


def test_to_dict_with_defaults():
    ctx = ExecutionContext()
    d = ctx.to_dict()
    assert d["step_idx"] == 0
    assert d["completed_step_ids"] == []
    assert d["token_usage_history"] == []
    assert d["run_id"] is None
