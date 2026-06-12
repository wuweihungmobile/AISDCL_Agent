"""tests/contract/test_runner_no_checkpoint_logic.py — AC2-1 / SD_06 W2-T2-14 契約。

對應：
  - SD_Improving_06.md v1.2 §6.5 AC2-1（`grep -c "_save_.*_checkpoint" autoclaude/execution/_runner_internals.py == 0`）
  - SD_Improving_06.md v1.2 §7 ❌13（mixin/plugin 雙寫法絕對禁止）
  - SD06_Execution_Guide.md W2 T2-14（importlinter 新增 runner-no-checkpoint-logic）

說明：
  importlinter 本身僅能管理 module-level import 圖，無法 grep 函式名稱。
  本 contract 以「字串掃描」形式 enforce W2 末期應達到的「mixin 內無 _save_*_checkpoint
  logic」目標。

W2 進行中允許階段性通過：
  - 階段 1（current）：mixin 仍持有 shim def + 內部呼叫端；measure_only=True
  - 階段 2（_run_steps / _apply_single_mutation_full 完成下沉後）：呼叫端歸零
  - 階段 3（mixin shim def 物理刪除後，T2-9~T2-11 完成）：grep == 0 才放行 G2

階段切換以環境變數 SD06_W2_PHASE 控制；CI G2 gate 階段須設定 SD06_W2_PHASE=3 強制。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest


_RUNNER_INTERNALS = Path(__file__).resolve().parents[2] / "autoclaude" / "execution" / "_runner_internals.py"
_PATTERN = re.compile(r"_save_.*_checkpoint")


def _count_matches() -> int:
    if not _RUNNER_INTERNALS.exists():
        return 0
    text = _RUNNER_INTERNALS.read_text(encoding="utf-8")
    return len(_PATTERN.findall(text))


def _phase() -> int:
    return int(os.environ.get("SD06_W2_PHASE", "1"))


class TestRunnerNoCheckpointLogicContract:
    """SD_06 W2 完成 — phase 3 自動啟用為預設（G2 gate）。"""

    def test_g2_gate_no_checkpoint_logic_in_mixin(self):
        """G2 gate 強制：`_runner_internals.py` 內 `_save_.*_checkpoint` == 0。

        達成方式（SD_06 W2 T2-9~T2-11）：
          - mixin `_save_evolution_resume_checkpoint` def 物理刪除（測試改呼叫 plugin 公開 API）
          - mixin `_save_interrupt_checkpoint` def 物理刪除（測試改呼叫 plugin 公開 API）
          - mixin `_save_escalation_dump` 改名/下沉至 escalation_dumper（保留 shim 但無 _checkpoint 後綴）
          - docstring 與 MIGRATED 注解清理
        """
        count = _count_matches()
        assert count == 0, (
            f"G2 gate 要求 _runner_internals.py 內 `_save_.*_checkpoint` == 0；實際 {count}。"
            f"mixin shim 必須物理刪除，呼叫端改 self._checkpoint_plugin.<method>。"
        )

    def test_grep_pattern_baseline_recorded(self):
        """W2 末 baseline = 0（W1 末 baseline 為 11；T2-9~T2-11 降至 0）。"""
        count = _count_matches()
        assert count == 0, f"W2 末 baseline 已 = 0；當前 {count}"

    def test_phase_legacy_marker_for_w3_regression_guard(self):
        """SD06_W2_PHASE 環境變數保留為後續 wave 退化保護：W3+ 若有人新增 mixin
        checkpoint logic 將立即被本 contract 抓出（因 G2 baseline 已 = 0）。
        """
        # phase 環境變數現在僅作為 W3+ regression guard 標記用途
        _phase()  # 確認可解析無錯
