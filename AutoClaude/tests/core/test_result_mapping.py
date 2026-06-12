"""W0b DoD：KernelResult 新增 4 欄位 round-trip 驗證（SD_03 §2.6）。"""
from __future__ import annotations

from autoclaude.core.kernel_state import KernelResult


class TestKernelResultW0bFields:
    def test_workflow_field_default(self):
        r = KernelResult(success=True, completed_steps=1, total_steps=1)
        assert r.workflow == ""

    def test_scheduled_resume_at_default_none(self):
        r = KernelResult(success=True, completed_steps=1, total_steps=1)
        assert r.scheduled_resume_at is None

    def test_evolved_playbook_path_default_none(self):
        r = KernelResult(success=True, completed_steps=1, total_steps=1)
        assert r.evolved_playbook_path is None

    def test_evolution_fresh_required_default_false(self):
        r = KernelResult(success=True, completed_steps=1, total_steps=1)
        assert r.evolution_fresh_required is False

    def test_all_new_fields_roundtrip(self):
        r = KernelResult(
            success=False, completed_steps=2, total_steps=5,
            workflow="aisdlc",
            scheduled_resume_at="2026-05-12T10:00:00",
            evolved_playbook_path="/tmp/evolved.yaml",
            evolution_fresh_required=True,
        )
        assert r.workflow == "aisdlc"
        assert r.scheduled_resume_at == "2026-05-12T10:00:00"
        assert r.evolved_playbook_path == "/tmp/evolved.yaml"
        assert r.evolution_fresh_required is True

    def test_factory_success_preserves_new_defaults(self):
        r = KernelResult.success_(
            completed_steps=3, total_steps=3,
            step_log=["[T01] s ✓ (attempt 1)"],
            completed_step_ids=["T01"],
            contributors=[],
        )
        assert r.workflow == ""
        assert r.scheduled_resume_at is None
        assert r.evolved_playbook_path is None
        assert r.evolution_fresh_required is False
