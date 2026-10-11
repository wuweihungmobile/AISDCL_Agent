"""DEF-200-518 端到端：真 build_kernel（真 plugin 全組）＋假 executor/evaluator。

不呼叫 claude 即可重現 F-SBR-001 的 C4 型 ESCALATION：同一個失敗特徵碼連續 2 次 →
ConvergencePlugin 要求升級（遠早於 max_retries）。驗證意圖（Rule 9）：使用者真正看得到的
三樣東西——checkpoint 目錄裡的 EscalationDump、通知（含 escalation_alert.log）、演化提案——
在 Kernel 路徑上真的產生；而且 dump 一定落在 checkpoint_dir，絕不落進 cwd。
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.core.wiring import build_kernel
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.utils.config import AppConfig


class _Exec:
    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        return ExecutionOutput(text="done")


class _SameSignatureEval:
    """C4 形態：每次都回同一組 (原因, eval_output, exit_code)＝同特徵碼。"""

    def evaluate(self, task, output):
        return ("評估指令失敗 (exit=5): pytest tests -k AT_001", "1 deselected in 0.06s", 5)


class _DistinctEval:
    """每次特徵碼都不同、exit_code 不遞增 ⇒ 收斂評估不會介入，只剩 retry 用盡。"""

    def __init__(self):
        self.n = 0

    def evaluate(self, task, output):
        self.n += 1
        return f"fail #{self.n}", f"unique error body {self.n} " + "x" * (self.n * 7), 1


class _TestFileBrokenEval:
    """錯誤始終指向測試檔本身（SyntaxError）⇒ suspect_test_file → 規則引擎有提案。"""

    def evaluate(self, task, output):
        out = "FAILED tests/test_foo.py - SyntaxError: invalid syntax"
        return ("評估指令失敗 (exit=2)", out, 2)


class _Pass:
    def evaluate(self, task, output):
        return None, "", 0


def _pb(max_retries: int) -> Playbook:
    return Playbook(
        version="1.0", project="esc-e2e",
        global_invariants=GlobalInvariants(max_retries_per_step=max_retries),
        tasks=[PlaybookTask(step_id="T01", name="step", prompt="do")],
    )


def _cfg(tmp_path: Path, *, notify: bool = False) -> AppConfig:
    cfg = AppConfig()
    cfg.checkpoint_dir = str(tmp_path / "checkpoints")
    cfg.log_dir = str(tmp_path / "logs")
    cfg.notification.enabled = notify
    return cfg


def _dumps(cfg: AppConfig) -> list[Path]:
    return sorted(Path(cfg.checkpoint_dir).glob("escalation_T01_*.md"))


def test_c4_shape_escalation_leaves_a_dump_under_checkpoint_dir(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)                  # 抓「空字串目錄＝寫進 cwd」這個陷阱
    cfg = _cfg(tmp_path)
    kernel = build_kernel(cfg, executor=_Exec(), evaluator=_SameSignatureEval())

    result = kernel.run(_pb(max_retries=5))

    assert result.escalated is True and result.reason.startswith("[T01] ")  # max_retries=5 之前
    dumps = _dumps(cfg)
    assert len(dumps) == 1, f"checkpoint_dir 應有恰 1 份 dump，實得 {dumps}"
    md = dumps[0].read_text(encoding="utf-8")
    assert "## 失敗鏈" in md and "1 deselected" in md and "T01" in md
    assert list(elsewhere.iterdir()) == [], "dump 不得落進 cwd"


def test_notification_enabled_alert_log_points_at_the_dump(tmp_path):
    cfg = _cfg(tmp_path, notify=True)
    with patch("autoclaude.utils.notifier._deliver"):          # 不真的彈窗
        kernel = build_kernel(cfg, executor=_Exec(), evaluator=_DistinctEval())
        result = kernel.run(_pb(max_retries=1))

    assert "max_retries_exhausted" in result.reason
    (dump,) = _dumps(cfg)
    alert = (Path(cfg.checkpoint_dir) / "escalation_alert.log").read_text(encoding="utf-8")
    assert f"dump={dump}" in alert, "dump 路徑必須由發布者轉交給通知（先 dump 後廣播）"


def test_notification_disabled_keeps_the_dump_but_writes_no_alert_log(tmp_path):
    """釘住裁決 D-2a：沿用 R84 語意（plugin 關 ⇒ 不碰 escalation_alert.log）；dump 檔照寫。
    若掌舵者改裁 D-2b（關閉時仍寫稽核檔），本測與 R84 鎖
    test_escalation_with_dump_path_stays_quiet_even_if_config_says_yes 的最後一個斷言一起反轉。"""
    cfg = _cfg(tmp_path, notify=False)
    kernel = build_kernel(cfg, executor=_Exec(), evaluator=_DistinctEval())
    kernel.run(_pb(max_retries=1))
    assert len(_dumps(cfg)) == 1
    assert not (Path(cfg.checkpoint_dir) / "escalation_alert.log").exists()


def test_rule_engine_proposal_is_logged_not_applied(tmp_path, caplog):
    cfg = _cfg(tmp_path)
    kernel = build_kernel(cfg, executor=_Exec(), evaluator=_TestFileBrokenEval())  # 無 minimax
    pb = _pb(max_retries=5)
    with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
        result = kernel.run(pb)

    assert result.escalated is True
    assert "=== EVOLUTION PROPOSAL | [T01] type=INJECT_BEFORE" in caplog.text
    assert [t.step_id for t in pb.tasks] == ["T01"], "提案不得被套用"
    assert result.evolved_playbook_path is None
    assert not list(tmp_path.rglob("*.mutated.yaml")), "不得產出演化版 playbook"


def test_successful_run_leaves_no_escalation_artifacts(tmp_path):
    cfg = _cfg(tmp_path)
    kernel = build_kernel(cfg, executor=_Exec(), evaluator=_Pass())
    assert kernel.run(_pb(max_retries=1)).success is True
    assert _dumps(cfg) == []
    assert not (Path(cfg.checkpoint_dir) / "escalation_alert.log").exists()
