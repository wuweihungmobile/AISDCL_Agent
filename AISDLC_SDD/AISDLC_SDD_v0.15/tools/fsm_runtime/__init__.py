"""FSM Runtime Package — SDD Agentic Closed-Loop State Machine Engine.

Phase D ACT-010 實作。將 SDD_FSM_ENGINE.md 的狀態定義升級為可執行引擎。
"""
from .state_loader import FSMState, load_state, save_state
from .transition_rules import (
    TransitionError,
    is_transition_allowed,
    next_state_on_gate_fail,
    next_state_on_gate_pass,
)
from .fsm_runtime import FSMRuntime

__all__ = [
    "FSMRuntime",
    "FSMState",
    "TransitionError",
    "is_transition_allowed",
    "load_state",
    "next_state_on_gate_fail",
    "next_state_on_gate_pass",
    "save_state",
]
