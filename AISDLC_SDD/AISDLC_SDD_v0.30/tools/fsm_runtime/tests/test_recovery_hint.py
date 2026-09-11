# enforces (governance rules): R-9.5, R-9.2
"""DEF-200-275 第四輪 D6／D6b：ESCALATION 人工恢復（recovery_hint／resume_from_escalation／CLI）
與 escalation／auto-compact 紀錄帶 details 的回歸鎖。

WHY（Rule 9）：根因 C 是 session 級事件寫進專案級黏著的 ESCALATION，人卻拿不到一條能跑的指令。
這裡守的是：(1) 提示裡的指令真的走合法邊（逐跳以 is_transition_allowed 驗）；(2) 恢復只由人觸發、
不弱化 R-9.5（noop／ValueError 兩側都鎖）；(3) `record_escalation(details=None)` 鍵集合逐字不變
（96 個既有呼叫端零改動）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import recovery_hint as rh  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402
from tools.fsm_runtime.transition_rules import is_transition_allowed  # noqa: E402

_SDD_ROOT = Path(__file__).resolve().parents[3]
# F3 夾具：Windows 載具路徑純字面值，只餵給 console_python() 做檔名換名；期望值一律由 Path 渲染
# （Windows 上 with_name() 會把正斜線渲染成反斜線），不得再寫第二個字面值去比對。
_WIN_PYTHONW = "C:/x/.venv/Scripts/pythonw.exe"  # platform-ok: 純字面值輸入，期望值由 Path 渲染
_WIN_PYTHONW_ORPHAN = "C:/x/pythonw.exe"  # platform-ok: 純字面值輸入，斷言的是「照印原值」


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.state_path = self.tmp / "FSM-STATE-rh.yaml"
        self.state = load_state("rh-proj", path=self.state_path)
        self.rt = FSMRuntime(self.state)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class RecordEscalationDetailsTests(_Base):
    def test_details_none_keeps_exact_legacy_key_set(self) -> None:
        self.state.record_escalation("manual_trigger")
        entry = self.state.root["escalation_history"][-1]
        self.assertEqual(set(entry), {"triggered_at", "trigger_reason", "resolved_at", "resolution"})
        self.assertEqual(self.state.current, "ESCALATION")

    def test_details_are_merged_without_overriding_base_keys(self) -> None:
        self.state.record_escalation(
            "TOKEN_BUDGET_CRITICAL: used=950000",
            details={"session_id": "s-1", "used": 950000, "window": 1_000_000,
                     "window_source": "查表值", "compact_boundaries": 0,
                     "trigger_reason": "HACK"},
        )
        entry = self.state.root["escalation_history"][-1]
        self.assertEqual(entry["session_id"], "s-1")
        self.assertEqual(entry["used"], 950000)
        self.assertEqual(entry["trigger_reason"], "TOKEN_BUDGET_CRITICAL: used=950000")

    def test_trigger_auto_compact_stores_details_and_passes_them_on_cap(self) -> None:
        """D13（DEF-200-275 第五輪）：per-stage cap 超限不再寫專案級 ESCALATION，改成
        auto_compact_state.cap_exceeded 一次性標記（session 級），details 透傳到標記裡。"""
        import tools.fsm_runtime.snapshot as snap_mod
        original = snap_mod.SNAPSHOT_DIR
        snap_mod.SNAPSHOT_DIR = self.tmp / "abort"
        try:
            self.state.current = "IMPLEMENTATION"
            details = {"session_id": "s-9", "used": 900_000, "window": 1_000_000,
                       "window_source": "指定值", "compact_boundaries": 1}
            res = self.rt.trigger_auto_compact(900_000, 0.9, details=details)
            self.assertFalse(res.get("escalated"))
            self.assertEqual(self.state.root["auto_compact_state"]["trigger_details"]["session_id"], "s-9")
            self.rt.complete_auto_compact(reset_ledger=False)
            # 逼到 per-stage cap
            for _ in range(2):
                self.rt.trigger_auto_compact(900_000, 0.9, details=details)
                self.rt.complete_auto_compact(reset_ledger=False)
            res = self.rt.trigger_auto_compact(900_000, 0.9, details=details)
            self.assertFalse(res.get("escalated"), "D13：cap 超限不再是 escalated=True")
            self.assertTrue(res.get("cap_exceeded"))
            self.assertTrue(res.get("noop"))
            self.assertEqual(self.state.root.get("escalation_history") or [], [],
                             "D13：cap 超限不得寫 escalation_history")
            self.assertEqual(self.state.current, "IMPLEMENTATION",
                             "D13：cap 超限不得把 FSM 轉態")
            marker = self.state.root["auto_compact_state"]["cap_exceeded"]
            self.assertEqual(marker["session_id"], "s-9")
            self.assertEqual(marker["stage_key"], "initial")
        finally:
            snap_mod.SNAPSHOT_DIR = original


class EscalationProvenanceTests(_Base):
    """D17（DEF-200-275 第六輪／DEF-200-283；F-ARCH-01／QA-C1）：`record_escalation()` 落一份
    `escalation_provenance` 快照——「誰、何時、為何、依哪條規則」寫入了這個 project-level
    ESCALATION，讓 recovery_hint() 能回答「這是不是我這個 session 觸發的」。缺席一律老實寫
    "unknown"（機讀 sentinel），不是 None、不臆測。"""

    def test_record_escalation_writes_provenance_with_rule_id_and_source(self) -> None:
        self.state.record_escalation(
            "gate retry exhausted", details={"session_id": "s-1"},
            rule_id="R-9.1", source="gate_retry_budget:SCG_VALIDATION",
        )
        prov = self.state.root["escalation_provenance"]
        self.assertEqual(prov["session_id"], "s-1")
        self.assertEqual(prov["rule_id"], "R-9.1")
        self.assertEqual(prov["source"], "gate_retry_budget:SCG_VALIDATION")
        self.assertEqual(prov["reason"], "gate retry exhausted")
        self.assertIn("T", prov["at"])  # aware ISO timestamp（同 escalation_history 的 triggered_at）
        self.assertEqual(prov["at"], self.state.root["escalation_history"][-1]["triggered_at"])

    def test_missing_session_id_rule_id_source_write_unknown_not_none(self) -> None:
        self.state.record_escalation("implementation budget exceeded")
        prov = self.state.root["escalation_provenance"]
        self.assertEqual(prov["session_id"], "unknown")
        self.assertEqual(prov["rule_id"], "unknown")
        self.assertEqual(prov["source"], "unknown")


class RecoveryHintProvenanceTests(_Base):
    """D17：recovery_hint() 的溯源行——是不是我這個 session 觸發的；m=None 首擊一樣要印。"""

    def test_first_strike_m_none_still_prints_full_provenance_and_resume_command(self) -> None:
        self.state.record_escalation(
            "HUMAN_PENDING 逾時 200h (≥168h)，自動進入 ESCALATION (ACT-023)",
            details={"session_id": "old-1"}, rule_id="R-9.7", source="human_pending_timeout",
        )
        # measurement/window/source 全不傳 ⇒ 首擊量不到 usage 的真實情境（新視窗第一次呼叫）。
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, python="/venv/bin/python",
                                caller_session_id="new-2")
        self.assertIn("溯源：此 ESCALATION 由 session=old-1", text)
        self.assertIn("因 HUMAN_PENDING 逾時 200h (≥168h)，自動進入 ESCALATION (ACT-023) 寫入", text)
        self.assertIn("rule_id=R-9.7", text)
        self.assertIn("本 session=new-2", text)
        self.assertIn("不是觸發者", text)
        self.assertIn("resume-from-escalation --to", text)
        self.assertIn("目前本 session 尚無可用 usage（新 session 首擊或 compact 後）", text)

    def test_same_session_is_named_as_trigger(self) -> None:
        self.state.record_escalation(
            "spec_patch limit exceeded for AC-1", details={"session_id": "s-same"},
            rule_id="R-9.22", source="spec_patch_limit:AC-1",
        )
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, caller_session_id="s-same")
        self.assertIn("本 session=s-same（是觸發者）", text)

    def test_unknown_provenance_session_says_cannot_confirm(self) -> None:
        self.state.record_escalation("implementation budget exceeded")  # 無 details ⇒ session unknown
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, caller_session_id="new-3")
        self.assertIn("無法確認是否為觸發者", text)

    def test_no_caller_session_id_also_cannot_confirm(self) -> None:
        """呼叫端沒傳 caller_session_id（例如既有舊呼叫簽名）時，同樣誠實印「無法確認」，
        不得因為 caller 端缺席就誤判成任何一種確定答案。"""
        self.state.record_escalation("x", details={"session_id": "s-1"})
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT)
        self.assertIn("無法確認是否為觸發者", text)

    def test_hours_ago_is_computed_from_provenance_timestamp(self) -> None:
        import datetime as _dt
        self.state.record_escalation("x", details={"session_id": "s-1"})
        fixed_now = _dt.datetime.fromisoformat(
            self.state.root["escalation_provenance"]["at"]
        ) + _dt.timedelta(hours=3)
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, caller_session_id="s-1", _now=fixed_now)
        self.assertIn("3.0 小時前", text)


class CompleteAutoCompactD4Tests(_Base):
    def _enter_pending(self, resume_state: str) -> None:
        import tools.fsm_runtime.snapshot as snap_mod
        self._snap_orig = snap_mod.SNAPSHOT_DIR
        snap_mod.SNAPSHOT_DIR = self.tmp / "abort"
        self.state.current = resume_state
        res = self.rt.trigger_auto_compact(900_000, 0.9)
        self.assertEqual(self.state.current, "AUTO_COMPACT_PENDING")
        self.assertEqual(self.state.root["auto_compact_state"]["resume_state"], resume_state)
        snap_mod.SNAPSHOT_DIR = self._snap_orig
        _ = res

    def test_illegal_resume_state_init_remaps_to_spec_drafting(self) -> None:
        """活狀態實測 resume_state=INIT；AUTO_COMPACT_PENDING 出口集不含 INIT ⇒ 不 crash、remap。"""
        self._enter_pending("INIT")
        out = self.rt.complete_auto_compact(reset_ledger=False)
        self.assertEqual(self.state.current, "SPEC_DRAFTING")
        self.assertEqual(out["remapped_from"], "INIT")
        self.assertIn("remap", self.state.root["decision_trace"][-1]["reason"])

    def test_observed_effective_resets_per_stage_count(self) -> None:
        self._enter_pending("IMPLEMENTATION")
        self.assertEqual(self.state.root["auto_compact_state"]["count_per_stage"], 1)
        self.rt.complete_auto_compact(reset_ledger=False, observed_effective=True)
        self.assertEqual(self.state.current, "IMPLEMENTATION")
        self.assertEqual(self.state.root["auto_compact_state"]["count_per_stage"], 0)

    def test_default_completion_keeps_legacy_semantics(self) -> None:
        self._enter_pending("IMPLEMENTATION")
        out = self.rt.complete_auto_compact(reset_ledger=False)
        self.assertEqual(out["resumed_to"], "IMPLEMENTATION")
        self.assertNotIn("remapped_from", out)
        self.assertEqual(self.state.root["auto_compact_state"]["count_per_stage"], 1)

    def _ledger_path_under(self, repo_root: Path) -> Path:
        import datetime as _dt
        d = repo_root / "build" / "reports" / "fsm"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"

    def test_corrupt_ledger_does_not_raise_state_still_resumes(self) -> None:
        """F2（SD-02／ARCH-08）：損毀帳本 ⇒ complete_auto_compact 不 raise、state 已轉、ledger.reset=False、
        損毀檔被 rotate 保留現場。此前 `_reset_today_ledger` 自己 yaml.safe_load 會在 transition 之後炸，
        hook 端 [DONE] 訊息變 [DONE][WARN] 誤導。"""
        import tools.fsm_runtime.state_loader as sl_mod
        repo = self.tmp / "repo"
        path = self._ledger_path_under(repo)
        path.write_text("date: x\nentries:\n- t: null\n  - [broken\n", encoding="utf-8")
        with patch.object(sl_mod, "REPO_ROOT", repo):
            self._enter_pending("IMPLEMENTATION")
            out = self.rt.complete_auto_compact()  # reset_ledger=True（預設）
        self.assertEqual(self.state.current, "IMPLEMENTATION")
        self.assertFalse(out["ledger"]["reset"], msg=out)
        self.assertTrue(out["ledger"].get("rotated"), msg=out)
        self.assertEqual(len(list(path.parent.glob("CONTEXT-LEDGER-*.corrupt-*.yaml"))), 1)

    def test_reset_ledger_exception_is_reported_in_ledger_field_not_raised(self) -> None:
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._enter_pending("IMPLEMENTATION")
        with patch.object(fsm_rt_mod, "_reset_today_ledger", side_effect=OSError("disk gone")):
            out = self.rt.complete_auto_compact()
        self.assertEqual(self.state.current, "IMPLEMENTATION")
        self.assertEqual(out["ledger"]["reset"], False)
        self.assertIn("disk gone", out["ledger"]["error"])

    def test_healthy_ledger_is_zeroed_under_lock_with_reset_entry(self) -> None:
        """對照組：健康帳本走新路徑仍歸零、留 compact-reset 列、無 .part 殘留（與 e2e S10 同義）。"""
        import tools.fsm_runtime.state_loader as sl_mod
        import yaml
        repo = self.tmp / "repo"
        path = self._ledger_path_under(repo)
        path.write_text(yaml.safe_dump({"date": "d", "cumulative_tokens": 4200, "entries": [{"tokens": 4200}],
                                        "conversation_overhead": {"last_merge_entry_index": 1}}),
                        encoding="utf-8")
        with patch.object(sl_mod, "REPO_ROOT", repo):
            self._enter_pending("IMPLEMENTATION")
            out = self.rt.complete_auto_compact()
        self.assertTrue(out["ledger"]["reset"])
        self.assertEqual(out["ledger"]["previous_cumulative"], 4200)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["cumulative_tokens"], 0)
        self.assertEqual(doc["entries"][-1]["phase"], "compact-reset")
        self.assertEqual(doc["conversation_overhead"]["last_merge_entry_index"], 1, "其餘鍵必須原樣保留")
        self.assertFalse(list(path.parent.glob("*.part.*")))
        self.assertFalse((path.parent / f"{path.name}.lock").exists(), "鎖必須釋放")

    def test_foreign_lock_reports_lock_timeout_within_one_second_budget(self) -> None:
        """G1（QA-R2-01）：他人持鎖 ⇒ `_reset_today_ledger` 只等 `lock_timeout`（預設 1s）就誠實回
        `lock_timeout=True`，不 raise、state 已轉、帳本不動；hook 端 PENDING 出口最壞 5+1=6s < router 8s。"""
        import time
        import tools.fsm_runtime.state_loader as sl_mod
        import yaml
        repo = self.tmp / "repo"
        path = self._ledger_path_under(repo)
        path.write_text(yaml.safe_dump({"date": "d", "cumulative_tokens": 4200, "entries": [{"tokens": 4200}]}),
                        encoding="utf-8")
        before = path.read_bytes()
        (path.parent / f"{path.name}.lock").write_text("pid=0 host=test ts=fresh\n", encoding="utf-8")
        with patch.object(sl_mod, "REPO_ROOT", repo):
            self._enter_pending("IMPLEMENTATION")
            t0 = time.monotonic()
            out = self.rt.complete_auto_compact()
            elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 3.0, msg=f"reset 等鎖 {elapsed:.2f}s（上界應為 1s 量級，不是 5s）")
        self.assertEqual(self.state.current, "IMPLEMENTATION")
        self.assertFalse(out["ledger"]["reset"], msg=out)
        self.assertTrue(out["ledger"].get("lock_timeout"), msg=out)
        self.assertEqual(path.read_bytes(), before, "等鎖失敗不得動帳本")

    def test_unreadable_ledger_is_not_overwritten_and_reports_reset_false(self) -> None:
        """G4（SD-R2-03）：讀不到（PermissionError）≠ 空帳本——修前 `_reset_today_ledger` 以 `{}` 為底整本覆寫
        （6 entries＋書籤＋custom 全滅）並回 `reset=True previous_cumulative=0`（假成功）。
        以 Path.open patch 注入而非 chmod 000：root 讀得到 000 檔、Windows chmod 對讀取權無作用（鐵律三）。"""
        import tools.fsm_runtime.state_loader as sl_mod
        import yaml
        repo = self.tmp / "repo"
        path = self._ledger_path_under(repo)
        path.write_text(yaml.safe_dump({"date": "d", "cumulative_tokens": 4200, "entries": [{"tokens": 700}] * 6,
                                        "conversation_overhead": {"last_merge_entry_index": 6}, "custom": 1}),
                        encoding="utf-8")
        before = path.read_bytes()
        orig = Path.open

        def _open(p, mode="r", *a, **k):
            if p == path and "r" in mode and "+" not in mode:
                raise PermissionError(13, "Permission denied (simulated)", str(p))
            return orig(p, mode, *a, **k)
        with patch.object(sl_mod, "REPO_ROOT", repo), patch.object(Path, "open", _open):
            self._enter_pending("IMPLEMENTATION")
            out = self.rt.complete_auto_compact()
        self.assertEqual(self.state.current, "IMPLEMENTATION")
        self.assertFalse(out["ledger"]["reset"], msg=out)
        self.assertIn("error", out["ledger"], msg=out)
        self.assertEqual(path.read_bytes(), before, "讀不到時不得以空 doc 覆寫帳本")

    def test_release_and_trigger_sessions_are_recorded(self) -> None:
        """D19（DEF-200-275 第六輪；SD-02）訂正 ARCH-03 的原始判讀：本測試釘住的是
        `FSMRuntime.complete_auto_compact()` 這支**底層 API 本身**——它刻意維持「不看 session」的
        無條件釋放行為，因為它是給 `/stage-compaction` 這類「人已經確認完成」的呼叫端當建構材料，
        呼叫端本來就該對自己的呼叫負責，這支方法不該替呼叫端決定政策。

        D19 新增的「非 owner 只在 owner 已陳舊時才可釋放」政策**不收斂在這支方法**，而是收斂在
        呼叫端 `.claude/hooks/context_ledger_pre.py` 的 D4/C5 完成判定分支（見
        `tests/test_context_ledger_pre_hook.py::PendingOwnerScopeTests`，那裡才是 D19 實際生效
        的地方）。本測試的斷言因此維持不變（方法本身確實沒變）；只有這段 docstring 改寫，把
        ARCH-03「任何 session 都可釋放」這句話的適用範圍講清楚：它現在只對這支底層方法本身成立，
        不再是使用者實際感受到的 hook 層行為（後者已被 D19 收斂為 owner-scope＋陳舊判準）。"""
        import tools.fsm_runtime.snapshot as snap_mod
        with patch.object(snap_mod, "SNAPSHOT_DIR", self.tmp / "abort"):
            self.state.current = "IMPLEMENTATION"
            self.rt.trigger_auto_compact(900_000, 0.9, details={"session_id": "sess-A"})
        out = self.rt.complete_auto_compact(reset_ledger=False, observed_effective=True, released_by="sess-B")
        self.assertEqual(out["released_by_session"], "sess-B")
        self.assertEqual(out["triggered_by_session"], "sess-A")
        reason = self.state.root["decision_trace"][-1]["reason"]
        self.assertIn("released_by_session=sess-B", reason)
        self.assertIn("triggered_by_session=sess-A", reason)
        self.assertEqual(self.state.root["auto_compact_state"]["count_per_stage"], 0,
                         "他 session 釋放亦歸零 count（現行取捨，見證據檔〈把握程度〉）")


class RecoveryHintTests(_Base):
    def test_new_format_prints_session_and_context_budget(self) -> None:
        self.state.record_escalation(
            "TOKEN_BUDGET_CRITICAL: used=950000 ratio=0.95",
            details={"session_id": "abc-123", "category": rh.CATEGORY_CONTEXT_BUDGET},
        )
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, python="/venv/bin/python")
        self.assertIn("session=abc-123", text)
        self.assertIn("類別=context-budget", text)
        self.assertIn("resume-from-escalation --to SPEC_DRAFTING", text)
        self.assertIn("fallback", text)  # 無 resume_state ⇒ fallback 註明
        self.assertIn("-m tools.fsm_runtime.fsm_runtime", text)
        self.assertIn("SDD_HOOKS_DRY_RUN=1", text)

    def test_old_format_infers_category_from_reason_prefix(self) -> None:
        self.state.record_escalation("auto_compact exceeded 3 per stage 'initial'")
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT)
        self.assertIn("session=未記錄（第四輪前）", text)
        self.assertIn("類別=context-budget", text)

    def test_structural_reason_is_structural(self) -> None:
        self.state.record_escalation("consecutive_compile_fail exceeded")
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT)
        self.assertIn("類別=structural", text)
        self.assertIn("結構性", text)

    def test_resume_state_in_targets_is_used_and_every_hop_is_legal(self) -> None:
        for resume in ("SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW", "INIT", None):
            self.state.root["auto_compact_state"] = {"resume_state": resume}
            target, fallback = rh.resume_target(self.state)
            self.assertEqual(fallback, resume not in rh.RESUME_TARGETS, msg=repr(resume))
            self.assertTrue(is_transition_allowed("ESCALATION", "RESUME_VERIFICATION"))
            self.assertTrue(is_transition_allowed("RESUME_VERIFICATION", target), msg=target)
        self.assertEqual(rh.RESUME_TARGETS, {"SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW"})

    def test_command_strips_double_quotes_from_reason(self) -> None:
        cmd = rh.recovery_command(sdd_root=Path("/x"), python="/p", target="SPEC_DRAFTING",
                                  reason='say "hi"')
        self.assertNotIn('"hi"', cmd)
        self.assertIn("--reason \"say 'hi'\"", cmd)

    def test_command_neutralises_shell_metacharacters_in_reason(self) -> None:
        """SA-R4-09／SD-R2-04（P3）：bash 與 PowerShell 的雙引號都會插值 `$`／反引號／反斜線；reason 雖為機器字串，
        仍一律中和。只斷言 `--reason` 之後那段（Windows 的 sdd_root 本來就含反斜線，鐵律三）。"""
        for shell in ("posix", "powershell"):
            cmd = rh.recovery_command(sdd_root=Path("/x"), python="/p", target="SPEC_DRAFTING",
                                      reason='cost $x `id` back\\slash "q"', shell=shell)
            tail = cmd.split("--reason ", 1)[1]
            for ch in ("$", "`", "\\"):
                self.assertNotIn(ch, tail, msg=cmd)
            self.assertEqual(tail, "\"cost 'x 'id' back'slash 'q'\"", msg=cmd)

    def test_pythonw_carrier_is_swapped_for_console_python(self) -> None:
        """F3（ARCH-01／SA-R4-04；鐵律三）：Windows hook 載具是 pythonw.exe（GUI 子系統，exec form 免閃窗），
        印給人跑的指令必須換成同目錄 python.exe；PowerShell 行的 `&` 緊貼直譯器路徑。"""
        self.state.record_escalation("TOKEN_BUDGET_CRITICAL: w", details={"session_id": "win-1"})
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, python=_WIN_PYTHONW,
                                exists=lambda p: p.name == "python.exe")
        expected = str(Path(_WIN_PYTHONW).with_name("python.exe"))  # 與生產碼同一渲染
        self.assertIn(expected, text)
        self.assertNotIn("pythonw", text)
        self.assertIn(f'& "{expected}" -m tools.fsm_runtime.fsm_runtime', text)
        self.assertIn('Set-Location "', text)
        self.assertIn('bash/zsh   : cd "', text)

    def test_pythonw_without_sibling_console_python_is_kept_verbatim(self) -> None:
        """誠實：找不到 python.exe 就照印原值，不捏造一個不存在的路徑。"""
        cmd = rh.recovery_command(sdd_root=Path("/x"), python=_WIN_PYTHONW_ORPHAN, target="SPEC_DRAFTING",
                                  reason="r", exists=lambda p: False)
        self.assertIn(f'"{_WIN_PYTHONW_ORPHAN}" -m', cmd)
        self.assertEqual(rh.console_python("python3"), "python3")  # 非 pythonw ⇒ 原值直通

    def test_two_shell_lines_share_the_same_module_invocation(self) -> None:
        posix = rh.recovery_command(sdd_root=Path("/x"), python="/p", target="PR_REVIEW", reason="r")
        ps = rh.recovery_command(sdd_root=Path("/x"), python="/p", target="PR_REVIEW", reason="r",
                                 shell="powershell")
        # 鐵律三：Path("/x") 在 Windows 渲染成 "\\x"（windows-compat-ci 實測轉紅），期望值與生產碼同一渲染
        root = str(Path("/x"))
        self.assertTrue(posix.startswith(f'cd "{root}" ; "/p" -m tools.fsm_runtime.fsm_runtime'), posix)
        self.assertTrue(ps.startswith(f'Set-Location "{root}"; & "/p" -m tools.fsm_runtime.fsm_runtime'), ps)
        self.assertEqual(posix.split(" -m ", 1)[1], ps.split(" -m ", 1)[1])


class RecoveryHintMeasurementTests(_Base):
    """D16（DEF-200-275 第五輪 SA-02）：recovery_hint 印目前真實水位——pre hook／session_start
    傳入量測時印真實 used/window/來源；量不到時印「尚無可用 usage」；既有簽名呼叫零改動即可繼續用。"""

    def test_prints_real_usage_when_measurement_present(self) -> None:
        self.state.record_escalation("TOKEN_BUDGET_CRITICAL: x", details={"session_id": "s-1"})

        class _M:
            used = 123456

        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, measurement=_M(),
                                window=1_000_000, source="指定值")
        self.assertIn("目前本 session 真實 used=123,456 window=1,000,000 來源=指定值", text)

    def test_prints_unmetered_when_no_measurement(self) -> None:
        self.state.record_escalation("TOKEN_BUDGET_CRITICAL: x", details={"session_id": "s-1"})
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT)
        self.assertIn("目前本 session 尚無可用 usage（新 session 首擊或 compact 後）", text)

    def test_measurement_with_none_used_is_treated_as_unmetered(self) -> None:
        self.state.record_escalation("TOKEN_BUDGET_CRITICAL: x")

        class _MNone:
            used = None

        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, measurement=_MNone(),
                                window=1_000_000, source="指定值")
        self.assertIn("目前本 session 尚無可用 usage（新 session 首擊或 compact 後）", text)

    def test_legacy_call_signature_still_works(self) -> None:
        """既有簽名呼叫零改動：不傳新參數仍可正常呼叫、不 crash，既有恢復指令內容照舊都在。"""
        self.state.record_escalation("x")
        text = rh.recovery_hint(self.state, sdd_root=_SDD_ROOT, python="/venv/bin/python")
        self.assertIn("resume-from-escalation --to", text)


class ResumeFromEscalationTests(_Base):
    def test_full_path_records_trace_and_resolution(self) -> None:
        self.state.record_escalation("TOKEN_BUDGET_CRITICAL: x", details={"session_id": "s"})
        out = self.rt.resume_from_escalation("SPEC_DRAFTING", reason="operator verified /context 9%")
        self.assertEqual(self.state.current, "SPEC_DRAFTING")
        self.assertEqual(out["via"], "RESUME_VERIFICATION")
        trace = self.state.root["decision_trace"]
        self.assertEqual([e["trigger"] for e in trace[-2:]], ["human_resume", "human_resume"])
        self.assertEqual([e["to"] for e in trace[-2:]], ["RESUME_VERIFICATION", "SPEC_DRAFTING"])
        last = self.state.root["escalation_history"][-1]
        self.assertIsNotNone(last["resolved_at"])
        self.assertIn("operator verified", last["resolution"])
        reloaded = load_state("rh-proj", path=self.state_path)
        self.assertEqual(reloaded.current, "SPEC_DRAFTING")

    def test_noop_when_not_escalated(self) -> None:
        self.state.current = "IMPLEMENTATION"
        out = self.rt.resume_from_escalation("SPEC_DRAFTING", reason="x")
        self.assertTrue(out["noop"])
        self.assertEqual(self.state.current, "IMPLEMENTATION")

    def test_illegal_target_or_empty_reason_raise(self) -> None:
        self.state.record_escalation("x")
        with self.assertRaises(ValueError):
            self.rt.resume_from_escalation("INIT", reason="x")
        with self.assertRaises(ValueError):
            self.rt.resume_from_escalation("SPEC_DRAFTING", reason="  ")
        self.assertEqual(self.state.current, "ESCALATION")

    def test_cli_subcommand_contract(self) -> None:
        """`--to INIT` rc≠0、缺 `--reason` rc≠0、正常呼叫 rc=0 且 state 落盤。"""
        self.state.record_escalation("TOKEN_BUDGET_CRITICAL: cli")
        from tools.fsm_runtime.state_loader import save_state
        save_state(self.state)
        import tools.fsm_runtime.state_loader as sl
        base = [sys.executable, "-c",
                "import sys; sys.path.insert(0, sys.argv[1]);"
                "import tools.fsm_runtime.state_loader as sl; from pathlib import Path;"
                "sl.DEFAULT_STATE_DIR = Path(sys.argv[2]);"
                "sys.argv = ['fsm_runtime'] + sys.argv[3:];"
                "from tools.fsm_runtime.fsm_runtime import _cli; sys.exit(_cli())",
                str(_SDD_ROOT), str(self.tmp)]
        # 🔴 子行程必須繼承 conftest 的隔離旗標並顯式關遙測：`transition()` 的 fire 遙測預設 ON，
        # 會把凍結 governance/rules/*.yaml 以 yaml.safe_dump 重寫（本輪實測：R-9.2 被改形態＋fire_count
        # 被灌），meta-loop ledger 亦導向 tmp。最小 env 正是污染凍結本體的形狀，不得再用。
        env = dict(os.environ)
        env.update({
            "SDD_PROJECT": "rh", "PYTHONUTF8": "1",
            "SDD_ENABLE_RULE_FIRE_TELEMETRY": "0", "SDD_ENABLE_RULE_CATCH_TELEMETRY": "0",
            "SDD_META_LEDGER_PATH": str(self.tmp / "meta-loop-ledger.yaml"),
            "SDD_SPEC_MONITOR": "0",
        })
        # 讓 CLI 的 bootstrap 讀到本測試的狀態檔：專案名 rh → FSM-STATE-rh.yaml
        bad_to = subprocess.run(base + ["resume-from-escalation", "--to", "INIT", "--reason", "x"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertNotEqual(bad_to.returncode, 0, bad_to.stderr)
        no_reason = subprocess.run(base + ["resume-from-escalation", "--to", "SPEC_DRAFTING"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertNotEqual(no_reason.returncode, 0, no_reason.stderr)
        ok = subprocess.run(base + ["resume-from-escalation", "--to", "SPEC_DRAFTING",
                                    "--reason", "cli test"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        payload = json.loads(ok.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["to"], "SPEC_DRAFTING")
        self.assertEqual(sl.load_state("rh", path=self.state_path).current, "SPEC_DRAFTING")


if __name__ == "__main__":
    unittest.main()
