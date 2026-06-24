"""Runtime facade used by hooks — one-call init + apply + save."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from .event_reconciler import reconcile
from .snapshot import save_abort_report, save_auto_snapshot
from .state_loader import FSMState, load_state, project_from_env, save_state
from .transition_rules import (
    IMPL_MAX_TEST_FAIL_WITHOUT_SPEC_CHANGE,
    MAX_AUTO_COMPACT_PER_STAGE,
    OBSERVATION_STATES,
    RETRY_LIMITS,
    SPEC_AUDIT_MAX_PER_STAGE,
    TransitionError,
    assert_transition,
    next_state_on_gate_fail,
    next_state_on_gate_pass,
    should_escalate_for_implementation,
)

_SPEC_TARGET_PREFIXES = (
    "docs/01_requirements/",
    "docs/02_architecture/",
    "docs/03_testing/",
)

# ── Phase G M2 / B-axis L4：有界自動恢復「接入 FSM 主迴圈」開關 ──────────────
# improving_15 W-15-1：把既有 enter_auto_recovery（ESCALATION → AUTO_RECOVERY_ATTEMPT，
# Rule 9.14 有界、已被五軌 TLC 證為有界停機之既存邊）從「proposal-only / 需 orchestrator
# 手動觸發」升級為「gate retry 耗盡時由 record_gate_result 自動嘗試」，使 B 軸流程自治
# 由 L3（失敗即停等人）升 L4（自動有界恢復，人僅在 escalation 介入）。
#
# v0.22（improving_57 B 軌 / B-axis L3→L4 常態化）：預設 **ON**——未設環境變數時自動有界
# 恢復為常態運作模式（流程自治由「失敗即停等人 opt-in」升為「有界自動恢復 default」）。
# 仍保留**顯式 opt-out**（SDD_ENABLE_AUTO_RECOVERY=0/false/no/off → 還原 v0.05 停機行為），
# 供除錯/保守場景關閉。轉態邊（ESCALATION→AUTO_RECOVERY_ATTEMPT）與 _HAPPY_PATH/*.tla
# **零變更**（improving_15 已模型化、五軌 TLC 已證有界），本輪僅翻轉「誰觸發」的預設。
# 採環境變數開關符 SDD 框架既有慣例（SDD_PROJECT / SDD_RUN_TLC / SDD_GATE_DRY_RUN…，
# FSMRuntime.__init__ 僅收 state、無 config 物件）。fail-closed 不變：enter_auto_recovery 內
# 已含 Rule 9.14 全部守界（structural 禁、≤3/session、≤1/同因、失敗→ESCALATION_FINAL），
# 任何 refusal/例外一律落回 ESCALATION 等人，絕不弱化紅線。
_AUTO_RECOVERY_ENV = "SDD_ENABLE_AUTO_RECOVERY"


def _auto_recovery_enabled() -> bool:
    """True 為預設（unset → ON，v0.22 常態化）；僅顯式 falsy（0/false/no/off）→ OFF opt-out。"""
    val = os.environ.get(_AUTO_RECOVERY_ENV, "").strip().lower()
    if val == "":
        return True  # v0.22 預設 ON（B-axis L4 常態化）
    return val in {"1", "true", "yes", "on"}


# W-16-1 / B-axis L5：規則自演化「自動提議」開關（同 _AUTO_RECOVERY_ENV env-flag 慣例；
# FSMRuntime.__init__ 無 config 物件）。預設 OFF＝learn 分支行為逐字同 v0.06（純轉態）。
_SLV_AUTO_PROPOSE_ENV = "SDD_ENABLE_SLV_AUTO_PROPOSE"


def _slv_auto_propose_enabled() -> bool:
    """True iff SDD_ENABLE_SLV_AUTO_PROPOSE is set to a truthy value (1/true/yes/on)."""
    return os.environ.get(_SLV_AUTO_PROPOSE_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


# W-17-1 / B-axis L5（鷹架代謝「自動提議退役」開關，鏡像 _SLV_AUTO_PROPOSE_ENV）。預設
# OFF＝enter_scaffold_gc 行為逐字同 v0.07（只記 tracking、不算 GC）。flag ON 時進代謝態
# 自動跑 run_gc 產 SCAFFOLD-ROI proposed 提議——退役仍須人工 set_maturity(reviewed_by=)
# （R-9.20 #11）。
_SCAFFOLD_GC_AUTO_PROPOSE_ENV = "SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE"


def _scaffold_gc_auto_propose_enabled() -> bool:
    """True iff SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE is truthy (1/true/yes/on)."""
    return os.environ.get(_SCAFFOLD_GC_AUTO_PROPOSE_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


# W-18-1 / B-axis L5（規則命中遙測「on-watch fire 記帳」開關，鏡像 _SCAFFOLD_GC_AUTO_PROPOSE_ENV）。
# 預設 OFF＝transition() 行為逐字同 v0.08（不記 fire）。flag ON 時每次 transition 進態後對
# load_for_state(dst) 命中規則各記一次 on-watch fire，使 scaffold_roi.fire_count 真實累積
# （閉合 DEF-17-001 點名的「fire_count=0」根因，GC 才有非零資料驅動退役提議）。獨立於
# SCAFFOLD_GC flag：per-transition YAML 寫入有 I/O 成本，與週期性 GC 是可分離 opt-in。
_RULE_FIRE_TELEMETRY_ENV = "SDD_ENABLE_RULE_FIRE_TELEMETRY"


def _rule_fire_telemetry_enabled() -> bool:
    """True iff SDD_ENABLE_RULE_FIRE_TELEMETRY is truthy (1/true/yes/on)."""
    return os.environ.get(_RULE_FIRE_TELEMETRY_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


# W-19-2 / B-axis L5（規則命中遙測「catch 側記帳」開關，鏡像 fire 側 flag）。預設 OFF＝
# escalation 路徑行為逐字同 v0.09（不記 catch）。flag ON 時 escalation 真實發生且呼叫端明確
# 歸因（attributed_rule_ids）→ 對 failure_mode 已定義的規則記 on-attribution catch（閉合
# DEF-18-001 catch 側語意未定義）。獨立於 fire flag：catch 是 escalation 稀疏事件、與 per-
# transition fire 記帳是可分離 opt-in。
_RULE_CATCH_TELEMETRY_ENV = "SDD_ENABLE_RULE_CATCH_TELEMETRY"


def _rule_catch_telemetry_enabled() -> bool:
    """True iff SDD_ENABLE_RULE_CATCH_TELEMETRY is truthy (1/true/yes/on)."""
    return os.environ.get(_RULE_CATCH_TELEMETRY_ENV, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _reset_today_ledger() -> dict:
    """Zero today's CONTEXT-LEDGER cumulative_tokens; keep entries history.

    Used by complete_auto_compact() so the next PreToolUse won't re-trigger
    the 90% AUTO_COMPACT loop after a successful compaction.
    Returns: {"reset": bool, "path": str|None, "previous_cumulative": int}
    """
    import datetime as _dt
    from .state_loader import REPO_ROOT  # local to avoid cycles
    try:
        import yaml  # type: ignore
    except Exception:
        return {"reset": False, "path": None, "previous_cumulative": 0}
    ledger_dir = REPO_ROOT / "build" / "reports" / "fsm"
    path = ledger_dir / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
    if not path.exists():
        return {"reset": False, "path": str(path), "previous_cumulative": 0}
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    prev = int(doc.get("cumulative_tokens", 0))
    entries = doc.get("entries") or []
    entries.append({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "phase": "compact-reset",
        "tool": "FSMRuntime",
        "target": "complete_auto_compact",
        "tokens": 0,
        "previous_cumulative": prev,
    })
    doc["cumulative_tokens"] = 0
    doc["entries"] = entries
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    import os as _os
    _os.replace(tmp, path)
    return {"reset": True, "path": str(path), "previous_cumulative": prev}



_STATES_ALLOWING_SPEC_WRITE = {
    "SPEC_DRAFTING",
    "SPEC_AUDIT",
    "SPEC_REGRESSION_CHECK",
    "RESUME_VERIFICATION",
    "INIT",
    "SCENARIO_DETECT",
    "AGENT_LOAD",
}


class FSMRuntime:
    """High-level API used by hook scripts and tests."""

    def __init__(self, state: FSMState):
        self.state = state

    @classmethod
    def bootstrap(cls, project: Optional[str] = None) -> "FSMRuntime":
        name = project or project_from_env()
        return cls(load_state(name))

    # ----- state mutation helpers -----
    def transition(
        self,
        dst: str,
        *,
        reason: str = "",
        spec_refs: Optional[list] = None,
        agents_consulted: Optional[list] = None,
        trigger: str = "transition",
    ) -> None:
        assert_transition(self.state.current, dst)
        src = self.state.current
        self.state.current = dst
        # ACT-023: stamp / clear HUMAN_PENDING tracking on state transitions.
        if dst == "HUMAN_PENDING" and src != "HUMAN_PENDING":
            from .timeout_checker import mark_entered_now  # local to avoid cycles
            mark_entered_now(self.state)
        elif src == "HUMAN_PENDING" and dst != "HUMAN_PENDING":
            from .timeout_checker import clear_tracking
            clear_tracking(self.state)
        # ACT-025: record decision trace (best-effort — never block transition).
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state=dst,
                reason=reason,
                spec_refs=spec_refs,
                agents_consulted=agents_consulted,
                trigger=trigger,
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        # W-18-1：規則命中遙測接入主迴圈（flag-gated、fail-closed、進態後 side-effect）。
        # flag ON → 對 load_for_state(dst) 命中規則各記一次 on-watch fire，使 scaffold_roi.
        # fire_count 真實累積（閉合 DEF-17-001 fire_count=0 根因）。**只增計數、永不
        # set_maturity**（退役仍 🔴 人工，R-9.20 #11）。flag OFF → 行為逐字同 v0.08＝零退化。
        # fail-closed：記帳任何失敗絕不阻塞已完成的轉態（轉態已 save_state 落定）。
        if _rule_fire_telemetry_enabled():
            try:
                from . import rule_loader as _rl  # local import：避 top-level cycle
                _rl.record_state_fires(dst)
            except Exception:  # noqa: BLE001 — fail-closed：轉態已完成，記帳失敗不回滾
                pass
        # Phase I M2 / ACT-064：runtime monitor 補位（opt-in via SDD_SPEC_MONITOR）。
        # 跳過 emergency/observation/monitor 目標以避免遞迴與重複觸發。
        if dst not in self._BLOCKING_STATES and dst not in OBSERVATION_STATES \
                and dst != "MONITOR_VIOLATION" and dst != "AUTO_COMPACT_PENDING":
            self._maybe_run_spec_monitor()

    # W-39（DEF-39-001 分母正當性）：具「唯一生產 escalation 落點 + 可結構化歸因 catch」的規則
    # 集合＝catch 接線的**正當分母 (escalation-scoped denominator)**。SSOT 來源＝本檔 9 個生產
    # record_escalation 落點之 _record_escalation_catches([...]) 接線：7 個接線歸因 R-9.7 / R-9.1 /
    # R-9.3 / R-9.2 / R-SELF-STRIDE / R-9.21 / R-9.22（即本集合）；另 2 落點正交無規則
    # （implementation-budget-exceeded、spec_patch unable-to-draft），不歸因。（不釘行號——additive
    # 編輯會漂移；以 _record_escalation_catches 呼叫為準。）其餘 32 條非 deprecated 規則由 hook /
    # lint / arch_fitness / TLC / meta-loop guard / 人工守門，**本質非 FSM-escalation catch-可歸因**，
    # 不應計入 catch 接線分母（catch_count 恆 0 非缺口）。test_w39_coverage_denominator.py 以靜態掃描
    # 本檔 _record_escalation_catches([...]) 接線 SSOT-鎖此集合，防漂移。
    _ESCALATION_ATTRIBUTABLE_RULE_IDS = frozenset({
        "R-9.1", "R-9.2", "R-9.3", "R-9.7", "R-9.21", "R-9.22", "R-SELF-STRIDE",
    })
    # W-54-1（守門機制五分類 SSOT，improving_55 / DEF-54-001）：enforcement_mechanism 取值的
    # 權威 enum + 各值「自動可度量性」語意（comprehensive_governance_coverage 誠實分母依據）。
    # W-39-1 五分類機讀化：A=escalation / B=hook / C=lint_tlc / D=meta_loop / E=manual。
    # test_governance_coverage.py 以「escalation 類 == _ESCALATION_ATTRIBUTABLE_RULE_IDS」交叉鎖
    # 防兩 SSOT 漂移。
    _ENFORCEMENT_MECHANISMS = frozenset({"escalation", "hook", "lint_tlc", "meta_loop", "manual"})
    # escalation：catch 側可自動度量（沿用 catch_attribution_coverage）。
    # hook/lint_tlc/meta_loop：守門分類在位，但「runtime 有效性」度量 justified-deferred
    #   （無消費者 + 違 Rule 2 speculative + meta_loop 恐觸 TLC）。
    # manual：人工/憲法，本質不可自動度量（人是否遵守簽核）→ 誠實排除於自動分母。
    _AUTO_MEASURABLE_MECHANISMS = frozenset({"escalation"})
    _DEFERRED_RUNTIME_MECHANISMS = frozenset({"hook", "lint_tlc", "meta_loop"})
    _NON_AUTO_MEASURABLE_MECHANISMS = frozenset({"manual"})

    def _record_escalation_catches(self, attributed_rule_ids: list) -> None:
        """W-19-2（catch 側契約接入）：escalation 真實發生時，對「明確歸因 + failure_mode 已
        定義」的規則記一次 on-attribution catch（rule_loader.record_state_catches）。

        接在 record_escalation 呼叫點（**非** transition()）——因 record_escalation 直接設
        current=ESCALATION、繞過 transition()，catch 記帳須跟著攔截事件的真實觸發點才不漏記。
        flag-gated（SDD_ENABLE_RULE_CATCH_TELEMETRY 預設 OFF＝行為逐字同 v0.09）；fail-closed
        （記帳任何失敗絕不阻塞已落定的 escalation）。**無 FSM 狀態副作用**＝純記帳、零新增
        reachable 邊、不碰 *.tla。紅線：只增 catch_count、永不 set_maturity（R-9.20 #11）。
        空歸因 / 無 failure_mode → record_state_catches 內 fail-closed 不記（DEF-18-001 寧缺勿濫）。
        """
        if not _rule_catch_telemetry_enabled() or not attributed_rule_ids:
            return
        try:
            from . import rule_loader as _rl  # local import：避 top-level cycle
            _rl.record_state_catches(attributed_rule_ids)
        except Exception:  # noqa: BLE001 — fail-closed：escalation 已落定，記帳失敗不回滾
            pass

    def escalate_human_pending_timeout(self, *, reason: str) -> None:
        """ACT-023 / R-9.7.2：HUMAN_PENDING wall-clock 逾時（≥168h）自動進 ESCALATION 的單一入口。

        把「record_escalation + catch 歸因」收斂到 runtime 同一落點（與 R-9.1 gate-retry /
        R-9.2 auto_compact / R-9.21 monitor / R-9.22 spec_patch 四條既有接線同範式）。供
        session_start hook 委派呼叫——hook 偵測逾時，但 catch 記帳須跟著攔截事件的真實
        escalation 落點才不漏記。W-37-1（DEF-19-001 catch 覆蓋 4/39→5/39）。
        """
        self.state.record_escalation(reason)
        # W-37-1：HUMAN_PENDING 逾時 ≥168h → ESCALATION 即 R-9.7（9.7.2）守望的失敗模式真實發生，
        # 結構化歸因到 R-9.7（無歧義映射）。**不含 9.7.3**（AUTO_COMPACT per-stage 歸 R-9.2，見
        # trigger_auto_compact 的 R-9.2 catch），杜絕雙重歸因（DEF-18-001）。flag OFF＝不記（零退化）。
        self._record_escalation_catches(["R-9.7"])

    def _maybe_run_spec_monitor(self) -> None:
        try:
            from . import spec_monitor
        except Exception:  # noqa: BLE001
            return
        if not spec_monitor.enabled():
            return
        result = spec_monitor.check_invariants(self.state)
        if result.ok:
            return
        try:
            spec_monitor.write_violation_report(result, state_name=self.state.current)
        except Exception:  # noqa: BLE001
            pass
        # 進 MONITOR_VIOLATION → ESCALATION（runtime monitor 補位）
        try:
            self.enter_monitor_violation(
                invariant=result.violations[0] if result.violations else "unknown",
                detail="; ".join(result.violations)[:300],
            )
            self.exit_monitor_violation(reason="spec_monitor invariant breach")
        except Exception:  # noqa: BLE001
            pass

    def run_spec_monitor(self, *, escalate: bool = True) -> dict:
        """主動執行 runtime monitor（orchestrator / 驗收流程顯式呼叫）。

        回傳 {ok, violations, escalated, report_path?}。escalate=True 且偵測到
        違反 → 進 MONITOR_VIOLATION → ESCALATION。
        """
        from . import spec_monitor
        result = spec_monitor.check_invariants(self.state)
        payload: dict = {"ok": result.ok, "violations": result.violations, "escalated": False}
        if result.ok:
            return payload
        try:
            payload["report_path"] = spec_monitor.write_violation_report(
                result, state_name=self.state.current
            )
        except Exception:  # noqa: BLE001
            payload["report_path"] = None
        if escalate and self.state.current not in self._BLOCKING_STATES:
            self.enter_monitor_violation(
                invariant=result.violations[0], detail="; ".join(result.violations)[:300]
            )
            self.exit_monitor_violation(reason="run_spec_monitor invariant breach")
            payload["escalated"] = True
        return payload

    def record_gate_result(self, gate: str, result: str, reason: str = "") -> dict:
        result = result.upper()
        payload: dict = {"gate": gate, "result": result}
        if result == "PASS":
            self.state.reset_retry(gate)
            nxt = next_state_on_gate_pass(gate)
            self.transition(
                nxt,
                reason=f"{gate} PASS",
                trigger="gate_pass",
            )
            payload["next_state"] = nxt
            return payload

        entry = self.state.retry(gate)
        new_count = self.state.increment_retry(gate, reason or f"{gate} FAIL")
        same_pattern_count = 0
        if gate == "PR_REVIEW":
            # ACT-021: semantic same-pattern detection replaces string equality.
            try:
                from .pattern_matcher import is_same_pattern  # local import
            except Exception:  # noqa: BLE001
                is_same_pattern = None  # fallback to legacy
            prev_pattern = entry.get("last_failure_pattern")
            if is_same_pattern is not None:
                matched = is_same_pattern(prev_pattern, reason)
            else:
                matched = prev_pattern == reason
            if matched:
                same_pattern_count = int(entry.get("same_pattern_count", 0)) + 1
            else:
                same_pattern_count = 1
            entry["same_pattern_count"] = same_pattern_count
            entry["last_failure_pattern"] = reason
            # Persist full pattern history for debug / audit (capped at 20 entries).
            patterns = entry.setdefault("patterns", [])
            patterns.append({
                "attempt": new_count,
                "reason": reason,
                "matched_prev": bool(matched),
                "same_pattern_count": same_pattern_count,
            })
            if len(patterns) > 20:
                del patterns[0:len(patterns) - 20]
        nxt, escalate = next_state_on_gate_fail(
            gate, new_count, same_pattern_count=same_pattern_count
        )
        if escalate:
            esc_reason = (
                f"{gate} retry_count {new_count} ≥ {RETRY_LIMITS.get(gate, 'N/A')}"
            )
            self.state.record_escalation(esc_reason)
            # W-19-2：gate retry budget 耗盡 → ESCALATION 即 R-9.1 守望的失敗模式真實發生，
            # 結構化歸因到 R-9.1（無歧義映射，非時序猜測）。flag OFF＝不記（零退化）。
            self._record_escalation_catches(["R-9.1"])
            # W-15-1 / B-axis L4：flag-gated 有界自動恢復接入。預設 OFF＝行為同 v0.05
            # （停在 ESCALATION 等人）。ON 時：對「可恢復 gate」自動嘗試既有
            # ESCALATION → AUTO_RECOVERY_ATTEMPT 邊（TLA T_EnterAutoRecover 已模型化、
            # 五軌 TLC 已證有界停機）。Rule 9.14 守界全在 enter_auto_recovery 內：
            #   • structural / bounds 耗盡 → enter_auto_recovery 自行轉 ESCALATION_FINAL
            #   • 任何例外 → fail-closed 停在 ESCALATION（不弱化紅線）
            # gate ∈ _GATE_RESUMABLE_TARGETS 預檢：避免 enter_auto_recovery 先轉態再於
            # record_attempt_start 因 resume_state 非白名單 raise，致 FSM 卡在
            # AUTO_RECOVERY_ATTEMPT 的撕裂狀態。RETRY_LIMITS 4 gate 全在白名單，此檢為防護。
            if _auto_recovery_enabled() and self._gate_is_resumable(gate):
                # 以「實際失敗 reason」作 diagnose 依據（transient/structural 分類靠它），
                # 非 gate-exhaust 格式字串；reason 缺時退回 esc_reason（多會診為 structural
                # → enter_auto_recovery 自轉 ESCALATION_FINAL，安全保守）。
                try:
                    payload["auto_recovery"] = self.enter_auto_recovery(
                        escalation_reason=(reason or esc_reason),
                        resume_state=gate,
                    )
                except Exception as exc:  # noqa: BLE001 — fail-closed 停在 ESCALATION
                    payload["auto_recovery"] = {
                        "entered": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
        else:
            try:
                self.transition(
                    nxt,
                    reason=f"{gate} FAIL (retry {new_count}) — {reason}".strip(" —"),
                    trigger="gate_fail",
                )
            except TransitionError as exc:
                # M2 QA Round-2 P1-2: target state not on happy path — log the
                # blocked transition so retry_count and decision_trace remain
                # consistent for cross-session audit.
                try:
                    self.state.append_decision_trace(
                        from_state=self.state.current,
                        to_state=self.state.current,  # not transitioned
                        reason=f"gate_fail transition rejected: {gate} -> {nxt}: {exc}",
                        trigger="gate_fail_blocked",
                    )
                except Exception:  # noqa: BLE001
                    pass
                save_state(self.state)
        payload.update({"retry_count": new_count, "next_state": self.state.current})
        if escalate:
            payload["escalated"] = True
        return payload

    def record_spec_audit(self) -> dict:
        """Called when PR_REVIEW same_pattern threshold triggers SPEC_AUDIT."""
        cum = self.state.cumulative()
        current = int(cum.get("spec_audit_total_count", 0)) + 1
        cum["spec_audit_total_count"] = current
        pr_entry = self.state.retry("PR_REVIEW")
        pr_entry["spec_audit_count"] = int(pr_entry.get("spec_audit_count", 0)) + 1
        if pr_entry["spec_audit_count"] >= SPEC_AUDIT_MAX_PER_STAGE:
            self.state.record_escalation(
                f"SPEC_AUDIT executed {pr_entry['spec_audit_count']} times without resolution"
            )
            # W-38-2（DEF-19-001 catch 覆蓋 6/39→7/39）：SPEC_AUDIT 於上限內無法解消 AC vs Test
            # Contract 矛盾 → ESCALATION 即 R-9.3（邏輯一致性防護）守望的失敗模式真實發生，結構化歸因。
            # **僅此 record_spec_audit 耗盡落點**：不含 check_implementation_budget 的
            # implementation-budget-exceeded 直接 escalate（正交、無規則）與 R-9.1 gate-retry 落點，
            # 杜絕雙重歸因（DEF-18-001）。flag OFF＝不記（零退化）。
            self._record_escalation_catches(["R-9.3"])
            save_state(self.state)
            return {"escalated": True}
        self.transition(
            "SPEC_AUDIT",
            reason=f"PR_REVIEW same-pattern reached threshold (audit_count={pr_entry['spec_audit_count']})",
            trigger="spec_audit",
        )
        return {"escalated": False, "audit_count": pr_entry["spec_audit_count"]}

    def record_spec_frozen(self, stage: str, spec_docs: list[str]) -> None:
        self.state.record_spec_frozen(stage, spec_docs)
        self.transition(
            "SPEC_FROZEN",
            reason=f"Stage frozen: {stage}",
            spec_refs=list(spec_docs or []),
            trigger="spec_frozen",
        )

    def reconcile_ci_events(self) -> list[str]:
        return reconcile(self.state)

    # ----- guardrails used by pre-tool hook -----
    # M4 QA Round-6 P1-5：deny 清單以 emergency-terminal 為基準；
    # OBSERVATION_STATES（PRODUCTION_SIGNAL / LEARNING_COMMIT）不在此 deny 清單，
    # 是顯式非阻擋宣告 — 這些觀測狀態下工具呼叫照常允許，僅由專屬 FSM API
    # 控制進出（enter_production_signal / enter_learning_commit）。
    # Phase G M1 / ACT-034: ESCALATION_FINAL is terminal-like — only human can
    # move out (RESUME_VERIFICATION or TERMINATED). Blocking like ESCALATION.
    _BLOCKING_STATES = frozenset(
        {"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "TOKEN_BUDGET_CRITICAL"}
    )

    def assert_tool_allowed(self, tool: str, target: Optional[str]) -> None:
        # deny 清單；OBSERVATION_STATES 刻意不在此 — 參見 transition_rules.OBSERVATION_STATES
        if self.state.current in self._BLOCKING_STATES:
            raise TransitionError(
                f"state {self.state.current} blocks all tool calls until human intervenes"
            )
        # sanity-check：OBSERVATION_STATES 不得意外落入 BLOCKING_STATES
        assert not (self._BLOCKING_STATES & OBSERVATION_STATES), (
            "invariant violated: OBSERVATION_STATES leaked into _BLOCKING_STATES"
        )
        if self.state.current == "AUTO_COMPACT_PENDING":
            self._assert_allowed_under_auto_compact(tool, target)
            return
        if tool in {"Write", "Edit"} and target:
            normalized = target.replace("\\", "/")
            if any(prefix in normalized for prefix in _SPEC_TARGET_PREFIXES):
                if self.state.current not in _STATES_ALLOWING_SPEC_WRITE:
                    raise TransitionError(
                        f"state {self.state.current} does not allow modifying spec files under {_SPEC_TARGET_PREFIXES}"
                    )

    @staticmethod
    def _assert_allowed_under_auto_compact(tool: str, target: Optional[str]) -> None:
        """Under AUTO_COMPACT_PENDING, only allow compact-related operations."""
        normalized = (target or "").replace("\\", "/")
        # Allow Read broadly (needed to run the compaction skill).
        if tool == "Read":
            return
        # Allow writing snapshot / compaction reports / FSM state updates.
        if tool in {"Write", "Edit"}:
            allowed_prefixes = (
                "build/reports/abort/CONTEXT-SNAPSHOT",
                "build/reports/compaction/",
                "build/reports/fsm/",
            )
            if any(p in normalized for p in allowed_prefixes):
                return
        # Allow Bash to run compaction / python fsm_runtime CLI.
        if tool == "Bash":
            return
        raise TransitionError(
            "state AUTO_COMPACT_PENDING — 只允許 /stage-compaction 相關操作。"
            " 請呼叫 Skill: stage-compaction 完成壓縮後繼續。"
        )

    def check_implementation_budget(self) -> dict:
        """Evaluate implementation budget; escalate or transition to SPEC_AUDIT.

        QA Round-3 P1-01: `should_escalate_for_implementation` can return
        ``(False, "test_fail_threshold → SPEC_AUDIT")`` when 5 consecutive test
        failures occur without a spec change. Previously the reason was only
        bubbled to the caller — no state transition happened, so the SPEC_AUDIT
        protection was a paper rule. We now detect the SPEC_AUDIT sentinel and
        invoke ``record_spec_audit()`` so the FSM actually moves.
        """
        budget = self.state.implementation_budget()
        escalate, reason = should_escalate_for_implementation(budget)
        if escalate:
            self.state.record_escalation(reason or "implementation budget exceeded")
            save_state(self.state)
            return {"escalated": True, "reason": reason}
        payload: dict = {"escalated": False, "reason": reason}
        if reason and "SPEC_AUDIT" in reason and self.state.current == "IMPLEMENTATION":
            audit = self.record_spec_audit()
            payload["spec_audit"] = audit
            if audit.get("escalated"):
                payload["escalated"] = True
            payload["next_state"] = self.state.current
        return payload

    # ----- auto-compact (90% threshold) -----
    def current_stage_key(self) -> str:
        """Return identifier for the current stage (ACT-026 rate-limit scope).

        QA Round-3 P2-03: promoted from `_current_stage_key`. The private form
        was being reached across module boundaries (`subagent_contract`), which
        defeats encapsulation. Public name is stable API; old name retained as
        a thin alias below for one release to avoid breaking external callers.
        """
        stages = self.state.root.get("frozen_stages") or []
        if stages:
            last = stages[-1]
            key = last.get("stage") if isinstance(last, dict) else None
            if key:
                return str(key)
        return "initial"

    # Deprecated alias — remove after downstream tooling migrates.
    _current_stage_key = current_stage_key

    def trigger_auto_compact(self, cumulative_tokens: int, ratio: float) -> dict:
        """Enter AUTO_COMPACT_PENDING, persist Snapshot. Idempotent.

        ACT-026: enforce MAX_AUTO_COMPACT_PER_STAGE — if the current stage has
        already triggered auto-compact 3 times, stop compacting and escalate.

        Safety: once the FSM is in a blocking terminal state (ESCALATION /
        TERMINATED / TOKEN_BUDGET_CRITICAL / RELEASE), further auto-compact
        requests are NO-OPs — they must not record another escalation nor
        attempt any transition. QA Round-3 P2-06 widened this guard: RELEASE
        is past-the-point (no compact needed), and TOKEN_BUDGET_CRITICAL
        must escalate rather than compact (Rule 9.9).
        """
        if self.state.current in {"ESCALATION", "TERMINATED", "TOKEN_BUDGET_CRITICAL", "RELEASE"}:
            return {
                "already_pending": False,
                "noop": True,
                "escalated": self.state.current != "RELEASE",
                "reason": f"FSM already in {self.state.current}; auto_compact suppressed",
            }
        if self.state.current == "AUTO_COMPACT_PENDING":
            return {"already_pending": True, "snapshot": None}
        resume_state = self.state.current
        auto = self.state.root.setdefault("auto_compact_state", {})
        # P2 fix: materialize max_per_stage so FSM-STATE overrides take effect
        # and appear explicitly in persisted state.
        auto.setdefault("max_per_stage", MAX_AUTO_COMPACT_PER_STAGE)

        # ACT-026: reset per-stage counter if stage has changed.
        stage_key = self.current_stage_key()
        if auto.get("stage_key") != stage_key:
            auto["stage_key"] = stage_key
            auto["count_per_stage"] = 0
        projected = int(auto.get("count_per_stage", 0)) + 1
        max_per_stage = int(auto.get("max_per_stage", MAX_AUTO_COMPACT_PER_STAGE))
        if projected > max_per_stage:
            reason = (
                f"auto_compact exceeded {max_per_stage} per stage '{stage_key}' "
                "— 可能引用文件過大或 stage 需拆分；拒絕再次 compact"
            )
            self.state.record_escalation(reason)
            # W-20-1（catch 覆蓋補強 DEF-19-001）：per-stage auto_compact 超限 → ESCALATION 即
            # R-9.2（Context Budget）守望的失敗模式真實發生，結構化歸因到 R-9.2（無歧義映射，
            # 非時序猜測）。flag OFF＝不記（零退化）；fail-closed；只增 catch_count（R-9.20 #11）。
            self._record_escalation_catches(["R-9.2"])
            save_state(self.state)
            # CLAUDE.md Rule 9.5 — ESCALATION 必須產出 Abort Report
            abort_report_path = None
            try:
                abort_report_path = save_abort_report(
                    self.state,
                    reason=reason,
                    category="auto-compact-rate-limit",
                    extra_context={
                        "count_per_stage": projected,
                        "max_per_stage": max_per_stage,
                        "stage_key": stage_key,
                        "cumulative_tokens": cumulative_tokens,
                        "ratio": ratio,
                        "suggestions": "文件過大需拆分 / 引用策略錯 / 考慮手動深度 compaction",
                    },
                )
            except Exception:  # noqa: BLE001 — abort report is best-effort
                abort_report_path = None
            return {
                "already_pending": False,
                "escalated": True,
                "reason": reason,
                "count_per_stage": auto.get("count_per_stage", 0),
                "max_per_stage": max_per_stage,
                "stage_key": stage_key,
                "abort_report": str(abort_report_path) if abort_report_path else None,
            }

        import datetime as _dt
        now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        auto["triggered_at"] = now
        auto["resume_state"] = resume_state
        auto["trigger_ratio"] = ratio
        auto["trigger_cumulative_tokens"] = cumulative_tokens
        auto["trigger_count"] = int(auto.get("trigger_count", 0)) + 1
        auto["count_per_stage"] = projected
        auto["completed_at"] = None
        snapshot_path = save_auto_snapshot(
            self.state,
            cumulative_tokens=cumulative_tokens,
            ratio=ratio,
            resume_state=resume_state,
            compact_index=projected,  # P1-C：避免同 stage 多次 compact 互相 overwrite
        )
        auto["snapshot_path"] = str(snapshot_path)
        self.state.current = "AUTO_COMPACT_PENDING"
        # ACT-025: record decision trace for auto-compact trigger (direct assignment
        # above, not via transition(); log explicitly here).
        try:
            self.state.append_decision_trace(
                from_state=resume_state,
                to_state="AUTO_COMPACT_PENDING",
                reason=(
                    f"auto-compact triggered at ratio={ratio:.2%} cumulative={cumulative_tokens} "
                    f"stage={stage_key} count_per_stage={projected}"
                ),
                trigger="auto_compact_trigger",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {
            "already_pending": False,
            "snapshot": str(snapshot_path),
            "resume_state": resume_state,
            "count_per_stage": projected,
            "stage_key": stage_key,
        }

    def complete_auto_compact(self, *, reset_ledger: bool = True) -> dict:
        """Called by stage-compaction Skill after successful compact.

        Side-effects when reset_ledger=True (default):
        - FSM transitions back to recorded resume_state
        - Today's CONTEXT-LEDGER cumulative_tokens is zeroed (entries kept)
        - auto_compact_state.completed_at / completed_count updated
        """
        if self.state.current != "AUTO_COMPACT_PENDING":
            return {"noop": True, "reason": f"state={self.state.current}"}
        auto = self.state.root.setdefault("auto_compact_state", {})
        resume_state = auto.get("resume_state") or "SPEC_DRAFTING"
        import datetime as _dt
        auto["completed_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        auto["completed_count"] = int(auto.get("completed_count", 0)) + 1
        self.transition(
            resume_state,
            reason="stage-compaction completed — resume from AUTO_COMPACT_PENDING",
            trigger="auto_compact_complete",
        )
        ledger_reset_info: dict = {"reset": False}
        if reset_ledger:
            ledger_reset_info = _reset_today_ledger()
        return {"resumed_to": resume_state, "ledger": ledger_reset_info}

    def is_auto_compact_pending(self) -> bool:
        return self.state.current == "AUTO_COMPACT_PENDING"

    # ----- Phase G M1 / ACT-033/034: Self-Healing entry/exit -----
    @staticmethod
    def _gate_is_resumable(gate: str) -> bool:
        """W-15-1：gate 是否為 auto_recovery 合法 resume_state（避免撕裂轉態）。"""
        from .auto_recovery import _GATE_RESUMABLE_TARGETS  # local to avoid cycles
        return gate in _GATE_RESUMABLE_TARGETS

    def auto_recovery_stats(self) -> dict:
        """W-15-1 / B-axis L4 可量測信號：彙整本 session 自動恢復成效。

        從 recovery_state.history（record_attempt_outcome flush）+ escalation/cumulative
        計數推導「無人工自動恢復率」與 escalation 率。純讀 state，無副作用。

        Returns:
            {
              "attempts": int,            # 已啟動的 AUTO_RECOVERY_ATTEMPT 次數
              "successes": int,           # outcome=success（自動恢復回 resume_state）
              "failures": int,            # outcome=fail（→ ESCALATION_FINAL）
              "recovery_success_rate": float,  # successes / attempts（attempts=0 → 0.0）
              "escalations": int,         # 累計 ESCALATION 次數（含已恢復者）
              "unattended_recovery_rate": float,  # successes / escalations（衡量「升級後不需人工即自癒」比例）
            }
        """
        rs = self.state.root.get("recovery_state") or {}
        history = rs.get("history") or []
        successes = sum(1 for h in history if h.get("outcome") == "success")
        failures = sum(1 for h in history if h.get("outcome") == "fail")
        attempts = successes + failures
        cum = self.state.cumulative()
        escalations = int(cum.get("escalation_count", 0))
        return {
            "attempts": attempts,
            "successes": successes,
            "failures": failures,
            "recovery_success_rate": (successes / attempts) if attempts else 0.0,
            "escalations": escalations,
            "unattended_recovery_rate": (
                (successes / escalations) if escalations else 0.0
            ),
        }

    def learning_loop_stats(self) -> dict:
        """W-16-2 / B-axis L5 可量測信號 + XAI 良基終止可解釋性。純讀 state，無副作用、零轉態。

        彙整規則自演化 meta-loop 本 session 成效：自動提議數、人工審結果、採納/churn 攔截，
        並輸出人類舵手可一眼判讀的「良基終止證書」（meta_halt ChurnBounded/GraduationRatchet
        的有界測度——正是「自演化在環上守界」的良基 ranking：每指紋 churn 嚴格有界 ⟹ add↔retire
        抖動不可能無限）。**純讀、不渲染遞迴大圖、不碰 meta-oracle**（守 R-9.37/R-9.24）。

        Returns:
            {
              "proposals_total": int,        # proposals_history 累計筆數（已審結）
              "auto_proposed": int,          # W-16-1 自動提議累計（auto_proposed_count）
              "human_approved": int,         # review_status=="approved"
              "human_rejected": int,         # review_status=="rejected"
              "pending": int,                # 當前 tracking 仍 pending（0/1）
              "approval_rate": float,        # approved / proposals_total（0 → 0.0）
              "unattended_proposal_rate": float,  # auto_proposed / (auto_proposed+manual proposals)（0 → 0.0）
              "termination_certificate": {   # XAI：良基終止守界摘要（獨立讀 bound，不盲信）
                "churn_max": int,            # 每指紋再採納上限 clamp[1,5] 預設 2（ChurnBounded）
                "graduation_ratchet": str,   # 單調棘輪：退役指紋無 capability-delta 不得 re-adopt
                "well_founded": bool,         # churn 計數器有界遞減 ⟹ 良基（add↔retire 抖動有限）
              },
            }
        """
        tracking = self.state.root.get("learning_commit_tracking") or {}
        history = tracking.get("proposals_history") or []
        if not isinstance(history, list):
            history = []
        approved = sum(1 for h in history if h.get("review_status") == "approved")
        rejected = sum(1 for h in history if h.get("review_status") == "rejected")
        total = len(history)
        auto_proposed = int(tracking.get("auto_proposed_count", 0))
        pending = 1 if tracking.get("review_status") == "pending" else 0
        # manual proposals ≈ 已審結但非自動來源（保守：total - 自動已審結；下限 0）
        manual_completed = max(total - auto_proposed, 0)
        proposal_universe = auto_proposed + manual_completed
        try:
            from .meta_halt.meta_halt_monitor import churn_max as _churn_max  # local import
            churn_bound = _churn_max()
        except Exception:  # noqa: BLE001 — 度量穩健：取不到 bound 不破壞純讀統計
            churn_bound = 2
        return {
            "proposals_total": total,
            "auto_proposed": auto_proposed,
            "human_approved": approved,
            "human_rejected": rejected,
            "pending": pending,
            "approval_rate": (approved / total) if total else 0.0,
            "unattended_proposal_rate": (
                (auto_proposed / proposal_universe) if proposal_universe else 0.0
            ),
            "termination_certificate": {
                "churn_max": churn_bound,
                "graduation_ratchet": (
                    "monotonic：退役指紋無 capability-delta 不得 re-adopt（R-9.24）"
                ),
                "well_founded": True,
            },
        }

    def enter_auto_recovery(
        self,
        *,
        escalation_reason: str,
        resume_state: str,
        spec_refs: Optional[list] = None,
    ) -> dict:
        """Transition ESCALATION → AUTO_RECOVERY_ATTEMPT after Rule 9.14 checks.

        Returns:
            On success: {"entered": True, "action": str, "wait_sec": int,
                         "diagnostic": dict, "resume_state": str}
            On refusal: {"entered": False, "next_state": "ESCALATION_FINAL",
                         "refusal_reason": str, "diagnostic": dict}

        Refusal cases (per Rule 9.14):
          - 9.14.3 structural diagnosis → ESCALATION_FINAL
          - 9.14.1 session_attempt_count ≥ 3 → ESCALATION_FINAL
          - 9.14.2 same reason already attempted → ESCALATION_FINAL
        """
        from . import auto_recovery  # local to avoid import cycles

        src = self.state.current
        if src != "ESCALATION":
            raise TransitionError(
                f"enter_auto_recovery blocked: current={src}, expected ESCALATION"
            )
        proposal = auto_recovery.propose_recovery(
            escalation_reason,
            state=self.state,
            spec_refs=spec_refs,
        )
        if not proposal.allowed:
            self.transition(
                "ESCALATION_FINAL",
                reason=(
                    f"auto_recovery refused: {proposal.refusal_reason}"
                ),
                spec_refs=list(spec_refs or []),
                trigger="auto_recovery_refused",
            )
            # Phase H M6 / ACT-056：structural ESCALATION_FINAL 必須由 FSM 層
            # 產出「含 DiagnosticResult」的 abort 報告（Rule 9.20.6 舵手交棒）。
            # 否則 diagnostic 雖回傳給 caller，仍仰賴 orchestrator 記得寫報告；
            # §G8 的核心缺口正是「機器算出診斷卻吞掉，只丟 retry exhausted 給人」。
            abort_report_path = None
            try:
                abort_report_path = save_abort_report(
                    self.state,
                    reason=f"auto_recovery refused: {proposal.refusal_reason}",
                    category="auto-recovery-refused",
                    diagnostic=proposal.diagnostic,
                    extra_context={"refusal_reason": proposal.refusal_reason},
                )
            except Exception:  # noqa: BLE001 — abort report is best-effort
                abort_report_path = None
            return {
                "entered": False,
                "next_state": "ESCALATION_FINAL",
                "refusal_reason": proposal.refusal_reason,
                "diagnostic": proposal.diagnostic,
                "abort_report_path": (
                    str(abort_report_path) if abort_report_path else None
                ),
            }

        # Proposal accepted — transition + record attempt-start.
        self.transition(
            "AUTO_RECOVERY_ATTEMPT",
            reason=(
                f"auto_recovery accepted: {proposal.diagnostic['sub_type']} "
                f"(action={proposal.action})"
            ),
            spec_refs=list(spec_refs or []),
            trigger="auto_recovery_enter",
        )
        auto_recovery.record_attempt_start(
            self.state,
            diagnostic=proposal.diagnostic,
            resume_state=resume_state,
        )
        save_state(self.state)
        return {
            "entered": True,
            "action": proposal.action,
            "wait_sec": proposal.wait_sec,
            "diagnostic": proposal.diagnostic,
            "resume_state": resume_state,
        }

    def exit_auto_recovery(self, outcome: str) -> dict:
        """Leave AUTO_RECOVERY_ATTEMPT with success → resume_state, fail → ESCALATION_FINAL.

        outcome ∈ {"success", "fail"}. On 'success' the FSM returns to the
        resume_state stored at entry-time. On 'fail' it transitions to
        ESCALATION_FINAL per Rule 9.14.4 (no further auto-recovery allowed).
        """
        from . import auto_recovery  # local

        if self.state.current != "AUTO_RECOVERY_ATTEMPT":
            raise TransitionError(
                f"exit_auto_recovery called in state={self.state.current}, "
                "expected AUTO_RECOVERY_ATTEMPT"
            )
        outcome_norm = (outcome or "").strip().lower()
        if outcome_norm not in {"success", "fail"}:
            raise ValueError(
                f"invalid outcome={outcome!r}; expected 'success' or 'fail'"
            )
        rs = self.state.root.get("recovery_state") or {}
        current_attempt = rs.get("current") or {}
        resume_state = current_attempt.get("resume_state")
        if outcome_norm == "success":
            if not resume_state:
                raise RuntimeError(
                    "no resume_state recorded for current AUTO_RECOVERY_ATTEMPT"
                )
            auto_recovery.record_attempt_outcome(self.state, "success")
            self.transition(
                resume_state,
                reason="auto_recovery success — resuming from recorded state",
                trigger="auto_recovery_success",
            )
            return {
                "exited": True,
                "outcome": "success",
                "next_state": resume_state,
            }
        # fail path → ESCALATION_FINAL
        auto_recovery.record_attempt_outcome(self.state, "fail")
        self.transition(
            "ESCALATION_FINAL",
            reason=(
                "auto_recovery failed — escalating to ESCALATION_FINAL per Rule 9.14.4"
            ),
            trigger="auto_recovery_fail",
        )
        return {
            "exited": True,
            "outcome": "fail",
            "next_state": "ESCALATION_FINAL",
        }

    # ----- Phase E / ACT-027: Production Feedback entry -----
    def enter_production_signal(self, *, reason: str = "", signal_refs: Optional[list] = None) -> dict:
        """Transition into PRODUCTION_SIGNAL (non-blocking observation state).

        ACT-027: Explicit entry API — bypasses happy-path because RELEASE is
        deliberately terminal in the FSM. PRODUCTION_SIGNAL is only meant for
        post-release drift monitoring; entry from non-post-release states is
        almost always a mis-dispatch, so we guard entry to {RELEASE,
        RELEASE_READY, PRODUCTION_SIGNAL} only.

        Does NOT block tool calls (contrast ESCALATION / TERMINATED) — the
        monitor keeps running while the session continues normal operation.
        """
        src = self.state.current
        if src == "PRODUCTION_SIGNAL":
            return {"noop": True, "current": src}
        if src not in {"RELEASE", "RELEASE_READY"}:
            raise TransitionError(
                f"enter_production_signal blocked: current={src}, "
                "expected one of {RELEASE, RELEASE_READY, PRODUCTION_SIGNAL}"
            )
        self.state.current = "PRODUCTION_SIGNAL"
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state="PRODUCTION_SIGNAL",
                reason=reason or "production feedback layer activated (ACT-027)",
                spec_refs=list(signal_refs or []),
                trigger="production_signal_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "PRODUCTION_SIGNAL"}

    # ----- Phase E M4 / ACT-028: Learning Layer entry -----
    def enter_learning_commit(
        self,
        *,
        fpl_id: str,
        proposed_slv_id: str,
        proposed_rule_path: Optional[str] = None,
        reason: str = "",
    ) -> dict:
        """Transition into LEARNING_COMMIT (non-blocking background state).

        ACT-028: entry is explicit via this API. Typical trigger is either:
          1) ESCALATION abort-report analysis finds an uncovered FPL pattern
             and `slv_generator.propose_slv_from_fpl()` produced a draft.
          2) Operator runs `/slv-generator propose <fpl_id>` manually.

        Allowed from terminal / near-terminal states; draft rules are always
        `trust_level: proposed` until human review commits them.
        """
        src = self.state.current
        if src == "LEARNING_COMMIT":
            return {"noop": True, "current": src}
        if src not in {"ESCALATION", "TERMINATED", "RELEASE", "PRODUCTION_SIGNAL"}:
            raise TransitionError(
                f"enter_learning_commit blocked: current={src}, "
                "expected one of {ESCALATION, TERMINATED, RELEASE, PRODUCTION_SIGNAL}"
            )
        self.state.current = "LEARNING_COMMIT"
        tracking = self.state.root.setdefault("learning_commit_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["fpl_id"] = fpl_id
        tracking["proposed_slv_id"] = proposed_slv_id
        tracking["proposed_rule_path"] = proposed_rule_path
        tracking["review_status"] = "pending"
        tracking["entered_from"] = src
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state="LEARNING_COMMIT",
                reason=(reason or f"SLV draft proposed from {fpl_id} → {proposed_slv_id}"),
                trigger="learning_commit_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "fpl_id": fpl_id, "proposed_slv_id": proposed_slv_id}

    def exit_learning_commit(self, review_outcome: str, *, reason: str = "") -> dict:
        """Leave LEARNING_COMMIT after human review.

        review_outcome ∈ {"approved", "rejected"}:
          - approved → transition back to RELEASE (rule will be re-loaded by
            spec-logical-validator on next session).
          - rejected → transition to ESCALATION so operators can triage the
            failing proposal (keeps auto-review loops bounded).

        M4 QA Round-6 強化：
          - P1-1：approved 分支必須先驗 proposed_rule_path 對應 YAML 已升級
            為 `trust_level: verified` 且 `reviewed_by` 非空，否則 raise
            ValueError — 防堵 FSM 被空 approve。
          - P1-2：每次 exit 將 {fpl_id, proposed_slv_id, proposed_rule_path,
            review_status, reviewed_at} append 至
            `learning_commit_tracking.proposals_history` 作為審計鏈。
        """
        if self.state.current != "LEARNING_COMMIT":
            raise TransitionError(
                f"exit_learning_commit called in state={self.state.current}, expected LEARNING_COMMIT"
            )
        outcome = review_outcome.strip().lower()
        if outcome not in {"approved", "rejected"}:
            raise ValueError(
                f"invalid review_outcome={review_outcome!r}; expected 'approved' or 'rejected'"
            )
        tracking = self.state.root.setdefault("learning_commit_tracking", {})
        # P1-1：approved 必須有真實 verified YAML 支持
        if outcome == "approved":
            rule_path_str = tracking.get("proposed_rule_path")
            if not rule_path_str:
                raise ValueError(
                    "approved exit requires learning_commit_tracking.proposed_rule_path "
                    "to be set — no rule YAML to audit"
                )
            from pathlib import Path as _Path  # local to avoid top-level churn
            from .state_loader import REPO_ROOT  # repo-relative fallback
            from . import slv_generator as _slv
            rule_path = _Path(rule_path_str)
            if not rule_path.is_absolute():
                rule_path = REPO_ROOT / rule_path
            if not rule_path.exists():
                raise ValueError(
                    f"approved exit requires rule YAML at {rule_path}, but file does not exist"
                )
            try:
                rule_doc = _slv.load_rule(rule_path)
            except Exception as exc:  # noqa: BLE001 — 任何 schema 違反都升成 ValueError
                raise ValueError(
                    f"approved exit requires YAML trust_level=verified with reviewer recorded; "
                    f"load_rule({rule_path}) failed: {exc}"
                ) from exc
            if rule_doc.get("trust_level") != "verified":
                raise ValueError(
                    f"approved exit requires YAML trust_level=verified with reviewer recorded; "
                    f"got trust_level={rule_doc.get('trust_level')!r} at {rule_path}"
                )
            if not (isinstance(rule_doc.get("reviewed_by"), str) and rule_doc["reviewed_by"].strip()):
                raise ValueError(
                    f"approved exit requires non-empty reviewed_by at {rule_path} "
                    f"(got {rule_doc.get('reviewed_by')!r})"
                )
        tracking["review_status"] = outcome
        import datetime as _dt
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["reviewed_at"] = now_iso
        # P1-2：append 一筆審計紀錄至 proposals_history
        history = tracking.setdefault("proposals_history", [])
        if not isinstance(history, list):
            # 防禦：若外部手動把 history 改成非 list，重置為 list（保留原值於新筆）
            history = []
            tracking["proposals_history"] = history
        history.append({
            "fpl_id": tracking.get("fpl_id"),
            "proposed_slv_id": tracking.get("proposed_slv_id"),
            "proposed_rule_path": tracking.get("proposed_rule_path"),
            "review_status": outcome,
            "reviewed_at": now_iso,
        })
        target = "RELEASE" if outcome == "approved" else "ESCALATION"
        exit_reason = reason or f"learning review {outcome}"
        meta_halt_info: dict = {}

        # Phase L M-L1 / ACT-090 / Rule 9.24.1~9.24.2：approved 採納 verified 規則前，
        # 必須經 meta_halt_monitor 守門落帳（禁繞過，破 9.24.1）。違反 ChurnBounded /
        # GraduationRatchet 即不放行 RELEASE，改導 ESCALATION（結構性、待人工裁決），
        # 例外不外炸破 FSM。首次採納（無 churn 史）照常落一筆 add 並轉 RELEASE。
        if outcome == "approved":
            meta_halt_info = self._record_learning_rule_adoption(
                rule_doc=rule_doc, rule_path=rule_path, tracking=tracking
            )
            if meta_halt_info.get("blocked"):
                target = "ESCALATION"
                exit_reason = (
                    f"[meta-halt] 元迴圈 churn 違反（{meta_halt_info.get('violation')}）"
                    f"：{meta_halt_info.get('detail')}（Rule 9.24.1/9.24.2，"
                    f"category=structural，導 MFSM_ESCALATION 待人工裁決）"
                )

        self.transition(
            target,
            reason=exit_reason,
            trigger="learning_commit_exit",
        )
        result = {"exited": True, "outcome": outcome, "to": target}
        if meta_halt_info:
            result["meta_halt"] = meta_halt_info
        return result

    def _record_learning_rule_adoption(self, *, rule_doc: dict, rule_path,
                                       tracking: dict) -> dict:
        """Phase L ACT-090：把一次 approved 規則採納落入 meta-loop ledger（經守門）。

        回傳 dict：
          - 守門放行 → {"recorded": True, "fingerprint": ..., "is_readopt": bool}
          - 守門攔截（ChurnBounded/GraduationRatchet）→ {"blocked": True,
            "violation": <類別>, "detail": <訊息>}；呼叫端據此改導 ESCALATION。

        記帳失敗（IO/路徑等非守門原因）只記 warning，不破壞 FSM 轉換（退役/採納帳本
        為 advisory 審計鏈，不應因落盤抖動而擋住合法的人工 approve）。
        """
        from .meta_halt import meta_halt_monitor as _mh
        from .meta_halt import meta_ledger as _ml

        # 語意指紋：以規則語意內容（name/scope/purpose/spec）正規化——**刻意排除 id**，
        # 使「換皮重學」（新 SLV-id 但同語意）收斂到同一指紋，churn 才抓得到 add↔retire
        # 抖動（meta_ledger 設計目標：語意同型 → 同指紋）。
        fp_src = " ".join(
            str(rule_doc.get(k, ""))
            for k in ("name", "scope", "purpose", "spec")
            if rule_doc.get(k)
        ).strip() or str(rule_path)
        fingerprint = _ml.fingerprint_of(fp_src)
        try:
            cap = int(rule_doc.get("capability_level", 0) or 0)
        except (TypeError, ValueError):
            cap = 0
        rule_id = str(rule_doc.get("id") or tracking.get("proposed_slv_id") or "SLV-?")
        was_readopt = _ml.is_readopt(fingerprint)  # 落帳前判定（add 後最後一筆會變 add）
        try:
            _mh.record_rule_add(
                rule_id, fingerprint, cap,
                source="learning_layer", note="exit_learning_commit(approved)",
            )
            return {"recorded": True, "fingerprint": fingerprint,
                    "is_readopt": was_readopt}
        except _mh.ChurnBoundExceeded as exc:
            return {"blocked": True, "violation": "ChurnBounded", "detail": str(exc),
                    "fingerprint": fingerprint}
        except _mh.GraduationRatchetViolation as exc:
            return {"blocked": True, "violation": "GraduationRatchet", "detail": str(exc),
                    "fingerprint": fingerprint}
        except Exception as exc:  # noqa: BLE001 — 非守門落盤錯誤不得破壞 FSM
            return {"recorded": False, "warning": f"meta-ledger 記帳失敗（不阻塞）：{exc}"}

    # ----- Phase G M2 / ACT-035/036: Predictive Halt entry/exit + helper -----

    def consult_predictor(
        self,
        *,
        gate: str = "PR_REVIEW",
        ledger_path: Optional[Path] = None,
        miss_dir: Optional[Path] = None,
    ) -> dict:
        """One-shot helper for orchestrator step_2_5_predict_trajectory.

        Reads current state, calls predict(), and if decision != continue
        performs enter+exit transitions automatically. Returns the
        PredictedAction dict + execution outcome.

        Caller MUST guard against retry_count == 0 (Rule 9.15.1) before calling.
        Returns {decision, executed, action, refusal_reason?} where executed
        indicates whether an actual state transition was performed.

        Rule 9.15.4 pre-check: if switch_to_audit was already used for `gate`
        in this stage, decision is downgraded to continue WITHOUT entering
        TRAJECTORY_PREDICTED (avoids being stranded mid-state when exit would
        raise). Same logic for Rule 9.15.2 (abort_early without confidence).
        """
        from .trajectory_predictor import predict
        action = predict(self.state, gate=gate, ledger_path=ledger_path)
        result = {"decision": action.decision, "action": action.to_dict(), "executed": False}
        if action.decision == "continue":
            return result

        tracking = self.state.root.setdefault("trajectory_prediction_tracking", {})
        per_stage = tracking.get("switch_count_per_stage", {})

        # Rule 9.15.4 pre-check: refuse second switch_to_audit per stage.
        if action.decision == "switch_to_audit" and int(per_stage.get(gate, 0)) >= 1:
            result["refusal_reason"] = f"Rule 9.15.4: switch_to_audit already used for stage={gate}"
            result["decision"] = "continue"
            return result

        # Rule 9.15.2 pre-check: refuse abort_early without confidence.
        if action.decision == "abort_early" and action.confidence < 0.8:
            result["refusal_reason"] = (
                f"Rule 9.15.2: abort_early needs confidence ≥ 0.8 (got {action.confidence})"
            )
            result["decision"] = "continue"
            return result

        # Active prediction → enter then immediately exit per the action
        self.enter_trajectory_predicted(predicted_action=action.to_dict(), gate=gate)
        self.exit_trajectory_predicted(action.decision, miss_dir=miss_dir)
        result["executed"] = True
        result["new_state"] = self.state.current
        return result



    _PREDICTOR_GATES = frozenset({
        "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY",
        "SCG_VALIDATION", "SPEC_REGRESSION_CHECK",
    })

    def enter_trajectory_predicted(
        self,
        *,
        predicted_action: dict,
        gate: str,
        resume_state: Optional[str] = None,
    ) -> dict:
        """Transition into TRAJECTORY_PREDICTED (non-blocking observation state).

        ACT-035: Explicit entry API. Caller must have already invoked
        `trajectory_predictor.predict()` and pass the result via `predicted_action`
        (PredictedAction.to_dict()). `resume_state` defaults to current state
        (the gate from which we are predicting).

        Rule 9.15.1: caller is responsible for guarding retry_count ≥ 1 — this
        method only validates the source state is a recognised retry-prone gate.
        """
        src = self.state.current
        if src == "TRAJECTORY_PREDICTED":
            return {"noop": True, "current": src}
        if src not in self._PREDICTOR_GATES:
            raise TransitionError(
                f"enter_trajectory_predicted blocked: current={src}, "
                f"expected one of {sorted(self._PREDICTOR_GATES)}"
            )
        resume = resume_state or src
        tracking = self.state.root.setdefault("trajectory_prediction_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["gate"] = gate
        tracking["resume_state"] = resume
        tracking["predicted_action"] = dict(predicted_action)
        # rolling switch counter per stage (Rule 9.15.4)
        per_stage = tracking.setdefault("switch_count_per_stage", {})
        per_stage.setdefault(gate, 0)
        self.state.current = "TRAJECTORY_PREDICTED"
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state="TRAJECTORY_PREDICTED",
                reason=str(predicted_action.get("rationale", "trajectory predicted")),
                trigger="trajectory_predicted_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "gate": gate, "resume_state": resume}

    def exit_trajectory_predicted(
        self,
        decision: str,
        *,
        reason: str = "",
        miss_dir: Optional[Path] = None,
        actual_outcome: Optional[str] = None,
    ) -> dict:
        """Leave TRAJECTORY_PREDICTED based on caller's chosen decision.

        decision ∈ {"continue", "switch_to_audit", "abort_early"}:
          - continue        → resume_state (the original retry gate)
          - switch_to_audit → SPEC_AUDIT (saves remaining retry budget)
          - abort_early     → ESCALATION (per Rule 9.15.2 — caller must verify
            confidence ≥ 0.8 before passing this)

        Rule 9.15.4: switch_to_audit is capped at 1 per stage (gate). A second
        attempt within the same stage raises TransitionError.

        Rule 9.15.3: when actual_outcome is supplied (e.g. test passed after
        we predicted abort), and predicted_action.decision was switch/abort,
        record a PREDICTOR-MISS log entry.
        """
        if self.state.current != "TRAJECTORY_PREDICTED":
            raise TransitionError(
                f"exit_trajectory_predicted called in state={self.state.current}, "
                "expected TRAJECTORY_PREDICTED"
            )
        decision = decision.strip().lower()
        if decision not in {"continue", "switch_to_audit", "abort_early"}:
            raise ValueError(
                f"invalid decision={decision!r}; expected 'continue' / 'switch_to_audit' / 'abort_early'"
            )
        tracking = self.state.root.setdefault("trajectory_prediction_tracking", {})
        gate = tracking.get("gate", "PR_REVIEW")
        resume = tracking.get("resume_state", gate)

        if decision == "continue":
            target = resume
        elif decision == "switch_to_audit":
            per_stage = tracking.setdefault("switch_count_per_stage", {})
            current = int(per_stage.get(gate, 0))
            if current >= 1:
                raise TransitionError(
                    f"Rule 9.15.4: switch_to_audit already used for stage={gate} "
                    f"(count={current}); refuse second switch"
                )
            per_stage[gate] = current + 1
            target = "SPEC_AUDIT"
        else:  # abort_early
            predicted = tracking.get("predicted_action") or {}
            confidence = float(predicted.get("confidence", 0.0))
            if confidence < 0.8:
                raise TransitionError(
                    f"Rule 9.15.2: abort_early requires confidence ≥ 0.8, got {confidence}"
                )
            target = "ESCALATION"

        # Optional false-positive log
        if actual_outcome and miss_dir is not None:
            from .trajectory_predictor import PredictedAction, record_miss
            predicted = tracking.get("predicted_action") or {}
            if predicted.get("decision") in ("switch_to_audit", "abort_early") and \
                    actual_outcome == "would_have_succeeded":
                action = PredictedAction(
                    decision=predicted.get("decision", "continue"),
                    confidence=float(predicted.get("confidence", 0.0)),
                    signals_triggered=list(predicted.get("signals_triggered", [])),
                    rationale=str(predicted.get("rationale", "")),
                    next_state_hint=predicted.get("next_state_hint"),
                    gate=str(predicted.get("gate", gate)),
                )
                record_miss(
                    action=action,
                    actual_outcome=actual_outcome,
                    miss_dir=miss_dir,
                    state_name="TRAJECTORY_PREDICTED",
                )

        self.transition(
            target,
            reason=reason or f"trajectory_predicted exit decision={decision}",
            trigger="trajectory_predicted_exit",
        )
        tracking["last_exit_decision"] = decision
        tracking["last_exit_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds")
        save_state(self.state)
        return {"exited": True, "decision": decision, "to": target, "gate": gate}

    # ----- Phase G M6 / ACT-044: Cost-Aware Orchestration -----
    DISPATCH_REJECT_LIMIT = 3  # Rule 9.19.3

    def record_dispatch_rejection(self, *, reason: str = "budget_exhausted") -> dict:
        """Track consecutive dispatch rejections; auto-ESCALATE at limit (Rule 9.19.3).

        Each call increments state.cost_gate.consecutive_rejections. When the
        counter hits DISPATCH_REJECT_LIMIT, transitions to ESCALATION with
        the supplied reason (default: budget_exhausted, which DiagnosticAgent
        classifies as structural -> retry_exhausted, per Rule 9.14.3).
        """
        bucket = self.state.root.setdefault("cost_gate", {})
        n = int(bucket.get("consecutive_rejections", 0)) + 1
        import datetime as _dt
        bucket["consecutive_rejections"] = n
        bucket["last_rejection_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        bucket["last_reason"] = reason
        save_state(self.state)
        if n >= self.DISPATCH_REJECT_LIMIT:
            bucket["consecutive_rejections"] = 0  # reset after escalation
            self.transition(
                "ESCALATION",
                reason=f"Rule 9.19.3: {n} consecutive dispatch rejections ({reason})",
                trigger="cost_gate_escalation",
            )
            return {"escalated": True, "count": n, "reason": reason}
        return {"escalated": False, "count": n, "reason": reason}

    def reset_dispatch_rejections(self) -> None:
        """Called after a successful dispatch — resets the rejection streak."""
        bucket = self.state.root.setdefault("cost_gate", {})
        if int(bucket.get("consecutive_rejections", 0)) > 0:
            bucket["consecutive_rejections"] = 0
            save_state(self.state)

    # ----- Phase G M4 / ACT-040: Continuous Drift Monitor (DRIFT_OBSERVATION) -----
    DRIFT_OBSERVATION_ALLOWED_SOURCES = frozenset({
        "SPEC_DRAFTING", "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW",
        "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK",
    })

    def enter_drift_observation(
        self,
        *,
        commit_sha: str,
        drift_score: float,
        consecutive: bool = False,
        resume_state: Optional[str] = None,
        reason: str = "",
    ) -> dict:
        """Enter DRIFT_OBSERVATION (Phase G M4 / Rule 9.17.2).

        Non-blocking observation state — caller decides continue/switch on exit.
        `consecutive=True` means consecutive drift threshold crossed (Rule 9.17.3).
        """
        src = self.state.current
        if src == "DRIFT_OBSERVATION":
            return {"noop": True, "current": src}
        if src not in self.DRIFT_OBSERVATION_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_drift_observation blocked: current={src}, "
                f"expected one of {sorted(self.DRIFT_OBSERVATION_ALLOWED_SOURCES)}"
            )
        resume = resume_state or src
        tracking = self.state.root.setdefault("drift_observation_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["commit_sha"] = commit_sha
        tracking["drift_score"] = float(drift_score)
        tracking["consecutive"] = bool(consecutive)
        tracking["resume_state"] = resume
        self.state.current = "DRIFT_OBSERVATION"
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state="DRIFT_OBSERVATION",
                reason=reason or f"drift_score={drift_score:.3f} commit={commit_sha[:12]}",
                trigger="drift_observation_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "resume_state": resume}

    def exit_drift_observation(self, decision: str, *, reason: str = "") -> dict:
        """Leave DRIFT_OBSERVATION based on decision.

        decision ∈ {"continue", "switch_to_audit"}:
          - continue        → resume_state (single drift, advisory only)
          - switch_to_audit → SPEC_AUDIT (Rule 9.17.3, consecutive threshold reached)
        """
        if self.state.current != "DRIFT_OBSERVATION":
            raise TransitionError(
                f"exit_drift_observation called in state={self.state.current}, "
                "expected DRIFT_OBSERVATION"
            )
        decision = decision.strip().lower()
        if decision not in {"continue", "switch_to_audit"}:
            raise ValueError(
                f"invalid decision={decision!r}; expected 'continue' / 'switch_to_audit'"
            )
        tracking = self.state.root.setdefault("drift_observation_tracking", {})
        resume = tracking.get("resume_state", "IMPLEMENTATION")
        target = resume if decision == "continue" else "SPEC_AUDIT"
        self.transition(
            target,
            reason=reason or f"drift_observation exit decision={decision}",
            trigger="drift_observation_exit",
        )
        tracking["last_exit_decision"] = decision
        save_state(self.state)
        return {"exited": True, "decision": decision, "to": target}

    def exit_production_signal(self, target: str, *, reason: str = "") -> dict:
        """Leave PRODUCTION_SIGNAL back into happy-path.

        Valid targets: {SPEC_DRAFTING, RELEASE}. SPEC_DRAFTING is used when
        persistent drift justifies re-opening the spec loop; RELEASE is used
        when the drift was purely informational.
        """
        if self.state.current != "PRODUCTION_SIGNAL":
            raise TransitionError(
                f"exit_production_signal called in state={self.state.current}, expected PRODUCTION_SIGNAL"
            )
        self.transition(
            target,
            reason=reason or f"exit PRODUCTION_SIGNAL to {target}",
            trigger="production_signal_exit",
        )
        return {"exited": True, "to": target}

    # ===== Phase H M2 / ACT-049: Test-Contract Negotiation gate =====
    def enter_test_contract_negotiated(self, *, reason: str = "", contract_ref: str = "") -> dict:
        """Enter TEST_CONTRACT_NEGOTIATED from SPEC_FROZEN (Rule 9.20.2).

        Gatekeep: Evaluator drafts a per-AC pass/fail oracle and the Generator
        formally signs it BEFORE implementation begins. Happy-path reachable, so
        a normal transition() is used.
        """
        src = self.state.current
        if src == "TEST_CONTRACT_NEGOTIATED":
            return {"noop": True, "current": src}
        self.transition(
            "TEST_CONTRACT_NEGOTIATED",
            reason=reason or "enter test-contract negotiation (ACT-049)",
            spec_refs=[contract_ref] if contract_ref else None,
            trigger="test_contract_enter",
        )
        return {"entered": True, "from": src, "to": "TEST_CONTRACT_NEGOTIATED"}

    def exit_test_contract_negotiated(self, outcome: str, *, reason: str = "") -> dict:
        """Leave TEST_CONTRACT_NEGOTIATED based on negotiation outcome.

        outcome ∈ {"agreed", "underspecified"}:
          - agreed         → IMPLEMENTATION  (both parties signed the oracle)
          - underspecified → SPEC_DRAFTING   (spec too vague to define oracle)
        """
        if self.state.current != "TEST_CONTRACT_NEGOTIATED":
            raise TransitionError(
                f"exit_test_contract_negotiated called in state={self.state.current}, "
                "expected TEST_CONTRACT_NEGOTIATED"
            )
        outcome = outcome.strip().lower()
        mapping = {"agreed": "IMPLEMENTATION", "underspecified": "SPEC_DRAFTING"}
        if outcome not in mapping:
            raise ValueError(f"invalid outcome={outcome!r}; expected 'agreed' / 'underspecified'")
        target = mapping[outcome]
        self.transition(
            target,
            reason=reason or f"test-contract negotiation outcome={outcome}",
            trigger="test_contract_exit",
        )
        return {"exited": True, "outcome": outcome, "to": target}

    # ===== Phase H M1 / ACT-045: Execution-Grounded Evaluation gate =====
    def enter_execution_evaluation(self, *, reason: str = "", artifact_refs: Optional[list] = None) -> dict:
        """Enter EXECUTION_EVALUATION from IMPLEMENTATION (Rule 9.20.1).

        Gatekeep: the Evaluator runs the produced software in an isolated sandbox
        and returns an OBJECTIVE verdict (exit code / HTTP status / OQS). Happy-path
        reachable (IMPLEMENTATION → EXECUTION_EVALUATION).
        """
        src = self.state.current
        if src == "EXECUTION_EVALUATION":
            return {"noop": True, "current": src}
        self.transition(
            "EXECUTION_EVALUATION",
            reason=reason or "enter execution-grounded evaluation (ACT-045)",
            spec_refs=list(artifact_refs or []),
            trigger="execution_evaluation_enter",
        )
        return {"entered": True, "from": src, "to": "EXECUTION_EVALUATION"}

    def exit_execution_evaluation(self, verdict: str, *, reason: str = "") -> dict:
        """Leave EXECUTION_EVALUATION based on the sandbox verdict.

        verdict ∈ {"pass", "runtime_fail", "spec_defect"}:
          - pass         → PR_REVIEW      (static compliance confirmation follows)
          - runtime_fail → IMPLEMENTATION (fix loop; EXEC_EVAL retry budget at caller)
          - spec_defect  → SPEC_AUDIT     (execution revealed a spec contradiction)
        """
        if self.state.current != "EXECUTION_EVALUATION":
            raise TransitionError(
                f"exit_execution_evaluation called in state={self.state.current}, "
                "expected EXECUTION_EVALUATION"
            )
        verdict = verdict.strip().lower()
        mapping = {"pass": "PR_REVIEW", "runtime_fail": "IMPLEMENTATION", "spec_defect": "SPEC_AUDIT"}
        if verdict not in mapping:
            raise ValueError(
                f"invalid verdict={verdict!r}; expected 'pass' / 'runtime_fail' / 'spec_defect'"
            )
        target = mapping[verdict]
        self.transition(
            target,
            reason=reason or f"execution evaluation verdict={verdict}",
            trigger="execution_evaluation_exit",
        )
        return {"exited": True, "verdict": verdict, "to": target}

    # ===== Phase H M5 / ACT-055: Scaffold Metabolism (SCAFFOLD_GC) =====
    # H-001 修：單一 RELEASE 入口（與 .tla T_EnterScaffoldGc / MD / test 四源一致，
    # 且 resume_state 固定 "RELEASE" 對 RELEASE 入口才正確；RELEASE_READY 入口會繞過
    # RELEASE_READY→RELEASE 邊，故移除）。
    SCAFFOLD_GC_ALLOWED_SOURCES = frozenset({"RELEASE"})

    def enter_scaffold_gc(self, *, reason: str = "", roi_report_ref: str = "") -> dict:
        """Enter SCAFFOLD_GC (non-blocking observation, Rule 9.20.5).

        Explicit entry API — bypasses happy-path because RELEASE is terminal.
        Mirrors enter_production_signal: scheduled / post-release / manual trigger.
        Does NOT block tool calls.
        """
        src = self.state.current
        if src == "SCAFFOLD_GC":
            return {"noop": True, "current": src}
        if src not in self.SCAFFOLD_GC_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_scaffold_gc blocked: current={src}, "
                f"expected one of {sorted(self.SCAFFOLD_GC_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("scaffold_gc_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = "RELEASE"
        if roi_report_ref:
            tracking["roi_report_ref"] = roi_report_ref
        self.state.current = "SCAFFOLD_GC"
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state="SCAFFOLD_GC",
                reason=reason or "scaffold metabolism GC cycle (ACT-055)",
                spec_refs=[roi_report_ref] if roi_report_ref else None,
                trigger="scaffold_gc_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        result = {"entered": True, "from": src, "to": "SCAFFOLD_GC"}
        # W-17-1：代謝提議接入主迴圈（flag-gated、fail-closed、進態後 side-effect）。
        # flag ON → 自動跑既有 run_gc 算 ROI 並落 SCAFFOLD-ROI 報告（鏡像 W-16-1
        # auto-draft 模式：呼叫既有純函式而非重寫）。run_gc 只產 RetirementProposal +
        # Markdown，**永不呼叫 set_maturity**（退役仍 🔴 人工，R-9.20 #11）。flag OFF →
        # 行為逐字同 v0.07（只記 tracking）＝零退化。
        if _scaffold_gc_auto_propose_enabled():
            try:
                from . import scaffold_gc as _gc  # local import：避 top-level cycle
                import datetime as _dt2
                _today = _dt2.datetime.now(_dt2.timezone.utc).strftime("%Y-%m-%d")
                gc_res = _gc.run_gc(self.state, today=_today)
                tracking["origin"] = "auto"
                tracking["roi_report_ref"] = gc_res.report_path
                tracking["proposals_total"] = len(gc_res.proposals)
                tracking["rules_scanned"] = gc_res.rules_scanned
                result["auto_gc"] = {
                    "proposed": True,
                    "report_path": gc_res.report_path,
                    "proposals_total": len(gc_res.proposals),
                }
            except Exception as exc:  # noqa: BLE001 — fail-closed：進態仍成功、不偽造報告
                tracking["auto_gc_error"] = str(exc)
                result["auto_gc"] = {"proposed": False, "error": str(exc)}
        save_state(self.state)
        return result

    def exit_scaffold_gc(self, decision: str, *, reason: str = "") -> dict:
        """Leave SCAFFOLD_GC based on GC decision.

        decision ∈ {"continue", "respec"}:
          - continue → RELEASE       (no action needed; retirement proposals go to
                                       SCAFFOLD-ROI report for async LEARNING_COMMIT review)
          - respec   → SPEC_DRAFTING  (GC found a spec-level inconsistency to fix)
        """
        if self.state.current != "SCAFFOLD_GC":
            raise TransitionError(
                f"exit_scaffold_gc called in state={self.state.current}, expected SCAFFOLD_GC"
            )
        decision = decision.strip().lower()
        mapping = {"continue": "RELEASE", "respec": "SPEC_DRAFTING"}
        if decision not in mapping:
            raise ValueError(f"invalid decision={decision!r}; expected 'continue' / 'respec'")
        target = mapping[decision]
        self.transition(
            target,
            reason=reason or f"scaffold_gc exit decision={decision}",
            trigger="scaffold_gc_exit",
        )
        return {"exited": True, "decision": decision, "to": target}

    def scaffold_gc_stats(self) -> dict:
        """W-17-2 / B-axis L5：鷹架代謝可量測信號 + XAI 安全證書（純讀、零副作用、零轉態）。

        從既有 scaffold_gc.compute_proposals() **獨立重算** ROI 提議（不盲信
        scaffold_gc_tracking 標籤，鏡像 improving_14 adapter digest 重算防偽），輸出供
        人類舵手一眼判讀的代謝信號：哪些鷹架被提議退役、ROI 階梯（升冪、ROI 最低＝最該
        退役 critical path）、退役方向分佈。

        XAI Turn：safety_certificate 把「GC 僅提議、永不自動退役 active 規則」的守界以
        人類可懂語言固化——對齊 W-16-2 termination_certificate 呈現原則（純讀、不渲染大
        圖、不碰 meta-oracle）。度量穩健：零提議不除零（回空清單 / 0）。
        """
        from . import scaffold_gc as _gc  # local import：避 top-level cycle
        proposals = _gc.compute_proposals()
        # ROI 升冪排序：ROI 最低（從不 catch）排最前＝最該退役（critical path）
        ladder = sorted(
            (
                {
                    "rule_id": p.rule_id,
                    "roi": p.roi,
                    "fire_count": p.fire_count,
                    "catch_count": p.catch_count,
                    "transition": f"{p.current_maturity}→{p.proposed_maturity}",
                }
                for p in proposals
            ),
            key=lambda d: (d["roi"], -d["fire_count"]),
        )
        by_transition: dict = {}
        for p in proposals:
            key = f"{p.current_maturity}→{p.proposed_maturity}"
            by_transition[key] = by_transition.get(key, 0) + 1
        tracking = self.state.root.get("scaffold_gc_tracking", {})
        return {
            "proposals_total": len(proposals),
            "by_transition": by_transition,
            "roi_ladder": ladder,
            "last_report_ref": tracking.get("roi_report_ref"),
            "origin": tracking.get("origin"),
            "safety_certificate": {
                "auto_retire": False,
                "human_gate": "rule_loader.set_maturity(reviewed_by=...)",
                "well_founded": (
                    "GC 僅提議、永不自動退役 active 規則（R-9.20 #11）；退役單調經人工 "
                    "review，ROI 棘輪不回震 — 代謝在環上守界。"
                ),
            },
        }

    def rule_fire_telemetry_stats(self) -> dict:
        """W-18-2 / B-axis L5：規則命中遙測可量測信號 + XAI 安全證書（純讀、零副作用、零轉態）。

        從 rule_loader.load_all() **獨立重算**各規則 on-watch fire 遙測（不盲信 tracking 標籤），
        輸出供人類舵手一眼判讀的「代謝遙測」信號：哪些鷹架被行使最多卻從不 catch（fire 高、
        catch=0）＝最逼近退役門檻（GRADUATION_MIN_FIRES）的 critical path。閉合 DEF-17-001
        fire_count=0 後，此信號才有非零資料。

        XAI Turn：safety_certificate 把守界以人類可懂語言固化——對齊 scaffold_gc_stats 呈現
        原則（純讀、不渲染大圖、不碰 meta-oracle）。**W-19 翻 catch_side_wired=True**：catch
        側契約已定義並接入（顯式可歸因，閉合 DEF-18-001），ROI=catch/fire 成雙側信號；證書內
        catch_attribution_coverage 誠實揭露目前有 failure_mode（可參與歸因）的規則覆蓋率——
        無 failure_mode 者不歸因（fail-closed，未歸因 escalation 不污染 catch_count）。度量穩健：
        零規則不除零（回空清單 / 0）。
        """
        from . import rule_loader as _rl  # local import：避 top-level cycle
        threshold = _rl.GRADUATION_MIN_FIRES
        rules = [r for r in _rl.load_all() if r.maturity != "deprecated"]
        # critical path：catch=0 且 fire 最高者最逼近退役門檻（降冪＝最該關注排最前）
        ladder = sorted(
            (
                {
                    "rule_id": r.id,
                    "maturity": r.maturity,
                    "fire_count": int(r.scaffold_roi.get("fire_count", 0)),
                    "catch_count": int(r.scaffold_roi.get("catch_count", 0)),
                    "roi": r.roi(),
                    "fires_to_threshold": max(
                        0, threshold - int(r.scaffold_roi.get("fire_count", 0))
                    ),
                }
                for r in rules
            ),
            key=lambda d: (-d["fire_count"], d["roi"]),
        )
        total_fires = sum(row["fire_count"] for row in ladder)
        total_catches = sum(row["catch_count"] for row in ladder)
        retirement_eligible = [
            row["rule_id"]
            for row in ladder
            if row["fire_count"] >= threshold and row["catch_count"] == 0
        ]
        # W-19：catch 歸因覆蓋率 — 有 failure_mode（可參與 catch 自動歸因）的規則。誠實揭露
        # 「目前哪些規則的 catch 側已接線」，未覆蓋者其 catch_count 恆 0（fail-closed 不歸因）。
        attributed_rule_ids = sorted(r.id for r in rules if r.failure_mode)
        # W-39（DEF-39-001）：escalation-scoped 分母透明化。rules_total（全部非 deprecated 規則）
        # 高估了「catch 應接線範圍」——只有具唯一生產 escalation 落點的規則 catch-可歸因（見
        # _ESCALATION_ATTRIBUTABLE_RULE_IDS）。其餘規則由 hook/lint/TLC/meta-loop/人工守門，catch_count
        # 恆 0 是**設計使然非缺口**。escalation_scoped_coverage 才是 catch 接線完成度的正當度量。
        # **純 additive**：既有三欄位（rules_with_failure_mode/rules_total/attributed_rule_ids）逐字不變。
        all_rule_ids = {r.id for r in rules}
        escalation_attributable = sorted(self._ESCALATION_ATTRIBUTABLE_RULE_IDS & all_rule_ids)
        wired_attributable = sorted(set(attributed_rule_ids) & set(escalation_attributable))
        esc_denom = len(escalation_attributable)
        escalation_scoped_pct = (
            round(100.0 * len(wired_attributable) / esc_denom, 1) if esc_denom else 0.0
        )
        return {
            "rules_tracked": len(ladder),
            "total_fires": total_fires,
            "total_catches": total_catches,
            "graduation_min_fires": threshold,
            "retirement_eligible": retirement_eligible,
            "fire_ladder": ladder,
            "safety_certificate": {
                "auto_retire": False,
                "catch_side_wired": True,
                "catch_attribution_coverage": {
                    "rules_with_failure_mode": len(attributed_rule_ids),
                    "rules_total": len(ladder),
                    "attributed_rule_ids": attributed_rule_ids,
                    # W-39（DEF-39-001）：escalation-scoped 正當分母透明化（additive）。
                    "escalation_attributable_rule_ids": escalation_attributable,
                    "escalation_attributable_total": esc_denom,
                    "escalation_scoped_coverage_pct": escalation_scoped_pct,
                    "non_escalation_governed_total": len(ladder) - esc_denom,
                    "denominator_note": (
                        "rules_total 為全部非 deprecated 規則，含由 hook/lint/TLC/meta-loop/人工"
                        "守門者（其 catch_count 恆 0 屬設計使然非缺口）；escalation_scoped_coverage_pct"
                        "＝catch 接線完成度的正當度量（分母＝具唯一生產 escalation 落點之規則）。DEF-39-001。"
                    ),
                },
                "human_gate": "rule_loader.set_maturity(reviewed_by=...)",
                "well_founded": (
                    "fire+catch 遙測只增計數、永不 set_maturity（R-9.20 #11）。catch 側採「顯式"
                    "可歸因」三要件（escalation 真實發生 ∧ 規則自描述 failure_mode ∧ 呼叫端"
                    "結構化歸因 rule_id），非時序鄰近猜測 — 本輪接 R-9.1（gate retry 耗盡）/"
                    "R-9.21（monitor 破壞）確定路徑；無 failure_mode 的規則與未歸因 escalation "
                    "一律 fail-closed 不記、不污染 catch_count（DEF-18-001 寧缺勿濫）。退役提議仍 "
                    "🔴 人工 review — 遙測在環上守界、不自走退役。"
                ),
            },
        }

    def comprehensive_governance_coverage(self) -> dict:
        """W-54-2（improving_55 / DEF-19-001 後續標的）：全部 active 治理規則的「守門機制覆蓋」
        誠實證書（純讀、零副作用、零轉態）。

        DEF-19-001 收尾點名：FSM-escalation catch 達結構天花板 7/7=100% 後，其餘 32 條
        （hook/lint_tlc/meta_loop/manual）守門覆蓋零度量。本證書把「覆蓋」從**不可能的**
        『守門 runtime 是否有效』**誠實重構**為可驗證的『每條規則宣稱守門機制是否真實分類 +
        (escalation 類) catch 側是否接線』之靜態-結構度量（抓 guard bit-rot），並對 manual 類
        **誠實排除於自動分母**（沿用 catch_attribution_coverage 的 denominator_note 紀律）。
        runtime 計數類（hook/lint_tlc/meta_loop）標 deferred（justified：無消費者 + Rule 2
        speculative + meta_loop 恐觸 TLC）。fail-closed：度量失敗不阻塞、不偽綠；永不 set_maturity
        （R-9.20 #11）；零新增 reachable 邊、不碰 *.tla。
        """
        from . import rule_loader as _rl  # local import：避 top-level cycle
        rules = [r for r in _rl.load_all() if r.maturity != "deprecated"]
        by_mech: dict = {}
        for r in rules:
            by_mech.setdefault(r.enforcement_mechanism or "unclassified", []).append(r.id)
        by_mech = {m: sorted(ids) for m, ids in by_mech.items()}
        # escalation 類沿用既有 catch-attribution（wired＝failure_mode 已定義 ∩ escalation SSOT）
        all_ids = {r.id for r in rules}
        esc_attributable = sorted(self._ESCALATION_ATTRIBUTABLE_RULE_IDS & all_ids)
        wired = sorted({r.id for r in rules if r.failure_mode} & set(esc_attributable))
        esc_denom = len(esc_attributable)
        esc_pct = round(100.0 * len(wired) / esc_denom, 1) if esc_denom else 0.0
        return {
            "total_active_rules": len(rules),
            "by_mechanism": {
                m: {"rule_ids": ids, "count": len(ids)} for m, ids in by_mech.items()
            },
            "escalation_coverage": {
                "wired_rule_ids": wired,
                "denominator": esc_denom,
                "coverage_pct": esc_pct,
            },
            "auto_measurable_mechanisms": sorted(self._AUTO_MEASURABLE_MECHANISMS),
            "deferred_runtime_mechanisms": sorted(self._DEFERRED_RUNTIME_MECHANISMS),
            "non_auto_measurable_mechanisms": sorted(self._NON_AUTO_MEASURABLE_MECHANISMS),
            # fail-closed：非空＝分類缺口（W-54-1 交叉鎖測試會擋）
            "unclassified_rule_ids": by_mech.get("unclassified", []),
            "denominator_note": (
                "覆蓋＝『守門機制是否真實分類 + (escalation 類) catch 側是否接線』之靜態-結構度量"
                "（非『守門 runtime 是否有效』——後者對 manual 類本質不可測、對 hook/lint_tlc/meta_loop "
                "屬 justified-deferred runtime 埋點）。manual 類誠實排除於自動分母；hook/lint_tlc/meta_loop "
                "分類在位但 runtime 有效性度量延後（無消費者 + Rule 2 + meta_loop 恐觸 TLC）。DEF-19-001 後續標的。"
            ),
            "well_founded": (
                "純讀 rule_loader.load_all()、零 FSM 副作用、零新增 reachable 邊、永不 set_maturity"
                "（R-9.20 #11）；fail-closed（度量失敗不阻塞、不偽綠）。unclassified 非空即分類缺口，"
                "由 enforcement_mechanism 交叉鎖測試攔下（W-54-1）。"
            ),
        }

    # ===== Phase I M3 / ACT-068: Value-driven goal autonomy (BACKLOG_PRIORITIZED) =====
    BACKLOG_PRIORITIZED_ALLOWED_SOURCES = frozenset({"AGENT_LOAD"})

    def enter_backlog_prioritized(self, *, reason: str = "", backlog_ref: str = "") -> dict:
        """Enter BACKLOG_PRIORITIZED gatekeep from AGENT_LOAD (Rule 9.21 / ACT-068).

        Happy-path reachable (AGENT_LOAD → BACKLOG_PRIORITIZED). value_planner
        ranks candidate specs; a human signs off the highest-ROI target BEFORE
        the spec loop begins. value model 只排序不裁決（人工 signoff gate）。
        """
        src = self.state.current
        if src == "BACKLOG_PRIORITIZED":
            return {"noop": True, "current": src}
        if src not in self.BACKLOG_PRIORITIZED_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_backlog_prioritized blocked: current={src}, "
                f"expected one of {sorted(self.BACKLOG_PRIORITIZED_ALLOWED_SOURCES)}"
            )
        self.transition(
            "BACKLOG_PRIORITIZED",
            reason=reason or "value-driven goal selection (ACT-068)",
            spec_refs=[backlog_ref] if backlog_ref else None,
            trigger="backlog_prioritized_enter",
        )
        return {"entered": True, "from": src, "to": "BACKLOG_PRIORITIZED"}

    def exit_backlog_prioritized(self, *, selected_ref: str = "", reason: str = "") -> dict:
        """Leave BACKLOG_PRIORITIZED → SPEC_DRAFTING (only exit, post human signoff)."""
        if self.state.current != "BACKLOG_PRIORITIZED":
            raise TransitionError(
                f"exit_backlog_prioritized called in state={self.state.current}, "
                "expected BACKLOG_PRIORITIZED"
            )
        self.transition(
            "SPEC_DRAFTING",
            reason=reason or f"backlog target selected={selected_ref}",
            spec_refs=[selected_ref] if selected_ref else None,
            trigger="backlog_prioritized_exit",
        )
        return {"exited": True, "to": "SPEC_DRAFTING", "selected": selected_ref}

    # ===== Phase I M1 / ACT-061: Sandbox Hardening Gate =====
    def enter_sandbox_hardening_gate(self, *, reason: str = "", artifact_refs: Optional[list] = None) -> dict:
        """Enter SANDBOX_HARDENING_GATE from IMPLEMENTATION (Rule 9.21 / ACT-061).

        Gatekeep before execution grounding: image allow-list + spec signature +
        dependency lockfile hash + loop self-STRIDE. Happy-path reachable.
        """
        src = self.state.current
        if src == "SANDBOX_HARDENING_GATE":
            return {"noop": True, "current": src}
        self.transition(
            "SANDBOX_HARDENING_GATE",
            reason=reason or "enter sandbox hardening gate (ACT-061)",
            spec_refs=list(artifact_refs or []),
            trigger="sandbox_hardening_enter",
        )
        return {"entered": True, "from": src, "to": "SANDBOX_HARDENING_GATE"}

    def exit_sandbox_hardening_gate(self, verdict: str, *, reason: str = "") -> dict:
        """Leave SANDBOX_HARDENING_GATE based on the hardening verdict.

        verdict ∈ {"pass", "policy_violation"}:
          - pass             → EXECUTION_EVALUATION (proceed to grounded eval)
          - policy_violation → ESCALATION (structural; DiagnosticAgent →
                               sandbox_policy_violation, not auto-recoverable)
        """
        if self.state.current != "SANDBOX_HARDENING_GATE":
            raise TransitionError(
                f"exit_sandbox_hardening_gate called in state={self.state.current}, "
                "expected SANDBOX_HARDENING_GATE"
            )
        verdict = verdict.strip().lower()
        if verdict == "pass":
            self.transition(
                "EXECUTION_EVALUATION",
                reason=reason or "sandbox hardening passed",
                trigger="sandbox_hardening_pass",
            )
            return {"exited": True, "verdict": "pass", "to": "EXECUTION_EVALUATION"}
        if verdict == "policy_violation":
            self.state.record_escalation(
                reason or "sandbox_policy_violation (ACT-061): image/簽章/lockfile/self-STRIDE 違反"
            )
            # W-38-1（DEF-19-001 catch 覆蓋 5/39→6/39）：SANDBOX_HARDENING_GATE policy_violation
            # → ESCALATION 即 R-SELF-STRIDE（Loop Self-STRIDE）守望的失敗模式真實發生，結構化歸因。
            # 此為唯一生產 escalation 落點（verdict=pass 路徑轉 EXECUTION_EVALUATION、不 escalate
            # 不歸因），與既有 5 條接線零交集，杜絕雙重歸因（DEF-18-001）。flag OFF＝不記（零退化）。
            self._record_escalation_catches(["R-SELF-STRIDE"])
            # transition to ESCALATION (emergency target) so decision_trace records it.
            self.transition(
                "ESCALATION",
                reason=reason or "sandbox hardening policy violation",
                trigger="sandbox_hardening_fail",
            )
            return {"exited": True, "verdict": "policy_violation", "to": "ESCALATION"}
        raise ValueError(f"invalid verdict={verdict!r}; expected 'pass' / 'policy_violation'")

    # ===== Phase I M1 / ACT-063: Evaluator self-audit (EVALUATOR_AUDIT) =====
    EVALUATOR_AUDIT_ALLOWED_SOURCES = frozenset({
        "EXECUTION_EVALUATION", "PRODUCTION_SIGNAL", "DRIFT_OBSERVATION",
    })

    def enter_evaluator_audit(self, *, reason: str = "", drift_ref: str = "") -> dict:
        """Enter EVALUATOR_AUDIT (non-blocking observation, Rule 9.21 / ACT-063).

        Triggered when OQS calibration detects drift ("OQS pass but production
        violated" N times) or oracle freshness check fails. Explicit entry API.
        """
        src = self.state.current
        if src == "EVALUATOR_AUDIT":
            return {"noop": True, "current": src}
        if src not in self.EVALUATOR_AUDIT_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_evaluator_audit blocked: current={src}, "
                f"expected one of {sorted(self.EVALUATOR_AUDIT_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("evaluator_audit_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        if drift_ref:
            tracking["drift_ref"] = drift_ref
        self.state.current = "EVALUATOR_AUDIT"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="EVALUATOR_AUDIT",
                reason=reason or "evaluator self-audit (ACT-063)",
                spec_refs=[drift_ref] if drift_ref else None,
                trigger="evaluator_audit_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "EVALUATOR_AUDIT"}

    def exit_evaluator_audit(self, decision: str, *, reason: str = "") -> dict:
        """Leave EVALUATOR_AUDIT based on audit decision.

        decision ∈ {"continue", "recalibrate", "respec"}:
          - continue    → EXECUTION_EVALUATION (no drift; resume evaluation)
          - recalibrate → RELEASE       (human recalibrated OQS / bumped SCORER_VERSION)
          - respec      → SPEC_DRAFTING  (oracle stale; spec must evolve)
        """
        if self.state.current != "EVALUATOR_AUDIT":
            raise TransitionError(
                f"exit_evaluator_audit called in state={self.state.current}, expected EVALUATOR_AUDIT"
            )
        decision = decision.strip().lower()
        mapping = {"continue": "EXECUTION_EVALUATION", "recalibrate": "RELEASE", "respec": "SPEC_DRAFTING"}
        if decision not in mapping:
            raise ValueError(
                f"invalid decision={decision!r}; expected 'continue' / 'recalibrate' / 'respec'"
            )
        target = mapping[decision]
        self.transition(
            target,
            reason=reason or f"evaluator_audit exit decision={decision}",
            trigger="evaluator_audit_exit",
        )
        return {"exited": True, "decision": decision, "to": target}

    # ===== Phase I M2 / ACT-064: Runtime Monitor Violation (MONITOR_VIOLATION) =====
    def enter_monitor_violation(self, *, invariant: str, detail: str = "", report_ref: str = "") -> dict:
        """Enter MONITOR_VIOLATION when spec_monitor detects an invariant breach.

        Rule 9.21 / ACT-064: runtime assertions synthesised from SDD_FSM.tla's
        safety invariants. Entry allowed from any non-blocking, non-terminal
        state (mirrors TOKEN_BUDGET_CRITICAL wildcard entry). Only exit is
        ESCALATION (non-recoverable).
        """
        src = self.state.current
        if src == "MONITOR_VIOLATION":
            return {"noop": True, "current": src}
        if src in self._BLOCKING_STATES or src in {"RELEASE", "TERMINATED"}:
            raise TransitionError(
                f"enter_monitor_violation blocked: current={src} is terminal/blocking"
            )
        tracking = self.state.root.setdefault("monitor_violation_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["invariant"] = invariant
        tracking["detail"] = detail
        tracking["source_state"] = src
        self.state.current = "MONITOR_VIOLATION"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="MONITOR_VIOLATION",
                reason=f"runtime monitor: {invariant} violated — {detail}"[:300],
                spec_refs=[report_ref] if report_ref else None,
                trigger="monitor_violation_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "invariant": invariant}

    def exit_monitor_violation(self, *, reason: str = "") -> dict:
        """Leave MONITOR_VIOLATION → ESCALATION (only legal exit, Rule 9.21)."""
        if self.state.current != "MONITOR_VIOLATION":
            raise TransitionError(
                f"exit_monitor_violation called in state={self.state.current}, expected MONITOR_VIOLATION"
            )
        tracking = self.state.root.get("monitor_violation_tracking", {})
        self.state.record_escalation(
            reason or f"runtime monitor invariant breach: {tracking.get('invariant', '?')}"
        )
        # W-19-2：monitor invariant 破壞 → MONITOR_VIOLATION → ESCALATION 即 R-9.21 守望的
        # 失敗模式真實發生，結構化歸因到 R-9.21（無歧義映射）。flag OFF＝不記（零退化）。
        self._record_escalation_catches(["R-9.21"])
        self.transition(
            "ESCALATION",
            reason=reason or "monitor_violation → ESCALATION",
            trigger="monitor_violation_exit",
        )
        return {"exited": True, "to": "ESCALATION"}

    # ===== Phase I M3 / ACT-066: Memory Consolidation (success crystallization) =====
    MEMORY_CONSOLIDATION_ALLOWED_SOURCES = frozenset({"LEARNING_COMMIT", "RELEASE"})

    def enter_memory_consolidation(self, *, reason: str = "", report_ref: str = "") -> dict:
        """Enter MEMORY_CONSOLIDATION (non-blocking observation, Rule 9.21 / ACT-066).

        nightly sleep-phase cron or post-LEARNING_COMMIT/RELEASE. spl_consolidator
        clusters productive episodes into proposed SPL skills (human verified gate).
        """
        src = self.state.current
        if src == "MEMORY_CONSOLIDATION":
            return {"noop": True, "current": src}
        if src not in self.MEMORY_CONSOLIDATION_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_memory_consolidation blocked: current={src}, "
                f"expected one of {sorted(self.MEMORY_CONSOLIDATION_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("memory_consolidation_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        if report_ref:
            tracking["report_ref"] = report_ref
        self.state.current = "MEMORY_CONSOLIDATION"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="MEMORY_CONSOLIDATION",
                reason=reason or "success crystallization sleep-phase (ACT-066)",
                spec_refs=[report_ref] if report_ref else None,
                trigger="memory_consolidation_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "MEMORY_CONSOLIDATION"}

    def exit_memory_consolidation(self, decision: str, *, reason: str = "") -> dict:
        """Leave MEMORY_CONSOLIDATION based on decision.

        decision ∈ {"done", "respec"}:
          - done   → RELEASE       (crystallization complete, no action)
          - respec → SPEC_DRAFTING (consolidation revealed a spec-level gap)
        """
        if self.state.current != "MEMORY_CONSOLIDATION":
            raise TransitionError(
                f"exit_memory_consolidation called in state={self.state.current}, "
                "expected MEMORY_CONSOLIDATION"
            )
        decision = decision.strip().lower()
        mapping = {"done": "RELEASE", "respec": "SPEC_DRAFTING"}
        if decision not in mapping:
            raise ValueError(f"invalid decision={decision!r}; expected 'done' / 'respec'")
        target = mapping[decision]
        self.transition(
            target,
            reason=reason or f"memory_consolidation exit decision={decision}",
            trigger="memory_consolidation_exit",
        )
        return {"exited": True, "decision": decision, "to": target}

    # ===== Phase J / ACT-074: Adversarial Evaluation (gatekeep) =====
    ADVERSARIAL_EVALUATION_ALLOWED_SOURCES = frozenset({"EXECUTION_EVALUATION"})

    def enter_adversarial_evaluation(self, *, reason: str = "", profile_version: str = "v1.0",
                                     rounds: int = 8) -> dict:
        """Enter ADVERSARIAL_EVALUATION (gatekeep, Rule 9.22.1 / ACT-074).

        對抗判官閘：接在 EXECUTION_EVALUATION verdict=pass 之後。攻擊輪數有界
        （rounds，clamp 由 adversarial_synthesizer.adversarial_rounds 守）。
        """
        src = self.state.current
        if src == "ADVERSARIAL_EVALUATION":
            return {"noop": True, "current": src}
        if src not in self.ADVERSARIAL_EVALUATION_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_adversarial_evaluation blocked: current={src}, "
                f"expected one of {sorted(self.ADVERSARIAL_EVALUATION_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("adversarial_evaluation_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["profile_version"] = profile_version
        tracking["rounds"] = int(rounds)
        self.transition(
            "ADVERSARIAL_EVALUATION",
            reason=reason or "adversarial evaluation gate (ACT-074)",
            trigger="adversarial_evaluation_enter",
        )
        return {"entered": True, "from": src, "to": "ADVERSARIAL_EVALUATION"}

    def exit_adversarial_evaluation(self, verdict: str, *, reason: str = "") -> dict:
        """Leave ADVERSARIAL_EVALUATION based on adversarial verdict.

        verdict ∈ {"robust", "counterexample", "spec_gap"}:
          - robust         → PR_REVIEW（N 輪攻擊無破）
          - counterexample → IMPLEMENTATION（runtime 缺陷，計入 retry budget）
          - spec_gap       → SPEC_AUDIT（AC 漏寫隱含 invariant）
        inconclusive (FLAKY) 不在此處理 — 隔離、不計分、不進 retry（Rule 9.22.1）。
        """
        if self.state.current != "ADVERSARIAL_EVALUATION":
            raise TransitionError(
                f"exit_adversarial_evaluation called in state={self.state.current}, "
                "expected ADVERSARIAL_EVALUATION"
            )
        v = verdict.strip().lower()
        mapping = {
            "robust": "PR_REVIEW",
            "counterexample": "IMPLEMENTATION",
            "spec_gap": "SPEC_AUDIT",
        }
        if v not in mapping:
            raise ValueError(
                f"invalid verdict={verdict!r}; expected 'robust'/'counterexample'/'spec_gap' "
                "(FLAKY/inconclusive must be isolated, not routed)"
            )
        target = mapping[v]
        self.transition(
            target,
            reason=reason or f"adversarial_evaluation verdict={v}",
            trigger="adversarial_evaluation_exit",
        )
        return {"exited": True, "verdict": v, "to": target}

    # ===== Phase K / ACT-082: Intent Decomposition (gatekeep, 有界) =====
    INTENT_DECOMPOSITION_ALLOWED_SOURCES = frozenset({"AGENT_LOAD"})

    def enter_intent_decomposition(self, *, reason: str = "", max_nodes: int = 32) -> dict:
        """Enter INTENT_DECOMPOSITION (gatekeep, Rule 9.23.1 / ACT-082).

        意圖分解閘：接在 AGENT_LOAD 後、BACKLOG_PRIORITIZED 前。把 high-level intent
        分解為 acyclic spec-DAG（節點數有界 max_nodes，clamp 由 intent_decomposer 守）。
        """
        src = self.state.current
        if src == "INTENT_DECOMPOSITION":
            return {"noop": True, "current": src}
        if src not in self.INTENT_DECOMPOSITION_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_intent_decomposition blocked: current={src}, "
                f"expected one of {sorted(self.INTENT_DECOMPOSITION_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("intent_decomposition_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["max_nodes"] = int(max_nodes)
        self.transition(
            "INTENT_DECOMPOSITION",
            reason=reason or "intent decomposition gate (ACT-082)",
            trigger="intent_decomposition_enter",
        )
        return {"entered": True, "from": src, "to": "INTENT_DECOMPOSITION"}

    def exit_intent_decomposition(self, outcome: str, *, reason: str = "") -> dict:
        """Leave INTENT_DECOMPOSITION based on decomposition outcome.

        outcome ∈ {"decomposed", "underspecified"}:
          - decomposed     → BACKLOG_PRIORITIZED（acyclic spec-DAG，候選餵 value_planner 排 ROI）
          - underspecified → HUMAN_PENDING（意圖過模糊/成環/觸頂，請人工澄清，Rule 8）
        """
        if self.state.current != "INTENT_DECOMPOSITION":
            raise TransitionError(
                f"exit_intent_decomposition called in state={self.state.current}, "
                "expected INTENT_DECOMPOSITION"
            )
        o = outcome.strip().lower()
        mapping = {"decomposed": "BACKLOG_PRIORITIZED", "underspecified": "HUMAN_PENDING"}
        if o not in mapping:
            raise ValueError(
                f"invalid outcome={outcome!r}; expected 'decomposed' / 'underspecified'"
            )
        target = mapping[o]
        self.transition(
            target,
            reason=reason or f"intent_decomposition outcome={o}",
            trigger="intent_decomposition_exit",
        )
        return {"exited": True, "outcome": o, "to": target}

    # ===== Phase K / ACT-084: Spec Debate (observation, advisory transient) =====
    SPEC_DEBATE_ALLOWED_SOURCES = frozenset({"SCG_VALIDATION"})

    def enter_spec_debate(self, *, ac_id: str = "", reason: str = "",
                          rounds: int = 4, profile_version: str = "v1.0") -> dict:
        """Enter SPEC_DEBATE (non-blocking observation, Rule 9.23.3 / ACT-084).

        SCG-0 子步：AmbiguityScorer 落 near-threshold band 時啟兩隔離詮釋辯證；
        observation 入口直設 current（不在 _HAPPY_PATH，比照 capability_benchmark）。
        """
        src = self.state.current
        if src == "SPEC_DEBATE":
            return {"noop": True, "current": src}
        if src not in self.SPEC_DEBATE_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_spec_debate blocked: current={src}, "
                f"expected one of {sorted(self.SPEC_DEBATE_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("spec_debate_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        tracking["rounds"] = int(rounds)
        tracking["profile_version"] = profile_version
        if ac_id:
            tracking["ac_id"] = ac_id
        self.state.current = "SPEC_DEBATE"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="SPEC_DEBATE",
                reason=reason or f"spec debate disambiguation for {ac_id} (ACT-084)",
                spec_refs=[ac_id] if ac_id else None,
                trigger="spec_debate_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "SPEC_DEBATE"}

    def exit_spec_debate(self, decision: str, *, reason: str = "",
                         interp_a: str = "", interp_b: str = "",
                         divergence: float = 0.0, markers=None) -> dict:
        """Leave SPEC_DEBATE.

        decision ∈ {"consensus"→SCG_VALIDATION（兩詮釋收斂，續跑 SCG）,
                    "divergence"→HUMAN_PENDING（兩詮釋互斥，人工澄清，Rule 9.23.4 advisory）}.

        divergence 路徑：若提供兩詮釋，落盤 knowledge/disambiguation/DIS-*.yaml
        （advisory、proposed、acyclic 不覆寫；回饋 AmbiguityScorer 校準語料，Rule 9.23.4/9.23.5）。
        """
        if self.state.current != "SPEC_DEBATE":
            raise TransitionError(
                f"exit_spec_debate called in state={self.state.current}, expected SPEC_DEBATE"
            )
        d = decision.strip().lower()
        mapping = {"consensus": "SCG_VALIDATION", "divergence": "HUMAN_PENDING"}
        if d not in mapping:
            raise ValueError(f"invalid decision={decision!r}; expected 'consensus' / 'divergence'")
        target = mapping[d]

        persisted: str = ""
        if d == "divergence" and (interp_a or interp_b):
            tracking = self.state.root.get("spec_debate_tracking", {})
            try:
                from tools.fsm_runtime.spec_debate import persist_disambiguation
                path = persist_disambiguation(
                    tracking.get("ac_id", ""), interp_a, interp_b, divergence,
                    verdict=None, markers=markers,
                    profile_version=tracking.get("profile_version", "v1.0"),
                )
                persisted = str(path)
            except Exception:  # noqa: BLE001  落盤為 advisory，失敗不阻塞退場
                persisted = ""

        self.transition(
            target,
            reason=reason or f"spec_debate decision={d}",
            trigger="spec_debate_exit",
        )
        result = {"exited": True, "decision": d, "to": target}
        if persisted:
            result["disambiguation"] = persisted
        return result

    # ===== Phase J / ACT-076: Capability Benchmark (observation) =====
    CAPABILITY_BENCHMARK_ALLOWED_SOURCES = frozenset({"SCAFFOLD_GC", "MEMORY_CONSOLIDATION"})

    def enter_capability_benchmark(self, *, reason: str = "", ledger_ref: str = "") -> dict:
        """Enter CAPABILITY_BENCHMARK (non-blocking observation, Rule 9.22.3 / ACT-076)."""
        src = self.state.current
        if src == "CAPABILITY_BENCHMARK":
            return {"noop": True, "current": src}
        if src not in self.CAPABILITY_BENCHMARK_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_capability_benchmark blocked: current={src}, "
                f"expected one of {sorted(self.CAPABILITY_BENCHMARK_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("capability_benchmark_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        if ledger_ref:
            tracking["ledger_ref"] = ledger_ref
        self.state.current = "CAPABILITY_BENCHMARK"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="CAPABILITY_BENCHMARK",
                reason=reason or "capability benchmark (ACT-076)",
                spec_refs=[ledger_ref] if ledger_ref else None,
                trigger="capability_benchmark_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "CAPABILITY_BENCHMARK"}

    def exit_capability_benchmark(self, decision: str, *, reason: str = "") -> dict:
        """Leave CAPABILITY_BENCHMARK. decision ∈ {"done"→RELEASE, "respec"→SPEC_DRAFTING}."""
        if self.state.current != "CAPABILITY_BENCHMARK":
            raise TransitionError(
                f"exit_capability_benchmark called in state={self.state.current}, "
                "expected CAPABILITY_BENCHMARK"
            )
        decision = decision.strip().lower()
        mapping = {"done": "RELEASE", "respec": "SPEC_DRAFTING"}
        if decision not in mapping:
            raise ValueError(f"invalid decision={decision!r}; expected 'done' / 'respec'")
        target = mapping[decision]
        self.transition(
            target,
            reason=reason or f"capability_benchmark exit decision={decision}",
            trigger="capability_benchmark_exit",
        )
        return {"exited": True, "decision": decision, "to": target}

    # ===== Phase J / ACT-078: Spec Patch Proposal (observation) =====
    SPEC_PATCH_PROPOSAL_ALLOWED_SOURCES = frozenset({"SPEC_AUDIT", "ESCALATION"})
    MAX_SPEC_PATCH_PER_AC = 2  # Rule 9.22.5

    def enter_spec_patch_proposal(self, *, ac_id: str, reason: str = "",
                                  patch_ref: str = "") -> dict:
        """Enter SPEC_PATCH_PROPOSAL (non-blocking observation, Rule 9.22.5 / ACT-078).

        同一 AC 全 session ≤ MAX_SPEC_PATCH_PER_AC 次；超限直升 ESCALATION
        （防 patch 抖動）。
        """
        src = self.state.current
        if src == "SPEC_PATCH_PROPOSAL":
            return {"noop": True, "current": src}
        if src not in self.SPEC_PATCH_PROPOSAL_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_spec_patch_proposal blocked: current={src}, "
                f"expected one of {sorted(self.SPEC_PATCH_PROPOSAL_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("spec_patch_tracking", {})
        counts = tracking.setdefault("count_per_ac", {})
        prior = int(counts.get(ac_id, 0))
        if prior >= self.MAX_SPEC_PATCH_PER_AC:
            # 超限 → 直升 ESCALATION（不進 SPEC_PATCH_PROPOSAL）
            self.state.record_escalation(
                f"spec_patch limit exceeded for {ac_id} "
                f"({prior} ≥ {self.MAX_SPEC_PATCH_PER_AC}); structural — needs human"
            )
            # W-20-1（catch 覆蓋補強 DEF-19-001）：spec_patch per-AC 上限耗盡 → ESCALATION 即
            # R-9.22（Phase J 規格自癒）守望的失敗模式真實發生，結構化歸因到 R-9.22（無歧義映射，
            # 非時序猜測）。flag OFF＝不記（零退化）；fail-closed；只增 catch_count（R-9.20 #11）。
            self._record_escalation_catches(["R-9.22"])
            self.transition(
                "ESCALATION",
                reason=reason or f"spec_patch limit exceeded for {ac_id}",
                trigger="spec_patch_limit_escalation",
            )
            return {"escalated": True, "ac_id": ac_id, "count": prior, "to": "ESCALATION"}
        counts[ac_id] = prior + 1
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        tracking["last_ac_id"] = ac_id
        if patch_ref:
            tracking["patch_ref"] = patch_ref
        self.state.current = "SPEC_PATCH_PROPOSAL"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="SPEC_PATCH_PROPOSAL",
                reason=reason or f"spec self-repair draft for {ac_id} (ACT-078)",
                spec_refs=[ac_id] + ([patch_ref] if patch_ref else []),
                trigger="spec_patch_proposal_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "SPEC_PATCH_PROPOSAL",
                "ac_id": ac_id, "count": counts[ac_id]}

    def exit_spec_patch_proposal(self, outcome: str, *, reason: str = "") -> dict:
        """Leave SPEC_PATCH_PROPOSAL. outcome ∈ {"drafted"→HUMAN_PENDING, "nodraft"→ESCALATION}."""
        if self.state.current != "SPEC_PATCH_PROPOSAL":
            raise TransitionError(
                f"exit_spec_patch_proposal called in state={self.state.current}, "
                "expected SPEC_PATCH_PROPOSAL"
            )
        outcome = outcome.strip().lower()
        mapping = {"drafted": "HUMAN_PENDING", "nodraft": "ESCALATION"}
        if outcome not in mapping:
            raise ValueError(f"invalid outcome={outcome!r}; expected 'drafted' / 'nodraft'")
        target = mapping[outcome]
        if outcome == "nodraft":
            self.state.record_escalation(reason or "spec_patch: unable to draft, escalate")
        self.transition(
            target,
            reason=reason or f"spec_patch_proposal outcome={outcome}",
            trigger="spec_patch_proposal_exit",
        )
        return {"exited": True, "outcome": outcome, "to": target}

    # ===== Phase L M-L2 / ACT-092: Experiment Replay (observation) =====
    EXPERIMENT_REPLAY_ALLOWED_SOURCES = frozenset({"SPEC_PATCH_PROPOSAL"})

    def enter_experiment_replay(self, *, ac_id: str = "", reason: str = "",
                                patch_ref: str = "") -> dict:
        """Enter EXPERIMENT_REPLAY (non-blocking observation, Rule 9.24.4 / ACT-092).

        補丁送 HUMAN_PENDING approve 前先過離線反事實重放；observation 入口直設
        current（不在 _HAPPY_PATH，比照 spec_debate / capability_benchmark）。
        """
        src = self.state.current
        if src == "EXPERIMENT_REPLAY":
            return {"noop": True, "current": src}
        if src not in self.EXPERIMENT_REPLAY_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_experiment_replay blocked: current={src}, "
                f"expected one of {sorted(self.EXPERIMENT_REPLAY_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("experiment_replay_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        if ac_id:
            tracking["ac_id"] = ac_id
        if patch_ref:
            tracking["patch_ref"] = patch_ref
        self.state.current = "EXPERIMENT_REPLAY"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="EXPERIMENT_REPLAY",
                reason=reason or f"counterfactual replay for {ac_id} (ACT-092)",
                spec_refs=[ac_id] if ac_id else None,
                trigger="experiment_replay_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "EXPERIMENT_REPLAY"}

    def exit_experiment_replay(self, decision: str, *, reason: str = "",
                               evidence: str = "") -> dict:
        """Leave EXPERIMENT_REPLAY.

        decision ∈ {"done"→SPEC_PATCH_PROPOSAL（命中率證據附上續送人工，advisory）,
                    "inconclusive"→HUMAN_PENDING（歷史語料不足，導人工裁決，Rule 8）}.

        evidence（如 replay report 命中率一行）落入 experiment_replay_tracking，
        供 SPEC_PATCH_PROPOSAL / steersman 附掛（Rule 9.24.4：僅證據不自動 approve）。
        """
        if self.state.current != "EXPERIMENT_REPLAY":
            raise TransitionError(
                f"exit_experiment_replay called in state={self.state.current}, "
                "expected EXPERIMENT_REPLAY"
            )
        d = decision.strip().lower()
        mapping = {"done": "SPEC_PATCH_PROPOSAL", "inconclusive": "HUMAN_PENDING"}
        if d not in mapping:
            raise ValueError(f"invalid decision={decision!r}; expected 'done' / 'inconclusive'")
        target = mapping[d]
        if evidence:
            tracking = self.state.root.setdefault("experiment_replay_tracking", {})
            tracking["evidence"] = evidence
        self.transition(
            target,
            reason=reason or f"experiment_replay decision={d}: {evidence}".strip(),
            trigger="experiment_replay_exit",
        )
        result = {"exited": True, "decision": d, "to": target}
        if evidence:
            result["evidence"] = evidence
        return result

    # ===== Phase I M3 / ACT-067: Production Behavioral Signal =====
    PRODUCTION_BEHAVIORAL_ALLOWED_SOURCES = frozenset({
        "RELEASE", "RELEASE_READY", "PRODUCTION_SIGNAL",
    })

    def enter_production_behavioral_signal(self, *, reason: str = "", divergence_ref: str = "") -> dict:
        """Enter PRODUCTION_BEHAVIORAL_SIGNAL (non-blocking observation, ACT-067).

        Production functional divergence (contract_shape / ordering /
        invariant_violation / missing_branch) — beyond numeric SLO. Explicit
        entry API (RELEASE deliberately terminal).
        """
        src = self.state.current
        if src == "PRODUCTION_BEHAVIORAL_SIGNAL":
            return {"noop": True, "current": src}
        if src not in self.PRODUCTION_BEHAVIORAL_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_production_behavioral_signal blocked: current={src}, "
                f"expected one of {sorted(self.PRODUCTION_BEHAVIORAL_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("production_behavioral_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        if divergence_ref:
            tracking["divergence_ref"] = divergence_ref
        self.state.current = "PRODUCTION_BEHAVIORAL_SIGNAL"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="PRODUCTION_BEHAVIORAL_SIGNAL",
                reason=reason or "production behavioral divergence (ACT-067)",
                spec_refs=[divergence_ref] if divergence_ref else None,
                trigger="production_behavioral_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "PRODUCTION_BEHAVIORAL_SIGNAL"}

    @staticmethod
    def _auto_draft_slv(fpl_id: str) -> dict:
        """W-16-1 / B-axis L5：自既有 FPL 合成一份 `trust_level: proposed` SLV 草案並落盤。

        純合成、**不轉態**（呼叫端負責 FSM 狀態）。鏡像 improving_15 接入 enter_auto_recovery
        「呼叫既有純函式而非重寫」模式：複用 slv_generator.{load_fpl_entry, propose_slv_from_fpl,
        write_rule_candidate}。草案恆 `trust_level: proposed`（R-9.11，永不自動升 verified）。

        **fail-closed**：FPL 缺/合成失敗/落盤失敗一律 raise；呼叫端據此停在 LEARNING_COMMIT
        不偽造草案（人仍可手動 /slv-generator propose）。

        Returns: {"slv_id": str, "rule_path": str, "trust_level": "proposed"}
        """
        from . import slv_generator as _slv  # local import to avoid top-level churn / cycles
        fpl = _slv.load_fpl_entry(fpl_id)
        cand = _slv.propose_slv_from_fpl(fpl)
        path = _slv.write_rule_candidate(cand)
        return {"slv_id": cand.id, "rule_path": str(path), "trust_level": cand.trust_level}

    def exit_production_behavioral_signal(
        self, decision: str, *, reason: str = "", fpl_id: Optional[str] = None
    ) -> dict:
        """Leave PRODUCTION_BEHAVIORAL_SIGNAL based on decision.

        decision ∈ {"inform", "respec", "learn"}:
          - inform → RELEASE         (informational only)
          - respec → SPEC_DRAFTING   (divergence requires re-spec)
          - learn  → LEARNING_COMMIT (divergence accumulated into FPL draft)

        W-16-1 / B-axis L5（規則自演化「自動提議」接入主迴圈）：當 decision=="learn"
        ∧ `_slv_auto_propose_enabled()`（flag `SDD_ENABLE_SLV_AUTO_PROPOSE` 預設 OFF）
        ∧ 提供 `fpl_id` 時，轉態到 LEARNING_COMMIT **之後**自動 draft 一份 proposed 草案並
        填 `learning_commit_tracking`（使迴圈不再需人手動跑 CLI ＝ L5 自走信號）。

        紅線守界：① 草案恆 trust_level=proposed（R-9.11）；② trust_level→verified 仍 🔴 人工
        （exit_learning_commit 既有強制檢查不動）；③ fail-closed：auto-draft 任何失敗停在
        LEARNING_COMMIT 不偽造、不轉錯態。flag OFF 或無 fpl_id → 行為逐字同 v0.06（純轉態）。
        **免五軌 TLC**：只在既有 learn→LEARNING_COMMIT 轉態後加非轉態 side-effect，零新增邊。

        附帶修 DEF-16-001：learn 路徑原不填 tracking，致 learn→exit_learning_commit("approved")
        因缺 proposed_rule_path 而 raise（採納鏈結構性斷裂）；flag ON 時填 tracking 即閉合該鏈。
        """
        if self.state.current != "PRODUCTION_BEHAVIORAL_SIGNAL":
            raise TransitionError(
                f"exit_production_behavioral_signal called in state={self.state.current}, "
                "expected PRODUCTION_BEHAVIORAL_SIGNAL"
            )
        decision = decision.strip().lower()
        mapping = {"inform": "RELEASE", "respec": "SPEC_DRAFTING", "learn": "LEARNING_COMMIT"}
        if decision not in mapping:
            raise ValueError(
                f"invalid decision={decision!r}; expected 'inform' / 'respec' / 'learn'"
            )
        target = mapping[decision]
        self.transition(
            target,
            reason=reason or f"production_behavioral exit decision={decision}",
            trigger="production_behavioral_exit",
        )
        result = {"exited": True, "decision": decision, "to": target}
        # W-16-1：learn 分支自動提議（flag-gated、fail-closed、轉態後 side-effect）
        if decision == "learn" and _slv_auto_propose_enabled() and fpl_id:
            try:
                drafted = self._auto_draft_slv(fpl_id)
                import datetime as _dt
                tracking = self.state.root.setdefault("learning_commit_tracking", {})
                tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(
                    timespec="seconds"
                )
                tracking["fpl_id"] = fpl_id
                tracking["proposed_slv_id"] = drafted["slv_id"]
                tracking["proposed_rule_path"] = drafted["rule_path"]
                tracking["review_status"] = "pending"
                tracking["entered_from"] = "PRODUCTION_BEHAVIORAL_SIGNAL"
                tracking["origin"] = "auto"  # W-16-2 L5 信號：標記自動提議來源
                # 跨提議累計（learning_commit_tracking 持久於 state.root），供 learning_loop_stats
                # 量測「自走比例」；exit_learning_commit 不需改動（零退化既有 35+ 學習測試）。
                tracking["auto_proposed_count"] = int(tracking.get("auto_proposed_count", 0)) + 1
                save_state(self.state)
                result["auto_slv"] = {"proposed": True, **drafted}
            except Exception as exc:  # noqa: BLE001 — fail-closed：停在 LEARNING_COMMIT 不偽造
                result["auto_slv"] = {
                    "proposed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        return result

    # ----- Phase F M2 / ACT-030: Cross-Project Learning Hub entry/exit -----
    HUB_SYNC_ALLOWED_SOURCES = frozenset({
        "INIT", "SCENARIO_DETECT", "SPEC_DRAFTING", "SPEC_FROZEN",
        "RELEASE", "RELEASE_READY", "LEARNING_COMMIT", "HUMAN_PENDING",
    })

    def enter_hub_sync(
        self,
        *,
        direction: str,
        endpoint: Optional[str] = None,
        reason: str = "",
    ) -> dict:
        """Transition into HUB_SYNC observation state (non-blocking).

        ACT-030 Cross-Project Learning Hub. Direction ∈ {"pull", "push"}.
        - Disallowed from terminal/critical states (ESCALATION / TERMINATED /
          TOKEN_BUDGET_CRITICAL / AUTO_COMPACT_PENDING).
        - Disallowed from PRODUCTION_SIGNAL (avoid double-observation entanglement).
        - Records `resume_state` so exit_hub_sync(success) can return to source.
        Does NOT block tool calls.
        """
        if direction not in {"pull", "push"}:
            raise ValueError(f"direction must be 'pull' or 'push'; got {direction!r}")
        src = self.state.current
        if src == "HUB_SYNC":
            return {"noop": True, "current": src}
        if src not in self.HUB_SYNC_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_hub_sync blocked: current={src}, "
                f"expected one of {sorted(self.HUB_SYNC_ALLOWED_SOURCES)}"
            )
        self.state.current = "HUB_SYNC"
        tracking = self.state.root.setdefault("hub_sync_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["direction"] = direction
        tracking["endpoint"] = endpoint
        tracking["resume_state"] = src
        tracking["outcome"] = None
        try:
            self.state.append_decision_trace(
                from_state=src,
                to_state="HUB_SYNC",
                reason=reason or f"hub_sync {direction}",
                spec_refs=[endpoint] if endpoint else [],
                trigger=f"hub_sync_enter_{direction}",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "direction": direction, "endpoint": endpoint}

    def exit_hub_sync(self, outcome: str, *, reason: str = "") -> dict:
        """Leave HUB_SYNC.

        outcome ∈ {"success", "partial", "failed"}:
          - success → resume to recorded resume_state
          - partial → HUMAN_PENDING (conflicts await review; trust-ladder §陸)
          - failed → resume to recorded resume_state (NON-blocking: HUB-GOVERNANCE §捌)
        """
        if self.state.current != "HUB_SYNC":
            raise TransitionError(
                f"exit_hub_sync called in state={self.state.current}, expected HUB_SYNC"
            )
        outcome_norm = outcome.strip().lower()
        if outcome_norm not in {"success", "partial", "failed"}:
            raise ValueError(
                f"invalid outcome={outcome!r}; expected 'success' | 'partial' | 'failed'"
            )
        tracking = self.state.root.setdefault("hub_sync_tracking", {})
        resume_state = tracking.get("resume_state") or "SPEC_DRAFTING"
        target = "HUMAN_PENDING" if outcome_norm == "partial" else resume_state

        # transition() enforces happy-path; HUB_SYNC outbound set covers these.
        self.transition(
            target,
            reason=reason or f"exit HUB_SYNC outcome={outcome_norm}",
            trigger=f"hub_sync_exit_{outcome_norm}",
        )
        tracking["outcome"] = outcome_norm
        import datetime as _dt
        tracking["exited_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        save_state(self.state)
        return {"exited": True, "to": target, "outcome": outcome_norm}

    # ===== Phase Z / ACT-172: AutoClaude Delegated Execution (observation) =====
    AUTOCLAUDE_DELEGATED_ALLOWED_SOURCES = frozenset({"IMPLEMENTATION"})

    def enter_autoclaude_delegated(self, *, reason: str = "", playbook_ref: str = "") -> dict:
        """Enter AUTOCLAUDE_DELEGATED (non-blocking observation, Phase Z / ACT-172).

        During IMPLEMENTATION, an implementation sub-task is delegated to the
        AutoClaude playbook engine for execution. Modeled as a transient
        observation state (mirrors enter_memory_consolidation / enter_evaluator_audit):
        entry only from IMPLEMENTATION; IMPLEMENTATION's happy-path out-set does
        NOT include this state (observation-entry convention). Exit via
        exit_autoclaude_delegated(decision).
        """
        src = self.state.current
        if src == "AUTOCLAUDE_DELEGATED":
            return {"noop": True, "current": src}
        if src not in self.AUTOCLAUDE_DELEGATED_ALLOWED_SOURCES:
            raise TransitionError(
                f"enter_autoclaude_delegated blocked: current={src}, "
                f"expected one of {sorted(self.AUTOCLAUDE_DELEGATED_ALLOWED_SOURCES)}"
            )
        tracking = self.state.root.setdefault("autoclaude_delegated_tracking", {})
        import datetime as _dt
        tracking["entered_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        tracking["resume_state"] = src
        if playbook_ref:
            tracking["playbook_ref"] = playbook_ref
        self.state.current = "AUTOCLAUDE_DELEGATED"
        try:
            self.state.append_decision_trace(
                from_state=src, to_state="AUTOCLAUDE_DELEGATED",
                reason=reason or "SDD→AutoClaude playbook delegation (ACT-172)",
                spec_refs=[playbook_ref] if playbook_ref else None,
                trigger="autoclaude_delegated_enter",
            )
        except Exception:  # noqa: BLE001
            pass
        save_state(self.state)
        return {"entered": True, "from": src, "to": "AUTOCLAUDE_DELEGATED"}

    def exit_autoclaude_delegated(self, decision: str, *, reason: str = "") -> dict:
        """Leave AUTOCLAUDE_DELEGATED based on decision.

        decision ∈ {"done", "failed"}:
          - done   → IMPLEMENTATION (delegation complete, resume implementation)
          - failed → ESCALATION     (AutoClaude-side evolution also failed / gate
                                      breach → escalate, no auto-recovery)
        """
        if self.state.current != "AUTOCLAUDE_DELEGATED":
            raise TransitionError(
                f"exit_autoclaude_delegated called in state={self.state.current}, "
                "expected AUTOCLAUDE_DELEGATED"
            )
        decision = decision.strip().lower()
        mapping = {"done": "IMPLEMENTATION", "failed": "ESCALATION"}
        if decision not in mapping:
            raise ValueError(f"invalid decision={decision!r}; expected 'done' / 'failed'")
        target = mapping[decision]
        self.transition(
            target,
            reason=reason or f"autoclaude_delegated exit decision={decision}",
            trigger="autoclaude_delegated_exit",
        )
        return {"exited": True, "decision": decision, "to": target}


def _cli() -> int:
    parser = argparse.ArgumentParser(description="SDD FSM Runtime CLI")
    parser.add_argument("command", choices=[
        "show", "transition", "gate", "reconcile", "spec-audit", "spec-frozen", "check-impl",
        "complete-auto-compact", "reset-ledger",
    ])
    parser.add_argument("--project", default=None)
    parser.add_argument("--to", dest="target", default=None)
    parser.add_argument("--gate", default=None)
    parser.add_argument("--result", default=None, choices=[None, "PASS", "FAIL", "pass", "fail"])
    parser.add_argument("--reason", default="")
    parser.add_argument("--trigger", default="cli_manual")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--doc", action="append", default=None)
    args = parser.parse_args()

    runtime = FSMRuntime.bootstrap(args.project)
    if args.command == "show":
        print(json.dumps(runtime.state.to_dict(), indent=2, ensure_ascii=False, default=str))
    elif args.command == "transition":
        if not args.target:
            parser.error("--to required")
        runtime.transition(
            args.target,
            reason=args.reason or f"cli transition to {args.target}",
            trigger=args.trigger,
        )
        print(f"OK transitioned to {runtime.state.current}")
    elif args.command == "gate":
        if not args.gate or not args.result:
            parser.error("--gate and --result required")
        payload = runtime.record_gate_result(args.gate, args.result, args.reason)
        print(json.dumps(payload, ensure_ascii=False))
    elif args.command == "reconcile":
        applied = runtime.reconcile_ci_events()
        print(json.dumps({"applied": applied}, ensure_ascii=False))
    elif args.command == "spec-audit":
        print(json.dumps(runtime.record_spec_audit(), ensure_ascii=False))
    elif args.command == "spec-frozen":
        if not args.stage:
            parser.error("--stage required")
        runtime.record_spec_frozen(args.stage, args.doc or [])
        print(f"OK spec frozen: {args.stage}")
    elif args.command == "check-impl":
        print(json.dumps(runtime.check_implementation_budget(), ensure_ascii=False))
    elif args.command == "complete-auto-compact":
        result = runtime.complete_auto_compact()
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "reset-ledger":
        result = _reset_today_ledger()
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
