"""improving_115（ADR-XPLAT-016 §6／§7.1／§8.3）：凍結閘端到端。

真 SddToPlaybookAdapter＋真 SddGovernancePlugin＋PlaybookKernel，用合成的 FSM 狀態檔（多專案
共處、凍結摘要、委派態）驗證引擎 PRE_RUN 的 fail-closed 行為——單元測試各自守規則，這裡守的是
「規則在引擎真正執行前的那一道門上確實生效」：

  1. 他專案已凍結不放行本專案（G-02／S-05）；不指定專案且多檔 ⇒ fail-closed
  2. 凍結後改檔 ⇒ PRE_RUN veto（G-06）
  3. 委派態（AUTOCLAUDE_DELEGATED）的舊狀態檔放行（Bridge 在 spawn 前已 delegate-enter）
  4. workflow_path 指向檔案時 PRE_RUN 載到同一份規格（S-04，plugin 與 port 簽名不改）
  5. 編譯後規格被加了編不成的 AT：PRE_RUN 不崩潰，但出聲（§8.2）
"""
from __future__ import annotations

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin
from autoclaude.tools.sdd_compile import compile_spec
from tests.infra.test_sdd_to_playbook_adapter import (
    _Events,
    _frozen_stage,
    _producer_digest,
    _spec_path,
    _spec_text,
    _write_fsm_state,
    _write_spec,
    _write_state,
)
from tests.integration.test_sdd_bridge.test_bridge_multi_ac import _RegexOnlyEvaluator


class _AnyExecutor:
    """所有步驟的輸出都能通過 Gherkin `Then 回傳 201 Created` 轉出的 regex。"""

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        return ExecutionOutput(text="HTTP 201 Created")


def _run(playbook, spec_source, obs=None):
    plugin = SddGovernancePlugin(spec_source=spec_source, observability=obs)
    bus = EventBus()
    bus.register(plugin)
    result = PlaybookKernel(_AnyExecutor(), _RegexOnlyEvaluator(), bus=bus).run(playbook)
    return result, plugin


_ONE_AT = _spec_text(rows=[("AC-001-1", "AT-001-1-1")], gherkin_ids=["AT-001-1-1"])


class TestSharedStateDirectory:
    """同一個 build/reports/fsm 住兩個專案：alpha 已凍結、zeta 還在草稿。"""

    @pytest.fixture()
    def shared(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_ONE_AT)
        _write_state(tmp_path, "alpha", current="SPEC_FROZEN")
        _write_state(tmp_path, "zeta", current="INIT")
        return spec_dir

    def test_the_unfrozen_project_is_vetoed_while_its_frozen_sibling_runs(
            self, shared, monkeypatch):
        playbook = compile_spec(str(shared), fsm_project="alpha")
        monkeypatch.setenv("SDD_PROJECT", "zeta")  # 引擎子行程的環境（Bridge 注入的就是這一個）
        result, _ = _run(playbook, SddToPlaybookAdapter())
        assert result.success is False and result.reason == "vetoed_at_pre_run"
        assert any("SDD-VIOLATION[SPEC_NOT_FROZEN]" in r and "INIT" in r
                   for r in result.veto_reasons)
        assert result.completed_steps == 0

        monkeypatch.setenv("SDD_PROJECT", "alpha")
        result, plugin = _run(playbook, SddToPlaybookAdapter())
        assert result.success is True and result.completed_steps == 1
        assert plugin.snapshot()["spec_digest"].startswith("sha256:")

    def test_without_a_project_key_the_shared_directory_is_refused_not_guessed(self, shared):
        """舊版取字母序第一份（alpha）而放行；現在不指定專案且多檔 ⇒ fail-closed。"""
        playbook = compile_spec(str(shared), fsm_project="alpha")
        result, _ = _run(playbook, SddToPlaybookAdapter())  # 環境沒有 SDD_PROJECT
        assert result.success is False and result.reason == "vetoed_at_pre_run"
        assert any("不唯一" in r for r in result.veto_reasons)


class TestDelegatedState:
    def test_a_delegated_legacy_state_file_is_let_through(self, tmp_path):
        """Bridge 在 spawn 前已 delegate-enter，引擎 PRE_RUN 讀到的 current_state 就是
        AUTOCLAUDE_DELEGATED；frozen_stages 為空的舊狀態檔缺這一項，委派一啟動就被 veto。"""
        spec_dir = _write_spec(tmp_path, text=_ONE_AT)
        _write_fsm_state(tmp_path, current_state="AUTOCLAUDE_DELEGATED")
        playbook = compile_spec(str(spec_dir))
        result, _ = _run(playbook, SddToPlaybookAdapter())
        assert result.success is True and result.completed_steps == 1


