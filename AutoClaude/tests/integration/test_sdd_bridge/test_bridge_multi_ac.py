"""AutoSDD_improving_13 W-13-1：多-AC SDD 規格 → playbook → 端到端跑綠載具。

升 A 軸（協作自治）：既有 test_bridge_smoke.py 僅以 2-AC/3-AT 簡易載具驗證過全鏈，
本載具以**真實規模的多-AC 規格**（3 AC / 6 AT、混合測試型別、三種 Gherkin Then 斷言）
壓測既有但未被端到端覆蓋的橋接路徑：

  1. 跨多個 AC 邊界的 maintain_context 翻轉（含**連續同-AC 多次 True**，smoke 僅單次）
  2. 混合測試型別 → SCG-4(retry=5) / SCG-5 E2E(retry=2) 映射
  3. 三種 Gherkin Then 斷言型別：引號字面 / HTTP 狀態碼 / 量化 NFR→weak fallback
     （weak fallback 必經 IObservabilityPort 留審計痕）

全鏈：凍結規格 + FSM 狀態 → sdd_compile CLI → playbook YAML →
真 SddToPlaybookAdapter + 真 SddGovernancePlugin + PlaybookKernel 執行至綠。
"""
from __future__ import annotations

import re

import yaml

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from autoclaude.models.playbook import Playbook
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin
from autoclaude.tools.sdd_compile import main as sdd_compile_main
from tests.infra.test_sdd_to_playbook_adapter import _write_fsm_state

# 場景：brownfield 既有錢包系統強化。3 AC / 6 AT。
# maintain_context 預期序列（同 AC 連續為 True，跨 AC 為 False）：F,T,T,F,T,F
_MULTI_AC_SPEC = """# Test Contract Specification — 錢包轉帳強化

場景：brownfield 既有系統改進

## 1. AC → AT 映射表

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 轉帳成功 | AT-001-1-1 | 正常轉帳 | ✅ | Unit | □ |
| AC-001-1 | 轉帳成功 | AT-001-1-2 | 餘額不足 | ✅ | Unit | □ |
| AC-001-1 | 轉帳成功 | AT-001-1-3 | 冪等重試 | ✅ | Integration | □ |
| AC-002-1 | 對帳一致 | AT-002-1-1 | 雙分錄平衡 | ✅ | Contract | □ |
| AC-002-1 | 對帳一致 | AT-002-1-2 | 稽核軌跡 | ✅ | Integration | □ |
| AC-003-1 | 端到端 | AT-003-1-1 | 完整轉帳流程 | ✅ | E2E | □ |

## 2. AT 格式

```gherkin
# AT-001-1-1
Scenario: 正常轉帳
  Given 帳戶餘額充足
  When 發起轉帳
  Then 回傳 201 Created
```

```gherkin
# AT-001-1-2
Scenario: 餘額不足
  Given 帳戶餘額為零
  When 發起轉帳
  Then 顯示錯誤訊息「餘額不足」
```

```gherkin
# AT-001-1-3
Scenario: 冪等重試
  Given 相同交易 ID 已成功
  When 重送同一筆轉帳
  Then 回傳 200 OK
```

```gherkin
# AT-002-1-1
Scenario: 雙分錄平衡
  Given 一筆已完成轉帳
  When 執行對帳
  Then 帳務顯示「借貸平衡」
```

```gherkin
# AT-002-1-2
Scenario: 稽核軌跡
  Given 一筆已完成轉帳
  When 查詢稽核紀錄
  Then 系統寫入稽核軌跡並回報完成
```

```gherkin
# AT-003-1-1
Scenario: 完整轉帳流程
  Given 系統在尖峰負載
  When 執行端到端轉帳
  Then 端到端回應時間 P95 < 500ms
```
"""

# 6 步驟 step_id（sdd-{scenario}-{at_id.lower()}，scenario=brownfield）對應可通過輸出
_OUTPUT_BY_STEP = {
    "sdd-brownfield-at-001-1-1": "HTTP 201 Created",        # 狀態碼斷言
    "sdd-brownfield-at-001-1-2": "錯誤：餘額不足",            # 引號字面
    "sdd-brownfield-at-001-1-3": "回應 200 OK",             # 狀態碼斷言
    "sdd-brownfield-at-002-1-1": "對帳結果：借貸平衡",         # 引號字面
    "sdd-brownfield-at-002-1-2": "audit log written: PASSED",  # weak fallback
    "sdd-brownfield-at-003-1-1": "e2e suite: 12 PASSED",       # weak fallback（量化 NFR）
}


class _MapExecutor:
    """依 step label 合成可通過輸出（不啟動真實 PTY）。"""

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        return ExecutionOutput(text=_OUTPUT_BY_STEP.get(label, "OK"))


class _RegexOnlyEvaluator:
    """只跑 regex 雙重驗證第一層（evaluator_command 留給真實環境）。"""

    def evaluate(self, task, output) -> tuple[str | None, str, int]:
        if task.expected_output_regex and not re.search(
                task.expected_output_regex, output):
            return f"regex 不符: {task.expected_output_regex}", output[-200:], 1
        return None, "", 0


class _SpyObservability:
    """攔截 weak_regex 審計事件（contract #7）。"""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def record_event(self, name, payload):
        self.events.append((name, payload))


