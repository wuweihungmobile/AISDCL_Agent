# enforces (governance rules): R-9.5, R-9.15, R-9.19, R-9.24
"""DEF-200-275 第六輪複審 ARCH-R6-01 回歸鎖。

WHY：D17 裁決要求「每一處寫入 ESCALATION 的站點都落一筆 escalation_provenance」，但第六輪複審
（ARCH-R6-01）抓到 fsm_runtime.py 仍有 4 個函式（exit_learning_commit 兩分支／
exit_trajectory_predicted 的 abort_early／record_dispatch_rejection／exit_autoclaude_delegated
的 failed）直接呼叫 self.transition("ESCALATION", ...) 繞過 record_escalation()，導致新視窗看到
的是前一次（可能已解決）事件的舊溯源——比 D17 修之前更誤導（舊版至少誠實模糊，新版會自信地講
錯話）。本檔驗證：

  (a) 寫入面：把 Architect 的重現改寫成回歸測試——舊 session 的 escalation 被人工 resume 解決
      後，經由其中一個此前繞過的函式（record_dispatch_rejection）再次真實觸發 ESCALATION，
      recovery_hint() 的溯源必須是本次事件，不得殘留舊原因。
  (b) 靜態鎖：fsm_runtime.py 不得再出現「轉態 ESCALATION 但未先呼叫 record_escalation()」的
      殘留站點（涵蓋字面 self.transition("ESCALATION", ...) 與 target 變數兩種形態）。
  (c) 4 個函式各自的 provenance 斷言（rule_id／source 與本輪修法一致）。
  (d) 讀取面陳舊防呆（第二道防線）：即使寫入面已修好，provenance 早於『本次轉入 ESCALATION』
      時仍需印「溯源不可信」，且不得把舊原因餵進恢復指令的 --reason（防未來新繞過站點／state
      遭手動竄改）。
"""
from __future__ import annotations

import datetime as _dt
import inspect
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import recovery_hint as rh  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402

_SDD_ROOT = Path(__file__).resolve().parents[3]
_FSM_RUNTIME_SRC = Path(__file__).resolve().parents[1] / "fsm_runtime.py"


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.state_path = self.tmp / "FSM-STATE-r6.yaml"
        self.state = load_state("r6-arch01", path=self.state_path)
        self.rt = FSMRuntime(self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# (a) Architect 重現：舊 session 已解決事件 → 全新原因再度觸發 ESCALATION →
#     recovery_hint() 不得殘留舊原因。
# ---------------------------------------------------------------------------


class ReproArchR601StaleAfterResumeTests(_Base):
    def test_dispatch_rejection_after_resume_does_not_leak_old_provenance(self) -> None:
        # (1) 舊事件：session OLD 因與本次完全無關的原因寫入 ESCALATION。
        self.state.record_escalation(
            "TOKEN_BUDGET_CRITICAL: used=950000 (stale, unrelated)",
            details={"session_id": "OLD-SESSION-XYZ"},
            rule_id="R-9.2", source="context_budget_stale",
        )
        self.assertEqual(self.state.current, "ESCALATION")
        # (2) 人工 resume 解決（模擬真人已處理完舊事件）。
        res = self.rt.resume_from_escalation(to="SPEC_DRAFTING", reason="manual resume, resolved")
        self.assertEqual(res["to"], "SPEC_DRAFTING")
        self.assertEqual(self.state.current, "SPEC_DRAFTING")
        # (3) 全新、無關原因：連續三次 dispatch rejection（Rule 9.19.3；此前是繞過站點之一）。
        for _ in range(2):
            res = self.rt.record_dispatch_rejection(reason="budget_exhausted")
            self.assertFalse(res["escalated"])
        res = self.rt.record_dispatch_rejection(reason="budget_exhausted")
        self.assertTrue(res["escalated"])
        self.assertEqual(self.state.current, "ESCALATION")

        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, python="/venv/bin/python",
                                caller_session_id="NEW-SESSION-ABC")
        self.assertNotIn("OLD-SESSION-XYZ", text)
        self.assertNotIn("TOKEN_BUDGET_CRITICAL: used=950000", text)
        self.assertIn("Rule 9.19.3", text)
        self.assertIn("consecutive dispatch rejections", text)
        self.assertNotIn("溯源不可信", text, "寫入面已修好，本情境不該觸發讀取面陳舊防呆")