class TestFrozenDigestAtPreRun:
    def test_editing_the_spec_after_compile_vetoes_the_run(self, tmp_path):
        """舊版：匯入後改檔仍可執行（僅執行中 advisory 漂移事件）；現在 PRE_RUN 即 fail-closed。"""
        spec_dir = _write_spec(tmp_path, text=_ONE_AT)
        spec_file = _spec_path(tmp_path)
        _write_state(tmp_path, "demo", current="SPEC_FROZEN",
                     frozen_stages=[_frozen_stage(tmp_path, spec_file)])
        playbook = compile_spec(str(spec_dir))
        spec_file.write_text(_ONE_AT + "\n編譯之後偷加的一行\n", encoding="utf-8")
        result, plugin = _run(playbook, SddToPlaybookAdapter())
        assert result.success is False and result.reason == "vetoed_at_pre_run"
        assert any("SDD-VIOLATION[SPEC_NOT_FROZEN]" in r and "與凍結時不同" in r
                   for r in result.veto_reasons)
        assert plugin.snapshot()["spec_digest"] is None and result.completed_steps == 0

    def test_an_unchanged_frozen_spec_runs_and_reports_verified(self, tmp_path):
        spec_dir = _write_spec(tmp_path, text=_ONE_AT)
        spec_file = _spec_path(tmp_path)
        _write_state(tmp_path, "demo", current="SPEC_FROZEN",
                     frozen_stages=[_frozen_stage(tmp_path, spec_file)])
        playbook = compile_spec(str(spec_dir))
        result, plugin = _run(playbook, SddToPlaybookAdapter())
        assert result.success is True
        assert plugin.snapshot()["spec_digest"] == _producer_digest(spec_file)


class TestSpecFileAnchoredPlaybook:
    def test_pre_run_loads_the_named_file_not_a_scan_of_the_directory(self, tmp_path):
        """兩份 TCS 同目錄：掃描會因歧義而 ValueError；workflow_path 是檔案時 PRE_RUN 載入該檔。"""
        alpha = _spec_text(rows=[("AC-001-1", "AT-001-1-1")], gherkin_ids=["AT-001-1-1"])
        beta = _spec_text(rows=[("AC-002-1", "AT-002-1-1"), ("AC-002-1", "AT-002-1-2")],
                          gherkin_ids=["AT-002-1-1", "AT-002-1-2"])
        spec_dir = _write_spec(tmp_path, text=alpha, name="TCS-Alpha.md")
        _write_spec(tmp_path, text=beta, name="TCS-Beta.md")
        beta_file = _spec_path(tmp_path, "TCS-Beta.md")
        _write_state(tmp_path, "demo", current="SPEC_FROZEN",
                     frozen_stages=[_frozen_stage(tmp_path, _spec_path(tmp_path, "TCS-Alpha.md"),
                                                  beta_file)])
        playbook = compile_spec(str(spec_dir), spec_file="03_testing/contracts/TCS-Beta.md")
        assert playbook.workflow_path.endswith("TCS-Beta.md")
        result, plugin = _run(playbook, SddToPlaybookAdapter())
        assert result.success is True and result.completed_steps == 2
        assert plugin.snapshot()["spec_digest"] == _producer_digest(beta_file)


class TestUnmappedAtsAtPreRun:
    def test_pre_run_does_not_crash_on_an_uncompilable_at_but_announces_it(self, tmp_path):
        """規格若在編譯後被改動，不能讓引擎在 PRE_RUN 崩潰（adapter 的 load_spec 不拋）；
        但「出現卻未編成」一律出聲（sdd.at_unmapped），不再靜默丟棄。"""
        spec_dir = _write_spec(tmp_path, text=_ONE_AT)
        _write_fsm_state(tmp_path)
        playbook = compile_spec(str(spec_dir))
        _spec_path(tmp_path).write_text(
            _spec_text(rows=[("AC-001-1", "AT-001-1-1"), ("AC-001-1", "AT-001-E-1")],
                       gherkin_ids=["AT-001-1-1"]), encoding="utf-8")
        obs = _Events()
        result, _ = _run(playbook, SddToPlaybookAdapter(observability=obs), obs)
        assert result.success is True and result.completed_steps == 1
        (event,) = obs.named("sdd.at_unmapped")
        assert event["at_ids"] == ["AT-001-E-1"]
