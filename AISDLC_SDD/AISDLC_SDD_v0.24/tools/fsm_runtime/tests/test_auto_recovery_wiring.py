# enforces (governance rules): R-9.14, R-9.5
"""improving_15 / W-15-1 — B-axis L4：auto_recovery 接入 FSM 主迴圈閉環測試。

驗證把既有 enter_auto_recovery（ESCALATION → AUTO_RECOVERY_ATTEMPT，Rule 9.14 有界、
TLA T_EnterAutoRecover 已模型化）從「proposal-only 需手動觸發」升級為「record_gate_result
於 gate retry 耗盡時自動嘗試」後，B 軸流程自治由 L3（失敗即停等人）升 L4（自動有界恢復）：

  - flag OFF（預設）→ 行為同 v0.05：escalate 後停在 ESCALATION，無 auto_recovery（零退化）
  - flag ON + transient 失敗 → 自動進 AUTO_RECOVERY_ATTEMPT；exit success → 回 resume gate（閉環自走）
  - flag ON + structural 失敗 → 拒絕 → ESCALATION_FINAL（Rule 9.14.3 紅線守界）
  - flag ON + bounds 耗盡（同 session ≥3）→ 拒絕 → ESCALATION_FINAL（Rule 9.14.1）
  - auto_recovery_stats L4 可量測信號（成功率 / 無人工恢復率）
  - _gate_is_resumable 預檢（防撕裂轉態）
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import (  # noqa: E402
    _AUTO_RECOVERY_ENV,
    _auto_recovery_enabled,
    FSMRuntime,
)
from tools.fsm_runtime.state_loader import load_state  # noqa: E402


def _drive_gate_to_escalation(rt: FSMRuntime, gate: str, limit: int, reason: str) -> dict:
    """以 FAIL 連續驅動 gate 至 retry 耗盡，回傳最後一次 escalate=True 的 payload。"""
    payload: dict = {}
    for _ in range(limit + 1):
        rt.state.current = gate
        payload = rt.record_gate_result(gate, "FAIL", reason=reason)
        if payload.get("escalated"):
            break
    return payload


class _Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.state_path = Path(self._td.name) / "FSM-STATE-w151.yaml"
        # 確保每測乾淨環境變數
        self._prev_env = None  # set by helpers

    def tearDown(self):
        self._td.cleanup()

    def _rt(self) -> FSMRuntime:
        return FSMRuntime(load_state("w151-proj", path=self.state_path))


class DefaultOnNormalizationTests(_Base):
    """v0.22 / improving_57 B 軌：AUTO_RECOVERY 常態化（預設 ON，B-axis L3→L4）。"""

    def test_default_unset_now_enters_recovery(self):
        """v0.22 預設（未設環境變數）→ ON：transient escalate 自動進 AUTO_RECOVERY_ATTEMPT。"""
        import os
        os.environ.pop(_AUTO_RECOVERY_ENV, None)
        self.assertTrue(_auto_recovery_enabled())  # v0.22：unset → ON
        rt = self._rt()
        payload = _drive_gate_to_escalation(rt, "RTM_VERIFY", 2, "CI runner timeout 30s")
        self.assertTrue(payload.get("escalated"))
        self.assertIn("auto_recovery", payload)
        self.assertTrue(payload["auto_recovery"]["entered"])
        self.assertEqual(rt.state.current, "AUTO_RECOVERY_ATTEMPT")

    def test_explicit_optout_stays_escalation(self):
        """顯式 opt-out（SDD_ENABLE_AUTO_RECOVERY=0）→ 還原 v0.05 停機行為（保留逃生口）。"""
        import os
        os.environ[_AUTO_RECOVERY_ENV] = "0"
        try:
            self.assertFalse(_auto_recovery_enabled())  # 顯式 falsy → OFF
            rt = self._rt()
            payload = _drive_gate_to_escalation(rt, "RTM_VERIFY", 2, "CI runner timeout 30s")
            self.assertTrue(payload.get("escalated"))
            self.assertEqual(rt.state.current, "ESCALATION")
            self.assertNotIn("auto_recovery", payload)
        finally:
            os.environ.pop(_AUTO_RECOVERY_ENV, None)


class FlagOnClosedLoopTests(_Base):
    def setUp(self):
        super().setUp()
        import os
        os.environ[_AUTO_RECOVERY_ENV] = "1"

    def tearDown(self):
        import os
        os.environ.pop(_AUTO_RECOVERY_ENV, None)
        super().tearDown()

    def test_flag_on_transient_auto_enters_recovery(self):
        """flag ON + transient → 自動進 AUTO_RECOVERY_ATTEMPT（不再停在 ESCALATION 等人）。"""
        self.assertTrue(_auto_recovery_enabled())
        rt = self._rt()
        payload = _drive_gate_to_escalation(rt, "RTM_VERIFY", 2, "CI runner timeout 30s")
        self.assertTrue(payload.get("escalated"))
        self.assertIn("auto_recovery", payload)
        self.assertTrue(payload["auto_recovery"]["entered"])
        self.assertEqual(rt.state.current, "AUTO_RECOVERY_ATTEMPT")
        self.assertEqual(payload["auto_recovery"]["resume_state"], "RTM_VERIFY")

    def test_full_closed_loop_success_resumes_gate(self):
        """完整閉環：自動進 recovery → exit success → 回 resume gate（自走、無人工）。"""
        rt = self._rt()
        _drive_gate_to_escalation(rt, "SCG_VALIDATION", 3, "CI runner timeout 30s")
        self.assertEqual(rt.state.current, "AUTO_RECOVERY_ATTEMPT")
        out = rt.exit_auto_recovery("success")
        self.assertEqual(out["outcome"], "success")
        self.assertEqual(rt.state.current, "SCG_VALIDATION")
        # L4 信號：一次成功自動恢復
        stats = rt.auto_recovery_stats()
        self.assertEqual(stats["attempts"], 1)
        self.assertEqual(stats["successes"], 1)
        self.assertEqual(stats["recovery_success_rate"], 1.0)

    def test_structural_failure_refused_to_final(self):
        """flag ON + structural 失敗 → 拒絕 → ESCALATION_FINAL（Rule 9.14.3 紅線）。"""
        rt = self._rt()
        payload = _drive_gate_to_escalation(rt, "RTM_VERIFY", 2, "SLV-005 FAIL on AC-015")
        self.assertIn("auto_recovery", payload)
        self.assertFalse(payload["auto_recovery"]["entered"])
        self.assertEqual(payload["auto_recovery"]["next_state"], "ESCALATION_FINAL")
        self.assertEqual(rt.state.current, "ESCALATION_FINAL")
        self.assertIn("9.14.3", payload["auto_recovery"]["refusal_reason"])

    def test_bounds_exhausted_refused_to_final(self):
        """同 session 已 3 次 attempt → bounds 耗盡 → 拒絕 → ESCALATION_FINAL（Rule 9.14.1）。"""
        rt = self._rt()
        # 預先把 session_attempt_count 灌到上限（模擬先前已用盡）
        rs = rt.state.root.setdefault("recovery_state", {})
        rs["session_attempt_count"] = 3
        rs.setdefault("per_reason_count", {})
        rs.setdefault("current", None)
        rs.setdefault("history", [])
        payload = _drive_gate_to_escalation(rt, "RTM_VERIFY", 2, "CI runner timeout 30s")
        self.assertIn("auto_recovery", payload)
        self.assertFalse(payload["auto_recovery"]["entered"])
        self.assertEqual(rt.state.current, "ESCALATION_FINAL")
        self.assertIn("9.14.1", payload["auto_recovery"]["refusal_reason"])

    def test_recovery_fail_goes_to_final(self):
        """進 recovery 後 exit fail → ESCALATION_FINAL（Rule 9.14.4，不可再恢復）。"""
        rt = self._rt()
        _drive_gate_to_escalation(rt, "SCG_VALIDATION", 3, "CI runner timeout 30s")
        self.assertEqual(rt.state.current, "AUTO_RECOVERY_ATTEMPT")
        out = rt.exit_auto_recovery("fail")
        self.assertEqual(rt.state.current, "ESCALATION_FINAL")
        stats = rt.auto_recovery_stats()
        self.assertEqual(stats["failures"], 1)
        self.assertEqual(stats["recovery_success_rate"], 0.0)


class GateResumableGuardTests(_Base):
    def test_gate_is_resumable_covers_all_retry_gates(self):
        """RETRY_LIMITS 4 gate 全為合法 resume_state（預檢不誤拒）。"""
        from tools.fsm_runtime.transition_rules import RETRY_LIMITS
        for gate in RETRY_LIMITS:
            self.assertTrue(
                FSMRuntime._gate_is_resumable(gate),
                f"gate {gate} 應為合法 resume_state",
            )

    def test_non_resumable_gate_rejected(self):
        """非白名單字串不被視為可恢復（防撕裂轉態的預檢）。"""
        self.assertFalse(FSMRuntime._gate_is_resumable("RELEASE"))
        self.assertFalse(FSMRuntime._gate_is_resumable("INIT"))


class StatsEmptyTests(_Base):
    def test_stats_empty_session_zero_rates(self):
        """無任何 attempt 時統計回零率（不除零）。"""
        rt = self._rt()
        stats = rt.auto_recovery_stats()
        self.assertEqual(stats["attempts"], 0)
        self.assertEqual(stats["recovery_success_rate"], 0.0)
        self.assertEqual(stats["unattended_recovery_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