# ---------------------------------------------------------------------------
# (b) 靜態鎖：fsm_runtime.py 不得再出現繞過 record_escalation() 的 ESCALATION 轉態站點。
# ---------------------------------------------------------------------------


class NoOrphanedEscalationTransitionSiteTests(unittest.TestCase):
    _VARIABLE_TARGET_FUNCS = (
        "exit_learning_commit", "exit_trajectory_predicted", "exit_autoclaude_delegated",
    )

    def test_variable_target_functions_guard_escalation_branch(self) -> None:
        """target 變數形態（target 可能是 ESCALATION 也可能不是）：函式原始碼裡必須看得到
        `if target == "ESCALATION"` 守衛下的 record_escalation() 呼叫。"""
        for name in self._VARIABLE_TARGET_FUNCS:
            src = inspect.getsource(getattr(FSMRuntime, name))
            self.assertIn(
                "record_escalation(", src,
                f"{name}() 仍未在導向 ESCALATION 前呼叫 record_escalation()（ARCH-R6-01 殘留）",
            )
            self.assertIn(
                'if target == "ESCALATION"', src,
                f'{name}() 應以 target=="ESCALATION" 守衛 record_escalation 呼叫',
            )

    def test_literal_transition_to_escalation_sites_are_all_preceded_by_record_escalation(self) -> None:
        """字面形態（self.transition(\\n    "ESCALATION", ...)）：往回找同一函式邊界內最近的
        record_escalation( 呼叫，必須找得到。"""
        text = _FSM_RUNTIME_SRC.read_text(encoding="utf-8")
        lines = text.splitlines()
        hits = []
        for i, line in enumerate(lines):
            if line.strip() == '"ESCALATION",' and i > 0 and lines[i - 1].strip() == "self.transition(":
                hits.append(i + 1)  # 1-indexed，供錯誤訊息定位
        # 已知合法站點：sandbox_hardening／monitor_violation／spec_patch_limit（既有）＋
        # record_dispatch_rejection（本輪新修）。判準本身要能找到東西，否則判準失效不自知。
        self.assertGreaterEqual(
            len(hits), 4,
            "預期至少 4 個字面 self.transition(\"ESCALATION\" 站點——判準本身可能失效",
        )
        for line_no in hits:
            func_start = 0
            for j in range(line_no - 2, -1, -1):
                if re.match(r"^    def ", lines[j]):
                    func_start = j
                    break
            preceding = "\n".join(lines[func_start:line_no])
            self.assertIn(
                "record_escalation(", preceding,
                f'fsm_runtime.py 第 {line_no} 行的 self.transition("ESCALATION" 站點前未見 '
                "record_escalation() 呼叫（ARCH-R6-01 殘留繞過站點）",
            )

    def test_grep_transition_escalation_literal_has_no_bare_code_hits(self) -> None:
        """對照 Architect 覆核指令 `grep -n 'transition("ESCALATION' fsm_runtime.py`：本輪修復後
        程式碼行（非註解）不應再有單行字面 self.transition("ESCALATION 殘留——現行寫法一律把
        "ESCALATION" 放在 self.transition( 的下一行，故這個單行字面 grep 只會命中說明性註解。"""
        text = _FSM_RUNTIME_SRC.read_text(encoding="utf-8")
        code_hits = [
            line for line in text.splitlines()
            if 'transition("ESCALATION' in line and not line.strip().startswith("#")
        ]
        self.assertEqual(
            code_hits, [],
            "fsm_runtime.py 仍有單行字面 self.transition(\"ESCALATION\" 直呼殘留",
        )


# ---------------------------------------------------------------------------
# (c) 4 個函式各自的 provenance 斷言（rule_id／source）。
# ---------------------------------------------------------------------------


class DispatchRejectionProvenanceTests(_Base):
    def test_record_dispatch_rejection_writes_provenance(self) -> None:
        for _ in range(2):
            self.rt.record_dispatch_rejection(reason="budget_exhausted")
        res = self.rt.record_dispatch_rejection(reason="budget_exhausted")
        self.assertTrue(res["escalated"])
        prov = self.state.root["escalation_provenance"]
        self.assertEqual(prov["rule_id"], "R-9.19.3")
        self.assertEqual(prov["source"], "cost_gate_escalation")
        self.assertIn("consecutive dispatch rejections", prov["reason"])
        self.assertEqual(prov["reason"], self.state.root["escalation_history"][-1]["trigger_reason"])


