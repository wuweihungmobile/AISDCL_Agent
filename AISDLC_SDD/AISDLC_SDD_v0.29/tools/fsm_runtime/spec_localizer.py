"""Phase K M-K3 / ACT-085 — Causal Spec Localizer（因果規格定位）.

把 RTM(AC↔TC↔FRD↔NFR) + decision_trace 當**因果圖**：任一下游訊號（adversarial
counterexample / production drift / rtm gap）進來時，自動算 blast-radius + ranked
suspect spec 節點 + 證據鏈，取代 sa-analyst 手動指認「是哪條 AC」。結果餵 SPEC_PATCH_PROPOSAL /
PBS-DRIFT / steersman 供人裁決。

advisory（Rule 9.23.5）：只建議 suspect + 證據，**絕不自動改 spec**。純離線、可重現、零外網。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_AC_RE = re.compile(r"AC-\d+(?:-\d+)?")
_FRD_RE = re.compile(r"F(?:RD)?-\d+")
_NFR_RE = re.compile(r"NFR-\d+")
_TC_RE = re.compile(r"TC-\d+(?:-\d+){0,2}")


@dataclass
class RTMRow:
    ac_id: str
    frd_id: str = ""
    nfr_id: str = ""
    tc_ids: List[str] = field(default_factory=list)


@dataclass
class Signal:
    signal_type: str            # adversarial_counterexample | production_drift | rtm_gap
    tc_id: str = ""
    nfr_id: str = ""
    ac_hint: str = ""
    evidence: str = ""


@dataclass
class Suspect:
    node_id: str
    score: float
    evidence: str


@dataclass
class LocalizationResult:
    signal: Signal
    suspects: List[Suspect] = field(default_factory=list)
    blast_radius: List[str] = field(default_factory=list)

    def top(self, k: int = 1) -> List[str]:
        return [s.node_id for s in self.suspects[:k]]


def _bump(scores: Dict[str, Suspect], node: str, score: float, evidence: str) -> None:
    """保留每節點最高分（同分時累加證據）。"""
    cur = scores.get(node)
    if cur is None or score > cur.score:
        scores[node] = Suspect(node_id=node, score=round(score, 4), evidence=evidence)


def _trace_refs(decision_trace: Optional[list]) -> set:
    refs: set = set()
    for entry in decision_trace or []:
        sr = entry.get("spec_refs") if isinstance(entry, dict) else getattr(entry, "spec_refs", None)
        for r in (sr or []):
            refs.add(r)
    return refs


def localize(signal: Signal, *, rtm: List[RTMRow],
             decision_trace: Optional[list] = None) -> LocalizationResult:
    """以 RTM + decision_trace 因果圖回溯 suspect 節點（ranked + 證據）。"""
    tc_to_ac: Dict[str, List[str]] = {}
    nfr_to_ac: Dict[str, List[str]] = {}
    ac_to_frd: Dict[str, str] = {}
    frd_to_acs: Dict[str, List[str]] = {}
    ac_row: Dict[str, RTMRow] = {}
    for row in rtm:
        ac_row[row.ac_id] = row
        if row.frd_id:
            ac_to_frd[row.ac_id] = row.frd_id
            frd_to_acs.setdefault(row.frd_id, []).append(row.ac_id)
        if row.nfr_id:
            nfr_to_ac.setdefault(row.nfr_id, []).append(row.ac_id)
        for tc in row.tc_ids:
            tc_to_ac.setdefault(tc, []).append(row.ac_id)

    scores: Dict[str, Suspect] = {}

    if signal.ac_hint:
        _bump(scores, signal.ac_hint, 1.0, f"直接 AC 提示（{signal.signal_type}）")
    if signal.tc_id:
        for ac in tc_to_ac.get(signal.tc_id, []):
            _bump(scores, ac, 0.9, f"{signal.tc_id} → {ac}（RTM 直接追溯）")
            frd = ac_to_frd.get(ac, "")
            if frd:
                _bump(scores, frd, 0.5, f"{ac} 之父 FRD {frd}")
    if signal.nfr_id:
        for ac in nfr_to_ac.get(signal.nfr_id, []):
            _bump(scores, ac, 0.9, f"NFR {signal.nfr_id} → {ac}（RTM NFR 追溯）")
            frd = ac_to_frd.get(ac, "")
            if frd:
                _bump(scores, frd, 0.5, f"{ac} 之父 FRD {frd}")

    # decision_trace 共現加成（因果近因訊號）
    refs = _trace_refs(decision_trace)
    for node, suspect in list(scores.items()):
        if node in refs:
            _bump(scores, node, min(1.0, suspect.score + 0.1),
                  suspect.evidence + " + decision_trace 命中")

    suspects = sorted(scores.values(), key=lambda s: (-s.score, s.node_id))

    # blast radius：top suspect AC 的一跳鄰域（FRD + 同 FRD 兄弟 AC + 自身 TC）
    blast: List[str] = []
    if suspects:
        top = suspects[0].node_id
        if top in ac_row:
            blast.append(top)
            frd = ac_to_frd.get(top, "")
            if frd:
                blast.append(frd)
                blast.extend(a for a in frd_to_acs.get(frd, []) if a != top)
            blast.extend(ac_row[top].tc_ids)
    # 去重保序
    seen: set = set()
    blast = [n for n in blast if not (n in seen or seen.add(n))]

    return LocalizationResult(signal=signal, suspects=suspects, blast_radius=blast)


# ---------- 便捷 adapter（三種下游訊號入口）----------

def localize_from_counterexample(tc_id: str, rtm: List[RTMRow], *, ac_hint: str = "",
                                 decision_trace: Optional[list] = None) -> LocalizationResult:
    return localize(Signal("adversarial_counterexample", tc_id=tc_id, ac_hint=ac_hint),
                    rtm=rtm, decision_trace=decision_trace)


def localize_from_production_drift(nfr_id: str, rtm: List[RTMRow], *,
                                   decision_trace: Optional[list] = None) -> LocalizationResult:
    return localize(Signal("production_drift", nfr_id=nfr_id),
                    rtm=rtm, decision_trace=decision_trace)


def localize_from_rtm_gap(tc_id: str, rtm: List[RTMRow], *,
                          decision_trace: Optional[list] = None) -> LocalizationResult:
    return localize(Signal("rtm_gap", tc_id=tc_id), rtm=rtm, decision_trace=decision_trace)


# ---------- RTM markdown 解析（從真實 RTM-*.md 建圖）----------

def parse_rtm_markdown(text: str) -> List[RTMRow]:
    """從 RTM pipe table 抽取 RTMRow（每列首個 AC、首個 FRD/NFR、所有 TC）。"""
    rows: List[RTMRow] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        if re.match(r"^\s*\|[\s:\-|]+\|?\s*$", line):   # 分隔列
            continue
        ac = _AC_RE.search(line)
        if not ac:
            continue
        frd = _FRD_RE.search(line)
        nfr = _NFR_RE.search(line)
        tcs = _TC_RE.findall(line)
        rows.append(RTMRow(ac_id=ac.group(0),
                           frd_id=frd.group(0) if frd else "",
                           nfr_id=nfr.group(0) if nfr else "",
                           tc_ids=tcs))
    return rows


# ---------- 報告（餵 patch / PBS-DRIFT / steersman）----------

def localization_report(result: LocalizationResult) -> str:
    """產出 markdown 定位報告（advisory，供人裁決；不自動改 spec）。"""
    sig = result.signal
    lines = [
        "## 🔎 因果定位（Causal Spec Localization — advisory，Rule 9.23.5）",
        "",
        f"- 訊號：`{sig.signal_type}`"
        + (f"｜tc={sig.tc_id}" if sig.tc_id else "")
        + (f"｜nfr={sig.nfr_id}" if sig.nfr_id else "")
        + (f"｜hint={sig.ac_hint}" if sig.ac_hint else ""),
    ]
    if result.suspects:
        lines.append(f"- Top suspect：**{result.suspects[0].node_id}**（score {result.suspects[0].score}）")
        lines += ["", "### Ranked suspects"]
        for s in result.suspects:
            lines.append(f"- `{s.node_id}` — score {s.score} — {s.evidence}")
        lines += ["", "### Blast radius", "- " + ", ".join(result.blast_radius or ["—"])]
    else:
        lines.append("- （無命中 suspect — RTM 未覆蓋此訊號，建議補 RTM 追溯）")
    lines += ["", "> advisory：僅建議 suspect + 證據，需人工裁決，**絕不自動改 spec**。"]
    return "\n".join(lines) + "\n"
