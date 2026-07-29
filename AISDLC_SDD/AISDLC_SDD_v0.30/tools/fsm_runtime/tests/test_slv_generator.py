# enforces (governance rules): R-9.11, R-9.3
"""ACT-028 SLV Rule Generator tests — Phase E M4 Learning Layer MVP."""
from __future__ import annotations

import datetime as _dt
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import yaml  # noqa: E402

from tools.fsm_runtime import slv_generator  # noqa: E402
from tools.fsm_runtime.slv_generator import (  # noqa: E402
    FPLEntry,
    FPLNotFound,
    FplAlreadyVerified,
    ImmutableFieldViolation,
    RuleOverwriteProtected,
    SchemaViolation,
    SLVRuleCandidate,
    VALID_TRUST_LEVELS,
    classify_result,
    find_verified_rule_for_fpl,
    iter_rule_files,
    load_fpl_entry,
    load_rule,
    next_available_slv_id,
    propose_slv_from_fpl,
    write_rule_candidate,
)


def _isolated_rules_dir(prefix: str) -> Path:
    """建立**行程獨立**的暫存規則目錄——絕不可退回樹內固定路徑。

    WHY（這不是風格偏好，是修一個會讓閘門說謊的真缺陷）：
      本檔各測試類原本把暫存規則目錄寫死成
      `Path(__file__).resolve().parent / "_tmp_*"`——那是 **tracked 樹內的共用固定路徑**，
      而 `setUp` 會清空它、`tearDown` 會 `rmdir` 它。於是同一支測試被兩個行程同時執行
      （並行四方複審、並行閘門、CI 與地端同時跑）時兩邊互刪對方的檔案，產生與被測邏輯
      **完全無關**的假紅，實測形態：
        · `FileNotFoundError: ..._tmp_rules\\SLV-900.yaml.lock`（file_lock.py:39）
        · `PermissionError: [WinError 32] ..._tmp_rules\\SLV-900.yaml`
        · `FileNotFoundError: [WinError 2] ..._tmp_imm_rules\\SLV-910.yaml.tmp`
      隔離重跑必綠 ⇒ 看起來像 flaky，實際是測試隔離缺陷。

    為何用 `mkdtemp` 而不是只加 `unlink(missing_ok=True)`：
      `missing_ok` 只讓競態**不拋例外**，兩行程仍共用同一個目錄、資料仍互相污染
      （A 寫的 SLV-900 被 B 的 setUp 清掉，A 的斷言讀到空）。`mkdtemp` 才是根治：
      兩行程拿到不同目錄，共用狀態從根本消失。
    """
    return Path(tempfile.mkdtemp(prefix=prefix))


class FPLLoadingTests(unittest.TestCase):
    def test_fpl_001_loads_and_extracts_yaml_block(self) -> None:
        entry = load_fpl_entry("FPL-001")
        self.assertEqual(entry.fpl_id, "FPL-001")
        self.assertIn("時序", entry.title)
        self.assertIsNotNone(entry.regex_pattern)
        self.assertTrue(entry.required_qualifiers, "FPL-001 必須帶 required_qualifier 清單")
        self.assertIn("%", entry.regex_pattern or "")

    def test_invalid_fpl_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            load_fpl_entry("not-an-id")

    def test_unknown_fpl_id_raises_not_found(self) -> None:
        with self.assertRaises(FPLNotFound):
            load_fpl_entry("FPL-999")