class TrajectoryPredictedAbortEarlyProvenanceTests(_Base):
    def test_abort_early_writes_provenance(self) -> None:
        self.state.root["current_state"] = "PR_REVIEW"
        save_state(self.state)
        self.rt.enter_trajectory_predicted(
            predicted_action={
                "decision": "abort_early", "confidence": 0.9,
                "signals_triggered": ["S1", "S2", "S3"], "rationale": "3 signals",
                "next_state_hint": "ESCALATION", "gate": "PR_REVIEW",
            },
            gate="PR_REVIEW",
        )
        res = self.rt.exit_trajectory_predicted("abort_early", reason="confidence 0.9 abort")
        self.assertEqual(res["to"], "ESCALATION")
        prov = self.state.root["escalation_provenance"]
        self.assertEqual(prov["rule_id"], "R-9.15.2")
        self.assertEqual(prov["source"], "trajectory_predicted_abort_early")
        self.assertEqual(prov["reason"], "confidence 0.9 abort")


class LearningCommitRejectedProvenanceTests(_Base):
    def test_rejected_writes_provenance_without_rule_id(self) -> None:
        self.state.root["current_state"] = "RELEASE"
        save_state(self.state)
        self.rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-900")
        res = self.rt.exit_learning_commit("rejected", reason="reviewer rejected: incomplete evidence")
        self.assertEqual(res["to"], "ESCALATION")
        prov = self.state.root["escalation_provenance"]
        self.assertEqual(prov["rule_id"], "unknown")
        self.assertEqual(prov["source"], "learning_review_rejected")
        self.assertEqual(prov["reason"], "reviewer rejected: incomplete evidence")


class LearningCommitMetaHaltProvenanceTests(_Base):
    """meta_halt ChurnBounded 攔截分支——與 test_meta_halt.py::
    test_wiring_churn_jitter_routes_to_escalation 同一情境建構手法，改斷言
    escalation_provenance（該既有測試只驗 res["meta_halt"]，不驗 provenance）。"""

    def _verified_rule_fixture(self, slv_id: str) -> Path:
        import yaml as _yaml
        target = self.tmp / f"{slv_id}.yaml"
        doc = {
            "id": slv_id, "name": "fixture verified rule",
            "source": "FPL-001 auto-generated 2026-04-24", "trust_level": "verified",
            "reviewed_by": "reviewer@example.com", "reviewed_at": "2026-04-24",
            "scope": "temporal", "purpose": "test fixture",
            "scan_targets": ["docs/01_requirements/FRD-*.md"],
            "required_qualifiers": ["必須不為空"], "failure_examples": [], "pass_examples": [],
            "severity": "CRITICAL", "blocks_scg": True, "source_fpl": "FPL-001",
        }
        target.write_text(_yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return target

    def test_churn_bound_exceeded_writes_provenance(self) -> None:
        from tools.fsm_runtime.meta_halt import meta_ledger as L
        ledger = self.tmp / "meta-loop-ledger.yaml"
        with patch.dict(os.environ, {"SDD_META_CHURN_MAX": "2", "SDD_META_LEDGER_PATH": str(ledger)}):
            fp = L.fingerprint_of("fixture verified rule temporal test fixture")
            L.record_event(L.EVENT_ADD, "SLV-a", fingerprint=fp, capability_level=0, ledger_path=ledger)
            L.record_event(L.EVENT_RETIRE, "SLV-a", fingerprint=fp, capability_level=0, ledger_path=ledger)
            L.record_event(L.EVENT_ADD, "SLV-b", fingerprint=fp, capability_level=1, ledger_path=ledger)
            L.record_event(L.EVENT_RETIRE, "SLV-b", fingerprint=fp, capability_level=1, ledger_path=ledger)
            L.record_event(L.EVENT_ADD, "SLV-c", fingerprint=fp, capability_level=2, ledger_path=ledger)
            L.record_event(L.EVENT_RETIRE, "SLV-c", fingerprint=fp, capability_level=2, ledger_path=ledger)
            self.assertEqual(L.compute_churn(fp, ledger_path=ledger), 2)

            self.state.root["current_state"] = "RELEASE"
            save_state(self.state)
            rule_path = self._verified_rule_fixture("SLV-777")  # 同語意 → 同指紋（換皮重學）
            self.rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-777",
                                          proposed_rule_path=str(rule_path))
            res = self.rt.exit_learning_commit("approved", reason="jitter readopt")
            self.assertEqual(res["to"], "ESCALATION")
            self.assertEqual(res["meta_halt"]["violation"], "ChurnBounded")
            prov = self.state.root["escalation_provenance"]
            self.assertEqual(prov["rule_id"], "R-9.24.1")
            self.assertEqual(prov["source"], "learning_commit_meta_halt")