def _write_multi_ac_spec(root):
    docs = root / "docs" / "03_testing" / "contracts"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "TEST-CONTRACT-SPEC-Wallet.md").write_text(_MULTI_AC_SPEC, encoding="utf-8")
    return root / "docs"


def _compile(tmp_path) -> Playbook:
    spec_dir = _write_multi_ac_spec(tmp_path)
    _write_fsm_state(tmp_path)  # current_state=IMPLEMENTATION（post-frozen）
    out = tmp_path / "wallet_playbook.yaml"
    rc = sdd_compile_main(["--spec-dir", str(spec_dir), "--out", str(out)])
    assert rc == 0
    return Playbook.model_validate(yaml.safe_load(out.read_text(encoding="utf-8")))


class TestMultiAcCompile:
    def test_six_contracts_compiled_in_order(self, tmp_path):
        pb = _compile(tmp_path)
        assert [t.step_id for t in pb.tasks] == [
            "sdd-brownfield-at-001-1-1", "sdd-brownfield-at-001-1-2",
            "sdd-brownfield-at-001-1-3", "sdd-brownfield-at-002-1-1",
            "sdd-brownfield-at-002-1-2", "sdd-brownfield-at-003-1-1",
        ]

    def test_maintain_context_flips_across_ac_boundaries(self, tmp_path):
        """跨 3 個 AC 的 maintain_context 序列＝F,T,T,F,T,F（含連續同-AC 兩次 True）。"""
        pb = _compile(tmp_path)
        assert [t.maintain_context for t in pb.tasks] == [
            False, True, True, False, True, False]

    def test_retry_mapping_by_scg_gate(self, tmp_path):
        """混合測試型別：Unit/Integration/Contract→SCG-4(5)，E2E→SCG-5(2)。"""
        pb = _compile(tmp_path)
        assert [t.max_retries for t in pb.tasks] == [5, 5, 5, 5, 5, 2]

    def test_workflow_path_anchored_to_spec_dir(self, tmp_path):
        pb = _compile(tmp_path)
        assert pb.workflow_path  # SddGovernancePlugin PRE_RUN 重載規格錨點


class TestMultiAcGherkinTranslation:
    def test_three_assertion_kinds_and_weak_audit_trail(self, tmp_path):
        """三種 Then 斷言型別正確轉譯；2 筆量化/無字面斷言走 weak fallback 並留審計痕。"""
        spec_dir = _write_multi_ac_spec(tmp_path)
        _write_fsm_state(tmp_path)
        spy = _SpyObservability()
        spec = SddToPlaybookAdapter(observability=spy).load_spec(str(spec_dir))
        by_id = {c.at_id: c for c in spec.contracts}

        # 引號字面
        assert by_id["AT-001-1-2"].expected_regex == re.escape("餘額不足")
        assert by_id["AT-002-1-1"].expected_regex == re.escape("借貸平衡")
        # HTTP 狀態碼（不分大小寫）
        assert by_id["AT-001-1-1"].expected_regex == "(?i)(201|created)"
        assert by_id["AT-001-1-3"].expected_regex == "(?i)(200|ok)"
        # 量化 NFR / 無可推導字面 → weak fallback
        assert by_id["AT-002-1-2"].weak_regex is True
        assert by_id["AT-003-1-1"].weak_regex is True
        assert by_id["AT-001-1-1"].weak_regex is False

        # 恰 2 筆 weak_regex 審計事件（禁 silent fallback）
        weak_events = [p["at_id"] for n, p in spy.events if n == "sdd.weak_regex"]
        assert sorted(weak_events) == ["AT-002-1-2", "AT-003-1-1"]


class TestMultiAcEndToEnd:
    def test_full_chain_six_steps_all_green(self, tmp_path):
        """compile → kernel(真 SddGovernancePlugin) → 6 步全綠、零契約違反。"""
        pb = _compile(tmp_path)
        plugin = SddGovernancePlugin(spec_source=SddToPlaybookAdapter())
        bus = EventBus()
        bus.register(plugin)
        kernel = PlaybookKernel(_MapExecutor(), _RegexOnlyEvaluator(), bus=bus)
        result = kernel.run(pb)
        assert result.success is True
        assert result.completed_steps == 6
        snap = plugin.snapshot()
        assert snap["spec_digest"] and snap["spec_digest"].startswith("sha256:")
        assert snap["contract_violations"] == []

    def test_unfrozen_multi_ac_spec_vetoed_at_pre_run(self, tmp_path):
        """規格先行硬閘攻防：狀態退回 SPEC_DRAFTING → pre_run veto，零步驟執行。"""
        pb = _compile(tmp_path)
        _write_fsm_state(tmp_path, current_state="SPEC_DRAFTING")
        plugin = SddGovernancePlugin(spec_source=SddToPlaybookAdapter())
        bus = EventBus()
        bus.register(plugin)
        kernel = PlaybookKernel(_MapExecutor(), _RegexOnlyEvaluator(), bus=bus)
        result = kernel.run(pb)
        assert result.success is False
        assert any("SDD-VIOLATION[SPEC_NOT_FROZEN]" in r for r in result.veto_reasons)
        assert result.completed_steps == 0