class ProposalSynthesisTests(unittest.TestCase):
    def test_propose_fpl_001_yields_slv_candidate(self) -> None:
        fpl = load_fpl_entry("FPL-001")
        cand = propose_slv_from_fpl(fpl, slv_id="SLV-777", now=_dt.date(2026, 4, 24))
        self.assertEqual(cand.id, "SLV-777")
        self.assertEqual(cand.trust_level, "proposed")
        self.assertIsNone(cand.reviewed_by, "新規則 reviewed_by 必須為 None（未 review）")
        self.assertIsNone(cand.reviewed_at)
        self.assertEqual(cand.source_fpl, "FPL-001")
        self.assertIn("2026-04-24", cand.source, "source 需含 auto-generated 日期供審計")
        self.assertEqual(cand.scope, "temporal")
        self.assertTrue(cand.required_qualifiers, "FPL-001 的 qualifier 必須被帶入")
        self.assertTrue(cand.pattern_regex, "FPL-001 的 regex 必須被帶入")

    def test_propose_requires_qualifiers_or_regex(self) -> None:
        empty = FPLEntry(fpl_id="FPL-900", title="空案例", path=Path("/nonexistent"))
        with self.assertRaises(ValueError):
            propose_slv_from_fpl(empty)

    def test_next_available_slv_id_advances(self) -> None:
        nxt = next_available_slv_id()
        self.assertRegex(nxt, r"^SLV-\d{3,}$")
        n = int(nxt.split("-")[1])
        self.assertGreaterEqual(n, 7, "生成器已跑過一次，下一個 id 必 ≥ SLV-007")


