"""SD_Improving_05 W0 SD-C7 + QA 建議：feature flag T18_P2_PHASES_MIGRATED 契約測。

SD_05 §8.2 G-gate 列為「W1+ contract gate」，W0 先建立基準測試以驗證：
  - 8 個合法 phase 名稱（LEGAL_PHASES）
  - 環境變數 AUTOCLAUDE_T18_P2_PHASES_MIGRATED 解析（逗號分隔 + 大小寫）
  - 非法 phase 名 raise ValueError
  - is_phase_migrated() 對應正確的 KernelPhase enum
  - set_migrated_phases() 測試 override 優先級
"""
from __future__ import annotations

import pytest

from autoclaude.core.hookspec import KernelPhase
from autoclaude.core.phase_migration_flag import (
    LEGAL_PHASES,
    get_migrated_phases,
    is_phase_migrated,
    set_migrated_phases,
)


@pytest.fixture(autouse=True)
def _reset_override():
    """每個 test 結束清空 override，避免狀態污染。"""
    yield
    set_migrated_phases(None)


class TestLegalPhases:
    def test_eight_legal_phases(self):
        """SD_05 §7 (2a)：8 個合法 phase 名稱。"""
        assert len(LEGAL_PHASES) == 8

    def test_legal_phase_names_match_KernelPhase_names(self):
        """每個 LEGAL_PHASES 名稱必為 KernelPhase enum 的 name。"""
        kernel_phase_names = {p.name for p in KernelPhase}
        for name in LEGAL_PHASES:
            assert name in kernel_phase_names, (
                f"LEGAL_PHASES '{name}' 不存在於 KernelPhase enum"
            )

    def test_legal_phases_are_W0_T0_1_new_phases(self):
        """LEGAL_PHASES 必須恰好是 SD_05 W0 T0-1 新增的 8 個 phase。"""
        expected = {
            "PRE_COMPACT", "POST_COMPACT", "ON_PERSISTENCE_REQUEST",
            "ON_ESCALATION_DUMP_REQUEST", "ON_EVOLUTION_PROPOSE",
            "ON_EVOLUTION_APPLY", "ON_AUTO_RESUME_WAKE", "ON_PROMPT_PREPARED",
        }
        assert LEGAL_PHASES == expected


class TestEnvVarParsing:
    def test_default_empty_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", raising=False)
        assert get_migrated_phases() == frozenset()

    def test_single_phase_parsed(self, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "PRE_COMPACT")
        assert get_migrated_phases() == frozenset({"PRE_COMPACT"})

    def test_multiple_phases_csv(self, monkeypatch):
        monkeypatch.setenv(
            "AUTOCLAUDE_T18_P2_PHASES_MIGRATED",
            "PRE_COMPACT,POST_COMPACT,ON_PERSISTENCE_REQUEST",
        )
        assert get_migrated_phases() == frozenset({
            "PRE_COMPACT", "POST_COMPACT", "ON_PERSISTENCE_REQUEST",
        })

    def test_lowercase_normalized(self, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "pre_compact,post_compact")
        phases = get_migrated_phases()
        assert "PRE_COMPACT" in phases
        assert "POST_COMPACT" in phases

    def test_whitespace_stripped(self, monkeypatch):
        monkeypatch.setenv(
            "AUTOCLAUDE_T18_P2_PHASES_MIGRATED",
            "  PRE_COMPACT ,  POST_COMPACT  ",
        )
        assert get_migrated_phases() == frozenset({"PRE_COMPACT", "POST_COMPACT"})

    def test_empty_string_returns_empty_set(self, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "")
        assert get_migrated_phases() == frozenset()


class TestIllegalPhaseRejection:
    def test_illegal_phase_raises(self, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "BOGUS_PHASE")
        with pytest.raises(ValueError, match="非法|illegal"):
            get_migrated_phases()

    def test_mixed_legal_illegal_still_raises(self, monkeypatch):
        monkeypatch.setenv(
            "AUTOCLAUDE_T18_P2_PHASES_MIGRATED",
            "PRE_COMPACT,UNKNOWN_PHASE",
        )
        with pytest.raises(ValueError, match="非法|illegal|UNKNOWN_PHASE"):
            get_migrated_phases()


class TestIsPhaseMigrated:
    def test_unmigrated_phase_returns_false(self, monkeypatch):
        monkeypatch.delenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", raising=False)
        set_migrated_phases(None)
        assert is_phase_migrated(KernelPhase.PRE_COMPACT) is False

    def test_migrated_phase_returns_true(self):
        set_migrated_phases({"PRE_COMPACT"})
        assert is_phase_migrated(KernelPhase.PRE_COMPACT) is True
        assert is_phase_migrated(KernelPhase.POST_COMPACT) is False

    def test_all_8_phases_can_be_migrated(self):
        set_migrated_phases(set(LEGAL_PHASES))
        for name in LEGAL_PHASES:
            phase = KernelPhase[name]
            assert is_phase_migrated(phase) is True


class TestOverridePrecedence:
    def test_override_supersedes_env_var(self, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "PRE_COMPACT")
        set_migrated_phases({"POST_COMPACT"})
        # override 應贏過 env
        assert get_migrated_phases() == frozenset({"POST_COMPACT"})

    def test_set_None_restores_env_var(self, monkeypatch):
        monkeypatch.setenv("AUTOCLAUDE_T18_P2_PHASES_MIGRATED", "PRE_COMPACT")
        set_migrated_phases({"POST_COMPACT"})
        set_migrated_phases(None)
        assert get_migrated_phases() == frozenset({"PRE_COMPACT"})

    def test_set_illegal_phase_raises(self):
        with pytest.raises(ValueError):
            set_migrated_phases({"BOGUS"})
