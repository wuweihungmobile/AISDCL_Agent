"""ACT-022: FSM spec (MD) vs runtime (Python) sync test.

Parses `狀態轉換表` in workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md and compares
against transition_rules._HAPPY_PATH. Any drift fails CI.

Conventions:
- Only happy-path transitions are compared (emergency targets are global).
- MD arrow targets can be compound phrases, e.g. "HUMAN_PENDING（...）" — the
  parser extracts the first ALL_CAPS token as the target.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.transition_rules import (  # noqa: E402
    _HAPPY_PATH,
    all_states,
)

# ACT-022 → R2：MD parser 已抽取為共用模組（單一真實來源），由本測試與
# arch_fitness FF-1 共用。
from tools.fsm_runtime.fsm_md_parser import (  # noqa: E402
    FSM_ENGINE_MD,
    _EMERGENCY_TARGETS_IN_MD,
    filter_to_happy_path,
    parse_md_transitions,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class MDPythonSyncTests(unittest.TestCase):
    def test_md_happy_path_subset_of_python(self) -> None:
        md = parse_md_transitions(FSM_ENGINE_MD)
        md_happy = filter_to_happy_path(md)
        missing_in_py: list[str] = []
        for src, dsts in md_happy.items():
            py_targets = _HAPPY_PATH.get(src, set())
            for dst in dsts:
                if dst not in py_targets:
                    missing_in_py.append(f"{src} → {dst}")
        # QA-03: 若失敗，連同解析出的完整 md_transitions 一起輸出，便於定位
        if missing_in_py:
            diag = "\n".join(
                f"  {src}: {sorted(dsts)}" for src, dsts in sorted(md_happy.items())
            )
            self.fail(
                "MD declared but Python does not allow: "
                + ", ".join(missing_in_py)
                + "\nfull parsed md_happy_path:\n"
                + diag
            )

    def test_core_python_edges_mentioned_in_md(self) -> None:
        """Core workflow edges (非 emergency / 非參數化來源) 必須在 MD 可被識別。

        AUTO_COMPACT_PENDING / RESUME_VERIFICATION / REMINDER 來源端在 MD 以抽象
        描述表達（"resume_state", "對應可恢復狀態", auto_return_to），因此不做嚴格
        字面比對，避免誤判。
        """
        md = parse_md_transitions(FSM_ENGINE_MD)
        abstract_sources = {"AUTO_COMPACT_PENDING", "RESUME_VERIFICATION", "REMINDER"}
        missing: list[str] = []
        for src, dsts in _HAPPY_PATH.items():
            if src in abstract_sources:
                continue
            md_dsts = md.get(src, set())
            for dst in dsts:
                if dst in _EMERGENCY_TARGETS_IN_MD:
                    continue
                if dst not in md_dsts:
                    missing.append(f"{src} → {dst}")
        self.assertFalse(
            missing,
            "Python core happy-path edges not declared in MD: " + ", ".join(missing),
        )

    def test_all_python_states_mentioned_in_md(self) -> None:
        text = FSM_ENGINE_MD.read_text(encoding="utf-8")
        missing = [s for s in all_states() if s not in text]
        self.assertFalse(
            missing,
            "States defined in Python but not mentioned in MD: " + ", ".join(missing),
        )

    def test_learning_commit_happy_path_targets(self) -> None:
        """P1-6：LEARNING_COMMIT 出口只能為 {RELEASE, ESCALATION}。

        此 invariant 與 FSMRuntime.exit_learning_commit 的 outcome→target 對應綁定；
        任何誤加 happy-path 邊（如 LEARNING_COMMIT → SPEC_DRAFTING）都會讓
        approved/rejected 二元語意崩壞，必須失敗。
        """
        self.assertEqual(
            _HAPPY_PATH.get("LEARNING_COMMIT"),
            {"RELEASE", "ESCALATION"},
            "LEARNING_COMMIT happy-path targets drifted — see Rule 9.11.4",
        )

    def test_learning_commit_entry_allowed_sources(self) -> None:
        """P1-6：enter_learning_commit 僅接受 {ESCALATION, TERMINATED, RELEASE, PRODUCTION_SIGNAL}。

        Fixture：用 tmp 建立 FSMState，逐個 src state 試 enter，確認：
          - 合法 source 可成功進入 LEARNING_COMMIT
          - 非法 source（happy-path 中段狀態）raise TransitionError
        """
        import tempfile
        from pathlib import Path as _Path
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state, save_state
        from tools.fsm_runtime.transition_rules import TransitionError

        allowed_sources = {"ESCALATION", "TERMINATED", "RELEASE", "PRODUCTION_SIGNAL"}
        illegal_samples = {"SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY"}

        with tempfile.TemporaryDirectory() as td:
            td_path = _Path(td)
            for src in allowed_sources:
                state_path = td_path / f"FSM-STATE-entry-ok-{src}.yaml"
                state = load_state("entry-ok", path=state_path, create_if_missing=True)
                state.root["current_state"] = src
                save_state(state)
                rt = FSMRuntime(state)
                rt.enter_learning_commit(
                    fpl_id="FPL-001",
                    proposed_slv_id="SLV-007",
                    proposed_rule_path=".claude/skills/spec-logical-validator/rules/SLV-007.yaml",
                )
                self.assertEqual(rt.state.current, "LEARNING_COMMIT", f"src={src} should enter")

            for src in illegal_samples:
                state_path = td_path / f"FSM-STATE-entry-bad-{src}.yaml"
                state = load_state("entry-bad", path=state_path, create_if_missing=True)
                state.root["current_state"] = src
                save_state(state)
                rt = FSMRuntime(state)
                with self.assertRaises(TransitionError, msg=f"src={src} should be rejected"):
                    rt.enter_learning_commit(
                        fpl_id="FPL-001",
                        proposed_slv_id="SLV-007",
                    )


if __name__ == "__main__":
    unittest.main()