class TrustLevelProtectionTests(unittest.TestCase):
    """驗證 proposed/verified trust level 的寫入保護。"""

    def setUp(self) -> None:
        # mkdtemp 已保證目錄存在且為空 ⇒ 原本的「清空殘留 *.yaml」迴圈連同 rmdir
        # 一併移除（見 _isolated_rules_dir 的 WHY：那正是互刪的來源）。
        self.tmp = _isolated_rules_dir("slv_rules_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_cand(self, slv_id: str = "SLV-900") -> SLVRuleCandidate:
        return SLVRuleCandidate(
            id=slv_id,
            name="test rule",
            source="unit-test",
            trust_level="proposed",
            reviewed_by=None,
            reviewed_at=None,
            scope="generic",
            purpose="t",
            scan_targets=["docs/01_requirements/FRD-*.md"],
            required_qualifiers=["必須不為空"],
            failure_examples=[],
            pass_examples=[],
            severity="CRITICAL",
            blocks_scg=True,
            source_fpl="FPL-999",
        )

    def test_write_proposed_then_overwrite_ok(self) -> None:
        cand = self._make_cand()
        path1 = write_rule_candidate(cand, rules_dir=self.tmp)
        # Second write with overwrite_proposed=True should succeed.
        path2 = write_rule_candidate(cand, rules_dir=self.tmp, overwrite_proposed=True)
        self.assertEqual(path1, path2)

    def test_write_proposed_then_no_overwrite_raises(self) -> None:
        cand = self._make_cand()
        write_rule_candidate(cand, rules_dir=self.tmp)
        with self.assertRaises(RuleOverwriteProtected):
            write_rule_candidate(cand, rules_dir=self.tmp, overwrite_proposed=False)

    def test_verified_rule_cannot_be_overwritten(self) -> None:
        cand = self._make_cand()
        target = write_rule_candidate(cand, rules_dir=self.tmp)
        # Flip trust_level to verified on disk
        doc = yaml.safe_load(target.read_text(encoding="utf-8"))
        doc["trust_level"] = "verified"
        doc["reviewed_by"] = "tester@example.com"
        doc["reviewed_at"] = "2026-04-24"
        target.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        # Now attempting to overwrite must raise.
        with self.assertRaises(RuleOverwriteProtected):
            write_rule_candidate(cand, rules_dir=self.tmp, overwrite_proposed=True)


class FplDedupGateTests(unittest.TestCase):
    """DEF-CLDREV-011 去重閘意圖鎖。

    為何重要：`propose_slv_from_fpl` 每次配新 id，過去無機制阻止「同一 FPL 已升
    verified 卻再產 proposed 重複」→ FPL-001 已有 verified SLV-007 仍重生 SLV-013/014
    （純噪音、永不可升第二條 verified）。此 gate 從持久化 choke point 治本。正例（已有
    verified → fire）與負例（僅 proposed / 不同 FPL / 覆寫逃生口 → 不 fire）對稱覆蓋，
    避免誤擋合法的「審核前多草案」與「人工指定變體」。
    """

    def setUp(self) -> None:
        self.tmp = _isolated_rules_dir("slv_dedup_rules_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cand(self, slv_id: str, fpl_id: str, trust: str = "proposed") -> SLVRuleCandidate:
        return SLVRuleCandidate(
            id=slv_id, name=f"rule {slv_id}", source=f"{fpl_id} auto-generated 2026-06-15",
            trust_level=trust,
            reviewed_by=("r@x" if trust == "verified" else None),
            reviewed_at=("2026-06-15" if trust == "verified" else None),
            scope="temporal", purpose="t",
            scan_targets=["docs/01_requirements/FRD-*.md"],
            required_qualifiers=["必須不為空"], failure_examples=[], pass_examples=[],
            severity="CRITICAL", blocks_scg=True, source_fpl=fpl_id,
        )

    def test_dedup_gate_fires_when_fpl_already_verified(self) -> None:
        """已有 verified SLV-A(FPL-001) → 為同 FPL 配新 id SLV-B 落盤須被擋（SLV-013/014 本體）。"""
        write_rule_candidate(self._cand("SLV-A", "FPL-001", trust="verified"), rules_dir=self.tmp)
        with self.assertRaises(FplAlreadyVerified):
            write_rule_candidate(self._cand("SLV-B", "FPL-001"), rules_dir=self.tmp)

    def test_dedup_gate_silent_when_only_proposed_exists(self) -> None:
        """僅有 proposed（尚未 review）→ 同 FPL 另一草案不擋（審核前多草案合法）。"""
        write_rule_candidate(self._cand("SLV-A", "FPL-002"), rules_dir=self.tmp)
        # 不應 raise
        path = write_rule_candidate(self._cand("SLV-B", "FPL-002"), rules_dir=self.tmp)
        self.assertTrue(path.exists())

    def test_dedup_gate_silent_for_different_fpl(self) -> None:
        """verified SLV-A(FPL-001) 不擋 FPL-003 的新草案（去重只針對同一 FPL）。"""
        write_rule_candidate(self._cand("SLV-A", "FPL-001", trust="verified"), rules_dir=self.tmp)
        path = write_rule_candidate(self._cand("SLV-B", "FPL-003"), rules_dir=self.tmp)
        self.assertTrue(path.exists())

    def test_allow_duplicate_fpl_overrides_gate(self) -> None:
        """allow_duplicate_fpl=True → 明確變體逃生口，即使已有 verified 仍放行。"""
        write_rule_candidate(self._cand("SLV-A", "FPL-001", trust="verified"), rules_dir=self.tmp)
        path = write_rule_candidate(
            self._cand("SLV-B", "FPL-001"), rules_dir=self.tmp, allow_duplicate_fpl=True
        )
        self.assertTrue(path.exists())

    def test_find_verified_rule_for_fpl_helper(self) -> None:
        """helper：verified 命中回 id、exclude_id 排除自身、無命中回 None。"""
        write_rule_candidate(self._cand("SLV-A", "FPL-001", trust="verified"), rules_dir=self.tmp)
        write_rule_candidate(self._cand("SLV-C", "FPL-004"), rules_dir=self.tmp)  # proposed
        self.assertEqual(find_verified_rule_for_fpl("FPL-001", rules_dir=self.tmp), "SLV-A")
        self.assertIsNone(  # 排除自身（overwrite 同 id 的 verified 不算重複）
            find_verified_rule_for_fpl("FPL-001", rules_dir=self.tmp, exclude_id="SLV-A"))
        self.assertIsNone(  # 只有 proposed，無 verified
            find_verified_rule_for_fpl("FPL-004", rules_dir=self.tmp))
        self.assertIsNone(find_verified_rule_for_fpl("", rules_dir=self.tmp))


class RuleSchemaTests(unittest.TestCase):
    def test_all_builtin_rules_validate(self) -> None:
        builtin_ids = []
        for p in iter_rule_files():
            doc = load_rule(p)  # raises on invalid
            builtin_ids.append(doc["id"])
            self.assertIn(doc["trust_level"], VALID_TRUST_LEVELS)
        # Ensure SLV-001..SLV-006 are all present and verified
        for n in range(1, 7):
            self.assertIn(f"SLV-{n:03d}", builtin_ids, f"missing builtin SLV-{n:03d}")

    def test_slv_007_human_approved_verified_with_audit_trail(self) -> None:
        """驗證 SLV-007 已由人工 review 升級為 verified + 審計欄位齊備。

        M4 QA Round-6：原本測試期望 SLV-007 保持 proposed；用戶於 2026-04-24
        完成 human review 並升級為 verified，測試跟進改為驗收 verified 的
        審計鏈完整性（reviewed_by / reviewed_at / source_fpl / source）。
        草案產出階段的 proposed 契約由
        test_propose_slv_from_fpl_produces_proposed_draft 單獨驗證。
        """
        rules_dir = slv_generator.RULES_DIR
        target = rules_dir / "SLV-007.yaml"
        self.assertTrue(target.exists(), "SLV-007 必須已由 ACT-028 CLI 產出")
        doc = load_rule(target)
        self.assertEqual(doc["trust_level"], "verified")
        self.assertEqual(doc.get("source_fpl"), "FPL-001")
        self.assertTrue(
            doc.get("reviewed_by"),
            "verified 規則必填 reviewed_by(reviewer email / id)",
        )
        self.assertTrue(
            doc.get("reviewed_at"),
            "verified 規則必填 reviewed_at(ISO date)",
        )
        self.assertEqual(doc["scope"], "temporal")
        self.assertIn(
            "auto-generated",
            str(doc.get("source", "")),
            "source 必保留 FPL 自動產出審計標記",
        )

    def test_propose_slv_from_fpl_produces_proposed_draft(self) -> None:
        """§9.11.1 契約：propose_slv_from_fpl() 產出 **永遠** 是 proposed。

        此測試獨立於磁碟上的 SLV-007.yaml（該檔已被人工升級為 verified），
        直接驗證產生器本身的 trust_level 契約 — 不論何時呼叫，新草案必為
        proposed、reviewed_by/reviewed_at 為 None、source_fpl 正確指向
        輸入 FPL。
        """
        fpl = load_fpl_entry("FPL-001")
        cand = propose_slv_from_fpl(fpl, slv_id="SLV-888", now=_dt.date(2026, 4, 24))
        doc = cand.to_yaml_doc()
        self.assertEqual(doc["trust_level"], "proposed")
        self.assertIsNone(doc["reviewed_by"])
        self.assertIsNone(doc["reviewed_at"])
        self.assertEqual(doc["source_fpl"], "FPL-001")
        self.assertIn("auto-generated", doc["source"])
        self.assertIn("2026-04-24", doc["source"])


class CLIIntegrationTests(unittest.TestCase):
    def test_cli_dry_run_prints_yaml(self) -> None:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = slv_generator._cli(["propose", "FPL-001", "--slv-id", "SLV-800", "--dry-run"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("SLV-800", out)
        self.assertIn("proposed", out)
        self.assertIn("FPL-001", out)

    def test_cli_validate_passes_for_builtin_rules(self) -> None:
        rc = slv_generator._cli(["validate"])
        self.assertEqual(rc, 0)


class FSMIntegrationTests(unittest.TestCase):
    """LEARNING_COMMIT 進入/離開流程（ACT-028 FSM 整合）。"""

    def _setup_runtime(self, tmp_path: Path):
        # Bootstrap a fresh FSM under a custom project name to avoid touching
        # the main FSM-STATE-*.yaml
        from tools.fsm_runtime.state_loader import load_state
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        project = "slv-gen-test"
        state_path = tmp_path / f"FSM-STATE-{project}.yaml"
        state = load_state(project, path=state_path, create_if_missing=True)
        # Fast-forward through happy path to RELEASE using state accessors
        # (avoid tripping auto-transition helpers we don't need here).
        state.root["current_state"] = "RELEASE"
        from tools.fsm_runtime.state_loader import save_state
        save_state(state)
        return FSMRuntime(state)

    def test_enter_learning_commit_from_release_sets_tracking(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rt = self._setup_runtime(Path(td))
            res = rt.enter_learning_commit(
                fpl_id="FPL-001",
                proposed_slv_id="SLV-007",
                proposed_rule_path=".claude/skills/spec-logical-validator/rules/SLV-007.yaml",
                reason="ACT-028 unit test",
            )
            self.assertTrue(res.get("entered"))
            self.assertEqual(rt.state.current, "LEARNING_COMMIT")
            tracking = rt.state.root["learning_commit_tracking"]
            self.assertEqual(tracking["fpl_id"], "FPL-001")
            self.assertEqual(tracking["proposed_slv_id"], "SLV-007")
            self.assertEqual(tracking["review_status"], "pending")

    def test_enter_learning_commit_rejects_wrong_source(self) -> None:
        import tempfile
        from tools.fsm_runtime.transition_rules import TransitionError
        with tempfile.TemporaryDirectory() as td:
            rt = self._setup_runtime(Path(td))
            # Force state to SPEC_DRAFTING (illegal source)
            rt.state.root["current_state"] = "SPEC_DRAFTING"
            with self.assertRaises(TransitionError):
                rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-007")

    def _make_verified_rule_fixture(self, td: Path, slv_id: str = "SLV-777") -> Path:
        """建立 approved 流程需要的 verified YAML fixture（P1-1 驗證依賴）。"""
        import yaml as _yaml
        target = td / f"{slv_id}.yaml"
        doc = {
            "id": slv_id,
            "name": "fixture verified rule",
            "source": "FPL-001 auto-generated 2026-04-24",
            "trust_level": "verified",
            "reviewed_by": "reviewer@example.com",
            "reviewed_at": "2026-04-24",
            "scope": "temporal",
            "purpose": "test fixture",
            "scan_targets": ["docs/01_requirements/FRD-*.md"],
            "required_qualifiers": ["必須不為空"],
            "failure_examples": [],
            "pass_examples": [],
            "severity": "CRITICAL",
            "blocks_scg": True,
            "source_fpl": "FPL-001",
        }
        target.write_text(_yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return target

    def test_exit_learning_commit_approved_goes_to_release(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            rt = self._setup_runtime(td_path)
            # P1-1：approved exit 需 verified YAML 審計；建 fixture 並傳入絕對路徑
            rule_path = self._make_verified_rule_fixture(td_path, "SLV-777")
            rt.enter_learning_commit(
                fpl_id="FPL-001",
                proposed_slv_id="SLV-777",
                proposed_rule_path=str(rule_path),
            )
            res = rt.exit_learning_commit("approved", reason="manual approve")
            self.assertEqual(res["outcome"], "approved")
            self.assertEqual(rt.state.current, "RELEASE")
            self.assertEqual(rt.state.root["learning_commit_tracking"]["review_status"], "approved")
            # P1-2：proposals_history 必須 append 一筆
            history = rt.state.root["learning_commit_tracking"]["proposals_history"]
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["fpl_id"], "FPL-001")
            self.assertEqual(history[0]["proposed_slv_id"], "SLV-777")
            self.assertEqual(history[0]["review_status"], "approved")
            self.assertTrue(history[0]["reviewed_at"])

    def test_exit_learning_commit_rejected_goes_to_escalation(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rt = self._setup_runtime(Path(td))
            rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-007")
            res = rt.exit_learning_commit("rejected", reason="manual reject")
            self.assertEqual(res["outcome"], "rejected")
            self.assertEqual(rt.state.current, "ESCALATION")

    def test_exit_learning_commit_invalid_outcome_raises(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rt = self._setup_runtime(Path(td))
            rt.enter_learning_commit(fpl_id="FPL-001", proposed_slv_id="SLV-007")
            with self.assertRaises(ValueError):
                rt.exit_learning_commit("maybe-later")

    def test_exit_learning_commit_approved_requires_verified_yaml(self) -> None:
        """P1-1：approved 但 YAML 仍是 proposed / 缺 reviewer → 必 raise。"""
        import tempfile
        import yaml as _yaml
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            rt = self._setup_runtime(td_path)
            # 建 proposed 狀態 YAML（未 review）
            bad_rule_path = td_path / "SLV-778.yaml"
            bad_doc = {
                "id": "SLV-778",
                "name": "still proposed",
                "source": "FPL-001 auto-generated 2026-04-24",
                "trust_level": "proposed",
                "reviewed_by": None,
                "reviewed_at": None,
                "scope": "temporal",
                "purpose": "t",
                "scan_targets": ["docs/01_requirements/FRD-*.md"],
                "required_qualifiers": ["x"],
                "failure_examples": [],
                "pass_examples": [],
                "severity": "CRITICAL",
                "blocks_scg": True,
                "source_fpl": "FPL-001",
            }
            bad_rule_path.write_text(
                _yaml.safe_dump(bad_doc, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            rt.enter_learning_commit(
                fpl_id="FPL-001",
                proposed_slv_id="SLV-778",
                proposed_rule_path=str(bad_rule_path),
            )
            with self.assertRaises(ValueError):
                rt.exit_learning_commit("approved")

    def test_exit_learning_commit_rejected_appends_history(self) -> None:
        """P1-2：rejected 分支也要 append 到 proposals_history。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            rt = self._setup_runtime(td_path)
            rt.enter_learning_commit(
                fpl_id="FPL-001",
                proposed_slv_id="SLV-779",
                proposed_rule_path=str(td_path / "SLV-779.yaml"),
            )
            res = rt.exit_learning_commit("rejected", reason="triage failed")
            self.assertEqual(res["outcome"], "rejected")
            self.assertEqual(rt.state.current, "ESCALATION")
            history = rt.state.root["learning_commit_tracking"]["proposals_history"]
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["review_status"], "rejected")
            self.assertEqual(history[0]["proposed_slv_id"], "SLV-779")


class ClassifyResultTests(unittest.TestCase):
    """P1-4：classify_result 的矩陣驗證。"""

    def _rule(self, trust_level: str) -> dict:
        return {"id": "SLV-TEST", "trust_level": trust_level}

    def test_classify_result_matrix(self) -> None:
        self.assertEqual(classify_result(self._rule("verified"), fail=True), "blocking")
        self.assertEqual(classify_result(self._rule("proposed"), fail=True), "advisory")
        self.assertEqual(classify_result(self._rule("external"), fail=True), "advisory")
        # pass 狀態不論 trust_level 一律 pass
        self.assertEqual(classify_result(self._rule("verified"), fail=False), "pass")
        self.assertEqual(classify_result(self._rule("proposed"), fail=False), "pass")
        self.assertEqual(classify_result(self._rule("external"), fail=False), "pass")

    def test_classify_result_rejects_invalid_trust_level(self) -> None:
        with self.assertRaises(SchemaViolation):
            classify_result({"id": "SLV-X", "trust_level": "bogus"}, fail=True)


class ImmutabilityTests(unittest.TestCase):
    """P0-4：source_fpl / source 是審計鏈錨點，overwrite 不得改寫。"""

    def setUp(self) -> None:
        # 原寫法的 `glob()`→`unlink()` 之間還有 TOCTOU（無 missing_ok）：另一行程在兩個
        # 呼叫之間刪掉同一個檔就炸 `FileNotFoundError [WinError 2] …SLV-910.yaml.tmp`。
        # 改用行程獨立目錄後，該競態的前提（共用目錄）本身消失。
        self.tmp = _isolated_rules_dir("slv_imm_rules_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _cand(self, slv_id: str, *, source_fpl: str, source: str) -> SLVRuleCandidate:
        return SLVRuleCandidate(
            id=slv_id,
            name="t",
            source=source,
            trust_level="proposed",
            reviewed_by=None,
            reviewed_at=None,
            scope="generic",
            purpose="t",
            scan_targets=["docs/01_requirements/FRD-*.md"],
            required_qualifiers=["x"],
            failure_examples=[],
            pass_examples=[],
            severity="CRITICAL",
            blocks_scg=True,
            source_fpl=source_fpl,
        )

    def test_overwrite_with_different_source_fpl_raises(self) -> None:
        first = self._cand(
            "SLV-910", source_fpl="FPL-001", source="FPL-001 auto-generated 2026-04-24"
        )
        write_rule_candidate(first, rules_dir=self.tmp)
        # 相同 id 但 source_fpl 被改 → 拒絕
        second = self._cand(
            "SLV-910", source_fpl="FPL-002", source="FPL-001 auto-generated 2026-04-24"
        )
        with self.assertRaises(ImmutableFieldViolation):
            write_rule_candidate(second, rules_dir=self.tmp, overwrite_proposed=True)

    def test_overwrite_with_different_source_string_raises(self) -> None:
        first = self._cand(
            "SLV-911", source_fpl="FPL-001", source="FPL-001 auto-generated 2026-04-24"
        )
        write_rule_candidate(first, rules_dir=self.tmp)
        # source 字串被改 → 拒絕
        second = self._cand(
            "SLV-911", source_fpl="FPL-001", source="FPL-001 auto-generated 2026-05-01"
        )
        with self.assertRaises(ImmutableFieldViolation):
            write_rule_candidate(second, rules_dir=self.tmp, overwrite_proposed=True)

    def test_overwrite_with_same_source_fields_succeeds(self) -> None:
        cand = self._cand(
            "SLV-912", source_fpl="FPL-001", source="FPL-001 auto-generated 2026-04-24"
        )
        write_rule_candidate(cand, rules_dir=self.tmp)
        # 相同 source / source_fpl → 可覆寫
        write_rule_candidate(cand, rules_dir=self.tmp, overwrite_proposed=True)


class SchemaValidationTests(unittest.TestCase):
    """P1-3：load_rule 對 verified 強制 reviewed_by / reviewed_at。"""

    def setUp(self) -> None:
        self.tmp = _isolated_rules_dir("slv_schema_rules_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, doc: dict, name: str = "SLV-920.yaml") -> Path:
        import yaml as _yaml
        p = self.tmp / name
        p.write_text(_yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return p

    def test_verified_without_reviewer_raises(self) -> None:
        p = self._write({
            "id": "SLV-920",
            "name": "x",
            "trust_level": "verified",
            "scope": "generic",
            "reviewed_by": None,
            "reviewed_at": None,
        })
        with self.assertRaises(SchemaViolation):
            load_rule(p)

    def test_verified_with_empty_reviewer_raises(self) -> None:
        p = self._write({
            "id": "SLV-921",
            "name": "x",
            "trust_level": "verified",
            "scope": "generic",
            "reviewed_by": "  ",
            "reviewed_at": "2026-04-24",
        }, name="SLV-921.yaml")
        with self.assertRaises(SchemaViolation):
            load_rule(p)

    def test_bad_source_fpl_format_raises(self) -> None:
        p = self._write({
            "id": "SLV-922",
            "name": "x",
            "trust_level": "proposed",
            "scope": "generic",
            "source_fpl": "not-an-fpl",
        }, name="SLV-922.yaml")
        with self.assertRaises(SchemaViolation):
            load_rule(p)

    def test_proposed_without_reviewer_ok(self) -> None:
        p = self._write({
            "id": "SLV-923",
            "name": "x",
            "trust_level": "proposed",
            "scope": "generic",
            "reviewed_by": None,
            "reviewed_at": None,
        }, name="SLV-923.yaml")
        # proposed 不需 reviewer — should not raise
        load_rule(p)


if __name__ == "__main__":
    unittest.main()
