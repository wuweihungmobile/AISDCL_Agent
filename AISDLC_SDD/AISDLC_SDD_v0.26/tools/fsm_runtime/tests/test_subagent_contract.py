"""Unit tests for ACT-020 Subagent Dispatch Contract (Phase E M2)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import tools.fsm_runtime.subagent_contract as sc  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402


class ModeResolutionTests(unittest.TestCase):
    def _with_env(self, value):
        return patch.dict(os.environ, {"SDD_SUBAGENT_CONTRACT": value}, clear=False)

    def test_default_is_soft(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SDD_SUBAGENT_CONTRACT", None)
            self.assertEqual(sc.mode(), "soft")

    def test_off_mode(self) -> None:
        with self._with_env("0"):
            self.assertEqual(sc.mode(), "off")

    def test_shadow_mode(self) -> None:
        with self._with_env("warn"):
            self.assertEqual(sc.mode(), "shadow")

    def test_hard_mode(self) -> None:
        with self._with_env("hard"):
            self.assertEqual(sc.mode(), "hard")


class VerifyActionAllowedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-sub.yaml"
        self.state = load_state("sub-proj", path=self.path)
        self.rt = FSMRuntime(self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _with_mode(self, mode: str):
        return patch.dict(os.environ, {"SDD_SUBAGENT_CONTRACT": mode}, clear=False)

    def test_escalation_blocks_write_in_soft_mode(self) -> None:
        self.rt.state.current = "ESCALATION"
        with self._with_mode("1"):
            ok, reason = sc.verify_action_allowed(
                "dev-senior", "Write", target="docs/03_testing/RTM.md",
                runtime=self.rt,
            )
        self.assertFalse(ok)
        self.assertIn("ESCALATION", reason)

    def test_escalation_warns_only_in_shadow(self) -> None:
        self.rt.state.current = "ESCALATION"
        with self._with_mode("warn"):
            ok, reason = sc.verify_action_allowed(
                "dev-senior", "Write", target="docs/03_testing/RTM.md",
                runtime=self.rt,
            )
        self.assertTrue(ok)
        self.assertIn("[shadow]", reason)

    def test_spec_write_forbidden_in_implementation(self) -> None:
        self.rt.state.current = "IMPLEMENTATION"
        with self._with_mode("1"):
            ok, reason = sc.verify_action_allowed(
                "dev-senior", "Write", target="docs/02_architecture/SRD.md",
                runtime=self.rt,
            )
        self.assertFalse(ok)
        self.assertIn("spec write forbidden", reason)

    def test_spec_write_ok_in_spec_drafting(self) -> None:
        self.rt.state.current = "SPEC_DRAFTING"
        with self._with_mode("1"):
            ok, _ = sc.verify_action_allowed(
                "sa-analyst", "Write", target="docs/01_requirements/FRD.md",
                runtime=self.rt,
            )
        self.assertTrue(ok)

    def test_non_spec_write_in_implementation_allowed(self) -> None:
        self.rt.state.current = "IMPLEMENTATION"
        with self._with_mode("1"):
            ok, _ = sc.verify_action_allowed(
                "dev-senior", "Write", target="src/services/auth.py",
                runtime=self.rt,
            )
        self.assertTrue(ok)

    def test_off_mode_always_ok(self) -> None:
        self.rt.state.current = "ESCALATION"
        with self._with_mode("0"):
            ok, _ = sc.verify_action_allowed(
                "dev-senior", "Write", target="docs/03_testing/x.md", runtime=self.rt,
            )
        self.assertTrue(ok)


class EnterExitFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-flow.yaml"
        self.state = load_state("flow-proj", path=self.path)
        self.rt = FSMRuntime(self.state)
        self.rt.state.current = "IMPLEMENTATION"
        self._patch_dirs = patch.multiple(
            sc,
            DISPATCH_LOG_DIR=Path(self._tmp.name),
            BYPASS_LOG_DIR=Path(self._tmp.name),
        )
        self._patch_dirs.start()

    def tearDown(self) -> None:
        self._patch_dirs.stop()
        self._tmp.cleanup()

    def test_enter_records_frozen_view(self) -> None:
        view = sc.enter_subagent("dev-senior", stage="Stage-1", runtime=self.rt)
        self.assertEqual(view["agent"], "dev-senior")
        self.assertEqual(view["fsm_state"], "IMPLEMENTATION")
        self.assertTrue(view["entered_at"])
        # File persisted
        import yaml  # noqa: WPS433
        dispatches = list(Path(self._tmp.name).glob("DISPATCH-LOG-*.yaml"))
        self.assertTrue(dispatches)
        doc = yaml.safe_load(dispatches[0].read_text(encoding="utf-8"))
        self.assertEqual(doc["dispatches"][0]["phase"], "enter")

    def test_exit_records_result(self) -> None:
        view = sc.enter_subagent("qa-tester", runtime=self.rt)
        sc.exit_subagent("qa-tester", "PASS", frozen_view=view)
        import yaml  # noqa: WPS433
        doc = yaml.safe_load(
            (list(Path(self._tmp.name).glob("DISPATCH-LOG-*.yaml"))[0]).read_text(encoding="utf-8")
        )
        phases = [d["phase"] for d in doc["dispatches"]]
        self.assertIn("enter", phases)
        self.assertIn("exit", phases)

    def test_record_bypass_writes_audit(self) -> None:
        path = sc.record_bypass(
            "dev-senior", "Write", "docs/03_testing/RTM.md",
            reason="Emergency hotfix approved by lead",
            env_value="HOTFIX-2026-04-20",
        )
        import yaml  # noqa: WPS433
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["bypasses"][0]["agent"], "dev-senior")
        self.assertEqual(doc["bypasses"][0]["env_value"], "HOTFIX-2026-04-20")

    def test_injection_hint_shadow_vs_hard(self) -> None:
        with patch.dict(os.environ, {"SDD_SUBAGENT_CONTRACT": "warn"}, clear=False):
            shadow = sc.injection_hint_for_task("dev-senior")
            self.assertIn("shadow", (shadow or "").lower())
        with patch.dict(os.environ, {"SDD_SUBAGENT_CONTRACT": "hard"}, clear=False):
            hard = sc.injection_hint_for_task("dev-senior")
            self.assertIn("hard", (hard or "").lower())

    def test_injection_hint_unregistered_returns_none(self) -> None:
        with patch.dict(os.environ, {"SDD_SUBAGENT_CONTRACT": "1"}, clear=False):
            self.assertIsNone(sc.injection_hint_for_task("unknown-agent"))

    def test_soft_bypass_env_allows_blocked_action(self) -> None:
        """soft mode + SDD_SUBAGENT_CONTRACT_BYPASS=<reason> must short-circuit
        contract refusal AND record a bypass audit entry."""
        self.rt.state.current = "ESCALATION"
        with patch.dict(os.environ, {
            "SDD_SUBAGENT_CONTRACT": "1",
            "SDD_SUBAGENT_CONTRACT_BYPASS": "EMERGENCY-HOTFIX-2026-04-20",
        }, clear=False):
            ok, reason = sc.verify_action_allowed(
                "dev-senior", "Write", target="docs/03_testing/RTM.md",
                runtime=self.rt,
            )
        self.assertTrue(ok)
        self.assertIn("[bypass]", reason)
        bypass_logs = list(Path(self._tmp.name).glob("SUBAGENT-BYPASS-*.yaml"))
        self.assertTrue(bypass_logs, "soft bypass must write SUBAGENT-BYPASS log")
        import yaml  # noqa: WPS433
        doc = yaml.safe_load(bypass_logs[0].read_text(encoding="utf-8"))
        self.assertEqual(
            doc["bypasses"][0]["env_value"], "EMERGENCY-HOTFIX-2026-04-20",
        )

    def test_hard_mode_record_bypass_is_noop(self) -> None:
        """Hard mode must refuse to write a bypass audit entry — Rule 9.8.4
        guarantees no bypass trail can exist under hard mode."""
        with patch.dict(os.environ, {"SDD_SUBAGENT_CONTRACT": "hard"}, clear=False):
            result = sc.record_bypass(
                "dev-senior", "Write", "docs/03_testing/RTM.md",
                reason="should be ignored",
                env_value="should-not-be-written",
            )
        self.assertIsNone(result)
        self.assertEqual(
            list(Path(self._tmp.name).glob("SUBAGENT-BYPASS-*.yaml")), [],
            "hard mode must NOT write any bypass log",
        )

    def test_hard_mode_bypass_env_does_not_short_circuit(self) -> None:
        """Even with SDD_SUBAGENT_CONTRACT_BYPASS set, hard mode must still
        refuse a contract violation."""
        self.rt.state.current = "ESCALATION"
        with patch.dict(os.environ, {
            "SDD_SUBAGENT_CONTRACT": "hard",
            "SDD_SUBAGENT_CONTRACT_BYPASS": "TRY-TO-BYPASS",
        }, clear=False):
            ok, reason = sc.verify_action_allowed(
                "dev-senior", "Write", target="docs/03_testing/RTM.md",
                runtime=self.rt,
            )
        self.assertFalse(ok)
        self.assertNotIn("[bypass]", reason)


class RegisteredAgentSyncTests(unittest.TestCase):
    """Rule 9.8.4 禁止條款：REGISTERED 必須與 orchestrator YAML 同步。"""

    def test_registered_matches_orchestrator_yaml(self) -> None:
        import yaml  # noqa: WPS433
        yaml_path = (
            Path(__file__).resolve().parents[3]
            / "agent" / "specialized" / "sdd-orchestrator-zh.yaml"
        )
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        registered_in_yaml = set(
            doc["agent"]["dispatch_protocol"]["registered_agents"]
        )
        self.assertEqual(
            sorted(registered_in_yaml), sorted(sc.REGISTERED),
            "subagent_contract.REGISTERED 與 orchestrator YAML 不一致",
        )


if __name__ == "__main__":
    unittest.main()
