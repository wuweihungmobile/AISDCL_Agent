"""DEF-200-518：CheckpointPlugin 的 ON_ESCALATION_DUMP_REQUEST 處理器必須能服務 Kernel 的 payload。

修前處理器只認 payload["tracker"]（execution/ 的 FailureTracker）與明確的 checkpoint_dir；
Kernel（core/，不得 import execution/）只能送 failure_history（list[dict]）。驗證意圖（Rule 9）：
(1) 只給 failure_history 也產出真檔，並把 dump 物件隨路徑一併回傳（給下游 EvolutionPlugin）；
(2) 沒帶 checkpoint_dir 時落在 plugin 自己的 CheckpointManager 目錄，而不是 cwd；
(3) dump 的自動診斷（is_stuck 等）由 eval_output 現算簽名後判斷，不得讀 error_signature 鍵。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from autoclaude.core.hookspec import EscalationDumpedResult, HookContext, KernelPhase
from autoclaude.models.escalation import EscalationDump
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.checkpoint import CheckpointPlugin
from autoclaude.utils.checkpoint_manager import CheckpointManager

_HISTORY = [
    {"attempt": 0, "failure_reason": "r0", "eval_output": "boom A", "exit_code": 1},
    {"attempt": 1, "failure_reason": "r1", "eval_output": "boom B", "exit_code": 1},
]
_SAME_SIGNATURE_HISTORY = [
    {"attempt": 0, "failure_reason": "r0", "eval_output": "boom A", "exit_code": 1},
    {"attempt": 1, "failure_reason": "r1", "eval_output": "boom A", "exit_code": 1},
]


def _ctx(payload):
    task = PlaybookTask(step_id="T01", name="n", prompt="p")
    pb = Playbook(version="1.0", project="P", global_invariants=GlobalInvariants(), tasks=[task])
    return HookContext(phase=KernelPhase.ON_ESCALATION_DUMP_REQUEST, playbook=pb,
                       task=task, step_idx=0, payload=payload)


def _plugin(tmp_path):
    return CheckpointPlugin(checkpoint_manager=CheckpointManager(checkpoint_dir=str(tmp_path)))


def test_failure_history_only_payload_produces_a_real_dump_and_returns_the_object(tmp_path):
    result = _plugin(tmp_path).on_event(
        _ctx({"failure_history": _HISTORY, "human_hint": "hint", "final_eval_output": "boom B"}))

    assert isinstance(result, EscalationDumpedResult)
    assert Path(result.dump_path).is_file() and Path(result.dump_path).parent == tmp_path
    assert isinstance(result.dump, EscalationDump)
    assert result.dump.total_attempts == 2 and result.dump.step_id == "T01"
    assert [r["attempt"] for r in result.dump.failure_chain] == [0, 1]
    assert result.dump.human_hint == "hint"


@pytest.mark.parametrize("history,expected_stuck", [
    (_HISTORY, False),
    (_SAME_SIGNATURE_HISTORY, True),
], ids=["different_signatures", "same_signature"])
def test_dump_diagnostics_are_computed_from_the_real_eval_output(tmp_path, history, expected_stuck):
    """is_stuck 必須由 eval_output 現算簽名後判斷：異簽名 ⇒ False、同簽名 ⇒ True。

    WHY：Kernel 的 failure_history 只有 attempt／failure_reason／eval_output／exit_code，沒有
    error_signature。重建 tracker 若改走 `FailureTracker.from_records()`（它讀 error_signature
    鍵），簽名全空 ⇒ is_stuck 對任何歷史都恆為 True，dump 會對每一次 Kernel 升級印
    「錯誤卡死（是）」，人照錯的診斷去修（QA 突變 Q11a；SA 設計 §3.2 點名的陷阱）。
    """
    result = _plugin(tmp_path).on_event(_ctx({"failure_history": history}))

    assert [r["error_signature"] for r in result.dump.failure_chain] == [
        h["eval_output"] for h in history]
    assert result.dump.is_stuck is expected_stuck


def test_missing_checkpoint_dir_never_falls_back_to_cwd(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    managed = tmp_path / "managed"
    monkeypatch.chdir(cwd)
    result = _plugin(managed).on_event(_ctx({"failure_history": _HISTORY}))

    assert Path(result.dump_path).parent == managed
    assert list(cwd.iterdir()) == []


def test_neither_tracker_nor_history_is_still_ignored(tmp_path):
    assert _plugin(tmp_path).on_event(_ctx({})) is None
    assert list(tmp_path.iterdir()) == []


_PLACEHOLDER = "python -m autoclaude <playbook.yaml> --config <config.yaml>"


def test_kernel_payload_dump_file_says_unknown_instead_of_blank_or_guessed_fields(tmp_path):
    """OBS-SI-193：Kernel 的 payload 沒有 playbook_path／log_dir（Kernel 是純 DAG，不持有）。

    修前落盤檔四處不精確：`**Playbook**:` 空白、`## 繼續執行指令` 是 `autoclaude ""`、
    `## 最後執行 Log` 是相對檔名 `playbook_T01_attempt1.log`（Kernel 執行器實際寫的是
    `playbook_{step_id}.log`，且目錄根本不明）、「從 checkpoint 繼續」措辭（ESCALATION 不存
    checkpoint）。用同簽名歷史讓 is_stuck 為真，才會走到清單裡的 `cat <log>` 分支。
    """
    result = _plugin(tmp_path).on_event(_ctx({"failure_history": _SAME_SIGNATURE_HISTORY}))
    md = Path(result.dump_path).read_text(encoding="utf-8")

    assert "錯誤卡死（特徵相同）: ✅ 是" in md          # 對照：stuck 分支確實被走到
    assert "**Playbook**: （Kernel 路徑未記錄 playbook 路徑）" in md
    assert "## 最後執行 Log\n未取得" in md
    assert _PLACEHOLDER in md and "Kernel 路徑由呼叫端持有 playbook 路徑" in md
    for forbidden in ('autoclaude ""', "cat ''", "playbook_T01_attempt", "從 checkpoint 繼續"):
        assert forbidden not in md, f"{forbidden!r} 不得出現在 Kernel 路徑 dump：\n{md}"


def test_payload_with_explicit_playbook_and_log_dir_keeps_the_real_values(tmp_path):
    """正控：呼叫端確實給了路徑（舊 facade 路徑）時，三處照舊印真值，不被「未取得」取代。"""
    logs = tmp_path / "logs"
    payload = {"failure_history": _SAME_SIGNATURE_HISTORY, "playbook_path": "pb.yaml",
               "log_dir": str(logs)}
    result = _plugin(tmp_path).on_event(_ctx(payload))
    md = Path(result.dump_path).read_text(encoding="utf-8")

    assert "**Playbook**: pb.yaml" in md
    assert f"`{logs / 'playbook_T01_attempt1.log'}`" in md
    assert md.count('autoclaude "pb.yaml"') == 2          # 接手清單＋「## 繼續執行指令」
    assert _PLACEHOLDER not in md and "未取得" not in md