class AutoclaudeDelegatedFailedProvenanceTests(_Base):
    def test_failed_writes_provenance_without_rule_id(self) -> None:
        self.state.root["current_state"] = "IMPLEMENTATION"
        save_state(self.state)
        self.rt.enter_autoclaude_delegated(reason="delegate to AutoClaude")
        res = self.rt.exit_autoclaude_delegated("failed", reason="AutoClaude playbook also failed")
        self.assertEqual(res["to"], "ESCALATION")
        prov = self.state.root["escalation_provenance"]
        self.assertEqual(prov["rule_id"], "unknown")
        self.assertEqual(prov["source"], "autoclaude_delegated_failed")
        self.assertEqual(prov["reason"], "AutoClaude playbook also failed")


# ---------------------------------------------------------------------------
# (d) 讀取面陳舊防呆（第二道防線）。
# ---------------------------------------------------------------------------


class StaleProvenanceGuardTests(_Base):
    def test_stale_provenance_is_flagged_and_reason_not_leaked_into_resume_command(self) -> None:
        # 舊事件：合法 record_escalation。
        self.state.record_escalation(
            "TOKEN_BUDGET_CRITICAL: used=950000 (stale, unrelated)",
            details={"session_id": "OLD-SESSION-XYZ"},
            rule_id="R-9.2", source="context_budget_stale",
        )
        # 人工 resume 解決。
        self.rt.resume_from_escalation(to="SPEC_DRAFTING", reason="manual resume, resolved")
        self.assertEqual(self.state.current, "SPEC_DRAFTING")
        # 把舊 provenance.at 明確撥回 5 小時前，模擬「這份 provenance 早於本次轉入」
        # （不依賴 sleep：時間戳直接注入，測試快且不 flaky）。
        old_at = _dt.datetime.fromisoformat(
            self.state.root["escalation_provenance"]["at"]
        ) - _dt.timedelta(hours=5)
        self.state.root["escalation_provenance"]["at"] = old_at.isoformat(timespec="seconds")
        # 模擬「繞過 record_escalation 直接轉態」（本輪修復前的舊行為／未來若再出現繞過站點的
        # 防線）：直接呼叫 transition()，不呼叫 record_escalation()。
        self.rt.transition(
            "ESCALATION", reason="simulated bypass — no provenance written",
            trigger="simulated_bypass_r6",
        )
        self.assertEqual(self.state.current, "ESCALATION")

        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, python="/venv/bin/python",
                                caller_session_id="NEW-SESSION-ABC")
        self.assertIn("溯源不可信", text)
        self.assertIn("OLD-SESSION-XYZ", text)  # 資訊性揭露：讓人知道舊溯源長什麼樣子，僅供參考
        cmd_lines = "\n".join(
            line for line in text.splitlines() if "resume-from-escalation" in line
        )
        self.assertTrue(cmd_lines, "應仍印出恢復指令")
        self.assertNotIn("950000", cmd_lines)
        self.assertNotIn("stale, unrelated", cmd_lines)

    def test_fresh_provenance_within_grace_window_is_not_flagged_stale(self) -> None:
        """反面案例：provenance 與『本次轉入』落在合法落點的正常時序（同一次呼叫內，容錯窗內）
        不得被誤判為陳舊——防止讀取面防呆把寫入面已修好的正常情境也擋成警訊。"""
        self.rt.record_dispatch_rejection(reason="budget_exhausted")
        self.rt.record_dispatch_rejection(reason="budget_exhausted")
        res = self.rt.record_dispatch_rejection(reason="budget_exhausted")
        self.assertTrue(res["escalated"])
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, caller_session_id="s-1")
        self.assertNotIn("溯源不可信", text)


if __name__ == "__main__":
    unittest.main()
