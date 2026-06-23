"""AutoSDD_improving_56 W-56-1：真實規模**雙向全鏈** e2e（A 軌協作自治 L3→L4 信號）。

既有 test_bridge_multi_ac.py 雖以 3 AC / 6 AT 真實規模壓過**正向**橋接 + SddGovernancePlugin
snapshot，但**逆向**橋接（RtmWritebackPlugin → RtmCoverageReport 覆蓋度報告）至今僅在
test_rtm_writeback_plugin.py 以手構 2-AT 載具單元測試過，**從未在 PlaybookKernel 內以真實
規模 e2e 跑過**——此即 A 軸成熟度評級點名之缺口（「playbook 執行結果回饋→RTM 的反向橋接
未在多 AC 規模下被驗證」）。

本載具補齊：複用 multi_ac 真實規模規格 → sdd_compile CLI → PlaybookKernel（真 SddGovernance
Plugin + 真 RtmWritebackPlugin + 真 PlaybookToRtmAdapter + 捕獲 sink）跑完整正向執行，**並
驗證 kernel POST_RUN 觸發的逆向覆蓋報告**：

  1. 正向 6 步全綠 + 逆向報告 3 AC 全覆蓋 / 6 AT 全通過 / is_fully_covered
  2. **spec_digest 閉環不變量（W-56-2 / DEF-56-001）在 e2e 脈絡成立**：逆向報告帶
     forward adapter 填入之**權威全 "sha256:..." digest**（非 prompt 反解之 8 字元截斷）
  3. 逆向報告於部分覆蓋下正確反映未覆蓋 AC（real-scale，非 happy-path-only 空殼）
"""
from __future__ import annotations

import yaml

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.infra.adapters.playbook_to_rtm_adapter import PlaybookToRtmAdapter
from autoclaude.infra.adapters.sdd_to_playbook_adapter import SddToPlaybookAdapter
from autoclaude.models.playbook import Playbook
from autoclaude.plugins.rtm_writeback_plugin import RtmWritebackPlugin
from autoclaude.plugins.sdd_governance_plugin import SddGovernancePlugin
from autoclaude.tools.sdd_compile import main as sdd_compile_main
from tests.infra.test_sdd_to_playbook_adapter import _write_fsm_state
from tests.integration.test_sdd_bridge.test_bridge_multi_ac import (
    _MapExecutor,
    _RegexOnlyEvaluator,
    _write_multi_ac_spec,
)

_ALL_STEP_IDS = [
    "sdd-brownfield-at-001-1-1", "sdd-brownfield-at-001-1-2",
    "sdd-brownfield-at-001-1-3", "sdd-brownfield-at-002-1-1",
    "sdd-brownfield-at-002-1-2", "sdd-brownfield-at-003-1-1",
]


class _RecordingSink:
    """捕獲逆向橋接寫出的 coverage/gap 報告（e2e 觀測點）。"""

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []
        self.history: list[tuple[str, str]] = []

    def write_report(self, report_name, content, *, fmt="yaml"):
        self.calls.append((report_name, content, fmt))
        return f"/fake/{report_name}.{fmt}"

    def append_report_line(self, report_name, line):
        self.history.append((report_name, line))
        return f"/fake/{report_name}.jsonl"


def _compile(tmp_path) -> Playbook:
    spec_dir = _write_multi_ac_spec(tmp_path)
    _write_fsm_state(tmp_path)  # current_state=IMPLEMENTATION（post-frozen）
    out = tmp_path / "wallet_playbook.yaml"
    rc = sdd_compile_main(["--spec-dir", str(spec_dir), "--out", str(out)])
    assert rc == 0
    return Playbook.model_validate(yaml.safe_load(out.read_text(encoding="utf-8")))


def _wire(spec_source, sink):
    bus = EventBus()
    bus.register(SddGovernancePlugin(spec_source=spec_source))
    bus.register(RtmWritebackPlugin(adapter=PlaybookToRtmAdapter(), sink=sink))
    return bus


