"""Phase I M3 / ACT-066 — Skill Pattern (SPL) Consolidator（成功結晶 sleep-phase）.

落實 SDD_improving_Automation_09.md §4.2 / §5.2 / PI-6：補上學習層的「合成代謝」。
掃 decision_trace（含 flushed）對 **productive** 軌跡用 pattern_matcher.is_same_pattern
聚類（沿用 ACT-021）；≥N 次同模式成功 → 產出 trust_level=proposed 的 SPL 草案
（人工 verified gate，禁自動 verified）。

與 scaffold_gc（分解代謝/退役）對稱：SPL = 合成代謝（結晶/固化）。MEMORY_CONSOLIDATION
observation 態於 nightly sleep-phase（03:00 UTC）/ LEARNING_COMMIT / RELEASE 後驅動本邏輯。

決定論：今天日期由 caller 傳入（避免 Date.now 不確定性，沿用 scaffold_gc 慣例）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .pattern_matcher import is_same_pattern

SKILL_PATTERNS_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "skill-patterns"

# 同模式成功 ≥ N 次才提案結晶（防偶發成功誤結晶為技能）
CONSOLIDATION_MIN_EPISODES = 3


@dataclass
class SkillProposal:
    spl_id: str
    trigger_states: List[str]
    abstracted_steps: List[str]
    reuse_count: int
    source_episodes: List[str] = field(default_factory=list)
    trust_level: str = "proposed"   # 永不自動 verified


def _productive_episodes(state) -> List[dict]:
    """從 decision_trace(+flushed) 取 productive（非 escalation/drift）軌跡。"""
    root = getattr(state, "root", {}) or {}
    trace = list(root.get("decision_trace", []) or [])
    trace += list(root.get("decision_trace_flushed", []) or [])
    out: List[dict] = []
    for rec in trace:
        if not isinstance(rec, dict):
            continue
        trig = str(rec.get("trigger", "")).lower()
        to_state = str(rec.get("to_state", rec.get("to", "")))
        if "escalat" in trig or "abort" in trig or "drift" in trig:
            continue
        if to_state in ("ESCALATION", "ESCALATION_FINAL", "DRIFT_OBSERVATION"):
            continue
        out.append(rec)
    return out


def _episode_signature(rec: dict) -> str:
    frm = str(rec.get("from_state", rec.get("from", "")))
    to = str(rec.get("to_state", rec.get("to", "")))
    return f"{frm}->{to}: {rec.get('reason', '')}"


def cluster_productive(state, *, min_episodes: int = CONSOLIDATION_MIN_EPISODES) -> List[SkillProposal]:
    """聚類 productive 軌跡為候選技能（≥ min_episodes 同模式才提案）。"""
    episodes = _productive_episodes(state)
    clusters: List[List[dict]] = []
    for rec in episodes:
        sig = _episode_signature(rec)
        placed = False
        for cl in clusters:
            if is_same_pattern(_episode_signature(cl[0]), sig):
                cl.append(rec)
                placed = True
                break
        if not placed:
            clusters.append([rec])

    proposals: List[SkillProposal] = []
    idx = 1
    for cl in clusters:
        if len(cl) < min_episodes:
            continue
        trig_states = sorted({str(r.get("from_state", r.get("from", ""))) for r in cl if r.get("from_state") or r.get("from")})
        steps = [_episode_signature(cl[0])]
        proposals.append(SkillProposal(
            spl_id=f"SPL-{idx:03d}",
            trigger_states=trig_states,
            abstracted_steps=steps,
            reuse_count=len(cl),
            source_episodes=[_episode_signature(r) for r in cl],
            trust_level="proposed",
        ))
        idx += 1
    return proposals


def write_proposal(
    proposal: SkillProposal,
    *,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
) -> str:
    """寫 SPL 草案 YAML（trust_level=proposed，帶 provenance 審計鏈）。

    永不寫 verified — 人工 review 升級才 enforce（仿 slv_generator）。
    """
    import yaml  # type: ignore
    target = out_dir or SKILL_PATTERNS_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{proposal.spl_id}.yaml"
    doc: Dict = {
        "id": proposal.spl_id,
        "trigger_states": proposal.trigger_states,
        "abstracted_steps": proposal.abstracted_steps,
        "reuse_count": proposal.reuse_count,
        "provenance": {
            "source_episodes": proposal.source_episodes,
            "consolidated_at": today or "unknown-date",
            "consolidator": "spl_consolidator (ACT-066)",
        },
        "trust_level": "proposed",   # 強制 proposed（禁自動 verified）
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(path)
    return str(path)


def consolidate(state, *, out_dir: Optional[Path] = None, today: Optional[str] = None,
                min_episodes: int = CONSOLIDATION_MIN_EPISODES, write: bool = True) -> List[SkillProposal]:
    """一次 sleep-phase 結晶：聚類 + （可選）寫 proposed SPL 草案。"""
    proposals = cluster_productive(state, min_episodes=min_episodes)
    if write:
        for p in proposals:
            write_proposal(p, out_dir=out_dir, today=today)
    return proposals
