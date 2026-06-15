"""Phase H M5 / ACT-055 — Scaffold Metabolism GC.

落實 SDD_improving_Automation_08.md §5.1 / §G6+G7：讓系統學會「丟棄自己」。
常駐 GC Agent（sdd-gc-zh.yaml）週期性執行此邏輯（SCAFFOLD_GC observation 態）：
  ① 算每條規則的 Scaffold ROI（catch/fire）
  ② 提議畢業/降級（active → audit-only → deprecated；須人工 review 生效）
  ③ 稽核 decision_trace 正確性（哪些決策事後導致 escalation/drift）
  ④ 產出 build/reports/gc/SCAFFOLD-ROI-{date}.md

關鍵安全約束（§8 風險表）：GC 只「提議」，永不自動退役 verified/active 安全
規則——退役走 rule_loader.set_maturity(reviewed_by=...) 人工 gate。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from . import rule_loader

_ROOT = Path(__file__).resolve().parents[2]
GC_REPORT_DIR = _ROOT / "build" / "reports" / "gc"


@dataclass
class RetirementProposal:
    rule_id: str
    current_maturity: str
    proposed_maturity: str
    roi: float
    fire_count: int
    catch_count: int
    rationale: str


@dataclass
class TraceAuditEntry:
    from_state: str
    to_state: str
    trigger: str
    outcome: str  # "productive" | "led_to_escalation" | "led_to_drift" | "unknown"


@dataclass
class GCResult:
    proposals: List[RetirementProposal] = field(default_factory=list)
    trace_audit: List[TraceAuditEntry] = field(default_factory=list)
    rules_scanned: int = 0
    report_path: Optional[str] = None


def compute_proposals(*, rules_dir: Optional[Path] = None,
                      capability_checker: Optional[object] = None) -> List[RetirementProposal]:
    """掃所有規則，回傳畢業/降級提案（不寫入、不自動套用）。

    Phase J / ACT-076：`capability_checker` 為可選 callable(rule)->bool，回傳該規則
    對應能力是否「已被模型超越」（capability_benchmark.capability_surpassed）。提供時
    優先用能力驅動退役（較早觸發），否則 fallback 純 fire-count graduation。
    """
    proposals: List[RetirementProposal] = []
    for r in rule_loader.load_all(rules_dir):
        new_maturity = None
        reason_tag = ""
        if capability_checker is not None:
            try:
                surpassed = bool(capability_checker(r))
            except Exception:  # noqa: BLE001
                surpassed = False
            new_maturity = rule_loader.propose_graduation_capability(r, capability_surpassed=surpassed)
            if new_maturity is not None:
                reason_tag = "（能力驅動：benchmark 連續滿分 + 近乎從不 catch）"
        if new_maturity is None:
            new_maturity = rule_loader.propose_graduation(r)
        if new_maturity is None:
            continue
        proposals.append(RetirementProposal(
            rule_id=r.id,
            current_maturity=r.maturity,
            proposed_maturity=new_maturity,
            roi=r.roi(),
            fire_count=int(r.scaffold_roi.get("fire_count", 0)),
            catch_count=int(r.scaffold_roi.get("catch_count", 0)),
            rationale=(
                f"觸發 {r.scaffold_roi.get('fire_count', 0)} 次但 catch_count="
                f"{r.scaffold_roi.get('catch_count', 0)}（ROI={r.roi()}）— 模型可能已超出此鷹架。"
                + reason_tag
            ),
        ))
    return proposals


def audit_decision_trace(state) -> List[TraceAuditEntry]:
    """稽核 FSMState 的 decision_trace：標註哪些決策事後導致 escalation/drift（§4.2）。

    `state` 為 FSMState（暴露 decision_trace() 或 root['decision_trace']）。
    純啟發式：trigger 含 escalation/abort → led_to_escalation；含 drift → led_to_drift。
    """
    try:
        trace = state.decision_trace() if hasattr(state, "decision_trace") else \
            state.root.get("decision_trace", [])
    except Exception:  # noqa: BLE001
        trace = []
    out: List[TraceAuditEntry] = []
    for rec in (trace or []):
        if not isinstance(rec, dict):
            continue
        trig = str(rec.get("trigger", "")).lower()
        to_state = str(rec.get("to_state", rec.get("to", "")))
        if "escalat" in trig or "abort" in trig or to_state in ("ESCALATION", "ESCALATION_FINAL"):
            outcome = "led_to_escalation"
        elif "drift" in trig or to_state == "DRIFT_OBSERVATION":
            outcome = "led_to_drift"
        else:
            outcome = "productive"
        out.append(TraceAuditEntry(
            from_state=str(rec.get("from_state", rec.get("from", ""))),
            to_state=to_state,
            trigger=str(rec.get("trigger", "")),
            outcome=outcome,
        ))
    return out


def run_gc(state=None, *, rules_dir: Optional[Path] = None,
           out_dir: Optional[Path] = None, today: Optional[str] = None) -> GCResult:
    """執行一次 GC 週期並產出報告。`today` 由 caller 提供（避免 Date.now 不確定性）。"""
    proposals = compute_proposals(rules_dir=rules_dir)
    trace_audit = audit_decision_trace(state) if state is not None else []
    rules_scanned = len(rule_loader.load_all(rules_dir))

    result = GCResult(
        proposals=proposals,
        trace_audit=trace_audit,
        rules_scanned=rules_scanned,
    )

    target_dir = out_dir or GC_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or "unknown-date"
    path = target_dir / f"SCAFFOLD-ROI-{date}.md"

    lines = [
        f"# Scaffold ROI 報告 — {date}",
        "",
        f"- 掃描規則數：{rules_scanned}",
        f"- 退役/降級提案數：{len(proposals)}",
        f"- decision_trace 稽核筆數：{len(trace_audit)}",
        "",
        "## 退役/降級提案（須人工 review 後以 set_maturity(reviewed_by=...) 套用）",
        "",
    ]
    if proposals:
        lines.append("| 規則 | 現況 | 建議 | ROI | fire | catch | 理由 |")
        lines.append("|------|------|------|-----|------|-------|------|")
        for p in proposals:
            lines.append(
                f"| {p.rule_id} | {p.current_maturity} | {p.proposed_maturity} | "
                f"{p.roi} | {p.fire_count} | {p.catch_count} | {p.rationale} |"
            )
    else:
        lines.append("（本週期無提案——所有鷹架仍具攔截價值或觀察窗未滿）")
    lines.append("")
    led_esc = sum(1 for t in trace_audit if t.outcome == "led_to_escalation")
    led_drift = sum(1 for t in trace_audit if t.outcome == "led_to_drift")
    lines += [
        "## decision_trace 稽核摘要",
        "",
        f"- 導致 escalation 的決策：{led_esc}",
        f"- 導致 drift 的決策：{led_drift}",
        f"- productive 決策：{len(trace_audit) - led_esc - led_drift}",
        "",
        "> GC 僅提議，永不自動退役 active 規則（§8 安全約束）。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result.report_path = str(path)
    return result