class TestBidirectionalChainE2E:
    def test_full_chain_forward_and_reverse_all_green(self, tmp_path):
        """正向 6 步全綠 + kernel POST_RUN 觸發逆向報告：3 AC 全覆蓋、6 AT 全通過。"""
        pb = _compile(tmp_path)
        sink = _RecordingSink()
        bus = _wire(SddToPlaybookAdapter(), sink)
        kernel = PlaybookKernel(_MapExecutor(), _RegexOnlyEvaluator(), bus=bus)
        result = kernel.run(pb)

        # 正向：6 步全綠
        assert result.success is True
        assert result.completed_steps == 6

        # 逆向：kernel POST_RUN 觸發 RtmWritebackPlugin 寫出 coverage + gap 兩報告
        names = [c[0] for c in sink.calls]
        assert names == [f"RTM-COVERAGE-{pb.project}", f"RTM-GAP-{pb.project}"]
        cov = yaml.safe_load(sink.calls[0][1])
        assert cov["summary"]["total_at"] == 6
        assert cov["summary"]["passed_at"] == 6
        assert cov["summary"]["total_ac"] == 3
        assert cov["summary"]["covered_ac"] == 3
        assert cov["summary"]["fully_covered"] is True

    def test_reverse_report_carries_full_authoritative_digest(self, tmp_path):
        """W-56-2 不變量於 e2e：逆向報告帶完整 sha256 digest（非 prompt 反解 8 字元截斷）。"""
        pb = _compile(tmp_path)
        # forward adapter 已對每個 SDD task 填入權威全 digest（結構化欄）
        full_digest = pb.tasks[0].spec_digest
        assert full_digest and full_digest.startswith("sha256:")
        assert len(full_digest) == len("sha256:") + 64  # 完整 64 hex，未截斷

        sink = _RecordingSink()
        bus = _wire(SddToPlaybookAdapter(), sink)
        kernel = PlaybookKernel(_MapExecutor(), _RegexOnlyEvaluator(), bus=bus)
        kernel.run(pb)

        cov = yaml.safe_load(sink.calls[0][1])
        # 不變量：逆向報告 digest == forward 權威全值，非 8 字元 prompt 截斷
        assert cov["spec_digest"] == full_digest
        prompt_digest8 = full_digest.split(":")[-1][:8]
        assert cov["spec_digest"] != prompt_digest8

    def test_reverse_report_reflects_partial_coverage(self, tmp_path):
        """逆向橋接非 happy-path-only 空殼：部分完成時正確標記未覆蓋 AC（real-scale）。

        kernel escalation 路徑依設計不發 POST_RUN（halt/escalate 提前 return），故部分覆蓋
        以「對 wired bus 直接 emit POST_RUN + 真實規格編譯之 tasks + 部分 completed 集」驗證
        逆向橋接覆蓋判定（complete_step_ids 缺 AT-001-1-2 → AC-001-1 不完全覆蓋）。
        """
        pb = _compile(tmp_path)
        sink = _RecordingSink()
        bus = _wire(SddToPlaybookAdapter(), sink)
        # 模擬 AT-001-1-2 未通過：自完成集移除
        partial = [s for s in _ALL_STEP_IDS if s != "sdd-brownfield-at-001-1-2"]
        bus.emit(HookContext(
            phase=KernelPhase.POST_RUN, playbook=pb, task=None,
            payload={"completed_step_ids": partial, "total_steps": len(pb.tasks)},
        ))
        cov = yaml.safe_load(sink.calls[0][1])
        assert cov["summary"]["passed_at"] == 5
        assert cov["summary"]["total_at"] == 6
        assert cov["summary"]["fully_covered"] is False
        # AC-001-1（含 AT-001-1-2）不再全覆蓋；AC-002-1 / AC-003-1 仍全覆蓋
        assert cov["summary"]["covered_ac"] == 2
        assert "AT-001-1-2" in cov["failed_at_ids"]
